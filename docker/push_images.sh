#!/bin/bash

# ============================================================================
# Docker镜像推送脚本 - TsingYun Baseline
# ============================================================================

# 版本配置 - 统一管理所有镜像版本
VERSION="1.11.1"

# 仓库配置
REGISTRY="registry.cn-beijing.aliyuncs.com/tsingyun_baseline/ty-dify"

# 日志配置
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

# 推送单个镜像的函数
push_image() {
    local name="$1"
    local target_image="$REGISTRY:${name}-${VERSION}"

    log_info "开始推送镜像: $name"

    # 检查镜像是否存在
    if ! docker image inspect "$target_image" >/dev/null 2>&1; then
        log_error "镜像不存在: $target_image"
        log_warning "请先运行 ./build_images.sh 构建镜像"
        return 1
    fi

    # 推送镜像
    log_info "推送中: $target_image"
    if docker push "$target_image" 2>&1 | tee -a "$SUMMARY_LOG"; then
        log_success "推送成功: $target_image"
        return 0
    else
        log_error "推送失败: $target_image"
        return 1
    fi
}

# 主函数
main() {
    log_info "============================================"
    log_info "开始推送 TsingYun Dify 镜像到阿里云仓库"
    log_info "============================================"
    log_info "版本: $VERSION"
    log_info "仓库: $REGISTRY"

    # 检查Docker是否运行
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker未运行或无权限访问"
        exit 1
    fi

    # 检查是否已登录阿里云仓库
    log_info ""
    log_info "检查Docker仓库登录状态..."
    if ! docker login --username=your_username --password-stdin registry.cn-beijing.aliyuncs.com < /dev/null 2>/dev/null; then
        log_warning "未登录到阿里云仓库"
        log_warning "请先执行: docker login registry.cn-beijing.aliyuncs.com"
        log_warning "继续尝试推送..."
    fi

    local success_count=0
    local failed_count=0

    # 推送 API 镜像
    log_info ""
    log_info "----------------------------------------"
    log_info "推送 Dify API 镜像"
    log_info "----------------------------------------"
    if push_image "dify-api"; then
        ((success_count++))
    else
        ((failed_count++))
    fi

    # 推送 Web 镜像
    log_info ""
    log_info "----------------------------------------"
    log_info "推送 Dify Web 镜像"
    log_info "----------------------------------------"
    if push_image "dify-web"; then
        ((success_count++))
    else
        ((failed_count++))
    fi

    # 推送 Quiz Flask Service 镜像
    log_info ""
    log_info "----------------------------------------"
    log_info "推送 Quiz Flask Service 镜像"
    log_info "----------------------------------------"
    if push_image "quiz-flask-service"; then
        ((success_count++))
    else
        ((failed_count++))
    fi

    # 统计结果
    local total_count=$((success_count + failed_count))

    echo ""
    echo "============================================"
    echo "           推送任务汇总报告"
    echo "============================================"
    echo ""
    echo "📊 统计信息:"
    echo "   总镜像数: $total_count"
    echo "   ✅ 成功: $success_count"
    echo "   ❌ 失败: $failed_count"
    echo ""

    if [ $failed_count -gt 0 ]; then
        echo "❌ 推送失败的镜像:"
        echo ""
        while IFS= read -r line; do
            echo "   • $line"
        done < "$FAILED_LOG"
        echo ""
        echo "详细错误日志: $FAILED_LOG"
        echo ""
        echo "============================================"
        echo "           ❌ 推送失败"
        echo "============================================"
        echo ""
        echo "脚本将在 3 秒后退出..."
        sleep 3
        exit 1
    fi

    echo "✅ 成功推送的镜像:"
    echo "   • $REGISTRY:dify-api-$VERSION"
    echo "   • $REGISTRY:dify-web-$VERSION"
    echo "   • $REGISTRY:quiz-flask-service-$VERSION"
    echo ""
    echo "📁 日志文件位置:"
    echo "   • 成功日志: $SUCCESS_LOG"
    echo "   • 失败日志: $FAILED_LOG"
    echo "   • 汇总日志: $SUMMARY_LOG"
    echo ""
    echo "🎉 所有镜像已成功推送到阿里云仓库！"
    echo ""
    echo "============================================"
    echo "           ✅ 推送成功完成"
    echo "============================================"
    echo ""
    echo "脚本将在 3 秒后退出..."
    sleep 3
}

# 信号处理
trap 'log_error "脚本被中断"; exit 1' INT TERM

# 执行主函数
main "$@"
