#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify
from pathlib import Path

# 创建YAML配置API蓝图
yaml_config_bp = Blueprint('yaml_config', __name__, url_prefix='/api/yaml_config')

# 稍后在main.py中初始化依赖项
YamlConfigParser = None
gitlab_client = None
WORKSPACE_PATH = None

def init_dependencies(yaml_parser_class, gitlab_cli, workspace_path):
    """初始化依赖项"""
    global YamlConfigParser, gitlab_client, WORKSPACE_PATH
    YamlConfigParser = yaml_parser_class
    gitlab_client = gitlab_cli
    WORKSPACE_PATH = workspace_path

@yaml_config_bp.route('/update_variables', methods=['POST'])
def update_variables():
    """更新YAML文件中的variables"""
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        variables = data.get('variables', {})
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        if not all([project_id, task_name]):
            return jsonify({'error': '缺少必要参数: project_id, task_name'}), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({'error': f'YAML文件不存在: {yaml_file}'}), 404
        
        # 更新variables
        parser = YamlConfigParser(str(yaml_file))
        parser.update_variables(variables)
        
        # 同步到GitLab
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=f"更新{task_name}的variables配置"
                )
            except Exception as e:
                return jsonify({
                    'message': 'variables更新成功，但GitLab同步失败',
                    'error': str(e)
                })
        
        return jsonify({'message': 'variables更新成功'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@yaml_config_bp.route('/get_variables', methods=['GET'])
def get_variables():
    """获取YAML文件中的variables"""
    try:
        project_id = request.args.get('project_id')
        branch = request.args.get('branch', 'develop')
        task_name = request.args.get('task_name')
        
        if not all([project_id, task_name]):
            return jsonify({'error': '缺少必要参数: project_id, task_name'}), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({'error': f'YAML文件不存在: {yaml_file}'}), 404
        
        # 读取variables
        parser = YamlConfigParser(str(yaml_file))
        variables = parser.get_variables()
        
        return jsonify({'variables': variables})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@yaml_config_bp.route('/update_stage_toggle', methods=['POST'])
def update_stage_toggle():
    """更新阶段开关状态"""
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        stage_name = data.get('stage_name')  # compile, build, deploy
        enabled = data.get('enabled', False)
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        if not all([project_id, task_name, stage_name]):
            return jsonify({'error': '缺少必要参数: project_id, task_name, stage_name'}), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({'error': f'YAML文件不存在: {yaml_file}'}), 404
        
        # 更新阶段开关
        parser = YamlConfigParser(str(yaml_file))
        parser.update_stage_toggle(stage_name, enabled)
        
        # 同步到GitLab
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=f"更新{task_name}的{stage_name}阶段开关状态"
                )
            except Exception as e:
                return jsonify({
                    'message': f'{stage_name}阶段开关更新成功，但GitLab同步失败',
                    'error': str(e)
                })
        
        return jsonify({'message': f'{stage_name}阶段开关更新成功'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@yaml_config_bp.route('/update_maven_config', methods=['POST'])
def update_maven_config():
    """更新Maven编译阶段配置"""
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        config = data.get('config', {})
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        if not all([project_id, task_name]):
            return jsonify({'error': '缺少必要参数: project_id, task_name'}), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({'error': f'YAML文件不存在: {yaml_file}'}), 404
        
        # 更新Maven配置
        parser = YamlConfigParser(str(yaml_file))
        parser.update_maven_config(config)
        
        # 同步到GitLab
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=f"更新{task_name}的Maven编译配置"
                )
            except Exception as e:
                return jsonify({
                    'message': 'Maven编译配置更新成功，但GitLab同步失败',
                    'error': str(e)
                })
        
        return jsonify({'message': 'Maven编译配置更新成功'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@yaml_config_bp.route('/update_npm_config', methods=['POST'])
def update_npm_config():
    """更新NPM编译阶段配置"""
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        config = data.get('config', {})
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        if not all([project_id, task_name]):
            return jsonify({'error': '缺少必要参数: project_id, task_name'}), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({'error': f'YAML文件不存在: {yaml_file}'}), 404
        
        # 更新NPM配置
        parser = YamlConfigParser(str(yaml_file))
        parser.update_npm_config(config)
        
        # 同步到GitLab
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=f"更新{task_name}的NPM编译配置"
                )
            except Exception as e:
                return jsonify({
                    'message': 'NPM编译配置更新成功，但GitLab同步失败',
                    'error': str(e)
                })
        
        return jsonify({'message': 'NPM编译配置更新成功'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@yaml_config_bp.route('/update_deploy_config', methods=['POST'])
def update_deploy_config():
    """更新部署阶段配置"""
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        config = data.get('config', {})
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        if not all([project_id, task_name]):
            return jsonify({'error': '缺少必要参数: project_id, task_name'}), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({'error': f'YAML文件不存在: {yaml_file}'}), 404
        
        # 更新部署配置
        parser = YamlConfigParser(str(yaml_file))
        parser.update_deploy_config(config)
        
        # 同步到GitLab
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=f"更新{task_name}的部署配置"
                )
            except Exception as e:
                return jsonify({
                    'message': '部署配置更新成功，但GitLab同步失败',
                    'error': str(e)
                })
        
        return jsonify({'message': '部署配置更新成功'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@yaml_config_bp.route('/validate', methods=['GET'])
def validate_yaml():
    """验证YAML文件格式"""
    try:
        project_id = request.args.get('project_id')
        branch = request.args.get('branch', 'develop')
        task_name = request.args.get('task_name')
        
        if not all([project_id, task_name]):
            return jsonify({'error': '缺少必要参数: project_id, task_name'}), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({'error': f'YAML文件不存在: {yaml_file}'}), 404
        
        # 验证YAML文件
        parser = YamlConfigParser(str(yaml_file))
        is_valid, message = parser.validate_yaml()
        
        return jsonify({
            'valid': is_valid,
            'message': message
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500 