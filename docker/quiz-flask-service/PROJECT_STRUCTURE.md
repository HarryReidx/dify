# 项目结构说明

本文档说明Quiz Generator项目的完整结构和各文件的作用。

## 📁 项目目录结构

```
docker/quiz-flask-service/                    # 主项目目录
├── 📄 main.py                                # Flask服务主文件
├── 📄 requirements.txt                       # Python依赖文件
├── 📄 Dockerfile                            # Docker构建文件
├── 📄 LICENSE                               # 开源许可证
├── 📄 README.md                             # 项目说明文档
├── 📄 QUIZ_SYSTEM_GUIDE.md                  # 试卷系统使用指南
├── 📄 DIFY_INTEGRATION.md                   # Dify集成说明
├── 📄 PROJECT_STRUCTURE.md                  # 本文档
├── 📄 install_to_dify.py                    # 一键安装到Dify的脚本
│
├── 📁 app/                                  # Flask应用核心代码
│   ├── 📄 __init__.py
│   ├── 📁 extensions/                       # Markdown扩展
│   │   ├── 📄 __init__.py
│   │   ├── 📄 checkbox.py                   # 多选题扩展
│   │   ├── 📄 radio.py                      # 单选题扩展
│   │   └── 📄 textbox.py                    # 文本框扩展
│   ├── 📁 static/                           # 静态资源
│   │   ├── 📄 app.js                        # 前端JavaScript逻辑
│   │   └── 📄 style.css                     # 样式文件
│   └── 📁 templates/                        # HTML模板
│       └── 📄 quiz.html                     # 试卷模板
│
├── 📁 data/                                 # 生成的试卷文件存储
│   ├── 📄 1754970571.html                   # 示例试卷文件
│   └── 📄 1755049970643.html                # 示例试卷文件
│
├── 📁 markdown-quiz-files/                  # 示例Markdown文件
│   └── 📄 sample-quiz.md                    # 示例试卷Markdown
│
└── 📁 dify_integration/                     # Dify集成文件
    ├── 📄 __init__.py
    ├── 📄 quiz_generator.py                 # Dify工具提供者
    ├── 📄 quiz_generator.yaml               # 工具配置文件
    ├── 📁 _assets/                          # 工具图标
    │   └── 📄 quiz_generator.svg
    └── 📁 tools/                            # 具体工具实现
        ├── 📄 __init__.py
        ├── 📄 save_quiz_and_get_url.py      # 保存试卷工具
        └── 📄 save_quiz_and_get_url.yaml    # 工具配置
```

## 📋 文件功能说明

### 🔧 核心服务文件

- **`main.py`**: Flask服务主文件，提供HTTP API接口
- **`requirements.txt`**: Python依赖包列表
- **`Dockerfile`**: Docker容器构建配置

### 🎨 前端文件

- **`app/static/app.js`**: 前端交互逻辑，处理答题、检查、重置等功能
- **`app/static/style.css`**: 试卷样式定义
- **`app/templates/quiz.html`**: 试卷HTML模板

### 🔌 Markdown扩展

- **`app/extensions/checkbox.py`**: 处理多选题 `[x]` `[ ]` 语法
- **`app/extensions/radio.py`**: 处理单选题 `(x)` `( )` 语法  
- **`app/extensions/textbox.py`**: 处理文本输入框语法

### 🔗 Dify集成

- **`dify_integration/`**: 完整的Dify工具集成包
- **`install_to_dify.py`**: 一键安装脚本，自动将集成包复制到Dify

### 📖 文档文件

- **`README.md`**: 项目主要说明文档
- **`DIFY_INTEGRATION.md`**: Dify集成详细说明
- **`QUIZ_SYSTEM_GUIDE.md`**: 试卷系统使用指南
- **`PROJECT_STRUCTURE.md`**: 本项目结构说明

## 🚀 使用流程

### 1. 独立使用
```bash
cd docker/quiz-flask-service
pip install -r requirements.txt
python main.py
```

### 2. 集成到Dify
```bash
cd docker/quiz-flask-service
python install_to_dify.py
```

### 3. 在Dify中配置
1. 重启Dify API服务
2. 在工具配置中找到"Quiz Generator"
3. 配置服务URL: `http://127.0.0.1:5006`

## ✨ 功能特性

- ✅ **多题型支持**: 单选题、多选题、判断题
- ✅ **交互式界面**: 答题、检查答案、重新开始
- ✅ **Markdown格式**: 简单易用的题目编写格式
- ✅ **Dify集成**: 支持Agent调用生成试卷
- ✅ **响应式设计**: 适配不同设备屏幕
- ✅ **一键安装**: 自动化集成到Dify系统

## 🔧 技术栈

- **后端**: Python Flask
- **前端**: HTML5 + CSS3 + JavaScript
- **Markdown处理**: Python-Markdown + 自定义扩展
- **集成**: Dify内置工具系统
