"""
Stardew Valley Controller Core
Handles OS desktop switching, window management, DPI-aware mouse & DirectInput keystrokes.
"""

import ctypes
from ctypes import wintypes
import os
import time
import xml.etree.ElementTree as ET
from PIL import Image
import pydirectinput

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()


class GameController:
    def __init__(self, hwnd=None):
        self.hwnd = hwnd or self.find_game_window()
        self.rect = None
        self.update_geometry()

    def find_game_window(self):
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
        user32.SetThreadDesktop(hdesk)

        hwnds = []
        def enum_cb(h, lparam):
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(h, title, 512)
            if title.value == "Stardew Valley":
                hwnds.append(h)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return hwnds[0] if hwnds else None

    def update_geometry(self):
        if not self.hwnd:
            self.hwnd = self.find_game_window()
        if self.hwnd:
            r = wintypes.RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(r))
            self.rect = (r.left, r.top, r.right, r.bottom)
            self.width = r.right - r.left
            self.height = r.bottom - r.top
        else:
            self.rect = None
            self.width = 0
            self.height = 0

    def focus(self):
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
        user32.SetThreadDesktop(hdesk)
        if self.hwnd:
            user32.ShowWindow(self.hwnd, 9)
            user32.SetForegroundWindow(self.hwnd)
            time.sleep(0.08)

    def capture(self, save_path=None):
        self.update_geometry()
        if not self.hwnd or not self.rect:
            return None

        w, h = self.width, self.height
        hdc_win = user32.GetDC(self.hwnd)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
        hbm = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
        gdi32.SelectObject(hdc_mem, hbm)

        user32.PrintWindow(self.hwnd, hdc_mem, 2)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', ctypes.c_uint32),
                ('biWidth', ctypes.c_int32),
                ('biHeight', ctypes.c_int32),
                ('biPlanes', ctypes.c_uint16),
                ('biBitCount', ctypes.c_uint16),
                ('biCompression', ctypes.c_uint32),
                ('biSizeImage', ctypes.c_uint32),
                ('biXPelsPerMeter', ctypes.c_int32),
                ('biYPelsPerMeter', ctypes.c_int32),
                ('biClrUsed', ctypes.c_uint32),
                ('biClrImportant', ctypes.c_uint32),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bmi), 0)

        im = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')

        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(self.hwnd, hdc_win)

        if save_path:
            im.save(save_path)
        return im

    def click(self, rel_x, rel_y, button='left'):
        self.focus()
        self.update_geometry()
        px = self.rect[0] + rel_x
        py = self.rect[1] + rel_y
        user32.SetCursorPos(px, py)
        time.sleep(0.08)

        down_flag = 0x0002 if button == 'left' else 0x0008
        up_flag = 0x0004 if button == 'left' else 0x0010

        user32.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.12)
        user32.mouse_event(up_flag, 0, 0, 0, 0)
        time.sleep(0.08)

    def tap(self, key, hold_time=0.12):
        self.focus()
        pydirectinput.keyDown(key)
        time.sleep(hold_time)
        pydirectinput.keyUp(key)
        time.sleep(0.05)

    def move(self, direction, duration=0.5):
        self.focus()
        pydirectinput.keyDown(direction.lower())
        time.sleep(duration)
        pydirectinput.keyUp(direction.lower())
        time.sleep(0.05)

    def select_slot(self, slot_num):
        key = str(slot_num if slot_num != 10 else 0)
        self.tap(key, 0.1)

    def pause_or_menu(self):
        self.tap('e', 0.12)

    def interact(self):
        self.tap('x', 0.15)

    def use_tool(self):
        self.tap('c', 0.15)
