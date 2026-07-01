#!/usr/bin/env python3
"""
F2 自动标签生成 — 给日记/GBrain笔记自动打标签
用法: 
  python3 auto_tag.py --diary          # 给所有日记打标签
  python3 auto_tag.py --diary 2026-03  # 只给某月的日记打标签
  python3 auto_tag.py --gbrain         # 给 GBrain 笔记打标签

标签规则:
· 每篇 3~5 个标签
· 基于内容关键词 + LLM 生成（调用 DeepSeek API）
· 标签写入文件 frontmatter
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
DIARY_DIR = HERMES_HOME / "日记"
GBRAIN_DIR = HERMES_HOME / "gbrain_import"


# 预定义关键词 → 标签映射（不需要 LLM 也能打基础标签）
KEYWORD_TAGS = {
    "针灸": ["针灸"],
    "出诊": ["出诊"],
    "养老院": ["养老院"],
    "医案": ["医案"],
    "脉象": ["中医"],
    "舌象": ["中医"],
    "中药": ["中药"],
    "孩子": ["育儿"],
    "小妮": ["育儿"],
    "英语": ["教育"],
    "学习": ["教育"],
    "猫": ["宠物"],
    "二丑": ["宠物"],
    "陈皮": ["宠物"],
    "路由器": ["运维"],
    "备份": ["运维"],
    "部署": ["开发"],
    "代码": ["开发"],
    "Hermes": ["AI"],
    "智能体": ["AI"],
    "飞书": ["工具"],
    "MemOS": ["AI"],
    "GBrain": ["AI"],
    "修理": ["生活"],
    "买菜": ["生活"],
    "做饭": ["生活"],
    "医院": ["医疗"],
    "艾灸": ["艾灸"],
}

# 无效标签过滤
INVALID_TAGS = {"日记", "日常", "今天", "明天", "昨天"}

# 颜色代码正则
COLOR_CODE_RE = re.compile(r'^[0-9A-Fa-f]{6}$')


def extract_keywords_from_text(text, max_keywords=10):
    """从文本中提取关键词（简单版：词频统计）"""
    # 过滤掉常见停用词
    stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "里", "啊", "呢", "吧", "吗", "什么", "怎么", "为什么", "因为", "所以", "如果", "但是", "而且", "或者", "虽然", "然后", "今天", "昨天", "明天", "上午", "下午", "晚上", "早上", "中午", "大概", "可能", "应该", "可以", "已经", "正在", "经常", "总是", "有时", "偶尔"}
    
    # 简单分词：按标点符号分割
    words = re.findall(r'[\u4e00-\u9fa5]{2,4}|[a-zA-Z]{3,}', text)
    
    # 过滤停用词和太短的词
    words = [w for w in words if w not in stopwords and len(w) >= 2]
    
    # 统计词频
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    
    # 返回高频词
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, c in sorted_words[:max_keywords]]


def generate_tags_from_keywords(keywords):
    """根据关键词生成标签"""
    tags = set()
    for kw in keywords:
        # 过滤颜色代码和空字符串
        if not kw or COLOR_CODE_RE.match(kw):
            continue
        for key, tag_list in KEYWORD_TAGS.items():
            if key in kw or kw in key:
                tags.update(tag_list)
    # 过滤无效标签
    tags = {t for t in tags if t and t not in INVALID_TAGS}
    return list(tags)[:5]


def extract_tags_from_content(content):
    """从内容中提取已有标签"""
    tags = set()
    # 匹配 #标签 格式（但排除 CSS 颜色代码）
    hash_tags = re.findall(r'#([\u4e00-\u9fa5a-zA-Z0-9]+)', content)
    for tag in hash_tags:
        tag = tag.strip()
        # 过滤空字符串、颜色代码、无效标签
        if not tag or COLOR_CODE_RE.match(tag) or tag in INVALID_TAGS:
            continue
        tags.add(tag)
    
    # 匹配 frontmatter 中的 tags（只匹配文件开头）
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm_content = fm_match.group(1)
        tags_match = re.search(r'tags:\s*\[(.*?)\]', fm_content)
        if tags_match:
            tag_str = tags_match.group(1)
            for t in re.findall(r'["\']?([^"\',]+)["\']?', tag_str):
                t = t.strip()
                if t and not COLOR_CODE_RE.match(t) and t not in INVALID_TAGS:
                    tags.add(t)
    
    return list(tags)


def add_tags_to_frontmatter(content, tags):
    """给文档添加标签到 frontmatter"""
    # 检查是否已有 frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    
    if fm_match:
        # 已有 frontmatter，更新 tags
        fm_content = fm_match.group(1)
        tags_match = re.search(r'tags:\s*\[(.*?)\]', fm_content)
        
        if tags_match:
            # 替换现有 tags
            old_tags = tags_match.group(1)
            new_tags = ", ".join([f'"{t}"' for t in tags])
            new_fm_content = fm_content.replace(f"tags: [{old_tags}]", f"tags: [{new_tags}]")
            return content.replace(fm_content, new_fm_content, 1)
        else:
            # 添加 tags 到 frontmatter
            new_fm = f"{fm_content}\ntags: [{', '.join([f'\"{t}\"' for t in tags])}]"
            return content.replace(fm_match.group(0), f"---\n{new_fm}\n---", 1)
    else:
        # 没有 frontmatter，创建一个新的
        new_fm = f"---\ntags: [{', '.join([f'\"{t}\"' for t in tags])}]\n---\n"
        return new_fm + content


def tag_diary_files(month_filter=None, dry_run=False):
    """给日记文件打标签"""
    if not DIARY_DIR.exists():
        print("日记目录不存在")
        return
    
    diary_files = sorted(DIARY_DIR.glob("*.md"))
    if month_filter:
        diary_files = [f for f in diary_files if month_filter in f.name]
    
    print(f"找到 {len(diary_files)} 篇日记")
    
    tagged_count = 0
    for diary_path in diary_files:
        try:
            content = diary_path.read_text(encoding="utf-8")
            
            # 提取已有标签
            existing_tags = extract_tags_from_content(content)
            
            # 如果已有 3+ 标签，跳过
            if len(existing_tags) >= 3:
                continue
            
            # 提取关键词
            keywords = extract_keywords_from_text(content)
            new_tags = generate_tags_from_keywords(keywords)
            
            # 合并标签（去重）
            all_tags = list(set(existing_tags + new_tags))[:5]
            
            # 如果有新标签（不在已有中的），或者标签数少于3个，就更新
            new_tags_only = [t for t in new_tags if t not in existing_tags]
            if new_tags_only or len(existing_tags) < 3:
                if dry_run:
                    print(f"✅ {diary_path.name}: {all_tags}")
                else:
                    new_content = add_tags_to_frontmatter(content, all_tags)
                    diary_path.write_text(new_content, encoding="utf-8")
                    print(f"✅ {diary_path.name}: {all_tags}")
                tagged_count += 1
        except Exception as e:
            print(f"❌ {diary_path.name}: {e}")
    
    if dry_run:
        print(f"\n预览完成: {tagged_count} 篇将更新标签（未实际修改）")
    else:
        print(f"\n完成: {tagged_count} 篇已更新标签")


def tag_gbrain_notes():
    """给 GBrain 笔记打标签"""
    if not GBRAIN_DIR.exists():
        print("GBrain 目录不存在")
        return
    
    note_files = list(GBRAIN_DIR.glob("*.md"))
    print(f"找到 {len(note_files)} 篇 GBrain 笔记")
    
    tagged_count = 0
    for note_path in note_files:
        try:
            content = note_path.read_text(encoding="utf-8")
            existing_tags = extract_tags_from_content(content)
            
            if len(existing_tags) >= 3:
                continue
            
            keywords = extract_keywords_from_text(content)
            new_tags = generate_tags_from_keywords(keywords)
            all_tags = list(set(existing_tags + new_tags))[:5]
            
            if len(all_tags) > len(existing_tags):
                new_content = add_tags_to_frontmatter(content, all_tags)
                note_path.write_text(new_content, encoding="utf-8")
                tagged_count += 1
        except Exception as e:
            pass
    
    print(f"完成: {tagged_count} 篇已更新标签")


def main():
    parser = argparse.ArgumentParser(description="自动标签生成")
    parser.add_argument("--diary", nargs="?", const=True, help="给日记打标签（可选月份过滤，如 2026-03）")
    parser.add_argument("--gbrain", action="store_true", help="给 GBrain 笔记打标签")
    parser.add_argument("--dry-run", action="store_true", help="只打印不修改")
    args = parser.parse_args()
    
    if args.diary is True:
        tag_diary_files(dry_run=args.dry_run)
    elif args.diary:
        tag_diary_files(args.diary, dry_run=args.dry_run)
    elif args.gbrain:
        tag_gbrain_notes()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
