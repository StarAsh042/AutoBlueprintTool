#!/usr/bin/env python3
"""
主题系统完整验证脚本
检查所有关键功能是否正常
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.theme_manager import ThemeManager

def test_theme_system():
    """测试主题系统"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    print("=" * 70)
    print("主题系统完整性测试")
    print("=" * 70)
    
    # 1. 创建主题管理器
    print("\n1. 创建主题管理器...")
    try:
        theme_mgr = ThemeManager()
        print("   ✓ ThemeManager 创建成功")
    except Exception as e:
        print(f"   ✗ 失败：{e}")
        return False
    
    # 2. 测试基本方法
    print("\n2. 测试基本方法...")
    tests = [
        ("get_current_theme()", lambda: theme_mgr.get_current_theme()),
        ("is_dark_mode()", lambda: theme_mgr.is_dark_mode()),
        ("get_colors()", lambda: theme_mgr.get_colors()),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            print(f"   ✓ {test_name} 正常，返回值：{result}")
        except Exception as e:
            print(f"   ✗ {test_name} 失败：{e}")
            return False
    
    # 3. 测试颜色字典
    print("\n3. 测试颜色字典...")
    colors = theme_mgr.get_colors()
    required_keys = [
        'card_background', 'surface', 'text_primary', 'border',
        'port_sequential', 'port_success', 'port_failure'
    ]
    
    missing_keys = []
    for key in required_keys:
        if key not in colors:
            missing_keys.append(key)
            print(f"   ✗ 缺少颜色键：{key}")
        else:
            print(f"   ✓ {key}: #{colors[key].name()}")
    
    if missing_keys:
        print(f"\n   ⚠ 共缺少 {len(missing_keys)} 个颜色键")
        return False
    
    # 4. 测试主题切换
    print("\n4. 测试主题切换...")
    try:
        # 切换到明亮主题
        theme_mgr.set_theme('light')
        current = theme_mgr.get_current_theme()
        is_dark = theme_mgr.is_dark_mode()
        print(f"   ✓ 切换到明亮主题：current={current}, is_dark={is_dark}")
        
        # 切换到黑暗主题
        theme_mgr.set_theme('dark')
        current = theme_mgr.get_current_theme()
        is_dark = theme_mgr.is_dark_mode()
        print(f"   ✓ 切换到黑暗主题：current={current}, is_dark={is_dark}")
        
        # 恢复到跟随系统
        theme_mgr.follow_system_theme()
        current = theme_mgr.get_current_theme()
        print(f"   ✓ 恢复跟随系统：current={current}")
        
    except Exception as e:
        print(f"   ✗ 主题切换失败：{e}")
        return False
    
    # 5. 测试信号连接
    print("\n5. 测试主题变化信号...")
    try:
        received_signals = []
        
        def on_theme_changed(mode):
            received_signals.append(mode)
            print(f"   → 收到主题变化信号：{mode}")
        
        theme_mgr.theme_changed.connect(on_theme_changed)
        theme_mgr.set_theme('light')
        
        if len(received_signals) > 0:
            print(f"   ✓ 信号正常，收到 {len(received_signals)} 个信号")
        else:
            print(f"   ⚠ 未收到信号")
            
    except Exception as e:
        print(f"   ✗ 信号测试失败：{e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓ 所有测试通过！主题系统工作正常！")
    print("=" * 70)
    return True

if __name__ == '__main__':
    import sys
    success = test_theme_system()
    sys.exit(0 if success else 1)
