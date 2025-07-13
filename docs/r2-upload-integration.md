# Cloudflare R2 上传集成功能文档

## 概述

本项目集成了 Cloudflare R2 存储服务，实现了从 sitemap 生成 RSS feed 并自动上传到云端存储的完整解决方案。

## 架构设计

### 组件架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sitemap       │───▶│   RSS Generator │───▶│   R2 Uploader   │
│   Parser        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Local File    │    │ Cloudflare R2   │
                       │   Storage       │    │   Storage       │
                       └─────────────────┘    └─────────────────┘
```

### 数据流程

1. **Sitemap 解析**: 从目标网站获取 sitemap.xml
2. **内容过滤**: 应用用户定义的过滤规则
3. **RSS 生成**: 创建符合 RSS 2.0 标准的 XML 文件
4. **R2 上传**: 将生成的 RSS 上传到 Cloudflare R2 存储
5. **URL 返回**: 提供可访问的公开 URL

## 核心模块

### R2Uploader (`lib/r2_uploader.py`)

#### 主要功能
- **配置管理**: 自动从环境变量加载 R2 配置
- **文件上传**: 支持本地文件和字符串内容上传
- **错误处理**: 完整的异常处理和日志记录
- **文件管理**: 提供删除、检查存在、列表等操作

#### 核心类

##### R2Config
```python
@dataclass
class R2Config:
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region: str = "auto"
    custom_domain: Optional[str] = None
```

##### R2Uploader
```python
class R2Uploader:
    def upload_file(self, local_file_path: str, object_key: str) -> Dict[str, Any]
    def upload_string(self, content: str, object_key: str) -> Dict[str, Any]
    def delete_file(self, object_key: str) -> Dict[str, Any]
    def file_exists(self, object_key: str) -> bool
    def list_files(self, prefix: str = "") -> List[Dict]
```

### 扩展的 Prefect 流程

#### 新增 Tasks

##### upload_rss_to_r2
- **功能**: 直接上传 RSS 字符串内容到 R2
- **参数**: RSS XML 内容、对象键、R2 配置
- **返回**: 上传结果字典

##### upload_rss_file_to_r2
- **功能**: 上传本地 RSS 文件到 R2
- **参数**: 本地文件路径、对象键、R2 配置
- **返回**: 上传结果字典

#### 新增 Flow

##### sitemap_to_rss_with_r2_flow
- **功能**: 完整的 sitemap → RSS → R2 流程
- **特性**: 
  - 支持两种上传模式
  - 包含详细的执行状态反馈
  - 保持向后兼容性

## 配置说明

### 环境变量配置

所有配置通过环境变量管理，支持 `.env` 文件自动加载：

```bash
# 必需配置
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=your-r2-bucket-name

# 可选配置
R2_REGION=auto
R2_CUSTOM_DOMAIN=your-custom-domain.com
```

### RSS 频道配置

```python
channel_config = {
    "title": "频道标题",
    "link": "网站链接",
    "description": "频道描述",
    "language": "zh-CN",  # ISO 语言代码
    "ttl": 60  # 缓存时间（分钟）
}
```

### 过滤器配置

```python
filter_config = {
    "include_patterns": ["/blog/", "/news/"],  # 包含模式
    "exclude_patterns": ["/tag/", "/page/"],   # 排除模式
    "max_items": 50  # 最大条目数
}
```

## 使用方式

### 基础使用

#### 1. 仅生成本地 RSS
```python
from flows.sitemap_to_rss import sitemap_to_rss_flow

result = sitemap_to_rss_flow(
    sitemap_url="https://example.com/sitemap.xml",
    channel_config={
        "title": "Example Site Updates",
        "link": "https://example.com",
        "description": "Latest updates",
        "language": "zh-CN"
    },
    output_file="output/example.xml",
    max_items=50
)
```

#### 2. 生成并上传到 R2
```python
from flows.sitemap_to_rss import sitemap_to_rss_with_r2_flow

result = sitemap_to_rss_with_r2_flow(
    sitemap_url="https://example.com/sitemap.xml",
    channel_config={
        "title": "Example Site Updates",
        "link": "https://example.com",
        "description": "Latest updates",
        "language": "zh-CN"
    },
    r2_object_key="feeds/example-site.xml",
    upload_method="direct"  # 或 "file"
)
```

### 高级使用

#### 批量处理多个网站
```python
from flows.sitemap_to_rss import SAMPLE_CONFIGS, sitemap_to_rss_with_r2_flow

