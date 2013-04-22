# -*- coding: utf-8 -*-
import mock
import os
from unittest import TestCase
from winwatcher import WinDirectoryWatcher, FSObjectWatcherWMFOPool

import ctypes
from ctypes import byref, sizeof, create_string_buffer
from ctypes import wintypes
import tempfile
import shutil

class Test_WinFSObjectWatcherTestCase(TestCase):

    def setUp(self):
        self.directory = tempfile.mkdtemp().decode('utf-8')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_watch_should_return_the_object_added_to_dir(self):
        watcher = WinDirectoryWatcher(self.directory)
        watcher.start_watching()
        with open(self.directory + "\\foo.bar", "w") as foo:
            foo.write("oi")

        result = watcher.pool().pop()
        self.assertEquals(result, ('Added', u'foo.bar'))
        watcher.stop_watching()

    def test_watch_should_return_the_object_modified_on_dir(self):
        watcher = WinDirectoryWatcher(self.directory)
        foo =  open(self.directory + "\\foo.bar", "w")
        watcher.start_watching()
        foo.write("caetano")
        foo.close()

        result = watcher.pool().pop()
        self.assertEquals(result, ('Modified', u'foo.bar'))
        watcher.stop_watching()
