#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# Hermes 备份脚本 — 打包关键文件并通过 SSH 推送到路由器硬盘
# 用法: backup_hermes.sh [--no-upload] [--local]
# ============================================================

set -e

HERMES_HOME="$HOME/.hermes"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="hermes_backup_${DATE}.tar.gz"
TEMP_BACKUP="${TMPDIR:-$PREFIX/tmp}/${BACKUP_NAME}"

# 路由器 SSH 配置
ROUTER_USER="root"
ROUTER_HOST="192.168.31.1"
ROUTER_PASS="8627432a"
ROUTER_BACKUP_DIR="/userdisk/data/hermes_backup"
SSH_OPTS="-o ConnectTimeout=10 -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa -o StrictHostKeyChecking=no"
SSH_CMD="sshpass -p \"$ROUTER_PASS\" ssh $SSH_OPTS $ROUTER_USER@$ROUTER_HOST"
SCP_CMD="sshpass -p \"$ROUTER_PASS\" scp $SSH_OPTS"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 打包关键文件
create_backup() {
    log "开始打包 Hermes 关键文件..."
    cd "$HERMES_HOME" || error "无法进入 $HERMES_HOME"

    # 要备份的清单
    ITEMS=""
    [ -f MEMORY.md ] && ITEMS="$ITEMS MEMORY.md"
    [ -f USER.md ] && ITEMS="$ITEMS USER.md"
    [ -f SOUL.md ] && ITEMS="$ITEMS SOUL.md"
    [ -f config.yaml ] && ITEMS="$ITEMS config.yaml"
    [ -f .env ] && ITEMS="$ITEMS .env"
    [ -f auth.json ] && ITEMS="$ITEMS auth.json"
    [ -d plugins ] && ITEMS="$ITEMS plugins"
    [ -d skills ] && ITEMS="$ITEMS skills"
    [ -d scripts ] && ITEMS="$ITEMS scripts"
    [ -d 日记 ] && ITEMS="$ITEMS 日记"
    [ -d logs ] && ITEMS="$ITEMS logs"
    [ -d cron ] && ITEMS="$ITEMS cron"
    [ -d memories ] && ITEMS="$ITEMS memories"
    [ -d profiles ] && ITEMS="$ITEMS profiles"
    [ -d backups ] && ITEMS="$ITEMS backups"

    if [ -z "$ITEMS" ]; then
        error "没有找到可备份的文件"
    fi

    log "打包内容:$ITEMS"
    tar -czf "$TEMP_BACKUP" $ITEMS 2>/dev/null || true

    if [ -f "$TEMP_BACKUP" ]; then
        SIZE=$(du -h "$TEMP_BACKUP" | cut -f1)
        log "打包完成: $TEMP_BACKUP ($SIZE)"
    else
        error "打包失败"
    fi
}

# 通过 SSH 上传到路由器（不用 scp，用 tar 管道，路由器不支持 sftp）
upload_to_router() {
    log "连接路由器 $ROUTER_HOST ..."

    # 检查连接
    if ! sshpass -p "$ROUTER_PASS" ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "echo ok" >/dev/null 2>&1; then
        warn "无法连接路由器，保存到本地"
        return 1
    fi

    # 创建远程目录
    sshpass -p "$ROUTER_PASS" ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "mkdir -p $ROUTER_BACKUP_DIR"

    # 用 tar 管道传输（不依赖 sftp/scp）
    log "上传到路由器 $ROUTER_BACKUP_DIR ..."
    cat "$TEMP_BACKUP" | sshpass -p "$ROUTER_PASS" ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "cat > '$ROUTER_BACKUP_DIR/$BACKUP_NAME'"

    # 验证文件大小
    REMOTE_SIZE=$(sshpass -p "$ROUTER_PASS" ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "stat -c%s '$ROUTER_BACKUP_DIR/$BACKUP_NAME'" 2>/dev/null)
    LOCAL_SIZE=$(stat -c%s "$TEMP_BACKUP" 2>/dev/null)

    if [ "$REMOTE_SIZE" = "$LOCAL_SIZE" ] && [ -n "$REMOTE_SIZE" ]; then
        # 更新最新备份记录
        sshpass -p "$ROUTER_PASS" ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "echo '$BACKUP_NAME' > $ROUTER_BACKUP_DIR/latest_backup.txt"
        sshpass -p "$ROUTER_PASS" ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "echo '$(date '+%Y-%m-%d %H:%M:%S') - $BACKUP_NAME ($(($LOCAL_SIZE/1024/1024))MB)' >> $ROUTER_BACKUP_DIR/backup_history.log"
        log "✅ 备份已上传: $ROUTER_BACKUP_DIR/$BACKUP_NAME ($(($LOCAL_SIZE/1024/1024))MB)"
    else
        warn "上传验证失败 (本地=$LOCAL_SIZE 远程=$REMOTE_SIZE)"
        return 1
    fi
}

# 保存到本地
save_local() {
    LOCAL_DIR="$HERMES_HOME/backups"
    mkdir -p "$LOCAL_DIR"
    cp "$TEMP_BACKUP" "$LOCAL_DIR/$BACKUP_NAME"
    log "✅ 备份已保存到本地: $LOCAL_DIR/$BACKUP_NAME"
}

# 清理旧备份（保留最近 5 个）
cleanup_local() {
    LOCAL_DIR="$HERMES_HOME/backups"
    if [ -d "$LOCAL_DIR" ]; then
        cd "$LOCAL_DIR"
        ls -t hermes_backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
        log "本地旧备份已清理（保留最近5个）"
    fi
}

cleanup_remote() {
    sshpass -p "$ROUTER_PASS" ssh $SSH_OPTS "$ROUTER_USER@$ROUTER_HOST" "cd $ROUTER_BACKUP_DIR && ls -t hermes_backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f" 2>/dev/null || true
}

cleanup_temp() {
    rm -f "$TEMP_BACKUP"
}

# 主流程
main() {
    log "🚀 Hermes 备份开始"
    create_backup

    if [ "$1" = "--no-upload" ]; then
        log "模拟模式: 只打包不上传"
        log "临时文件: $TEMP_BACKUP"
        cleanup_temp
        log "🎉 完成"
        exit 0
    fi

    # 尝试上传路由器，失败则存本地
    if ! upload_to_router; then
        save_local
    fi

    cleanup_local
    cleanup_remote 2>/dev/null || true
    cleanup_temp
    log "🎉 备份完成！"
}

main "$@"
