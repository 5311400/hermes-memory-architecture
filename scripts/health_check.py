#!/usr/bin/env python3
"""
Hermes 健康看板 — 只查真实存在的东西
用法: python3 health_check.py [--json]
"""

import os
import sys
import json
import subprocess
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
MEMORIES_DIR = HERMES_HOME / "memories"
DIARY_DIR = HERMES_HOME / "日记"
LOG_DIR = HERMES_HOME / "logs"
SCRIPTS_DIR = HERMES_HOME / "scripts"
SKILLS_DIR = HERMES_HOME / "skills"
PLUGINS_DIR = HERMES_HOME / "plugins"
CONFIG = HERMES_HOME / "config.yaml"
ENV_FILE = HERMES_HOME / ".env"


def count_files(directory, pattern="*", recursive=False):
    """统计目录下文件数"""
    if not directory.exists():
        return 0
    if recursive:
        return len(list(directory.rglob(pattern)))
    return len(list(directory.glob(pattern)))


def count_scripts():
    """统计 .py + .sh 脚本数"""
    total = 0
    for ext in ("*.py", "*.sh", "*.mjs"):
        total += count_files(SCRIPTS_DIR, ext)
    return total


def dir_size_mb(directory):
    """目录大小 (MB)"""
    if not directory.exists():
        return 0
    try:
        result = subprocess.run(
            ["du", "-sm", str(directory)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return int(result.stdout.split()[0])
    except:
        pass
    return 0


def get_memory_usage():
    """MEMORY 和 USER 存储的字符数"""
    memory_path = MEMORIES_DIR / "MEMORY.md"
    user_path = MEMORIES_DIR / "USER.md"
    result = {"memory_chars": 0, "user_chars": 0}
    for key, path in [("memory_chars", memory_path), ("user_chars", user_path)]:
        if path.exists():
            result[key] = len(path.read_text(encoding="utf-8", errors="ignore"))
    return result


def get_disk_usage():
    """~/.hermes 所在分区磁盘使用"""
    try:
        result = subprocess.run(
            ["df", str(HERMES_HOME)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                # Termux df: Filesystem 1K-blocks Used Available Use% Mounted
                parts = lines[1].split()
                # Find the percentage column (contains %)
                pct = "?"
                total_kb = 0
                used_kb = 0
                free_kb = 0
                for i, p in enumerate(parts):
                    if "%" in p:
                        pct = p
                        if i >= 3:
                            total_kb = int(parts[i-3])
                            used_kb = int(parts[i-2])
                            free_kb = int(parts[i-1])
                return {
                    "total_mb": total_kb // 1024,
                    "used_mb": used_kb // 1024,
                    "free_mb": free_kb // 1024,
                    "percent": pct,
                }
    except:
        pass
    return {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent": "?"}


def check_port(port, host="127.0.0.1"):
    """检查端口是否可达"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except:
        return False


def get_bridge_count():
    """MemOS 桥进程数量"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "node.*memos.*bridge"],
            capture_output=True, text=True
        )
        pids = [p for p in result.stdout.strip().split() if p]
        return len(pids)
    except:
        return 0


def get_gateway_status():
    """检查网关进程"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "hermes.*gateway"],
            capture_output=True, text=True
        )
        pids = [p for p in result.stdout.strip().split() if p]
        return len(pids)
    except:
        return 0


def get_config_models():
    """读取当前配置的模型"""
    if not CONFIG.exists():
        return "未知"
    try:
        content = CONFIG.read_text(encoding="utf-8")
        models = []
        for line in content.split("\n"):
            line = line.strip()
            if "model:" in line and not line.startswith("#"):
                val = line.split("model:")[1].strip().strip('"').strip("'")
                if val and val not in ("{}", "[]"):
                    models.append(val)
        return ", ".join(models[:3]) if models else "未配置"
    except:
        return "读取失败"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes 健康看板")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    data = {
        "hermes_size_mb": dir_size_mb(HERMES_HOME),
        "disk": get_disk_usage(),
        "memory": get_memory_usage(),
        "models": get_config_models(),
        "gateway": {"processes": get_gateway_status()},
        "memos_bridge": {"processes": get_bridge_count()},
        "memos_port_18800": check_port(18800),
        "sidecar_port_8765": check_port(8765),
        "diary": {"count": count_files(DIARY_DIR, "*.md")},
        "skills": {"count": count_files(SKILLS_DIR, "SKILL.md", recursive=True)},
        "plugins": {"count": count_files(PLUGINS_DIR)},
        "scripts": {"count": count_scripts()},
        "logs": {"size_mb": dir_size_mb(LOG_DIR)},
        "config": {"exists": CONFIG.exists(), "env_exists": ENV_FILE.exists()},
    }

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("╔══════════════════════════════════════════╗")
        print("║       Hermes 记忆健康看板               ║")
        print("╚══════════════════════════════════════════╝")
        print()
        d = data["disk"]
        print(f"  💾 ~/.hermes 大小  : {data['hermes_size_mb']} MB")
        print(f"  💾 磁盘剩余       : {d.get('free_mb', '?')} MB / {d.get('total_mb', '?')} MB ({d.get('percent', '?')} 已用)")
        print()
        m = data["memory"]
        print(f"  📄 记忆 (memory)   : {m.get('memory_chars', 0):,} 字符")
        print(f"  📄 用户偏好 (user) : {m.get('user_chars', 0):,} 字符")
        print(f"  🤖 当前模型        : {data['models']}")
        print()
        print(f"  🚪 网关进程        : {data['gateway']['processes']} 个")
        print(f"  🌉 MemOS 桥进程   : {data['memos_bridge']['processes']} 个")
        print(f"  🔌 MemOS 18800    : {'✅ 可达' if data['memos_port_18800'] else '❌ 未监听'}")
        print(f"  🔌 侧边服务 8765  : {'✅ 可达' if data['sidecar_port_8765'] else '❌ 未监听'}")
        print()
        print(f"  📝 日记           : {data['diary']['count']} 篇")
        print(f"  📚 技能           : {data['skills']['count']} 个")
        print(f"  🔌 插件           : {data['plugins']['count']} 个")
        print(f"  🛠 脚本           : {data['scripts']['count']} 个")
        print(f"  📋 日志大小       : {data['logs']['size_mb']} MB")
        print()
        print(f"  ⚙ 配置文件       : {'✅' if data['config']['exists'] else '❌'}  config.yaml  {'✅' if data['config']['env_exists'] else '❌'}  .env")

if __name__ == "__main__":
    main()
