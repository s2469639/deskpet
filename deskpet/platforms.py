"""Windows integration. No network, audio, or telemetry."""
import os
import subprocess
import sys


def no_activate(widget):
    if sys.platform != "win32":
        return
    import ctypes
    user32 = ctypes.windll.user32
    get_style = user32.GetWindowLongW
    set_style = user32.SetWindowLongW
    get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
    get_style.restype = ctypes.c_long
    set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
    hwnd = int(widget.winId())
    # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW, preserving Qt's layered window style.
    set_style(hwnd, -20, get_style(hwnd, -20) | 0x08000000 | 0x00000080)


def foreground_fullscreen(own_hwnd):
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    hwnd = user32.GetForegroundWindow()
    if not hwnd or hwnd == own_hwnd or user32.IsIconic(hwnd):
        return False
    name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW(hwnd, name, 256)
    if name.value in ("Progman", "WorkerW", "Shell_TrayWnd"):
        return False
    rect = wintypes.RECT()
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(info)
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
    if not user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
        return False
    monitor = info.rcMonitor
    return (rect.left <= monitor.left and rect.top <= monitor.top
            and rect.right >= monitor.right and rect.bottom >= monitor.bottom)


def set_autostart(enabled):
    if sys.platform != "win32":
        if enabled:
            raise OSError("시작 시 실행은 Windows에서 사용할 수 있습니다.")
        return
    import winreg
    if getattr(sys, "frozen", False):
        command = subprocess.list2cmdline([sys.executable])
    else:
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        launcher = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run_pet.py"))
        command = subprocess.list2cmdline([pythonw, launcher])
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                          r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            winreg.SetValueEx(key, "GlassesMandu", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "GlassesMandu")
            except FileNotFoundError:
                pass
