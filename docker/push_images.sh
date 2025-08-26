#!/bin/bash

# Docker镜像推送脚本 - 支持多线程和日志记录
# 作者: AI Assistant
# 日期: $(date)

# 配置
REGISTRY="registry.cn-beijing.aliyuncs.com/tsingyun_baseline/ty-dify"
MAX_PARALLEL_JOBS=4  # 最大并行任务数
LOG_DIR="./push_logs"
SUCCESS_LOG="$LOG_DIR/success.log"
FAILED_LOG="$LOG_DIR/failed.log"
SUMMARY_LOG="$LOG_DIR/summary.log"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 清空之前的日志
> "$SUCCESS_LOG"
> "$FAILED_LOG"
> "$SUMMARY_LOG"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1" >> "$SUMMARY_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1" >> "$SUCCESS_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1" >> "$SUMMARY_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >> "$FAILED_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >> "$SUMMARY_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1" >> "$SUMMARY_LOG"
}

# 处理单个镜像的函数
process_image() {
    local source_image="$1"
    local target_tag="$2"
    local target_image="$REGISTRY:$target_tag"
    
    log_info "开始处理镜像: $source_image -> $target_tag"
    
    # 检查源镜像是否存在
    if ! docker image inspect "$source_image" >/dev/null 2>&1; then
        log_warning "源镜像不存在，尝试拉取: $source_image"
        if ! docker pull "$source_image" 2>/dev/null; then
            log_error "无法拉取镜像: $source_image"
            return 1
        fi
    fi
    
    # 标记镜像
    if docker tag "$source_image" "$target_image" 2>/dev/null; then
        log_info "标记成功: $source_image -> $target_image"
    else
        log_error "标记失败: $source_image -> $target_image"
        return 1
    fi
    
    # 推送镜像
    if docker push "$target_image" 2>/dev/null; then
        log_success "推送成功: $target_image"
        return 0
    else
        log_error "推送失败: $target_image"
        return 1
    fi
}

# 镜像列表 (源镜像:目标标签)
declare -A IMAGES=(
    # 核心服务镜像
    ["langgenius/dify-api:1.7.2"]="dify-api-1.7.2"
    ["dify-web:ty-1.0"]="dify-web-ty-1.0"
    ["postgres:15-alpine"]="postgres-15-alpine"
    ["redis:6-alpine"]="redis-6-alpine"
    ["langgenius/dify-sandbox:0.2.12"]="dify-sandbox-0.2.12"
    ["langgenius/dify-plugin-daemon:0.2.0-local"]="dify-plugin-daemon-0.2.0-local"
    ["nginx:latest"]="nginx-latest"
    ["ubuntu/squid:latest"]="ubuntu-squid-latest"
    ["certbot/certbot"]="certbot-certbot"
    
    # 向量数据库镜像
    ["semitechnologies/weaviate:1.19.0"]="weaviate-1.19.0"
    ["langgenius/qdrant:v1.7.3"]="qdrant-v1.7.3"
    ["pgvector/pgvector:pg16"]="pgvector-pg16"
    ["vastdata/vastbase-vector"]="vastbase-vector"
    ["tensorchord/pgvecto-rs:pg16-v0.3.0"]="pgvecto-rs-pg16-v0.3.0"
    ["ghcr.io/chroma-core/chroma:0.5.20"]="chroma-0.5.20"
    ["oceanbase/oceanbase-ce:4.3.5-lts"]="oceanbase-ce-4.3.5-lts"
    ["container-registry.oracle.com/database/free:latest"]="oracle-database-free-latest"
    ["opengauss/opengauss:7.0.0-RC1"]="opengauss-7.0.0-RC1"
    ["myscale/myscaledb:1.6.4"]="myscaledb-1.6.4"
    ["matrixorigin/matrixone:2.1.1"]="matrixone-2.1.1"
    
    # Milvus 相关镜像
    ["quay.io/coreos/etcd:v3.5.5"]="etcd-v3.5.5"
    ["minio/minio:RELEASE.2023-03-20T20-16-18Z"]="minio-RELEASE.2023-03-20T20-16-18Z"
    ["milvusdb/milvus:v2.5.15"]="milvus-v2.5.15"
    
    # OpenSearch 相关镜像
    ["opensearchproject/opensearch:latest"]="opensearch-latest"
    ["opensearchproject/opensearch-dashboards:latest"]="opensearch-dashboards-latest"
    
    # Elasticsearch 相关镜像
    ["docker.elastic.co/elasticsearch/elasticsearch:8.14.3"]="elasticsearch-8.14.3"
    ["docker.elastic.co/kibana/kibana:8.14.3"]="kibana-8.14.3"
    
    # 其他服务镜像
    ["downloads.unstructured.io/unstructured-io/unstructured-api:latest"]="unstructured-api-latest"
)

