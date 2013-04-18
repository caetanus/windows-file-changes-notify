# -*- coding: utf-8 -*-

from winwatcher import (FindFirstChangeNotification,
                        FindNextChangeNotification,
                        FindCloseChangeNotification,
                        WaitForMultipleObjectsPool,
                        TimeoutError,
                        NOTIFY_CONSTANTS,
                        WAIT_OBJECT_0, WAIT_OBJECT_ABANDONED_0,
                        WAIT_TIMEOUT, WAIT_FAILED)
from unittest import TestCase, skip
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

    def test_wmfo_register_handle_should_add_handle_and_lphandles(self):
        wmfo = WaitForMultipleObjectsPool()
        handle = FindFirstChangeNotification(self.directory)
        wmfo.register_handle(handle)
        self.assertIn(handle, wmfo._handles)
        self.assertIn(handle, wmfo._lphandles[0][1][:])

    def test_unregister_handle(self):

        handle = FindFirstChangeNotification(self.directory)
        wmfo = WaitForMultipleObjectsPool()
        wmfo.register_handle(handle)
        wmfo.unregister_handle(handle)
        self.assertNotIn(handle, wmfo._handles, 'handles')
        self.assertFalse(wmfo._lphandles)

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

    def test_wmfo_should_raise_TimeoutError_when_a_handle_is_removed_and_no_handle_is_left(self):
        def create_file_inside_directory(directory):
            time.sleep(0.01)
            with self.dir_mutex:
                open(directory + "\\foo.bar", "wb").close()

        handle = FindFirstChangeNotification(self.directory)
        thread = threading.Thread(target=create_file_inside_directory,
                                  args=(self.directory,))

        wmfo = WaitForMultipleObjectsPool()
        wmfo.register_handle(handle)
        wmfo.unregister_handle(handle)
        thread.start()
        self.assertRaises(TimeoutError,
                         wmfo.pool, (0.5))


    def test_wmfo_should_raise_TimeoutError_when_a_handle_is_removed_and_there_is_other_handles(self):
        def create_file_inside_directory(directory):
            time.sleep(0.01)
            with self.dir_mutex:
                open(directory + "\\foo.bar", "wb").close()

        handle = FindFirstChangeNotification(self.directory)
        other_dir = tempfile.mkdtemp()
        handle2 = FindFirstChangeNotification(other_dir)
        thread = threading.Thread(target=create_file_inside_directory,
                                  args=(self.directory,))

        wmfo = WaitForMultipleObjectsPool()
        wmfo.register_handle(handle)
        wmfo.unregister_handle(handle)
        thread.start()
        self.assertRaises(TimeoutError,
                         wmfo.pool, (0.5))
        shutil.rmtree(other_dir)

