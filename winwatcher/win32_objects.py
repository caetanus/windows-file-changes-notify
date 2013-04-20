# -*- coding: utf-8 -*-


import sys
from ctypes import (windll, c_wchar_p, c_long, c_int, c_uint, c_void_p,
                    c_int32,  Structure, wstring_at, c_wchar_p, POINTER)
from ctypes.wintypes import (DWORD, HANDLE, BOOL, LPWSTR, LPVOID, GetLastError,
                             FormatError, WCHAR)
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

OVERLAPPED = c_void_p

MAX_OBJECTS = 0x7F
WAIT_OBJECT_0 = 0x00000000
WAIT_OBJECT_ABANDONED_0 = 0x00000080
WAIT_TIMEOUT = 0x00000102L
WAIT_FAILED = ~0 # -1
WAIT_INFINITE = ~0 # -1


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

ReadDirectoryChangesW = kernel32.ReadDirectoryChangesW
FILE_ACTION_ADDED = 0x1
FILE_ACTION_REMOVED = 0x2
FILE_ACTION_MODIFIED = 0x3
FILE_ACTION_RENAMED_OLD_NAME = 0x4
FILE_ACTION_RENAMED_NEW_NAME = 0x5

class FILE_NOTIFY_INFORMATION(Structure):
    _fields_ = [
                ('NextEntryOffset', DWORD),
                ('Action', DWORD),
                ('FileNameLength', DWORD),
                ('FileName', c_wchar_p)
               ]
LPFILE_NOTIFY_INFORMATION = POINTER(FILE_NOTIFY_INFORMATION)

class OVERLAPPED(Structure):
    _fields_ = [('Internal', LPVOID),
                ('InternalHigh', LPVOID),
                ('Offset', DWORD),
                ('OffsetHigh', DWORD),
                ('Pointer', LPVOID),
                ('hEvent', HANDLE),
               ]
LPOVERLAPPED = POINTER(OVERLAPPED)
#ReadDirectoryChangesW.argtypes = [HANDLE, LPFILE_NOTIFY_INFORMATION,
#                                  DWORD, BOOL, POINTER(DWORD),
#                                  c_void_p, c_void_p]

try:
    ReadDirectoryChangesW = kernel32.ReadDirectoryChangesW
except AttributeError:
    raise ImportError("ReadDirectoryChangesW is not available")
ReadDirectoryChangesW.restype = BOOL
ReadDirectoryChangesW.argtypes = (
    HANDLE, # hDirectory
    LPVOID, # lpBuffer
    DWORD, # nBufferLength
    BOOL, # bWatchSubtree
    DWORD, # dwNotifyFilter
    POINTER(DWORD), # lpBytesReturned
    LPOVERLAPPED,# lpOverlapped
    LPVOID #FileIOCompletionRoutine # lpCompletionRoutine
)

CreateFileW = kernel32.CreateFileW
CreateFileW.restype = HANDLE
CreateFileW.argtypes = (
    LPCWSTR, # lpFileName
    DWORD, # dwDesiredAccess
    DWORD, # dwShareMode
    LPVOID, # lpSecurityAttributes
    DWORD, # dwCreationDisposition
    DWORD, # dwFlagsAndAttributes
    HANDLE # hTemplateFile
)

class DirectoryWatcherError(WindowsError):
    pass

class WaitForMultipleObjectsError(WindowsError):
    pass

class TimeoutError(WaitForMultipleObjectsError):
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
        self._lphandles = []
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

        if not self._lphandles and timeout:
            raise TimeoutError

        elif not self._lphandles:
            raise WaitForMultipleObjectsError, "can't pool an empty list"

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


