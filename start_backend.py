#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Backend API服务启动脚本

使用方法：
python start_backend.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

if __name__ == '__main__':
    try:
        # 导入并启动后端应用
        from backend.main import app
        
        print("=" * 50)
        print("CICD流水线管理系统 - Backend API服务")
        print("=" * 50)
        print("服务地址: http://0.0.0.0:5000")
        print("健康检查: http://0.0.0.0:5000/api/health")
        print("系统信息: http://0.0.0.0:5000/api/system/info")
        print("API文档: 参见 doc/YAML配置API接口文档.md")
        print("=" * 50)
        
        # 启动Flask应用
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装所有依赖包：")
        print("pip install flask flask-cors psycopg2-binary requests pyyaml")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1) 