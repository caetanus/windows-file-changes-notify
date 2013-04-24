# -*- coding: utf-8 -*-

import os

from .object_watcher import WinDirectoryWatcher, DirectoryWatcherError


class DirWatcherError(DirectoryWatcherError):
   pass

def get_directory_tree(path):
   if type(path) is not unicode:
      raise TypeError, "path should be unicode."

   if not os.path.exists(path):
      raise OSError, "path doesn't exists."

   if not os.path.isdir(path):
      raise OSError, "path is not a directory."
   fs_tree = set()

   for root, dirs, files in os.walk(path):
      relative_root = root[len(path):]

      while relative_root.endswith(os.path.sep):
         relative_root = relative_root[:-1]
      while relative_root.startswith(os.path.sep):
         relative_root = relative_root[1:]

      for d in dirs:
         fs_tree.add(os.path.join(relative_root, d))

   return fs_tree


class DirWatcher(WinDirectoryWatcher):
   """
   Do almost the same things that WinDirectoryWatcher does,
   but the events are more especifics:
   Moved will be DirectoryMoved or FileMoved and etc.

   this happens by maintaning an internal tree in memory,
   it could be a little slow to start watching in a bigger directory tree
   """

   def __init__(self, path, recursive=True):
      super(DirWatcher, self).__init__(path, recursive)
      self._evt_processor = {
               'Added': self._added_event,
               'Removed': self._removed_event,
               'Modified': self._modified_event,
               'Moved': self._moved_event
         }

   def start_watching(self):
      self._fs_tree = get_directory_tree(self.path)
      return WinDirectoryWatcher.start_watching(self)

   def observe(self, timeout=-1):
      obj = self.pool(timeout)

      if len(obj) == 2:
         evt, obj = obj
         return self._evt_processor[evt](obj)

      else:
         evt, oldobj, newobj = obj
         return self._evt_processor[evt](oldobj, newobj)

   def __is_dir(self, obj):
      return os.path.isdir(os.path.join(self.path, obj))

   def _added_event(self, obj):
      isdir = self.__is_dir(obj)
      if isdir:
         self._fs_tree.add(obj)
      evt = 'DirectoryAdded' if isdir else 'FileAdded'
      return (evt, obj)

   def _moved_event(self, old_obj, new_obj):
      isdir = self.__is_dir(old_obj)
      if isdir:
         self._fs_tree.remove(old_obj)
         self._fs_tree.add(new_obj)
      evt = 'DirectoryMoved' if isdir else 'FileMoved'
      return (evt, old_obj, new_obj)

   def _removed_event(self, obj):
      if obj in self._fs_tree:
         isdir = True
         self._fs_tree.remove(obj)
      else:
         isdir = False
      evt = 'DirectoryRemoved' if isdir else 'FileRemoved'

      return (evt, obj)

   def _modified_event(self, obj):
      isdir = self.__is_dir(obj)
      evt = 'DirectoryModified' if isdir else 'FileModified'
      return (evt, obj)





