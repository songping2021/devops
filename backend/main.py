#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# 导入配置和工具类
from backend.config.settings import FLASK_CONFIG, ensure_directories
from backend.utils.database import db_manager
from backend.utils.gitlab_client import gitlab_client
from backend.utils.yaml_config_parser import YamlConfigParser
from backend.config.settings import WORKSPACE_PATH, TEMPLATE_PATH

# 导入API蓝图
from backend.api.pipelines import pipelines_bp, init_dependencies as init_pipelines_deps
from backend.api.yaml_config import yaml_config_bp, init_dependencies as init_yaml_deps
from backend.api.task_config import task_config_bp, init_dependencies as init_task_config_deps
from backend.api.config_validation import validation_bp
from backend.api.template_config import template_config_bp, init_dependencies as init_template_config_deps

# 创建Flask应用
app = Flask(__name__)

# 配置CORS以支持跨域请求
CORS(app, 
     origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000", "http://127.0.0.1:8080"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True)

# 确保必要的目录存在
ensure_directories()

# 初始化各模块的依赖项
yaml_parser = YamlConfigParser()
init_pipelines_deps(db_manager, gitlab_client, WORKSPACE_PATH, TEMPLATE_PATH)
init_yaml_deps(YamlConfigParser, gitlab_client, WORKSPACE_PATH)
init_task_config_deps(yaml_parser, gitlab_client, db_manager, WORKSPACE_PATH)
init_template_config_deps(db_manager)

# 注册API蓝图
app.register_blueprint(pipelines_bp)
app.register_blueprint(yaml_config_bp)
app.register_blueprint(task_config_bp)
app.register_blueprint(validation_bp)
app.register_blueprint(template_config_bp)

# 注册GitLab同步API蓝图
try:
    from backend.api.gitlab_sync import gitlab_sync_bp
    app.register_blueprint(gitlab_sync_bp)
    print("✅ GitLab同步API模块已加载")
except ImportError as e:
    print(f"⚠️ GitLab同步模块导入失败: {e}")
    print("GitLab同步功能将不可用")

# 健康检查接口
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': 'Backend API服务运行正常',
        'version': '1.0.0'
    })

# 获取系统信息接口
@app.route('/api/system/info', methods=['GET'])
def get_system_info():
    """获取系统信息"""
    try:
        # 测试数据库连接
        db_status = 'connected'
        try:
            db_manager.execute_query("SELECT 1", fetch_one=True)
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        # 测试GitLab连接
        gitlab_status = 'connected'
        try:
            # 这里可以添加一个简单的GitLab API测试
            gitlab_status = 'configured'
        except Exception as e:
            gitlab_status = f'error: {str(e)}'
        
        return jsonify({
            'database': db_status,
            'gitlab': gitlab_status,
            'workspace_path': str(WORKSPACE_PATH),
            'template_path': str(TEMPLATE_PATH)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 处理CORS预检请求
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'ok'})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,X-Requested-With")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        return response

# 错误处理器
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': '请求参数错误'}), 400

# 兼容性路由 - 将原有的server.py路由转发到新的结构
@app.route('/get_pipelines', methods=['GET'])
def legacy_get_pipelines():
    """兼容性路由：获取流水线列表"""
    return pipelines_bp.view_functions['get_pipelines']()

@app.route('/get_pipeline/<int:pipeline_id>', methods=['GET'])
def legacy_get_pipeline(pipeline_id):
    """兼容性路由：获取单个流水线"""
    return pipelines_bp.view_functions['get_pipeline'](pipeline_id)

@app.route('/create_pipeline', methods=['POST'])
def legacy_create_pipeline():
    """兼容性路由：创建流水线"""
    return pipelines_bp.view_functions['create_pipeline']()

@app.route('/update_pipeline/<int:pipeline_id>', methods=['POST'])
def legacy_update_pipeline(pipeline_id):
    """兼容性路由：更新流水线"""
    return pipelines_bp.view_functions['update_pipeline'](pipeline_id)

@app.route('/delete_pipeline/<int:pipeline_id>', methods=['POST'])
def legacy_delete_pipeline(pipeline_id):
    """兼容性路由：删除流水线"""
    return pipelines_bp.view_functions['delete_pipeline'](pipeline_id)

@app.route('/get_pipeline_tasks/<int:pipeline_id>', methods=['GET'])
def legacy_get_pipeline_tasks(pipeline_id):
    """兼容性路由：获取流水线任务"""
    return pipelines_bp.view_functions['get_pipeline_tasks'](pipeline_id)

# YAML配置兼容性路由
@app.route('/api/yaml_config/update_variables', methods=['POST'])
def legacy_update_variables():
    """兼容性路由：更新YAML变量"""
    return yaml_config_bp.view_functions['update_variables']()

@app.route('/api/yaml_config/get_variables', methods=['GET'])
def legacy_get_variables():
    """兼容性路由：获取YAML变量"""
    return yaml_config_bp.view_functions['get_variables']()

@app.route('/api/yaml_config/update_stage_toggle', methods=['POST'])
def legacy_update_stage_toggle():
    """兼容性路由：更新阶段开关"""
    return yaml_config_bp.view_functions['update_stage_toggle']()

@app.route('/api/yaml_config/update_maven_config', methods=['POST'])
def legacy_update_maven_config():
    """兼容性路由：更新Maven配置"""
    return yaml_config_bp.view_functions['update_maven_config']()

@app.route('/api/yaml_config/update_npm_config', methods=['POST'])
def legacy_update_npm_config():
    """兼容性路由：更新NPM配置"""
    return yaml_config_bp.view_functions['update_npm_config']()

@app.route('/api/yaml_config/update_deploy_config', methods=['POST'])
def legacy_update_deploy_config():
    """兼容性路由：更新部署配置"""
    return yaml_config_bp.view_functions['update_deploy_config']()

@app.route('/api/yaml_config/validate', methods=['GET'])
def legacy_validate_yaml():
    """兼容性路由：验证YAML"""
    return yaml_config_bp.view_functions['validate_yaml']()

# 流水线管理兼容性路由
@app.route('/api/create-pipeline', methods=['POST'])
def api_create_pipeline():
    """API兼容性路由：创建流水线"""
    # 直接导入并调用函数
    from backend.api.pipelines import create_pipeline
    return create_pipeline()

@app.route('/api/pipelines/<int:pipeline_id>', methods=['PUT', 'POST'])
def api_update_pipeline(pipeline_id):
    """API兼容性路由：更新流水线"""
    # 直接导入并调用函数
    from backend.api.pipelines import update_pipeline
    return update_pipeline(pipeline_id)

# 任务管理兼容性路由
@app.route('/api/pipeline/task', methods=['POST'])
def legacy_create_task():
    """兼容性路由：创建任务"""
    # 直接导入并调用函数
    from backend.api.pipelines import create_task
    return create_task()

@app.route('/api/pipeline/task/delete', methods=['POST'])
def legacy_delete_task():
    """兼容性路由：删除任务"""
    # 直接导入并调用函数
    from backend.api.pipelines import delete_task
    return delete_task()

if __name__ == '__main__':
    print("启动Backend API服务...")
    print(f"数据库连接: {db_manager.db_config}")
    print(f"GitLab API: {gitlab_client.api_url}")
    print(f"工作区路径: {WORKSPACE_PATH}")
    print(f"模板路径: {TEMPLATE_PATH}")
    
    app.run(
        host=FLASK_CONFIG['HOST'],
        port=FLASK_CONFIG['PORT'],
        debug=FLASK_CONFIG['DEBUG']
    ) 