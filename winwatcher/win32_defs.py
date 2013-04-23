# -*- coding:utf-8 -*-

from ctypes import (windll, c_wchar_p, c_long, c_int, c_uint, c_void_p,
                    c_int32,  Structure, wstring_at, c_wchar, c_wchar_p,
                    POINTER)
from ctypes.wintypes import (DWORD, HANDLE, BOOL, LPWSTR, LPVOID, GetLastError,
                             FormatError, WCHAR, LPCWSTR)
from ctypes import byref

#kernel endpoint
kernel32 = windll.kernel32

#constants
INVALID_HANDLE_VALUE = ~0
FILE_NOTIFY_CHANGE_FILE_NAME = 0x00000001
FILE_NOTIFY_CHANGE_DIR_NAME = 0x00000002
FILE_NOTIFY_CHANGE_ATTRIBUTES = 0x00000004
FILE_NOTIFY_CHANGE_SIZE = 0x00000008
FILE_NOTIFY_CHANGE_LAST_WRITE = 0x00000010
FILE_NOTIFY_CHANGE_SECURITY = 0x00000100


MAX_OBJECTS = 0x40
WAIT_OBJECT_0 = 0x00000000
WAIT_OBJECT_ABANDONED_0 = 0x00000080
WAIT_TIMEOUT = 0x00000102L
WAIT_FAILED = ~0 # -1
WAIT_INFINITE = ~0 # -1

THREAD_ACCESS_DELETE = 0x00010000L
THREAD_ACCESS_READ_CONTROL = 0x00020000L
THREAD_ACCESS_SYNCHRONIZE = 0x00100000L
THREAD_ACCESS_DAC = 0x00040000L
THREAD_ACCESS_WRITE_OWNER = 0x00080000L


FILE_ACTION_ADDED = 0x1
FILE_ACTION_REMOVED = 0x2
FILE_ACTION_MODIFIED = 0x3
FILE_ACTION_RENAMED_OLD_NAME = 0x4
FILE_ACTION_RENAMED_NEW_NAME = 0x5

FILE_LIST_DIRECTORY = 0x01
FILE_SHARE_READ = 0x01
FILE_SHARE_WRITE = 0x02
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_OVERLAPPED = 0x40000000


FILE_NOTIFY_CHANGE_ALL_BUT_SECURITY = (FILE_NOTIFY_CHANGE_FILE_NAME |
                                       FILE_NOTIFY_CHANGE_ATTRIBUTES |
                                       FILE_NOTIFY_CHANGE_DIR_NAME |
                                       FILE_NOTIFY_CHANGE_LAST_WRITE |
                                       FILE_NOTIFY_CHANGE_SIZE)


FILE_NOTIFY_CHANGE_ALL = (FILE_NOTIFY_CHANGE_ALL_BUT_SECURITY |
                          FILE_NOTIFY_CHANGE_SECURITY)

#structs

class OVERLAPPED(Structure):
    _fields_ = [('Internal', LPVOID),
                ('InternalHigh', LPVOID),
                ('Offset', DWORD),
                ('OffsetHigh', DWORD),
                ('Pointer', LPVOID),
                ('hEvent', HANDLE),
               ]
LPOVERLAPPED = POINTER(OVERLAPPED)

class FILE_NOTIFY_INFORMATION(Structure):
    _fields_ = [
                ('NextEntryOffset', DWORD),
                ('Action', DWORD),
                ('FileNameLength', DWORD),
                ('FileName', c_wchar*256)
               ]

class SECURITY_ATTRIBUTES(Structure):
    _fields_ = [
                ('nLength', DWORD),
                ('lpSecurityDescriptor', LPVOID),
                ('bInheritHandle', BOOL)
               ]
LPSECURITY_ATTRIBUTES = POINTER(SECURITY_ATTRIBUTES)


#function definitions

OpenThread = kernel32.OpenThread

OpenThread.argtypes = (DWORD, BOOL, DWORD)
#--- dwDesiredAccess, bInheritHandle, dwThreadId



_FindFirstChangeNotification = kernel32.FindFirstChangeNotificationW
_FindFirstChangeNotification.argtypes = [LPWSTR, BOOL, DWORD]
def FindFirstChangeNotification(directory,
                                flags=FILE_NOTIFY_CHANGE_ALL_BUT_SECURITY,
                                recursive=False):
    handle = _FindFirstChangeNotification(directory, recursive, flags)

    if handle == INVALID_HANDLE_VALUE:
        raise WindowsError("Cannot watch with an invalid path."
                           "%s" % FormatError(GetLastError))
    return handle


FindNextChangeNotification = kernel32.FindNextChangeNotification
FindNextChangeNotification.argtypes = [HANDLE]

FindCloseChangeNotification = kernel32.FindCloseChangeNotification
FindCloseChangeNotification.argtypes = [HANDLE]

_WaitForMultipleObjects = kernel32.WaitForMultipleObjects
_WaitForMultipleObjects.argtypes = [DWORD, c_void_p, BOOL, DWORD]

ReadDirectoryChangesW = kernel32.ReadDirectoryChangesW

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [HANDLE]
CloseHandle.restype = BOOL

_CreateEvent = kernel32.CreateEventW

_CreateEvent.argtypes = [LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCWSTR]
# (LPSECURITY_ATTRIBUTES lpEventAttributes, BOOL bManualReset,
#  BOOL bInitialState, LPCWSTR lpName)

_CreateEvent.restype = HANDLE

SetEvent = kernel32.SetEvent
SetEvent.argtypes = [HANDLE] # Event Handle
SetEvent.restype = BOOL

ResetEvent = kernel32.ResetEvent
ResetEvent.argtypes = [HANDLE]
ResetEvent.restype = BOOL


try:
    ReadDirectoryChangesW = kernel32.ReadDirectoryChangesW
except AttributeError:
    raise ImportError("ReadDirectoryChanges is not available")
ReadDirectoryChangesW.restype = BOOL
ReadDirectoryChangesW.argtypes = (
    HANDLE, # hDirectory
    LPVOID, # lpBuffer
    DWORD, # nBufferLength
    BOOL, # bWatchSubtree
    DWORD, # dwNotifyFilter
    POINTER(DWORD), # lpBytesReturned
    LPOVERLAPPED,# lpOverlapped
    LPVOID #FileIOCompletionRoutine # lpCompletionRoutine
)


CreateFileW = kernel32.CreateFileW
CreateFileW.restype = HANDLE
CreateFileW.argtypes = (
    LPCWSTR, # lpFileName
    DWORD, # dwDesiredAccess
    DWORD, # dwShareMode
    LPVOID, # lpSecurityAttributes
    DWORD, # dwCreationDisposition
    DWORD, # dwFlagsAndAttributes
    HANDLE # hTemplateFile
)
CloseHandle = kernel32.CloseHandle
CloseHandle.restype = BOOL
CloseHandle.argtypes = (
    HANDLE, # hObject
)

GetOverlappedResult = kernel32.GetOverlappedResult
GetOverlappedResult.argtypes = (HANDLE, LPOVERLAPPED, POINTER(DWORD),
                                BOOL)
