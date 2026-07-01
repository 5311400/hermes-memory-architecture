# Setup — 环境搭建指南

## 前置条件

- Hermes Agent v0.15.2+
- Termux on Android 14 (ARM64)
- 可选：WSL (Ubuntu) 做深度知识管理
- 可选：小米 R3D 路由器做冷存储

## 手机端（核心环境）

### 1. MEMORY.md / USER.md

自动存在，无需安装。由 `memory` 工具维护。

### 2. 日记系统

```bash
# 脚本位置
~/.hermes/scripts/diary.py

# IMA 认证（已配置）
~/.config/ima/client_id
~/.config/ima/api_key
```

### 3. 运维脚本

```bash
# 所有脚本
~/.hermes/scripts/
├── diary.py              # 日记管理
├── health_check.py       # 健康检查
├── backup_hermes.sh      # 备份到路由器
├── auto_maintenance.py   # 自动维护
├── auto_tag.py           # 日记打标签
├── entity_links.py       # 实体索引
├── unified_search.py     # 统一搜索
├── session_summarizer.py # 会话摘要
└── restore_deepseek.sh   # 配置备份恢复
```

### 4. MemOS v2.0

```bash
# 检查运行状态
curl -s http://localhost:18800/health | head -1

# 如果未运行，确认桥进程
ps aux | grep memos

# 重启
~/.bin/gc
```

## 路由端（冷存储）

### SSH 访问

```bash
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 root@192.168.31.1
# 密码：8627432a
```

### WebDAV 验证

```bash
# alaya 服务运行在 8081 端口
curl -s http://192.168.31.1:8081/
```

### Mihomo（代理）

```bash
# 查看代理状态
curl -s http://127.0.0.1:9090/version

# 注意：路由器重启后 Mihomo 会恢复到 DIRECT 直连
```

## 电脑端（深度知识管理）

### WSL 连接

```bash
# 通过 Tailscale
ssh survival@100.93.203.100

# 项目位置
cd ~/zhongyi/       # 中医项目
cd ~/hermes-memory-architecture/  # 本仓库
```

### GBrain

通过 Hermes MCP 工具调用，无需手动连接。

## 备份流程

### 全量备份

```bash
~/.hermes/scripts/backup_hermes.sh
# → 打包 ~60MB → 上传到路由器 /userdisk/data/hermes_backup/
# → 路由器不可达时存到 ~/.hermes/backups/
# → 保留最近 5 份
```

### 恢复

```bash
tar -xzf <备份文件> -C ~/.hermes
```

### 配置备份

```bash
~/.hermes/scripts/restore_deepseek.sh backup  # 备份
~/.hermes/scripts/restore_deepseek.sh restore  # 恢复
```

## 日记碎片汇总（cron）

晚 22:00 自动汇总当天的碎片日记：

```bash
# 查看定时任务
cronjob action=list

# 相关技能
diary-fragment-workflow
```
