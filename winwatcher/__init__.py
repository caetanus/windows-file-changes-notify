# -*- coding: utf-8 -*-

from ctypes import windll, c_wchar_p, c_long
import os

INVALID_HANDLE_VALUE = ~0
FILE_NOTIFY_CHANGE_FILE_NAME = 0x00000001
FILE_NOTIFY_CHANGE_DIR_NAME = 0x00000002
FILE_NOTIFY_CHANGE_ATTRIBUTES = 0x00000004
FILE_NOTIFY_CHANGE_SIZE = 0x00000008
FILE_NOTIFY_CHANGE_LAST_WRITE = 0x00000010
FILE_NOTIFY_CHANGE_SECURITY = 0x00000100

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


FindFirstChangeNotification = kernel32.FindFirstChangeNotificationW
FindFirstChangeNotification.argtypes = [c_wchar_p, bool, int]


FindNextChangeNotification = kernel32.FindNextChangeNotificationW
FindNextChangeNotification.argtypes = [int]

FindCloseChangeNotification = kernel32.FindCloseChangeNotificationW
FindCloseChangeNotification.argtypes = [int]

class DirectoryWatcherError(WindowsError):
    pass

class FSWatcherError(DirectoryWatcherError):
    pass

class FSFileWatcherError(DirectoryWatcherError):
    pass


def FindFirstChangeNotification(directory,
                                flags=FILE_NOTIFY_CHANGE_ALL_BUT_SECURITY):

    handle = FindFirstChangeNotificationW(directory, recursive, flags)
    if handle == INVALID_HANDLE_VALUE:
        raise DirectoryWatcherError
    return handle

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
            handle = FindFirstChangeNotification(path, recursive, notify_const]
            self._handles[handle] = notify_type
            self._event_type_handles[notify_type] = handle

       def on_change_size(self, p):
        self._event_type_handles['ChangeSize']

class FolderTracker(object):
    pass


class _WinFSObjectWatcher(object):
    def __init__(self, path):
        if not os.path.exists(path):
            raise FSWatcherError, "path doesn't exist"
        self._childs = []
        self.is_dir = os.path.isdir(path)
        self._stat = os.path.stat(path)
        self.path = path
        self._handles = {}
        self._event_type_handles = {}

    def _watch_by_event_type(self, event_type):
        handle = FindFirstChangeNotification(self.path,
                                             NOTIFY_CONSTANTS[event_type])
        self._handles[handle] = event_type
        self._event_type_handles[event_type] = handle

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
        else



class _WinFileObjectWatcher(_WinFSObjectWatcher):
    def __init__(self, path):
        super(_WinFileObjectWatcher, self).__init__(path)
        if self.is_dir:
            raise FSFileWatcherError, "the path %s looks like a directory." % path

    def start_watching(self):
        super(_WinFSObjectWatcher, self).start_watching()
        map(self._watch_by_event_type, ["ChangeFileName", "ChangeSize", "LastWrite"])


