# 使用官方 Python 3.13 镜像作为基础镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理器
RUN pip install uv

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash prefect

# 复制项目配置文件
COPY pyproject.toml uv.lock ./

# 确保 prefect 用户拥有 /app 目录权限
RUN chown -R prefect:prefect /app

# 切换到 prefect 用户
USER prefect

# 创建虚拟环境并安装依赖
RUN uv sync --frozen

# 复制项目代码
COPY --chown=prefect:prefect . .

# 设置环境变量 - 确保虚拟环境的 bin 目录在 PATH 中
ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

CMD ["tail", "-f", "README.md"]
# CMD ["uv", "run", "prefect", "worker", "start", "-p", "$WORKER_POOL_NAME", "--type", "process"]