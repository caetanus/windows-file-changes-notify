# -*- coding: utf-8 -*-

from unittest import TestCase, skip
from winwatcher import (FindFirstChangeNotification,
                        FindNextChangeNotification,
                        FindCloseChangeNotification,
                        WaitForMultipleObjectsPool,
                        TimeoutError,
                        NOTIFY_CONSTANTS,
                        WAIT_OBJECT_0, WAIT_OBJECT_ABANDONED_0,
                        WAIT_TIMEOUT, WAIT_FAILED)
import tempfile
import threading
import shutil
import time
import os

class TestWFMOIntegrationTestCase(TestCase):

    def setUp(self):
        self.dir_mutex = threading.Lock()
        self.dir_mutex.acquire()
        self.directory = tempfile.mkdtemp(prefix="winwatcher_")
        self.dir_mutex.release()

    def tearDown(self):
        self.dir_mutex.acquire()
        shutil.rmtree(self.directory)
        self.dir_mutex.release()

    def test_wfmo_register_handle_should_add_handle_and_lphandles(self):
        wfmo = WaitForMultipleObjectsPool()
        handle = FindFirstChangeNotification(self.directory)
        wfmo.register_handle(handle)
        self.assertIn(handle, wfmo._handles)
        self.assertIn(handle, wfmo._lphandles[0][:])

    def test_wfmo_register_many_lphandles_should_pass(self):
        wfmo = WaitForMultipleObjectsPool()
        handles = range(1, 513)
        wfmo._handles = handles
        out = []
        wfmo._update_lphandles()
        for handle in wfmo._lphandles:
            out += handle[:]
        self.assertListEqual(out, handles)

    def test_wfmo_register_many_handles_update_lphandles_correcly(self):
        wfmo = WaitForMultipleObjectsPool()
        handles = range(1, 513)
        map(wfmo.register_handle, handles)
        out = []
        for handle in wfmo._lphandles:
            out += handle[:]
        self.assertListEqual(out, handles)

    def test_unregister_handle(self):
        handle = FindFirstChangeNotification(self.directory)
        wfmo = WaitForMultipleObjectsPool()
        wfmo.register_handle(handle)
        wfmo.unregister_handle(handle)
        self.assertNotIn(handle, wfmo._handles, 'handles')
        self.assertFalse(wfmo._lphandles)

    def test_add_directory_to_watch_should_not_raise(self):
        handle = FindFirstChangeNotification(self.directory)
        FindCloseChangeNotification(handle)

    def test__update_handles(self):
        wfmo = WaitForMultipleObjectsPool()
        wfmo._handles = [4, 3, 2, 9]
        wfmo._update_lphandles()
        self.assertEqual(wfmo._lphandles[0][:], wfmo._handles)

    def test__update_handles_splited(self):
        handles = range(256)
        wfmo = WaitForMultipleObjectsPool()
        wfmo._handles = handles
        wfmo._update_lphandles()
        out = reduce(lambda x, y: x + y, wfmo._lphandles)
        self.assertEqual(out, handles)

    def test_wfmo_should_return_handlers(self):
        def create_file_inside_directory(foo_file):
            self.dir_mutex.acquire()
            foo_file.write("fooo")
            os.fsync(foo_file)
            foo_file.close()
            self.dir_mutex.release()

        handle = FindFirstChangeNotification(self.directory)
        foo_file = open(self.directory + "\\foo.bar", "wb")
        create_file_inside_directory(foo_file)
        wfmo = WaitForMultipleObjectsPool()
        wfmo.register_handle(handle)
        self.assertEqual(handle,
                         wfmo.pool(1))

    def test_wfmo_should_raise_TimeoutError_when_a_handle_is_removed_and_no_handle_is_left(self):
        def create_file_inside_directory(foo_file):
            self.dir_mutex.acquire()
            foo_file.write("fooo")
            os.fsync(foo_file)
            foo_file.close()
            self.dir_mutex.release()

        foo_file = open(self.directory + "\\foo.bar", "wb")
        handle = FindFirstChangeNotification(self.directory)
        create_file_inside_directory(foo_file)

        wfmo = WaitForMultipleObjectsPool()
        wfmo.register_handle(handle)
        wfmo.unregister_handle(handle)
        self.assertRaises(TimeoutError,
                         wfmo.pool, (1))

    def test_wfmo_should_raise_TimeoutError_when_a_handle_is_removed_and_no_handle_is_left(self):
        handle = FindFirstChangeNotification(self.directory)
        wfmo = WaitForMultipleObjectsPool()
        wfmo.register_handle(handle)
        self.assertRaises(TimeoutError,
                         wfmo.pool, (0))


    def test_wfmo_should_raise_TimeoutError_when_a_handle_is_removed_and_there_is_other_handles(self):
        def create_file_inside_directory(directory):
            self.dir_mutex.acquire()
            foo_file.write("fooo")
            os.fsync(foo_file)
            foo_file.close()
            self.dir_mutex.release()

        foo_file = open(self.directory + "\\foo.bar", "wb")
        handle = FindFirstChangeNotification(self.directory)
        other_dir = tempfile.mkdtemp()
        handle2 = FindFirstChangeNotification(other_dir)
        create_file_inside_directory(foo_file)
        wfmo = WaitForMultipleObjectsPool()
        wfmo.register_handle(handle)
        wfmo.unregister_handle(handle)
        self.assertRaises(TimeoutError,
                         wfmo.pool, (0.5))
        shutil.rmtree(other_dir)

    def test_wfmo_with_more_than_31_objects_should_work_and_notify_everything(self):
        number = 32
        directories = map(lambda x: tempfile.mkdtemp(prefix='winwatcher'),
                          range(number))

        handles = map(lambda d: FindFirstChangeNotification(d,
                      NOTIFY_CONSTANTS['ChangeSize']), directories)

        def create_file_inside_directory(directory):
            foo_file = open(directory + "\\foo.bar", "w")
            foo_file.write("fooo")
            os.fsync(foo_file)
            foo_file.close()

        map(create_file_inside_directory, directories)
        wfmo = WaitForMultipleObjectsPool()
        map(wfmo.register_handle, handles)
        out = []
        for i in range(number):
            handle = wfmo.pool()
            out.append(handle)
            FindNextChangeNotification(handle)

        map(FindCloseChangeNotification, handles)
        out.sort()
        handles.sort()
        self.assertListEqual(out, handles)
        map(shutil.rmtree, directories)

    def test_wfmo_with_more_than_64_objects_should_work_and_notify_everything(self):
        number = 64
        directories = map(lambda x: tempfile.mkdtemp(prefix='winwatcher'),
                          range(number))

        handles = map(lambda d: FindFirstChangeNotification(d,
                      NOTIFY_CONSTANTS['ChangeSize']), directories)
        def create_file_inside_directory(directory):
            foo_file = open(directory + "\\foo.bar", "w")
            foo_file.write("fooo")
            os.fsync(foo_file)
            foo_file.close()

        map(create_file_inside_directory, directories)
        wfmo = WaitForMultipleObjectsPool()
        map(wfmo.register_handle, handles)
        pending = True
        out = []
        for i in range(number):
            handle = wfmo.pool()
            FindNextChangeNotification(handle)
            out.append(handle)

        map(FindCloseChangeNotification, handles)
        out.sort()
        handles.sort()
        self.assertListEqual(out, handles)
        map(shutil.rmtree, directories)

    def test_wfmo_with_more_than_128_objects_should_work_and_notify_everything(self):
        number = 128
        directories = map(lambda x: tempfile.mkdtemp(prefix='winwatcher'),
                          range(number))

        handles = map(lambda d: FindFirstChangeNotification(d,
                      NOTIFY_CONSTANTS['ChangeSize']), directories)
        def create_file_inside_directory(directory):
            foo_file = open(directory + "\\foo.bar", "w")
            foo_file.write("fooo")
            os.fsync(foo_file)
            foo_file.close()

        map(create_file_inside_directory, directories)
        wfmo = WaitForMultipleObjectsPool()
        map(wfmo.register_handle, handles)
        pending = True
        out = []
        for i in range(number):
            handle = wfmo.pool()
            FindNextChangeNotification(handle)
            out.append(handle)

        map(FindCloseChangeNotification, handles)
        out.sort()
        handles.sort()
        self.assertListEqual(out, handles)
        map(shutil.rmtree, directories)


    def test_wfmo_with_more_than_196_objects_should_work_and_notify_everything(self):
        number = 196
        directories = map(lambda x: tempfile.mkdtemp(prefix='winwatcher'),
                          range(number))

        handles = map(lambda d: FindFirstChangeNotification(d,
                      NOTIFY_CONSTANTS['ChangeSize']), directories)
        def create_file_inside_directory(directory):
            foo_file = open(directory + "\\foo.bar", "w")
            foo_file.write("fooo")
            os.fsync(foo_file)
            foo_file.close()

        map(create_file_inside_directory, directories)
        wfmo = WaitForMultipleObjectsPool()
        map(wfmo.register_handle, handles)
        pending = True
        out = []
        for i in range(number):
            handle = wfmo.pool()
            FindNextChangeNotification(handle)
            out.append(handle)

        map(FindCloseChangeNotification, handles)
        out.sort()
        handles.sort()
        self.assertListEqual(out, handles)
        map(shutil.rmtree, directories)


