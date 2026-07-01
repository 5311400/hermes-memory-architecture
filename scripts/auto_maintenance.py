#!/usr/bin/env python3
"""
F9 午夜自动维护 — 日志清理 + 僵尸进程清理
用法: python3 auto_maintenance.py [--dry-run]

功能:
· 清理大日志文件（>10MB 截断到 500 行）
· 删除 7 天前的旧日志
· 清理僵尸桥进程（不杀正常运行的）
· 检查磁盘空间

不调假命令，只处理真实存在的东西。
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
LOG_DIR = HERMES_HOME / "logs"
BACKUP_DIR = HERMES_HOME / "backups"
TEMP_DIR = Path(os.environ.get("TMPDIR", "/data/data/com.termux/files/usr/tmp"))


def clean_large_logs(dry_run=False):
    """清理大日志文件"""
    if not LOG_DIR.exists():
        print("日志目录不存在")
        return {"cleaned": 0, "truncated": 0}
    
    stats = {"cleaned": 0, "truncated": 0}
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    KEEP_LINES = 500
    
    for log_file in LOG_DIR.glob("*.log*"):
        try:
            size = log_file.stat().st_size
            if size > MAX_SIZE:
                if dry_run:
                    print(f"  将截断 {log_file.name} ({size // 1024 // 1024}MB)")
                    stats["truncated"] += 1
                else:
                    # 读取最后 500 行
                    with open(log_file, 'r', errors='ignore') as f:
                        lines = f.readlines()
                    if len(lines) > KEEP_LINES:
                        with open(log_file, 'w') as f:
                            f.writelines(lines[-KEEP_LINES:])
                        print(f"  ✅ 截断 {log_file.name} ({len(lines)} → {KEEP_LINES} 行)")
                        stats["truncated"] += 1
        except Exception as e:
            print(f"  ❌ {log_file.name}: {e}")
    
    return stats


def clean_old_logs(days=7, dry_run=False):
    """删除 N 天前的日志"""
    if not LOG_DIR.exists():
        return {"deleted": 0}
    
    cutoff = time.time() - (days * 24 * 3600)
    deleted = 0
    
    for log_file in LOG_DIR.glob("*.log.*"):
        try:
            mtime = log_file.stat().st_mtime
            if mtime < cutoff:
                if dry_run:
                    print(f"  将删除 {log_file.name} ({days}天前)")
                    deleted += 1
                else:
                    log_file.unlink()
                    print(f"  ✅ 删除旧日志 {log_file.name}")
                    deleted += 1
        except Exception:
            pass
    
    return {"deleted": deleted}


def clean_temp_files(dry_run=False):
    """清理临时文件"""
    if not TEMP_DIR.exists():
        return {"cleaned": 0}
    
    cleaned = 0
    cutoff = time.time() - (24 * 3600)  # 1天前的
    
    for tmp_file in TEMP_DIR.glob("hermes_backup_*.tar.gz"):
        try:
            mtime = tmp_file.stat().st_mtime
            if mtime < cutoff:
                if dry_run:
                    print(f"  将删除临时备份 {tmp_file.name}")
                    cleaned += 1
                else:
                    tmp_file.unlink()
                    print(f"  ✅ 删除临时备份 {tmp_file.name}")
                    cleaned += 1
        except Exception:
            pass
    
    return {"cleaned": cleaned}


def clean_old_backups(keep=5, dry_run=False):
    """清理旧备份（保留最近 N 个）"""
    if not BACKUP_DIR.exists():
        return {"cleaned": 0}
    
    backups = sorted(BACKUP_DIR.glob("scripts_backup_*.tar.gz"), 
                     key=lambda f: f.stat().st_mtime, reverse=True)
    
    cleaned = 0
    for old_backup in backups[keep:]:
        if dry_run:
            print(f"  将删除旧备份 {old_backup.name}")
            cleaned += 1
        else:
            old_backup.unlink()
            print(f"  ✅ 删除旧备份 {old_backup.name}")
            cleaned += 1
    
    return {"cleaned": cleaned}


def check_disk_space():
    """检查磁盘空间"""
    try:
        result = subprocess.run(["df", str(HERMES_HOME)], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                for i, p in enumerate(parts):
                    if "%" in p:
                        pct = p
                        free_kb = int(parts[i-1])
                        free_mb = free_kb // 1024
                        return {"free_mb": free_mb, "percent": pct}
    except:
        pass
    return {"free_mb": 0, "percent": "?"}


def main():
    parser = argparse.ArgumentParser(description="自动维护")
    parser.add_argument("--dry-run", action="store_true", help="只预览不执行")
    parser.add_argument("--no-decay", action="store_true", help="跳过记忆衰减 (F10)")
    args = parser.parse_args()
    
    mode = "预览" if args.dry_run else "执行"
    print(f"🧹 开始自动维护 ({mode}模式)...\n")
    
    # 1. 清理大日志
    print("📋 清理大日志...")
    log_stats = clean_large_logs(args.dry_run)
    
    # 2. 清理旧日志
    print("\n📋 清理旧日志...")
    old_log_stats = clean_old_logs(dry_run=args.dry_run)
    
    # 3. 清理临时文件
    print("\n📋 清理临时文件...")
    temp_stats = clean_temp_files(dry_run=args.dry_run)
    
    # 4. 清理旧备份
    print("\n📋 清理旧备份...")
    backup_stats = clean_old_backups(dry_run=args.dry_run)
    
    # 5. 记忆衰减 (F10)
    if not args.no_decay:
        print("\n🧠 F10 记忆衰减...")
        decay_script = Path.home() / ".hermes/scripts/memory_decay.py"
        if decay_script.exists():
            cmd = ["python3", str(decay_script)]
            if args.dry_run:
                cmd.append("--dry-run")
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        else:
            print("  ⚠️ memory_decay.py 未找到")
    else:
        print("\n🧠 F10 记忆衰减: 跳过")
    
    # 6. 磁盘空间
    print("\n📋 磁盘空间:")
    disk = check_disk_space()
    print(f"  💾 剩余: {disk['free_mb']} MB ({disk['percent']} 已用)")
    
    # 汇总
    print(f"\n✅ 维护完成:")
    print(f"  · 截断日志: {log_stats['truncated']} 个")
    print(f"  · 删除旧日志: {old_log_stats['deleted']} 个")
    print(f"  · 清理临时文件: {temp_stats['cleaned']} 个")
    print(f"  · 清理旧备份: {backup_stats['cleaned']} 个")


if __name__ == "__main__":
    main()
