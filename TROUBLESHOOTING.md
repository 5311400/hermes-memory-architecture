# Troubleshooting — 常见问题排查

## L1 — MEMORY.md 不生效

**现象：** 对话中记忆内容未出现。

**排查：**
```bash
# 检查文件存在
ls -la ~/.hermes/MEMORY.md ~/.hermes/USER.md

# 检查大小（超 5000 字会被截断）
wc -c ~/.hermes/MEMORY.md ~/.hermes/USER.md

# 检查文件编码
file ~/.hermes/MEMORY.md
```

**解决：** 删旧留新，确保不超过容量上限。

---

## L2 — session_search 搜不到结果

**现象：** 明明有相关对话，但搜索返回空。

**排查：**
- 确认当前 profile 正确（不同 profile 会话 DB 独立）
- 检查搜索词是否有 FTS5 语法问题（标点符号、停用词）

**解决：** 简化搜索词，用单字或多词 OR 查询。

---

## L3 — 日记同步失败

### IMA 同步失败

**现象：** `diary.py` 报 IMA 错误。

**排查：**
```bash
# 检查 API Key 是否过期
cat ~/.config/ima/client_id
cat ~/.config/ima/api_key
```

**解决：** 重新获取 IMA OpenAPI 凭证并写入对应文件。

### Obsidian 同步失败

**现象：** 手机端 Obsidian 看不到新日记。

**解决：** 确认 `/storage/emulated/0/Documents/Hermes/日记/` 目录存在于手机文件系统。

---

## L4 — 技能不触发

**现象：** 特定场景下技能没有被自动加载。

**排查：**
- 确认技能已存在：`skills_list()`
- 确认 triggers 包含当前场景的关键词

**解决：** 用 `skill_manage(action="patch")` 更新 triggers。

---

## L5 — 实体索引不更新

**现象：** 新增的日记内容未反映在索引中。

**解决：**
```bash
python3 ~/.hermes/scripts/entity_links.py --build --dry-run  # 预览
python3 ~/.hermes/scripts/entity_links.py --build             # 执行
```

---

## L6 — R3D 路由器不可达

**现象：** 备份失败，SSH 连不上。

**排查：**
```bash
# 路由器是否开机
ping 192.168.31.1

# SSH 是否响应（需特殊 KexAlgorithms）
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o ConnectTimeout=5 root@192.168.31.1 "echo OK"
```

**常见原因：**
- 路由器重启（每天凌晨 3:00-3:10 自动重启光猫和路由）
- Mihomo 规则变化导致 SSH 被封
- HostKey 变更（路由器重刷固件后）

**解决：**
- 等待路由器重启完成
- 路由器重启后 Mihomo 回到 DIRECT 直连，需手动切回代理
- SSH HostKey 变更时需清理 `~/.ssh/known_hosts`

---

## L7 — MemOS 桥卡住

**现象：** 记忆查询慢或无响应，`health_check.py` 显示 18800 端口未监听。

**典型特征：**
- 进程在（`ps aux | grep memos` 能看到），但端口未监听
- `curl localhost:18800` 超时或拒绝连接
- 桥进程堆积（多个 memos 进程在跑）

**解决：**
```bash
# 一键修复
~/.bin/gc
# gc = pkill -f "memos|bridge" + sleep 1 + hermes gateway restart
```

**预防：** 配置了 cron 定时检查，每天早上 8:00 自动检查并清理。

---

## L8 — GBrain 不可达

**现象：** `mcp_gbrain_*` 工具调用超时或失败。

**排查：**
```bash
# 检查 WSL 是否在线
ping -c 1 100.93.203.100

# 检查 GBrain 服务
ssh survival@100.93.203.100 "curl -s localhost:18888/health"
```

**常见原因：**
- WSL 电脑关机或休眠
- Tailscale 断开
- GBrain 服务崩溃

**解决：**
- 远程唤醒或等待用户开机
- 重启 Tailscale
- SSH 到 WSL 重启 GBrain 服务

---

## 通用 — 改东西前备份

**这是用户铁律，没有例外。**

```bash
~/.hermes/scripts/backup_hermes.sh
```

如果不确定，先备份再操作。恢复命令：

```bash
tar -xzf ~/.hermes/backups/backup_*.tar.gz -C ~/.hermes
```

## 通用 — Termux 环境特殊限制

| 限制 | 替代方案 |
|------|----------|
| 无 /tmp | 用 $PREFIX/tmp |
| 无 which 命令 | 用 `type` 或 `command -v` |
| df 不支持 -m | 用 `df -h` |
| 无 sqlite-vec | 不用向量数据库方案 |
| 无完整 locale | 中文显示用 font.ttf |
| 网关重启 | `sv restart hermes`（小写） |

---

## 通用 — 恢复出厂配置

如果 Hermes 配置损坏：

```bash
# 从路由器恢复最新备份
scp root@192.168.31.1:/userdisk/data/hermes_backup/latest.tar.gz ~/
tar -xzf latest.tar.gz -C ~/.hermes

# 或从 local 备份恢复
ls ~/.hermes/backups/
tar -xzf ~/.hermes/backups/backup_*.tar.gz -C ~/.hermes
```
