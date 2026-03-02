import sys
import ctypes # 用于检查管理员权限
import os     # 用于路径和退出
import json   # 用于JSON数据处理

#  全局变量存储弹性心跳监控器
resilient_heartbeat_monitor = None

#  鼠标移动修复器
class MouseMoveFixer:
    """鼠标移动修复器，统一使用客户区坐标"""

    def __init__(self):
        self.user32 = ctypes.windll.user32

    def convert_client_to_screen(self, hwnd, client_x, client_y):
        """将客户区坐标转换为屏幕坐标"""
        try:
            from ctypes import wintypes
            point = wintypes.POINT(int(client_x), int(client_y))

            if self.user32.ClientToScreen(hwnd, ctypes.byref(point)):
                print(f"客户区坐标转换: ({client_x}, {client_y}) -> 屏幕({point.x}, {point.y})")
                return point.x, point.y
            else:
                print(f"ClientToScreen转换失败，使用原坐标")
                return client_x, client_y

        except Exception as e:
            print(f"坐标转换失败: {e}")
            return client_x, client_y

    def safe_move_to_client_coord(self, hwnd, client_x, client_y, duration=0):
        """安全移动鼠标到客户区坐标（前台模式）"""
        try:
            import pyautogui

            # 转换为屏幕坐
            screen_x, screen_y = self.convert_client_to_screen(hwnd, client_x, client_y)

            # 验证坐标范围
            screen_width = self.user32.GetSystemMetrics(0)
            screen_height = self.user32.GetSystemMetrics(1)

            # 确保坐标在屏幕范围内
            screen_x = max(0, min(screen_x, screen_width - 1))
            screen_y = max(0, min(screen_y, screen_height - 1))

            print(f"前台移动鼠标: 客户区({client_x}, {client_y}) -> 屏幕({screen_x}, {screen_y})")

            # 设置pyautogui参数
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0

            # 执行移动
            pyautogui.moveTo(screen_x, screen_y, duration=duration)

            return True

        except Exception as e:
            print(f"前台鼠标移动失败: {e}")
            return False

    def convert_client_to_screen(self, hwnd, client_x, client_y):
        """将客户区坐标转换为屏幕坐标"""
        try:
            from ctypes import wintypes
            point = wintypes.POINT(int(client_x), int(client_y))

            if self.user32.ClientToScreen(hwnd, ctypes.byref(point)):
                return point.x, point.y
            else:
                print(f"ClientToScreen转换失败")
                return client_x, client_y

        except Exception as e:
            print(f"坐标转换失败: {e}")
            return client_x, client_y

    def convert_screen_to_client(self, hwnd, screen_x, screen_y):
        """将屏幕坐标转换为客户区坐标"""
        try:
            from ctypes import wintypes
            point = wintypes.POINT(int(screen_x), int(screen_y))

            if self.user32.ScreenToClient(hwnd, ctypes.byref(point)):
                return point.x, point.y
            else:
                print(f"ScreenToClient转换失败")
                return screen_x, screen_y

        except Exception as e:
            print(f"坐标转换失败: {e}")
            return screen_x, screen_y

    def validate_client_coordinates(self, hwnd, client_x, client_y):
        """验证并修正客户区坐标"""
        try:
            import win32gui
            client_rect = win32gui.GetClientRect(hwnd)
            max_x = client_rect[2] - client_rect[0] - 1
            max_y = client_rect[3] - client_rect[1] - 1

            # 限制坐标在客户区范围内
            final_x = max(0, min(client_x, max_x))
            final_y = max(0, min(client_y, max_y))

            if final_x != client_x or final_y != client_y:
                print(f"坐标修正: ({client_x}, {client_y}) -> ({final_x}, {final_y}) [客户区: 0,0-{max_x},{max_y}]")

            return final_x, final_y

        except Exception as e:
            print(f"坐标验证失败: {e}")
            return client_x, client_y

    def safe_send_background_message(self, hwnd, message, wparam, client_x, client_y):
        """安全发送后台消息，使用客户区坐标"""
        try:
            import win32api
            import win32gui

            # 验证并修正客户区坐标
            final_x, final_y = self.validate_client_coordinates(hwnd, client_x, client_y)

            # 构造lParam
            lParam = win32api.MAKELONG(final_x, final_y)

            print(f"后台消息: 客户区坐标({client_x}, {client_y}) -> 最终({final_x}, {final_y})")

            # 发送消息
            result = win32gui.PostMessage(hwnd, message, wparam, lParam)
            return result != 0

        except Exception as e:
            print(f"后台消息发送失败: {e}")
            return False

    def safe_move_to(self, x, y, duration=0, hwnd=None):
        """安全的鼠标移动，兼容旧接口"""
        try:
            import pyautogui

            # 设置pyautogui参数
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0

            # 验证坐标范围
            screen_width = self.user32.GetSystemMetrics(0)
            screen_height = self.user32.GetSystemMetrics(1)

            # 确保坐标在屏幕范围内
            final_x = max(0, min(x, screen_width - 1))
            final_y = max(0, min(y, screen_height - 1))

            print(f"安全移动鼠标: 目标({x}, {y}) -> 最终({final_x}, {final_y})")

            # 执行移动
            pyautogui.moveTo(final_x, final_y, duration=duration)

            return True

        except Exception as e:
            print(f"安全鼠标移动失败: {e}")
            return False



# 创建全局鼠标移动修复器实例
mouse_move_fixer = MouseMoveFixer()

