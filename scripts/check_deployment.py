#!/usr/bin/env python3
"""
AI Survey Assistant - 部署前检查脚本
在部署到生产环境前运行此脚本，检查所有必需配置是否正确
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def check_env_file():
    """检查 .env 文件是否存在"""
    print("\n" + "=" * 60)
    print("1. 检查环境变量文件")
    print("=" * 60)
    
    if not Path(".env").exists():
        print_error(".env 文件不存在")
        print_info("请复制 .env.example 并重命名为 .env")
        print_info("命令: cp .env.example .env")
        return False
    
    print_success(".env 文件存在")
    
    # 检查文件权限（Unix系统）
    if sys.platform != "win32":
        import stat
        file_stat = os.stat(".env")
        permissions = oct(file_stat.st_mode)[-3:]
        if permissions != "600":
            print_warning(f".env 文件权限为 {permissions}，建议设置为 600")
            print_info("命令: chmod 600 .env")
        else:
            print_success(".env 文件权限正确 (600)")
    
    return True

def check_required_env_vars():
    """检查必需的环境变量"""
    print("\n" + "=" * 60)
    print("2. 检查必需的环境变量")
    print("=" * 60)
    
    load_dotenv()
    
    required_vars = {
        "DASHSCOPE_API_KEY": "阿里云通义千问 API Key",
        "SECRET_KEY": "Session 加密密钥",
    }
    
    recommended_vars = {
        "ENVIRONMENT": "运行环境 (建议: production)",
        "ALLOWED_HOSTS": "允许的主机列表",
        "APP_PORT": "应用端口",
    }
    
    all_ok = True
    
    # 检查必需变量
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value == f"your_{var.lower()}_here" or "your_" in value:
            print_error(f"{var} 未设置或仍是默认值")
            print_info(f"  {description}")
            all_ok = False
        else:
            # 不显示完整的密钥，只显示前后几位
            if "KEY" in var or "SECRET" in var:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print_success(f"{var} = {masked}")
            else:
                print_success(f"{var} = {value}")
    
    # 检查推荐变量
    print("\n推荐配置:")
    for var, description in recommended_vars.items():
        value = os.getenv(var)
        if value:
            print_success(f"{var} = {value}")
        else:
            print_warning(f"{var} 未设置")
            print_info(f"  {description}")
    
    return all_ok

def check_environment_mode():
    """检查是否为生产环境模式"""
    print("\n" + "=" * 60)
    print("3. 检查环境模式")
    print("=" * 60)
    
    env = os.getenv("ENVIRONMENT", "development")
    
    if env.lower() == "production":
        print_success(f"环境模式: {env} (生产环境)")
        return True
    else:
        print_warning(f"环境模式: {env} (非生产环境)")
        print_info("生产部署建议设置 ENVIRONMENT=production")
        return False

def check_security_settings():
    """检查安全设置"""
    print("\n" + "=" * 60)
    print("4. 检查安全设置")
    print("=" * 60)
    
    all_ok = True
    
    # 检查 SECRET_KEY 强度
    secret_key = os.getenv("SECRET_KEY", "")
    if len(secret_key) < 32:
        print_error("SECRET_KEY 太短（应至少32字符）")
        print_info("生成强密钥: python -c \"import secrets; print(secrets.token_hex(32))\"")
        all_ok = False
    else:
        print_success("SECRET_KEY 长度充足")
    
    # 检查 ALLOWED_HOSTS
    allowed_hosts = os.getenv("ALLOWED_HOSTS", "")
    if not allowed_hosts or allowed_hosts == "localhost,127.0.0.1":
        print_warning("ALLOWED_HOSTS 仅包含 localhost")
        print_info("生产环境请添加您的域名和服务器IP")
    else:
        hosts = [h.strip() for h in allowed_hosts.split(",")]
        print_success(f"ALLOWED_HOSTS 包含 {len(hosts)} 个主机:")
        for host in hosts:
            print(f"    - {host}")
    
    return all_ok

def check_dependencies():
    """检查依赖文件"""
    print("\n" + "=" * 60)
    print("5. 检查依赖文件")
    print("=" * 60)
    
    files = ["requirements.txt", "run_all.py"]
    all_exist = True
    
    for file in files:
        if Path(file).exists():
            print_success(f"{file} 存在")
        else:
            print_error(f"{file} 不存在")
            all_exist = False
    
    # 检查 Python 环境
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 8:
        print_success(f"Python 版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print_error(f"Python 版本过低: {python_version.major}.{python_version.minor}.{python_version.micro}")
        print_info("需要 Python 3.8 或更高版本")
        all_exist = False
    
    return all_exist

def check_data_directories():
    """检查数据目录"""
    print("\n" + "=" * 60)
    print("6. 检查数据目录")
    print("=" * 60)
    
    directories = [
        "data",
        "data/surveys",
        "data/responses",
        "data/analyses",
        "data/chroma_db"
    ]
    
    for directory in directories:
        path = Path(directory)
        if path.exists():
            print_success(f"{directory}/ 存在")
        else:
            print_warning(f"{directory}/ 不存在（将在首次运行时自动创建）")

def check_api_key():
    """检查 API Key 格式"""
    print("\n" + "=" * 60)
    print("7. 检查 API Key")
    print("=" * 60)
    
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    
    if not api_key or api_key == "your_dashscope_api_key_here":
        print_error("API Key 未设置或仍是默认值")
        print_info("请访问 https://dashscope.console.aliyun.com/apiKey 获取")
        return False
    
    # 基本格式检查
    if api_key.startswith("sk-"):
        print_success("API Key 格式看起来正确")
        return True
    else:
        print_warning("API Key 格式可能不正确（通常以 sk- 开头）")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🔍 AI Survey Assistant - 部署前检查")
    print("=" * 60)
    
    checks = [
        ("环境变量文件", check_env_file),
        ("必需环境变量", check_required_env_vars),
        ("环境模式", check_environment_mode),
        ("安全设置", check_security_settings),
        ("依赖文件", check_dependencies),
        ("数据目录", check_data_directories),
        ("API Key", check_api_key),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print_error(f"检查 {check_name} 时出错: {e}")
            results.append((check_name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 检查结果总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n通过检查: {passed}/{total}")
    
    if passed == total:
        print_success("\n✓ 所有检查通过！可以进行部署。")
        return 0
    else:
        print_warning("\n⚠ 部分检查未通过，请修复后再部署。")
        print("\n未通过的检查:")
        for check_name, result in results:
            if not result:
                print(f"  - {check_name}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        print("\n" + "=" * 60)
        print("检查完成")
        print("=" * 60 + "\n")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n检查已取消")
        sys.exit(1)

