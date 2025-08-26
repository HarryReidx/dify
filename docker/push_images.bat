@echo off
setlocal enabledelayedexpansion

REM Docker镜像推送脚本 - Windows批处理版本
REM 作者: AI Assistant
REM 日期: %date% %time%

REM 配置
set "REGISTRY=registry.cn-beijing.aliyuncs.com/tsingyun_baseline/ty-dify"
set "LOG_DIR=push_logs"
set "SUCCESS_LOG=%LOG_DIR%\success.log"
set "FAILED_LOG=%LOG_DIR%\failed.log"
set "SUMMARY_LOG=%LOG_DIR%\summary.log"

REM 创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 清空之前的日志
echo. > "%SUCCESS_LOG%"
echo. > "%FAILED_LOG%"
echo. > "%SUMMARY_LOG%"

REM 计数器
set /a SUCCESS_COUNT=0
set /a FAILED_COUNT=0
set /a TOTAL_COUNT=0

echo [INFO] 开始批量推送Docker镜像到阿里云仓库
echo [INFO] 目标仓库: %REGISTRY%
echo [INFO] 日志目录: %LOG_DIR%

REM 检查Docker是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker未运行或无权限访问
    pause
    exit /b 1
)

echo [INFO] Docker运行正常，开始处理镜像...

REM 定义镜像处理函数
goto :main

:process_image
set "source_image=%~1"
set "target_tag=%~2"
set "target_image=%REGISTRY%:%target_tag%"

echo [INFO] 处理镜像: %source_image% -^> %target_tag%

REM 检查源镜像是否存在
docker image inspect "%source_image%" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] 源镜像不存在，尝试拉取: %source_image%
    docker pull "%source_image%" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] 无法拉取镜像: %source_image%
        echo %date% %time% [ERROR] 无法拉取镜像: %source_image% >> "%FAILED_LOG%"
        set /a FAILED_COUNT+=1
        goto :eof
    )
)

REM 标记镜像
docker tag "%source_image%" "%target_image%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 标记失败: %source_image% -^> %target_image%
    echo %date% %time% [ERROR] 标记失败: %source_image% -^> %target_image% >> "%FAILED_LOG%"
    set /a FAILED_COUNT+=1
    goto :eof
)

echo [INFO] 标记成功，开始推送: %target_image%

REM 推送镜像
docker push "%target_image%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 推送失败: %target_image%
    echo %date% %time% [ERROR] 推送失败: %target_image% >> "%FAILED_LOG%"
    set /a FAILED_COUNT+=1
) else (
    echo [SUCCESS] 推送成功: %target_image%
    echo %date% %time% [SUCCESS] 推送成功: %target_image% >> "%SUCCESS_LOG%"
    set /a SUCCESS_COUNT+=1
)

goto :eof

:main
REM 核心服务镜像
set /a TOTAL_COUNT+=1
call :process_image "langgenius/dify-api:1.7.2" "dify-api-1.7.2"

set /a TOTAL_COUNT+=1
call :process_image "dify-web:ty-1.0" "dify-web-ty-1.0"

set /a TOTAL_COUNT+=1
call :process_image "postgres:15-alpine" "postgres-15-alpine"

set /a TOTAL_COUNT+=1
call :process_image "redis:6-alpine" "redis-6-alpine"

set /a TOTAL_COUNT+=1
call :process_image "langgenius/dify-sandbox:0.2.12" "dify-sandbox-0.2.12"

set /a TOTAL_COUNT+=1
call :process_image "langgenius/dify-plugin-daemon:0.2.0-local" "dify-plugin-daemon-0.2.0-local"

set /a TOTAL_COUNT+=1
call :process_image "nginx:latest" "nginx-latest"

set /a TOTAL_COUNT+=1
call :process_image "ubuntu/squid:latest" "ubuntu-squid-latest"

set /a TOTAL_COUNT+=1
call :process_image "certbot/certbot" "certbot-certbot"

REM 向量数据库镜像
set /a TOTAL_COUNT+=1
call :process_image "semitechnologies/weaviate:1.19.0" "weaviate-1.19.0"

set /a TOTAL_COUNT+=1
call :process_image "langgenius/qdrant:v1.7.3" "qdrant-v1.7.3"

set /a TOTAL_COUNT+=1
call :process_image "pgvector/pgvector:pg16" "pgvector-pg16"

set /a TOTAL_COUNT+=1
call :process_image "vastdata/vastbase-vector" "vastbase-vector"

set /a TOTAL_COUNT+=1
call :process_image "tensorchord/pgvecto-rs:pg16-v0.3.0" "pgvecto-rs-pg16-v0.3.0"

set /a TOTAL_COUNT+=1
call :process_image "ghcr.io/chroma-core/chroma:0.5.20" "chroma-0.5.20"

set /a TOTAL_COUNT+=1
call :process_image "oceanbase/oceanbase-ce:4.3.5-lts" "oceanbase-ce-4.3.5-lts"

set /a TOTAL_COUNT+=1
call :process_image "container-registry.oracle.com/database/free:latest" "oracle-database-free-latest"

set /a TOTAL_COUNT+=1
call :process_image "opengauss/opengauss:7.0.0-RC1" "opengauss-7.0.0-RC1"

set /a TOTAL_COUNT+=1
call :process_image "myscale/myscaledb:1.6.4" "myscaledb-1.6.4"

set /a TOTAL_COUNT+=1
call :process_image "matrixorigin/matrixone:2.1.1" "matrixone-2.1.1"

REM Milvus 相关镜像
set /a TOTAL_COUNT+=1
call :process_image "quay.io/coreos/etcd:v3.5.5" "etcd-v3.5.5"

set /a TOTAL_COUNT+=1
call :process_image "minio/minio:RELEASE.2023-03-20T20-16-18Z" "minio-RELEASE.2023-03-20T20-16-18Z"

set /a TOTAL_COUNT+=1
call :process_image "milvusdb/milvus:v2.5.15" "milvus-v2.5.15"

REM OpenSearch 相关镜像
set /a TOTAL_COUNT+=1
call :process_image "opensearchproject/opensearch:latest" "opensearch-latest"

set /a TOTAL_COUNT+=1
call :process_image "opensearchproject/opensearch-dashboards:latest" "opensearch-dashboards-latest"

REM Elasticsearch 相关镜像
set /a TOTAL_COUNT+=1
call :process_image "docker.elastic.co/elasticsearch/elasticsearch:8.14.3" "elasticsearch-8.14.3"

set /a TOTAL_COUNT+=1
call :process_image "docker.elastic.co/kibana/kibana:8.14.3" "kibana-8.14.3"

REM 其他服务镜像
set /a TOTAL_COUNT+=1
call :process_image "downloads.unstructured.io/unstructured-io/unstructured-api:latest" "unstructured-api-latest"

REM 输出统计结果
echo.
echo =============== 推送完成 ===============
echo 总计: %TOTAL_COUNT% 个镜像
echo 成功: %SUCCESS_COUNT% 个镜像
echo 失败: %FAILED_COUNT% 个镜像
echo.

if %FAILED_COUNT% gtr 0 (
    echo [ERROR] 失败的镜像列表:
    type "%FAILED_LOG%"
    echo.
)

echo [INFO] 详细日志保存在: %LOG_DIR%\
echo [INFO] - 成功日志: %SUCCESS_LOG%
echo [INFO] - 失败日志: %FAILED_LOG%
echo [INFO] - 汇总日志: %SUMMARY_LOG%

echo.
echo 按任意键退出...
pause >nul
