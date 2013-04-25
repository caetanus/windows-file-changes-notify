# -*- coding: utf-8 -*-

import os
import sys
import struct
from Queue import Queue, Empty
import threading, thread


from .win32_defs import *
from .win32_defs import (_CreateEvent, _FindFirstChangeNotification,
                         _WaitForMultipleObjects)


class DirectoryWatcherError(WindowsError):
    pass

class WaitForMultipleObjectsError(WindowsError):
    pass

class TimeoutError(WaitForMultipleObjectsError):
    pass



NOTIFY_CONSTANTS = {'ChangeFileName': FILE_NOTIFY_CHANGE_FILE_NAME,
                    'ChangeDirName' : FILE_NOTIFY_CHANGE_DIR_NAME,
                    'ChangeAttributes' : FILE_NOTIFY_CHANGE_ATTRIBUTES,
                    'ChangeSize' : FILE_NOTIFY_CHANGE_SIZE,
                    'LastWrite' : FILE_NOTIFY_CHANGE_LAST_WRITE,
                    'ChangeSecurity' : FILE_NOTIFY_CHANGE_SECURITY
                   }


ACTION_DICT = {
        FILE_ACTION_ADDED: "Added",
        FILE_ACTION_REMOVED: "Removed",
        FILE_ACTION_MODIFIED: "Modified",
        FILE_ACTION_RENAMED_OLD_NAME: "RenamedOld",
        FILE_ACTION_RENAMED_NEW_NAME: "RenamedNew"
    }

def CreateEvent():
    return _CreateEvent(None, False, False, None)

def AccessThreadSynchronize(thread_id):
    handle = OpenThread(THREAD_ACCESS_SYNCHRONIZE, False, thread_id)
    if not handle:
        raise WindowsError, "Cannot open thread to synchronization."
    CloseHandle(handle)

def CreateFileDirectory(path):
    if type(path) is not unicode:
        raise IOError, "Directory path should be unicode."
    handle = CreateFileW(path, FILE_LIST_DIRECTORY,
                         FILE_SHARE_READ | FILE_SHARE_WRITE,
                         None,
                         OPEN_EXISTING,
                         FILE_FLAG_BACKUP_SEMANTICS| FILE_FLAG_OVERLAPPED,
                         None)
    return handle

class IoCompletionPortError(WindowsError):
    pass

class IoCompletionPort(object):
    def __init__(self):
        self._fsobjects = {}
        self._iocp_key = CreateIoCompletionPort(INVALID_HANDLE_VALUE,
                                                None, None, 0)
        if self._iocp_key is None:
            raise IoCompletionPortError, ("cannot create io "
                                          "completion port in this system")

    def attach_fsobject(self, fsobject):
        if fsobject in self._fsobjects:
            return
        completion_key = c_ulong()

        self._fsobjects[fsobject] = completion_key
        CreateIoCompletionPort(fsobject._handle, self._iocp_key,
                               byref(completion_key), 0)

    def fsobject_get_status(self, fsobject):
        if not fsobject in self._fsobjects:
            raise IoCompletionPortError, ("object is not attached to "
                                          "io completion port")
        bytes_to_read = DWORD()
        completion_key = self._fsobjects[fsobject]
        over = OVERLAPPED()

        res = GetQueuedCompletionStatus(self._iocp_key, byref(bytes_to_read),
                                        byref(completion_key),
                                        byref(over), 0)
        if not res:
            raise IoCompletionPortError, FormatError(GetLastError())
        return bytes_to_read.value

    def destroy(self):
        CloseHandle(self._iocp_key)



FILE_NOTIFY_INFORMATION_STRUCT = "iii"


class WaitForMultipleObjectsPool(object):
    def __init__(self):
        self._queue = Queue()
        self._mutex = threading.Lock()
        self._handles = []
        self._lphandles = []
        self._threads = []

    def register_handle(self, handle):
        self._handles.append(handle)
        with self._mutex:
            self._update_lphandles()

    def _update_lphandles(self):
        handles = self._handles[:]
        self._lphandles = []
        while handles:
            handle_slice = handles[:MAX_OBJECTS]
            handles = handles[MAX_OBJECTS:]
            lphandles = handle_slice
            self._lphandles.append(lphandles)

    def unregister_handle(self, handle):
        self._handles.remove(handle)
        with self._mutex:
            self._update_lphandles()

    def __start_workers(self, timeout):

        for index, handles in enumerate(self._lphandles):
            event = CreateEvent()

            count = len(handles) + 1
            lphandles = [event] + handles
            thread = threading.Thread(name='WFMO-Worker-%d' % index,
                                      target=self._WaitForMultipleObjectsWorker,
                                      args=(index, lphandles, timeout))
            self._threads.append((thread, event))
            thread.start()


    def pool(self, timeout=-1):

        try:
            handle_id = self._queue.get_nowait()
            return self._parse_wfmo_result(handle_id)
        except Empty:
            pass

        self._cancel_all_threads()

        if len(self._lphandles) > 0:
            self.__start_workers(timeout)

        elif not self._lphandles and timeout > 0:
            raise TimeoutError

        elif not self._lphandles:
            raise WaitForMultipleObjectsError, "can't pool an empty list"

        return self._parse_wfmo_result(self._queue.get())

    def _cancel_all_threads(self):
        for thread, event in self._threads:
            SetEvent(event)
            try:
                thread.join()
            except RuntimeError:
                pass
            CloseHandle(event)
        self._threads = []

    def _WaitForMultipleObjectsWorker(self, index, lphandles,
                                      timeout=-1):

        #NOTE: we can't put the WaitForMultipleEvents on a while just waiting
        #      for next event, because sometimes the user needs to signal
        #      the event as seen. so, it will fail.
        wait_all = False
        with self._mutex:
            lphandles = (HANDLE * len(lphandles))(*lphandles)

        if timeout > 0:
            timeout = int(timeout * 1000)

        result = _WaitForMultipleObjects(len(lphandles),
                                         lphandles, False,
                                         timeout)

        if result == WAIT_FAILED:
            self._queue.put(index, GetLastError(), FormatError(GetLastError()))

        elif result in (WAIT_OBJECT_ABANDONED_0, WAIT_OBJECT_0):
            #used when we got the first event.
            #we don't need the first event because it is used to cancel
            return

        elif result == WAIT_TIMEOUT:
            self._queue.put((index, TimeoutError, "WFMO timeout expired"))

        elif result > WAIT_OBJECT_ABANDONED_0:
            obj = (WAIT_OBJECT_ABANDONED_0 - result - 1) + (MAX_OBJECTS * index)
            self._queue.put(obj)

        else:
            obj = result - 1 + (MAX_OBJECTS * index)
            self._queue.put(obj)

    def _parse_wfmo_result(self, ret_value):
        if type(ret_value) is tuple:
            index, error, desc = ret_value
            if type(error) is int:
                raise WaitForMultipleObjectsError, (
                    "Thread(%d): Failed %d: %s" % (ret_value)
                )
            else:
                raise error, ('Thread(%d) %s' % (index, error))
        try:
            return self._handles[ret_value]
        except:
            raise DirectoryWatcherError, "unhandled error, trying to get an event that doesn't exists, race condition?"



