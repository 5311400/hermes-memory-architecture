#!/usr/bin/env python3
"""
F3 实体链接提取 — 从日记/记忆中提取人名、地点、项目等实体，建立交叉引用
用法: python3 entity_links.py [--build] [--report]

功能:
· 扫描日记和记忆文件，提取命名实体
· 生成实体索引文件
· 可选：在笔记间自动添加 [[实体]] 链接

注意：不调 GBrain API（本地无 GBrain 文件），只处理本地日记和记忆。
"""

import os
import sys
import json
import re
from pathlib import Path
from collections import defaultdict

HERMES_HOME = Path.home() / ".hermes"
MEMORY_FILE = HERMES_HOME / "memories" / "MEMORY.md"
USER_FILE = HERMES_HOME / "memories" / "USER.md"
DIARY_DIR = HERMES_HOME / "日记"
ENTITY_INDEX = HERMES_HOME / "entity_index.json"


# 预定义实体库（从记忆中提取的稳定实体）
KNOWN_ENTITIES = {
    # 人物
    "二丑": {"type": "人物", "desc": "猫（黑白）"},
    "陈皮": {"type": "人物", "desc": "猫（花菊）"},
    "桃夭": {"type": "人物", "desc": "猫（三花，走丢）"},
    "小妮": {"type": "人物", "desc": "用户女儿"},
    "孩子": {"type": "人物", "desc": "用户女儿"},
    "孩他娘": {"type": "人物", "desc": "用户妻子"},
    
    # 地点
    "养老院": {"type": "地点", "desc": "出诊地点"},
    "花卉市场": {"type": "地点", "desc": "出诊地点"},
    "诊所": {"type": "地点", "desc": "中医诊所"},
    "会所": {"type": "地点", "desc": "用户工作场所"},
    
    # 项目
    "Hermes": {"type": "项目", "desc": "AI智能体系统"},
    "GBrain": {"type": "项目", "desc": "知识图谱系统"},
    "MemOS": {"type": "项目", "desc": "记忆操作系统"},
    "zhongyi": {"type": "项目", "desc": "中医项目"},
    "MiGPT": {"type": "项目", "desc": "小爱音箱接入大模型"},
    
    # 设备
    "路由器": {"type": "设备", "desc": "小米R3D路由器"},
    "小爱音箱": {"type": "设备", "desc": "小米小爱音箱"},
    "手机": {"type": "设备", "desc": "小米11"},
    
    # 医疗
    "针灸": {"type": "医疗", "desc": "中医治疗手段"},
    "艾灸": {"type": "医疗", "desc": "中医治疗手段"},
    "脉象": {"type": "医疗", "desc": "中医诊断方法"},
    "舌象": {"type": "医疗", "desc": "中医诊断方法"},
}


def extract_entities_from_text(text):
    """从文本中提取实体"""
    found = set()
    for entity, info in KNOWN_ENTITIES.items():
        if entity in text:
            found.add(entity)
    return list(found)


def scan_diaries():
    """扫描所有日记，提取实体出现情况"""
    entity_occurrences = defaultdict(list)  # entity -> [(date, snippet)]
    
    if not DIARY_DIR.exists():
        return entity_occurrences
    
    diary_files = sorted(DIARY_DIR.glob("*.md"))
    for diary_path in diary_files:
        try:
            content = diary_path.read_text(encoding="utf-8", errors="ignore")
            entities = extract_entities_from_text(content)
            
            # 提取日期
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', diary_path.name)
            date_str = date_match.group(1) if date_match else diary_path.name
            
            for entity in entities:
                # 找到实体出现的上下文
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if entity in line:
                        start = max(0, i - 1)
                        end = min(len(lines), i + 2)
                        snippet = '\n'.join(lines[start:end])
                        entity_occurrences[entity].append({
                            "date": date_str,
                            "snippet": snippet[:200],
                        })
                        break  # 每篇日记只记录一次
        except Exception:
            pass
    
    return entity_occurrences


def scan_memory():
    """扫描 MEMORY.md 和 USER.md"""
    entity_occurrences = defaultdict(list)
    
    for name, path in [("MEMORY", MEMORY_FILE), ("USER", USER_FILE)]:
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            entities = extract_entities_from_text(content)
            for entity in entities:
                entity_occurrences[entity].append({
                    "source": name,
                    "snippet": content[:200],
                })
        except Exception:
            pass
    
    return entity_occurrences


def build_entity_index():
    """构建实体索引"""
    print("扫描日记...")
    diary_entities = scan_diaries()
    
    print("扫描记忆...")
    memory_entities = scan_memory()
    
    # 合并
    all_entities = defaultdict(list)
    for entity, occurrences in diary_entities.items():
        all_entities[entity].extend(occurrences)
    for entity, occurrences in memory_entities.items():
        all_entities[entity].extend(occurrences)
    
    # 构建索引
    index = {
        "entities": {},
        "stats": {
            "total_entities": len(all_entities),
            "total_occurrences": sum(len(v) for v in all_entities.values()),
        }
    }
    
    for entity, occurrences in sorted(all_entities.items()):
        info = KNOWN_ENTITIES.get(entity, {"type": "未知", "desc": ""})
        index["entities"][entity] = {
            "type": info["type"],
            "desc": info["desc"],
            "occurrences": occurrences[:10],  # 最多保留10条
            "count": len(occurrences),
        }
    
    # 保存索引
    ENTITY_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 实体索引已保存到 {ENTITY_INDEX}")
    print(f"   实体数: {index['stats']['total_entities']}")
    print(f"   出现次数: {index['stats']['total_occurrences']}")
    
    return index


def report_entities():
    """打印实体报告"""
    if not ENTITY_INDEX.exists():
        print("实体索引不存在，先运行 --build")
        return
    
    index = json.loads(ENTITY_INDEX.read_text(encoding="utf-8"))
    
    print("📊 实体链接报告\n")
    print(f"实体总数: {index['stats']['total_entities']}")
    print(f"总出现次数: {index['stats']['total_occurrences']}\n")
    
    # 按类型分组
    by_type = defaultdict(list)
    for entity, info in index["entities"].items():
        by_type[info["type"]].append((entity, info["count"]))
    
    for entity_type, entities in sorted(by_type.items()):
        print(f"\n## {entity_type}")
        for entity, count in sorted(entities, key=lambda x: x[1], reverse=True):
            print(f"  · {entity} ({count} 次)")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="实体链接提取")
    parser.add_argument("--build", action="store_true", help="构建实体索引")
    parser.add_argument("--report", action="store_true", help="打印实体报告")
    args = parser.parse_args()
    
    if args.build:
        build_entity_index()
    elif args.report:
        report_entities()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
