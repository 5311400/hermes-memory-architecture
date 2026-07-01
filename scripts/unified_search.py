#!/usr/bin/env python3
"""
F1 统一记忆网关 — 聚合搜索
用法: python3 unified_search.py --query "关键词" [--top 5] [--source all|memory|diary|memos]

搜索范围:
· MEMORY.md / USER.md — 开机记忆
· 日记文件 — ~/.hermes/日记/*.md
· MemOS — 通过 bridge_client 调用（如果桥在运行）

不调假命令，只查真实存在的东西。
"""

import os
import sys
import json
import re
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

HERMES_HOME = Path.home() / ".hermes"
MEMORY_FILE = HERMES_HOME / "memories" / "MEMORY.md"
USER_FILE = HERMES_HOME / "memories" / "USER.md"
DIARY_DIR = HERMES_HOME / "日记"


def search_memory(query):
    """搜索 MEMORY.md 和 USER.md"""
    results = []
    for name, path in [("MEMORY", MEMORY_FILE), ("USER", USER_FILE)]:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            # 按段落搜索
            paragraphs = re.split(r'\n\s*\n|§\n?', text)
            for i, para in enumerate(paragraphs):
                para = para.strip()
                if not para or len(para) < 5:
                    continue
                if query.lower() in para.lower():
                    results.append({
                        "source": name,
                        "content": para[:300],
                        "score": 1.0 - (i * 0.05),  # 越靠前分数越高
                        "timestamp": path.stat().st_mtime,
                    })
                    if len(results) >= 10:
                        break
        except Exception as e:
            pass
    return results


def search_diary(query):
    """搜索日记文件"""
    results = []
    if not DIARY_DIR.exists():
        return results
    
    # 获取所有日记文件，按修改时间倒序
    diary_files = sorted(DIARY_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    
    for diary_path in diary_files[:50]:  # 最多搜50篇
        try:
            text = diary_path.read_text(encoding="utf-8", errors="ignore")
            if query.lower() not in text.lower():
                continue
            
            # 找到匹配的行
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if query.lower() in line.lower() and len(line.strip()) > 5:
                    # 取上下文
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    context = '\n'.join(lines[start:end])
                    
                    # 提取日期（从文件名或内容）
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', diary_path.name)
                    date_str = date_match.group(1) if date_match else diary_path.name
                    
                    results.append({
                        "source": f"日记({date_str})",
                        "content": context[:300],
                        "score": 0.8,
                        "timestamp": diary_path.stat().st_mtime,
                    })
                    break  # 每篇日记只取第一个匹配
        except Exception:
            pass
        
        if len(results) >= 10:
            break
    
    return results


def search_memos(query):
    """搜索 MemOS（通过 bridge_client）"""
    results = []
    try:
        # 尝试通过 MemOS bridge 搜索
        sys.path.insert(0, str(HERMES_HOME / "plugins"))
        from memtensor.bridge_client import BridgeClient
        
        plugin_root = HERMES_HOME / "plugins" / "memtensor"
        with BridgeClient(plugin_root) as client:
            # 调用 MemOS 搜索
            resp = client.request("memos.search", {"query": query, "limit": 5})
            if resp and "result" in resp:
                for hit in resp["result"].get("hits", []):
                    results.append({
                        "source": "MemOS",
                        "content": hit.get("snippet", hit.get("text", ""))[:300],
                        "score": hit.get("score", 0.5),
                        "timestamp": time.time(),
                    })
    except Exception as e:
        # MemOS 不可用时静默跳过
        pass
    return results


def deduplicate_and_rank(results, top_k=5):
    """去重 + 排序"""
    if not results:
        return []
    
    # 去重：内容前100字符相同的视为重复
    seen = set()
    unique = []
    for r in results:
        key = r["content"][:100].strip()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    # 排序：分数 > 时间
    unique.sort(key=lambda x: (x["score"], x["timestamp"]), reverse=True)
    
    return unique[:top_k]


def unified_search(query, top_k=5, source="all"):
    """统一搜索入口"""
    all_results = []
    
    sources = {
        "memory": search_memory,
        "diary": search_diary,
        "memos": search_memos,
    }
    
    if source == "all":
        funcs = list(sources.values())
    else:
        funcs = [sources.get(source, search_memory)]
    
    # 顺序搜索（避免线程池超时问题）
    for f in funcs:
        try:
            results = f(query)
            all_results.extend(results)
        except Exception as e:
            pass
    
    return deduplicate_and_rank(all_results, top_k)


def main():
    parser = argparse.ArgumentParser(description="统一记忆网关 — 聚合搜索")
    parser.add_argument("--query", required=True, help="搜索关键词")
    parser.add_argument("--top", type=int, default=5, help="返回结果数量")
    parser.add_argument("--source", choices=["all", "memory", "diary", "memos"], default="all", help="搜索范围")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()
    
    results = unified_search(args.query, args.top, args.source)
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if not results:
            print("没有找到相关内容")
            return
        
        print(f"🔍 搜索结果 ({len(results)} 条):\n")
        for i, hit in enumerate(results, 1):
            print(f"{i}. [{hit['source']}]")
            print(f"   {hit['content'][:200]}")
            print()


if __name__ == "__main__":
    main()
