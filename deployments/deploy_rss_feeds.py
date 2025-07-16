#!/usr/bin/env uv run
"""
RSS Feed 部署脚本
用于部署多个网站的 RSS 生成任务
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv

load_dotenv()

from flows.sitemap_to_rss import sitemap_to_rss_flow


def get_git_repository_url() -> str:
    """获取当前 Git 仓库的远程 URL"""
    try:
        # 获取 origin remote 的 URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=project_root, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # 如果获取失败，返回默认值
        return "https://github.com/user/repo.git"


def load_sites_config(config_path: str = "deployments/sites_rss_config.yaml") -> dict[str, Any]:
    """加载网站配置文件"""
    config_file = project_root / config_path

    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_file}")

    with open(config_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def merge_with_defaults(site_config: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """将站点配置与默认配置合并"""
    merged = {}

    # 合并 options
    merged_options = defaults.get("options", {}).copy()
    merged_options.update(site_config.get("options", {}))

    # 合并 channel_config
    merged_channel = defaults.get("channel_config", {}).copy()
    merged_channel.update(site_config.get("channel_config", {}))

    # 复制其他配置
    merged.update(site_config)
    merged["options"] = merged_options
    merged["channel_config"] = merged_channel

    # 如果没有指定 schedule，使用默认值
    if "schedule" not in merged:
        merged["schedule"] = defaults.get("schedule", "0 */6 * * *")

    # 如果没有指定 work_pool_name，使用默认值
    if "work_pool_name" not in merged:
        merged["work_pool_name"] = defaults.get("work_pool_name", "default")

    # 如果没有指定 source_repository，使用默认值
    if "source_repository" not in merged:
        merged["source_repository"] = defaults.get("source_repository", get_git_repository_url())

    # 如果没有指定 entrypoint，使用默认值
    if "entrypoint" not in merged:
        merged["entrypoint"] = defaults.get("entrypoint", "flows/sitemap_to_rss.py:sitemap_to_rss_flow")

    return merged


def deploy_single_site(site_name: str, site_config: dict[str, Any], use_r2: bool = True) -> None:
    """部署单个网站的 RSS 生成任务"""
    print(f"部署 {site_name} RSS 任务...")

    if not site_config.get("enabled", True):
        print(f"  跳过 {site_name}：已禁用")
        return

    try:
        # 准备部署参数
        deploy_params = {
            "sitemap_url": site_config["sitemap_url"],
            "channel_config": site_config["channel_config"],
            "output_file": site_config["output"]["local_file"],
            "filter_config": site_config.get("filter_config"),
            "fetch_titles": site_config["options"].get("fetch_titles", True),
            "max_items": site_config["options"].get("max_items", 30),
            "sort_by_date": site_config["options"].get("sort_by_date", True),
        }

        if use_r2:
            deploy_params.update(
                {
                    "r2_object_key": site_config["output"]["r2_object_key"],
                    "upload_method": site_config["options"].get("upload_method", "direct"),
                    "r2_config": None,  # 使用环境变量配置
                }
            )
            deployment_name = f"rss-r2-{site_name}"
        else:
            deployment_name = f"rss-{site_name}"

        # 创建部署
        sitemap_to_rss_flow.from_source(
            source=site_config.get("source_repository", get_git_repository_url()),
            entrypoint=site_config.get("entrypoint", "flows/sitemap_to_rss.py:sitemap_to_rss_flow"),
        ).deploy(
            name=deployment_name,
            work_pool_name=site_config.get("work_pool_name", "default"),
            cron=site_config["schedule"],
            parameters=deploy_params,
            ignore_warnings=True,
            description=f"RSS feed generation for {site_name}",
            tags=["rss", "sitemap", site_name, "auto-generated"],
        )

        print(f"  ✅ {site_name} 部署成功: {deployment_name}")
        print(f"     调度: {site_config['schedule']}")
        print(f"     输出: {site_config['output']['r2_object_key'] if use_r2 else site_config['output']['local_file']}")

    except Exception as e:
        print(f"  ❌ {site_name} 部署失败: {e}")


def deploy_all_sites(use_r2: bool = True, config_path: str = "deployments/sites_rss_config.yaml") -> None:
    """部署所有网站的 RSS 生成任务"""
    try:
        # 加载配置
        config = load_sites_config(config_path)
        sites = config.get("sites", {})
        defaults = config.get("defaults", {})

        print(f"开始部署 RSS 任务，共 {len(sites)} 个网站")
        print(f"使用 R2 上传: {'是' if use_r2 else '否'}")
        print("-" * 50)

        # 部署每个网站
        enabled_count = 0
        for site_name, site_config in sites.items():
            # 与默认配置合并
            merged_config = merge_with_defaults(site_config, defaults)

            # 部署站点
            deploy_single_site(site_name, merged_config, use_r2)

            if merged_config.get("enabled", True):
                enabled_count += 1

        print("-" * 50)
        print(f"部署完成！启用的网站数: {enabled_count}/{len(sites)}")

    except Exception as e:
        print(f"部署失败: {e}")
        sys.exit(1)


def list_sites(config_path: str = "deployments/sites_rss_config.yaml") -> None:
    """列出所有配置的网站"""
    try:
        config = load_sites_config(config_path)
        sites = config.get("sites", {})

        print(f"配置的网站列表 (共 {len(sites)} 个):")
        print("-" * 60)

        for site_name, site_config in sites.items():
            status = "✅ 启用" if site_config.get("enabled", True) else "❌ 禁用"
            schedule = site_config.get("schedule", config.get("defaults", {}).get("schedule", "未设置"))

            print(f"{site_name:20} | {status:8} | {schedule:15} | {site_config['sitemap_url']}")

    except Exception as e:
        print(f"读取配置失败: {e}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="RSS Feed 部署管理工具")
    parser.add_argument(
        "action",
        choices=["deploy", "deploy-local", "list"],
        help="执行的操作: deploy(部署到R2), deploy-local(仅本地), list(列出配置)",
    )
    parser.add_argument(
        "--config",
        default="deployments/sites_rss_config.yaml",
        help="配置文件路径 (默认: deployments/sites_rss_config.yaml)",
    )
    parser.add_argument("--site", help="仅部署指定的网站")

    args = parser.parse_args()

    if args.action == "list":
        list_sites(args.config)
    elif args.action == "deploy":
        if args.site:
            # 部署单个网站
            config = load_sites_config(args.config)
            sites = config.get("sites", {})
            defaults = config.get("defaults", {})

            if args.site in sites:
                merged_config = merge_with_defaults(sites[args.site], defaults)
                deploy_single_site(args.site, merged_config, use_r2=True)
            else:
                print(f"错误: 网站 '{args.site}' 在配置中不存在")
                print(f"可用的网站: {', '.join(sites.keys())}")
                sys.exit(1)
        else:
            # 部署所有网站
            deploy_all_sites(use_r2=True, config_path=args.config)
    elif args.action == "deploy-local":
        if args.site:
            # 部署单个网站（仅本地）
            config = load_sites_config(args.config)
            sites = config.get("sites", {})
            defaults = config.get("defaults", {})

            if args.site in sites:
                merged_config = merge_with_defaults(sites[args.site], defaults)
                deploy_single_site(args.site, merged_config, use_r2=False)
            else:
                print(f"错误: 网站 '{args.site}' 在配置中不存在")
                sys.exit(1)
        else:
            # 部署所有网站（仅本地）
            deploy_all_sites(use_r2=False, config_path=args.config)


if __name__ == "__main__":
    main()
