# 使用官方 Python 3.13 镜像作为基础镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash prefect

# RUN mkdir -p /workspace
# RUN pwd

# RUN chown -R prefect:prefect /workspace

# USER prefect

# RUN pip install uv

# COPY --chown=prefect:prefect /app /workspace

# RUN uv sync --frozen

# 设置环境变量 - 确保虚拟环境的 bin 目录在 PATH 中
# ENV VIRTUAL_ENV="/app/.venv"
# ENV PATH="$VIRTUAL_ENV/bin:$PATH"
# ENV PYTHONPATH="/workspace:$PYTHONPATH"

RUN ls -la
# RUN which uv 

CMD ["ls"]
# CMD ["tail", "-f", "README.md"]
# CMD ["uv", "run", "prefect", "worker", "start", "-p", "$WORKER_POOL_NAME", "--type", "process"]