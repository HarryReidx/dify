#!/bin/bash

# =============================================================================
# Docker镜像并行拉取脚本 - CentOS优化版
# 用途: 从阿里云镜像仓库并行拉取所有已推送的Dify相关镜像
# 适用系统: CentOS 7/8/9, RHEL, Rocky Linux
# 执行方式: chmod +x pull_images.sh && ./pull_images.sh
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置参数
REGISTRY="registry.cn-beijing.aliyuncs.com/tsingyun_baseline/ty-dify"
MAX_PARALLEL_JOBS=4  # 最大并行任务数，可根据网络和系统性能调整
PULL_TIMEOUT=1800    # 单个镜像拉取超时时间（秒）
LOG_DIR="./pull_logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建日志目录
mkdir -p "$LOG_DIR"

# 镜像列表 - 按大小排序，大镜像优先拉取
declare -A IMAGES=(
    ["dify-api-1.7.2"]="2.24GB"
    ["dify-web-ty-1.0"]="546MB"
    ["dify-web-ty-1.1"]="537MB"
    ["postgres-15-alpine"]="262.7MB"
    ["minio-RELEASE.2025-06-13T11-33-47Z"]="175MB"
    ["nginx-latest"]="117.4MB"
    ["weaviate-1.19.0"]="52.5MB"
    ["redis-6-alpine"]="30.2MB"
)

# 函数：打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

# 函数：检查Docker是否安装和运行
check_docker() {
    print_message $BLUE "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        print_message $RED "错误: Docker未安装"
        print_message $YELLOW "请先安装Docker: sudo yum install -y docker-ce"
        exit 1
    fi
    
    if ! systemctl is-active --quiet docker; then
        print_message $YELLOW "Docker服务未运行，正在启动..."
        sudo systemctl start docker
        if [ $? -ne 0 ]; then
            print_message $RED "错误: 无法启动Docker服务"
            exit 1
        fi
    fi
    
    print_message $GREEN "Docker环境检查通过"
}

# 函数：检查网络连接
check_network() {
    print_message $BLUE "检查网络连接..."
    
    if ! ping -c 1 registry.cn-beijing.aliyuncs.com &> /dev/null; then
        print_message $RED "错误: 无法连接到阿里云镜像仓库"
        print_message $YELLOW "请检查网络连接或DNS设置"
        exit 1
    fi
    
    print_message $GREEN "网络连接正常"
}

# 函数：检查磁盘空间
check_disk_space() {
    print_message $BLUE "检查磁盘空间..."
    
    local required_space=5000000  # 5GB in KB
    local available_space=$(df /var/lib/docker 2>/dev/null | awk 'NR==2 {print $4}' || df / | awk 'NR==2 {print $4}')
    
    if [ "$available_space" -lt "$required_space" ]; then
        print_message $RED "警告: 磁盘空间不足，建议至少有5GB可用空间"
        print_message $YELLOW "当前可用空间: $(($available_space/1024/1024))GB"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_message $GREEN "磁盘空间充足: $(($available_space/1024/1024))GB"
    fi
}

# 函数：拉取单个镜像
pull_image() {
    local image_tag=$1
    local image_size=$2
    local full_image="${REGISTRY}:${image_tag}"
    local log_file="${LOG_DIR}/pull_${image_tag}_${TIMESTAMP}.log"
    
    print_message $CYAN "开始拉取: ${image_tag} (${image_size})"
    
    # 记录开始时间
    local start_time=$(date +%s)
    
    # 执行拉取命令，使用timeout防止卡死
    if timeout $PULL_TIMEOUT docker pull "$full_image" > "$log_file" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_message $GREEN "✅ 成功拉取: ${image_tag} (耗时: ${duration}秒)"
        echo "SUCCESS: ${image_tag} - ${duration}s" >> "${LOG_DIR}/pull_summary_${TIMESTAMP}.log"
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_message $RED "❌ 拉取失败: ${image_tag} (耗时: ${duration}秒)"
        echo "FAILED: ${image_tag} - ${duration}s" >> "${LOG_DIR}/pull_summary_${TIMESTAMP}.log"
        
        # 显示错误信息
        print_message $YELLOW "错误详情:"
        tail -5 "$log_file" | sed 's/^/  /'
        return 1
    fi
}

