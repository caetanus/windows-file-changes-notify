# -*- coding: utf-8 -*-

from .win32_objects import (NOTIFY_CONSTANTS, FindNextChangeNotification,
               FindCloseChangeNotification, FindFirstChangeNotification,
               DirectoryWatcherError, WaitForMultipleObjectsPool,
               CreateFileDirectory, ReadDirectoryChangesW, OVERLAPPED,
               ACTION_DICT, FILE_NOTIFY_INFORMATION_STRUCT, CloseHandle)
from ctypes import byref, create_string_buffer
import struct
import os



class FSWatcherError(DirectoryWatcherError):
    pass

class FSFileWatcherError(DirectoryWatcherError):
    pass

class InvalidWatchType(FSFileWatcherError):
    pass

def get_stat(path):
    return os.stat(path)

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
        self._stat = get_stat(path)
        self.path = path


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

    def add_child(self, obj):
        if not isinstance(obj, _WinFSObjectWatcher):
            raise FSWatcherError("cannot add child with type(%s), "
                                 "just accept objects of family "
                                 "_WinFSOBjectWatcher" % type(obj))
        self._children.append(obj)
        obj._parent = self

    def start_watching(self):
        self._watching = True
        self._watch()
        self._file_handle = CreateFileDirectory(self.path)
        self._overlapped = OVERLAPPED()
        self._result = create_string_buffer(1024)
        self._async_watch_directory()

    def stop_watching(self):
        if self._file_handle:
            closed = CloseHandle(self._file_handle)
            self._file_handle = None
        if self._handle:
            closed = CloseHandle(self._handle)
            self._handle = None
        if hasattr(self, '_wfmo'):
            del self._wmfo
        self._overlapped = None
        self._result = None
        self._watching = False

    def _parse_read_directory_changes_result(self, location=0):
        fmt = FILE_NOTIFY_INFORMATION_STRUCT
        fmt_size = struct.calcsize(FILE_NOTIFY_INFORMATION_STRUCT)
        next_entry = 1
        pos = location
        while next_entry:
            next_entry, action, namelen = struct.unpack_from(fmt, self._result[pos:])
            str_pos = location + fmt_size
            str_len = namelen + str_pos
            name = self._result[str_pos:str_len].decode('utf-16')
            yield (ACTION_DICT[action], name)
            pos += next_entry

    def _get_results(self):
        for action, name in self._parse_read_directory_changes_result():
            import ipdb; ipdb.set_trace()
            print action, name.encode('utf-8')

    def _auto_fetch_events(self):
        self._wmfo = FSObjectWatcherWMFOPool()
        self._wmfo.register(self)

    def pool(self):
        if not self._watching:
            raise DirectoryWatcherError, "Not Watching"

        if not hasattr(self, '_wmfo'):
            self._auto_fetch_events()

        self._wmfo.pool()
        return [i for i in self._parse_read_directory_changes_result()]


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
        return obj
