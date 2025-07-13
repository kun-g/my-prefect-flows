#!/usr/bin/env python3
"""
智能内容分析系统部署脚本
自动化配置和部署流程
"""

import os
import sys
import json
import shutil
from pathlib import Path


def check_environment():
    """检查环境依赖"""
    print("🔍 检查环境依赖...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"❌ Python版本过低: {python_version.major}.{python_version.minor}")
        print("💡 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查必要的包
    required_packages = [
        ('litellm', 'litellm'), 
        ('tiktoken', 'tiktoken'), 
        ('prefect', 'prefect'), 
        ('beautifulsoup4', 'bs4'), 
        ('python-dotenv', 'dotenv'), 
        ('requests', 'requests')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}: 已安装")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name}: 未安装")
    
    if missing_packages:
        print(f"\n💡 请安装缺失的包:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True


def setup_configuration():
    """设置配置文件"""
    print("\n⚙️ 设置配置文件...")
    
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # 检查是否已有配置文件
    config_file = config_dir / "llm_config.json"
    example_file = config_dir / "llm_config.json.example"
    
    if config_file.exists():
        print("✅ 配置文件已存在")
        return True
    
    if not example_file.exists():
        print("❌ 配置模板文件不存在")
        return False
    
    # 复制示例配置
    shutil.copy(example_file, config_file)
    print(f"✅ 已创建配置文件: {config_file}")
    
    # 检查环境变量
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        # 更新配置文件中的API密钥
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新API密钥
            for model in config.get("models", []):
                if "openai" in model.get("model_name", "").lower():
                    model["litellm_params"]["api_key"] = api_key
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print("✅ 已自动配置OpenAI API密钥")
        except Exception as e:
            print(f"⚠️ 自动配置API密钥失败: {e}")
    else:
        print("⚠️ 未检测到OPENAI_API_KEY环境变量")
        print("💡 请手动编辑配置文件或设置环境变量")
    
    return True


def setup_directories():
    """创建必要的目录"""
    print("\n📁 创建目录结构...")
    
    directories = [
        "output",
        "output/content_analysis", 
        "output/batch_analysis",
        "logs",
        "tmp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {directory}")
    
    return True


def create_gitignore():
    """更新.gitignore文件"""
    print("\n📝 更新.gitignore...")
    
    gitignore_entries = [
        "# 智能内容分析系统",
        "config/llm_config.json",
        "output/",
        "logs/",
        "tmp/",
        "*.log",
        "__pycache__/",
        "*.pyc",
        ".pytest_cache/",
        ".coverage"
    ]
    
    gitignore_path = Path(".gitignore")
    
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    else:
        existing_content = ""
    
    new_entries = []
    for entry in gitignore_entries:
        if entry not in existing_content:
            new_entries.append(entry)
    
    if new_entries:
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            if existing_content and not existing_content.endswith('\n'):
                f.write('\n')
            f.write('\n'.join(new_entries) + '\n')
        
        print(f"✅ 已添加 {len(new_entries)} 条.gitignore规则")
    else:
        print("✅ .gitignore已是最新")
    
    return True


def test_basic_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本功能...")
    
    try:
        sys.path.append('.')
        from lib.content_analysis import ContentAnalysis, ScoreDimensions
        from lib.content_optimizer import ContentOptimizer
        from lib.llm_manager import LLMManager
        
        # 测试数据结构
        weights = ScoreDimensions.get_weights()
        print(f"✅ 评分维度: {len(weights)}个")
        
        # 测试内容优化器
        optimizer = ContentOptimizer()
        test_text = "这是一个测试文本。" * 100
        tokens = optimizer.estimate_tokens(test_text)
        print(f"✅ Token计算: {tokens}")
        
        # 测试LLM管理器
        manager = LLMManager()
        print("✅ LLM管理器初始化成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        return False


def create_env_template():
    """创建环境变量模板"""
    print("\n📋 创建环境变量模板...")
    
    env_template = """# 智能内容分析系统环境变量配置

# OpenAI API配置 (必需)
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic API配置 (可选)
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# LLM配置文件路径 (可选)
LLM_CONFIG_PATH=config/llm_config.json

# 并发控制 (可选)
MAX_CONCURRENT_REQUESTS=5
DEFAULT_MAX_TOKENS=4000

# 成本控制 (可选)
DAILY_BUDGET=10.0
COST_ALERT_THRESHOLD=0.8

# 日志级别 (可选)
LOG_LEVEL=INFO

# 输出目录 (可选)
OUTPUT_DIR=output
"""
    
    env_file = Path(".env.content_analysis")
    
    if not env_file.exists():
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_template)
        print(f"✅ 已创建环境变量模板: {env_file}")
        print("💡 请复制到.env并填入真实值")
    else:
        print("✅ 环境变量模板已存在")
    
    return True


def deploy_prefect_flows():
    """部署Prefect工作流"""
    print("\n🚀 部署Prefect工作流...")
    
    try:
        import subprocess
        
        # 检查Prefect状态
        result = subprocess.run(['prefect', 'version'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Prefect未正确安装")
            return False
        
        print(f"✅ Prefect版本: {result.stdout.strip()}")
        
        # 部署工作流
        flow_file = "flows/content_analysis_flow.py"
        if Path(flow_file).exists():
            print(f"📦 部署工作流: {flow_file}")
            
            deploy_cmd = [
                'prefect', 'deployment', 'build',
                f'{flow_file}:content_analysis_flow',
                '-p', 'local-process',
                '--name', 'content-analysis',
                '--description', '智能内容分析工作流'
            ]
            
            result = subprocess.run(deploy_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 工作流部署成功")
                print("💡 使用以下命令启动worker:")
                print("   prefect worker start --pool default")
            else:
                print(f"⚠️ 工作流部署失败: {result.stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Prefect部署失败: {e}")
        return False


def generate_deployment_summary():
    """生成部署总结"""
    print("\n📊 部署总结")
    print("=" * 50)
    
    print("✅ 智能内容分析系统部署完成!")
    
    print("\n📝 下一步操作:")
    print("1. 设置API密钥:")
    print("   export OPENAI_API_KEY='your-api-key'")
    
    print("\n2. 运行测试:")
    print("   python test_content_analysis.py")
    
    print("\n3. 运行示例:")
    print("   python example_content_analysis.py")
    
    print("\n4. 启动Prefect工作流:")
    print("   prefect worker start --pool default")
    
    print("\n5. 运行内容分析:")
    print("   python flows/content_analysis_flow.py")
    
    print(f"\n📚 文档位置:")
    print(f"   docs/content_analysis_guide.md")
    
    print(f"\n⚙️ 配置文件:")
    print(f"   config/llm_config.json")
    print(f"   .env.content_analysis")


def main():
    """主部署函数"""
    print("🚀 智能内容分析系统部署脚本")
    print("=" * 50)
    
    steps = [
        ("检查环境", check_environment),
        ("设置配置", setup_configuration),
        ("创建目录", setup_directories),
        ("更新gitignore", create_gitignore),
        ("创建环境模板", create_env_template),
        ("测试功能", test_basic_functionality),
        ("部署工作流", deploy_prefect_flows)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        
        try:
            success = step_func()
            if not success:
                print(f"❌ {step_name}失败，请检查并重试")
                return False
        except Exception as e:
            print(f"❌ {step_name}异常: {e}")
            return False
    
    generate_deployment_summary()
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)