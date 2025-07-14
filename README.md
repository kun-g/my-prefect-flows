
# Prefect 多工作流集合平台

基于 Prefect 的多工作流集合平台，用于实现和管理各种自动化工作流。目前包含 RSS 生成工具流，未来将扩展到更多不同类型的工作流和自动化任务。

## 快速开始

### 环境设置

```bash
# 安装依赖
uv sync

# 初始化 Prefect 项目
uv run prefect init

# 启动 Prefect Worker
uv run prefect worker start --pool default
```

### 开发环境

安装开发依赖：
```bash
uv sync --extra dev
```

### 测试

运行测试：
```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_rss_generator.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=lib --cov-report=html

# 并行运行测试
uv run pytest -n auto
```

### 代码质量

代码格式化：
```bash
uv run black .
```

代码检查：
```bash
uv run ruff check .
uv run ruff check . --fix  # 自动修复
```

类型检查：
```bash
uv run mypy .
```

## 工作流

### RSS 生成工作流

从网站 sitemap 生成 RSS feed：

```bash
# 运行 RSS 生成
python flows/sitemap_to_rss.py

# 批量部署 RSS feeds
python deployments/deploy_rss_feeds.py deploy
```

### 其他工作流

更多工作流请参考 `flows/` 目录和 [CLAUDE.md](CLAUDE.md) 文档。

## 架构

- `lib/` - 通用业务逻辑库
- `flows/` - Prefect 工作流定义  
- `deployments/` - 部署配置和脚本
- `tests/` - 单元测试

详细架构说明请参考 [CLAUDE.md](CLAUDE.md)。

## 贡献

1. Fork 项目
2. 创建功能分支
3. 运行测试确保通过
4. 提交 Pull Request

## 参考资料
- https://github.com/AboutRSS/ALL-about-RSS