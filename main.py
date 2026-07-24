"""
GitHub 加速器 - 主程序
使用公共 DNS 解析 GitHub 域名，通过 hosts 文件加速访问
"""

import argparse
import ctypes
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from resolver import resolve_all_domains, test_ip_latency, GITHUB_DOMAINS
from hosts_manager import (
    backup_hosts,
    get_current_entries,
    get_hosts_path,
    is_admin,
    read_hosts,
    remove_accelerator_entries,
    write_hosts,
)

# 配置文件路径
CONFIG_DIR = Path.home() / ".github-accelerator"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "cf_worker_url": "",  # Cloudflare Worker URL
    "auto_refresh": True,
    "refresh_interval": 3600,  # 秒（1小时）
    "last_update": None,
    "last_ips": {},
}


def load_config() -> dict:
    """加载配置文件"""
    CONFIG_DIR.mkdir(exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """保存配置文件"""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def do_accelerate(config: dict) -> Dict[str, str]:
    """
    执行加速：解析域名 -> 测试延迟 -> 更新 hosts
    返回 {域名: IP} 映射
    """
    cf_worker_url = config.get("cf_worker_url") or None

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始解析 GitHub 域名...")

    # 解析所有域名
    results = resolve_all_domains(cf_worker_url)

    # 收集所有候选 IP
    ip_map = {}
    all_candidates = []

    for domain, result in results.items():
        if result.best_ip:
            ip_map[domain] = result.best_ip
            for ip_info in result.all_ips:
                if ip_info.ip not in [c[0] for c in all_candidates]:
                    all_candidates.append((ip_info.ip, ip_info.latency_ms, ip_info.source))
            print(f"  ✓ {domain} -> {result.best_ip} (来自 {result.all_ips[0].source if result.all_ips else 'N/A'})")
        else:
            print(f"  ✗ {domain} -> 解析失败")

    if not ip_map:
        print("错误：未能解析任何域名")
        return {}

    # 测试实际连接延迟并选择最优 IP
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 测试实际连接延迟...")

    # 对每个域名找最快的 IP
    final_map = {}
    for domain in GITHUB_DOMAINS:
        if domain in ip_map:
            # 收集该域名的所有候选 IP
            domain_result = results.get(domain)
            if domain_result and domain_result.all_ips:
                candidate_ips = [ip_info.ip for ip_info in domain_result.all_ips[:5]]  # 测试前5个
                test_results = []
                for ip in candidate_ips:
                    latency = test_ip_latency(ip, 443)
                    if latency:
                        test_results.append((ip, latency))

                if test_results:
                    test_results.sort(key=lambda x: x[1])
                    best_ip = test_results[0][0]
                    final_map[domain] = best_ip
                    print(f"  ✓ {domain} -> {best_ip} (延迟: {test_results[0][1]:.1f}ms)")
                else:
                    final_map[domain] = ip_map[domain]
                    print(f"  ? {domain} -> {ip_map[domain]} (无法测试延迟，使用 DNS 结果)")
            else:
                final_map[domain] = ip_map[domain]

    # 写入 hosts 文件
    if final_map:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 写入 hosts 文件...")
        backup_hosts()
        write_hosts(final_map)
        print("  ✓ hosts 文件已更新")

        # 更新配置
        config["last_update"] = datetime.now().isoformat()
        config["last_ips"] = final_map
        save_config(config)

    return final_map


def request_admin():
    """请求管理员权限重新运行"""
    if sys.platform == "win32":
        try:
            script = sys.argv[0]
            params = " ".join(sys.argv[1:])
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}" {params}', None, 1
            )
            sys.exit(0)
        except Exception:
            print("需要管理员权限才能修改 hosts 文件")
            sys.exit(1)
    else:
        print("请使用 sudo 运行此程序")
        sys.exit(1)


def main_cli():
    """命令行模式"""
    parser = argparse.ArgumentParser(description="GitHub 加速器")
    parser.add_argument("--cf-worker", help="Cloudflare Worker URL")
    parser.add_argument("--disable", action="store_true", help="禁用加速")
    parser.add_argument("--daemon", action="store_true", help="后台模式（每小时自动刷新）")
    args = parser.parse_args()

    # 检查管理员权限
    if not is_admin():
        print("需要管理员权限，正在请求提升权限...")
        request_admin()

    config = load_config()
    if args.cf_worker:
        config["cf_worker_url"] = args.cf_worker
        save_config(config)

    if args.disable:
        print("正在禁用加速...")
        remove_accelerator_entries()
        print("已移除 hosts 条目")
        return

    if args.daemon:
        print("后台模式启动，每小时自动刷新")
        while True:
            try:
                do_accelerate(config)
            except Exception as e:
                print(f"加速失败: {e}")
            time.sleep(config.get("refresh_interval", 3600))
    else:
        do_accelerate(config)


def main_gui():
    """图形界面模式"""
    # 检查管理员权限
    if not is_admin():
        print("需要管理员权限，正在请求提升权限...")
        request_admin()

    config = load_config()

    # 导入 GUI 模块
    from gui import GitHubAcceleratorGUI

    # 自动刷新线程
    auto_refresh_running = threading.Event()
    auto_refresh_running.set()

    def on_refresh():
        """刷新回调"""
        try:
            gui.update_status("正在加速...")
            result = do_accelerate(config)
            if result:
                gui.update_status("已启用")
                gui.update_last_time(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                gui.update_entries_display(result)
            else:
                gui.update_status("加速失败")
        except Exception as e:
            gui.update_status("错误")
            print(f"错误: {e}")

    def on_disable():
        """禁用回调"""
        remove_accelerator_entries()
        gui.update_entries_display({})

    def on_enable():
        """启用回调"""
        on_refresh()

    def auto_refresh_loop():
        """自动刷新循环"""
        while auto_refresh_running.is_set():
            # 等待 1 小时
            for _ in range(3600):
                if not auto_refresh_running.is_set():
                    return
                time.sleep(1)

            if gui.auto_refresh_var.get():
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 自动刷新...")
                on_refresh()

    # 创建 GUI
    gui = GitHubAcceleratorGUI(
        on_refresh=on_refresh,
        on_disable=on_disable,
        on_enable=on_enable,
    )

    # 启动自动刷新线程
    refresh_thread = threading.Thread(target=auto_refresh_loop, daemon=True)
    refresh_thread.start()

    # 显示上次的条目
    last_ips = config.get("last_ips", {})
    if last_ips:
        gui.update_entries_display(last_ips)
        gui.update_status("已启用")
        last_update = config.get("last_update")
        if last_update:
            try:
                dt = datetime.fromisoformat(last_update)
                gui.update_last_time(dt.strftime("%Y-%m-%d %H:%M:%S"))
            except Exception:
                pass

    print("GitHub 加速器已启动")
    print(f"Hosts 文件: {get_hosts_path()}")
    if config.get("cf_worker_url"):
        print(f"Cloudflare Worker: {config['cf_worker_url']}")
    print()

    # 启动时自动加速
    threading.Thread(target=on_refresh, daemon=True).start()

    # 运行 GUI
    try:
        gui.run()
    finally:
        auto_refresh_running.clear()


if __name__ == "__main__":
    # 如果有 --gui 参数或在 Windows 上双击运行，使用 GUI 模式
    if "--gui" in sys.argv or (sys.platform == "win32" and len(sys.argv) == 1):
        # 移除 --gui 参数避免 argparse 报错
        sys.argv = [arg for arg in sys.argv if arg != "--gui"]
        main_gui()
    else:
        main_cli()
