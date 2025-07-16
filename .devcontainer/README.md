# Dev Container 配置

这个 dev container 配置为 Perfect 工作流平台提供了完整的开发环境。

## 包含的工具和扩展

### 基础环境
- **Python 3.13**: 项目要求的Python版本
- **Node.js 22**: 用于安装 Claude Code CLI
- **Docker-in-Docker**: 支持容器化工作流测试
- **uv**: 现代化Python包管理器

### VS Code 扩展
- **Python支持**: python, pylint, black-formatter, mypy-type-checker
- **代码质量**: ruff (linting), pytest (测试)
- **文件格式**: yaml, json 支持
- **AI辅助**: github.copilot

### 预配置设置
- 代码格式化：Black (120字符行长度)
- 代码检查：Ruff
- 测试框架：pytest
- 保存时自动格式化和导入排序

## 端口转发

- **8000**: Prefect UI
- **4200**: Prefect Server

## 使用方法

1. **打开项目**: 在 VS Code 中打开项目，会自动提示在容器中重新打开
2. **等待初始化**: 首次启动会运行 `setup.sh` 脚本安装所有依赖
3. **配置环境变量**: 复制 `.env.example` 到 `.env` 并配置必要变量
4. **开始开发**: 所有工具和依赖都已准备就绪

## 文件挂载

- `.env` 文件会从主机挂载到容器中，便于管理敏感配置

## 常用命令

在容器内可以直接使用项目的所有命令:

```bash
# 安装依赖
uv sync

# 启动 Prefect Worker
uv run prefect worker start --pool default

# 运行测试
uv run pytest

# 代码质量检查
uv run ruff check .
uv run black .
uv run mypy .

# 运行工作流示例
python flows/content_analysis_flow.py
```

## 故障排除

1. **uv 命令未找到**: 重新运行 `bash .devcontainer/setup.sh`
2. **端口访问问题**: 检查端口转发配置
3. **权限问题**: 确保 `setup.sh` 有执行权限