#!/bin/bash

# ============================================================================
# Docker镜像构建脚本 - TsingYun Baseline
# ============================================================================

# 版本配置 - 统一管理所有镜像版本
VERSION="1.11.1"

# 仓库配置
REGISTRY="registry.cn-beijing.aliyuncs.com/tsingyun_baseline/ty-dify"

# 日志配置
LOG_DIR="./build_logs"
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
NC='\033[0m'

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

# 构建单个镜像的函数
build_image() {
    local name="$1"
    local context="$2"
    local dockerfile="$3"
    local target_image="$REGISTRY:${name}-${VERSION}"

    log_info "开始构建镜像: $name"
    log_info "构建上下文: $context"
    log_info "Dockerfile: $dockerfile"
    log_info "目标镜像: $target_image"

    # 检查构建上下文是否存在
    if [ ! -d "$context" ]; then
        log_error "构建上下文不存在: $context"
        return 1
    fi

    # 检查Dockerfile是否存在
    if [ ! -f "$context/$dockerfile" ]; then
        log_error "Dockerfile不存在: $context/$dockerfile"
        return 1
    fi

    # 构建镜像
    if docker build -t "$target_image" -f "$context/$dockerfile" "$context" 2>&1 | tee -a "$SUMMARY_LOG"; then
        log_success "构建成功: $target_image"
        return 0
    else
        log_error "构建失败: $target_image"
        return 1
    fi
}

# 主函数
main() {
    log_info "============================================"
    log_info "开始构建 TsingYun Dify 镜像"
    log_info "============================================"
    log_info "版本: $VERSION"
    log_info "仓库: $REGISTRY"

    # 检查Docker是否运行
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker未运行或无权限访问"
        exit 1
    fi

    local success_count=0
    local failed_count=0

    # 构建 API 镜像
    log_info ""
    log_info "----------------------------------------"
    log_info "构建 Dify API 镜像"
    log_info "----------------------------------------"
    if build_image "dify-api" "../api" "Dockerfile"; then
        ((success_count++))
    else
        ((failed_count++))
    fi

    # 构建 Web 镜像
    log_info ""
    log_info "----------------------------------------"
    log_info "构建 Dify Web 镜像"
    log_info "----------------------------------------"
    if build_image "dify-web" "../web" "Dockerfile"; then
        ((success_count++))
    else
        ((failed_count++))
    fi

    # 构建 Quiz Flask Service 镜像
    log_info ""
    log_info "----------------------------------------"
    log_info "构建 Quiz Flask Service 镜像"
    log_info "----------------------------------------"
    if build_image "quiz-flask-service" "./quiz-flask-service" "Dockerfile"; then
        ((success_count++))
    else
        ((failed_count++))
    fi

    # 统计结果
    local total_count=$((success_count + failed_count))

    echo ""
    echo "============================================"
    echo "           构建任务汇总报告"
    echo "============================================"
    echo ""
    echo "📊 统计信息:"
    echo "   总镜像数: $total_count"
    echo "   ✅ 成功: $success_count"
    echo "   ❌ 失败: $failed_count"
    echo ""

    if [ $failed_count -gt 0 ]; then
        echo "❌ 构建失败的镜像:"
        echo ""
        while IFS= read -r line; do
            echo "   • $line"
        done < "$FAILED_LOG"
        echo ""
        echo "详细错误日志: $FAILED_LOG"
        echo ""
        echo "============================================"
        echo "           ❌ 构建失败"
        echo "============================================"
        echo ""
        echo "脚本将在 5 秒后退出..."
        sleep 5
        exit 1
    fi

    echo "✅ 成功构建的镜像:"
    echo "   • $REGISTRY:dify-api-$VERSION"
    echo "   • $REGISTRY:dify-web-$VERSION"
    echo "   • $REGISTRY:quiz-flask-service-$VERSION"
    echo ""
    echo "📁 日志文件位置:"
    echo "   • 成功日志: $SUCCESS_LOG"
    echo "   • 失败日志: $FAILED_LOG"
    echo "   • 汇总日志: $SUMMARY_LOG"
    echo ""
    echo "🚀 下一步操作:"
    echo "   运行 ./push_images.sh 推送镜像到阿里云仓库"
    echo ""
    echo "============================================"
    echo "           ✅ 构建成功完成"
    echo "============================================"
    echo ""
    echo "脚本将在 3 秒后退出..."
    sleep 3
}

# 信号处理
trap 'log_error "脚本被中断"; exit 1' INT TERM

# 执行主函数
main "$@"
