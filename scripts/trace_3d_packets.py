"""
trace_3d_packets.py — Surgical Win32 Debug API tracer for TheRaw.exe 3D world entry.

Attaches to a running TheRaw.exe (or launches it) and logs:
  - Every UDP packet ID processed in CClientShell::ProcessPacket (0x0047E1AB / 0x0047E1C0)
    whenever a handler returns non-zero (LT_ERROR) or on key packets (6, 7, 8, 10, 13, 15, 24).
  - Failures in CStateReceiptMgr::HandleAdd (0x00480688, eax==0 -> NULL object),
    HandleRemove (0x0048007A), and HandleChange (0x00480113).
  - CClientMgr::ProcessError (0x00414820) with error code and return address.

Usage:
  python scripts/trace_3d_packets.py           # attach to running TheRaw.exe
  python scripts/trace_3d_packets.py --launch  # launch TheRaw.exe under debugger
"""
import ctypes
from ctypes import wintypes
import os
import sys
import struct
import time

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

DEBUG_PROCESS = 0x00000001
DEBUG_ONLY_THIS_PROCESS = 0x00000002
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5

EXCEPTION_BREAKPOINT = 0x80000003
EXCEPTION_SINGLE_STEP = 0x80000004
STATUS_WX86_BREAKPOINT = 0x4000001F
STATUS_WX86_SINGLE_STEP = 0x4000001E
BP_CODES = (EXCEPTION_BREAKPOINT, STATUS_WX86_BREAKPOINT)
SS_CODES = (EXCEPTION_SINGLE_STEP, STATUS_WX86_SINGLE_STEP)

CONTEXT_FULL = 0x00010007
THREAD_ALL_ACCESS = 0x001F03FF
PROCESS_ALL_ACCESS = 0x001F0FFF

# 32-bit WOW64/x86 CONTEXT structure
class FLOATING_SAVE_AREA(ctypes.Structure):
    _fields_ = [
        ("ControlWord", wintypes.DWORD),
        ("StatusWord", wintypes.DWORD),
        ("TagWord", wintypes.DWORD),
        ("ErrorOffset", wintypes.DWORD),
        ("ErrorSelector", wintypes.DWORD),
        ("DataOffset", wintypes.DWORD),
        ("DataSelector", wintypes.DWORD),
        ("RegisterArea", ctypes.c_ubyte * 80),
        ("Cr0NpxState", wintypes.DWORD),
    ]

class WOW64_CONTEXT(ctypes.Structure):
    _fields_ = [
        ("ContextFlags", wintypes.DWORD),
        ("Dr0", wintypes.DWORD), ("Dr1", wintypes.DWORD), ("Dr2", wintypes.DWORD),
        ("Dr3", wintypes.DWORD), ("Dr6", wintypes.DWORD), ("Dr7", wintypes.DWORD),
        ("FloatSave", FLOATING_SAVE_AREA),
        ("SegGs", wintypes.DWORD), ("SegFs", wintypes.DWORD),
        ("SegEs", wintypes.DWORD), ("SegDs", wintypes.DWORD),
        ("Edi", wintypes.DWORD), ("Esi", wintypes.DWORD), ("Ebx", wintypes.DWORD),
        ("Edx", wintypes.DWORD), ("Ecx", wintypes.DWORD), ("Eax", wintypes.DWORD),
        ("Ebp", wintypes.DWORD), ("Eip", wintypes.DWORD), ("SegCs", wintypes.DWORD),
        ("EFlags", wintypes.DWORD), ("Esp", wintypes.DWORD), ("SegSs", wintypes.DWORD),
        ("ExtendedRegisters", ctypes.c_ubyte * 512),
    ]

class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [
        ("ExceptionCode", wintypes.DWORD),
        ("ExceptionFlags", wintypes.DWORD),
        ("ExceptionRecord", ctypes.c_void_p),
        ("ExceptionAddress", ctypes.c_void_p),
        ("NumberParameters", wintypes.DWORD),
        ("ExceptionInformation", ctypes.c_size_t * 15),
    ]

class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("ExceptionRecord", EXCEPTION_RECORD),
        ("dwFirstChance", wintypes.DWORD),
    ]

class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("Exception", EXCEPTION_DEBUG_INFO),
        ("Raw", ctypes.c_ubyte * 160),
    ]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", wintypes.DWORD),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
        ("u", DEBUG_EVENT_UNION),
    ]

