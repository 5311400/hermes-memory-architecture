# Layers — 各层详解

## L1 — MEMORY.md / USER.md（开机记忆）

**位置：** `~/.hermes/MEMORY.md`（~5000 字符上限）
**位置：** `~/.hermes/USER.md`（~1375 字符上限）

每次对话自动注入到系统提示词中，是智能体的"开机记忆"。

### 存储内容

**MEMORY.md（我的笔记）：**
- 环境事实（OS、路径、目录结构）
- 配置细节（API Key 截断陷阱、Termux 限制）
- 项目约定（中文日记规则、文档格式要求）
- 工具用法（脚本路径、常用命令）
- 用户铁律（改前备份、日记用 diary.py）

**USER.md（用户画像）：**
- 说话风格（要直接简短、不要文言字眼）
- 偏好习惯（技能不用提醒自动调用、不要跳题）
- 个人背景（40 岁、小妮高一、中医+计算机）
- 禁忌（不要表格、不要英文术语）

### 维护规则
- 接近容量上限时需清理过时信息
- 用 `memory` 工具写入（`action="add"` / `"replace"`）
- 不记任务进度、临时状态

---

## L2 — session_search（对话检索）

**技术：** SQLite FTS5（Hermes 内置）
**接口：** `session_search` 工具

### 四种调用方式

| 模式 | 用途 | 调用方式 |
|------|------|----------|
| Discovery | 搜索关键词找到相关会话 | `session_search(query="关键词")` |
| Scroll | 在会话中前后滚动 | `session_search(session_id=..., around_message_id=...)` |
| Read | 读取完整会话 | `session_search(session_id=...)` |
| Browse | 浏览最近会话 | `session_search()`（无参） |

### 注意事项
- 只搜索当前 profile 的会话 DB
- FTS5 语法：多词 AND 默认，OR 需显式，引号精确匹配
- 不跨 profile 搜索

---

## L3 — 日记系统

**位置：** `~/.hermes/日记/YYYY-MM-DD.md`
**同步目标：** IMA「日记」笔记本 + Obsidian
**脚本：** `~/.hermes/scripts/diary.py`

### 三向同步机制

```
diary.py
    ├── 1. 写入本地 ~/.hermes/日记/YYYY-MM-DD.md
    ├── 2. POST → IMA OpenAPI (ima.qq.com/openapi/note/v1)
    └── 3. 写入 Obsidian (/storage/emulated/0/Documents/Hermes/日记/)
```

### 使用方式

```bash
python3 diary.py "内容"                           # 新建今天
python3 diary.py --date 2026-06-21 "内容"          # 指定日期
python3 diary.py --append "追加"                   # 追加到今天
python3 diary.py --date YYYY-MM-DD --append "追加" # 追加到指定日期
```

### 日记结构
1. **原文** — 用户原话不改不删
2. **思考/联系** — 我的分析和关联
3. **与个人AI实践的联系** — 日记内容→Hermes 实践映射

### 相关技能
- `diary-workflow` — 日记写作工作流
- `diary-fragment-workflow` — 碎片日记汇总（晚 22:00 cron）

---

## L4 — SKILL.md 技能（程序化记忆）

**位置：** `~/.hermes/skills/`（155+ 个 SKILL.md）
**接口：** `skill_view()` / `skill_manage()` / `skills_list()` / `skills_search()`

把可重复的工作流固化为技能，下次直接加载。

### 技能生命周期

```
发现模式 → 创建 SKILL.md → 使用中发现缺陷 → patch 更新
    ↑                                              │
    └──────── 复杂任务完成后保存新技能 ←───────────┘
```

### 规则
- 先搜社区技能（awesome-hermes-agent、hermeshub 等），有现成的先用
- 完成 5+ 工具调用的复杂任务后保存为技能
- 用 `skill_manage(action="patch")` 更新过时/错误的技能
- 用 `skill_manage(action="delete", absorbed_into=...)` 合并技能

---

## L5 — 实体索引

**位置：** `~/.hermes/entity_index.json`
**脚本：** `~/.hermes/scripts/entity_links.py`

从日记和记忆中提取结构化实体索引。

### 实体类别（22 个）

| 类别 | 示例 |
|------|------|
| 人物 | 小妮、桃夭、陈皮、二丑 |
| 地点 | 邯郸、乐一 |
| 项目 | zhongyi、bridge-guard |
| 设备 | 小米11、红米5A、R3D路由器 |
| 医疗 | 艾灸、诊室 |

### 更新

```bash
python3 ~/.hermes/scripts/entity_links.py --build   # 重建索引
python3 ~/.hermes/scripts/entity_links.py --report  # 查看报告
```

---

## L6 — R3D 路由器 WebDAV（冷存储）

**硬件：** 小米路由器 HD（R3D）
**硬盘：** 3TB（剩余 382GB）
**系统：** 双系统（原厂固件 + OpenWRT）
**网络：** Mihomo 常开（7890 端口），WebDAV（alaya:8081）
**访问：** SSH root/密码，需特殊 KexAlgorithms

### 四层存储结构

```
/userdisk/data/
├── hermes_backup/       # 1层：全量备份（保留5份）
├── hermes_diary/        # 2层：日记归档
├── hermes_knowledge/    # 3层：结构化知识文档
└── hermes_memory/       # 4层：深层记忆快照
```

### SSH 注意事项
```bash
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 root@192.168.31.1
```
- Entware 仅剩 10MB 空间
- Node.js v18 可用但 npm 损坏
- U 盘路径：`/extdisks/sdb1`（14.7GB）

---

## L7 — MemOS v2.0（行为+世界模型）

**端口：** 18800（本地桥进程）
**架构：** 四层自进化、图结构、多知识库隔离

### 四层结构

| 层 | 内容 | 说明 |
|----|------|------|
| Trace（轨迹） | 每个会话的关键行为记录 | 短期行为记忆 |
| World Model（世界模型） | 环境事实和规则 | 长期知识 |
| Policy（策略） | 行为准则 | 指导原则 |
| Skill（晶体化技能） | 固化的可调用技能 | 程序化知识 |

### 运维

```bash
# 检查状态
python3 ~/.hermes/scripts/health_check.py

# 桥卡住时重启
~/.bin/gc  # kill MemOS 桥 + sleep 1 + hermes gateway
```

**注意：** 进程在但 18800 端口未监听 = 桥卡住，需要 `gc` 重启。

### 相关技能
- `memos-bridge-defense` — 防 MemOS 桥进程堆积

---

## L8 — GBrain（WSL 电脑端深度知识管理）

**位置：** WSL（survival@100.93.203.100）
**连接：** Tailscale 互联（手机 100.74.0.107）
**协议：** MCP（通过 `mcp_gbrain_*` 工具调用）

### 核心功能

| 功能 | 工具 | 用途 |
|------|------|------|
| 知识库搜索 | `mcp_gbrain_query` | 语义+关键词混合搜索 |
| 知识图谱 | `mcp_gbrain_get_page` / `put_page` | 页面+链接+标签 |
| 事实提取 | `mcp_gbrain_extract_facts` | 从对话提取结构化事实 |
| 多跳推理 | `mcp_gbrain_think` | 跨页面合成推理 |
| 矛盾检测 | `mcp_gbrain_find_contradictions` | 发现知识不一致 |
| 趋势分析 | `mcp_gbrain_find_trajectory` | 指标随时间变化 |
| 校准评估 | `mcp_gbrain_get_calibration_profile` | 预测准确性统计 |
