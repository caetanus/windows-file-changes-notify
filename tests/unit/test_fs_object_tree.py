# -*- coding: utf-8 -*-

import winwatcher
from unittest import TestCase, skip
import mock

@skip
class _WinFSObjectTreeWatcherTestCase(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch("winwatcher.object_watcher.FindFirstChangeNotification")
    @mock.patch("winwatcher.win32_objects.os.path.exists")
    @mock.patch("winwatcher.win32_objects.os.stat")
    def test_event_handle_in_level_0_should_return_same_object(self, stat_mock, path_exists_mock, FindFirstNotification_mock):
        path_exists_mock.return_value = True
        FindFirstNotification_mock.side_effect = [3, 4, 6, 9, 3, 5, 6, 32, 44, 55]
        winfswatcher = winwatcher._WinFSObjectWatcher("c:\\foo\\bar")
        winfswatcher._watch_by_event_type("ChangeAttributes")
        obj = winfswatcher.find_child_by_handle(3)
        self.assertIs(obj, winfswatcher)


    @mock.patch("winwatcher.object_watcher.FindFirstChangeNotification")
    @mock.patch("winwatcher.win32_objects.os.path.exists")
    @mock.patch("winwatcher.win32_objects.os.stat")
    def test_add_child_with_same_object_family_should_pass(self, stat_mock, path_exists_mock, FindFirstNotification_mock):

        winfswatcher = winwatcher._WinFSObjectWatcher("c:\\foo\\bar")
        winfswatcher2 = winwatcher._WinFSObjectWatcher("c:\\foo\\bar\\2")
        winfswatcher.add_child(winfswatcher2)
        self.assertIs(winfswatcher, winfswatcher2._parent)
        self.assertIn(winfswatcher2, winfswatcher._children)
        self.assertFalse(winfswatcher2._children)

    @mock.patch("winwatcher.object_watcher.FindFirstChangeNotification")
    @mock.patch("winwatcher.win32_objects.os.path.exists")
    @mock.patch("winwatcher.win32_objects.os.stat")
    def test_event_handle_in_level_1_should_return_object(self, stat_mock, path_exists_mock, FindFirstNotification_mock):
        path_exists_mock.return_value = True
        FindFirstNotification_mock.side_effect = [3, 4, 6, 9, 3, 5, 6, 32, 44, 55]
        winfswatcher = winwatcher._WinFSObjectWatcher("c:\\foo\\bar")
        winfswatcher2 = winwatcher._WinFSObjectWatcher("c:\\foo\\bar\\2")
        winfswatcher.add_child(winfswatcher2)
        winfswatcher._watch_by_event_type("ChangeAttributes")
        winfswatcher2._watch_by_event_type("ChangeAttributes")
        obj = winfswatcher.find_child_by_handle(4)
        self.assertIs(obj, winfswatcher2)

    @mock.patch("winwatcher.FindFirstChangeNotification")
    @mock.patch("winwatcher.win32_objects.os.path.exists")
    @mock.patch("winwatcher.win32_objects.os.stat")
    def test_get_root_with_root_object_should_return_self(self, stat_mock, path_exists_mock, FindFirstNotification_mock):

        winfswatcher = winwatcher._WinFSObjectWatcher("c:\\foo\\bar")
        winfswatcher2 = winwatcher._WinFSObjectWatcher("c:\\foo\\bar\\2")
        winfswatcher.add_child(winfswatcher2)
        self.assertIs(winfswatcher.get_root_object(), winfswatcher)

    @mock.patch("winwatcher.FindFirstChangeNotification")
    @mock.patch("winwatcher.win32_objects.os.path.exists")
    @mock.patch("winwatcher.win32_objects.os.stat")
    def test_get_root_with_child_object_should_return_root(self, stat_mock, path_exists_mock, FindFirstNotification_mock):

        winfswatcher = winwatcher._WinFSObjectWatcher("c:\\foo\\bar")
        winfswatcher2 = winwatcher._WinFSObjectWatcher("c:\\foo\\bar\\2")
        winfswatcher.add_child(winfswatcher2)
        self.assertIs(winfswatcher2.get_root_object(), winfswatcher)


    @mock.patch("winwatcher.FindFirstChangeNotification")
    @mock.patch("winwatcher.win32_objects.os.path.exists")
    @mock.patch("winwatcher.win32_objects.os.stat")
    def test_add_invalid_object_should_raise_FSWAtcherError(self, stat_mock, path_exists_mock, FindFirstNotification_mock):

        winfswatcher = winwatcher._WinFSObjectWatcher("c:\\foo\\bar")
        winfswatcher2 = "oi"
        self.assertRaises(winwatcher.FSWatcherError, winfswatcher.add_child, winfswatcher2)

    @mock.patch("winwatcher.win32_objects.os.path.exists")
    def test_add_invalid_path_should_raise_FSWatcherError(self, os_path_exist_mock):
        os_path_exist_mock.return_value = False
        self.assertRaises(winwatcher.FSWatcherError,
                          winwatcher._WinFSObjectWatcher,
                          "c:\\foo\\bar")