# Breakpoints in TheRaw.exe (ImageBase = 0x00400000)
BPS = {
    0x0047E1AB: "ProcessPacket_Enter",     # AL = pkt_id
    0x0047E1C0: "ProcessPacket_Ret",       # EAX = result (0=LT_OK, !=0=LT_ERROR)
    0x0047EC0B: "After_AddObjectToWorld",  # EAX = LTRESULT (0=LT_OK), [EBP+0xC] = objId, [EBP-0xD90] = OCS
    0x00480688: "HandleAdd_AfterCreate",   # EAX = pObject (NULL -> fail), [EBP+0x10] = stateHandle
    0x0048007A: "HandleRemove_Fail",       # xor al, al
    0x00480113: "HandleChange_Fail",       # xor al, al
    0x0047EB74: "Fail_ReadNewObjectInfo",  # ReadNewObjectInfo == false
    0x0047EC61: "Fail_AddObjectToWorld",   # Error adding object #%d to world
    0x0047ECEC: "Fail_HandleChangeObjPkt", # HandleChangeObjectPacket() == false
    0x004408D0: "Fail_OpenModelFile",      # Unable to open up model file '%s' (EBX = fname)
    0x00440942: "Fail_ParseModelFile",     # Error loading model %s (EBX = fname)
    0x00414820: "CClientMgr_ProcessError", # [ESP+4] = errCode, [ESP] = RET
}

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT_DIR, "targets", "district-187", "traffic", "trace_3d_packets.log")

def find_theraw_pid():
    import subprocess
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process -Name TheRaw -ErrorAction SilentlyContinue | Select-Object -First 1).Id"],
        text=True
    ).strip()
    return int(out) if out.isdigit() else None

