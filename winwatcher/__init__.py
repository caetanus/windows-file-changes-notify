# -*- coding: utf-8 -*-
import sys
from ctypes import windll, c_wchar_p, c_long, c_uint, c_void_p
from ctypes.wintypes import (DWORD, HANDLE, BOOL, LPWSTR, GetLastError,
                             FormatError)
from Queue import Queue, Empty
import threading

import os
kernel32 = windll.kernel32
INVALID_HANDLE_VALUE = ~0
FILE_NOTIFY_CHANGE_FILE_NAME = 0x00000001
FILE_NOTIFY_CHANGE_DIR_NAME = 0x00000002
FILE_NOTIFY_CHANGE_ATTRIBUTES = 0x00000004
FILE_NOTIFY_CHANGE_SIZE = 0x00000008
FILE_NOTIFY_CHANGE_LAST_WRITE = 0x00000010
FILE_NOTIFY_CHANGE_SECURITY = 0x00000100

MAX_OBJECTS = 0x7F
WAIT_OBJECT_0 = 0x00000000
WAIT_OBJECT_ABANDONED_0 = 0x00000080
WAIT_TIMEOUT = 0x00000102L
WAIT_FAILED = ~0


NOTIFY_CONSTANTS = {'ChangeFileName': FILE_NOTIFY_CHANGE_FILE_NAME,
                    'ChangeDirName' : FILE_NOTIFY_CHANGE_DIR_NAME,
                    'ChangeAttributes' : FILE_NOTIFY_CHANGE_ATTRIBUTES,
                    'ChangeSize' : FILE_NOTIFY_CHANGE_SIZE,
                    'LastWrite' : FILE_NOTIFY_CHANGE_LAST_WRITE,
                    'ChangeSecurity' : FILE_NOTIFY_CHANGE_SECURITY
                   }

FILE_NOTIFY_CHANGE_ALL_BUT_SECURITY = (FILE_NOTIFY_CHANGE_FILE_NAME|
                                       FILE_NOTIFY_CHANGE_ATTRIBUTES|
                                       FILE_NOTIFY_CHANGE_DIR_NAME|
                                       FILE_NOTIFY_CHANGE_LAST_WRITE|
                                       FILE_NOTIFY_CHANGE_SIZE)


_FindFirstChangeNotification = kernel32.FindFirstChangeNotificationW
_FindFirstChangeNotification.argtypes = [LPWSTR, BOOL, DWORD]



FindNextChangeNotification = kernel32.FindNextChangeNotification
FindNextChangeNotification.argtypes = [HANDLE]

FindCloseChangeNotification = kernel32.FindCloseChangeNotification
FindCloseChangeNotification.argtypes = [HANDLE]

_WaitForMultipleObjects = kernel32.WaitForMultipleObjects
_WaitForMultipleObjects.argtypes = [DWORD, c_void_p, BOOL, DWORD]

class DirectoryWatcherError(WindowsError):
    pass

class WaitForMultipleObjectsError(WindowsError):
    pass

class TimeoutError(WaitForMultipleObjectsError):
    pass

class FSWatcherError(DirectoryWatcherError):
    pass

class FSFileWatcherError(DirectoryWatcherError):
    pass

def FindFirstChangeNotification(directory,
                                flags=FILE_NOTIFY_CHANGE_ALL_BUT_SECURITY,
                                recursive=False):

    handle = _FindFirstChangeNotification(directory, recursive, flags)
    if handle == INVALID_HANDLE_VALUE:
        raise DirectoryWatcherError
    return handle


