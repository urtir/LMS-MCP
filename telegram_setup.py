#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup Script for Telegram Security Bot
Install dependencies and configure environment
"""

import subprocess
import sys
import os
import logging

def run_command(command, description):
    """Run command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def install_requirements():
    """Install required Python packages"""
    print("📦 Installing Python packages...")
    
    # Core packages that should be available
    core_packages = [
        "python-telegram-bot==20.7",
        "schedule==1.2.0", 
        "reportlab==4.0.7",
        "matplotlib==3.7.2",
        "Pillow==10.1.0",
        "pandas==2.1.1",
        "httpx==0.25.0",
        "pydantic==2.4.2",
        "python-dotenv==1.0.0",
        "requests==2.31.0"
    ]
    
    success_count = 0
    for package in core_packages:
        print(f"Installing {package}...")
        if run_command([sys.executable, "-m", "pip", "install", package], f"Installing {package}"):
            success_count += 1
        else:
            print(f"⚠️  Failed to install {package}, but continuing...")
    
    print(f"📦 Installed {success_count}/{len(core_packages)} packages")
    return success_count > len(core_packages) // 2  # At least half should succeed

def check_existing_components():
    """Check if existing components are available"""
    print("🔍 Checking existing components...")
    
    required_files = [
        "database.py",
        "mcp_tool_bridge.py", 
        "wazuh_fastmcp_server.py",
        "wazuh_archives.db"
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ Found {file}")
        else:
            print(f"❌ Missing {file}")
            missing_files.append(file)
    
    if missing_files:
        print(f"⚠️  Warning: {len(missing_files)} required files are missing:")
        for file in missing_files:
            print(f"   - {file}")
        print("Make sure all existing components are in the same directory")
        return False
    
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = ["config", "logs"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"ℹ️  Directory already exists: {directory}")
    
    print("✅ Directory setup completed")
    return True

def check_lm_studio():
    """Check LM Studio connection"""
    print("🤖 Checking LM Studio connection...")
    
    try:
        import requests
        response = requests.get("http://192.168.56.1:1234/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ LM Studio is accessible")
            return True
        else:
            print(f"⚠️  LM Studio responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to LM Studio: {e}")
        print("Make sure LM Studio is running at http://192.168.56.1:1234")
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("🔧 TELEGRAM SECURITY BOT SETUP")
    print("=" * 60)
    
    setup_steps = [
        ("Creating directories", create_directories),
        ("Installing Python packages", install_requirements),
        ("Checking existing components", check_existing_components),
        ("Checking LM Studio connection", check_lm_studio)
    ]
    
    results = []
    for step_name, step_function in setup_steps:
        print(f"\n📋 Step: {step_name}")
        print("-" * 40)
        try:
            result = step_function()
            results.append((step_name, result))
        except Exception as e:
            print(f"❌ Error in {step_name}: {e}")
            results.append((step_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SETUP SUMMARY")
    print("=" * 60)
    
    success_count = 0
    for step_name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{status}: {step_name}")
        if result:
            success_count += 1
    
    print(f"\n🎯 Setup completed: {success_count}/{len(results)} steps successful")
    
    if success_count == len(results):
        print("\n🚀 Ready to start! Run the following commands:")
        print("\n1. Start FastMCP Server:")
        print("   python wazuh_fastmcp_server.py")
        print("\n2. Start Telegram Bot:")
        print("   python telegram_bot_main.py")
        print("\nOr run both with:")
        print("   python telegram_bot_main.py")
        print("   (FastMCP server will be started automatically)")
    else:
        print("\n⚠️  Some setup steps failed. Please resolve issues before running the bot.")
        print("\nCommon issues:")
        print("- Install missing Python packages manually")
        print("- Make sure LM Studio is running")
        print("- Check that all database files exist")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