def read_mem(hProc, addr, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    if kernel32.ReadProcessMemory(hProc, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
        return buf.raw[:read.value]
    return b""

def write_mem(hProc, addr, data):
    written = ctypes.c_size_t(0)
    old = wintypes.DWORD(0)
    kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(addr), len(data), 0x40, ctypes.byref(old))
    ok = kernel32.WriteProcessMemory(hProc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(written))
    kernel32.FlushInstructionCache(hProc, ctypes.c_void_p(addr), len(data))
    return bool(ok)

def get_ctx(hThread):
    ctx = WOW64_CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL
    if not kernel32.Wow64GetThreadContext(hThread, ctypes.byref(ctx)):
        return None
    return ctx

def set_ctx(hThread, ctx):
    return bool(kernel32.Wow64SetThreadContext(hThread, ctypes.byref(ctx)))

def main():
    watch = "--watch" in sys.argv
    if watch:
        print("[*] --watch mode: waiting for a newly launched TheRaw.exe...", flush=True)
        pid = None
        while not pid:
            pid = find_theraw_pid()
            if not pid:
                time.sleep(0.5)
        print(f"[*] Found TheRaw.exe PID={pid}, waiting 12s for DXVK/Scaleform boot to settle...", flush=True)
        time.sleep(12.0)
    else:
        pid = find_theraw_pid()
        if not pid:
            print("[-] TheRaw.exe not running. Start the game first.")
            return 1

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logf = open(LOG_PATH, "w", encoding="utf-8", buffering=1)
    def log(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n")

    log(f"[*] Attaching to TheRaw.exe (PID={pid})...")
    if not kernel32.DebugActiveProcess(pid):
        log(f"[-] DebugActiveProcess failed: GetLastError={ctypes.get_last_error()}")
        return 1
    kernel32.DebugSetProcessKillOnExit(False)

    hProc = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    orig_bytes = {}
    for addr, name in BPS.items():
        b = read_mem(hProc, addr, 1)
        if b:
            orig_bytes[addr] = b
            write_mem(hProc, addr, b"\xCC")
            log(f"[+] Armed BP 0x{addr:08X} ({name}), orig=0x{b[0]:02X}")

    pending_rearm = {}  # tid -> addr
    last_pkt_id = {}    # tid -> pkt_id
    pkt_counts = {}

    ev = DEBUG_EVENT()
    try:
        while True:
            if not kernel32.WaitForDebugEvent(ctypes.byref(ev), 500):
                continue
            code = ev.dwDebugEventCode
            tid = ev.dwThreadId
            cont = DBG_CONTINUE

            if code == EXIT_PROCESS_DEBUG_EVENT:
                log("[*] TheRaw.exe exited.")
                kernel32.ContinueDebugEvent(ev.dwProcessId, tid, cont)
                break

            elif code == EXCEPTION_DEBUG_EVENT:
                exc = ev.u.Exception.ExceptionRecord
                ecode = exc.ExceptionCode
                eaddr = int(exc.ExceptionAddress or 0)

                if ecode in BP_CODES and eaddr in orig_bytes:
                    hThread = kernel32.OpenThread(THREAD_ALL_ACCESS, False, tid)
                    ctx = get_ctx(hThread)
                    if ctx:
                        # Rewind EIP to the INT3 instruction
                        ctx.Eip = eaddr
                        name = BPS[eaddr]

                        if name == "ProcessPacket_Enter":
                            pkt_id = ctx.Eax & 0xFF
                            last_pkt_id[tid] = pkt_id
                            pkt_counts[pkt_id] = pkt_counts.get(pkt_id, 0) + 1
                            if pkt_id in (6, 7, 8, 10, 15, 24) and pkt_counts[pkt_id] <= 5:
                                log(f"[UDP] pkt_id={pkt_id} (count={pkt_counts[pkt_id]})")
                        elif name == "ProcessPacket_Ret":
                            ret = ctx.Eax
                            pid_cur = last_pkt_id.get(tid, -1)
                            if ret != 0:
                                log(f"[FAIL] ProcessPacket(pkt_id={pid_cur}) returned 0x{ret:08X} (LT_ERROR)!")
                        elif name == "After_AddObjectToWorld":
                            if ctx.Eax != 0:
                                raw_oid = read_mem(hProc, ctx.Ebp + 0xC, 2)
                                oid = struct.unpack("<H", raw_oid)[0] if len(raw_oid) == 2 else -1
                                ocs = read_mem(hProc, ctx.Ebp - 0xD90, 0x300)
                                obj_type = struct.unpack_from("<H", ocs, 0)[0] if len(ocs) >= 2 else -1
                                import re
                                strs = [m.decode("ascii", "ignore") for m in re.findall(rb"[ -~]{4,80}", ocs)]
                                log(f"[FAIL] AddObjectToWorld(objId={oid}, type={obj_type}) -> LTRESULT=0x{ctx.Eax:08X} ({ctx.Eax}) strings={strs[:8]}")
                        elif name == "HandleAdd_AfterCreate":
                            if ctx.Eax == 0:
                                raw_oid = read_mem(hProc, ctx.Ebp + 0x10, 4)
                                oid = struct.unpack("<I", raw_oid)[0] if len(raw_oid) == 4 else -1
                                log(f"[FAIL] CStateReceiptMgr::HandleAdd -> CreateObject(0x414C05) returned NULL! objId={oid}")
                        elif name in ("Fail_OpenModelFile", "Fail_ParseModelFile"):
                            fname = read_mem(hProc, ctx.Ebx, 128).split(b"\x00")[0].decode("ascii", "ignore")
                            log(f"[FAIL] {name}: '{fname}'")
                        elif name in ("HandleRemove_Fail", "HandleChange_Fail",
                                      "Fail_ReadNewObjectInfo", "Fail_AddObjectToWorld",
                                      "Fail_HandleChangeObjPkt"):
                            log(f"[FAIL] {name} hit! EAX=0x{ctx.Eax:08X} EBX=0x{ctx.Ebx:08X} EDI=0x{ctx.Edi:08X} ESI=0x{ctx.Esi:08X}")
                        elif name == "CClientMgr_ProcessError":
                            stk = read_mem(hProc, ctx.Esp, 16)
                            if len(stk) == 16:
                                ret_addr, err_code, a2, a3 = struct.unpack("<IIII", stk)
                                log(f"[ERROR] CClientMgr::ProcessError(err=0x{err_code:08X}) RET=0x{ret_addr:08X} last_pkt={last_pkt_id.get(tid, -1)}")

                        # Restore original byte, enable TF for single-step, and re-arm on next event
                        write_mem(hProc, eaddr, orig_bytes[eaddr])
                        ctx.EFlags |= 0x100
                        set_ctx(hThread, ctx)
                        pending_rearm[tid] = eaddr
                    kernel32.CloseHandle(hThread)

                elif ecode in SS_CODES and tid in pending_rearm:
                    addr = pending_rearm.pop(tid)
                    write_mem(hProc, addr, b"\xCC")
                elif ecode not in BP_CODES:
                    cont = DBG_EXCEPTION_NOT_HANDLED

            kernel32.ContinueDebugEvent(ev.dwProcessId, tid, cont)
    except KeyboardInterrupt:
        log("[*] Detaching...")
    finally:
        for addr, b in orig_bytes.items():
            write_mem(hProc, addr, b)
        kernel32.CloseHandle(hProc)
        kernel32.DebugActiveProcessStop(pid)
        logf.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
