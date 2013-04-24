# -*- coding: utf-8 -*-
import mock
import os
from unittest import TestCase
from winwatcher import WinDirectoryWatcher, FSObjectWatcherWMFOPool, TimeoutError

import ctypes
from ctypes import byref, sizeof, create_string_buffer
from ctypes import wintypes
import tempfile
import shutil
import random

class Test_WinDirectoryObjectWatcherTestCase(TestCase):

    def setUp(self):
        self.directory = tempfile.mkdtemp().decode('utf-8')

    def tearDown(self):
        shutil.rmtree(self.directory.encode('utf-8'))

    def test_watch_should_return_the_object_added_to_dir(self):
        watcher = WinDirectoryWatcher(self.directory)
        watcher.start_watching()
        with open(self.directory + "\\foo.bar", "w") as foo:
            foo.write("oi")

        result = watcher.pool()
        self.assertEquals(result, ('Added', u'foo.bar'))
        watcher.stop_watching()

    def test_watch_should_return_the_object_modified_on_dir(self):
        watcher = WinDirectoryWatcher(self.directory)
        foo =  open(self.directory + "\\foo.bar", "w")
        watcher.start_watching()
        foo.write("caetano")
        foo.close()

        result = watcher.pool()
        self.assertEquals(result, ('Modified', u'foo.bar'))
        watcher.stop_watching()

    def test_watch_should_return_the_object_deleted_on_dir(self):
        filename = "\\foo.bar"
        watcher = WinDirectoryWatcher(self.directory)
        foo =  open(self.directory + filename, "w")
        foo.write("caetano")
        foo.close()

        watcher.start_watching()

        os.remove(self.directory + filename)

        result = watcher.pool()
        self.assertEquals(result, ('Removed', u'foo.bar'))
        watcher.stop_watching()


    def test_watch_should_return_the_object_moved_on_dir_to_the_same_dir(self):
        filename = "\\foo.bar"
        watcher = WinDirectoryWatcher(self.directory)
        foo =  open(self.directory + filename, "w")
        foo.write("caetano")
        foo.close()

        watcher.start_watching()

        shutil.move(self.directory + filename, self.directory + filename + 'new')

        result = watcher.pool()
        self.assertEquals(result, ('Moved', u'foo.bar', u'foo.barnew'))
        watcher.stop_watching()


    def test_watch_should_return_the_object_moved_from_outside_to_the_dir_as_added(self):
        filename = "\\foo.bar"
        watcher = WinDirectoryWatcher(self.directory)
        fd, name = tempfile.mkstemp()
        os.write(fd, "caetano")
        os.close(fd)

        watcher.start_watching()

        shutil.move(name, self.directory + filename)

        result = watcher.pool()
        self.assertEquals(result, ('Added', u'foo.bar'))
        watcher.stop_watching()

    def test_file_watcher_should_never_notify_the_same_event_twice(self):
        filename = "\\foo.bar"
        complete_file_name = self.directory + filename
        new_complete_file_name = tempfile.gettempdir() + filename
        watcher = WinDirectoryWatcher(self.directory)
        foo = open(self.directory + filename,"w")
        foo.write("caetano")
        foo.close()
        watcher.start_watching()
        shutil.move(complete_file_name, new_complete_file_name)

        result = watcher.pool()
        self.assertEquals(result, ('Removed', u'foo.bar'))
        self.assertRaises(TimeoutError, watcher.pool, (0))
        watcher.stop_watching()

        os.remove(new_complete_file_name)

    def test_file_watcher_do_4096_file_alteration_with_events(self):

        filename = "\\foo.bar"
        complete_file_name = self.directory + filename
        new_complete_file_name = tempfile.gettempdir() + filename
        watcher = WinDirectoryWatcher(self.directory)
        open(self.directory + filename,"w").close()
        def append_data_to_file(data):
            foo = open(self.directory + filename, 'a+')
            foo.write(data)
            foo.close()

        watcher.start_watching()

        out = []

        for i in range(4096):
            try:
                append_data_to_file('hello ')
                out.append(watcher.pool(0.5))

            except TimeoutError:
                break

        watcher.stop_watching()

        self.assertEqual(len(out), 4096)


    def test_file_watcher_do_256_random_delete_rename_and_create_file_events(self):
        """
        we're not checking modified event because windows can dispatch this events
        more than once, and randomly.
        """

        changes_journal = []
        filenames = []
        watcher = WinDirectoryWatcher(self.directory)
        watcher.start_watching()

        def create_random_file():
            fd, complete_fname = tempfile.mkstemp(dir=self.directory)
            fname = os.path.basename(complete_fname)
            changes_journal.append(("Added", fname))
            filenames.append(fname)
            os.close(fd)

        def append_data_to_file(data='\x00'):
            if not filenames:
                create_random_file()
            fname = random.choice(filenames)
            foo = open(os.path.join(self.directory, fname), 'a+')
            foo.write(data)
            os.fsync(foo)
            foo.close()

        def remove_random_file():
            if not filenames:
                create_random_file()
            fname = random.choice(filenames)
            os.remove(os.path.join(self.directory, fname))
            filenames.remove(fname)
            changes_journal.append(('Removed', fname))

        def mv_random_file():
            if not filenames:
                create_random_file()
            complete_fname_new = tempfile.mktemp(dir=self.directory)
            fname_new = os.path.basename(complete_fname_new)
            fname_old = random.choice(filenames)
            filenames.remove(fname_old)
            filenames.append(fname_new)
            shutil.move(os.path.join(self.directory, fname_old),
                        complete_fname_new)

            changes_journal.append(('Moved', fname_old, fname_new))

        out = []

        operations = [mv_random_file, remove_random_file, append_data_to_file,
                      create_random_file]

        for i in range(256):
            random.choice(operations)()
            out.append(watcher.pool())

        while 1:
            try:
                out.append(watcher.pool(0))
            except TimeoutError:
                break

        out = [i for i in out if not 'Modified' in i]
        out_not_in_changes = [i for i in out if i not in changes_journal]
        changes_not_in_out = [i for i in changes_journal if i not in out]

        self.assertListEqual(out, changes_journal)
        watcher.stop_watching()



