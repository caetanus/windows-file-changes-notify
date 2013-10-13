# -*- coding: utf-8 -*-

from .win32_objects import (NOTIFY_CONSTANTS, FindNextChangeNotification,
               FindCloseChangeNotification, FindFirstChangeNotification,
               DirectoryWatcherError, WaitForMultipleObjectsPool,
               CreateFileDirectory, ReadDirectoryChangesW, OVERLAPPED,
               ACTION_DICT, FILE_NOTIFY_INFORMATION_STRUCT, CloseHandle,
               GetOverlappedResult, IoCompletionPort, CreateEvent,
               GetLastError, FormatError, FILE_ACTION_RENAMED_OLD_NAME,
               FILE_ACTION_RENAMED_NEW_NAME)
from ctypes import byref, create_string_buffer
from ctypes.wintypes import DWORD
import struct
import os



class FSWatcherError(DirectoryWatcherError):
    pass

class FSFileWatcherError(DirectoryWatcherError):
    pass

class InvalidWatchType(FSFileWatcherError):
    pass


default_notification_list = ('ChangeSize',
                             'LastWrite',
                             'ChangeSecurity',
                             'ChangeAttributes',
                             'ChangeDirName',
                             'ChangeFileName')

class WinDirectoryWatcher(object):
    def __init__(self, path, recursive=True,
                 notify_atributes_list=default_notification_list):
        if type(path) is not unicode:
            try:
                path = unicode(path)
            except:
                raise IOError, "path should be unicode or convertable."

        if not os.path.isdir(path):
            raise InvalidWatchType, "the path should be a directory."

        if not os.path.exists(path):
            raise FSWatcherError, "path doesn't exist"
        try:
            self._flags = reduce(lambda a, b: a | b,
                                (NOTIFY_CONSTANTS[i]
                                 for i in notify_atributes_list))
        except KeyError:
            raise DirectoryWatcherError, "invalid notify_attributes_list"

        self._watching = False
        self.recursive = True
        self.path = path
        self._queued_results = []


    def _async_watch_directory(self):
        overlapped = self._overlapped
        overlapped.Internal = 0
        overlapped.InternalHigh = 0
        overlapped.Offset = 0
        overlapped.OffsetHigh = 0
        overlapped.Pointer = 0
        overlapped.hEvent = 0
        ReadDirectoryChangesW(self._file_handle, byref(self._result),
                              len(self._result), self.recursive,
                              self._flags, None, overlapped, None)


    def _watch(self):
        self._handle = FindFirstChangeNotification(self.path, self._flags,
                                                  self.recursive)

    def start_watching(self):
        self._watching = True
        self._watch()
        self._file_handle = CreateFileDirectory(self.path)
        #self._iocp = IoCompletionPort()
        #self._iocp.attach_fsobject(self)
        self._overlapped = OVERLAPPED()
        self._overlapped.hEvent = CreateEvent()
        self._result = create_string_buffer(8192)
        self._async_watch_directory()

    def stop_watching(self):
        if self._file_handle:
            closed = CloseHandle(self._file_handle)
            self._file_handle = None

        if hasattr(self, '_wfmo'):
            self._watch._cancel_all_threads()
            del self._wmfo

        if self._handle:
            closed = CloseHandle(self._handle)
            self._handle = None

        if self._overlapped:
            CloseHandle(self._overlapped.hEvent)

        self._overlapped = None
        self._result = None
        self._watching = False

        if hasattr(self, '_iocp'):
            self._iocp.destroy()
            del self._iocp


    def _parse_read_directory_changes_result(self, location=0):
        fmt = FILE_NOTIFY_INFORMATION_STRUCT
        fmt_size = struct.calcsize(FILE_NOTIFY_INFORMATION_STRUCT)
        next_entry = 1
        pos = location
        FindNextChangeNotification(self._handle)
        bytes_read = DWORD()
        old_overlapped = self._overlapped

        while next_entry:
            next_entry, action, namelen = struct.unpack_from(fmt, self._result[pos:])
            str_pos = pos + fmt_size
            str_len = namelen + str_pos
            name = self._result[str_pos:str_len].decode('utf-16')
            pos += next_entry
            if action == FILE_ACTION_RENAMED_OLD_NAME:
                renamed_old = name
                continue
            if action == FILE_ACTION_RENAMED_NEW_NAME:
                yield ('Moved', renamed_old, name)
                continue

            yield (ACTION_DICT[action], name)

        ret_value = GetOverlappedResult(self._handle, old_overlapped,
                                        byref(bytes_read), True)
        if not ret_value:
            raise WinDirectoryWatcher, FormatError(GetLastError())

        self._async_watch_directory()

    def _auto_fetch_events(self):
        self._wmfo = FSObjectWatcherWMFOPool()
        self._wmfo.register(self)

    def pool(self, timeout=-1):
        if not self._watching:
            raise DirectoryWatcherError, "Not Watching"

        if not hasattr(self, '_wmfo'):
            self._auto_fetch_events()

        if self._queued_results:
            return self._queued_results.pop(0)

        self._wmfo.pool(timeout)
        self._queued_results = [i for i in
                                self._parse_read_directory_changes_result()]
        return self.pool(timeout)


class FSObjectWatcherWMFOPool(WaitForMultipleObjectsPool):

    def __init__(self):
        self._handle_fs_object_watcher = {}
        self._fs_object_watcher_handle = {}
        WaitForMultipleObjectsPool.__init__(self)

    def register(self, object_watcher):
        handle = object_watcher._handle
        WaitForMultipleObjectsPool.register_handle(self, handle)
        self._handle_fs_object_watcher[handle] = object_watcher

    def unregister(self, object_watcher):
        for handle in self._fs_object_watcher_handle[object_watcher]:
            WaitForMultipleObjectsPool.unregister_handle(self, handle)
            del self._handle_fs_object_watcher[handle]

    def pool(self, timeout=-1):
        ret_val = WaitForMultipleObjectsPool.pool(self, timeout)
        obj = self._handle_fs_object_watcher[ret_val]
        return (ret_val, obj)
