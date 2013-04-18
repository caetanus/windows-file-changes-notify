# -*- coding: utf-8 -*-

from . import (NOTIFY_CONSTANTS, FindNextChangeNotification,
               FindCloseChangeNotification, FindFirstChangeNotification)




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


