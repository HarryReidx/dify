#!/bin/bash

# =============================================================================
# 批量Docker镜像拉取脚本 - 带重试机制
# 用途: 批量拉取镜像，支持失败重试和断点续传
# 执行方式: chmod +x batch_pull.sh && ./batch_pull.sh
# =============================================================================

REGISTRY="registry.cn-beijing.aliyuncs.com/tsingyun_baseline/ty-dify"
MAX_RETRIES=3
RETRY_DELAY=5

# 镜像配置：标签:大小:描述
declare -A IMAGE_CONFIG=(
    ["dify-api-1.7.2"]="2.24GB:Dify API服务"
    ["dify-web-ty-1.0"]="546MB:Dify Web前端 v1.0"
    ["dify-web-ty-1.1"]="537MB:Dify Web前端 v1.1"
    ["postgres-15-alpine"]="262.7MB:PostgreSQL数据库"
    ["minio-RELEASE.2025-06-13T11-33-47Z"]="175MB:MinIO对象存储"
    ["nginx-latest"]="117.4MB:Nginx反向代理"
    ["weaviate-1.19.0"]="52.5MB:Weaviate向量数据库"
    ["redis-6-alpine"]="30.2MB:Redis缓存数据库"
)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] ✅ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}"
}

# 检查镜像是否已存在
check_image_exists() {
    local image="$1"
    docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image}$"
}

# 拉取单个镜像（带重试）
pull_image_with_retry() {
    local tag="$1"
    local image="${REGISTRY}:${tag}"
    local config="${IMAGE_CONFIG[$tag]}"
    local size=$(echo "$config" | cut -d':' -f1)
    local desc=$(echo "$config" | cut -d':' -f2)
    
    log "开始拉取: ${tag}"
    log "  描述: ${desc}"
    log "  大小: ${size}"
    
    # 检查是否已存在
    if check_image_exists "$image"; then
        log_warning "镜像已存在，跳过: ${tag}"
        return 0
    fi
    
    local attempt=1
    while [ $attempt -le $MAX_RETRIES ]; do
        log "  尝试 ${attempt}/${MAX_RETRIES}..."
        
        if timeout 1800 docker pull "$image"; then
            log_success "拉取成功: ${tag}"
            return 0
        else
            log_error "拉取失败: ${tag} (尝试 ${attempt}/${MAX_RETRIES})"
            
            if [ $attempt -lt $MAX_RETRIES ]; then
                log "等待 ${RETRY_DELAY} 秒后重试..."
                sleep $RETRY_DELAY
            fi
            
            ((attempt++))
        fi
    done
    
    log_error "拉取最终失败: ${tag}"
    return 1
}

# 主函数
main() {
    echo -e "${PURPLE}==================== Dify镜像批量拉取工具 ====================${NC}"
    echo -e "${BLUE}镜像仓库: ${REGISTRY}${NC}"
    echo -e "${BLUE}最大重试: ${MAX_RETRIES} 次${NC}"
    echo -e "${BLUE}重试间隔: ${RETRY_DELAY} 秒${NC}"
    echo -e "${BLUE}镜像总数: ${#IMAGE_CONFIG[@]} 个${NC}"
    echo
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! systemctl is-active --quiet docker; then
        log "启动Docker服务..."
        sudo systemctl start docker || {
            log_error "无法启动Docker服务"
            exit 1
        }
    fi
    
    # 显示镜像列表
    log "准备拉取以下镜像:"
    for tag in "${!IMAGE_CONFIG[@]}"; do
        local config="${IMAGE_CONFIG[$tag]}"
        local size=$(echo "$config" | cut -d':' -f1)
        local desc=$(echo "$config" | cut -d':' -f2)
        echo "  - ${tag} (${size}) - ${desc}"
    done
    echo
    
    # 确认开始
    read -p "是否开始拉取? [Y/n]: " -r
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log "用户取消操作"
        exit 0
    fi
    
    # 开始拉取
    local start_time=$(date +%s)
    local success_count=0
    local failed_count=0
    local failed_images=()
    
    # 按大小排序（大镜像优先）
    local sorted_tags=($(for tag in "${!IMAGE_CONFIG[@]}"; do
        local size=$(echo "${IMAGE_CONFIG[$tag]}" | cut -d':' -f1)
        echo "${size} ${tag}"
    done | sort -hr | cut -d' ' -f2))
    
    log "开始按大小顺序拉取镜像..."
    
    for tag in "${sorted_tags[@]}"; do
        echo
        if pull_image_with_retry "$tag"; then
            ((success_count++))
        else
            ((failed_count++))
            failed_images+=("$tag")
        fi
    done
    
    # 计算总耗时
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    # 显示结果
    echo
    echo -e "${PURPLE}==================== 拉取结果 ====================${NC}"
    log_success "成功拉取: ${success_count} 个镜像"
    
    if [ $failed_count -gt 0 ]; then
        log_error "拉取失败: ${failed_count} 个镜像"
        log "失败的镜像:"
        for failed_tag in "${failed_images[@]}"; do
            echo "  - ${failed_tag}"
        done
    fi
    
    log "总耗时: ${minutes}分${seconds}秒"
    
    # 显示已拉取的镜像
    echo
    log "已拉取的镜像列表:"
    docker images "${REGISTRY}:*" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"
    
    # 清理
    log "清理临时文件..."
    docker system prune -f > /dev/null 2>&1 || true
    
    echo
    if [ $failed_count -eq 0 ]; then
        log_success "所有镜像拉取完成！"
    else
        log_warning "部分镜像拉取失败，请检查网络连接后重新运行脚本"
        exit 1
    fi
}

# 运行主函数
main "$@"