# 函数：并行拉取所有镜像
pull_images_parallel() {
    print_message $BLUE "开始并行拉取镜像 (最大并行数: $MAX_PARALLEL_JOBS)"
    
    local pids=()
    local job_count=0
    local total_images=${#IMAGES[@]}
    local completed=0
    local failed=0
    
    # 按镜像大小排序（大镜像优先）
    local sorted_images=($(for img in "${!IMAGES[@]}"; do echo "$img"; done | sort -k1,1))
    
    for image_tag in "${sorted_images[@]}"; do
        image_size=${IMAGES[$image_tag]}
        
        # 控制并行任务数
        while [ ${#pids[@]} -ge $MAX_PARALLEL_JOBS ]; do
            for i in "${!pids[@]}"; do
                if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                    wait "${pids[$i]}"
                    local exit_code=$?
                    if [ $exit_code -eq 0 ]; then
                        ((completed++))
                    else
                        ((failed++))
                    fi
                    unset "pids[$i]"
                fi
            done
            # 重新索引数组
            pids=("${pids[@]}")
            sleep 1
        done
        
        # 启动新的拉取任务
        pull_image "$image_tag" "$image_size" &
        pids+=($!)
        ((job_count++))
        
        print_message $PURPLE "已启动任务 $job_count/$total_images: $image_tag"
    done
    
    # 等待所有任务完成
    print_message $BLUE "等待所有拉取任务完成..."
    for pid in "${pids[@]}"; do
        wait "$pid"
        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            ((completed++))
        else
            ((failed++))
        fi
    done
    
    # 显示最终结果
    print_message $BLUE "==================== 拉取完成 ===================="
    print_message $GREEN "成功拉取: $completed 个镜像"
    if [ $failed -gt 0 ]; then
        print_message $RED "拉取失败: $failed 个镜像"
    fi
    print_message $BLUE "总计镜像: $total_images 个"
    print_message $BLUE "日志目录: $LOG_DIR"
}

# 函数：显示拉取的镜像列表
show_pulled_images() {
    print_message $BLUE "检查已拉取的镜像..."
    echo
    docker images "${REGISTRY}:*" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo
}

# 函数：清理失败的拉取
cleanup_failed_pulls() {
    print_message $BLUE "清理失败的镜像拉取..."
    docker system prune -f > /dev/null 2>&1 || true
}

# 函数：显示使用帮助
show_help() {
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -j, --jobs NUM     设置最大并行任务数 (默认: $MAX_PARALLEL_JOBS)"
    echo "  -t, --timeout SEC  设置单个镜像拉取超时时间 (默认: $PULL_TIMEOUT 秒)"
    echo "  -h, --help         显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0                 # 使用默认设置拉取所有镜像"
    echo "  $0 -j 8            # 使用8个并行任务"
    echo "  $0 -j 2 -t 3600    # 使用2个并行任务，超时时间1小时"
}

# 主函数
main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -j|--jobs)
                MAX_PARALLEL_JOBS="$2"
                shift 2
                ;;
            -t|--timeout)
                PULL_TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_message $RED "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 验证参数
    if ! [[ "$MAX_PARALLEL_JOBS" =~ ^[0-9]+$ ]] || [ "$MAX_PARALLEL_JOBS" -lt 1 ]; then
        print_message $RED "错误: 并行任务数必须是正整数"
        exit 1
    fi
    
    if ! [[ "$PULL_TIMEOUT" =~ ^[0-9]+$ ]] || [ "$PULL_TIMEOUT" -lt 60 ]; then
        print_message $RED "错误: 超时时间必须是大于60的整数"
        exit 1
    fi
    
    print_message $BLUE "==================== Docker镜像拉取脚本 ===================="
    print_message $BLUE "镜像仓库: $REGISTRY"
    print_message $BLUE "并行任务数: $MAX_PARALLEL_JOBS"
    print_message $BLUE "超时时间: $PULL_TIMEOUT 秒"
    print_message $BLUE "镜像总数: ${#IMAGES[@]} 个"
    print_message $BLUE "预计总大小: ~4.0GB"
    echo
    
    # 执行检查
    check_docker
    check_network
    check_disk_space
    
    # 询问用户确认
    print_message $YELLOW "准备拉取以下镜像:"
    for image_tag in "${!IMAGES[@]}"; do
        echo "  - ${REGISTRY}:${image_tag} (${IMAGES[$image_tag]})"
    done
    echo
    
    read -p "是否开始拉取? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_message $YELLOW "用户取消操作"
        exit 0
    fi
    
    # 记录开始时间
    local total_start_time=$(date +%s)
    
    # 开始拉取
    pull_images_parallel
    
    # 清理
    cleanup_failed_pulls
    
    # 计算总耗时
    local total_end_time=$(date +%s)
    local total_duration=$((total_end_time - total_start_time))
    local minutes=$((total_duration / 60))
    local seconds=$((total_duration % 60))
    
    print_message $GREEN "==================== 拉取任务完成 ===================="
    print_message $GREEN "总耗时: ${minutes}分${seconds}秒"
    
    # 显示拉取结果
    show_pulled_images
    
    print_message $BLUE "日志文件保存在: $LOG_DIR"
    print_message $GREEN "所有镜像拉取完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
