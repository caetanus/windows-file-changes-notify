# -*- coding: utf-8 -*-

from . import (NOTIFY_CONSTANTS, FindNextChangeNotification,
               FindCloseChangeNotification, FindFirstChangeNotification,
               DirectoryWatcherError, WaitForMultipleObjectsPool)
import os



class FSWatcherError(DirectoryWatcherError):
    pass

class FSFileWatcherError(DirectoryWatcherError):
    pass

class InvalidWatchType(FSFileWatcherError):
    pass

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

def get_stat(path):
    return os.stat(path)

class _WinFSObjectWatcher(object):
    def __init__(self, path):
        if not os.path.exists(path):
            raise FSWatcherError, "path doesn't exist"
        self._children = []
        self._parent = None
        self.is_dir = os.path.isdir(path)
        self._stat = get_stat(path)
        self.path = path
        self._handles = {}
        self._event_type_handles = {}

    def _get_event_type_by_handle(self, handle):
        return self._handles[handle]

    def _watch_by_event_type(self, event_type):
        try:
            notify_flag = NOTIFY_CONSTANTS[event_type]
        except KeyError:
            raise InvalidWatchType, "invalid event type"
        handle = FindFirstChangeNotification(self.path, notify_flag)
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


class FSObjectWatcherWMFOPool(WaitForMultipleObjectsPool):

    def __init__(self):
        self._handle_fs_object_watcher = {}
        self._fs_object_watcher_handle = {}
        WaitForMultipleObjectsPool.__init__(self)

    def register(self, object_watcher):
        handles = object_watcher._handles.keys()
        self._fs_object_watcher_handle[object_watcher] = handles
        for  handle in handles:
            WaitForMultipleObjectsPool.register_handle(self, handle)
            self._handle_fs_object_watcher[handle] = object_watcher

    def unregister(self, object_watcher):
        for handle in self._fs_object_watcher_handle[object_watcher]:
            WaitForMultipleObjectsPool.unregister_handle(self, handle)
            del self._handle_fs_object_watcher[handle]

    def pool(self, timeout=-1):
        ret_val = WaitForMultipleObjectsPool.pool(self, timeout)
        obj = self._handle_fs_object_watcher[ret_val]
        return (obj, obj._get_event_type_by_handle(ret_val))