import ctypes
import os
import struct
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32

DEBUG_ONLY_THIS_PROCESS = 0x00000002

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD), ('lpReserved', wintypes.LPSTR),
        ('lpDesktop', wintypes.LPSTR), ('lpTitle', wintypes.LPSTR),
        ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.c_void_p), ('hStdInput', wintypes.HANDLE),
        ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)
    ]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ('dwDebugEventCode', wintypes.DWORD),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD),
        ('u', wintypes.BYTE * 200)
    ]

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
client_dir = os.path.join(base_dir, "targets", "district-187", "client-rebirth")
exe = os.path.join(client_dir, "TheRaw.exe")
cmd = f'"{exe}" -arch game -windowtitle "District 187: Sin Streets" +gs_ip 127.0.0.1 +gs_port 12000 +windowed 1 +ScreenWidth 1920 +ScreenHeight 1080 +ShowLog 1'

si = STARTUPINFO()
si.cb = ctypes.sizeof(si)
pi = PROCESS_INFORMATION()

os.environ['__COMPAT_LAYER'] = 'RunAsInvoker'

ok = kernel32.CreateProcessA(None, cmd.encode(), None, None, False, DEBUG_ONLY_THIS_PROCESS, None, client_dir.encode(), ctypes.byref(si), ctypes.byref(pi))
if not ok:
    print('Failed CreateProcess:', kernel32.GetLastError())
    exit(1)

print('Started debugging PID:', pi.dwProcessId)

h_proc = pi.hProcess

while True:
    evt = DEBUG_EVENT()
    if not kernel32.WaitForDebugEvent(ctypes.byref(evt), 2000):
        print('Timeout')
        break
    code = evt.dwDebugEventCode
    continue_status = 0x00010002 # DBG_EXCEPTION_NOT_HANDLED
    
    if code == 1: # EXCEPTION_DEBUG_EVENT
        exc_code, exc_flags, exc_rec, exc_addr = struct.unpack_from('<IIQQ', evt.u, 0)
        dw_first_chance = struct.unpack_from('<I', evt.u, 152)[0]
        if exc_code == 0x80000003 or exc_code == 0x406D1388:
            continue_status = 0x00010001
        else:
            print(f'Exception: 0x{exc_code:08X} at 0x{exc_addr:016X} (FirstChance={dw_first_chance})')
            if exc_code == 0xC0000005 or exc_code == 0xE06D7363:
                print(f'Detailed Exception 0x{exc_code:08X}')
            continue_status = 0x00010001 # DBG_CONTINUE to let SEH handler handle it!
    elif code == 5: # EXIT_PROCESS
        exit_code = struct.unpack_from('<I', evt.u, 0)[0]
        print(f'Process exited with code {exit_code}')
        kernel32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, 0x00010001)
        break
    else:
        continue_status = 0x00010001

    kernel32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, continue_status)

kernel32.CloseHandle(pi.hThread)
kernel32.CloseHandle(pi.hProcess)
