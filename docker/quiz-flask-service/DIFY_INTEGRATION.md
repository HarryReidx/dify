# Dify集成说明

本文档说明如何将Quiz Generator集成到Dify中，让Agent能够调用试卷生成服务。

## 安装步骤

### 1. 复制集成文件

将 `dify_integration` 目录复制到Dify的内置工具目录：

```bash
# 从quiz-flask-service目录执行
cp -r dify_integration /path/to/dify/api/core/tools/builtin_tool/providers/quiz_generator
```

或者手动复制：
- 源目录：`docker/quiz-flask-service/dify_integration/`
- 目标目录：`api/core/tools/builtin_tool/providers/quiz_generator/`

### 2. 文件结构

复制后的目录结构应该是：
```
api/core/tools/builtin_tool/providers/quiz_generator/
├── __init__.py
├── _assets/
│   └── quiz_generator.svg
├── quiz_generator.py
├── quiz_generator.yaml
└── tools/
    ├── __init__.py
    ├── save_quiz_and_get_url.py
    └── save_quiz_and_get_url.yaml
```

### 3. 启动服务

1. **启动Quiz Flask服务**：
   ```bash
   cd docker/quiz-flask-service
   python main.py
   ```
   服务将在 http://127.0.0.1:5006 启动

2. **重启Dify服务**：
   ```bash
   # 重启Dify API服务以加载新工具
   docker-compose restart api
   ```

## 使用方法

### 1. 在Dify中配置工具

1. 进入Dify管理界面
2. 找到"Quiz Generator"工具
3. 配置工具参数：
   - **Quiz Service URL**: `http://127.0.0.1:5006`

### 2. 在Agent中使用

在Agent的工具配置中添加"Quiz Generator"工具，然后Agent就可以：

1. 接收用户的试题内容（Markdown格式）
2. 调用Quiz Generator工具
3. 返回生成的试卷链接

### 3. 支持的Markdown格式

**单选题**：
```markdown
1. 这是单选题？
- ( ) 选项A
- (x) 正确答案B
- ( ) 选项C
```

**多选题**：
```markdown
2. 这是多选题？
- [x] 正确答案1
- [x] 正确答案2
- [ ] 错误答案
```

**判断题**：
```markdown
3. 这是判断题。
- (x) 正确
- ( ) 错误
```

## 测试

### 1. 测试Flask服务

```bash
cd docker/quiz-flask-service
python -c "
from dify_integration.tools.save_quiz_and_get_url import save_quiz_standalone

content = '''# 测试试卷
1. 测试题？
- (x) 正确
- ( ) 错误'''

result = save_quiz_standalone(content)
print('测试结果:', result)
"
```

### 2. 测试Dify集成

1. 在Dify中创建一个Agent
2. 添加Quiz Generator工具
3. 发送试题内容给Agent
4. 检查是否返回试卷链接

## 故障排除

### 1. 工具未显示
- 确认文件复制到正确位置
- 重启Dify API服务
- 检查日志是否有错误

### 2. 连接失败
- 确认Quiz Flask服务正在运行
- 检查URL配置是否正确
- 确认端口5006未被占用

### 3. 生成失败
- 检查Markdown格式是否正确
- 查看Flask服务日志
- 确认题目格式符合要求

## 功能特性

- ✅ 支持单选题、多选题、判断题
- ✅ 自动题目编号和样式
- ✅ 交互式答题界面
- ✅ 检查答案功能
- ✅ 重新开始功能
- ✅ 响应式设计
- ✅ 错误处理和验证
