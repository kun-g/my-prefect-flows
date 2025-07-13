# 快速开始指南

## 🚀 5分钟快速上手

本指南将帮助你在5分钟内设置并运行 RSS 生成和 R2 上传功能。

## 前置要求

- Python ≥ 3.13
- Cloudflare 账户（用于 R2 存储）
- 网络连接

## 步骤 1: 安装依赖

```bash
# 克隆项目后，安装依赖
uv sync

# 或使用 pip
pip install -r requirements.txt
```

## 步骤 2: 配置 Cloudflare R2

### 2.1 创建 R2 存储桶

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 导航到 **R2 Object Storage**
3. 点击 **创建存储桶**
4. 输入存储桶名称（例如：`my-rss-feeds`）
5. 选择位置（建议：自动）
6. 点击 **创建存储桶**

### 2.2 生成 API 令牌

1. 在 R2 控制台，点击 **管理 R2 API 令牌**
2. 点击 **创建 API 令牌**
3. 配置权限：
   - **权限**：对象读写
   - **资源**：包括所有存储桶资源
4. 点击 **继续以显示摘要**
5. 点击 **创建 API 令牌**
6. **重要**：复制并保存以下信息：
   - Account ID
   - Access Key ID  
   - Secret Access Key

### 2.3 设置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

在 `.env` 文件中填入你的配置：

```bash
# Cloudflare R2 配置
R2_ACCOUNT_ID=你的账户ID
R2_ACCESS_KEY_ID=你的访问密钥ID
R2_SECRET_ACCESS_KEY=你的秘密访问密钥
R2_BUCKET_NAME=你的存储桶名称
R2_REGION=auto
# R2_CUSTOM_DOMAIN=你的自定义域名（可选）
```

## 步骤 3: 验证配置

运行配置诊断工具：

```bash
python debug_r2_config.py
```

你应该看到类似输出：
```
✅ .env 文件已加载
=== R2 配置诊断 ===

1. 环境变量检查:
   ✅ R2_ACCOUNT_ID: your-account-id
   ✅ R2_ACCESS_KEY_ID: your-access-key
   ✅ R2_SECRET_ACCESS_KEY: ***
   ✅ R2_BUCKET_NAME: your-bucket
   ✅ R2_REGION: auto

2. R2Config 验证:
   ✅ 配置验证通过
```

## 步骤 4: 运行第一个示例

### 4.1 基础示例

```bash
# 运行完整示例
python example_r2_usage.py
```

### 4.2 生成特定网站的 RSS

```bash
# 运行主流程（使用预配置的 Prefect 博客）
python flows/sitemap_to_rss.py
```

成功运行后，你会看到：
```
✅ RSS 生成并上传到 R2 流程完成! 访问URL: https://your-bucket.your-account.r2.cloudflarestorage.com/feeds/prefect-blog.xml
```

## 步骤 5: 自定义你的 RSS feed

### 5.1 添加新网站

编辑 `flows/sitemap_to_rss.py` 中的 `SAMPLE_CONFIGS`：

```python
SAMPLE_CONFIGS = {
    # 现有配置...
    
    "my-website": {
        "sitemap_url": "https://mywebsite.com/sitemap.xml",
        "channel_config": {
            "title": "我的网站更新",
            "link": "https://mywebsite.com",
            "description": "最新文章和更新",
            "language": "zh-CN"
        },
        "filter_config": {
            "include_patterns": ["/posts/", "/articles/"],
            "exclude_patterns": ["/tags/"],
            "max_items": 20
        },
        "output_file": "output/my-website-rss.xml",
        "r2_object_key": "feeds/my-website.xml"
    }
}
```

### 5.2 运行自定义配置

```python
from flows.sitemap_to_rss import sitemap_to_rss_with_r2_flow, SAMPLE_CONFIGS

config = SAMPLE_CONFIGS["my-website"]

result = sitemap_to_rss_with_r2_flow(
    sitemap_url=config["sitemap_url"],
    channel_config=config["channel_config"],
    r2_object_key=config["r2_object_key"],
    filter_config=config["filter_config"],
    max_items=20,
    upload_method="direct"
)

print(f"RSS URL: {result['r2_upload']['file_url']}")
```

## 常见用法

### 仅生成本地 RSS（不上传）

```python
from flows.sitemap_to_rss import sitemap_to_rss_flow

result = sitemap_to_rss_flow(
    sitemap_url="https://example.com/sitemap.xml",
    channel_config={
        "title": "示例网站",
        "link": "https://example.com",
        "description": "最新更新"
    },
    output_file="my-feed.xml",
    max_items=10
)
```

### 生成并上传到 R2

```python
from flows.sitemap_to_rss import sitemap_to_rss_with_r2_flow

result = sitemap_to_rss_with_r2_flow(
    sitemap_url="https://example.com/sitemap.xml",
    channel_config={
        "title": "示例网站",
        "link": "https://example.com", 
        "description": "最新更新"
    },
    r2_object_key="feeds/example.xml",
    max_items=10
)

if result["r2_upload"]["success"]:
    print(f"RSS 已上传: {result['r2_upload']['file_url']}")
```

### 批量处理多个网站

```python
from flows.sitemap_to_rss import SAMPLE_CONFIGS, sitemap_to_rss_with_r2_flow

for name, config in SAMPLE_CONFIGS.items():
    print(f"处理 {name}...")
    result = sitemap_to_rss_with_r2_flow(**config)
    
    if result and result["r2_upload"]["success"]:
        print(f"✅ {name}: {result['r2_upload']['file_url']}")
    else:
        print(f"❌ {name}: 处理失败")
```

## 定时任务设置

使用 Prefect 设置定时任务：

```bash
# 部署流程
uv run prefect deployment build flows/sitemap_to_rss.py:sitemap_to_rss_with_r2_flow -p local-process

# 启动工作进程
uv run prefect worker start --pool local-process
```

或使用 Python 代码：

```python
from flows.sitemap_to_rss import deploy_rss_feeds_with_r2

# 部署所有预配置网站的定时任务（每6小时）
deploy_rss_feeds_with_r2()
```

## 故障排除

### 配置问题

如果遇到 "R2 配置不完整" 错误：

1. 确认 `.env` 文件存在且有内容
2. 运行诊断工具：`python debug_r2_config.py`
3. 检查环境变量是否正确设置

### 网络问题

如果上传失败：

1. 检查网络连接
2. 验证 R2 凭证是否正确
3. 确认存储桶名称和权限

### RSS 生成问题

如果 RSS 为空：

1. 检查 sitemap URL 是否可访问
2. 验证过滤规则是否过于严格
3. 查看执行日志了解详情

## 下一步

- 📖 阅读 [完整文档](./r2-upload-integration.md)
- 🔧 了解 [高级配置选项](./r2-upload-integration.md#配置说明)
- 🎯 探索 [最佳实践](./r2-upload-integration.md#最佳实践)
- 🚀 设置 [生产环境部署](./r2-upload-integration.md#部署和调度)

## 需要帮助？

- 查看 [故障排除指南](./r2-upload-integration.md#故障排除)
- 运行诊断工具：`python debug_r2_config.py`
- 查看示例代码：`example_r2_usage.py`