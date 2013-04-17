# -*- coding: utf-8 -*-

from winwatcher import (FindFirstChangeNotification,
                        FindNextChangeNotification,
                        FindCloseChangeNotification,
                        WaitForMultipleObjectsPool,
                        NOTIFY_CONSTANTS,
                        WAIT_OBJECT_0, WAIT_OBJECT_ABANDONED_0,
                        WAIT_TIMEOUT, WAIT_FAILED)
from unittest import TestCase
import tempfile
import threading
import shutil
import time

class TestWFMOIntegrationTestCase(TestCase):

    def setUp(self):
        self.dir_mutex = threading.Lock()
        with self.dir_mutex:
            self.directory = tempfile.mkdtemp(prefix="winwatcher_")

    def tearDown(self):
        with self.dir_mutex:
            shutil.rmtree(self.directory)

    def test_add_directory_to_watch_should_not_raise(self):
        handle = FindFirstChangeNotification(self.directory)
        FindCloseChangeNotification(handle)

    def test__update_handles(self):
        wmfo = WaitForMultipleObjectsPool()
        wmfo._handles = [4, 3, 2, 9]
        wmfo._update_lphandles()
        self.assertEqual(wmfo._lphandles[0][1][:], wmfo._handles)

    def test_wmfo_should_return_handlers(self):
        def create_file_inside_directory(directory):
            time.sleep(0.01)
            with self.dir_mutex:
                open(directory + "\\foo.bar", "wb").close()

        handle = FindFirstChangeNotification(self.directory)
        thread = threading.Thread(target=create_file_inside_directory,
                                  args=(self.directory,))
        thread.start()
        wmfo = WaitForMultipleObjectsPool()
        wmfo.register_handle(handle)
        self.assertEqual(handle,
                         wmfo.pool(1))