# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 Prefect 的**多工作流集合平台**，用于实现和管理各种自动化工作流。目前包含 RSS 生成工具流，未来将扩展到更多不同类型的工作流和自动化任务。

## 开发环境设置

### 包管理和依赖
```bash
# 安装依赖（首选方式）
uv sync

# 使用 pip 安装（备选）
pip install -r requirements.txt

# 初始化 Prefect 项目
uv run prefect deployment build sitemap_workflow.py:sitemap_to_todo_workflow -p local-process
```

### 环境要求
- Python ≥ 3.13
- uv 包管理器
- Cloudflare R2 账户（可选，用于云存储）

## 核心架构

### 主要模块结构
- `lib/` - 通用业务逻辑库（按功能领域组织）
  - `sitemap.py` - XML sitemap解析器
  - `rss_generator.py` - RSS 2.0生成器
  - `content_extractor.py` - HTML内容提取工具
  - `r2.py` - Cloudflare R2存储客户端
- `flows/` - Prefect工作流定义（各类工作流的集合）
  - `sitemap_to_rss.py` - RSS生成工作流
  - `sitemap_workflow.py` - Sitemap处理工作流
  - `02-etl.py` - ETL示例工作流（Dev.to API）
- `deployments/` - 部署配置和脚本
  - `sites_rss_config.yaml` - RSS工作流的多站点配置
  - `deploy_rss_feeds.py` - RSS工作流批量部署脚本

### 当前工作流类型
1. **RSS生成工作流**: Sitemap → RSS feed生成 → 云存储上传
2. **内容监控工作流**: Sitemap → TODO列表生成
3. **ETL数据流**: 外部API → 数据处理 → 存储（示例）

### 扩展架构设计
- `lib/` 中按功能域组织通用工具库
- `flows/` 中每个文件代表一类完整的工作流
- `deployments/` 中为每类工作流提供独立的配置和部署脚本

## 常用命令

### 基础开发命令
```bash
# 初始化项目
uv init
uv run prefect init

# 安装依赖
uv sync

# 启动Prefect Worker
uv run prefect worker start --pool default

# 构建和部署工作流（通用模式）
uv run prefect deployment build <flow_file.py>:<flow_function> -p local-process
```

### RSS工作流专用命令
```bash
# 运行RSS生成流程
python flows/sitemap_to_rss.py

# RSS配置诊断
python debug_r2_config.py

# RSS示例运行
python example_r2_usage.py

# RSS批量部署
python deployments/deploy_rss_feeds.py deploy
python deployments/deploy_rss_feeds.py list
```

### 其他工作流示例
```bash
# 运行ETL示例工作流
python 02-etl.py

# 运行Sitemap工作流
python flows/sitemap_workflow.py
```

### Docker操作
```bash
# 构建镜像
docker build -t perfect .

# 运行容器（需要环境变量）
docker run -e WORKER_POOL_NAME=default perfect
```

## 配置说明

### 通用配置
- `prefect.yaml` - Prefect项目配置文件
- `.env` - 环境变量配置（各工作流共享）

### RSS工作流配置
- `deployments/sites_rss_config.yaml` - 多站点RSS生成配置
- 环境变量：R2存储相关配置（R2_ACCOUNT_ID, R2_ACCESS_KEY_ID等）

### 添加新工作流的配置模式
1. 在 `flows/` 中创建新的工作流文件
2. 在 `lib/` 中添加相关工具库（如有需要）
3. 在 `deployments/` 中添加对应的配置文件和部署脚本
4. 更新 `pyproject.toml` 中的依赖（如有需要）

## 关键设计决策

### 多工作流平台架构
- **模块化设计**: `lib/` 提供可复用的通用工具库
- **工作流隔离**: `flows/` 中每个工作流独立，避免相互干扰
- **配置分离**: 每类工作流有独立的配置和部署脚本

### 技术栈选择
- **uv 包管理器**: 现代化替代 pip，更快的依赖解析和安装
- **Prefect 3.x**: 强大的工作流编排，支持本地和云端部署
- **Python 3.13+**: 使用最新语言特性和性能优化

### 可扩展性设计
- **通用库模式**: 新工作流可复用 `lib/` 中的现有工具
- **标准化部署**: 遵循统一的部署和配置模式
- **容器化支持**: 所有工作流都可通过 Docker 运行

## 故障排除

### 通用问题
1. `uv: not found` - 确保正确安装 uv 包管理器
2. Docker 构建失败 - 检查 Dockerfile 中的用户权限和路径
3. Prefect 连接问题 - 验证 Prefect 服务状态和配置

### RSS工作流特定问题
1. R2配置问题 - 运行 `python debug_r2_config.py` 诊断
2. RSS为空 - 检查 sitemap URL 可访问性和过滤规则
3. 上传失败 - 验证 R2 凭证和存储桶权限

### 调试工具
- `debug_r2_config.py` - R2配置验证（RSS工作流）
- `example_r2_usage.py` - RSS功能演示
- Prefect UI - 所有工作流执行状态监控

## 开发注意事项

### 添加新工作流的最佳实践
1. **工具库复用**: 优先使用 `lib/` 中的现有工具，避免重复实现
2. **独立配置**: 为新工作流创建独立的配置文件和部署脚本
3. **标准化接口**: 遵循现有工作流的参数和返回值模式
4. **文档更新**: 在 CLAUDE.md 中添加新工作流的使用说明

### 代码组织原则
- **`lib/`**: 按功能域组织通用工具（如：存储、解析、生成等）
- **`flows/`**: 每个文件包含一个完整的工作流逻辑
- **`deployments/`**: 每类工作流的配置和部署脚本独立管理

### 测试和验证

#### 单元测试框架
- **测试框架**: pytest 作为主要测试框架
- **测试路径**: `tests/` 目录下的所有 `test_*.py` 文件
- **覆盖率检查**: pytest-cov 提供代码覆盖率报告
- **并行测试**: pytest-xdist 支持多进程并行测试

#### 测试命令
```bash
# 运行所有测试
uv run pytest

# 运行特定模块测试
uv run pytest tests/test_rss_generator.py

# 生成覆盖率报告
uv run pytest --cov=lib --cov-report=html

# 并行运行测试
uv run pytest -n auto
```

#### 代码质量工具
- **代码格式化**: black (120字符行长度)
- **代码检查**: ruff (pycodestyle + pyflakes + isort + bugbear)
- **类型检查**: mypy (严格模式)

#### 质量检查命令
```bash
# 代码格式化
uv run black .

# 代码检查和自动修复
uv run ruff check .
uv run ruff check . --fix

# 类型检查
uv run mypy .
```

#### 测试最佳实践
- 为每个新功能编写对应的单元测试
- 保持测试覆盖率在90%以上
- 使用测试标记区分单元测试和集成测试
- 在CI/CD中运行完整的测试套件

### 扩展建议
- 新工作流类型：参考现有 `flows/` 中的模式
- 新工具库：在 `lib/` 中按功能域添加
- 新存储后端：参考 `r2.py` 的客户端封装模式