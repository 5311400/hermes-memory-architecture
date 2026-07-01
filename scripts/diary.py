#!/usr/bin/env python3
""""
日记一步到位：写本地 + 同步IMA + 同步Obsidian + 写入Hindsight记忆
用法：
  python3 diary.py "日记内容"                         # 新建今天的日记
  python3 diary.py --date 2026-06-21 "日记内容"       # 指定日期
  python3 diary.py --append "追加内容"                 # 追加到今天的日记（全部同步）
  python3 diary.py --date 2026-06-21 --append "内容"  # 追加到指定日期
"""
import json, urllib.request, os, sys, shutil
from datetime import datetime, timedelta

HOME = os.path.expanduser('~')
DIARY_DIR = os.path.join(HOME, '.hermes/日记')
OBSIDIAN_DIR = '/storage/emulated/0/Documents/Hermes/日记'
IMA_API = 'https://ima.qq.com/openapi/note/v1'
FOLDER_ID = 'folder37561e96bfa6fcb7'  # 日记笔记本
HINDSIGHT_API = 'http://127.0.0.1:8888'

def get_credentials():
    client_id = open(os.path.join(HOME, '.config/ima/client_id')).read().strip()
    api_key = open(os.path.join(HOME, '.config/ima/api_key')).read().strip()
    return client_id, api_key

def get_date(args):
    for i, arg in enumerate(args):
        if arg == '--date' and i + 1 < len(args):
            return args[i + 1]
    now = datetime.now()
    if now.hour < 5:
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')
    return now.strftime('%Y-%m-%d')

def get_content(args):
    skip = set()
    for i, arg in enumerate(args):
        if arg == '--date' and i + 1 < len(args):
            skip.add(i); skip.add(i + 1)
        if arg == '--append':
            skip.add(i)
    return ' '.join(args[i] for i in range(len(args)) if i not in skip).strip()

def meta_path(date):
    return os.path.join(DIARY_DIR, f'{date}.meta.json')

def load_note_id(date):
    p = meta_path(date)
    if os.path.exists(p):
        return json.load(open(p)).get('ima_note_id')
    return None

def save_note_id(date, note_id):
    with open(meta_path(date), 'w') as f:
        json.dump({"ima_note_id": note_id}, f)

def ima_import(content):
    """新建IMA笔记，返回note_id"""
    client_id, api_key = get_credentials()
    payload = json.dumps({
        "content_format": 1, "content": content, "folder_id": FOLDER_ID
    }).encode('utf-8')
    req = urllib.request.Request(f"{IMA_API}/import_doc", data=payload, headers={
        "ima-openapi-clientid": client_id, "ima-openapi-apikey": api_key,
        "Content-Type": "application/json"
    }, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        if result.get('code') == 0:
            return result['data']['note_id']
        raise Exception(f"IMA新建失败: {result}")

def ima_append(note_id, content):
    """追加到已有IMA笔记"""
    client_id, api_key = get_credentials()
    payload = json.dumps({
        "note_id": note_id, "content_format": 1, "content": content
    }).encode('utf-8')
    req = urllib.request.Request(f"{IMA_API}/append_doc", data=payload, headers={
        "ima-openapi-clientid": client_id, "ima-openapi-apikey": api_key,
        "Content-Type": "application/json"
    }, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        if result.get('code') == 0:
            return True
        raise Exception(f"IMA追加失败: {result}")

def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__); return

    date = get_date(args)
    content = get_content(args)
    append_mode = '--append' in args
    force = '--force' in args

    if not content:
        print("❌ 没有日记内容"); return

    os.makedirs(DIARY_DIR, exist_ok=True)
    path = os.path.join(DIARY_DIR, f'{date}.md')

    # ⚠️ 防重复：meta.json已有note_id但不是追加模式 → 跳过IMA
    existing_id = load_note_id(date)
    if existing_id and not append_mode and not force:
        print(f"⚠️ [{date}] 已存在IMA笔记(note_id={existing_id})，跳过新建。使用 --append 追加或 --force 强制新建。")
        # fall through to still write local + Obsidian + Hindsight
    elif existing_id and not append_mode and force:
        print(f"⚠️ [{date}] 强制重建IMA笔记")

    # 1. 写本地
    if append_mode and os.path.exists(path):
        with open(path, 'a') as f:
            f.write(f'\n\n{content}')
        print(f"✅ 本地追加: {path}")
    else:
        with open(path, 'w') as f:
            f.write(f'# {date} 日记\n\n{content}\n')
        print(f"✅ 本地创建: {path}")

    # 2. 同步IMA
    if existing_id and not append_mode and not force:
        print(f"⏭️ IMA跳过（已有note_id={existing_id}，已在上面警告）")
    else:
        try:
            if append_mode and existing_id:
                ima_append(existing_id, f'\n\n{content}')
                print(f"✅ IMA追加成功: note_id={existing_id}")
            else:
                full = f'# {date} 日记\n\n{content}'
                note_id = ima_import(full)
                save_note_id(date, note_id)
                print(f"✅ IMA新建成功: note_id={note_id}")
        except Exception as e:
            print(f"⚠️ IMA同步失败（本地已保存）: {e}")

    # 3. 同步Obsidian
    try:
        os.makedirs(OBSIDIAN_DIR, exist_ok=True)
        obsidian_path = os.path.join(OBSIDIAN_DIR, f'{date}.md')
        full = f'# {date} 日记\n\n{content}\n'
        if append_mode and os.path.exists(obsidian_path):
            with open(obsidian_path, 'a') as f:
                f.write(f'\n\n{content}')
        else:
            with open(obsidian_path, 'w') as f:
                f.write(full)
        print(f"✅ Obsidian同步: {obsidian_path}")
    except Exception as e:
        print(f"⚠️ Obsidian同步失败: {e}")

    # 4. 写入Hindsight记忆
    try:
        req = urllib.request.Request(
            f'{HINDSIGHT_API}/retain',
            data=json.dumps({
                "bank_id": "hermes",
                "content": f"[日记 {date}] {content[:300]}",
                "context": "日记",
                "tags": ["日记", date],
                "source": "diary.py"
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"✅ Hindsight记忆已存储")
    except Exception as e:
        print(f"⚠️ Hindsight记忆存储失败: {e}")

if __name__ == '__main__':
    main()
