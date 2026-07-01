# Hermes Memory Architecture

构建在 Hermes Agent 之上的 8 层个人记忆管理系统。热数据在上、冷数据在下，每层在不同速度/容量/持久性之间取得平衡。

## 架构速览

```
L1   MEMORY.md / USER.md       开机记忆            每次对话自动注入
L2   session_search             对话检索            SQLite FTS5 跨会话搜索
L3   日记系统                    每日记录            本地+IMA+Obsidian 三向同步
L4   SKILL.md 技能              程序化记忆           155+ 个可重用工作流
L5   实体索引                    结构关联            22 个实体交叉引用
─────────────────────────────────────────────────────────────
L6   R3D 路由器 WebDAV         冷存储               3TB 硬盘·四层归档
L7   MemOS v2.0                行为+世界模型        图结构·四层自进化
L8   GBrain                    深度知识管理         知识图谱·事实提取
```

## 设计原则

- **上层快下层慢** — 热数据在上层（MEMORY.md），冷数据在下层（R3D WebDAV/GBrain）
- **每层独立可替换** — 从 Hindsight 迁移到 MemOS 证明了这种解耦的价值
- **改前必备份** — 所有写入操作前必须执行备份脚本
- **数据不重复** — 每层存不同粒度的数据，不跨层冗余

## 文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 架构设计深度解析 |
| [LAYERS.md](LAYERS.md) | 每层详细技术说明 |
| [SETUP.md](SETUP.md) | 环境搭建指南 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 常见问题排查 |

## 快速开始

```bash
# 1. 健康检查
python3 scripts/health_check.py

# 2. 查看各层状态
#   - MEMORY.md: cat ~/.hermes/MEMORY.md | wc -c
#   - MemOS: curl -s http://localhost:18800/health
#   - R3D: ssh root@192.168.31.1 df -h /userdisk/data

# 3. 备份
./scripts/backup_hermes.sh

# 4. 记日记
python3 scripts/diary.py "今天的内容..."
```

## 系统要求

- **手机端（主运行环境）：** Termux on Android 14, ARM64
- **电脑端（辅助）：** WSL (Ubuntu), Tailscale 互联
- **冷存储：** 小米 R3D 路由器（OpenWRT/Mihomo），3TB 硬盘，WebDAV (alaya:8081)

## 技术栈

- **Hermes Agent** — AI 智能体框架（v0.15.2+）
- **MemOS** — 行为轨迹+世界模型（v2.0，图结构）
- **GBrain** — 知识图谱引擎（MCP 协议）
- **SQLite FTS5** — 全文搜索
- **IMA OpenAPI** — 笔记同步
- **Obsidian** — 本地知识库
- **WebDAV (alaya)** — 冷存储传输

## 许可证

MIT
