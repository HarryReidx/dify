#!/bin/bash

# =============================================================================
# 快速Docker镜像拉取脚本 - 简化版
# 用途: 快速并行拉取所有Dify相关镜像
# 执行方式: chmod +x quick_pull.sh && ./quick_pull.sh
# =============================================================================

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 配置
REGISTRY="registry.cn-beijing.aliyuncs.com/tsingyun_baseline/ty-dify"
PARALLEL_JOBS=4

# 镜像列表
IMAGES=(
    "dify-api-1.7.2"
    "dify-web-ty-1.0"
    "dify-web-ty-1.1"
    "postgres-15-alpine"
    "minio-RELEASE.2025-06-13T11-33-47Z"
    "nginx-latest"
    "weaviate-1.19.0"
    "redis-6-alpine"
)

echo -e "${BLUE}==================== 快速拉取Dify镜像 ====================${NC}"
echo -e "${BLUE}镜像仓库: ${REGISTRY}${NC}"
echo -e "${BLUE}并行任务: ${PARALLEL_JOBS}${NC}"
echo -e "${BLUE}镜像数量: ${#IMAGES[@]}${NC}"
echo

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker未安装${NC}"
    exit 1
fi

if ! systemctl is-active --quiet docker; then
    echo -e "${YELLOW}启动Docker服务...${NC}"
    sudo systemctl start docker
fi

# 拉取函数
pull_image() {
    local tag=$1
    local image="${REGISTRY}:${tag}"
    echo -e "${BLUE}拉取: ${tag}${NC}"
    if docker pull "$image"; then
        echo -e "${GREEN}✅ 成功: ${tag}${NC}"
    else
        echo -e "${RED}❌ 失败: ${tag}${NC}"
        return 1
    fi
}

# 并行拉取
echo -e "${YELLOW}开始并行拉取镜像...${NC}"
export -f pull_image
export REGISTRY GREEN BLUE RED NC

# 使用xargs并行执行
printf '%s\n' "${IMAGES[@]}" | xargs -n 1 -P $PARALLEL_JOBS -I {} bash -c 'pull_image "$@"' _ {}

echo
echo -e "${GREEN}==================== 拉取完成 ====================${NC}"
echo -e "${BLUE}检查已拉取的镜像:${NC}"
docker images "${REGISTRY}:*" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
echo
echo -e "${GREEN}所有镜像拉取完成！${NC}"
