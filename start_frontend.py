#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
前端开发服务器启动脚本

使用方法：
python start_frontend.py
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path
import http.server
import socketserver
import threading
import time

def check_node_available():
    """检查Node.js是否可用"""
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✓ Node.js版本: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_npm_available():
    """检查npm是否可用"""
    try:
        result = subprocess.run(['npm', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✓ npm版本: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_with_npm():
    """使用npm启动开发服务器"""
    frontend_dir = Path(__file__).parent / 'frontend'
    
    print("🚀 使用npm启动前端开发服务器...")
    
    # 检查是否已安装依赖
    if not (frontend_dir / 'node_modules').exists():
        print("📦 安装npm依赖...")
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
    
    # 启动开发服务器
    print("🌐 启动开发服务器...")
    subprocess.run(['npm', 'start'], cwd=frontend_dir)

def start_with_python():
    """使用Python内置服务器启动"""
    frontend_dir = Path(__file__).parent / 'frontend'
    port = 3000
    
    print(f"🚀 使用Python HTTP服务器启动前端...")
    print(f"📁 服务目录: {frontend_dir}")
    print(f"🌐 服务地址: http://localhost:{port}")
    
    # 切换到frontend目录
    os.chdir(frontend_dir)
    
    # 启动HTTP服务器
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            # 简化日志输出
            print(f"📡 {self.address_string()} - {format % args}")
    
    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        print(f"✅ 服务器已启动在端口 {port}")
        
        # 延迟打开浏览器
        def open_browser():
            time.sleep(1)
            webbrowser.open(f'http://localhost:{port}')
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n⏹️  服务器已停止")

def main():
    print("=" * 60)
    print("🎨 CI/CD流水线管理系统 - 前端开发服务器")
    print("=" * 60)
    
    # 检查前端目录是否存在
    frontend_dir = Path(__file__).parent / 'frontend'
    if not frontend_dir.exists():
        print("❌ 错误: frontend目录不存在!")
        print("请确保已正确组织前端文件结构")
        sys.exit(1)
    
    # 检查index.html是否存在
    if not (frontend_dir / 'index.html').exists():
        print("❌ 错误: frontend/index.html文件不存在!")
        sys.exit(1)
    
    print("📋 检查环境...")
    
    # 尝试使用Node.js + npm
    if check_node_available() and check_npm_available():
        print("🎯 使用Node.js开发服务器 (推荐)")
        try:
            start_with_npm()
        except KeyboardInterrupt:
            print("\n⏹️  开发服务器已停止")
        except Exception as e:
            print(f"❌ npm启动失败: {e}")
            print("🔄 回退到Python服务器...")
            start_with_python()
    else:
        print("⚠️  Node.js/npm不可用，使用Python内置服务器")
        print("💡 建议安装Node.js以获得更好的开发体验")
        start_with_python()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1) 