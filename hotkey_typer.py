#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快捷键输入工具 - 设置快捷键对应常用语，在任何输入框中自动输入
使用 Windows 原生 RegisterHotKey API
"""

import json
import os
import sys
import threading
import time
from tkinter import *
from tkinter import messagebox, ttk

# 检查操作系统，如果不是 Windows 就报错退出
if sys.platform != 'win32':
    messagebox.showerror("错误", "本工具仅支持 Windows 系统")
    sys.exit(1)

import ctypes
from ctypes import wintypes

# ==================== Windows API 常量定义 ====================

# 热键消息编号，当用户按下注册的热键时，Windows 会发送这个消息
WM_HOTKEY = 0x0312

# 修饰键的标识码，用于组合键（如 Ctrl+Alt+A）
MOD_ALT = 0x0001      # Alt 键
MOD_CONTROL = 0x0002  # Ctrl 键
MOD_SHIFT = 0x0004    # Shift 键
MOD_WIN = 0x0008      # Win 键（Windows 徽标键）

# 虚拟键码映射表：把键盘上的字符转换成 Windows 能识别的数字编码
# 这样我们就可以用 'ctrl+a' 这样的字符串来注册快捷键了
VK_MAP = {
    # 字母键
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
    'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
    'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
    's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
    'y': 0x59, 'z': 0x5A,
    # 数字键
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    # 功能键 F1-F12
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74,
    'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79,
    'f11': 0x7A, 'f12': 0x7B,
    # 特殊键
    'space': 0x20,      # 空格键
    'tab': 0x09,        # Tab 键
    'enter': 0x0D,      # 回车键
    'esc': 0x1B,        # Esc 键
    'up': 0x26,         # 方向上
    'down': 0x28,       # 方向下
    'left': 0x25,       # 方向左
    'right': 0x27,      # 方向右
    'insert': 0x2D,     # Insert 键
    'delete': 0x2E,     # Delete 键
    'home': 0x24,       # Home 键
    'end': 0x23,        # End 键
    'pageup': 0x21,     # Page Up
    'pagedown': 0x22,   # Page Down
}

# ==================== 加载 Windows 系统函数 ====================

# 加载 user32.dll 和 kernel32.dll，这是 Windows 的核心系统库
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 注册热键函数：告诉 Windows 当用户按下某个组合键时通知我们
# 参数：窗口句柄、热键ID、修饰键、虚拟键码
RegisterHotKey = user32.RegisterHotKey
RegisterHotKey.argtypes = [wintypes.HWND, wintypes.INT, wintypes.UINT, wintypes.UINT]

# 注销热键函数：取消之前注册的热键
UnregisterHotKey = user32.UnregisterHotKey
UnregisterHotKey.argtypes = [wintypes.HWND, wintypes.INT]

# 消息获取函数：从 Windows 消息队列中获取消息（阻塞式）
GetMessage = user32.GetMessageW

# 消息翻译和分发函数
TranslateMessage = user32.TranslateMessage
DispatchMessage = user32.DispatchMessageW

# 创建窗口函数：创建一个隐藏的窗口来接收热键消息
CreateWindowEx = user32.CreateWindowExW
CreateWindowEx.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
CreateWindowEx.restype = wintypes.HWND

# 默认窗口处理函数：处理我们不关心的消息
# 注意：返回类型必须是 LRESULT (ctypes.c_longlong 在 64 位系统上)
DefWindowProc = user32.DefWindowProcW
DefWindowProc.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
DefWindowProc.restype = ctypes.c_longlong  # LRESULT

# 销毁窗口函数
DestroyWindow = user32.DestroyWindow

# SendInput 函数：用于模拟键盘输入
SendInput = user32.SendInput
SendInput.argtypes = [wintypes.UINT, ctypes.c_void_p, wintypes.INT]
SendInput.restype = wintypes.UINT


# ==================== 数据结构定义 ====================

class MSG(ctypes.Structure):
    """Windows 消息结构体：用来接收 Windows 发来的各种消息"""
    _fields_ = [
        ("hwnd", wintypes.HWND),      # 窗口句柄
        ("message", wintypes.UINT),   # 消息类型
        ("wParam", wintypes.WPARAM),  # 附加参数1
        ("lParam", wintypes.LPARAM),  # 附加参数2
        ("time", wintypes.DWORD),     # 消息发生时间
        ("pt", wintypes.POINT),       # 鼠标位置
    ]


# ==================== 主程序类 ====================

class HotkeyTyper:
    """快捷键输入工具的主类"""

    def __init__(self):
        print("[初始化] 程序启动，正在初始化...")
        # 配置文件名，用来保存用户的快捷键设置
        self.config_file = "hotkey_config.json"

        # 存储所有快捷键和对应的文本，格式：{"ctrl+1": "你好", "ctrl+2": "谢谢"}
        self.hotkeys = {}

        # 标记当前是否正在监听快捷键
        self.is_running = False

        # 隐藏窗口的句柄，用来接收 Windows 消息
        self.hwnd = None

        # 快捷键到ID的映射，Windows 要求每个热键有一个唯一ID
        self.hotkey_id_map = {}

        # 下一个可用的热键ID，从1开始递增
        self.next_id = 1

        # 监听线程对象，用来在后台运行消息循环
        self.listener_thread = None

        # Tkinter 主窗口对象
        self.root = None

        # 窗口过程回调函数引用，必须保持引用防止被垃圾回收
        self.wnd_proc_callback = None

        # 启动时加载之前保存的配置
        print("[初始化] 正在加载配置文件...")
        self.load_config()
        print(f"[初始化] 加载完成，共 {len(self.hotkeys)} 个快捷键")

    def load_config(self):
        """从配置文件加载快捷键设置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.hotkeys = json.load(f)
                print(f"[配置] 成功从 {self.config_file} 加载配置")
            except Exception as e:
                print(f"[配置] 加载配置失败: {e}")
                self.hotkeys = {}
        else:
            print(f"[配置] 配置文件 {self.config_file} 不存在，使用空配置")

    def save_config(self):
        """保存快捷键设置到配置文件"""
        print(f"[配置] 正在保存配置到 {self.config_file}...")
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.hotkeys, f, ensure_ascii=False, indent=2)
            print("[配置] 保存成功")
            return True
        except Exception as e:
            print(f"[配置] 保存配置失败: {e}")
            return False

    def add_hotkey(self, hotkey_str, text):
        """添加一个新的快捷键"""
        print(f"[添加] 正在添加快捷键: {hotkey_str} -> {text}")
        self.hotkeys[hotkey_str] = text
        result = self.save_config()
        if result:
            print(f"[添加] 快捷键添加成功")
        else:
            print(f"[添加] 快捷键添加失败")
        return result

    def remove_hotkey(self, hotkey_str):
        """删除一个快捷键"""
        print(f"[删除] 正在删除快捷键: {hotkey_str}")
        if hotkey_str in self.hotkeys:
            del self.hotkeys[hotkey_str]
            result = self.save_config()
            if result:
                print(f"[删除] 快捷键删除成功")
            else:
                print(f"[删除] 快捷键删除失败")
            return result
        print(f"[删除] 快捷键不存在: {hotkey_str}")
        return False

    def parse_hotkey(self, hotkey_str):
        """
        把用户输入的快捷键字符串（如 "ctrl+1"）解析成 Windows 能理解的格式
        返回：(修饰键组合, 虚拟键码)
        """
        print(f"[解析] 正在解析快捷键: {hotkey_str}")
        # 按 + 号分割，比如 "ctrl+shift+a" 变成 ["ctrl", "shift", "a"]
        parts = hotkey_str.lower().split('+')

        modifiers = 0  # 修饰键组合（Ctrl/Alt/Shift/Win）
        key_part = None  # 主键（字母、数字、F键等）

        # 遍历每个部分，识别修饰键和主键
        for part in parts:
            part = part.strip()
            if part == 'ctrl':
                modifiers |= MOD_CONTROL
                print(f"[解析]   识别到修饰键: Ctrl")
            elif part == 'alt':
                modifiers |= MOD_ALT
                print(f"[解析]   识别到修饰键: Alt")
            elif part == 'shift':
                modifiers |= MOD_SHIFT
                print(f"[解析]   识别到修饰键: Shift")
            elif part == 'win':
                modifiers |= MOD_WIN
                print(f"[解析]   识别到修饰键: Win")
            else:
                key_part = part  # 不是修饰键，就是主键
                print(f"[解析]   识别到主键: {part}")

        # 如果没有主键，返回失败
        if key_part is None:
            print(f"[解析] 错误: 没有主键")
            return None

        # 在虚拟键码映射表中查找主键对应的数字编码
        vk = VK_MAP.get(key_part)
        if vk is None:
            print(f"[解析] 错误: 未知的主键 '{key_part}'")
            return None

        print(f"[解析] 成功: modifiers={modifiers}, vk={vk}")
        return (modifiers, vk)

    def type_text(self, text):
        """
        模拟键盘输入，把指定的文本输入到当前光标位置
        使用 Windows 的 SendInput 函数，支持中文输入
        """
        print(f"[输入] 开始输入文本: '{text}'")
        
        # 第一步：先释放所有修饰键（Ctrl/Alt/Shift/Win）
        # 如果不这样做，可能会导致输入异常，比如一直按着 Ctrl 键
        print("[输入] 步骤1: 释放所有修饰键...")
        modifier_keys = [0xA0, 0xA1, 0xA2, 0xA3, 0x5B, 0x5C]  # Shift左/右, Ctrl左/右, Win左/右
        for vk in modifier_keys:
            # 0x0002 表示按键释放
            user32.keybd_event(vk, 0, 0x0002, 0)
        time.sleep(0.05)  # 稍微等一下，确保按键真的释放了
        print("[输入] 步骤1: 修饰键已释放")

        # 第二步：使用 SendInput 函数输入每个字符
        print("[输入] 步骤2: 使用 SendInput 输入字符...")
        
        # 定义键盘输入结构体
        # 注意：Windows API 中的 KEYBDINPUT 结构体有特定的内存布局
        # 在 64 位系统上，总大小应该是 32 字节，需要 8 字节对齐
        class KEYBDINPUT(ctypes.Structure):
            _pack_ = 8  # 8 字节对齐
            _fields_ = [
                ("wVk", wintypes.WORD),           # 虚拟键码（我们用 0，因为用 Unicode）
                ("wScan", wintypes.WORD),         # 扫描码（这里放 Unicode 字符编码）
                ("dwFlags", wintypes.DWORD),      # 标志位
                ("time", wintypes.DWORD),         # 时间戳
                ("dwExtraInfo", ctypes.c_ulonglong),  # 额外信息 - 必须是 8 字节！
            ]

        # 定义鼠标输入结构体（用于填充联合体，保持大小一致）
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

        # 定义硬件输入结构体
        class HARDWAREINPUT(ctypes.Structure):
            _pack_ = 8
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD),
            ]

        # 定义输入联合体（包含键盘、鼠标、硬件三种输入）
        class INPUT_I(ctypes.Union):
            _pack_ = 8
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT),
            ]

        # 定义输入结构体
        class INPUT(ctypes.Structure):
            _pack_ = 8
            _fields_ = [("type", wintypes.DWORD), ("_input", INPUT_I)]
            _anonymous_ = ("_input",)  # 匿名联合体，可以直接用 .ki 访问

        # 常量定义
        INPUT_KEYBOARD = 1           # 输入类型：键盘
        KEYEVENTF_UNICODE = 0x0004   # 使用 Unicode 输入
        KEYEVENTF_KEYUP = 0x0002     # 按键释放

        # 为每个字符创建两个输入事件：按下和释放
        inputs = []
        for char in text:
            char_code = ord(char)  # 获取字符的 Unicode 编码

            # 按下事件
            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.ki.wVk = 0                      # 虚拟键码设为 0
            inp_down.ki.wScan = char_code            # 扫描码设为 Unicode 编码
            inp_down.ki.dwFlags = KEYEVENTF_UNICODE  # 标志：使用 Unicode
            inp_down.ki.time = 0
            inp_down.ki.dwExtraInfo = 0
            inputs.append(inp_down)

            # 释放事件
            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.ki.wVk = 0
            inp_up.ki.wScan = char_code
            inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP  # Unicode + 释放
            inp_up.ki.time = 0
            inp_up.ki.dwExtraInfo = 0
            inputs.append(inp_up)

        # 调用 SendInput 函数一次性发送所有输入事件
        nInputs = len(inputs)
        print(f"[输入] 步骤2: 共 {nInputs} 个输入事件（{len(text)} 个字符）")
        
        # 创建输入数组类型
        LPINPUT = INPUT * nInputs
        pInputs = LPINPUT(*inputs)
        cbSize = ctypes.sizeof(INPUT)
        
        print(f"[输入] 步骤2: 调用 SendInput (cbSize={cbSize})...")
        # 使用已经定义好参数类型的 SendInput 函数
        result = SendInput(nInputs, ctypes.cast(pInputs, ctypes.c_void_p), cbSize)
        print(f"[输入] 步骤2: SendInput 返回 {result}")
        
        if result == 0:
            print(f"[输入] 错误: SendInput 失败，错误码: {kernel32.GetLastError()}")
        elif result != nInputs:
            print(f"[输入] 警告: SendInput 只发送了 {result}/{nInputs} 个事件")
        else:
            print(f"[输入] 成功: 所有 {result} 个事件已发送")
        print("[输入] 文本输入完成")

    def on_hotkey_triggered(self, hotkey_id):
        """
        当用户按下注册的快捷键时，这个函数会被调用
        根据热键ID找到对应的文本，然后输入到当前光标位置
        """
        print(f"\n[触发] ========== 快捷键被触发 (ID={hotkey_id}) ==========")
        
        # 遍历查找哪个快捷键对应这个ID
        found = False
        for hotkey_str, hid in self.hotkey_id_map.items():
            if hid == hotkey_id:
                found = True
                # 找到对应的文本
                text = self.hotkeys.get(hotkey_str, "")
                print(f"[触发] 匹配到快捷键: {hotkey_str}")
                print(f"[触发] 对应文本: '{text}'")
                
                if text:
                    print("[触发] 启动输入线程...")
                    # 在新线程中执行输入，避免阻塞消息循环
                    # 如果不这样做，输入过程中界面会卡住
                    threading.Thread(
                        target=lambda t=text: self.type_text(t),
                        daemon=True
                    ).start()
                else:
                    print("[触发] 警告: 文本为空，不执行输入")
                break
        
        if not found:
            print(f"[触发] 错误: 未找到 ID={hotkey_id} 对应的快捷键")
        print("[触发] ========== 处理完成 ==========\n")

    def create_message_window(self):
        """
        创建一个隐藏的窗口，用来接收 Windows 发来的热键消息
        Windows 要求必须有一个窗口才能接收热键通知
        """
        print("[窗口] 开始创建消息窗口...")
        
        # 如果之前注册过窗口类，先注销掉，避免重复注册报错
        print("[窗口] 步骤1: 注销之前的窗口类（如果存在）...")
        try:
            ctypes.windll.user32.UnregisterClassW(
                "HotkeyTyperWindow",
                kernel32.GetModuleHandleW(None)
            )
            print("[窗口] 步骤1: 已注销旧窗口类")
        except:
            print("[窗口] 步骤1: 没有旧窗口类需要注销")

        # 定义窗口过程函数：处理 Windows 发给窗口的消息
        # 这是一个回调函数，Windows 会在有消息时调用它
        print("[窗口] 步骤2: 定义窗口过程回调函数...")
        # 注意：窗口过程的返回类型必须是 LRESULT (64位系统上是 ctypes.c_longlong)
        @ctypes.WINFUNCTYPE(
            ctypes.c_longlong,  # 返回值类型 LRESULT
            wintypes.HWND,      # 窗口句柄
            wintypes.UINT,      # 消息类型
            wintypes.WPARAM,    # 参数1
            wintypes.LPARAM     # 参数2
        )
        def wnd_proc(hwnd, msg, wParam, lParam):
            # 如果是热键消息，调用处理函数
            if msg == WM_HOTKEY:
                self.on_hotkey_triggered(wParam)
                return 0  # 返回 0 表示消息已处理
            # 其他消息交给 Windows 默认处理
            # 注意：DefWindowProc 的返回值是 LRESULT，需要正确转换
            result = DefWindowProc(hwnd, msg, wParam, lParam)
            return ctypes.c_longlong(result).value

        # 保存回调函数引用，防止被 Python 垃圾回收导致程序崩溃
        self.wnd_proc_callback = wnd_proc
        print("[窗口] 步骤2: 回调函数已定义并保存引用")

        # 动态创建窗口类结构体
        print("[窗口] 步骤3: 创建窗口类结构体...")
        WNDCLASSEXW = type('WNDCLASSEXW', (ctypes.Structure,), {
            '_fields_': [
                ("cbSize", wintypes.UINT),        # 结构体大小
                ("style", wintypes.UINT),         # 窗口样式
                ("lpfnWndProc", ctypes.c_void_p), # 窗口过程函数指针
                ("cbClsExtra", wintypes.INT),     # 额外类内存
                ("cbWndExtra", wintypes.INT),     # 额外窗口内存
                ("hInstance", wintypes.HINSTANCE), # 实例句柄
                ("hIcon", wintypes.HANDLE),       # 图标
                ("hCursor", wintypes.HANDLE),     # 光标
                ("hbrBackground", wintypes.HANDLE), # 背景画刷
                ("lpszMenuName", wintypes.LPCWSTR), # 菜单名称
                ("lpszClassName", wintypes.LPCWSTR), # 类名称
                ("hIconSm", wintypes.HANDLE),     # 小图标
            ]
        })

        # 获取当前程序实例句柄
        hinst = kernel32.GetModuleHandleW(None)
        class_name = "HotkeyTyperWindow"  # 窗口类名

        # 填充窗口类信息
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        # 把 Python 函数转换为 C 函数指针
        wc.lpfnWndProc = ctypes.cast(wnd_proc, ctypes.c_void_p).value
        wc.hInstance = hinst
        wc.lpszClassName = class_name

        # 注册窗口类
        print("[窗口] 步骤4: 注册窗口类...")
        result = ctypes.windll.user32.RegisterClassExW(ctypes.byref(wc))
        if result == 0:
            err = ctypes.get_last_error()
            print(f"[窗口] 步骤4: 注册窗口类失败，错误码: {err}")
            return None
        print(f"[窗口] 步骤4: 窗口类注册成功 (atom={result})")

        # 创建隐藏窗口
        print("[窗口] 步骤5: 创建隐藏窗口...")
        hwnd = CreateWindowEx(
            0,              # 扩展样式
            class_name,     # 窗口类名
            "HotkeyTyper",  # 窗口标题
            0,              # 窗口样式
            0, 0, 0, 0,     # 位置和大小（都是0表示隐藏）
            None,           # 父窗口
            None,           # 菜单
            hinst,          # 实例句柄
            None            # 附加参数
        )

        if hwnd == 0:
            err = ctypes.get_last_error()
            print(f"[窗口] 步骤5: 创建窗口失败，错误码: {err}")
            return None

        print(f"[窗口] 步骤5: 隐藏窗口创建成功 (hwnd={hwnd})")
        print("[窗口] 消息窗口创建完成")
        return hwnd

    def register_all_hotkeys(self):
        """把所有配置的快捷键注册到 Windows 系统"""
        print(f"\n[注册] ========== 开始注册快捷键 ==========")
        print(f"[注册] 共有 {len(self.hotkeys)} 个快捷键需要注册")
        
        # 清空之前的映射
        self.hotkey_id_map = {}
        self.next_id = 1

        # 遍历所有配置的快捷键
        success_count = 0
        fail_count = 0
        
        for hotkey_str in list(self.hotkeys.keys()):
            print(f"\n[注册] 正在注册: {hotkey_str}")
            
            # 解析快捷键字符串
            parsed = self.parse_hotkey(hotkey_str)
            if parsed is None:
                print(f"[注册]   失败: 无法解析快捷键")
                fail_count += 1
                continue

            modifiers, vk = parsed
            hotkey_id = self.next_id
            self.next_id += 1

            # 调用 Windows API 注册热键
            print(f"[注册]   调用 RegisterHotKey(hwnd={self.hwnd}, id={hotkey_id}, modifiers={modifiers}, vk={vk})...")
            result = RegisterHotKey(self.hwnd, hotkey_id, modifiers, vk)
            
            if result:
                self.hotkey_id_map[hotkey_str] = hotkey_id
                print(f"[注册]   成功: {hotkey_str} (id={hotkey_id})")
                success_count += 1
            else:
                err = ctypes.get_last_error()
                print(f"[注册]   失败: 错误码={err}")
                fail_count += 1

        print(f"\n[注册] ========== 注册完成 ==========")
        print(f"[注册] 成功: {success_count} 个, 失败: {fail_count} 个")

    def unregister_all_hotkeys(self):
        """注销所有已注册的热键"""
        print(f"\n[注销] 正在注销所有热键...")
        count = 0
        for hotkey_id in self.hotkey_id_map.values():
            result = UnregisterHotKey(self.hwnd, hotkey_id)
            if result:
                count += 1
        print(f"[注销] 已注销 {count}/{len(self.hotkey_id_map)} 个热键")
        self.hotkey_id_map = {}

    def message_loop(self):
        """
        消息循环：不断从 Windows 获取消息并处理
        这是 Windows 程序的标准做法，必须在一个循环中不断获取消息
        """
        print("[消息循环] 消息循环线程已启动")
        msg = MSG()
        loop_count = 0
        
        while self.is_running:
            # 获取消息，如果没有消息会阻塞等待
            ret = GetMessage(ctypes.byref(msg), self.hwnd, 0, 0)

            # ret == 0 表示收到退出消息，ret == -1 表示出错
            if ret == 0:
                print("[消息循环] 收到退出消息，循环结束")
                break
            if ret == -1:
                err = ctypes.get_last_error()
                print(f"[消息循环] 获取消息出错，错误码: {err}")
                break

            # 翻译消息（把键盘消息转换为字符消息）
            TranslateMessage(ctypes.byref(msg))
            # 分发消息给窗口过程处理
            DispatchMessage(ctypes.byref(msg))
            
            loop_count += 1
            if loop_count % 100 == 0:
                print(f"[消息循环] 已处理 {loop_count} 条消息")

        print(f"[消息循环] 消息循环结束，共处理 {loop_count} 条消息")

    def start_listener(self):
        """启动全局快捷键监听"""
        print("\n[启动监听] ========== 开始启动监听 ==========")
        
        # 如果已经在监听，直接返回
        if self.is_running:
            print("[启动监听] 已经在监听中，无需重复启动")
            return

        # 如果没有配置任何快捷键，提示用户
        if not self.hotkeys:
            print("[启动监听] 没有配置快捷键，监听未启动")
            return

        # 标记为运行状态
        self.is_running = True
        print("[启动监听] 状态已设置为运行中")

        # 创建接收消息的隐藏窗口
        print("[启动监听] 正在创建消息窗口...")
        self.hwnd = self.create_message_window()
        if not self.hwnd:
            self.is_running = False
            print("[启动监听] 创建消息窗口失败，监听启动失败")
            return
        print("[启动监听] 消息窗口创建成功")

        # 注册所有快捷键到 Windows
        print("[启动监听] 正在注册快捷键...")
        self.register_all_hotkeys()
        print("[启动监听] 快捷键注册完成")

        # 在后台线程启动消息循环
        # 这样不会阻塞 GUI 界面
        print("[启动监听] 正在启动消息循环线程...")
        self.listener_thread = threading.Thread(
            target=self.message_loop,
            daemon=True
        )
        self.listener_thread.start()
        print("[启动监听] 消息循环线程已启动")
        print("[启动监听] ========== 监听启动成功 ==========\n")

    def stop_listener(self):
        """停止全局快捷键监听"""
        print("\n[停止监听] ========== 开始停止监听 ==========")
        
        if not self.is_running:
            print("[停止监听] 当前未在监听，无需停止")
            return
            
        self.is_running = False
        print("[停止监听] 状态已设置为停止")

        # 注销所有热键
        print("[停止监听] 正在注销热键...")
        self.unregister_all_hotkeys()

        # 销毁隐藏窗口
        if self.hwnd:
            print("[停止监听] 正在销毁消息窗口...")
            result = DestroyWindow(self.hwnd)
            print(f"[停止监听] 销毁窗口结果: {result}")
            self.hwnd = None

        self.listener_thread = None
        print("[停止监听] ========== 监听已停止 ==========\n")

    # ==================== GUI 界面部分 ====================

    def create_gui(self):
        """创建图形用户界面"""
        print("[GUI] 正在创建图形界面...")
        
        # 创建主窗口
        self.root = Tk()
        self.root.title("快捷键输入工具")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        print("[GUI] 主窗口已创建")

        # 尝试设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap("icon.ico")
            print("[GUI] 窗口图标已设置")
        except:
            print("[GUI] 窗口图标未找到，使用默认图标")

        # ===== 顶部状态栏 =====
        print("[GUI] 创建状态栏...")
        status_frame = Frame(self.root)
        status_frame.pack(fill=X, padx=10, pady=5)

        # 状态标签
        self.status_label = Label(
            status_frame,
            text="状态: 已停止",
            bg="#f0f0f0",
            fg="black",
            font=("微软雅黑", 10, "bold")
        )
        self.status_label.pack(side=LEFT, padx=10, pady=5)

        # 开始/停止按钮
        self.toggle_btn = Button(
            status_frame,
            text="开始监听",
            command=self.toggle_listener,
            bg="#4CAF50",
            fg="white",
            font=("微软雅黑", 9)
        )
        self.toggle_btn.pack(side=RIGHT, padx=10, pady=5)
        print("[GUI] 状态栏创建完成")

        # ===== 添加快捷键区域 =====
        print("[GUI] 创建添加快捷键区域...")
        add_frame = LabelFrame(
            self.root,
            text="添加快捷键",
            font=("微软雅黑", 10, "bold")
        )
        add_frame.pack(fill=X, padx=10, pady=10)

        # 快捷键输入框
        Label(add_frame, text="快捷键:", font=("微软雅黑", 9)).grid(
            row=0, column=0, padx=5, pady=5, sticky=E
        )
        self.hotkey_entry = Entry(add_frame, font=("微软雅黑", 9))
        self.hotkey_entry.grid(row=0, column=1, padx=5, pady=5, sticky=W+E)
        self.hotkey_entry.insert(0, "ctrl+1")  # 默认值

        # 格式提示
        Label(
            add_frame,
            text="(格式: ctrl+1, alt+shift+a)",
            font=("微软雅黑", 8),
            fg="gray"
        ).grid(row=0, column=2, padx=5, pady=5, sticky=W)

        # 常用语输入框
        Label(add_frame, text="常用语:", font=("微软雅黑", 9)).grid(
            row=1, column=0, padx=5, pady=5, sticky=E
        )
        self.text_entry = Entry(add_frame, font=("微软雅黑", 9))
        self.text_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=W+E)
        self.text_entry.insert(0, "你好")  # 默认值

        # 添加按钮
        Button(
            add_frame,
            text="添加",
            command=self.add_hotkey_from_gui,
            bg="#2196F3",
            fg="white",
            font=("微软雅黑", 9)
        ).grid(row=2, column=1, columnspan=2, padx=5, pady=10, sticky=E)

        add_frame.columnconfigure(1, weight=1)
        print("[GUI] 添加快捷键区域创建完成")

        # ===== 快捷键列表区域 =====
        print("[GUI] 创建快捷键列表区域...")
        list_frame = LabelFrame(
            self.root,
            text="已设置的快捷键",
            font=("微软雅黑", 10, "bold")
        )
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 创建表格
        columns = ("hotkey", "text")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # 设置表头
        self.tree.heading("hotkey", text="快捷键")
        self.tree.heading("text", text="常用语")

        # 设置列宽
        self.tree.column("hotkey", width=150, anchor=W)
        self.tree.column("text", width=400, anchor=W)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(
            list_frame,
            orient=VERTICAL,
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 使用 grid 布局，更好地控制各个组件的位置
        self.tree.grid(row=0, column=0, sticky=NSEW, padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky=NS, pady=5)

        # 按钮区域
        btn_frame = Frame(list_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky=EW, padx=5, pady=5)

        # 修改按钮
        Button(
            btn_frame,
            text="修改选中",
            command=self.edit_selected_hotkey,
            bg="#FF9800",
            fg="white",
            font=("微软雅黑", 9)
        ).pack(side=LEFT, padx=5)

        # 删除按钮
        Button(
            btn_frame,
            text="删除选中",
            command=self.remove_selected_hotkey,
            bg="#f44336",
            fg="white",
            font=("微软雅黑", 9)
        ).pack(side=LEFT, padx=5)

        # 配置 grid 权重，让树形控件可以扩展
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        print("[GUI] 快捷键列表区域创建完成")

        # 刷新列表显示
        self.refresh_list()

        # 设置窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        print("[GUI] 界面创建完成，进入主循环")
        # 进入主循环
        self.root.mainloop()

    def toggle_listener(self):
        """切换监听状态（开始/停止）"""
        print(f"\n[切换] 用户点击了{'停止' if self.is_running else '开始'}按钮")
        if self.is_running:
            self.stop_listener()
        else:
            self.start_listener()
        self.update_status_ui()

    def update_status_ui(self):
        """根据当前状态更新界面显示"""
        print(f"[界面] 更新状态显示: {'运行中' if self.is_running else '已停止'}")
        if self.is_running:
            self.status_label.config(
                text="状态: 运行中",
                bg="#4CAF50",
                fg="white"
            )
            self.toggle_btn.config(
                text="停止监听",
                bg="#f44336"
            )
        else:
            self.status_label.config(
                text="状态: 已停止",
                bg="#f0f0f0",
                fg="black"
            )
            self.toggle_btn.config(
                text="开始监听",
                bg="#4CAF50"
            )

    def add_hotkey_from_gui(self):
        """从界面获取输入并添加快捷键"""
        hotkey = self.hotkey_entry.get().strip()
        text = self.text_entry.get().strip()
        
        print(f"\n[界面] 用户点击添加按钮")
        print(f"[界面]   快捷键: {hotkey}")
        print(f"[界面]   常用语: {text}")

        # 检查输入是否为空
        if not hotkey or not text:
            print("[界面] 错误: 输入为空")
            messagebox.showwarning("警告", "快捷键和常用语都不能为空！")
            return

        # 检查格式是否包含 +
        if '+' not in hotkey:
            print("[界面] 错误: 格式不正确，缺少 + 号")
            messagebox.showwarning(
                "警告",
                "快捷键格式不正确！请使用类似 'ctrl+1' 的格式"
            )
            return

        # 解析快捷键，检查是否有效
        print("[界面] 正在解析快捷键...")
        parsed = self.parse_hotkey(hotkey)
        if parsed is None:
            print("[界面] 错误: 快捷键解析失败")
            messagebox.showwarning(
                "警告",
                f"无法识别快捷键 '{hotkey}'，请检查格式"
            )
            return

        # 添加到配置
        print("[界面] 正在添加到配置...")
        if self.add_hotkey(hotkey, text):
            messagebox.showinfo("成功", f"快捷键 '{hotkey}' 添加成功！")
            self.text_entry.delete(0, END)  # 清空常用语输入框
            self.refresh_list()  # 刷新列表

            # 如果正在监听，需要重启以加载新快捷键
            if self.is_running:
                print("[界面] 正在监听中，重启监听以加载新快捷键...")
                self.stop_listener()
                self.start_listener()
        else:
            messagebox.showerror("错误", "添加快捷键失败！")

    def edit_selected_hotkey(self):
        """修改选中的快捷键"""
        # 获取选中的项
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要修改的快捷键！")
            return

        # 获取当前值
        item = self.tree.item(selected[0])
        old_hotkey = item['values'][0]
        old_text = item['values'][1]

        print(f"\n[界面] 用户请求修改快捷键: {old_hotkey}")

        # 创建修改对话框
        edit_window = Toplevel(self.root)
        edit_window.title("修改快捷键")
        edit_window.geometry("400x150")
        edit_window.resizable(False, False)
        edit_window.transient(self.root)  # 设置为模态对话框
        edit_window.grab_set()

        # 快捷键输入框
        Label(edit_window, text="快捷键:", font=("微软雅黑", 9)).grid(
            row=0, column=0, padx=5, pady=10, sticky=E
        )
        hotkey_var = StringVar(value=old_hotkey)
        hotkey_entry = Entry(edit_window, textvariable=hotkey_var, font=("微软雅黑", 9))
        hotkey_entry.grid(row=0, column=1, padx=5, pady=10, sticky=W+E)

        # 常用语输入框
        Label(edit_window, text="常用语:", font=("微软雅黑", 9)).grid(
            row=1, column=0, padx=5, pady=10, sticky=E
        )
        text_var = StringVar(value=old_text)
        text_entry = Entry(edit_window, textvariable=text_var, font=("微软雅黑", 9))
        text_entry.grid(row=1, column=1, padx=5, pady=10, sticky=W+E)

        edit_window.columnconfigure(1, weight=1)

        def save_edit():
            """保存修改"""
            new_hotkey = hotkey_var.get().strip()
            new_text = text_var.get().strip()

            # 检查输入
            if not new_hotkey or not new_text:
                messagebox.showwarning("警告", "快捷键和常用语都不能为空！", parent=edit_window)
                return

            if '+' not in new_hotkey:
                messagebox.showwarning("警告", "快捷键格式不正确！请使用类似 'ctrl+1' 的格式", parent=edit_window)
                return

            # 解析快捷键
            parsed = self.parse_hotkey(new_hotkey)
            if parsed is None:
                messagebox.showwarning("警告", f"无法识别快捷键 '{new_hotkey}'，请检查格式", parent=edit_window)
                return

            # 如果快捷键变了，需要删除旧的，添加新的
            if new_hotkey != old_hotkey:
                print(f"[界面] 快捷键从 '{old_hotkey}' 变为 '{new_hotkey}'")
                # 删除旧的
                if not self.remove_hotkey(old_hotkey):
                    messagebox.showerror("错误", "修改快捷键失败（删除旧键时出错）！", parent=edit_window)
                    return
                # 添加新的
                if not self.add_hotkey(new_hotkey, new_text):
                    # 如果添加失败，恢复旧的
                    self.add_hotkey(old_hotkey, old_text)
                    messagebox.showerror("错误", "修改快捷键失败（添加新键时出错）！", parent=edit_window)
                    return
            else:
                # 快捷键没变，只修改文本
                print(f"[界面] 只修改常用语: '{old_text}' -> '{new_text}'")
                self.hotkeys[old_hotkey] = new_text
                if not self.save_config():
                    messagebox.showerror("错误", "保存配置失败！", parent=edit_window)
                    return

            messagebox.showinfo("成功", "快捷键修改成功！", parent=edit_window)
            edit_window.destroy()
            self.refresh_list()

            # 如果正在监听，重启监听
            if self.is_running:
                print("[界面] 正在监听中，重启监听...")
                self.stop_listener()
                if self.hotkeys:
                    self.start_listener()
                self.update_status_ui()

        # 按钮区域
        btn_frame = Frame(edit_window)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15)

        Button(
            btn_frame,
            text="保存",
            command=save_edit,
            bg="#4CAF50",
            fg="white",
            font=("微软雅黑", 9),
            width=10
        ).pack(side=LEFT, padx=10)

        Button(
            btn_frame,
            text="取消",
            command=edit_window.destroy,
            bg="#9E9E9E",
            fg="white",
            font=("微软雅黑", 9),
            width=10
        ).pack(side=LEFT, padx=10)

        # 让对话框居中显示
        edit_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - edit_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - edit_window.winfo_height()) // 2
        edit_window.geometry(f"+{x}+{y}")

        # 聚焦到常用语输入框
        text_entry.select_range(0, END)
        text_entry.focus()

    def remove_selected_hotkey(self):
        """删除选中的快捷键"""
        # 获取选中的项
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的快捷键！")
            return

        # 获取快捷键字符串
        item = self.tree.item(selected[0])
        hotkey = item['values'][0]

        print(f"\n[界面] 用户请求删除快捷键: {hotkey}")

        # 确认删除
        if messagebox.askyesno("确认", f"确定要删除快捷键 '{hotkey}' 吗？"):
            if self.remove_hotkey(hotkey):
                messagebox.showinfo("成功", "快捷键删除成功！")
                self.refresh_list()

                # 如果正在监听，重启监听
                if self.is_running:
                    print("[界面] 正在监听中，重启监听...")
                    self.stop_listener()
                    if self.hotkeys:
                        self.start_listener()
                    self.update_status_ui()
            else:
                messagebox.showerror("错误", "删除快捷键失败！")

    def refresh_list(self):
        """刷新快捷键列表显示"""
        print("[界面] 刷新快捷键列表...")
        # 清空现有内容
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加所有快捷键
        for hotkey, text in self.hotkeys.items():
            self.tree.insert("", END, values=(hotkey, text))
        print(f"[界面] 列表已刷新，共 {len(self.hotkeys)} 项")

    def on_closing(self):
        """窗口关闭时的处理"""
        print("\n[关闭] 用户关闭窗口，正在清理...")
        self.stop_listener()  # 停止监听
        print("[关闭] 正在销毁窗口...")
        self.root.destroy()   # 销毁窗口
        print("[关闭] 程序已退出")


def main():
    """程序入口"""
    print("=" * 50)
    print("快捷键输入工具 - 启动")
    print("=" * 50)
    app = HotkeyTyper()
    app.create_gui()


if __name__ == "__main__":
    main()
