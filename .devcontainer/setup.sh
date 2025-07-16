#!/bin/bash

# Dev Container 初始化脚本
# 为 Perfect 工作流平台配置开发环境

set -e

echo "🚀 初始化 Perfect 开发环境..."

# 安装 uv 包管理器
echo "📦 安装 uv 包管理器..."
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 添加 uv 到 PATH
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/.cargo/bin:$PATH"

# 验证 uv 安装
echo "✅ 验证 uv 安装..."
uv --version

# 安装项目依赖
echo "📋 安装项目依赖..."
uv sync

# 安装 Claude Code CLI
echo "🤖 安装 Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# 初始化 Prefect
echo "⚙️ 初始化 Prefect..."
uv run prefect config set PREFECT_API_URL="http://127.0.0.1:4200/api"

# 创建输出目录
echo "📁 创建必要的目录..."
mkdir -p output/content_analysis
mkdir -p output/rss_feeds
mkdir -p output/batch_analysis

# 设置权限
chmod +x .devcontainer/setup.sh

# 显示环境信息
echo "📊 环境信息:"
echo "Python: $(python --version)"
echo "uv: $(uv --version)"
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"

# 提示用户设置环境变量
echo ""
echo "✅ 开发环境设置完成！"
echo ""
echo "📝 下一步:"
echo "1. 复制 .env.example 到 .env 并配置必要的环境变量"
echo "2. 如需使用内容分析功能，请设置 OPENAI_API_KEY"
echo "3. 如需使用 R2 存储，请配置 R2 相关环境变量"
echo ""
echo "🚀 常用命令:"
echo "  uv run prefect worker start --pool default  # 启动 Prefect Worker"
echo "  uv run pytest                                # 运行测试"
echo "  uv run ruff check .                         # 代码检查"
echo "  uv run black .                              # 代码格式化"
echo ""