for name, config in SAMPLE_CONFIGS.items():
    result = sitemap_to_rss_with_r2_flow(
        sitemap_url=config["sitemap_url"],
        channel_config=config["channel_config"],
        r2_object_key=config["r2_object_key"],
        filter_config=config["filter_config"],
        max_items=30
    )
    print(f"{name}: {result['r2_upload']['file_url']}")
```

#### 定时任务部署
```python
from flows.sitemap_to_rss import deploy_rss_feeds_with_r2

# 部署所有预配置网站的定时任务（每6小时执行）
deploy_rss_feeds_with_r2()
```

## URL 生成策略

### 默认 R2 域名
```
https://{bucket_name}.{account_id}.r2.cloudflarestorage.com/{object_key}
```

### 自定义域名
```
https://{custom_domain}/{object_key}
```

## 错误处理

### 常见错误类型

1. **配置错误**
   - 环境变量缺失
   - R2 凭证无效
   - 存储桶不存在

2. **网络错误**
   - 连接超时
   - DNS 解析失败
   - 权限被拒绝

3. **业务逻辑错误**
   - Sitemap 解析失败
   - RSS 生成异常
   - 文件上传失败

### 错误处理机制

- **日志记录**: 所有操作都有详细的日志记录
- **异常捕获**: 完整的异常处理，不会中断整个流程
- **状态返回**: 每个操作都返回详细的状态信息
- **重试机制**: 网络操作支持自动重试

## 安全考虑

### 凭证管理
- 环境变量存储敏感信息
- 支持 `.env` 文件（不应提交到版本控制）
- 日志中自动隐藏敏感信息

### 访问控制
- R2 存储桶权限配置
- API 密钥权限最小化
- 支持自定义域名的 HTTPS 访问

## 性能优化

### 上传优化
- 支持直接内存上传，避免临时文件
- 自动设置正确的 MIME 类型
- 批量操作支持

### 缓存策略
- RSS 生成结果可缓存
- R2 对象 TTL 配置
- CDN 集成支持

## 监控和调试

### 诊断工具
- `debug_r2_config.py`: R2 配置诊断
- 详细的执行日志
- 状态码和错误信息

### 监控指标
- 上传成功率
- 响应时间
- 错误类型统计
- 存储使用量

## 扩展性

### 支持的存储后端
- 当前: Cloudflare R2
- 可扩展: 其他 S3 兼容存储
- 接口标准化设计

### 自定义扩展
- 支持自定义上传器
- 插件式架构
- 配置驱动的行为

## 依赖关系

### 核心依赖
- `boto3>=1.35.0`: S3 兼容 API 客户端
- `python-dotenv>=1.0.0`: 环境变量管理
- `prefect>=3.4.6`: 工作流编排

### 可选依赖
- `httpx`: HTTP 客户端（页面标题抓取）
- `pandas`: 数据处理（如需要）

## 测试和验证

### 单元测试
- R2Config 配置验证
- 上传功能测试
- 错误处理测试

### 集成测试
- 端到端流程测试
- 多网站批量处理测试
- 定时任务执行测试

### 性能测试
- 大文件上传测试
- 并发上传测试
- 长时间运行稳定性测试

## 故障排除

### 常见问题

1. **"R2 配置不完整"错误**
   - 检查 `.env` 文件是否存在且配置正确
   - 确认 `python-dotenv` 已安装
   - 运行 `python debug_r2_config.py` 诊断

2. **上传失败**
   - 验证 R2 凭证和权限
   - 检查网络连接
   - 确认存储桶配置

3. **RSS 生成为空**
   - 检查 sitemap URL 可访问性
   - 验证过滤规则配置
   - 查看详细执行日志

### 调试步骤

1. **配置诊断**
   ```bash
   python debug_r2_config.py
   ```

2. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **测试基础功能**
   ```bash
   python example_r2_usage.py
   ```

## 最佳实践

### 配置管理
- 使用 `.env` 文件存储本地配置
- 生产环境使用系统环境变量
- 定期轮换 API 密钥

### 性能优化
- 合理设置 `max_items` 限制
- 使用 `direct` 上传模式减少 I/O
- 配置适当的过滤规则

### 安全建议
- 不要在代码中硬编码凭证
- 使用最小权限原则配置 API 密钥
- 定期审查存储桶权限

### 运维建议
- 监控上传成功率
- 设置适当的告警阈值
- 定期备份重要配置