# -*- coding: utf-8 -*-
"""
主题系统调试脚本
用于检查主题系统是否正常工作
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_config():
    """检查配置文件"""
    print("=" * 60)
    print("检查配置文件")
    print("=" * 60)
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        theme_config = config.get('theme', 'system')
        print(f"[OK] 配置文件读取成功")
        print(f"  theme 配置: {theme_config}")
        return theme_config
    except Exception as e:
        print(f"[FAIL] 配置文件读取失败: {e}")
        return None

def check_theme_files():
    """检查主题文件是否存在"""
    print("\n" + "=" * 60)
    print("检查主题文件")
    print("=" * 60)
    theme_dir = os.path.join(os.path.dirname(__file__), 'ui', 'theme')
    files = ['__init__.py', 'fluent_colors.py', 'theme_manager.py', 'stylesheet_builder.py']

    all_exist = True
    for file in files:
        file_path = os.path.join(theme_dir, file)
        if os.path.exists(file_path):
            print(f"[OK] {file} 存在")
        else:
            print(f"[FAIL] {file} 不存在")
            all_exist = False

    return all_exist

def check_stylesheet_generation():
    """检查样式表生成"""
    print("\n" + "=" * 60)
    print("检查样式表生成")
    print("=" * 60)
    try:
        from ui.theme import ThemeManager, get_current_stylesheet, ThemeMode

        # 初始化主题管理器
        tm = ThemeManager.instance()
        tm.initialize('dark')

        # 获取样式表
        stylesheet = get_current_stylesheet()

        print(f"[OK] 样式表生成成功")
        print(f"  样式表长度: {len(stylesheet)} 字符")
        print(f"  当前主题: {tm.get_current_mode().value}")

        # 检查关键样式
        checks = [
            ('QMainWindow', '主窗口样式'),
            ('background', '背景色'),
            ('QButton', '按钮样式'),
            ('QLineEdit', '输入框样式'),
        ]

        for keyword, desc in checks:
            if keyword in stylesheet:
                print(f"  [OK] 包含 {desc}")
            else:
                print(f"  [FAIL] 缺少 {desc}")

        return True
    except ImportError as e:
        print(f"[FAIL] 导入主题模块失败: {e}")
        print("  提示: 需要安装 PySide6")
        return False
    except Exception as e:
        print(f"[FAIL] 样式表生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_color_palette():
    """检查配色方案"""
    print("\n" + "=" * 60)
    print("检查配色方案")
    print("=" * 60)
    try:
        from ui.theme import ThemeManager, ThemeMode

        tm = ThemeManager.instance()

        # 检查暗色模式
        tm.set_theme(ThemeMode.DARK)
        dark_colors = tm.get_palette()
        print(f"[OK] 暗色模式配色:")
        print(f"  背景: {dark_colors.get('background')}")
        print(f"  表面: {dark_colors.get('surface')}")
        print(f"  文字: {dark_colors.get('text_primary')}")
        print(f"  主色: {dark_colors.get('primary')}")

        # 检查明亮模式
        tm.set_theme(ThemeMode.LIGHT)
        light_colors = tm.get_palette()
        print(f"\n[OK] 明亮模式配色:")
        print(f"  背景: {light_colors.get('background')}")
        print(f"  表面: {light_colors.get('surface')}")
        print(f"  文字: {light_colors.get('text_primary')}")
        print(f"  主色: {light_colors.get('primary')}")

        # 验证两种模式不同
        if dark_colors['background'] != light_colors['background']:
            print(f"\n[OK] 明暗模式配色不同")
        else:
            print(f"\n[FAIL] 明暗模式配色相同（错误）")

        return True
    except Exception as e:
        print(f"[FAIL] 配色方案检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有检查"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 18 + "主题系统调试" + " " * 32 + "║")
    print("╚" + "═" * 58 + "╝")

    results = []

    # 运行检查
    theme_config = check_config()
    results.append(("配置文件", theme_config is not None))

    results.append(("主题文件", check_theme_files()))

    # 只有在前两项都通过时才继续
    if all(r[1] for r in results):
        results.append(("样式表生成", check_stylesheet_generation()))
        results.append(("配色方案", check_color_palette()))
    else:
        print("\n⚠️  前置检查未通过，跳过后续检查")

    # 汇总结果
    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "通过" if result else "失败"
        print(f"  {test_name}: {status}")

    print(f"\n总计: {passed}/{total} 检查通过")

    if passed == total:
        print("\n[OK] 所有检查通过！主题系统应该可以正常工作。")
        print("\n下一步:")
        print("  1. 运行程序: python main.py")
        print("  2. 在全局设置中切换主题")
        print("  3. 检查界面颜色是否变化")
        return 0
    else:
        print(f"\n[FAIL] 有 {total - passed} 个检查失败，请根据上述信息排查问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