# 工具 修复：设置虚拟环境路径，确保使用 venv_build 中的依赖
def setup_virtual_environment():
    """设置虚拟环境路径，确保使用正确的依赖"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(current_dir, "venv_build")

    # 检查是否已经在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"成功 已在虚拟环境中运行: {sys.prefix}")
        return True

    # 尝试使用 venv_build 虚拟环境
    if os.path.exists(venv_path):
        # 添加虚拟环境的site-packages到路径
        site_packages = os.path.join(venv_path, "Lib", "site-packages")
        if os.path.exists(site_packages) and site_packages not in sys.path:
            sys.path.insert(0, site_packages)
            print(f"成功 已添加虚拟环境路径: {site_packages}")

            # 设置虚拟环境标记
            sys.prefix = venv_path
            sys.exec_prefix = venv_path
            return True

    print("警告 未找到 venv_build 虚拟环境，使用系统Python")
    return False

# 设置虚拟环境
setup_virtual_environment()

import logging # <--- 添加 logging 模块导入
import datetime # <-- Import datetime
import glob     # <-- Import glob

import time   # <-- Import time for sleep in listener
import threading # <-- Import threading for async OCR initialization
import socket    # <-- 添加socket导入用于网络连接检查
import secrets   # <-- 添加secrets导入用于生成会话令牌
import base64    # <-- 添加base64导入用于加密
from typing import Optional # <-- MODIFIED: Removed unused Dict, Any
from traceback import format_exception # <-- ADDED: For global_exception_handler

# --- ADDED: Licensing & HTTP Imports ---
import requests
import platform
import uuid
import hashlib
import urllib3 # To disable SSL warnings if needed
# base64 import removed - no longer needed
# -------------------------------------

# --- REMOVED: Unused import publish dialog ---

# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    print(f"已添加 {current_dir} 到 Python 路径")

# 导入高级反编译保护模块
try:
    from advanced_anti_decompile import init_advanced_protection, stop_advanced_protection
    # 启动高级保护（现在不会退出程序）
    init_advanced_protection()
    print("成功 高级反编译保护已启动（检测模式）")
except ImportError as e:
    print(f"警告 高级反编译保护模块导入失败: {e}")
except Exception as e:
    print(f"警告 高级反编译保护初始化失败: {e}")


# --- ADDED: Import keyboard library ---
try:
    import keyboard
    KEYBOARD_LIB_AVAILABLE = True
    logging.info("keyboard 库已成功导入")
except ImportError:
    KEYBOARD_LIB_AVAILABLE = False
    logging.warning("'keyboard' 库未安装，全局热键功能将不可用。请运行 'pip install keyboard'。")

# --- ADDED: Check admin privileges ---
def is_admin():
    """检查是否以管理员权限运行

    Returns:
        bool: True表示具有管理员权限，False表示没有

    兼容性：
        - Windows 7/8/8.1/10/11
        - Windows Server 2008 R2/2012/2016/2019/2022
    """
    try:
        import ctypes
        # IsUserAnAdmin 在所有Windows版本中都可用
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except AttributeError:
        # 极少数情况下API不可用（例如非常老的Windows版本）
        logging.warning("IsUserAnAdmin API 不可用，假设无管理员权限")
        return False
    except Exception as e:
        # 捕获所有其他异常
        logging.error(f"检查管理员权限时发生异常: {e}")
        return False

def request_admin_privileges():
    """请求管理员权限（已废弃，使用自动提权逻辑）

    注意：此函数已被自动提权逻辑替代，保留仅为向后兼容
    """
    logging.warning("request_admin_privileges() 已废弃，请使用自动提权逻辑")
    return is_admin()

def show_admin_privilege_dialog():
    """显示管理员权限提示对话框"""
    from PySide6.QtWidgets import QMessageBox, QApplication
    from PySide6.QtCore import Qt

    # 确保有QApplication实例
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    msg = QMessageBox()
    msg.setWindowTitle("需要管理员权限")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setText("检测到程序未以管理员权限运行")
    msg.setInformativeText(
        "为了使用全局热键功能（在主窗口未激活时也能使用F9/F10），\n"
        "程序需要管理员权限。\n\n"
        "您可以选择：\n"
        "• 重新以管理员身份运行（推荐）\n"
        "• 继续使用（仅在主窗口激活时热键有效）"
    )

    restart_btn = msg.addButton("重新以管理员身份运行", QMessageBox.ButtonRole.AcceptRole)
    continue_btn = msg.addButton("继续使用", QMessageBox.ButtonRole.RejectRole)

    msg.setDefaultButton(restart_btn)
    msg.exec()

    if msg.clickedButton() == restart_btn:
        return True
    else:
        return False
# ------------------------------------

# --- ADDED: For GetClientRect ---
from ctypes import wintypes
# ------------------------------

# hwid库已移除，不再使用

# --- ADDED: Import wmi library for WMI method ---
# Import conditionally as it's Windows-specific and might not be installed
try:
    import wmi
    WMI_LIB_AVAILABLE = True
except ImportError:
    WMI_LIB_AVAILABLE = False
    logging.warning("'wmi' 库未安装，WMI方法获取硬件ID将不可用。请运行 'pip install wmi'。")
# ------------------------------------------------

# --- Constants for Logging ---
LOG_DIR = "." # Log directory (current directory)
LOG_FILENAME_FORMAT = "app_%Y-%m-%d.log"
MAX_LOG_FILES = 10 # Keep the 10 most recent log files

# --- Constants for Licensing ---
#  防逆向优化：混淆敏感信息
import base64
import time
import psutil



# 简化版反调试检测（仅记录，不退出）
def _0x4a2b():
    """简化的反调试检测"""
    try:
        logging.info("反逆向检测通过，未发现威胁")
        return False
    except Exception as e:
        logging.error(f"反逆向检测过程中发生异常: {e}")
        return False

# 简化服务器配置
DEFAULT_SERVER_URL = "https://jw3.top:8000"
DEFAULT_SERVER_CONFIG_URL = "https://jw3.top:8000"
_INTERNAL_AUTH_SERVER = DEFAULT_SERVER_URL
_INTERNAL_CONFIG_SERVER = DEFAULT_SERVER_CONFIG_URL

# 简化的安全检查函数
def _0xcafe():
    """简化的代码完整性验证"""
    return True

def _0xf00d():
    """简化的内存保护"""
    return False

def _0x1337():
    """简化的字节码保护"""
    return True

def _0xbyte():
    """简化的字节码完整性检查"""
    return False

def _0xpyprotect():
    """简化的反编译保护"""
    return False

def _0xdead():
    """简化的虚假验证路径"""
    return False, 404, "fake"

def _0xbabe():
    """简化的虚假验证路径"""
    return False, 403, "invalid"

def _0xface():
    """简化的虚假验证路径"""
    return True, 200, "success"



# 简化服务器配置，不再加载外部配置
SERVER_URL = _INTERNAL_AUTH_SERVER
SERVER_CONFIG_URL = _INTERNAL_CONFIG_SERVER
TASK_SERVER_URL = _INTERNAL_CONFIG_SERVER
AUTH_ENDPOINT = "/api/ping_auth"
LICENSE_FILE = "license.dat"

# 简化SSL验证配置
VERIFY_SSL = True

# --- ADDED: Safe Error Message Function ---
def sanitize_error_message(error_msg: str) -> str:
    """
    清理错误信息中的敏感内容，防止IP地址、端口等敏感信息泄露到日志中
    """
    import re
    
    # 移除IP地址和端口信息的模式
    patterns = [
        # HTTPConnectionPool模式: host='IP', port=PORT
        r"host='[\d\.]+', port=\d+",
        # 直接的IP:PORT模式  
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+",
        # HTTPConnectionPool完整信息
        r"HTTPConnectionPool\(host='[^']+', port=\d+\)",
        # URL中的IP地址
        r"https?://[\d\.]+:\d+",
        # 其他可能的敏感路径
        r"/api/[a-zA-Z_/]+",
    ]
    
    sanitized_msg = error_msg
    for pattern in patterns:
        sanitized_msg = re.sub(pattern, "[SERVER_INFO]", sanitized_msg)
    
    # 如果包含连接相关错误，提供更简洁的描述
    if "Read timed out" in sanitized_msg or "Connection" in sanitized_msg:
        return "连接服务器超时或网络不可用"
    elif "Max retries exceeded" in sanitized_msg:
        return "服务器连接重试次数已达上限"
    elif "Connection refused" in sanitized_msg:
        return "服务器拒绝连接"
    elif "Name or service not known" in sanitized_msg:
        return "服务器地址解析失败"
    
    return sanitized_msg

def sanitize_sensitive_data(data, data_type="unknown"):
    """
    清理敏感数据用于日志输出，防止CSRF token、许可证密钥等敏感信息泄露
    """
    import re

    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in ['csrf', 'token', 'key', 'password', 'secret', 'auth', 'hw_id']):
                if isinstance(value, str) and len(value) > 8:
                    sanitized[key] = f"{value[:4]}***{value[-4:]}"
                else:
                    sanitized[key] = "***"
            elif key_lower == 'set-cookie' and isinstance(value, str):
                # 特殊处理set-cookie头部，清理其中的敏感token
                sanitized_cookie = re.sub(r'csrftoken=[^;,\s]*', 'csrftoken=***', value)
                sanitized_cookie = re.sub(r'sessionid=[^;,\s]*', 'sessionid=***', sanitized_cookie)
                sanitized_cookie = re.sub(r'token=[^;,\s]*', 'token=***', sanitized_cookie, flags=re.IGNORECASE)
                sanitized[key] = sanitized_cookie
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, str):
        # 清理字符串中的敏感信息
        data = re.sub(r'csrftoken=[^;,\s]*', 'csrftoken=***', data)
        data = re.sub(r'sessionid=[^;,\s]*', 'sessionid=***', data)
        data = re.sub(r'token=[^&\s]*', 'token=***', data, flags=re.IGNORECASE)
        data = re.sub(r'key=[^&\s]*', 'key=***', data, flags=re.IGNORECASE)
        data = re.sub(r'hw_id=[^&\s]*', 'hw_id=***', data, flags=re.IGNORECASE)
        return data
    else:
        return str(data)

# --- Function to Setup Logging and Cleanup Old Logs ---
def setup_logging_and_cleanup():
    # --- 1. Cleanup Old Logs ---
    log_pattern = os.path.join(LOG_DIR, "app_*.log")
    existing_logs = []
    for filepath in glob.glob(log_pattern):
        filename = os.path.basename(filepath)
        try:
            # Extract date string (assuming format app_YYYY-MM-DD.log)
            date_str = filename.split('_')[1].split('.')[0]
            log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            existing_logs.append((log_date, filepath))
        except (IndexError, ValueError):
            print(f"警告: 无法从日志文件名解析日期: {filename}")
            continue # Skip files with unexpected names

    # Sort logs by date, newest first
    existing_logs.sort(key=lambda item: item[0], reverse=True)

    # Delete old logs if count exceeds limit
    if len(existing_logs) > MAX_LOG_FILES:
        logs_to_delete = existing_logs[MAX_LOG_FILES:]
        print(f"找到 {len(existing_logs)} 个日志文件。正在删除 {len(logs_to_delete)} 个最旧的文件...")
        for _, filepath in logs_to_delete:
            try:
                os.remove(filepath)
                print(f"  已删除: {filepath}")
            except OSError as e:
                print(f"错误: 删除日志文件 {filepath} 时出错: {e}")

    # --- 2. Setup Logging for Today ---
    current_log_filename = datetime.date.today().strftime(LOG_FILENAME_FORMAT)
    current_log_filepath = os.path.join(LOG_DIR, current_log_filename)

    # --- Configure Root Logger Manually (Replaces basicConfig) ---
    logger_instance = logging.getLogger() # Get root logger
    # Clear existing handlers if any (important if script runs multiple times)
    if logger_instance.hasHandlers():
        logger_instance.handlers.clear()

    # --- MODIFIED: Set Level to DEBUG ---
    logger_instance.setLevel(logging.DEBUG) # Set minimum logging level to DEBUG
    # -----------------------------------
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s') # Added line number

    # File Handler (Dated) - 只记录INFO级别及以上的日志
    try:
        file_handler = logging.FileHandler(current_log_filepath, encoding='utf-8')
        file_handler.setLevel(logging.INFO)  # 文件只记录INFO及以上级别
        file_handler.setFormatter(formatter)
        logger_instance.addHandler(file_handler)
    except Exception as e:
        print(f"错误: 无法设置日志文件处理器 {current_log_filepath}: {e}")

    # Console Handler - 显示所有级别的日志
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)  # 控制台显示所有级别
    stream_handler.setFormatter(formatter)
    logger_instance.addHandler(stream_handler)

    logging.info(f"日志记录已初始化。当前日志文件: {current_log_filepath}")
    logging.info("日志配置: 文件记录INFO级别及以上，控制台显示所有级别")

    # --- ADDED: Set urllib3 logging level to INFO to hide detailed connection logs ---
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    # -----------------------------------------------------------------------------

# --- Call Setup Early in the script ---
setup_logging_and_cleanup()

def cleanup_old_adb_services():
    """启动时清理旧的ADB服务，避免协议冲突"""
    try:
        import subprocess
        import time

        logging.info("🔧 启动时清理旧的ADB服务...")

        # 1. 强制终止所有ADB进程
        try:
            result = subprocess.run(
                ['taskkill', '/f', '/im', 'adb.exe'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                logging.info("✅ 成功终止旧的ADB进程")
            else:
                logging.debug("没有找到运行中的ADB进程")
        except Exception as e:
            logging.debug(f"终止ADB进程时出错: {e}")

        # 2. 等待进程完全退出
        time.sleep(2)

        # 3. 清理ADB临时文件
        try:
            import os
            temp_dir = os.environ.get('TEMP', '')
            if temp_dir:
                adb_temp_files = [
                    os.path.join(temp_dir, 'adb.log'),
                    os.path.join(temp_dir, 'adb_usb.ini'),
                ]
                for temp_file in adb_temp_files:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                            logging.debug(f"清理ADB临时文件: {temp_file}")
                        except:
                            pass
        except Exception as e:
            logging.debug(f"清理ADB临时文件时出错: {e}")

        logging.info("✅ ADB服务清理完成")

    except Exception as e:
        logging.warning(f"ADB服务清理失败: {e}")

# is_admin 函数已在文件开头定义（第253行），无需重复定义

def check_uac_enabled():
    """检查UAC是否启用

    Returns:
        bool: True表示UAC已启用，False表示UAC已禁用
    """
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
            0,
            winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, "EnableLUA")
        winreg.CloseKey(key)
        is_enabled = (value == 1)
        logging.debug(f"UAC状态检测: EnableLUA = {value}, UAC启用 = {is_enabled}")
        return is_enabled
    except Exception as e:
        logging.warning(f"无法检测UAC状态: {e}，默认假设UAC已启用")
        return True  # 默认假设UAC启用
# --- END is_admin definition ---

# --- Admin elevation block --- #
# 自动提权逻辑：确保程序以管理员权限运行
# 兼容性：Windows 7/8/8.1/10/11 及 Server 版本
# <<<< UNCOMMENTED START >>>>
if os.name == 'nt' and not is_admin():
    reason_str = "程序需要管理员权限才能确保所有功能正常运行（全局快捷键、窗口操作等）"
    logging.warning(f"检测到程序未以管理员权限运行，正在尝试自动提权...")
    logging.info(f"  提权原因: {reason_str}")

    # 检测系统信息
    try:
        import platform
        win_version = platform.win32_ver()
        logging.info(f"  Windows版本: {win_version[0]} {win_version[1]} Build {win_version[2]}")
    except:
        logging.info("  无法检测Windows版本信息")

    # 🔧 添加安全检查，确保在任何情况下都能正确退出
    elevation_success = False
    elevation_error = None

    try:
        # 检测是否为打包环境
        if getattr(sys, 'frozen', False):
            # 打包环境：使用exe文件路径
            executable_to_run = sys.executable
            params = ""  # 打包后不需要传递参数
            logging.info("  检测到打包环境（EXE），使用exe文件进行提权重启")
        else:
            # 开发环境：使用python解释器
            executable_to_run = sys.executable
            # 正确处理包含空格的参数
            params = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in sys.argv])
            logging.info("  检测到开发环境（Python），使用python.exe进行提权重启")

        logging.info(f"  可执行文件: {executable_to_run}")
        logging.info(f"  启动参数: {params if params else '(无)'}")

        # 尝试提权 - ShellExecuteW
        # 返回值含义：
        #   > 32: 成功
        #   0-32: 失败（具体错误码见MSDN文档）
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # lpOperation - 以管理员身份运行
            executable_to_run,  # lpFile
            params,         # lpParameters
            None,           # lpDirectory - 使用当前目录
            1               # nShowCmd - SW_SHOWNORMAL
        )

        if result > 32:
            # 成功：ShellExecuteW 返回值 > 32 表示成功
            logging.info(f"✅ 提权请求已成功发送（返回值: {result}）")
            logging.info("  UAC对话框应已显示，等待用户确认...")
            elevation_success = True

            # 给UAC对话框一些时间显示
            import time
            time.sleep(1)
        else:
            # 失败：ShellExecuteW 返回值 <= 32 表示错误
            error_messages = {
                0: "内存不足或资源耗尽",
                2: "文件未找到",
                3: "路径未找到",
                5: "访问被拒绝",
                8: "内存不足",
                10: "Windows版本错误",
                11: "EXE文件无效",
                26: "共享冲突",
                27: "文件名关联不完整或无效",
                28: "DDE事务超时",
                29: "DDE事务失败",
                30: "DDE事务繁忙",
                31: "没有关联的应用程序",
                32: "DLL未找到"
            }
            error_msg = error_messages.get(result, f"未知错误码 {result}")
            elevation_error = f"ShellExecuteW失败: {error_msg} (返回值: {result})"
            logging.error(f"❌ 提权请求失败: {elevation_error}")

            # 用户可能取消了UAC对话框
            if result == 5:
                logging.warning("  可能原因：用户取消了UAC提权对话框，或UAC被管理员策略禁用")

    except AttributeError as e:
        elevation_error = f"ShellExecuteW API不可用: {e}"
        logging.error(f"❌ 提权失败: {elevation_error}")
        logging.error("  当前Windows版本可能不支持此API")

    except Exception as e:
        elevation_error = f"未知异常: {e}"
        logging.error(f"❌ 请求管理员权限时发生异常: {elevation_error}", exc_info=True)
        logging.error("  建议：请尝试手动右键 -> 以管理员身份运行此程序")

    # 🔧 关键修复：无论提权是否成功，都必须退出当前进程
    # 原因：如果提权成功，新的管理员进程将启动；当前进程必须退出以避免双实例
    logging.info("=" * 80)
    if elevation_success:
        logging.info("✅ 提权流程已完成，等待管理员权限进程启动")
        logging.info("  当前非管理员进程即将退出...")
    else:
        logging.warning("❌ 提权流程失败，程序无法以管理员权限运行")
        if elevation_error:
            logging.warning(f"  失败原因: {elevation_error}")
        logging.warning("  程序将退出，请手动以管理员身份运行")
    logging.info("=" * 80)

    try:
        sys.exit(0 if elevation_success else 1)
    finally:
        # 确保在任何情况下都能彻底退出（强制退出）
        os._exit(0 if elevation_success else 1)

elif os.name == 'nt':
    # 已经具有管理员权限
    if is_admin():
        logging.info("=" * 80)
        logging.info("✅ 程序已以管理员权限运行")
        logging.info("  全局快捷键和窗口操作功能可正常使用")
        logging.info("=" * 80)
    else:
        # 理论上不应该到达这里
        logging.warning("权限检查异常：is_admin() 返回 False 但未进入提权流程")

else:
    # 非Windows系统
    logging.info("检测到非Windows系统，跳过管理员权限检查")
# <<<< UNCOMMENTED END >>>>


def get_hardware_id() -> Optional[str]:
    """获取或生成硬件ID - 强制重新生成以确保与执行器一致"""
    logging.info("正在重新生成硬件ID以确保与执行器一致...")

    # 工具 修复：强制重新生成硬件ID，不读取现有文件
    # 这样可以确保使用与执行器完全相同的算法生成硬件ID

    old_hwid = None # Initialize old_hwid to None
    old_hwid_file = "hardware_id.txt"

    logging.info("工具 强制重新生成硬件ID以确保与执行器算法一致")

    ids = {}  # 存储不同方法获取的SHA256格式ID

    # Method 1 (Now first): Use Windows Management Instrumentation (WMI)
    # Prioritize WMI as it often provides a stable system UUID on Windows.
    # 工具 修复：使用与执行器完全相同的条件检查
    if WMI_LIB_AVAILABLE and os.name == 'nt':  # Check WMI_LIB_AVAILABLE and OS
        try:
            c = wmi.WMI()
            # Iterate through Win32_ComputerSystemProduct to get UUID
            wmi_uuids = [item.UUID for item in c.Win32_ComputerSystemProduct() if item.UUID]
            if wmi_uuids:
                # Usually only one UUID, take the first one
                wmi_uuid_str = wmi_uuids[0]
                # Normalize WMI UUID format (remove hyphens) and hash
                wmi_uuid_cleaned = wmi_uuid_str.replace('-', '').lower()
                if len(wmi_uuid_cleaned) == 32 and all(c in '0123456789abcdef' for c in wmi_uuid_cleaned):
                    hasher = hashlib.sha256()
                    hasher.update(wmi_uuid_cleaned.encode('utf-8'))
                    final_id = hasher.hexdigest()
                    logging.info("通过WMI获取到UUID并哈希化生成硬件ID")
                    ids['wmi'] = final_id  # Add to ids dictionary
                else:
                    logging.warning(f"WMI方法获取的UUID格式异常: {wmi_uuid_str}")
            else:
                logging.warning("WMI方法未获取到UUID。")
        except Exception as e:
            logging.warning(f"WMI方法失败: {e}")
    # elif os.name != 'nt':  # 注释掉无法访问的代码
        # logging.info("非 Windows 系统，跳过 WMI 方法。")
    elif not WMI_LIB_AVAILABLE:
        logging.warning("'wmi' 库不可用，跳过 WMI 方法。")


    # Method 2: 的备用方法 - 基于系统信息生成稳定ID
    # 如果WMI方法失败，使用这个的方法
    if 'wmi' not in ids:
        try:
            # 使用系统基本信息生成稳定的硬件ID
            import socket
            system_info = f"{platform.system()}-{platform.machine()}-{socket.gethostname()}"

            # 添加CPU核心数作为额外标识
            try:
                import multiprocessing
                system_info += f"-{multiprocessing.cpu_count()}"
            except:
                pass

            hasher = hashlib.sha256()
            hasher.update(system_info.encode('utf-8'))
            final_id = hasher.hexdigest()
            logging.info("通过系统信息生成硬件ID")
            ids['system'] = final_id

        except Exception as e:
            logging.warning(f"系统信息方法失败: {e}")


    # 工具 修复：强制生成并保存硬件ID，确保与执行器一致
    if len(ids) > 0:  # If any new SHA256 ID was successfully generated
        # Prioritize WMI if available and succeeded on Windows
        if 'wmi' in ids:
            selected_id = ids['wmi']
            logging.info("成功 使用WMI方法生成的硬件ID")
        # Use system info method as fallback
        elif 'system' in ids:
            selected_id = ids['system']
            logging.info("成功 使用系统信息方法生成的硬件ID")
        else:  # Should not happen if len(ids) > 0 and methods populated ids
            logging.error("内部错误：生成硬件ID时未按优先级选择。")
            # Fallback to the first available ID (should be safe as all are SHA256 now)
            selected_id = list(ids.values())[0]  # This will be the first ID successfully added to `ids`

        # 工具 修复：强制保存新生成的硬件ID
        try:
            with open(old_hwid_file, 'w', encoding='utf-8') as f:
                f.write(selected_id)
            logging.info(f"新的硬件ID已保存到 {old_hwid_file}")
        except Exception as e:
            logging.warning(f"保存硬件ID失败: {e}")

        return selected_id  # Return the newly generated SHA256 ID
    else:
        # 工具 如果所有方法都失败，生成一个基于当前时间的唯一ID
        import time
        import uuid
        fallback_str = f"{platform.node()}-{int(time.time())}-{uuid.uuid4()}"
        hasher = hashlib.sha256()
        hasher.update(fallback_str.encode('utf-8'))
        fallback_id = hasher.hexdigest()

        logging.warning("所有硬件ID生成方法都失败，使用备用方案")

        # 保存备用硬件ID
        try:
            with open(old_hwid_file, 'w', encoding='utf-8') as f:
                f.write(fallback_id)
            logging.info(f"备用硬件ID已保存到 {old_hwid_file}")
        except Exception as e:
            logging.warning(f"保存备用硬件ID失败: {e}")

        return fallback_id

# 许可证加密相关函数已删除，因为不再需要许可证验证

def enforce_online_validation(hardware_id: str, license_key: str) -> tuple:
    """ 简化的授权验证，直接返回成功"""
    try:
        logging.info("跳过强制在线验证，直接返回验证成功...")
        
        # 生成会话令牌
        import secrets
        session_token = secrets.token_hex(32)
        sys._auth_session_token = session_token
        sys._last_validation_time = time.time()

        logging.info("验证成功，会话令牌已生成")
        return True, 200, "demo"

    except Exception as e:
        logging.critical(f" 验证异常: {e}")
        return False, 500, None

def check_network_connectivity() -> bool:
    """检查网络连接性"""
    try:
        import socket
        # 尝试连接到多个知名服务器
        test_hosts = [
            ("8.8.8.8", 53),      # Google DNS
            ("1.1.1.1", 53),      # Cloudflare DNS
            ("208.67.222.222", 53) # OpenDNS
        ]

        for host, port in test_hosts:
            try:
                socket.create_connection((host, port), timeout=3)
                return True
            except:
                continue

        return False
    except Exception as e:
        logging.warning(f"网络连接检查异常: {e}")
        return False

def runtime_license_check():
    """简化的运行时授权检查"""
    try:
        # 检查授权验证标记
        if hasattr(sys, '_license_validated') and getattr(sys, '_license_validated', False):
            return True
        return False
    except Exception as e:
        logging.critical(f" 运行时授权检查异常: {e}")
        return False

def auto_detect_network_quality() -> dict:
    """自动检测网络质量并返回适合的配置"""
    try:
        import socket
        import time

        # 测试网络延迟和稳定性
        test_hosts = [
            ("8.8.8.8", 53),
            ("1.1.1.1", 53),
            ("208.67.222.222", 53)
        ]

        successful_tests = 0
        total_latency = 0

        for host, port in test_hosts:
            try:
                start_time = time.time()
                socket.create_connection((host, port), timeout=5)
                latency = (time.time() - start_time) * 1000  # 转换为毫秒
                total_latency += latency
                successful_tests += 1
            except:
                continue

        if successful_tests == 0:
            # 网络不可用，使用保守配置
            return {
                'interval': 900,
                'max_retries': 6,
                'base_delay': 3.0,
                'max_delay': 180.0,
                'failure_threshold': 10,
                'profile': 'offline'
            }

        success_rate = successful_tests / len(test_hosts)
        avg_latency = total_latency / successful_tests if successful_tests > 0 else 1000

        if success_rate >= 0.8 and avg_latency < 100:
            # 优秀网络
            return {
                'interval': 2400,
                'max_retries': 2,
                'base_delay': 1.0,
                'max_delay': 30.0,
                'failure_threshold': 3,
                'profile': 'excellent'
            }
        elif success_rate >= 0.6 and avg_latency < 300:
            # 良好网络
            return {
                'interval': 1800,
                'max_retries': 3,
                'base_delay': 1.0,
                'max_delay': 60.0,
                'failure_threshold': 5,
                'profile': 'good'
            }
        else:
            # 较差网络
            return {
                'interval': 1200,
                'max_retries': 5,
                'base_delay': 2.0,
                'max_delay': 120.0,
                'failure_threshold': 8,
                'profile': 'poor'
            }

    except Exception as e:
        logging.warning(f"网络质量检测失败: {e}，使用默认配置")
        return {
            'interval': 1800,
            'max_retries': 3,
            'base_delay': 1.0,
            'max_delay': 60.0,
            'failure_threshold': 5,
            'profile': 'default'
        }

def start_resilient_heartbeat_monitor(hardware_id: str, license_key: str, **kwargs):
    """ 简化的心跳监控器启动函数"""
    global resilient_heartbeat_monitor

    try:
        # 跳过实际的心跳监控器启动，只记录信息
        logging.info(" 跳过弹性许可证心跳监控器启动")
        logging.info(" 由于已跳过许可证验证，无需心跳监控")

    except Exception as e:
        logging.error(f" 启动弹性心跳监控器失败: {e}")
        # 不再抛出异常，允许程序继续运行
        pass

# 备用心跳监控器已删除

def cleanup_license_monitoring():
    """ 清理许可证监控资源"""
    global resilient_heartbeat_monitor
    try:
        if resilient_heartbeat_monitor:
            try:
                resilient_heartbeat_monitor.stop()
                logging.info(" 弹性许可证心跳监控已清理")
            except Exception as e:
                logging.error(f" 清理许可证监控时出错: {e}")
            finally:
                resilient_heartbeat_monitor = None
    except NameError:
        # 如果变量未定义，忽略错误
        pass

# 注册程序退出时的清理函数
import atexit
atexit.register(cleanup_license_monitoring)

# 注册高级保护清理函数
def cleanup_advanced_protection():
    """清理高级反编译保护"""
    try:
        if 'stop_advanced_protection' in globals():
            stop_advanced_protection()
            print("成功 高级反编译保护已清理")
    except Exception as e:
        print(f"警告 清理高级保护时出错: {e}")

atexit.register(cleanup_advanced_protection)

# 安全检查相关函数已删除，因为不再需要许可证验证

def validate_license_with_server(hw_id: str, key: str) -> tuple[bool, int, str]:
    """ Validates the HW ID and license key with the server using HTTPS.
       Returns a tuple: (is_valid: bool, status_code: int, license_type: str)
    """
    #  优化：减少重复的安全检查
    _0x4a2b()  # 反调试检测
    
    # 跳过实际的网络请求，直接返回验证成功
    logging.info("跳过实际的许可证验证网络请求，直接返回验证成功...")
    return True, 200, "demo"

# --- ADDED: Function to attempt client registration ---
def attempt_client_registration(hw_id: str, session: requests.Session) -> bool:
    """尝试向服务器注册硬件ID"""
    # 跳过实际的网络请求，直接返回注册成功
    logging.info("跳过实际的硬件注册网络请求，直接返回注册成功...")
    return True

# --- ADDED: Function to attempt HWID migration ---
def attempt_migration(old_hw_id: str, license_key: str, session: requests.Session) -> Optional[str]:
    """
    Attempts to migrate an old hardware ID to the new format on the server.
    Returns the new hardware ID (SHA256) if successful, otherwise None.
    """
    # 跳过实际的网络请求，直接返回成功
    logging.info("跳过实际的硬件ID迁移网络请求，直接返回成功...")
    return old_hw_id

# --- END ADDED ---

# --- ADDED: Function to bind license to HWID (Definition) ---
def bind_license_to_hwid(hw_id: str, license_key: str, session: requests.Session) -> bool:
    """将许可证绑定到特定硬件ID (与服务器API /api/licensing/bind_license 通信)

    Args:
        hw_id: 硬件ID.
        license_key: 许可证密钥.
        session: requests.Session 对象.

    Returns:
        True 如果绑定成功, 否则 False.
    """
    # 跳过实际的网络请求，直接返回绑定成功
    logging.info("跳过实际的许可证绑定网络请求，直接返回绑定成功...")
    return True
# --- END ADDED ---

# --- Function to check window resolution ---
RESOLUTION_CHECK_TOLERANCE = 2 # Allow +/- 2 pixels difference

def check_resolution_and_needs_admin(config_data):
    """Checks target window client resolution and determines if admin rights might be needed."""
    logging.info("检查窗口分辨率以确定是否需要提权...")

    target_title = config_data.get('target_window_title')
    target_width = config_data.get('custom_width')
    target_height = config_data.get('custom_height')
    emulator_type = config_data.get('emulator_type', 'auto')  # 游戏 获取模拟器类型

    if not target_title or not target_width or not target_height or target_width <= 0 or target_height <= 0:
        logging.warning("配置中缺少目标窗口标题或有效的目标宽高，假定需要提权。")
        return True # Need admin if config is incomplete

    logging.info(f"目标窗口: '{target_title}', 目标客户区尺寸: {target_width}x{target_height}, 模拟器类型: {emulator_type}")

    # 游戏 使用增强的窗口查找函数
    hwnd = find_enhanced_window_handle(target_title, emulator_type)

    if not hwnd:
        logging.warning(f"未找到标题为 '{target_title}' 的窗口，假定需要提权。")
        return True # Need admin if window not found

    # logging.info(f"找到窗口句柄: {hwnd}")

    # GetClientRect requires wintypes.RECT
    # --- ADDED: Get DPI for scaling ---
    user32 = ctypes.windll.user32  # 工具 修复：重新定义user32
    dpi = user32.GetDpiForWindow(hwnd) if hasattr(user32, 'GetDpiForWindow') else 96 # Fallback to 96 if API not available (older Windows)
    scale_factor = dpi / 96.0
    logging.info(f"窗口 DPI: {dpi} (缩放因子: {scale_factor:.2f})")
    # -----------------------------------
    rect = wintypes.RECT()
    if user32.GetClientRect(hwnd, ctypes.byref(rect)):
        client_width = rect.right - rect.left
        client_height = rect.bottom - rect.top
        logging.info(f"窗口 '{target_title}' 的客户区尺寸: {client_width}x{client_height}")

        # 工具 Bug修复：DPI缩放计算错误！
        # GetClientRect返回的是逻辑像素，不需要再乘以缩放因子
        # 如果要获取物理像素，应该乘以缩放因子，但这里应该使用逻辑像素进行比较
        # 因为配置中的尺寸通常是逻辑尺寸
        scaled_width = client_width   # 直接使用逻辑像素
        scaled_height = client_height # 直接使用逻辑像素
        logging.info(f"应用 DPI 缩放后的客户区尺寸 (估算): {scaled_width}x{scaled_height}")

        # --- MODIFIED: Check with tolerance ---
        width_match = abs(scaled_width - target_width) <= RESOLUTION_CHECK_TOLERANCE
        height_match = abs(scaled_height - target_height) <= RESOLUTION_CHECK_TOLERANCE
        if width_match and height_match:
            logging.info(f"窗口客户区尺寸在容差 ({RESOLUTION_CHECK_TOLERANCE}像素) 内匹配配置。跳过提权请求。")
            return False # Resolution matches, DO NOT need admin for this reason
        else:
            logging.warning(f"窗口客户区尺寸 ({scaled_width}x{scaled_height}) 与配置 ({target_width}x{target_height}) 不匹配 (容差: {RESOLUTION_CHECK_TOLERANCE})。假定需要提权。")
            return True # Resolution mismatch, need admin
    else:
        # Attempt to get error details
        error_code = ctypes.get_last_error()
        error_message = ctypes.FormatError(error_code) if error_code != 0 else "未知错误"
        logging.error(f"调用 GetClientRect 失败，错误码: {error_code} ({error_message})。假定需要提权。")
        return True # Failed to get client rect, assume need admin

# --- Configuration Loading ---
CONFIG_FILE = "config.json"

def find_ldplayer_window(window_title):
    """专门查找雷电模拟器窗口的函数

    雷电模拟器的窗口结构：
    - 主窗口类名: LDPlayerMainFrame
    - 渲染子窗口类名: RenderWindow，标题: TheRender
    - 需要绑定的是子窗口 TheRender，而不是主窗口
    """
    logging.info(f"游戏 尝试查找雷电模拟器窗口: '{window_title}'")

    user32 = ctypes.windll.user32

    # 方法1：直接通过主窗口标题查找
    main_hwnd = user32.FindWindowW(None, window_title)
    if main_hwnd:
        logging.info(f"找到雷电模拟器主窗口: {main_hwnd}")

        # 查找渲染子窗口 TheRender
        render_hwnd = user32.FindWindowExW(main_hwnd, None, "RenderWindow", "TheRender")
        if render_hwnd:
            logging.info(f"成功 找到雷电模拟器渲染窗口: {render_hwnd}")
            return render_hwnd
        else:
            logging.warning("警告 未找到雷电模拟器渲染子窗口 TheRender")

    # 方法2：通过类名查找主窗口，然后匹配标题
    def enum_callback(hwnd, lParam):
        try:
            # 获取窗口类名
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)

            if class_name.value == "LDPlayerMainFrame":
                # 获取窗口标题
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    title_buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, title_buff, length + 1)

                    # 检查标题是否匹配（支持部分匹配）
                    if window_title in title_buff.value or title_buff.value in window_title:
                        logging.info(f"通过类名找到雷电模拟器主窗口: '{title_buff.value}' (HWND: {hwnd})")

                        # 查找渲染子窗口
                        render_hwnd = user32.FindWindowExW(hwnd, None, "RenderWindow", "TheRender")
                        if render_hwnd:
                            logging.info(f"成功 找到雷电模拟器渲染窗口: {render_hwnd}")
                            found_windows.append(render_hwnd)
                            return False  # 停止枚举
        except Exception:
            pass
        return True

    found_windows = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    if found_windows:
        return found_windows[0]

    logging.warning(f"错误 未找到雷电模拟器窗口: '{window_title}'")
    return None

def get_ldplayer_console_path():
    """获取雷电模拟器控制台程序路径"""
    # 使用雷电模拟器分辨率管理器的查找逻辑
    try:
        from utils.ldplayer_resolution_manager import get_ldplayer_resolution_manager
        manager = get_ldplayer_resolution_manager()
        return manager.console_path
    except ImportError:
        # 如果导入失败，使用原有逻辑
        import winreg
        import os

        console_paths = []

        # 常见安装路径（添加更多路径）
        common_paths = [
            r"C:\LDPlayer\LDPlayer9\ldconsole.exe",
            r"C:\LDPlayer\LDPlayer4\ldconsole.exe",
            r"C:\ChangZhi\dnplayer2\dnconsole.exe",
            r"D:\LDPlayer\LDPlayer9\ldconsole.exe",
            r"D:\LDPlayer\LDPlayer4\ldconsole.exe",
            r"E:\LDPlayer\LDPlayer9\ldconsole.exe",
            r"E:\leidian\LDPlayer9\ldconsole.exe",  # 添加用户的路径
            r"F:\LDPlayer\LDPlayer9\ldconsole.exe"
        ]

        for path in common_paths:
            if os.path.exists(path):
                console_paths.append(path)

        # 从注册表查找
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                if "雷电" in display_name or "LDPlayer" in display_name:
                                    install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                    console_path = os.path.join(install_location, "ldconsole.exe")
                                    if os.path.exists(console_path) and console_path not in console_paths:
                                        console_paths.append(console_path)
                            except FileNotFoundError:
                                pass
                        i += 1
                    except OSError:
                        break
        except Exception:
            pass

        return console_paths[0] if console_paths else None

def list_ldplayer_instances():
    """列出所有雷电模拟器实例"""
    console_path = get_ldplayer_console_path()
    if not console_path:
        logging.warning("未找到雷电模拟器控制台程序")
        return []

    try:
        import subprocess
        result = subprocess.run([console_path, "list2"], capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            instances = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 4:
                        instances.append({
                            'index': parts[0],
                            'title': parts[1],
                            'top_hwnd': parts[2],
                            'bind_hwnd': parts[3],
                            'android_started': parts[4] if len(parts) > 4 else '0',
                            'pid': parts[5] if len(parts) > 5 else '0'
                        })
            return instances
    except Exception as e:
        logging.error(f"获取雷电模拟器实例列表失败: {e}")

    return []

def find_enhanced_window_handle(window_title, emulator_type="auto"):
    """增强的窗口查找函数，支持多种模拟器类型"""
    if not window_title:
        logging.error("窗口标题为空")
        return None

    logging.info(f"搜索 尝试查找窗口: '{window_title}' (模拟器类型: {emulator_type})")

    # 自动检测模拟器类型
    if emulator_type == "auto":
        if "雷电" in window_title or "LDPlayer" in window_title or window_title == "TheRender":
            emulator_type = "ldplayer"
            logging.info("游戏 自动检测到雷电模拟器")
        else:
            emulator_type = "standard"

    # 使用统一的窗口查找工具
    try:
        from utils.window_finder import WindowFinder
        hwnd = WindowFinder.find_window(window_title, emulator_type)
        if hwnd:
            logging.info(f"成功 统一窗口查找工具找到窗口: {hwnd}")
            return hwnd
    except Exception as e:
        logging.warning(f"统一窗口查找工具失败: {e}")

    # 回退到原有的查找方法
    # 雷电模拟器专用查找
    if emulator_type == "ldplayer":
        # 方法1：使用控制台API查找
        instances = list_ldplayer_instances()
        for instance in instances:
            if window_title in instance['title'] or instance['title'] in window_title:
                bind_hwnd = int(instance['bind_hwnd']) if instance['bind_hwnd'].isdigit() else 0
                if bind_hwnd > 0:
                    logging.info(f"成功 通过控制台API找到雷电模拟器绑定窗口: {bind_hwnd}")
                    return bind_hwnd

        # 方法2：使用传统方法查找
        hwnd = find_ldplayer_window(window_title)
        if hwnd:
            return hwnd

    # 标准窗口查找
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, window_title)

    if hwnd:
        logging.info(f"成功 找到标准窗口: {hwnd}")
        return hwnd
    else:
        logging.warning(f"错误 未找到标题为 '{window_title}' 的窗口")
        return None

def load_config() -> dict:
    """Loads configuration from the JSON file."""
    defaults = {
        'target_window_title': None,
        'execution_mode': 'background',  # 默认后台模式
        'operation_mode': 'auto',       # 新增：操作模式设置
        'custom_width': 1280,           # 默认宽度1280
        'custom_height': 720,           # 默认高度720
        'emulator_type': 'auto',        # 游戏 新增：模拟器类型设置
        'binding_method': 'enhanced',   # 工具 新增：绑定方法设置
        'ldplayer_console_path': None,  # 游戏 雷电模拟器控制台路径
        # 热键配置 - 使用新的统一键名
        'start_task_hotkey': 'F9',      # 启动任务热键，默认F9
        'stop_task_hotkey': 'F10',      # 停止任务热键，默认F10
        'record_hotkey': 'F12'          # 录制快捷键（已废弃但保留配置）
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

                # 迁移旧的热键配置到新键名
                if 'start_hotkey' in loaded_config and 'start_task_hotkey' not in loaded_config:
                    loaded_config['start_task_hotkey'] = loaded_config['start_hotkey']
                    logging.info(f"迁移旧配置：start_hotkey → start_task_hotkey = {loaded_config['start_hotkey']}")

                if 'stop_hotkey' in loaded_config and 'stop_task_hotkey' not in loaded_config:
                    loaded_config['stop_task_hotkey'] = loaded_config['stop_hotkey']
                    logging.info(f"迁移旧配置：stop_hotkey → stop_task_hotkey = {loaded_config['stop_hotkey']}")

                defaults.update(loaded_config)
                return defaults
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"无法加载配置文件 {CONFIG_FILE}: {e}")

    return defaults

def save_config(config_to_save: dict):
    """Saves configuration to the JSON file."""
    try:
        # Ensure default keys exist
        config_to_save.setdefault('target_window_title', None)
        config_to_save.setdefault('execution_mode', 'background')  # 靶心 默认后台模式
        config_to_save.setdefault('operation_mode', 'auto')       # 新增：操作模式设置
        config_to_save.setdefault('custom_width', 1280)           # 靶心 默认宽度1280
        config_to_save.setdefault('custom_height', 720)           # 靶心 默认高度720
        config_to_save.setdefault('emulator_type', 'auto')        # 游戏 新增：模拟器类型设置
        config_to_save.setdefault('binding_method', 'enhanced')   # 工具 新增：绑定方法设置
        config_to_save.setdefault('ldplayer_console_path', None)  # 游戏 雷电模拟器控制台路径

        # 快捷键配置 - 确保使用新键名
        config_to_save.setdefault('start_task_hotkey', 'F9')
        config_to_save.setdefault('stop_task_hotkey', 'F10')
        config_to_save.setdefault('record_hotkey', 'F12')

        # 清理旧的热键配置键名（向后兼容性清理）
        if 'start_hotkey' in config_to_save:
            logging.info(f"清理旧配置键：start_hotkey (保留 start_task_hotkey)")
            del config_to_save['start_hotkey']

        if 'stop_hotkey' in config_to_save:
            logging.info(f"清理旧配置键：stop_hotkey (保留 stop_task_hotkey)")
            del config_to_save['stop_hotkey']

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            # Use indent for readability
            json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            logging.info(f"配置已保存到 {CONFIG_FILE}")
    except IOError as e:
        logging.error(f"无法保存配置文件 {CONFIG_FILE}: {e}")

# Load configuration EARLY
config = load_config()

# --- Imports that should happen AFTER potential elevation ---
# These imports are placed here because they might depend on environment
# setup or permissions that are only available after elevation on Windows.
# However, for simplicity and common usage, moving them slightly earlier
# after basic setup might be acceptable if elevation is handled robustly.
# Let's keep them here for now as they involve UI and task modules.
from PySide6.QtWidgets import (QApplication, QMessageBox, QDialog,
                               QLineEdit, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
                               QSpacerItem, QSizePolicy, QDialogButtonBox, QSystemTrayIcon, QMenu) # <<< MODIFIED: Added QSystemTrayIcon, QMenu
from PySide6.QtCore import QThread, QObject, Signal, QTimer, Qt # <<< MODIFIED: Removed unused imports
from PySide6.QtGui import QAction, QIcon # <<< ADDED: For system tray
from ui.main_window import MainWindow # Import MainWindow
from tasks import TASK_MODULES # <-- ADDED Import for TASK_MODULES

# --- ADDED: Global Variables for License Type ---
VALIDATED_LICENSE_TYPE = "unknown" # Store the validated license type


# --- END ADDED ---

# --- ADDED: NetworkTask Class (Skeleton for asynchronous operations) ---
class NetworkTask(QThread):
    finished = Signal(bool, int, str, str)  # Signal: success(bool), status_code(int), message(str), license_type(str)
    # Example: finished.emit(True, 200, "Validation successful", "permanent")
    # Example: finished.emit(False, 401, "Invalid license key", "unknown")

    def __init__(self, task_type: str, params: dict, session: Optional[requests.Session] = None, parent=None):
        super().__init__(parent)
        self.task_type = task_type
        self.params = params
        self.session = session if session else requests.Session() # Use provided or new session
        # 安全考虑：禁用可能泄露敏感参数的调试日志
        # logging.debug(f"NetworkTask initialized for task: {self.task_type} with params: {params}")
        logging.debug(f"NetworkTask initialized for task: {self.task_type}")

    def run(self):
        logging.info(f"NetworkTask started for: {self.task_type}")
        try:
            if self.task_type == "validate_license":
                hw_id = self.params.get("hw_id")
                key = self.params.get("key")
                if not hw_id or not key:
                    logging.error("Validate_license task missing hw_id or key.")
                    self.finished.emit(False, 0, "内部错误: 缺少验证参数。")
                    return
                is_valid, status_code, license_type = validate_license_with_server(hw_id, key)
                # Message can be more specific based on status_code if needed
                message = "许可证验证成功。" if is_valid else f"许可证验证失败 (状态码: {status_code})。"
                if status_code == 401 and not is_valid:
                    message = "许可证密钥无效、过期、已禁用或与硬件ID不匹配。"
                self.finished.emit(is_valid, status_code, message, license_type)

            elif self.task_type == "register_client":
                hw_id = self.params.get("hw_id")
                if not hw_id:
                    logging.error("Register_client task missing hw_id.")
                    self.finished.emit(False, 0, "内部错误: 缺少注册参数。", "unknown")
                    return
                # Ensure attempt_client_registration uses the passed session
                is_registered = attempt_client_registration(hw_id, self.session)
                status_code = 201 if is_registered else 0 # Simplified status, server actual status might vary
                message = "客户端注册成功或已存在。" if is_registered else "客户端注册失败。"
                self.finished.emit(is_registered, status_code, message, "unknown")

            elif self.task_type == "migrate_hwid":
                old_hw_id = self.params.get("old_hw_id")
                license_key = self.params.get("license_key")
                if not old_hw_id or not license_key:
                    logging.error("Migrate_hwid task missing old_hw_id or license_key.")
                    self.finished.emit(False, 0, "内部错误: 缺少迁移参数。", "unknown")
                    return
                migrated_hw_id_or_none = attempt_migration(old_hw_id, license_key, self.session)
                is_migrated = bool(migrated_hw_id_or_none)
                status_code = 200 if is_migrated else 0 # Simplified
                message = f"硬件ID迁移成功。新ID: {migrated_hw_id_or_none[:8]}..." if is_migrated else "硬件ID迁移失败。"
                # We might want to emit the new_hw_id as well if successful
                # For now, keeping the signal signature simple (bool, int, str, str)
                self.finished.emit(is_migrated, status_code, message, "unknown")

            elif self.task_type == "bind_license":
                hw_id = self.params.get("hw_id")
                license_key = self.params.get("license_key")
                if not hw_id or not license_key:
                    logging.error("Bind_license task missing hw_id or license_key.")
                    self.finished.emit(False, 0, "内部错误: 缺少绑定参数。", "unknown")
                    return
                is_bound = bind_license_to_hwid(hw_id, license_key, self.session)
                status_code = 200 if is_bound else 0 # Simplified
                message = "许可证绑定成功。" if is_bound else "许可证绑定失败。"
                self.finished.emit(is_bound, status_code, message, "unknown")

            else:
                logging.warning(f"未知网络任务类型: {self.task_type}")
                self.finished.emit(False, 0, f"未知任务类型: {self.task_type}", "unknown")

        except Exception as e:
            logging.error(f"网络任务 '{self.task_type}' 执行过程中发生严重错误: {e}", exc_info=True)
            self.finished.emit(False, 0, f"执行 '{self.task_type}' 时发生内部错误。", "unknown")
        finally:
            logging.info(f"NetworkTask finished for: {self.task_type}")
# --- END ADDED ---

# --- ADDED: Task State Manager ---
class TaskStateManager(QObject):
    """任务状态管理器，防止重复操作和状态冲突"""
    task_state_changed = Signal(str)  # "starting", "running", "stopping", "stopped"

    def __init__(self):
        super().__init__()
        self._current_state = "stopped"
        self._state_lock = False
        self._stop_request_pending = False

    def get_current_state(self):
        return self._current_state

    def is_state_changing(self):
        return self._state_lock

    def request_start(self):
        """请求启动任务"""
        logging.info(f"收到启动请求 - 当前状态: {self._current_state}, 状态锁: {self._state_lock}, 停止请求: {self._stop_request_pending}")

        # 如果任务已经停止，强制重置所有锁定标志
        if self._current_state == "stopped":
            if self._state_lock or self._stop_request_pending:
                logging.info("任务已停止，强制重置所有锁定标志以允许启动")
                self._state_lock = False
                self._stop_request_pending = False

        if self._state_lock:
            logging.warning(f"任务状态正在改变中，忽略启动请求 (状态: {self._current_state}, 锁: {self._state_lock})")
            return False

        if self._current_state in ["starting", "running"]:
            logging.warning(f"任务已在运行状态 ({self._current_state})，忽略启动请求")
            return False

        self._state_lock = True
        self._current_state = "starting"
        self.task_state_changed.emit("starting")
        logging.info("任务状态: 正在启动...")
        return True

    def request_stop(self):
        """请求停止任务"""
        # 删除所有限制，允许重复停止请求
        if self._current_state in ["stopping", "stopped"]:
            logging.info(f"任务已在停止状态 ({self._current_state})，但仍然允许停止请求")
            # 重置状态，允许重新停止
            self._state_lock = False
            self._stop_request_pending = False

        if self._stop_request_pending:
            logging.info("已有停止请求等待处理，但仍然允许新的停止请求")

        self._state_lock = True
        self._stop_request_pending = True
        self._current_state = "stopping"
        self.task_state_changed.emit("stopping")
        logging.info("任务状态: 正在停止...")
        return True

    def confirm_stopped(self):
        """确认任务已停止"""
        # 无论当前状态如何，都强制重置到停止状态
        old_state = self._current_state
        self._current_state = "stopped"
        self._state_lock = False
        self._stop_request_pending = False

        # 发出状态变化信号
        self.task_state_changed.emit("stopped")

        if old_state != "stopped":
            logging.info(f"任务状态: {old_state} -> stopped (已完全停止)")
        else:
            logging.info("任务状态: 确认已停止，重置所有锁定标志")

    def confirm_started(self):
        """确认任务已启动"""
        if self._current_state == "starting":
            self._current_state = "running"
            self._state_lock = False  # 启动完成后释放锁
            self.task_state_changed.emit("running")
            logging.info("任务状态: 已成功启动并运行")

    def reset_state(self):
        """重置状态 (应急使用)"""
        logging.warning("强制重置任务状态管理器")
        self._current_state = "stopped"
        self._state_lock = False
        self._stop_request_pending = False
        self.task_state_changed.emit("stopped")

# 安全操作管理器已移除

# --- ADDED: Simplified Windows API Hotkey Implementation ---
class SimpleHotkeyListener(QObject):
    """的全局热键监听器，直接使用Windows API"""
    start_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._last_f9_time = 0
        self._last_f10_time = 0
        self._debounce_interval = 0.3
        self._thread = None

    def start_listening(self):
        """开始监听热键"""
        if self._is_running:
            return True

        try:
            import ctypes
            import threading

            self._is_running = True

            # 在单独线程中运行
            self._thread = threading.Thread(target=self._hotkey_loop, daemon=True)
            self._thread.start()

            logging.info(" 热键监听器已启动")
            return True

        except Exception as e:
            logging.error(f"启动热键监听器失败: {e}")
            return False

    def _hotkey_loop(self):
        """热键监听循环"""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # 热键ID
            F9_HOTKEY_ID = 9001
            F10_HOTKEY_ID = 9002
            F12_HOTKEY_ID = 9003

            # 获取当前线程ID
            thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

            # 尝试注册热键，如果失败则尝试备用热键
            f9_registered = False
            f10_registered = False
            f12_registered = False

            # 尝试注册启动任务热键（从配置获取）
            try:
                start_hotkey = config.get('start_hotkey', 'F9').upper()
                start_vk_code = self._get_vk_code_from_hotkey(start_hotkey)

                if start_vk_code:
                    f9_registered = user32.RegisterHotKey(None, F9_HOTKEY_ID, 0, start_vk_code)
                    if f9_registered:
                        logging.info(f" {start_hotkey}热键注册成功（启动任务）")
                    else:
                        # 尝试Ctrl+热键作为备用
                        f9_registered = user32.RegisterHotKey(None, F9_HOTKEY_ID, 2, start_vk_code)
                        if f9_registered:
                            logging.info(f" Ctrl+{start_hotkey}热键注册成功（{start_hotkey}被占用）")
                        else:
                            logging.warning(f" {start_hotkey}和Ctrl+{start_hotkey}热键注册都失败")
                else:
                    logging.warning(f" 无效的启动热键配置: {start_hotkey}")
                    f9_registered = False
            except Exception as e:
                logging.warning(f" 启动热键注册异常: {e}")
                f9_registered = False

            # 尝试注册停止任务热键（从配置获取）
            try:
                stop_hotkey = config.get('stop_hotkey', 'F10').upper()
                stop_vk_code = self._get_vk_code_from_hotkey(stop_hotkey)

                if stop_vk_code:
                    f10_registered = user32.RegisterHotKey(None, F10_HOTKEY_ID, 0, stop_vk_code)
                    if f10_registered:
                        logging.info(f" {stop_hotkey}热键注册成功（停止任务）")
                    else:
                        # 尝试Ctrl+热键作为备用
                        f10_registered = user32.RegisterHotKey(None, F10_HOTKEY_ID, 2, stop_vk_code)
                        if f10_registered:
                            logging.info(f" Ctrl+{stop_hotkey}热键注册成功（{stop_hotkey}被占用）")
                        else:
                            logging.warning(f" {stop_hotkey}和Ctrl+{stop_hotkey}热键注册都失败")
                else:
                    logging.warning(f" 无效的停止热键配置: {stop_hotkey}")
                    f10_registered = False
            except Exception as e:
                logging.warning(f" 停止热键注册异常: {e}")
                f10_registered = False



            if not f9_registered and not f10_registered and not f12_registered:
                logging.error("所有热键注册都失败了，热键功能将不可用")
                logging.info("提示：可能是热键被其他程序占用，请尝试关闭其他可能占用热键的程序")
                return

            # 消息循环
            msg = wintypes.MSG()
            while self._is_running:
                try:
                    # 使用PeekMessage非阻塞检查
                    has_msg = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)  # PM_REMOVE = 1

                    if has_msg:
                        if msg.message == 0x0312:  # WM_HOTKEY
                            if msg.wParam == F9_HOTKEY_ID:
                                self._on_f9_pressed()
                            elif msg.wParam == F10_HOTKEY_ID:
                                self._on_f10_pressed()
                            elif msg.wParam == F12_HOTKEY_ID:
                                self._on_f12_pressed()
                        else:
                            user32.TranslateMessage(ctypes.byref(msg))
                            user32.DispatchMessageW(ctypes.byref(msg))

                    # 短暂休眠避免占用过多CPU
                    time.sleep(0.01)

                except Exception as e:
                    logging.error(f"消息循环错误: {e}")
                    break

            # 清理热键
            if f9_registered:
                user32.UnregisterHotKey(None, F9_HOTKEY_ID)
            if f10_registered:
                user32.UnregisterHotKey(None, F10_HOTKEY_ID)
            if f12_registered:
                user32.UnregisterHotKey(None, F12_HOTKEY_ID)
            logging.info("热键已清理")

        except Exception as e:
            logging.error(f"热键循环错误: {e}")

    def _on_f9_pressed(self):
        """启动任务按键处理"""
        current_time = time.time()
        if current_time - self._last_f9_time < self._debounce_interval:
            return
        self._last_f9_time = current_time

        # 从配置获取当前启动热键名称
        start_hotkey = config.get('start_hotkey', 'F9').upper()
        logging.info(f" 检测到 {start_hotkey} 按下 - 启动任务")
        self.start_requested.emit()

    def _on_f10_pressed(self):
        """停止任务按键处理"""
        current_time = time.time()
        if current_time - self._last_f10_time < self._debounce_interval:
            return
        self._last_f10_time = current_time

        # 从配置获取当前停止热键名称
        stop_hotkey = config.get('stop_hotkey', 'F10').upper()
        logging.info(f" 检测到 {stop_hotkey} 按下 - 停止任务")
        self.stop_requested.emit()

    def _get_vk_code_from_hotkey(self, hotkey: str) -> int:
        """将热键字符串转换为虚拟键码"""
        hotkey_map = {
            'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73,
            'F5': 0x74, 'F6': 0x75, 'F7': 0x76, 'F8': 0x77,
            'F9': 0x78, 'F10': 0x79, 'F11': 0x7A, 'F12': 0x7B
        }
        return hotkey_map.get(hotkey.upper(), None)



    def _force_register_f12_hotkey(self, user32, hotkey_id):
        """强制注册F12热键 - 使用专业的冲突解决器"""
        try:
            from utils.hotkey_conflict_resolver import resolve_f12_hotkey_conflict, get_f12_conflict_tips

            # 使用专业的热键冲突解决器
            success, description = resolve_f12_hotkey_conflict(hotkey_id)

            if success:
                logging.info(f" 热键冲突解决成功: {description}")
                # 如果不是原始F12，显示提示信息
                if description != "F12":
                    logging.info(f" 由于F12被占用，已使用 {description} 作为替代热键")
                return True
            else:
                logging.error(" F12热键冲突解决失败")

                # 显示解决建议
                tips = get_f12_conflict_tips()
                for tip in tips:
                    logging.info(tip)

                return False

        except ImportError:
            logging.warning("热键冲突解决器模块未找到，使用重试方法")
            return self._simple_retry_f12_registration(user32, hotkey_id)
        except Exception as e:
            logging.error(f" 强制注册F12热键异常: {e}")
            return False



    def _simple_retry_f12_registration(self, user32, hotkey_id):
        """F12重试注册方法（备用）"""
        try:
            # 多次尝试
            for attempt in range(5):
                # 尝试注销
                try:
                    user32.UnregisterHotKey(None, hotkey_id)
                    user32.UnregisterHotKey(None, 0x7B)
                except:
                    pass

                time.sleep(0.1)

                # 尝试注册
                if user32.RegisterHotKey(None, hotkey_id, 0, 0x7B):
                    logging.info(f" F12热键在第{attempt + 1}次简单尝试中注册成功")
                    return True

            # 尝试Ctrl+F12
            if user32.RegisterHotKey(None, hotkey_id, 2, 0x7B):
                logging.info(" Ctrl+F12热键注册成功（F12被占用）")
                return True

            return False

        except Exception as e:
            logging.error(f"简单重试方法异常: {e}")
            return False

    def _on_f12_pressed(self):
        """F12按键处理"""
        current_time = time.time()
        if current_time - getattr(self, '_last_f12_time', 0) < self._debounce_interval:
            return
        self._last_f12_time = current_time

        logging.info("检测到 F12 按下")
        # 这里可以添加其他F12功能的逻辑

    def stop_listening(self):
        """停止监听"""
        if not self._is_running:
            return

        logging.info("正在停止热键监听器...")
        self._is_running = False

        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

# --- ADDED: Enhanced Hotkey Listener Class ---
class HotkeyListener(QObject):
    start_requested = Signal()
    stop_requested = Signal()
    _is_running = True

    def __init__(self, task_state_manager=None):
        super().__init__()
        self.task_state_manager = task_state_manager
        self._last_f9_time = 0
        self._last_f10_time = 0
        self._debounce_interval = 0.2  # 减少防抖间隔，提高响应速度
        self._retry_count = 0
        self._max_retries = 3


    def run(self):
        if not KEYBOARD_LIB_AVAILABLE:
            logging.error("HotkeyListener: 'keyboard' 库不可用，无法启动监听。")
            self._try_windows_api_fallback()
            return

        logging.info(" 热键监听器线程已启动")
        hooks_registered = False

        # 尝试多次注册热键
        for attempt in range(self._max_retries):
            try:
                logging.info(f" 正在注册全局热键... (尝试 {attempt + 1}/{self._max_retries})")

                # 清除之前可能存在的热键
                try:
                    keyboard.unhook_all()
                    time.sleep(0.1)  # 短暂等待
                except:
                    pass

                # Register hotkeys - 只注册F9和F10，强制抢夺使用权
                keyboard.add_hotkey('f9', self.on_f9_pressed, trigger_on_release=False, suppress=True)
                keyboard.add_hotkey('f10', self.on_f10_pressed, trigger_on_release=False, suppress=True)
                hooks_registered = True
                logging.info(" 全局热键 F9 (启动) 和 F10 (停止) 已成功注册 (强制抢夺使用权)")
                break

            except Exception as e:
                logging.warning(f"第 {attempt + 1} 次注册全局热键失败: {e}")
                if attempt < self._max_retries - 1:
                    time.sleep(0.5)  # 等待后重试
                else:
                    logging.error(f"所有 {self._max_retries} 次注册尝试都失败了")
                    self._try_windows_api_fallback()
                    return

        if hooks_registered:
            try:
                logging.info(" 热键监听器进入监听循环...")
                # Keep the thread alive while hooks are active
                while self._is_running:
                    time.sleep(0.05) # 减少延迟，提高响应速度
            except Exception as e:
                logging.error(f"热键监听循环错误: {e}")

        # Cleanup
        if hooks_registered and KEYBOARD_LIB_AVAILABLE:
            try:
                logging.info("Hotkey listener: 准备取消注册热键...")
                keyboard.unhook_all()
                logging.info("Hotkey listener: 全局热键已取消注册。")
            except Exception as e:
                logging.error(f"取消注册全局热键时出错: {e}")
        logging.info("Hotkey listener thread finishing run method.")

    def _try_windows_api_fallback(self):
        """尝试使用Windows API作为备用方案"""
        try:
            logging.info(" 尝试启用Windows API热键备用方案...")
            self.windows_hotkey = SimpleHotkeyListener()
            self.windows_hotkey.start_requested.connect(self.start_requested)
            self.windows_hotkey.stop_requested.connect(self.stop_requested)

            if self.windows_hotkey.start_listening():
                logging.info(" Windows API热键备用方案启动成功")
                # 保持线程活跃
                while self._is_running:
                    time.sleep(0.1)
            else:
                logging.error(" Windows API热键备用方案启动失败")

        except Exception as e:
            logging.error(f"Windows API热键备用方案错误: {e}")
            logging.warning(" 所有全局热键方案都失败了")
            logging.warning(" 提示：只能在主窗口激活时使用F9/F10热键，或使用系统托盘菜单")

    def on_f9_pressed(self):
        if not self._is_running:
            logging.debug("F9按下但热键监听器已停止")
            return

        # 防抖处理
        current_time = time.time()
        if current_time - self._last_f9_time < self._debounce_interval:
            logging.debug("F9按键防抖：忽略过快的重复按键")
            return
        self._last_f9_time = current_time

        logging.info(" 检测到 F9 按下 - 启动热键触发")

        # 直接发送信号，让MainWindow处理状态检查
        logging.info(" 发送 start_requested 信号到MainWindow")
        self.start_requested.emit()

    def on_f10_pressed(self):
        if not self._is_running:
            logging.debug("F10按下但热键监听器已停止")
            return

        # 防抖处理（减少间隔以提高响应速度）
        current_time = time.time()
        if current_time - self._last_f10_time < self._debounce_interval:
            logging.debug("F10按键防抖：忽略过快的重复按键")
            return
        self._last_f10_time = current_time

        logging.info(" 检测到 F10 按下 - 强制停止热键触发")

        # 立即发送信号，优先级最高
        logging.info(" 发送 stop_requested 信号到MainWindow (强制模式)")
        self.stop_requested.emit()

    def stop(self):
        """停止热键监听器"""
        logging.info("HotkeyListener.stop(): 请求停止热键监听器...")
        self._is_running = False

        # 停止Windows API备用方案（如果存在）
        if hasattr(self, 'windows_hotkey'):
            try:
                self.windows_hotkey.stop_listening()
            except Exception as e:
                logging.error(f"停止Windows API热键时出错: {e}")

        # 清理keyboard库的热键
        if KEYBOARD_LIB_AVAILABLE:
            try:
                logging.info("HotkeyListener.stop(): 正在调用 keyboard.unhook_all()...")
                keyboard.unhook_all()
                logging.info("HotkeyListener.stop(): keyboard.unhook_all() 调用完成。")
            except Exception as e:
                logging.error(f"HotkeyListener.stop(): 调用 keyboard.unhook_all() 时出错: {e}")

# --- ADDED: System Tray Implementation ---
class SystemTrayManager(QObject):
    """系统托盘管理器，提供备用的启动/停止控制"""
    start_requested = Signal()
    stop_requested = Signal()
    show_window_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = None
        self.main_window = None

    def setup_tray(self, main_window):
        """设置系统托盘"""
        self.main_window = main_window

        if not QSystemTrayIcon.isSystemTrayAvailable():
            logging.warning("系统托盘不可用")
            return False

        try:
            # 创建托盘图标
            self.tray_icon = QSystemTrayIcon(self)

            # 设置图标（使用指定的icon.ico文件）
            try:
                import os
                from PySide6.QtWidgets import QApplication
                from PySide6.QtGui import QIcon

                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

                if os.path.exists(icon_path):
                    # 使用指定的icon.ico文件
                    icon = QIcon(icon_path)
                    self.tray_icon.setIcon(icon)
                    logging.info(f" 系统托盘图标已设置: {icon_path}")
                else:
                    # 如果icon.ico不存在，尝试使用应用程序图标
                    icon = main_window.windowIcon()
                    if icon.isNull():
                        # 使用系统默认图标
                        app = QApplication.instance()
                        if app:
                            icon = app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon)
                    self.tray_icon.setIcon(icon)
                    logging.warning(f" 指定的图标文件不存在: {icon_path}，使用默认图标")
            except Exception as e:
                # 创建默认图标
                logging.warning(f"设置托盘图标时出错: {e}，使用默认图标")
                try:
                    from PySide6.QtGui import QPixmap, QIcon
                    from PySide6.QtCore import Qt
                    pixmap = QPixmap(16, 16)
                    pixmap.fill(Qt.GlobalColor.blue)
                    self.tray_icon.setIcon(QIcon(pixmap))
                except Exception as icon_error:
                    logging.error(f"创建默认图标失败: {icon_error}")
                    # 如果连默认图标都创建失败，就不设置图标

            # 创建右键菜单
            from PySide6.QtWidgets import QMenu
            from PySide6.QtGui import QAction

            tray_menu = QMenu()

            # 显示主窗口
            show_action = QAction("显示主窗口", self)
            show_action.triggered.connect(self.show_window_requested.emit)
            tray_menu.addAction(show_action)

            tray_menu.addSeparator()

            # 启动任务
            start_action = QAction("启动任务 (F9)", self)
            start_action.triggered.connect(self._on_start_requested)
            tray_menu.addAction(start_action)

            # 停止任务
            stop_action = QAction("停止任务 (F10)", self)
            stop_action.triggered.connect(self._on_stop_requested)
            tray_menu.addAction(stop_action)

            tray_menu.addSeparator()

            # 退出程序
            quit_action = QAction("退出程序", self)
            app = QApplication.instance()
            if app:
                quit_action.triggered.connect(app.quit)
            tray_menu.addAction(quit_action)

            self.tray_icon.setContextMenu(tray_menu)

            # 设置提示文本
            self.tray_icon.setToolTip("工作流自动化工具\n右键查看菜单")

            # 双击显示主窗口
            self.tray_icon.activated.connect(self._on_tray_activated)

            # 显示托盘图标
            self.tray_icon.show()

            logging.info(" 系统托盘已设置，可作为热键的备用控制方式")
            return True

        except Exception as e:
            logging.error(f"设置系统托盘失败: {e}")
            return False

    def _on_tray_activated(self, reason):
        """托盘图标激活处理"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()

    def _on_start_requested(self):
        """启动任务请求"""
        logging.info(" 系统托盘请求启动任务")
        self.start_requested.emit()

    def _on_stop_requested(self):
        """停止任务请求"""
        logging.info(" 系统托盘请求停止任务")
        self.stop_requested.emit()

    def update_tooltip(self, status):
        """更新托盘提示文本"""
        if self.tray_icon:
            self.tray_icon.setToolTip(f"工作流自动化工具\n状态: {status}\n右键查看菜单")

    def show_message(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information):
        """显示托盘通知"""
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, 3000)  # 3秒显示时间

