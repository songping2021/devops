#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path

# 数据库连接配置
DB_CONFIG = {
    'dbname': '',
    'user': '',
    'password': '',
    'host': '',
    'port': ''
}

# GitLab API配置
GITLAB_API_URL = ''
GITLAB_NAMESPACE = 'cicd'  # GitLab命名空间/组
GITLAB_TOKEN = ''  # 替换为你的GitLab访问令牌

# 路径配置
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BASE_PATH = BASE_DIR / "pipelines"
TEMPLATE_PATH = BASE_DIR / "templates"
WORKSPACE_PATH = BASE_DIR / "workspace"

# Flask应用配置
FLASK_CONFIG = {
    'DEBUG': True,
    'HOST': "0.0.0.0",
    'PORT': 5000
}

# 确保必要的目录存在
def ensure_directories():
    """确保必要的目录存在"""
    BASE_PATH.mkdir(exist_ok=True)
    TEMPLATE_PATH.mkdir(exist_ok=True)
    WORKSPACE_PATH.mkdir(exist_ok=True) 