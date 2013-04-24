windows-file-changes-notify
===========================

notify file and directories changes on windows using ctypes

view smoke.py to view the library working

------------
$ smoke.py c:\test-path



# *File Structure*

*  win32\_defs :
> contains ctypes definitions of win32api 

* win32\_objects
> contains a little more highlevel for win32api and WFMO pooler

* object\_watcher
> contains the real watcher of filesystem, but a little low level, because it don't says if the event occurred on a file or directory

* watcher
> contains a little more highlevel api, an example of use is in smoke.py