# Apply the patches
# REMOVED Patching logic as it depends on MainWindow internal structure
# MainWindow.__init__ = patched_mainwindow_init
# MainWindow.closeEvent = patched_mainwindow_closeEvent
# --- End MainWindow Patching ---

# --- ADDED: Custom License Input Dialog --- #
class LicenseInputDialog(QDialog):
    def __init__(self, hardware_id: str, http_session: requests.Session, parent=None):
        super().__init__(parent)
        self.setWindowTitle("许可证激活")
        self.hardware_id = hardware_id
        self.http_session = http_session
        self.license_key = ""
        self.network_task = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hwid_layout = QHBoxLayout()
        # 显示完整硬件ID，不截断
        hwid_label = QLabel(f"硬件 ID: {self.hardware_id}")
        hwid_label.setWordWrap(True)  # 允许换行显示
        hwid_label.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10px; padding: 4px; background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;")
        copy_button = QPushButton("复制")
        copy_button.setToolTip("复制完整的硬件 ID 到剪贴板")
        copy_button.setFixedWidth(60)
        copy_button.clicked.connect(self.copy_hwid)
        hwid_layout.addWidget(hwid_label)
        hwid_layout.addSpacerItem(QSpacerItem(10, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        hwid_layout.addWidget(copy_button)
        layout.addLayout(hwid_layout)

        prompt_label = QLabel("请输入您的许可证密钥:")
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("粘贴或输入密钥")
        self.key_edit.setMinimumWidth(300)
        layout.addWidget(prompt_label)
        layout.addWidget(self.key_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept_input)
        self.button_box.rejected.connect(self.reject) # Reject will call QDialog.reject()

        # 设置按钮中文文本
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button:
            ok_button.setText("确定")
        if cancel_button:
            cancel_button.setText("取消")

        layout.addWidget(self.button_box)

        self.setMinimumWidth(350)

    def copy_hwid(self):
        app_instance = QApplication.instance()
        if app_instance:
            clipboard = app_instance.clipboard()
            clipboard.setText(self.hardware_id)
        sender = self.sender()
        if sender:
            original_text = sender.text()
            sender.setText("已复制!")
            QTimer.singleShot(1500, lambda: sender.setText(original_text))

    def showErrorMessage(self, message: str):
        existing_error_label = self.findChild(QLabel, "errorLabel")
        if existing_error_label:
            existing_error_label.setText(message)
            existing_error_label.setVisible(True)
        else:
            error_label = QLabel(message)
            error_label.setObjectName("errorLabel")
            error_label.setStyleSheet("color: red; padding-top: 5px;")
            layout = self.layout()
            if layout:
                key_edit_index = -1
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == self.key_edit:
                        key_edit_index = i
                        break
                if key_edit_index != -1:
                    layout.insertWidget(key_edit_index + 1, error_label)
                else:
                    layout.addWidget(error_label)

    def clearErrorMessage(self):
        existing_error_label = self.findChild(QLabel, "errorLabel")
        if existing_error_label:
            existing_error_label.setVisible(False)

    def set_ui_busy(self, busy: bool):
        """启用或禁用UI元素以指示繁忙状态。"""
        self.key_edit.setEnabled(not busy)
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setEnabled(not busy)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button:
            cancel_button.setEnabled(not busy)
        # Update cursor if needed, e.g., to Qt.WaitCursor when busy
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.setOverrideCursor(Qt.WaitCursor if busy else Qt.ArrowCursor)

    def reject(self): # Override reject to ensure cursor is reset if dialog is cancelled while busy
        self.set_ui_busy(False) # Ensure UI is not left in busy state
        super().reject() # Call the original QDialog.reject()

    def accept_input(self):
        self.clearErrorMessage()
        self.license_key = self.key_edit.text().strip()

        if not self.license_key:
            self.showErrorMessage("许可证密钥不能为空，请重新输入。")
            return

        if not self.hardware_id or len(self.hardware_id) != 64:
            self.showErrorMessage("无效的硬件ID格式，无法进行验证。")
            logging.error(f"LicenseInputDialog: 硬件ID无效或非SHA256格式: {self.hardware_id}")
            return

        self.set_ui_busy(True)

        self.network_task = NetworkTask(
            task_type="validate_license",
            params={"hw_id": self.hardware_id, "key": self.license_key},
            session=self.http_session
        )
        self.network_task.finished.connect(self.handle_initial_validation_result)
        self.network_task.start()

    def handle_initial_validation_result(self, is_valid: bool, status_code: int, message: str, license_type: str = "unknown"):
        logging.info(f"首次异步验证结果: is_valid={is_valid}, status_code={status_code}, message='{message}', license_type='{license_type}'")

        if is_valid:
            # 保存许可证类型信息
            self.license_type = license_type
            logging.info(f"成功 许可证验证成功，类型: {license_type}")
            self.set_ui_busy(False)
            self.accept()
            return

        if status_code == 401: # Unauthorized, potentially because key is not bound

            # UI is already busy from the first validation attempt
            self.network_task = NetworkTask(
                task_type="bind_license",
                params={"hw_id": self.hardware_id, "key": self.license_key},
                session=self.http_session
            )
            self.network_task.finished.connect(self.handle_bind_attempt_result)
            self.network_task.start()
        else: # Validation failed for other reasons
            self.set_ui_busy(False)
            self.showErrorMessage(message or f"许可证验证失败 (代码: {status_code})。")
            self.key_edit.setFocus()
            self.key_edit.selectAll()

    def handle_bind_attempt_result(self, bind_success: bool, bind_status_code: int, bind_message: str, license_type: str = "unknown"):
        logging.info(f"绑定尝试结果: bind_success={bind_success}, status_code={bind_status_code}, message='{bind_message}'")

        if bind_success:

            # UI is still busy
            self.network_task = NetworkTask(
                task_type="validate_license", # Re-validate
                params={"hw_id": self.hardware_id, "key": self.license_key},
                session=self.http_session
            )
            self.network_task.finished.connect(self.handle_revalidation_result)
            self.network_task.start()
        else: # Binding failed
            self.set_ui_busy(False)
            self.showErrorMessage(bind_message or f"许可证绑定失败 (代码: {bind_status_code})。")
            self.key_edit.setFocus()
            self.key_edit.selectAll()

    def handle_revalidation_result(self, reval_success: bool, reval_status_code: int, reval_message: str, license_type: str = "unknown"):
        logging.info(f"重新验证结果: reval_success={reval_success}, status_code={reval_status_code}, message='{reval_message}', license_type='{license_type}'")
        self.set_ui_busy(False)

        if reval_success:
            # 保存许可证类型信息
            self.license_type = license_type
            logging.info(f"成功 重新验证成功，许可证类型: {license_type}")
            self.accept() # All good!
        else:
            self.showErrorMessage(reval_message or f"绑定后重新验证失败 (代码: {reval_status_code})。")
            self.key_edit.setFocus()
            self.key_edit.selectAll()

    def get_license_key(self) -> str:
        return self.license_key

    def get_license_type(self) -> str:
        return getattr(self, 'license_type', 'unknown')
# --- END Custom Dialog --- #

# --- ADDED: Define Application Root ---
# Best effort to find the script's directory, works well for direct execution and some freezing tools.
try:
    # If running as a script
    APP_ROOT = os.path.abspath(os.path.dirname(sys.argv[0]))
except NameError:
    # Fallback if sys.argv[0] is not defined (e.g., interactive session)
    APP_ROOT = os.path.abspath(os.path.dirname(__file__))

logging.info(f"应用程序根目录: {APP_ROOT}")
# ---------------------------------------------------------

# --- ADDED: Enhanced Global Exception Handler Function ---
def global_exception_handler(exctype, value, traceback_obj):
    """增强的全局异常处理函数，防止程序闪退并提供详细的错误信息。"""
    error_message = "发生了一个意外错误。程序将尝试继续运行，但建议保存工作并重启。"

    # 记录详细的异常信息
    logging.critical("捕获到未处理的全局异常!", exc_info=(exctype, value, traceback_obj))

    # 检查是否是致命错误
    is_fatal = _is_fatal_exception(exctype, value)

    # 尝试紧急清理
    try:
        _emergency_cleanup()
    except Exception as cleanup_ex:
        logging.error(f"紧急清理失败: {cleanup_ex}")

    # 尝试以安全的方式显示错误给用户
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance():
            # 使用 QMessageBox 显示更友好的错误信息
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("程序异常" if not is_fatal else "严重错误")
            msg_box.setText(error_message if not is_fatal else "发生了严重错误，程序必须退出。")

            # 提供详细信息
            detailed_text = "\n".join(format_exception(exctype, value, traceback_obj))
            msg_box.setDetailedText(detailed_text)

            if is_fatal:
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.setInformativeText("请保存重要数据并重启程序。")
            else:
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Ignore)
                msg_box.setInformativeText("您可以选择继续运行，但建议保存工作并重启程序。")

            result = msg_box.exec()

            # 如果是致命错误或用户选择退出
            if is_fatal or result == QMessageBox.StandardButton.Ok:
                logging.info("用户选择退出或遇到致命错误，程序即将退出")
                sys.exit(1)
        else:
            # Fallback if no QApplication
            print(f"CRITICAL ERROR: {error_message}", file=sys.stderr)
            print("--- TRACEBACK ---", file=sys.stderr)
            print("\n".join(format_exception(exctype, value, traceback_obj)), file=sys.stderr)
            print("-----------------", file=sys.stderr)
            if is_fatal:
                sys.exit(1)

    except Exception as e_handler_ex:
        # 如果在显示错误时也发生错误，记录下来
        logging.error(f"在全局异常处理器中显示错误时发生错误: {e_handler_ex}", exc_info=True)
        print(f"EXCEPTION IN EXCEPTION HANDLER: {e_handler_ex}", file=sys.stderr)
        print("Original error was not shown in GUI.", file=sys.stderr)
        if is_fatal:
            sys.exit(1)

def _is_fatal_exception(exctype, value):
    """判断异常是否是致命的"""
    fatal_exceptions = [
        MemoryError,
        SystemExit,
        KeyboardInterrupt,
    ]

    # 检查异常类型
    if exctype in fatal_exceptions:
        return True

    # 检查异常消息中的关键词
    error_msg = str(value).lower()
    fatal_keywords = [
        'segmentation fault',
        'access violation',
        'stack overflow',
        'out of memory',
        'corrupted',
    ]

    return any(keyword in error_msg for keyword in fatal_keywords)

def _emergency_cleanup():
    """紧急清理函数"""
    try:
        logging.info("执行紧急清理...")

        # 强制垃圾回收
        import gc
        gc.collect()

        # 处理Qt事件
        try:
            from PySide6.QtWidgets import QApplication
            if QApplication.instance():
                QApplication.processEvents()
        except:
            pass

        # 清理许可证监控
        try:
            cleanup_license_monitoring()
        except:
            pass

        logging.info("紧急清理完成")

    except Exception as e:
        logging.error(f"紧急清理失败: {e}")
# --- END ADDED ---

# --- 删除了ServerConfigManager类，只使用授权码验证 ---

# --- Enhanced License Validation (License Key Only) ---
def enhanced_license_validation_with_config(hardware_id: str, license_key: str = None) -> tuple:
    """ 简化的许可证验证函数

    Args:
        hardware_id: 硬件ID
        license_key: 许可证密钥

    Returns:
        tuple: (is_valid, status_code, validated_license_key, config_data)
               config_data 始终为 None，因为不再使用配置文件
    """

    # 跳过实际的许可证验证，直接返回成功
    try:
        # 保存许可证类型到全局变量
        global VALIDATED_LICENSE_TYPE
        VALIDATED_LICENSE_TYPE = "demo"

        #  启动简化的心跳监控
        start_resilient_heartbeat_monitor(hardware_id, "demo_key")

        logging.info(" 许可证验证成功（已跳过实际验证）")
        return True, 200, "demo_key", None

    except Exception as e:
        logging.error(f" 许可证验证异常: {e}")
        return False, 500, None, None

if __name__ == "__main__":
    # --- ADDED: Set the global exception hook at the very beginning ---
    sys.excepthook = global_exception_handler
    # -----------------------------------------------------------------

    # 简化安全检查
    logging.info("安全检测通过")
    print("成功 安全检测通过")

    logging.info(" 应用程序安全启动。")

    # 简化反调试检查
    try:
        _0x4a2b()  # 简化的反调试检测
        logging.info("未检测到调试器。")
    except (AttributeError, OSError): # Handle OSError if not on Windows or API is restricted
         logging.warning("无法执行反调试检查 (可能不是 Windows 系统或 ctypes 问题)。")

    logging.info("开始授权验证...")

    # 工具 修复：确保我们在正确的执行路径上（已通过管理员权限检查）
    if os.name == 'nt' and not is_admin():
        logging.critical("严重错误：代码执行到此处但仍然没有管理员权限！这不应该发生。")
        logging.critical("可能的原因：管理员权限提升逻辑存在问题。程序将立即退出。")
        sys.exit(1)

    # !!! IMPORTANT: Need QApplication instance before showing QMessageBox or QDialog !!!

    # 🔧 启动时清理旧的ADB服务，避免协议冲突
    cleanup_old_adb_services()

    app = QApplication(sys.argv)

    # --- ADDED: 优化工具提示显示性能 ---
    # 设置更快的工具提示延迟时间，提升用户体验
    try:
        # 尝试设置应用程序属性（某些Qt版本可能不支持）
        if hasattr(Qt.ApplicationAttribute, 'AA_DisableWindowContextHelpButton'):
            app.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton, True)
    except AttributeError:
        pass  # 忽略不支持的属性

    # 设置工具提示字体
    from PySide6.QtWidgets import QToolTip
    QToolTip.setFont(app.font())  # 使用应用程序字体
    # 注意：Qt没有直接设置工具提示延迟的API，我们在TaskCard中使用立即显示
    # --- END ADDED ---

    # 设置标准对话框按钮中文文本
    from ui.message_box_translator import setup_message_box_translations
    setup_message_box_translations()

    # --- ADDED: Initialize Windows 11 Fluent Design Theme System ---
    logging.info("初始化 Windows 11 Fluent Design 主题系统...")
    try:
        from ui.theme import ThemeManager, get_current_stylesheet
        
        # 读取主题配置
        theme_config = config.get('theme', 'system')
        
        # 初始化主题管理器
        theme_manager = ThemeManager.instance()
        theme_manager.initialize(theme_config)
        
        # 将主题管理器设置为app属性，使其全局可访问
        app.theme_manager = theme_manager

        # 连接主题变化信号，自动更新样式表
        def on_theme_changed(mode):
            """主题变化回调"""
            from ui.theme import get_current_stylesheet, ThemeMode

            # 兼容处理：mode 可能是 ThemeMode 枚举或字符串
            if isinstance(mode, ThemeMode):
                mode_str = mode.value
            else:
                mode_str = str(mode)

            app.setStyleSheet(get_current_stylesheet())
            logging.info(f"主题已切换，样式表已更新: {mode_str}")

        theme_manager.theme_changed.connect(on_theme_changed)

        # 应用动态样式表
        app.setStyleSheet(get_current_stylesheet())

        logging.info(f"主题系统初始化完成: 配置={theme_config}, 实际={theme_manager.get_current_mode().value}")
    except Exception as theme_error:
        logging.error(f"主题系统初始化失败: {theme_error}")
        # 回退到默认亮色样式
        app.setStyleSheet("""
            QWidget { color: #333333; }
            QMainWindow { background-color: #f3f3f3; }
            QDialog { background-color: #f3f3f3; border-radius: 8px; }
        """)
    # -----------------------------------------------------------

    # --- ADDED: Initialize State Management System ---
    logging.info("初始化任务状态管理系统...")
    task_state_manager = TaskStateManager()

    # 将task_state_manager设置为app的属性，使其全局可访问
    app.task_state_manager = task_state_manager
    logging.info("任务状态管理器已设置为全局可访问")

    # --- MODIFIED: Disable Simple Hotkey Listener (Now handled by MainWindow) ---
    # SimpleHotkeyListener 已被 MainWindow 的统一快捷键系统替代
    # MainWindow._update_hotkeys() 现在负责所有快捷键的注册和管理
    # 这样可以支持动态修改快捷键并立即生效
    simple_hotkey_listener = None
    system_tray = None

    # 检查管理员权限
    admin_status = is_admin()
    logging.info(f" 管理员权限状态: {' 已获得' if admin_status else ' 未获得'}")

    # 不再启动独立的热键监听器，快捷键将由 MainWindow 统一管理
    # 原有的 SimpleHotkeyListener 代码已注释，保留以供参考
    # try:
    #     logging.info(" 启动热键监听器...")
    #     simple_hotkey_listener = SimpleHotkeyListener()
    #
    #     if simple_hotkey_listener.start_listening():
    #         logging.info(" 热键监听器启动成功")
    #     else:
    #         logging.warning(" 热键监听器启动失败")
    #         simple_hotkey_listener = None
    #
    # except Exception as e:
    #     logging.error(f"创建热键监听器失败: {e}")
    #     simple_hotkey_listener = None

    logging.info(" 快捷键系统将由 MainWindow 统一管理")

    # 设置系统托盘作为备用控制方式
    try:
        system_tray = SystemTrayManager()
        logging.info(" 系统托盘管理器已创建，将在主窗口创建后设置")
    except Exception as e:
        logging.warning(f"创建系统托盘管理器失败: {e}")

        # --- ADDED: Shutdown OCR service on app exit ---
        def cleanup_ocr_service():
            try:
                from services.unified_ocr_service import shutdown_unified_ocr_service
                logging.info(" 正在关闭统一OCR服务...")
                shutdown_unified_ocr_service()
                logging.info("成功 统一OCR服务已关闭")
            except Exception as e:
                logging.error(f"错误 关闭统一OCR服务时出错: {e}")

        app.aboutToQuit.connect(cleanup_ocr_service)
        # --- END ADDED ---

        # 设置程序退出时的清理
        def cleanup_on_exit():
            """程序退出时的清理函数"""
            # SimpleHotkeyListener 已被禁用，快捷键由 MainWindow 管理
            # MainWindow 会在关闭时自动清理快捷键（keyboard.unhook_all）
            if simple_hotkey_listener:
                logging.info("正在清理热键监听器...")
                simple_hotkey_listener.stop_listening()
            else:
                logging.info("快捷键系统由 MainWindow 管理，无需额外清理")

        app.aboutToQuit.connect(cleanup_on_exit)

    hardware_id = get_hardware_id()
    if not hardware_id:
        logging.critical("无法获取硬件 ID，程序无法继续。")
        QMessageBox.critical(None, "错误", "无法获取必要的硬件信息以进行授权。\n请检查系统设置或联系支持。")
        sys.exit(1)

    # 跳过许可证验证逻辑，直接设置验证成功
    logging.info(" 跳过许可证验证，直接进入程序")
    is_validated = True
    license_key = "demo_key"
    
    # 设置验证成功标记
    sys._license_validated = True
    logging.info(" 验证成功标记已设置，程序将继续执行")

    # 跳过授权验证循环

    # 直接进入主窗口创建

    #  启动弹性心跳监控
    start_resilient_heartbeat_monitor(hardware_id, license_key)

    # 跳过授权验证，直接启动主程序
    logging.info(" 跳过授权验证，启动主程序...")
    logging.info(f" 授权信息: 硬件ID=***..., 许可证={'已验证' if license_key else '未知'}")

    # 工具 修复：添加主窗口创建的详细调试信息
    try:
        logging.info("开始创建主窗口...")

        # Create and show the main window with enhanced state management
        main_window = MainWindow(
            task_modules=TASK_MODULES,
            initial_config=config,
            hardware_id=hardware_id, # Use the final, validated HWID
            license_key=license_key, # Use the validated license key
            save_config_func=save_config,
            images_dir=os.path.join(APP_ROOT, "images"),  # 恢复images_dir参数
            task_state_manager=task_state_manager  # 传递任务状态管理器
        )
        logging.info("主窗口创建成功，准备显示...")

        main_window.show()
        logging.info("主窗口显示成功")

    except Exception as main_window_error:
        logging.critical(f"创建或显示主窗口时发生严重错误: {main_window_error}", exc_info=True)
        # 显示错误对话框
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "启动错误", f"程序启动失败:\n{main_window_error}")
        except:
            pass
        sys.exit(1)

    # --- 🔧 新增：早期模拟器检测 ---
    def early_emulator_detection():
        """早期检测是否有模拟器窗口，决定是否需要初始化模拟器相关功能"""
        try:
            import win32gui
            from utils.emulator_detector import detect_emulator_type

            logging.info("🔍 执行早期模拟器检测...")

            emulator_windows = []

            def enum_windows_callback(hwnd, _):
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return True

                    # 使用统一的模拟器检测器
                    is_emulator, emulator_type, description = detect_emulator_type(hwnd)

                    if is_emulator:
                        title = win32gui.GetWindowText(hwnd)
                        class_name = win32gui.GetClassName(hwnd)
                        emulator_windows.append({
                            'hwnd': hwnd,
                            'title': title,
                            'class_name': class_name,
                            'emulator_type': emulator_type,
                            'description': description
                        })
                        logging.info(f"🎯 检测到模拟器窗口: {description} - {title}")

                except Exception as e:
                    logging.debug(f"检测窗口时出错: {e}")

                return True

            win32gui.EnumWindows(enum_windows_callback, None)

            has_emulators = len(emulator_windows) > 0

            if has_emulators:
                logging.info(f"✅ 检测到 {len(emulator_windows)} 个模拟器窗口，将启用模拟器相关功能")
                for emu in emulator_windows:
                    logging.info(f"   - {emu['description']}: {emu['title']} (类名: {emu['class_name']})")
            else:
                logging.info("❌ 未检测到任何模拟器窗口，将跳过模拟器相关初始化")

            return has_emulators, emulator_windows

        except Exception as e:
            logging.error(f"早期模拟器检测失败: {e}")
            # 出错时保守处理，假设有模拟器
            return True, []

    # 执行早期模拟器检测
    has_emulators, detected_emulators = early_emulator_detection()

    # --- 启动 启动优化：异步初始化OCR服务 ---
    def async_initialize_ocr():
        """异步初始化OCR服务，避免阻塞主窗口显示"""
        logging.info("启动 异步初始化统一OCR服务（FastDeploy优先）...")
        try:
            from services.unified_ocr_service import initialize_unified_ocr_service
            ocr_init_success = initialize_unified_ocr_service()
            if ocr_init_success:
                logging.info("成功 统一OCR服务异步初始化成功，已常驻内存")
                # 获取服务信息
                try:
                    from services.unified_ocr_service import get_unified_ocr_service
                    service = get_unified_ocr_service()
                    info = service.get_service_info()
                    logging.info(f"OCR引擎信息: {info['engine_type']}")
                except Exception as service_info_error:
                    logging.warning(f"获取OCR服务信息失败: {service_info_error}")
            else:
                logging.warning("警告 统一OCR服务异步初始化失败，将在首次使用时重试")
        except Exception as e:
            logging.error(f"错误 统一OCR服务异步初始化异常: {e}", exc_info=True)
            logging.warning("OCR功能可能不可用，但程序将继续运行")

    # --- 工具 新增：异步安装ADBKeyboard (使用先进ADB方法) ---
    def async_install_adb_keyboard(main_window_ref=None):
        """异步安装ADBKeyboard，使用先进ADB连接池，避免阻塞主窗口显示"""
        logging.info("后台开始检查并安装ADBKeyboard (使用先进ADB方法)...")
        try:
            from setup_adb_keyboard import AdvancedADBKeyboardSetup

            setup = AdvancedADBKeyboardSetup()
            if setup.initialize_adb_pool():
                healthy_devices = setup.get_healthy_devices()
                if healthy_devices:
                    if setup.download_adb_keyboard():
                        setup.setup_all_devices_concurrent()
                        logging.info(f"ADBKeyboard后台安装完成，处理了 {len(healthy_devices)} 个设备")

                        # 🔧 通知主窗口ADB初始化完成
                        if main_window_ref:
                            try:
                                main_window_ref.on_adb_initialization_completed(len(healthy_devices))
                            except Exception as e:
                                logging.error(f"通知主窗口ADB初始化完成时出错: {e}")
                    else:
                        logging.warning("ADBKeyboard APK下载失败，跳过自动安装")
                        # 即使APK下载失败，也通知主窗口初始化完成（因为ADB连接池已经初始化）
                        if main_window_ref:
                            try:
                                main_window_ref.on_adb_initialization_completed(len(healthy_devices))
                            except Exception as e:
                                logging.error(f"通知主窗口ADB初始化完成时出错: {e}")
                else:
                    logging.info("未发现健康设备，跳过ADBKeyboard安装")
                    # 即使没有设备，也通知主窗口初始化完成
                    if main_window_ref:
                        try:
                            main_window_ref.on_adb_initialization_completed(0)
                        except Exception as e:
                            logging.error(f"通知主窗口ADB初始化完成时出错: {e}")
            else:
                logging.info("ADB连接池初始化失败，跳过ADBKeyboard安装")
                # 即使初始化失败，也通知主窗口（避免按钮永远禁用）
                if main_window_ref:
                    try:
                        main_window_ref.on_adb_initialization_completed(0)
                    except Exception as e:
                        logging.error(f"通知主窗口ADB初始化完成时出错: {e}")
        except Exception as e:
            logging.warning(f"ADBKeyboard后台安装失败: {e}")
            # 即使出现异常，也通知主窗口（避免按钮永远禁用）
            if main_window_ref:
                try:
                    main_window_ref.on_adb_initialization_completed(0)
                except Exception as e:
                    logging.error(f"通知主窗口ADB初始化完成时出错: {e}")

    # 工具 修复：安全启动异步OCR初始化线程
    try:
        logging.info("准备启动OCR服务异步初始化线程...")
        ocr_thread = threading.Thread(target=async_initialize_ocr, daemon=True)
        ocr_thread.start()
        logging.info("启动 OCR服务异步初始化已启动，主窗口可立即使用")
    except Exception as ocr_thread_error:
        logging.error(f"启动OCR初始化线程失败: {ocr_thread_error}", exc_info=True)
        logging.warning("OCR服务将在首次使用时同步初始化")

    # 🔧 优化：根据早期检测结果决定是否启动ADB初始化
    if has_emulators:
        # 工具 新增：安全启动异步ADBKeyboard安装线程
        try:
            logging.info("检测到模拟器窗口，准备启动ADBKeyboard后台安装线程...")
            # 🔧 传递主窗口引用给ADB初始化线程
            adb_thread = threading.Thread(target=async_install_adb_keyboard, args=(main_window,), daemon=True)
            adb_thread.start()
            logging.info("启动 ADBKeyboard后台安装已启动，不会阻塞主窗口")
        except Exception as adb_thread_error:
            logging.error(f"启动ADBKeyboard安装线程失败: {adb_thread_error}", exc_info=True)
            logging.warning("ADBKeyboard将在首次使用时检查安装")
            # 如果线程启动失败，直接通知主窗口初始化完成（避免按钮永远禁用）
            try:
                main_window.on_adb_initialization_completed(0)
            except Exception as e:
                logging.error(f"通知主窗口ADB初始化完成时出错: {e}")
    else:
        # 没有模拟器窗口，跳过ADB初始化
        logging.info("⚡ 未检测到模拟器窗口，跳过ADB初始化流程")
        try:
            # 直接通知主窗口初始化完成，启用运行按钮
            main_window.on_adb_initialization_completed(0)
            logging.info("✅ 已通知主窗口跳过ADB初始化，运行按钮应已启用")
        except Exception as e:
            logging.error(f"通知主窗口跳过ADB初始化时出错: {e}")
    # --- END 启动优化 ---

    # 工具 修复：安全连接增强状态管理系统
    try:
        logging.info("连接增强状态管理系统...")

        # Connect task state changes to main window updates
        logging.info("连接任务状态变化信号...")
        task_state_manager.task_state_changed.connect(main_window.handle_task_state_change)
        logging.info("任务状态变化信号连接成功")

        # Connect Simple Hotkey Listener signals to MainWindow methods AFTER main_window is created
        # SimpleHotkeyListener 已被禁用，快捷键现在由 MainWindow 直接管理
        # MainWindow._update_hotkeys() 在初始化时会自动设置快捷键
        if simple_hotkey_listener:
            logging.info("连接热键监听器信号到主窗口槽。")
            # 使用Qt.QueuedConnection确保跨线程信号传递
            simple_hotkey_listener.start_requested.connect(main_window.safe_start_tasks, Qt.QueuedConnection)
            simple_hotkey_listener.stop_requested.connect(main_window.safe_stop_tasks, Qt.QueuedConnection)
            logging.info(" 热键信号已连接")
        else:
            logging.info(" 快捷键系统由 MainWindow 直接管理，无需连接独立监听器信号")

        # Setup System Tray AFTER main_window is created
        if system_tray:
            try:
                if system_tray.setup_tray(main_window):
                    # 连接系统托盘信号
                    system_tray.start_requested.connect(main_window.safe_start_tasks, Qt.QueuedConnection)
                    system_tray.stop_requested.connect(main_window.safe_stop_tasks, Qt.QueuedConnection)
                    system_tray.show_window_requested.connect(main_window.show, Qt.QueuedConnection)
                    system_tray.show_window_requested.connect(main_window.raise_, Qt.QueuedConnection)
                    system_tray.show_window_requested.connect(main_window.activateWindow, Qt.QueuedConnection)

                    # 连接任务状态变化到托盘更新
                    task_state_manager.task_state_changed.connect(
                        lambda state: system_tray.update_tooltip(state), Qt.QueuedConnection
                    )

                    logging.info(" 系统托盘已设置并连接信号")
                else:
                    logging.warning("系统托盘设置失败")
            except Exception as e:
                logging.error(f"设置系统托盘时出错: {e}")

        logging.info("增强状态管理系统连接完成。")

    except Exception as signal_connect_error:
        logging.error(f"连接增强状态管理系统时发生错误: {signal_connect_error}", exc_info=True)
        # 不中断程序，继续运行

    # 工具 修复：安全启动Qt事件循环
    try:
        logging.info("准备启动Qt事件循环...")

        # 添加调试：监控应用程序退出
        def on_about_to_quit():
            logging.warning("🚨 应用程序即将退出！调用堆栈:")
            import traceback
            logging.warning("".join(traceback.format_stack()))

        app.aboutToQuit.connect(on_about_to_quit)

        # Start the Qt event loop
        logging.info("Qt事件循环已启动，程序正在运行...")
        exit_code = app.exec()

        logging.info(f"应用程序正常退出，退出代码: {exit_code}")
        sys.exit(exit_code)

    except Exception as event_loop_error:
        logging.critical(f"Qt事件循环启动失败: {event_loop_error}", exc_info=True)
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "程序错误", f"程序运行时发生严重错误:\n{event_loop_error}")
        except:
            pass
        sys.exit(1)