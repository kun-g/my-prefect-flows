# RSS 部署管理

这个目录包含了 RSS 订阅生成的配置文件和部署脚本。

## 文件说明

- `sites_rss_config.yaml` - 网站配置文件
- `deploy_rss_feeds.py` - 部署管理脚本
- `README.md` - 使用说明

## 使用方法

### 1. 查看配置的网站列表

```bash
python deployments/deploy_rss_feeds.py list
```

### 2. 部署所有启用的网站（使用 R2 上传）

```bash
python deployments/deploy_rss_feeds.py deploy
```

### 3. 部署所有网站（仅保存到本地文件）

```bash
python deployments/deploy_rss_feeds.py deploy-local
```

### 4. 部署单个网站

```bash
# 部署到 R2
python deployments/deploy_rss_feeds.py deploy --site prefect

# 仅本地部署
python deployments/deploy_rss_feeds.py deploy-local --site prefect
```

### 5. 使用自定义配置文件

```bash
python deployments/deploy_rss_feeds.py deploy --config /path/to/custom_config.yaml
```

## 配置文件格式

### 网站配置

每个网站包含以下配置项：

```yaml
sites:
  website_name:
    enabled: true                    # 是否启用
    sitemap_url: "https://..."       # sitemap URL
    schedule: "0 */6 * * *"          # cron 调度表达式
    channel_config:                  # RSS 频道配置
      title: "网站标题"
      link: "https://..."
      description: "描述"
      language: "zh-CN"
      ttl: 60
    filter_config:                   # 过滤器配置
      include_patterns: ["/blog/"]   # 包含的 URL 模式
      exclude_patterns: ["/tags/"]   # 排除的 URL 模式
      max_items: 20                  # 最大条目数
    options:                         # 生成选项
      fetch_titles: true             # 是否获取页面标题
      sort_by_date: true             # 是否按日期排序
      max_items: 20                  # 最大条目数
      upload_method: "direct"        # 上传方式
    output:                          # 输出配置
      local_file: "output/rss.xml"   # 本地文件路径
      r2_object_key: "feeds/rss.xml" # R2 对象键
```

### 默认配置

可以设置默认值，减少重复配置：

```yaml
defaults:
  schedule: "0 */6 * * *"
  options:
    fetch_titles: true
    sort_by_date: true
    max_items: 30
    upload_method: "direct"
  channel_config:
    language: "zh-CN"
    ttl: 60
```

## 环境变量

确保设置了以下环境变量（用于 R2 上传）：

```bash
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_R2_ACCESS_KEY_ID=your-access-key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-secret-key
CLOUDFLARE_R2_BUCKET_NAME=your-bucket-name
```

## 添加新网站

1. 编辑 `sites_rss_config.yaml`
2. 在 `sites` 部分添加新的网站配置
3. 运行部署命令

## 管理网站

- **启用/禁用**: 修改配置文件中的 `enabled` 字段
- **调整调度**: 修改 `schedule` 字段（cron 表达式）
- **更新过滤规则**: 修改 `filter_config` 部分
- **修改输出路径**: 修改 `output` 部分

## 监控和日志

部署后的任务会在 Prefect UI 中显示，可以通过以下方式监控：

1. 访问 Prefect UI
2. 查看部署列表（以 `rss-` 开头）
3. 监控任务执行状态和日志