# -*- coding: utf-8 -*-
import mock
import os
from unittest import TestCase
from winwatcher import _WinFSObjectWatcher, FSObjectWatcherWMFOPool
from winwatcher.win32_objects import (LPFILE_NOTIFY_INFORMATION, DWORD,
                                      FILE_NOTIFY_INFORMATION,
                                      ReadDirectoryChangesW, OVERLAPPED,
                                      FILE_NOTIFY_CHANGE_ALL_BUT_SECURITY)
import ctypes
from ctypes import byref, sizeof, create_string_buffer
import tempfile
import shutil
def get_next_event(handle):
    overlapped = OVERLAPPED()
    overlapped.Internal = 0
    overlapped.InternalHigh = 0
    overlapped.Offset = 0
    overlapped.OffsetHigh = 0
    overlapped.Pointer = 0
    overlapped.hEvent = 0

    lpresult = create_string_buffer(1024)
    bytes = len(lpresult)
    data = ReadDirectoryChangesW(handle, byref(lpresult), bytes,
                                 0, FILE_NOTIFY_CHANGE_ALL_BUT_SECURITY,
                                 None, overlapped, None)
    import ipdb; ipdb.set_trace()

class Test_WinFSObjectWatcherTestCase(TestCase):

    def setUp(self):
        self.directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_watch_should_return_the_object(self):
        watcher = _WinFSObjectWatcher(self.directory)
        watcher._watch_by_event_type("ChangeSize")
        watcher._watch_by_event_type("LastWrite")
        with open(self.directory + "\\foo.bar", "w") as foo:
            foo.write("oi")

        pooler = FSObjectWatcherWMFOPool()
        pooler.register(watcher)
        obj, evt = pooler.pool()
        handle = obj._event_type_handles[evt]
        get_next_event(handle)