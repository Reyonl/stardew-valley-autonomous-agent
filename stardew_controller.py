"""
Stardew Valley Autonomous Controller & Vision Module
DirectInput and Win32 automation for Stardew Valley 1.6 on Windows.
"""

import ctypes
from ctypes import wintypes
import os
import time
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
import pydirectinput

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()


class StardewController:
    def __init__(self, hwnd=None):
        self.hwnd = hwnd or self.find_stardew_hwnd()
        self.rect = None
        self.update_rect()

    def find_stardew_hwnd(self):
        """Finds Stardew Valley window handle on Default desktop."""
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
        user32.SetThreadDesktop(hdesk)

        stardew_hwnds = []

        def enum_cb(hwnd, lparam):
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, 512)
            if title.value == "Stardew Valley":
                stardew_hwnds.append(hwnd)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

        if stardew_hwnds:
            return stardew_hwnds[0]
        return None

    def update_rect(self):
        """Updates window bounding rectangle in physical screen coordinates."""
        if not self.hwnd:
            self.hwnd = self.find_stardew_hwnd()
        if self.hwnd:
            rect = wintypes.RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            self.rect = (rect.left, rect.top, rect.right, rect.bottom)
            self.width = rect.right - rect.left
            self.height = rect.bottom - rect.top
        else:
            self.rect = None
            self.width = 0
            self.height = 0

    def focus(self):
        """Restores and focuses the Stardew Valley game window."""
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
        user32.SetThreadDesktop(hdesk)
        if self.hwnd:
            user32.ShowWindow(self.hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(self.hwnd)
            time.sleep(0.1)

    def capture(self, filename=None):
        """Captures the current Stardew Valley window as a PIL Image."""
        self.update_rect()
        if not self.hwnd or not self.rect:
            return None

        w, h = self.width, self.height
        hdc_win = user32.GetDC(self.hwnd)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
        hbm = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
        gdi32.SelectObject(hdc_mem, hbm)

        # PW_RENDERFULLCONTENT = 2
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

        if filename:
            im.save(filename)
        return im

    def click_window(self, rel_x, rel_y, button='left'):
        """Clicks at coordinates relative to the Stardew Valley window."""
        self.focus()
        self.update_rect()
        px = self.rect[0] + rel_x
        py = self.rect[1] + rel_y
        user32.SetCursorPos(px, py)
        time.sleep(0.08)

        down_flag = 0x0002 if button == 'left' else 0x0008
        up_flag = 0x0004 if button == 'left' else 0x0010

        user32.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.12)
        user32.mouse_event(up_flag, 0, 0, 0, 0)
        time.sleep(0.1)

    def tap_key(self, key, hold_time=0.12):
        """Taps a keyboard key with suitable hold time for 60 FPS input polling."""
        self.focus()
        pydirectinput.keyDown(key)
        time.sleep(hold_time)
        pydirectinput.keyUp(key)
        time.sleep(0.05)

    def hold_key(self, key, duration):
        """Holds a keyboard key for movement."""
        self.focus()
        pydirectinput.keyDown(key)
        time.sleep(duration)
        pydirectinput.keyUp(key)
        time.sleep(0.05)

    def move(self, direction, duration=0.5):
        """Moves the character in a cardinal direction ('w', 'a', 's', 'd')."""
        self.hold_key(direction.lower(), duration)

    def select_slot(self, slot_num):
        """Selects inventory toolbar slot 1-10."""
        key = str(slot_num if slot_num != 10 else 0)
        self.tap_key(key, 0.1)

    def toggle_menu(self):
        """Opens or closes the player menu / inventory."""
        self.tap_key('e', 0.12)

    def interact(self):
        """Interacts with adjacent object / NPC / dialogue using 'x'."""
        self.tap_key('x', 0.15)

    def use_tool(self):
        """Uses currently selected tool using 'c'."""
        self.tap_key('c', 0.15)

    @staticmethod
    def read_save_summary():
        """Reads and parses the active save file XML state."""
        appdata = os.environ.get('APPDATA', '')
        saves_dir = os.path.join(appdata, 'StardewValley', 'Saves')
        if not os.path.isdir(saves_dir):
            return None

        # Find latest save folder
        folders = [os.path.join(saves_dir, d) for d in os.listdir(saves_dir) if os.path.isdir(os.path.join(saves_dir, d))]
        if not folders:
            return None
        save_folder = max(folders, key=os.path.getmtime)
        save_name = os.path.basename(save_folder)
        save_file = os.path.join(save_folder, save_name)

        if not os.path.isfile(save_file):
            return None

        tree = ET.parse(save_file)
        root = tree.getroot()

        player = root.find('player')
        return {
            'player_name': player.find('name').text if player.find('name') is not None else '',
            'farm_name': player.find('farmName').text if player.find('farmName') is not None else '',
            'day': int(root.find('dayOfMonth').text),
            'season': root.find('currentSeason').text,
            'year': int(root.find('year').text),
            'money': int(player.find('money').text) if player.find('money') is not None else 0,
            'stamina': float(player.find('stamina').text) if player.find('stamina') is not None else 0.0,
            'max_stamina': float(player.find('maxStamina').text) if player.find('maxStamina') is not None else 0.0,
            'weather_tomorrow': root.find('weatherForTomorrow').text if root.find('weatherForTomorrow') is not None else '',
        }
