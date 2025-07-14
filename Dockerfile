FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash prefect

RUN chown -R prefect:prefect /app

USER prefect

COPY --chown=prefect:prefect . /app

# 设置环境变量 - 确保虚拟环境的 bin 目录在 PATH 中
ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH="/workspace:$PYTHONPATH"

RUN uv sync --frozen
RUN uv tree

CMD uv run prefect worker start -p "$WORKER_POOL_NAME" --type process