# 主函数
main() {
    log_info "开始批量推送Docker镜像到阿里云仓库"
    log_info "目标仓库: $REGISTRY"
    log_info "最大并行任务数: $MAX_PARALLEL_JOBS"
    log_info "总镜像数量: ${#IMAGES[@]}"
    
    # 检查Docker是否运行
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker未运行或无权限访问"
        exit 1
    fi
    
    # 检查是否已登录阿里云仓库
    log_info "检查Docker仓库登录状态..."
    if ! docker pull "$REGISTRY:test" 2>/dev/null; then
        log_warning "可能未登录到阿里云仓库，请确保已执行: docker login registry.cn-beijing.aliyuncs.com"
    fi
    
    local success_count=0
    local failed_count=0
    local total_count=${#IMAGES[@]}
    
    # 使用GNU parallel或xargs实现并行处理
    if command -v parallel >/dev/null 2>&1; then
        log_info "使用GNU parallel进行并行处理"
        export -f process_image log_info log_success log_error log_warning
        export REGISTRY SUCCESS_LOG FAILED_LOG SUMMARY_LOG RED GREEN YELLOW BLUE NC
        
        # 创建临时文件存储镜像列表
        temp_file=$(mktemp)
        for source_image in "${!IMAGES[@]}"; do
            echo "$source_image ${IMAGES[$source_image]}" >> "$temp_file"
        done
        
        # 并行处理
        parallel -j "$MAX_PARALLEL_JOBS" --colsep ' ' process_image {1} {2} :::: "$temp_file"
        rm "$temp_file"
    else
        log_warning "GNU parallel未安装，使用后台任务模拟并行处理"
        
        # 使用后台任务模拟并行处理
        local job_count=0
        for source_image in "${!IMAGES[@]}"; do
            target_tag="${IMAGES[$source_image]}"
            
            # 控制并行任务数量
            while [ $(jobs -r | wc -l) -ge $MAX_PARALLEL_JOBS ]; do
                sleep 1
            done
            
            # 后台执行
            process_image "$source_image" "$target_tag" &
            ((job_count++))
            
            log_info "已启动任务 $job_count/$total_count: $source_image"
        done
        
        # 等待所有后台任务完成
        wait
    fi
    
    # 统计结果
    success_count=$(wc -l < "$SUCCESS_LOG" 2>/dev/null || echo 0)
    failed_count=$(wc -l < "$FAILED_LOG" 2>/dev/null || echo 0)
    
    log_info "=============== 推送完成 ==============="
    log_info "总计: $total_count 个镜像"
    log_success "成功: $success_count 个镜像"
    log_error "失败: $failed_count 个镜像"
    
    if [ $failed_count -gt 0 ]; then
        log_error "失败的镜像列表:"
        cat "$FAILED_LOG"
    fi
    
    log_info "详细日志保存在: $LOG_DIR/"
    log_info "- 成功日志: $SUCCESS_LOG"
    log_info "- 失败日志: $FAILED_LOG"
    log_info "- 汇总日志: $SUMMARY_LOG"
}

# 信号处理
trap 'log_error "脚本被中断"; exit 1' INT TERM

# 执行主函数
main "$@"
