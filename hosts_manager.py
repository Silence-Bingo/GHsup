"""
GitHub 加速器 - Hosts 文件管理模块
管理 hosts 文件的读取、备份、写入
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# 标记注释，用于识别加速器添加的内容
MARKER_BEGIN = "# >>> GitHub Accelerator Begin"
MARKER_END = "# <<< GitHub Accelerator End"

# Windows hosts 文件路径
HOSTS_PATH = Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32" / "drivers" / "etc" / "hosts"

# Linux/Mac hosts 文件路径
if os.name != "nt":
    HOSTS_PATH = Path("/etc/hosts")


def get_hosts_path() -> Path:
    """获取 hosts 文件路径"""
    return HOSTS_PATH


def is_admin() -> bool:
    """检查是否有管理员权限"""
    try:
        if os.name == "nt":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False


def backup_hosts() -> Optional[Path]:
    """备份 hosts 文件，返回备份文件路径"""
    if not HOSTS_PATH.exists():
        return None

    backup_dir = HOSTS_PATH.parent / "hosts_backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"hosts_{timestamp}.bak"

    shutil.copy2(HOSTS_PATH, backup_path)
    return backup_path


def read_hosts() -> str:
    """读取 hosts 文件内容"""
    if not HOSTS_PATH.exists():
        return ""
    try:
        with open(HOSTS_PATH, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except PermissionError:
        raise PermissionError("没有权限读取 hosts 文件，请以管理员身份运行")


def parse_existing_hosts(content: str) -> str:
    """
    解析 hosts 文件，移除加速器之前添加的内容
    返回清理后的内容
    """
    lines = content.split("\n")
    result = []
    skip = False

    for line in lines:
        if line.strip() == MARKER_BEGIN:
            skip = True
            continue
        elif line.strip() == MARKER_END:
            skip = False
            continue
        elif not skip:
            result.append(line)

    return "\n".join(result)


def generate_hosts_entries(ip_map: Dict[str, str]) -> str:
    """
    生成 hosts 条目
    ip_map: {域名: IP地址}
    """
    lines = [MARKER_BEGIN]
    lines.append(f"# GitHub Accelerator - 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for domain, ip in ip_map.items():
        if ip:
            lines.append(f"{ip}\t{domain}")

    lines.append(MARKER_END)
    return "\n".join(lines)


def write_hosts(ip_map: Dict[str, str]) -> bool:
    """
    写入 hosts 文件
    ip_map: {域名: IP地址}
    返回是否成功
    """
    try:
        # 读取现有内容
        original_content = read_hosts()

        # 移除旧的加速器内容
        clean_content = parse_existing_hosts(original_content)

        # 生成新条目
        new_entries = generate_hosts_entries(ip_map)

        # 合并内容
        final_content = clean_content.rstrip("\n") + "\n\n" + new_entries + "\n"

        # 写入文件（使用临时文件确保原子性）
        temp_fd, temp_path = tempfile.mkstemp(
            dir=HOSTS_PATH.parent,
            prefix="hosts_",
            suffix=".tmp"
        )
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(final_content)

            # 备份原文件
            backup_hosts()

            # 替换原文件
            shutil.move(temp_path, HOSTS_PATH)
        except Exception:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

        return True

    except PermissionError:
        raise PermissionError("没有权限写入 hosts 文件，请以管理员身份运行")
    except Exception as e:
        raise Exception(f"写入 hosts 文件失败: {e}")


def remove_accelerator_entries() -> bool:
    """
    移除加速器添加的 hosts 条目
    """
    try:
        content = read_hosts()
        clean_content = parse_existing_hosts(content)

        with open(HOSTS_PATH, "w", encoding="utf-8") as f:
            f.write(clean_content)

        return True
    except Exception as e:
        raise Exception(f"移除 hosts 条目失败: {e}")


def get_current_entries() -> Dict[str, str]:
    """
    获取当前加速器添加的 hosts 条目
    返回 {域名: IP}
    """
    content = read_hosts()
    entries = {}
    in_marker = False

    for line in content.split("\n"):
        line = line.strip()
        if line == MARKER_BEGIN:
            in_marker = True
            continue
        elif line == MARKER_END:
            in_marker = False
            continue
        elif in_marker and line and not line.startswith("#"):
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith("#"):
                ip, domain = parts[0], parts[1]
                entries[domain] = ip

    return entries
