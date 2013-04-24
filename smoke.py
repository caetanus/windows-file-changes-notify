# -*- coding: utf-8 -*-

from winwatcher.watcher import DirWatcher

import sys
import os


def do_watch(watcher):
    while 1:
        print watcher.observe()

def print_help():
    "usage %s path-to-a-directory. "

if len(sys.argv) != 2:
    print_help()

else:
    path = sys.argv[1]
    if os.path.isdir(path):
        watcher = DirWatcher(os.path.abspath(path.decode('utf-8')))
        watcher.start_watching()
        do_watch(watcher)
    else:
        print_help()

