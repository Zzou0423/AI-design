#!/bin/bash
# ==========================================
# AI Survey Assistant - 数据备份脚本
# ==========================================
# 
# 用途：备份应用数据
# 使用：./scripts/backup.sh
#
# ==========================================

set -e

# 配置
BACKUP_DIR="./backups"
DATA_DIR="./data"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DATE}.tar.gz"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "AI Survey Assistant - 数据备份"
echo -e "==========================================${NC}"

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 执行备份
echo -e "${BLUE}正在备份数据...${NC}"
tar -czf "${BACKUP_FILE}" \
    --exclude="${DATA_DIR}/chroma_db" \
    "${DATA_DIR}"

# 显示备份信息
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo -e "${GREEN}✓ 备份完成${NC}"
echo "备份文件: ${BACKUP_FILE}"
echo "备份大小: ${BACKUP_SIZE}"

# 清理旧备份（保留最近7天）
echo -e "${BLUE}清理旧备份...${NC}"
find "${BACKUP_DIR}" -name "backup_*.tar.gz" -mtime +7 -delete
echo -e "${GREEN}✓ 清理完成${NC}"

# 列出所有备份
echo ""
echo "现有备份文件:"
ls -lh "${BACKUP_DIR}"/backup_*.tar.gz 2>/dev/null || echo "无备份文件"

