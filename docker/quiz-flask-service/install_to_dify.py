#!/usr/bin/env python3
"""
一键安装脚本：将Quiz Generator集成到Dify中

使用方法：
python install_to_dify.py [dify_root_path]

如果不提供dify_root_path，脚本会尝试自动检测
"""

import os
import shutil
import sys
from pathlib import Path


def find_dify_root():
    """自动查找Dify根目录"""
    current_dir = Path(__file__).parent.absolute()
    
    # 从当前目录向上查找，寻找包含api/core/tools的目录
    for parent in [current_dir] + list(current_dir.parents):
        api_tools_path = parent / "api" / "core" / "tools"
        if api_tools_path.exists():
            return parent
    
    return None


def install_to_dify(dify_root_path):
    """安装Quiz Generator到Dify"""
    dify_root = Path(dify_root_path)
    
    # 检查Dify目录结构
    api_tools_path = dify_root / "api" / "core" / "tools" / "builtin_tool" / "providers"
    if not api_tools_path.exists():
        print(f"❌ 错误: 在 {dify_root} 中未找到Dify的工具目录")
        print(f"   期望路径: {api_tools_path}")
        return False
    
    # 源目录和目标目录
    source_dir = Path(__file__).parent / "dify_integration"
    target_dir = api_tools_path / "quiz_generator"
    
    if not source_dir.exists():
        print(f"❌ 错误: 源目录不存在: {source_dir}")
        return False
    
    try:
        # 如果目标目录存在，先备份
        if target_dir.exists():
            backup_dir = target_dir.with_suffix('.backup')
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.move(str(target_dir), str(backup_dir))
            print(f"📦 已备份现有目录到: {backup_dir}")
        
        # 复制文件
        shutil.copytree(str(source_dir), str(target_dir))
        print(f"✅ 成功复制文件到: {target_dir}")
        
        # 验证安装
        required_files = [
            "quiz_generator.py",
            "quiz_generator.yaml",
            "_assets/quiz_generator.svg",
            "tools/save_quiz_and_get_url.py",
            "tools/save_quiz_and_get_url.yaml"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (target_dir / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"⚠️  警告: 以下文件缺失: {missing_files}")
            return False
        
        print("✅ 安装验证通过")
        return True
        
    except Exception as e:
        print(f"❌ 安装失败: {e}")
        return False


def main():
    print("🚀 Quiz Generator Dify集成安装器")
    print("=" * 50)
    
    # 获取Dify根目录
    if len(sys.argv) > 1:
        dify_root_path = sys.argv[1]
        print(f"📁 使用指定的Dify路径: {dify_root_path}")
    else:
        dify_root_path = find_dify_root()
        if dify_root_path:
            print(f"📁 自动检测到Dify路径: {dify_root_path}")
        else:
            print("❌ 无法自动检测Dify路径")
            print("请手动指定Dify根目录:")
            print("python install_to_dify.py /path/to/dify")
            return 1
    
    # 检查路径是否存在
    if not os.path.exists(dify_root_path):
        print(f"❌ 错误: 路径不存在: {dify_root_path}")
        return 1
    
    # 执行安装
    if install_to_dify(dify_root_path):
        print("\n🎉 安装成功!")
        print("\n📋 后续步骤:")
        print("1. 启动Quiz Flask服务:")
        print("   cd docker/quiz-flask-service")
        print("   python main.py")
        print("\n2. 重启Dify API服务:")
        print("   docker-compose restart api")
        print("\n3. 在Dify中配置Quiz Generator工具:")
        print("   - Quiz Service URL: http://127.0.0.1:5006")
        print("\n📖 详细说明请查看: DIFY_INTEGRATION.md")
        return 0
    else:
        print("\n❌ 安装失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
