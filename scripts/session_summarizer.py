#!/usr/bin/env python3
"""
F4 会话摘要归档 — 把长会话压缩成摘要存入日记
用法: python3 session_summarizer.py [--days 7] [--min-turns 20]

功能:
· 扫描最近N天的会话
· 找出超过N轮的长会话
· 生成摘要并追加到对应日期的日记

注意：不依赖不存在的 hermes CLI 命令，通过 session_search MCP 工具获取会话数据。
由于脚本无法直接调用 MCP 工具，此功能主要通过 cron 任务在 Hermes 对话中触发。
此脚本仅作为辅助工具，提供摘要模板和格式化功能。
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

HERMES_HOME = Path.home() / ".hermes"
DIARY_DIR = HERMES_HOME / "日记"
SESSION_SUMMARIES = HERMES_HOME / "session_summaries"


def create_summary_template(session_date, topic, summary, key_points):
    """创建会话摘要模板"""
    template = f"""---
type: session_summary
date: {session_date}
topic: {topic}
---

# 会话摘要 · {session_date}

## 主题
{topic}

## 摘要
{summary}

## 关键点
"""
    for i, point in enumerate(key_points, 1):
        template += f"{i}. {point}\n"
    
    template += "\n---\n"
    return template


def append_to_diary(date_str, summary_content):
    """追加到日记文件"""
    diary_path = DIARY_DIR / f"{date_str}.md"
    
    if diary_path.exists():
        content = diary_path.read_text(encoding="utf-8")
        # 检查是否已有会话摘要部分
        if "## 🤖 会话摘要" not in content:
            content += f"\n\n## 🤖 会话摘要\n\n{summary_content}"
        else:
            # 追加到现有摘要部分
            content = content.replace(
                "## 🤖 会话摘要",
                f"## 🤖 会话摘要\n\n{summary_content}"
            )
    else:
        content = f"""# 日记 · {date_str}

## 🤖 会话摘要

{summary_content}
"""
    
    diary_path.write_text(content, encoding="utf-8")
    print(f"✅ 已追加到 {diary_path.name}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="会话摘要归档")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--topic", help="会话主题")
    parser.add_argument("--summary", help="会话摘要内容")
    parser.add_argument("--points", nargs="*", help="关键点列表")
    args = parser.parse_args()
    
    if not args.date:
        args.date = datetime.now().strftime("%Y-%m-%d")
    
    if not args.topic:
        args.topic = "日常会话"
    
    if not args.summary:
        args.summary = "无摘要内容"
    
    key_points = args.points or ["无关键点"]
    
    template = create_summary_template(args.date, args.topic, args.summary, key_points)
    append_to_diary(args.date, template)


if __name__ == "__main__":
    main()
