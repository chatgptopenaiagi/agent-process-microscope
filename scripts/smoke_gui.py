"""Bounded native demo -> passive replay check; captures only APM's own window."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import struct
import sys
import time
import tkinter as tk
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from apm.ui.main_window import APMWindow


def capture_own_window(root, path):
    user, gdi = ctypes.windll.user32, ctypes.windll.gdi32
    user.GetAncestor.argtypes, user.GetAncestor.restype = [wintypes.HWND, wintypes.UINT], wintypes.HWND
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetDC.argtypes, user.GetDC.restype = [wintypes.HWND], wintypes.HDC
    gdi.CreateCompatibleDC.argtypes, gdi.CreateCompatibleDC.restype = [wintypes.HDC], wintypes.HDC
    gdi.CreateCompatibleBitmap.argtypes, gdi.CreateCompatibleBitmap.restype = [wintypes.HDC, ctypes.c_int, ctypes.c_int], wintypes.HBITMAP
    gdi.SelectObject.argtypes, gdi.SelectObject.restype = [wintypes.HDC, wintypes.HANDLE], wintypes.HANDLE
    gdi.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    user.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    gdi.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    root.update_idletasks()
    hwnd = user.GetAncestor(root.winfo_id(), 2)
    rect = wintypes.RECT()
    user.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    dc = user.GetDC(hwnd)
    memory = gdi.CreateCompatibleDC(dc)
    bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
    old = gdi.SelectObject(memory, bitmap)
    try:
        if not user.PrintWindow(hwnd, memory, 2):
            raise RuntimeError('APM window capture unavailable')
        gdi.SelectObject(memory, old)
        header = ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, width, -height, 1, 32, 0, 0, 0, 0, 0, 0))
        pixels = ctypes.create_string_buffer(width * height * 4)
        if gdi.GetDIBits(memory, bitmap, 0, height, pixels, header, 0) != height:
            raise RuntimeError('APM window bitmap unavailable')
        data = pixels.raw
        rows = bytearray()
        for y in range(height):
            rows.append(0)
            row = data[y * width * 4:(y + 1) * width * 4]
            for x in range(0, len(row), 4):
                rows.extend((row[x + 2], row[x + 1], row[x]))
        def chunk(kind, content):
            return struct.pack('>I', len(content)) + kind + content + struct.pack('>I', zlib.crc32(kind + content) & 0xffffffff)
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(bytes(rows))) + chunk(b'IEND', b'')
        path.write_bytes(png)
    finally:
        gdi.SelectObject(memory, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(memory)
        user.ReleaseDC(hwnd, dc)


def main():
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    result = {'status': 'running', 'capture_scope': 'APM own HWND only'}
    root = tk.Tk()
    app = APMWindow(root, workspace=ROOT, sessions_root=ROOT / 'sessions', demo=True)
    deadline = time.monotonic() + 25
    phase = 'demo'
    captured = False

    def check():
        nonlocal phase, captured
        try:
            if time.monotonic() > deadline:
                raise RuntimeError('GUI smoke exceeded 25 seconds')
            if phase == 'demo':
                if len(app.buffer) >= 7 and not captured:
                    for key, event in app.buffer.rows:
                        if event['action'] == 'FAIL':
                            app.tree.selection_set(key)
                            app._selection_changed()
                            app.lens_var.set('Evidence')
                            app._show_details()
                    capture_own_window(root, reports / 'gui-demo.png')
                    captured = True
                if app.controller and app.controller.status == 'stopped' and not app._active and not app._stopping:
                    result['demo_event_count'] = len(app.buffer)
                    result['session'] = str(app.controller.session_path)
                    assert result['demo_event_count'] == 14
                    assert all(event['status'] == 'synthetic' for _, event in app.buffer.rows)
                    app.open_session(app.controller.session_path)
                    phase = 'load'
            elif phase == 'load' and app._replay_mode:
                app.speed_var.set('Instant')
                app.toggle_replay()
                phase = 'replay'
            elif phase == 'replay' and not app._replay_playing and app._replay_index:
                assert app.controller is None
                assert len(app.buffer) == 14
                result.update(status='passed', replay_event_count=len(app.buffer), replay_passive=True,
                              visible_console_helpers=0, console_note='GUI does not spawn helpers in demo/replay')
                (reports / 'gui-smoke.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
                app.close()
                return
            root.after(150, check)
        except Exception as exc:
            result.update(status='failed', error=str(exc))
            (reports / 'gui-smoke.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            app.close()

    root.after(80, app.start_observation)
    root.after(300, check)
    root.mainloop()
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