class WaitForMultipleObjectsPool(object):
    def __init__(self):
        self._queue = Queue()
        self._mutex = threading.Lock()
        self._handles = []
        self._lphandles = []

    def register_handle(self, handle):
        self._handles.append(handle)
        with self._mutex:
            self._update_lphandles()

    def _update_lphandles(self):
        handles = self._handles[:]
        while handles:
            handle_slice = handles[:MAX_OBJECTS]
            handles = handles[MAX_OBJECTS:]
            lphandles = (HANDLE * len(handle_slice))(*handle_slice)
            self._lphandles.append((len(handle_slice), lphandles))

    def unregister_handle(self, handle):
        self._handles.remove(handle)
        with self._mutex:
            self._update_lphandles()

    def pool(self, timeout=None):
        try:
            handle_id = self._queue.get_nowait()
            return self._parse_wfmo_result(handle_id)
        except Empty:
            pass

        for count, lphandles in self._lphandles:
            thread = threading.Thread(target=self._WaitForMultipleObjectsWorker, args=(count, lphandles, timeout))
            sys.stderr.flush()
            thread.start()
        return self._parse_wfmo_result(self._queue.get())
    def _WaitForMultipleObjectsWorker(self, count, lphandles, timeout):
        wait_all = False
        timeout = int(timeout * 1000)
        self._queue.put(_WaitForMultipleObjects(count, lphandles, wait_all, timeout))

    def _parse_wfmo_result(self, ret_value):
        count = len(self._handles)
        if ret_value == WAIT_FAILED:
            raise WaitForMultipleObjectsError, "Failed %s" % FormatError(GetLastError())

        if (WAIT_OBJECT_0 - ret_value) > count:
            if ret_value == 0x80:
                raise WaitForMultipleObjectsError, "Wait Abandoned"
            if ret_value == WAIT_TIMEOUT:
                raise TimeoutError
        return self._handles[WAIT_OBJECT_0 - ret_value]

class WinFolderWatcher(object):

    def __init__(self):
        self._handles = {}
        self._event_type_handles = {}

    def watch(self, path, recursive):
        self._path = path
        ignore_notifies = ['NotifyChangeSecurity']
        for notify_type, notify_const in NOTIFY_CONSTANTS.items():
            if notify_type in ignore_notifies:
                continue
            handle = FindFirstChangeNotification(path, recursive, notify_const)
            self._handles[handle] = notify_type
            self._event_type_handles[notify_type] = handle

class FolderTracker(object):
    pass


class _WinFSObjectWatcher(object):
    def __init__(self, path):
        if not os.path.exists(path):
            raise FSWatcherError, "path doesn't exist"
        self._children = []
        self._parent = None
        self.is_dir = os.path.isdir(path)
        self._stat = os.stat(path)
        self.path = path
        self._handles = {}
        self._event_type_handles = {}

    def _watch_by_event_type(self, event_type):
        handle = FindFirstChangeNotification(self.path,
                                             NOTIFY_CONSTANTS[event_type])
        self._handles[handle] = event_type
        self._event_type_handles[event_type] = handle

    def add_child(self, obj):
        if not isinstance(obj, _WinFSObjectWatcher):
            raise FSWatcherError("cannot add child with type(%s), "
                                 "just accept objects of family "
                                 "_WinFSOBjectWatcher" % type(obj))
        self._children.append(obj)
        obj._parent = self


    def start_watching(self):
        self._watch_by_event_type('ChangeAttributes')

    def unwatch_ret_handlers(self):
        handles = []
        for handle in self._handles.keys():
            out.append(handle)
            FindCloseChangeNotification(handle)
            event_type = self._handles[handle]
            del self._handles[handle]
            del self._event_type_handles[event_type]
        return handles

    def find_child_by_handle(self, handle):
        if handle in self._handles:
            return self
        else:
            for obj in map(lambda child: child.find_child_by_handle(handle),
                           self._children):
                if obj:
                    return obj

    def get_root_object(self):
        if self._parent is None:
            return self
        else:
            return self._parent.get_root_object()



class _WinFileObjectWatcher(_WinFSObjectWatcher):
    def __init__(self, path):
        super(_WinFileObjectWatcher, self).__init__(path)
        if self.is_dir:
            raise FSFileWatcherError, "the path %s looks like a directory." % path

    def start_watching(self):
        super(_WinFSObjectWatcher, self).start_watching()
        map(self._watch_by_event_type, ["ChangeFileName", "ChangeSize", "LastWrite"])


