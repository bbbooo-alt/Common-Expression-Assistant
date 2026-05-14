#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快捷键输入工具 - 现代化 UI 版本
使用 tkinter 实现类似截图的界面效果
"""

import json
import os
import sys
import threading
import time
from tkinter import *
from tkinter import messagebox, ttk

# 检查操作系统
if sys.platform != 'win32':
    messagebox.showerror("错误", "本工具仅支持 Windows 系统")
    sys.exit(1)

import ctypes
from ctypes import wintypes

# ==================== Windows API 常量定义 ====================
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

VK_MAP = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
    'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
    'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
    's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
    'y': 0x59, 'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74,
    'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79,
    'f11': 0x7A, 'f12': 0x7B,
    'space': 0x20, 'tab': 0x09, 'enter': 0x0D, 'esc': 0x1B,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    'insert': 0x2D, 'delete': 0x2E, 'home': 0x24, 'end': 0x23,
    'pageup': 0x21, 'pagedown': 0x22,
}

# ==================== Windows API 函数 ====================
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

RegisterHotKey = user32.RegisterHotKey
RegisterHotKey.argtypes = [wintypes.HWND, wintypes.INT, wintypes.UINT, wintypes.UINT]

UnregisterHotKey = user32.UnregisterHotKey
UnregisterHotKey.argtypes = [wintypes.HWND, wintypes.INT]

GetMessage = user32.GetMessageW
TranslateMessage = user32.TranslateMessage
DispatchMessage = user32.DispatchMessageW

CreateWindowEx = user32.CreateWindowExW
CreateWindowEx.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
CreateWindowEx.restype = wintypes.HWND

DefWindowProc = user32.DefWindowProcW
DefWindowProc.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
DefWindowProc.restype = ctypes.c_longlong

DestroyWindow = user32.DestroyWindow

SendInput = user32.SendInput
SendInput.argtypes = [wintypes.UINT, ctypes.c_void_p, wintypes.INT]
SendInput.restype = wintypes.UINT


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


# ==================== 主程序类 ====================
class HotkeyTyper:
    def __init__(self):
        self.config_file = "hotkey_config.json"
        self.hotkeys = {}
        self.is_running = False
        self.hwnd = None
        self.hotkey_id_map = {}
        self.next_id = 1
        self.listener_thread = None
        self.root = None
        self.today_usage = 0
        self.load_config()

    def load_config(self):
        """加载配置 - 支持新数据结构：快捷键、名称、内容"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        name_counter = 1
                        for key, value in data.items():
                            if isinstance(value, dict):
                                # 新格式或已转换的格式
                                if "content" not in value:
                                    # 旧格式：text 字段变成 content，添加默认名称
                                    value["content"] = value.pop("text", "")
                                if "name" not in value:
                                    value["name"] = f"未命名{name_counter}"
                                    name_counter += 1
                                self.hotkeys[key] = value
                            else:
                                # 旧格式字符串
                                self.hotkeys[key] = {
                                    "name": f"未命名{name_counter}",
                                    "content": value,
                                    "enabled": True
                                }
                                name_counter += 1
            except Exception as e:
                print(f"加载配置失败: {e}")
                self.hotkeys = {}

    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.hotkeys, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def parse_hotkey(self, hotkey_str):
        """解析快捷键字符串"""
        parts = hotkey_str.lower().split('+')
        parts = [p.strip() for p in parts]

        modifiers = 0
        key_part = None

        for part in parts:
            if part == 'ctrl' or part == 'control':
                modifiers |= MOD_CONTROL
            elif part == 'alt':
                modifiers |= MOD_ALT
            elif part == 'shift':
                modifiers |= MOD_SHIFT
            elif part == 'win':
                modifiers |= MOD_WIN
            else:
                key_part = part

        if key_part is None:
            return None

        vk = VK_MAP.get(key_part)
        if vk is None:
            return None

        return (modifiers, vk)

    def type_text(self, text):
        """模拟键盘输入"""
        modifier_keys = [0xA0, 0xA1, 0xA2, 0xA3, 0x5B, 0x5C]
        for vk in modifier_keys:
            user32.keybd_event(vk, 0, 0x0002, 0)
        time.sleep(0.05)

        class KEYBDINPUT(ctypes.Structure):
            _pack_ = 8
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_ulonglong),
            ]

        class MOUSEINPUT(ctypes.Structure):
            _pack_ = 8
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_ulonglong),
            ]

        class HARDWAREINPUT(ctypes.Structure):
            _pack_ = 8
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD),
            ]

        class INPUT_I(ctypes.Union):
            _pack_ = 8
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT),
            ]

        class INPUT(ctypes.Structure):
            _pack_ = 8
            _fields_ = [("type", wintypes.DWORD), ("_input", INPUT_I)]
            _anonymous_ = ("_input",)

        INPUT_KEYBOARD = 1
        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002

        inputs = []
        for char in text:
            char_code = ord(char)

            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.ki.wVk = 0
            inp_down.ki.wScan = char_code
            inp_down.ki.dwFlags = KEYEVENTF_UNICODE
            inp_down.ki.time = 0
            inp_down.ki.dwExtraInfo = 0
            inputs.append(inp_down)

            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.ki.wVk = 0
            inp_up.ki.wScan = char_code
            inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            inp_up.ki.time = 0
            inp_up.ki.dwExtraInfo = 0
            inputs.append(inp_up)

        nInputs = len(inputs)
        LPINPUT = INPUT * nInputs
        pInputs = LPINPUT(*inputs)
        cbSize = ctypes.sizeof(INPUT)

        result = SendInput(nInputs, ctypes.cast(pInputs, ctypes.c_void_p), cbSize)

        if result > 0:
            self.today_usage += 1
            self.update_stats()

    def on_hotkey_triggered(self, hotkey_id):
        """快捷键被触发 - 使用 content 字段"""
        for hotkey_str, hid in self.hotkey_id_map.items():
            if hid == hotkey_id:
                data = self.hotkeys.get(hotkey_str, {})
                if isinstance(data, dict) and data.get("enabled", True):
                    # 优先使用 content 字段，兼容旧数据使用 text 字段
                    content = data.get("content", "")
                    if not content:
                        content = data.get("text", "")  # 兼容旧数据
                    if content:
                        threading.Thread(target=lambda t=content: self.type_text(t), daemon=True).start()
                break

    def create_message_window(self):
        """创建消息窗口"""
        WC_WNDCLASS = "HotkeyTyperWindow"

        try:
            user32.UnregisterClassW(WC_WNDCLASS, None)
        except:
            pass

        @ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        def wnd_proc(hwnd, msg, wParam, lParam):
            if msg == WM_HOTKEY:
                self.on_hotkey_triggered(wParam)
                return 0
            result = DefWindowProc(hwnd, msg, wParam, lParam)
            return ctypes.c_longlong(result).value

        self.wnd_proc_callback = wnd_proc

        WNDCLASSEXW = type('WNDCLASSEXW', (ctypes.Structure,), {
            '_fields_': [
                ("cbSize", wintypes.UINT),
                ("style", wintypes.UINT),
                ("lpfnWndProc", ctypes.c_void_p),
                ("cbClsExtra", wintypes.INT),
                ("cbWndExtra", wintypes.INT),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HANDLE),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HANDLE),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HANDLE),
            ]
        })

        hinst = kernel32.GetModuleHandleW(None)

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = ctypes.cast(wnd_proc, ctypes.c_void_p).value
        wc.hInstance = hinst
        wc.lpszClassName = WC_WNDCLASS

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if atom == 0:
            return None

        hwnd = CreateWindowEx(
            0, WC_WNDCLASS, "HotkeyTyper", 0,
            0, 0, 0, 0, None, None, hinst, None
        )

        return hwnd if hwnd != 0 else None

    def register_all_hotkeys(self):
        """注册所有启用的快捷键"""
        self.hotkey_id_map = {}
        self.next_id = 1

        for hotkey_str, data in self.hotkeys.items():
            if isinstance(data, dict) and not data.get("enabled", True):
                continue

            parsed = self.parse_hotkey(hotkey_str)
            if parsed is None:
                continue

            modifiers, vk = parsed
            hotkey_id = self.next_id
            self.next_id += 1

            result = RegisterHotKey(self.hwnd, hotkey_id, modifiers, vk)
            if result:
                self.hotkey_id_map[hotkey_str] = hotkey_id

    def unregister_all_hotkeys(self):
        """注销所有热键"""
        for hotkey_id in self.hotkey_id_map.values():
            UnregisterHotKey(self.hwnd, hotkey_id)
        self.hotkey_id_map = {}

    def message_loop(self):
        """消息循环"""
        msg = MSG()
        while self.is_running:
            ret = GetMessage(ctypes.byref(msg), self.hwnd, 0, 0)
            if ret == 0 or ret == -1:
                break
            TranslateMessage(ctypes.byref(msg))
            DispatchMessage(ctypes.byref(msg))

    def start_listener(self):
        """启动监听"""
        if self.is_running or not self.hotkeys:
            return

        self.is_running = True
        self.hwnd = self.create_message_window()
        if not self.hwnd:
            self.is_running = False
            return

        self.register_all_hotkeys()
        self.listener_thread = threading.Thread(target=self.message_loop, daemon=True)
        self.listener_thread.start()

    def stop_listener(self):
        """停止监听"""
        if not self.is_running:
            return

        self.is_running = False
        self.unregister_all_hotkeys()
        if self.hwnd:
            DestroyWindow(self.hwnd)
            self.hwnd = None
        self.listener_thread = None

    # ==================== 现代化 UI ====================

    def create_gui(self):
        """创建现代化界面"""
        self.root = Tk()
        self.root.title("快捷键输入工具")
        self.root.geometry("900x650")
        self.root.configure(bg="#f5f7fa")

        # 主容器
        main_container = Frame(self.root, bg="#f5f7fa")
        main_container.pack(fill=BOTH, expand=True)

        # ===== 左侧导航栏 =====
        nav_frame = Frame(main_container, bg="#ffffff", width=180)
        nav_frame.pack(side=LEFT, fill=Y)
        nav_frame.pack_propagate(False)

        # Logo 区域
        logo_frame = Frame(nav_frame, bg="#ffffff", height=80)
        logo_frame.pack(fill=X, pady=20)
        logo_frame.pack_propagate(False)

        # 闪电图标
        logo_canvas = Canvas(logo_frame, bg="#ffffff", width=40, height=40, highlightthickness=0)
        logo_canvas.place(x=20, y=10)
        logo_canvas.create_oval(2, 2, 38, 38, fill="#3b82f6", outline="")
        logo_canvas.create_text(20, 20, text="⚡", font=("微软雅黑", 18), fill="white")

        Label(logo_frame, text="快捷键输入工具", font=("微软雅黑", 12, "bold"), 
              bg="#ffffff", fg="#1f2937").place(x=70, y=12)
        Label(logo_frame, text="让输入更高效", font=("微软雅黑", 9), 
              bg="#ffffff", fg="#6b7280").place(x=70, y=35)

        # 导航菜单 - 只保留快捷键管理
        nav_items = [
            ("🏠", "快捷键管理", True),
        ]

        self.nav_buttons = []
        for icon, text, active in nav_items:
            btn = self.create_nav_button(nav_frame, icon, text, active)
            btn.pack(fill=X, padx=10, pady=2)
            self.nav_buttons.append(btn)

        # 监听状态（底部）
        status_frame = Frame(nav_frame, bg="#ffffff")
        status_frame.pack(side=BOTTOM, fill=X, padx=15, pady=20)

        Label(status_frame, text="监听状态", font=("微软雅黑", 10), 
              bg="#ffffff", fg="#6b7280").pack(anchor=W)

        self.listener_switch_var = BooleanVar(value=False)
        self.listener_switch = self.create_toggle_switch(status_frame, self.listener_switch_var, self.toggle_listener_from_switch)
        self.listener_switch.pack(anchor=W, pady=5)

        self.listener_status_label = Label(status_frame, text="已停止", font=("微软雅黑", 9), 
                                           bg="#ffffff", fg="#ef4444")
        self.listener_status_label.pack(anchor=W)

        # 版本号
        Label(nav_frame, text="v1.0.0", font=("微软雅黑", 8), 
              bg="#ffffff", fg="#9ca3af").pack(side=BOTTOM, pady=10)

        # ===== 右侧内容区 =====
        content_frame = Frame(main_container, bg="#f5f7fa")
        content_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=20, pady=20)

        # 顶部统计卡片 - 保存引用以便更新
        self.stats_frame = Frame(content_frame, bg="#f5f7fa")
        self.stats_frame.pack(fill=X, pady=(0, 20))

        # 快捷键总数
        total_card = self.create_stat_card(self.stats_frame, "🎯", "快捷键总数", str(len(self.hotkeys)), "#3b82f6")
        total_card.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        # 启用数量
        enabled_count = sum(1 for data in self.hotkeys.values() if isinstance(data, dict) and data.get("enabled", True))
        enabled_card = self.create_stat_card(self.stats_frame, "✅", "启用数量", str(enabled_count), "#10b981")
        enabled_card.pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        # 今日使用
        usage_card = self.create_stat_card(self.stats_frame, "📈", "今日使用", str(self.today_usage), "#f59e0b")
        usage_card.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0))

        # 添加按钮
        add_btn = Button(self.stats_frame, text="+ 添加快捷键", font=("微软雅黑", 10),
                         bg="#3b82f6", fg="white", relief=FLAT, bd=0,
                         padx=20, pady=10, cursor="hand2",
                         command=self.show_add_dialog)
        add_btn.pack(side=RIGHT, padx=(20, 0))

        # 搜索和筛选
        filter_frame = Frame(content_frame, bg="#f5f7fa")
        filter_frame.pack(fill=X, pady=(0, 15))

        # 搜索框
        search_frame = Frame(filter_frame, bg="white", highlightbackground="#e5e7eb", 
                             highlightthickness=1)
        search_frame.pack(side=LEFT)

        Label(search_frame, text="🔍", font=("微软雅黑", 10), bg="white", fg="#9ca3af").pack(side=LEFT, padx=10)
        self.search_entry = Entry(search_frame, font=("微软雅黑", 10), bg="white", fg="#374151",
                                  relief=FLAT, width=30)
        self.search_entry.pack(side=LEFT, padx=5, pady=8)
        self.search_entry.insert(0, "搜索快捷键或常用语...")
        self.search_entry.bind("<FocusIn>", lambda e: self.on_search_focus_in())
        self.search_entry.bind("<FocusOut>", lambda e: self.on_search_focus_out())
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_list())

        # 仅显示启用
        show_enabled_frame = Frame(filter_frame, bg="#f5f7fa")
        show_enabled_frame.pack(side=RIGHT)

        Label(show_enabled_frame, text="仅显示启用", font=("微软雅黑", 9),
              bg="#f5f7fa", fg="#6b7280").pack(side=LEFT, padx=5)

        self.show_enabled_var = BooleanVar(value=False)
        show_enabled_switch = self.create_toggle_switch(show_enabled_frame, self.show_enabled_var, self.filter_list)
        show_enabled_switch.pack(side=LEFT)

        # 列表表头
        header_frame = Frame(content_frame, bg="#f9fafb")
        header_frame.pack(fill=X, pady=(0, 5))

        headers = [("快捷键", 100), ("名称", 200), ("状态", 80), ("操作", 200)]
        for text, width in headers:
            lbl = Label(header_frame, text=text, font=("微软雅黑", 10, "bold"),
                        bg="#f9fafb", fg="#6b7280", width=10)
            lbl.pack(side=LEFT, padx=15, pady=10)
            Frame(header_frame, width=width).pack(side=LEFT)

        # 列表区域
        list_container = Frame(content_frame, bg="white", highlightbackground="#e5e7eb", 
                               highlightthickness=1)
        list_container.pack(fill=BOTH, expand=True)

        # 创建画布用于滚动
        self.list_canvas = Canvas(list_container, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient=VERTICAL, command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=RIGHT, fill=Y)
        self.list_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # 列表内容框架
        self.list_inner_frame = Frame(self.list_canvas, bg="white")
        self.list_canvas_window = self.list_canvas.create_window((0, 0), window=self.list_inner_frame, anchor=NW, width=860)

        self.list_inner_frame.bind("<Configure>", lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>", lambda e: self.list_canvas.itemconfig(self.list_canvas_window, width=e.width))

        # 底部提示
        footer_frame = Frame(content_frame, bg="#f5f7fa")
        footer_frame.pack(fill=X, pady=(15, 0))

        Label(footer_frame, text="💡 提示: 按下设置的快捷键即可快速输入对应内容到当前焦点处",
              font=("微软雅黑", 9), bg="#f5f7fa", fg="#6b7280").pack(side=LEFT)

        # 刷新列表
        self.refresh_list()

        # 窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.root.mainloop()

    def create_nav_button(self, parent, icon, text, active):
        """创建导航按钮"""
        bg_color = "#eff6ff" if active else "#ffffff"
        fg_color = "#3b82f6" if active else "#6b7280"

        btn = Frame(parent, bg=bg_color, height=40, cursor="hand2")
        btn.pack_propagate(False)

        Label(btn, text=icon, font=("微软雅黑", 12), bg=bg_color).pack(side=LEFT, padx=15)
        Label(btn, text=text, font=("微软雅黑", 10), bg=bg_color, fg=fg_color).pack(side=LEFT)

        if active:
            Frame(btn, bg="#3b82f6", width=3).pack(side=RIGHT, fill=Y)

        return btn

    def create_stat_card(self, parent, icon, title, value, color):
        """创建统计卡片"""
        card = Frame(parent, bg="white", highlightbackground="#e5e7eb", highlightthickness=1)
        card.pack_propagate(False)
        card.configure(height=80)

        inner = Frame(card, bg="white")
        inner.pack(fill=BOTH, expand=True, padx=15, pady=12)

        # 图标背景 - 使用浅色版本
        bg_colors = {
            "#3b82f6": "#dbeafe",  # 蓝色
            "#10b981": "#d1fae5",  # 绿色
            "#f59e0b": "#fef3c7",  # 橙色
        }
        icon_bg_color = bg_colors.get(color, "#f3f4f6")

        icon_bg = Frame(inner, bg=icon_bg_color, width=40, height=40)
        icon_bg.pack(side=LEFT)
        icon_bg.pack_propagate(False)

        Label(icon_bg, text=icon, font=("微软雅黑", 16), bg=icon_bg_color).place(relx=0.5, rely=0.5, anchor=CENTER)

        # 文字
        text_frame = Frame(inner, bg="white")
        text_frame.pack(side=LEFT, padx=12)

        Label(text_frame, text=title, font=("微软雅黑", 9), bg="white", fg="#6b7280").pack(anchor=W)
        Label(text_frame, text=value, font=("微软雅黑", 20, "bold"), bg="white", fg="#1f2937").pack(anchor=W)

        return card

    def create_toggle_switch(self, parent, var, command):
        """创建切换开关"""
        switch_frame = Frame(parent, bg="#e5e7eb", width=44, height=24, cursor="hand2")
        switch_frame.pack_propagate(False)

        circle = Canvas(switch_frame, bg="#e5e7eb", highlightthickness=0, width=44, height=24)
        circle.pack()

        def toggle(event=None):
            var.set(not var.get())
            update_appearance()
            if command:
                command()

        def update_appearance():
            if var.get():
                circle.delete("all")
                circle.create_oval(2, 2, 22, 22, fill="#3b82f6", outline="")
                circle.create_oval(20, 2, 42, 22, fill="#3b82f6", outline="")
                circle.create_oval(22, 2, 42, 22, fill="white", outline="")
            else:
                circle.delete("all")
                circle.create_oval(2, 2, 22, 22, fill="#e5e7eb", outline="")
                circle.create_oval(20, 2, 42, 22, fill="#e5e7eb", outline="")
                circle.create_oval(2, 2, 22, 22, fill="white", outline="")

        switch_frame.bind("<Button-1>", toggle)
        circle.bind("<Button-1>", toggle)

        update_appearance()
        return switch_frame

    def on_search_focus_in(self):
        """搜索框获得焦点"""
        if self.search_entry.get() == "搜索快捷键或常用语...":
            self.search_entry.delete(0, END)
            self.search_entry.config(fg="#374151")

    def on_search_focus_out(self):
        """搜索框失去焦点"""
        if not self.search_entry.get():
            self.search_entry.insert(0, "搜索快捷键或常用语...")
            self.search_entry.config(fg="#9ca3af")

    def toggle_listener_from_switch(self):
        """从开关切换监听状态"""
        if self.listener_switch_var.get():
            self.start_listener()
        else:
            self.stop_listener()
        self.update_listener_ui()

    def update_listener_ui(self):
        """更新监听状态UI"""
        if self.is_running:
            self.listener_switch_var.set(True)
            self.listener_status_label.config(text="运行中", fg="#10b981")
        else:
            self.listener_switch_var.set(False)
            self.listener_status_label.config(text="已停止", fg="#ef4444")

    def update_stats(self):
        """更新统计数据（今日使用）"""
        self.update_stat_cards()

    def update_stat_cards(self):
        """更新统计卡片显示"""
        # 清空统计框架中的旧卡片
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        # 重新创建统计卡片
        total_count = len(self.hotkeys)
        enabled_count = sum(1 for data in self.hotkeys.values() if isinstance(data, dict) and data.get("enabled", True))

        total_card = self.create_stat_card(self.stats_frame, "🎯", "快捷键总数", str(total_count), "#3b82f6")
        total_card.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        enabled_card = self.create_stat_card(self.stats_frame, "✅", "启用数量", str(enabled_count), "#10b981")
        enabled_card.pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        usage_card = self.create_stat_card(self.stats_frame, "📈", "今日使用", str(self.today_usage), "#f59e0b")
        usage_card.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0))

        # 添加按钮
        add_btn = Button(self.stats_frame, text="+ 添加快捷键", font=("微软雅黑", 10),
                         bg="#3b82f6", fg="white", relief=FLAT, bd=0,
                         padx=20, pady=10, cursor="hand2",
                         command=self.show_add_dialog)
        add_btn.pack(side=RIGHT, padx=(20, 0))

    def filter_list(self):
        """筛选列表"""
        self.refresh_list()

    def refresh_list(self):
        """刷新列表 - 使用新的数据结构"""
        # 清空现有内容
        for widget in self.list_inner_frame.winfo_children():
            widget.destroy()

        search_text = self.search_entry.get().lower()
        if search_text == "搜索快捷键或常用语...":
            search_text = ""

        show_enabled_only = self.show_enabled_var.get()

        for hotkey_str, data in self.hotkeys.items():
            if isinstance(data, dict):
                name = data.get("name", "未命名")
                content = data.get("content", "")
                enabled = data.get("enabled", True)
            else:
                # 兼容旧数据
                name = "未命名"
                content = str(data)
                enabled = True

            # 筛选（搜索快捷键、名称或内容）
            if search_text:
                search_in = f"{hotkey_str.lower()} {name.lower()} {content.lower()}"
                if search_text not in search_in:
                    continue
            if show_enabled_only and not enabled:
                continue

            self.create_list_item(hotkey_str, name, content, enabled)

    def create_list_item(self, hotkey_str, name, content, enabled):
        """创建列表项 - 新布局：快捷键、名称、状态、操作按钮"""
        item_frame = Frame(self.list_inner_frame, bg="white", height=50)
        item_frame.pack(fill=X)
        item_frame.pack_propagate(False)

        # 快捷键标签
        hotkey_label = Label(item_frame, text=hotkey_str.replace('+', ' + ').title(),
                             font=("微软雅黑", 10), bg="#eff6ff", fg="#3b82f6",
                             padx=8, pady=2)
        hotkey_label.place(x=15, y=12)

        # 名称（截断显示）
        display_name = name[:10] + "..." if len(name) > 10 else name
        name_label = Label(item_frame, text=display_name, font=("微软雅黑", 10),
                           bg="white", fg="#374151", width=15, anchor=W)
        name_label.place(x=130, y=15)

        # 状态开关
        status_var = BooleanVar(value=enabled)
        status_switch = self.create_toggle_switch(item_frame, status_var,
                                                   lambda h=hotkey_str, v=status_var: self.toggle_hotkey_status(h, v))
        status_switch.place(x=340, y=13)

        # 操作按钮区域
        btn_frame = Frame(item_frame, bg="white")
        btn_frame.place(x=400, y=10)

        # 编辑按钮
        edit_btn = Button(btn_frame, text="修改", font=("微软雅黑", 9), bg="#f3f4f6", fg="#374151",
               relief=FLAT, bd=0, padx=10, pady=3, cursor="hand2",
               command=lambda h=hotkey_str: self.edit_hotkey(h))
        edit_btn.pack(side=LEFT, padx=2)

        # 删除按钮
        delete_btn = Button(btn_frame, text="删除", font=("微软雅黑", 9), bg="#fef2f2", fg="#ef4444",
               relief=FLAT, bd=0, padx=10, pady=3, cursor="hand2",
               command=lambda h=hotkey_str: self.delete_hotkey(h))
        delete_btn.pack(side=LEFT, padx=2)

        # 详情按钮
        detail_btn = Button(btn_frame, text="详情", font=("微软雅黑", 9), bg="#eff6ff", fg="#3b82f6",
               relief=FLAT, bd=0, padx=10, pady=3, cursor="hand2",
               command=lambda c=content: self.show_detail(c))
        detail_btn.pack(side=LEFT, padx=2)

        # 分隔线
        Frame(self.list_inner_frame, bg="#e5e7eb", height=1).pack(fill=X)

    def show_detail(self, text):
        """显示详情弹窗"""
        dialog = Toplevel(self.root)
        dialog.title("详情")
        dialog.geometry("500x300")
        dialog.configure(bg="white")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # 居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        Label(dialog, text="快捷键内容：", font=("微软雅黑", 11, "bold"),
              bg="white", fg="#1f2937").pack(anchor=W, padx=20, pady=(20, 10))

        # 文本显示区域
        text_frame = Frame(dialog, bg="white")
        text_frame.pack(fill=BOTH, expand=True, padx=20, pady=5)

        text_widget = Text(text_frame, font=("微软雅黑", 10), wrap=WORD,
                          bg="#f9fafb", fg="#374151", relief=FLAT, padx=10, pady=10)
        text_widget.pack(fill=BOTH, expand=True)
        text_widget.insert("1.0", text)
        text_widget.config(state=DISABLED)

        # 关闭按钮
        Button(dialog, text="关闭", font=("微软雅黑", 10), bg="#f3f4f6", fg="#374151",
               relief=FLAT, bd=0, padx=30, pady=8, command=dialog.destroy).pack(pady=15)

    def toggle_hotkey_status(self, hotkey_str, var):
        """切换快捷键启用状态"""
        if hotkey_str in self.hotkeys:
            if isinstance(self.hotkeys[hotkey_str], dict):
                self.hotkeys[hotkey_str]["enabled"] = var.get()
            else:
                self.hotkeys[hotkey_str] = {"text": self.hotkeys[hotkey_str], "enabled": var.get()}
            self.save_config()
            self.refresh_list()
            self.update_stat_cards()  # 更新统计卡片

            if self.is_running:
                self.stop_listener()
                self.start_listener()

    def show_add_dialog(self, edit_mode=False, hotkey_str=None):
        """显示添加/编辑对话框

        Args:
            edit_mode: 是否为编辑模式
            hotkey_str: 编辑的快捷键（编辑模式时使用）
        """
        dialog = Toplevel(self.root)
        dialog.title("修改快捷键" if edit_mode else "添加快捷键")
        dialog.geometry("400x300")
        dialog.configure(bg="white")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # 让对话框居中显示
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # 如果是编辑模式，获取现有数据
        original_hotkey = hotkey_str if edit_mode else None
        original_name = ""
        original_content = ""
        if edit_mode and hotkey_str in self.hotkeys:
            data = self.hotkeys[hotkey_str]
            if isinstance(data, dict):
                original_name = data.get("name", "")
                original_content = data.get("content", "")

        Label(dialog, text="快捷键:", font=("微软雅黑", 10), bg="white").pack(anchor=W, padx=20, pady=(15, 5))
        hotkey_entry = Entry(dialog, font=("微软雅黑", 10), relief=SOLID, bd=1, highlightbackground="#e5e7eb")
        hotkey_entry.pack(fill=X, padx=20, pady=5)
        hotkey_entry.insert(0, original_hotkey if edit_mode else "ctrl+1")

        Label(dialog, text="名称:", font=("微软雅黑", 10), bg="white").pack(anchor=W, padx=20, pady=(10, 5))
        name_entry = Entry(dialog, font=("微软雅黑", 10), relief=SOLID, bd=1, highlightbackground="#e5e7eb")
        name_entry.pack(fill=X, padx=20, pady=5)
        name_entry.insert(0, original_name if edit_mode else "")

        Label(dialog, text="内容:", font=("微软雅黑", 10), bg="white").pack(anchor=W, padx=20, pady=(10, 5))
        content_entry = Entry(dialog, font=("微软雅黑", 10), relief=SOLID, bd=1, highlightbackground="#e5e7eb")
        content_entry.pack(fill=X, padx=20, pady=5)
        content_entry.insert(0, original_content if edit_mode else "你好")

        def save():
            hotkey = hotkey_entry.get().strip()
            name = name_entry.get().strip()
            content = content_entry.get().strip()

            if not hotkey or not content:
                messagebox.showwarning("警告", "快捷键和内容都不能为空！", parent=dialog)
                return

            if '+' not in hotkey:
                messagebox.showwarning("警告", "格式不正确！", parent=dialog)
                return

            if self.parse_hotkey(hotkey) is None:
                messagebox.showwarning("警告", f"无法识别快捷键 '{hotkey}'", parent=dialog)
                return

            # 如果没有填写名称，自动生成
            if not name:
                # 查找最大的未命名编号
                max_id = 0
                for k, v in self.hotkeys.items():
                    if isinstance(v, dict) and v.get("name", "").startswith("未命名"):
                        try:
                            num = int(v["name"].replace("未命名", ""))
                            max_id = max(max_id, num)
                        except:
                            pass
                name = f"未命名{max_id + 1}"

            # 检查是否重复（编辑模式下如果快捷键没变则不提示）
            if hotkey in self.hotkeys and hotkey != original_hotkey:
                if not messagebox.askyesno("确认", f"快捷键 '{hotkey}' 已存在，是否覆盖？", parent=dialog):
                    return

            # 编辑模式：如果快捷键改变了，删除旧的
            if edit_mode and original_hotkey and original_hotkey != hotkey:
                if original_hotkey in self.hotkeys:
                    del self.hotkeys[original_hotkey]

            self.hotkeys[hotkey] = {"name": name, "content": content, "enabled": True}
            self.save_config()
            self.refresh_list()
            self.update_stat_cards()  # 更新统计卡片
            dialog.destroy()

            if self.is_running:
                self.stop_listener()
                self.start_listener()

        def delete():
            """删除当前快捷键"""
            if original_hotkey and original_hotkey in self.hotkeys:
                if messagebox.askyesno("确认", f"确定要删除 '{original_hotkey}' 吗？", parent=dialog):
                    del self.hotkeys[original_hotkey]
                    self.save_config()
                    self.refresh_list()
                    self.update_stat_cards()  # 更新统计卡片
                    dialog.destroy()

                    if self.is_running:
                        self.stop_listener()
                        if self.hotkeys:
                            self.start_listener()
                        self.update_listener_ui()

        # 按钮区域
        btn_frame = Frame(dialog, bg="white")
        btn_frame.pack(fill=X, padx=20, pady=20)

        # 编辑模式下显示删除按钮
        if edit_mode:
            Button(btn_frame, text="删除", font=("微软雅黑", 10), bg="#fef2f2", fg="#ef4444",
                   relief=FLAT, bd=0, padx=25, pady=8, command=delete).pack(side=LEFT, padx=5)

        Button(btn_frame, text="取消", font=("微软雅黑", 10), bg="#f3f4f6", fg="#6b7280",
               relief=FLAT, bd=0, padx=30, pady=8, command=dialog.destroy).pack(side=RIGHT, padx=5)

        Button(btn_frame, text="保存", font=("微软雅黑", 10), bg="#3b82f6", fg="white",
               relief=FLAT, bd=0, padx=30, pady=8, command=save).pack(side=RIGHT, padx=5)

    def edit_hotkey(self, hotkey_str):
        """编辑快捷键 - 调用统一的对话框"""
        self.show_add_dialog(edit_mode=True, hotkey_str=hotkey_str)

    def delete_hotkey(self, hotkey_str):
        """删除快捷键"""
        if messagebox.askyesno("确认", f"确定要删除 '{hotkey_str}' 吗？"):
            del self.hotkeys[hotkey_str]
            self.save_config()
            self.refresh_list()
            self.update_stat_cards()  # 更新统计卡片

            if self.is_running:
                self.stop_listener()
                if self.hotkeys:
                    self.start_listener()
                self.update_listener_ui()

    def on_closing(self):
        """关闭窗口"""
        self.stop_listener()
        self.root.destroy()


def main():
    app = HotkeyTyper()
    app.create_gui()


if __name__ == "__main__":
    main()
