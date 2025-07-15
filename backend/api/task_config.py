#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify
from pathlib import Path
import json
from datetime import datetime
import sys
import os

# 添加后端路径到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config_validator import ConfigValidator

# 创建任务配置API蓝图
task_config_bp = Blueprint('task_config', __name__, url_prefix='/api/task_config')

# 稍后在main.py中初始化依赖项
yaml_parser = None
gitlab_client = None
db_manager = None
WORKSPACE_PATH = None

def init_dependencies(yaml_parser_instance, gitlab_cli, db_mgr, workspace_path):
    """初始化依赖项"""
    global yaml_parser, gitlab_client, db_manager, WORKSPACE_PATH
    yaml_parser = yaml_parser_instance
    gitlab_client = gitlab_cli
    db_manager = db_mgr
    WORKSPACE_PATH = workspace_path

@task_config_bp.route('/stage_toggle', methods=['POST'])
def stage_toggle():
    """
    阶段开关控制API
    
    功能描述：控制compile、build、deploy三个阶段的启用/禁用状态
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - stage_name: 阶段名称（compile/build/deploy）
    - enabled: 是否启用（true/false）
    - sync_to_gitlab: 是否同步到GitLab（默认true）
    
    返回参数：
    - message: 操作结果消息
    - success: 操作是否成功
    - stage_status: 更新后的阶段状态
    """
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        stage_name = data.get('stage_name')
        enabled = data.get('enabled', False)
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        # 参数验证
        if not all([project_id, task_name, stage_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name, stage_name'
            }), 400
        
        # 验证阶段名称有效性
        valid_stages = ['compile', 'build', 'deploy']
        if stage_name not in valid_stages:
            return jsonify({
                'success': False,
                'error': f'无效的阶段名称。支持的阶段: {", ".join(valid_stages)}'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 更新阶段开关
        stage_value = "on" if enabled else "off"
        
        # 使用现有的update_stage_toggle方法
        success = yaml_parser.update_stage_toggle(str(yaml_file), stage_name, enabled)
        
        if not success:
            return jsonify({
                'success': False,
                'error': '更新YAML文件失败'
            }), 500
        
        # 获取更新后的所有阶段状态
        variables = yaml_parser.get_variables(str(yaml_file))
        stage_status = {
            'compile': variables.get('compile', 'off'),
            'build': variables.get('build', 'off'),
            'deploy': variables.get('deploy', 'off')
        }
        
        # 更新数据库中的阶段配置
        try:
            # 查找对应的pipeline和task
            pipeline = db_manager.execute_query(
                "SELECT id FROM pipelines WHERE project_id = %s AND branch = %s",
                params=(project_id, branch),
                fetch_one=True
            )
            
            if pipeline:
                task = db_manager.execute_query(
                    "SELECT id FROM pipeline_tasks WHERE pipeline_id = %s AND name = %s",
                    params=(pipeline['id'], task_name),
                    fetch_one=True
                )
                
                if task:
                    # 更新或插入阶段配置
                    existing_stage = db_manager.execute_query(
                        "SELECT id, config FROM pipeline_task_stages WHERE task_id = %s AND type = %s",
                        params=(task['id'], stage_name),
                        fetch_one=True
                    )
                    
                    if existing_stage:
                        # 更新现有阶段配置
                        try:
                            # 安全地解析现有配置
                            if existing_stage['config']:
                                if isinstance(existing_stage['config'], str):
                                    current_config = json.loads(existing_stage['config'])
                                else:
                                    current_config = existing_stage['config']
                            else:
                                current_config = {}
                        except (json.JSONDecodeError, TypeError):
                            print(f"解析现有配置失败，使用空配置: {existing_stage['config']}")
                            current_config = {}
                        
                        current_config['enabled'] = enabled
                        current_config['status'] = stage_value
                        
                        db_manager.execute_update(
                            "UPDATE pipeline_task_stages SET config = %s WHERE id = %s",
                            params=(json.dumps(current_config), existing_stage['id'])
                        )
                    else:
                        # 创建新的阶段配置
                        stage_config = {
                            'enabled': enabled,
                            'status': stage_value,
                            'type': stage_name
                        }
                        
                        db_manager.execute_insert(
                            """INSERT INTO pipeline_task_stages (task_id, type, name, order_index, config)
                               VALUES (%s, %s, %s, %s, %s)""",
                            params=(task['id'], stage_name, stage_name, 
                                   0 if stage_name == 'compile' else 1 if stage_name == 'build' else 2,
                                   json.dumps(stage_config))
                        )
        except Exception as db_error:
            print(f"数据库更新失败: {db_error}")
            # 数据库更新失败不影响主要功能
        
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
                    commit_message=f"更新{task_name}的{stage_name}阶段开关状态为{stage_value}"
                )
            except Exception as e:
                return jsonify({
                    'success': True,
                    'message': f'{stage_name}阶段开关更新成功，但GitLab同步失败',
                    'stage_status': stage_status,
                    'warning': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': f'{stage_name}阶段开关更新成功',
            'stage_status': stage_status,
            'updated_stage': {
                'name': stage_name,
                'enabled': enabled,
                'value': stage_value
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/stage_status', methods=['GET'])
def get_stage_status():
    """
    获取阶段状态API
    
    功能描述：获取指定任务的所有阶段开关状态
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    
    返回参数：
    - stage_status: 各阶段状态
    - success: 操作是否成功
    """
    try:
        project_id = request.args.get('project_id')
        branch = request.args.get('branch', 'develop')
        task_name = request.args.get('task_name')
        
        # 参数验证
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 读取阶段状态
        variables = yaml_parser.get_variables(str(yaml_file))
        
        stage_status = {
            'compile': {
                'enabled': variables.get('compile', 'off') == 'on',
                'value': variables.get('compile', 'off')
            },
            'build': {
                'enabled': variables.get('build', 'off') == 'on',
                'value': variables.get('build', 'off')
            },
            'deploy': {
                'enabled': variables.get('deploy', 'off') == 'on',
                'value': variables.get('deploy', 'off')
            }
        }
        
        return jsonify({
            'success': True,
            'stage_status': stage_status,
            'project_id': project_id,
            'branch': branch,
            'task_name': task_name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/batch_stage_toggle', methods=['POST'])
def batch_stage_toggle():
    """
    批量阶段开关控制API
    
    功能描述：一次性设置多个阶段的开关状态
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - stages: 阶段配置对象 {compile: true/false, build: true/false, deploy: true/false}
    - sync_to_gitlab: 是否同步到GitLab（默认true）
    
    返回参数：
    - message: 操作结果消息
    - success: 操作是否成功
    - stage_status: 更新后的阶段状态
    """
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        stages = data.get('stages', {})
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        # 参数验证
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        if not stages:
            return jsonify({
                'success': False,
                'error': '缺少阶段配置参数'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 批量更新阶段开关
        updated_stages = []
        
        valid_stages = ['compile', 'build', 'deploy']
        for stage_name, enabled in stages.items():
            if stage_name in valid_stages:
                success = yaml_parser.update_stage_toggle(str(yaml_file), stage_name, enabled)
                if success:
                    updated_stages.append({
                        'name': stage_name,
                        'enabled': enabled,
                        'value': 'on' if enabled else 'off'
                    })
        
        # 获取更新后的所有阶段状态
        variables = yaml_parser.get_variables(str(yaml_file))
        stage_status = {
            'compile': variables.get('compile', 'off'),
            'build': variables.get('build', 'off'),
            'deploy': variables.get('deploy', 'off')
        }
        
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
                    commit_message=f"批量更新{task_name}的阶段开关状态"
                )
            except Exception as e:
                return jsonify({
                    'success': True,
                    'message': '批量阶段开关更新成功，但GitLab同步失败',
                    'stage_status': stage_status,
                    'updated_stages': updated_stages,
                    'warning': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': '批量阶段开关更新成功',
            'stage_status': stage_status,
            'updated_stages': updated_stages
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/maven_config', methods=['POST'])
def maven_config():
    """
    Maven模板配置参数API
    
    功能描述：更新Maven项目的阶段配置参数，支持编译、构建、部署三个阶段的参数配置
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - stage_configs: 阶段配置对象，包含以下可选阶段：
      * compile: 编译阶段配置
        - JDKVERSION: JDK版本（默认8）
        - CODEPATH: 代码路径（默认空）
        - TARGETDIR: 制品路径（默认target）
        - BUILDFORMAT: 制品格式（默认jar）
        - BUILDCMD: 编译命令（默认mvn clean package -Dmaven.test.skip=true -U）
      * build: 构建阶段配置
        - HARBORNAME: Harbor项目名称（默认devops）
        - BUILDDIR: Dockerfile路径（默认.）
        - PLATFORM: 镜像架构（默认linux/amd64）
        - SERVICENAME: 服务名（默认app）
      * deploy: 部署阶段配置
        - NAMESPACE: 命名空间（默认app-dev）
        - SERVICENAME: 服务名（默认app）
        - CTPORT: 应用端口（默认80）
        - K8S: 发布集群（默认K8S_cmdicncf_jkyw）
        - INGRESS: 是否启用Ingress（默认yes）
        - LIMITSCPU: CPU资源限制（默认1000m）
        - LIMITSMEM: 内存资源限制（默认1024Mi）
    - sync_to_gitlab: 是否同步到GitLab（默认true）
    
    返回参数：
    - message: 操作结果消息
    - success: 操作是否成功
    - updated_configs: 更新的配置信息
    """
    try:
        print("=== Maven配置API收到请求 ===")
        print(f"原始请求数据: {request.data}")
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        
        data = request.json
        print(f"解析后的JSON数据: {data}")
        print(f"数据类型: {type(data)}")
        
        if data is None:
            print("ERROR: 无法解析JSON数据")
            return jsonify({
                'success': False,
                'error': '无法解析JSON数据，请检查Content-Type和数据格式'
            }), 400
        
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        stage_configs = data.get('stage_configs', {})
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        print(f"提取的参数:")
        print(f"  project_id: {project_id} (类型: {type(project_id)})")
        print(f"  branch: {branch} (类型: {type(branch)})")
        print(f"  task_name: {task_name} (类型: {type(task_name)})")
        print(f"  stage_configs: {stage_configs} (类型: {type(stage_configs)})")
        print(f"  sync_to_gitlab: {sync_to_gitlab} (类型: {type(sync_to_gitlab)})")
        
        # 参数验证
        if not all([project_id, task_name]):
            error_msg = '缺少必要参数: project_id, task_name'
            print(f"ERROR: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        if not stage_configs:
            error_msg = '缺少配置参数: stage_configs'
            print(f"ERROR: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 获取验证级别
        validation_level = data.get('validation_level', 'normal')
        
        # 创建配置验证器
        validator = ConfigValidator()
        
        # 预处理所有配置以进行验证
        all_config_for_validation = {}
        for stage_name, config in stage_configs.items():
            all_config_for_validation.update(config)
        
        # 执行配置验证
        validation_result = validator.validate_complete_config(all_config_for_validation, 'maven')
        
        # 根据验证级别决定是否继续
        if validation_level == 'strict' and (validation_result['errors'] or validation_result['warnings']):
            return jsonify({
                'success': False,
                'error': '配置验证失败（严格模式）',
                'validation_result': validation_result
            }), 400
        elif validation_level in ['normal', 'lenient'] and validation_result['errors']:
            return jsonify({
                'success': False,
                'error': '配置验证失败',
                'validation_result': validation_result
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 定义Maven配置参数映射
        maven_config_mapping = {
            'compile': {
                'JDKVERSION': {'required': False, 'default': '8', 'description': 'JDK版本'},
                'CODEPATH': {'required': False, 'default': '', 'description': '代码路径'},
                'TARGETDIR': {'required': False, 'default': 'target', 'description': '制品路径'},
                'BUILDFORMAT': {'required': False, 'default': 'jar', 'description': '制品格式'},
                'BUILDCMD': {'required': False, 'default': 'mvn clean package -Dmaven.test.skip=true -U', 'description': '编译命令'}
            },
            'build': {
                'HARBORNAME': {'required': False, 'default': 'devops', 'description': 'Harbor项目名称'},
                'BUILDDIR': {'required': False, 'default': '.', 'description': 'Dockerfile路径'},
                'PLATFORM': {'required': False, 'default': 'linux/amd64', 'description': '镜像架构'},
                'SERVICENAME': {'required': False, 'default': 'app', 'description': '服务名'}
            },
            'deploy': {
                'NAMESPACE': {'required': False, 'default': 'app-dev', 'description': '命名空间'},
                'SERVICENAME': {'required': False, 'default': 'app', 'description': '服务名'},
                'CTPORT': {'required': False, 'default': 80, 'description': '应用端口'},
                'K8S': {'required': False, 'default': 'K8S_cmdicncf_jkyw', 'description': '发布集群'},
                'INGRESS': {'required': False, 'default': 'yes', 'description': '是否启用Ingress'},
                'LIMITSCPU': {'required': False, 'default': '1000m', 'description': 'CPU资源限制'},
                'LIMITSMEM': {'required': False, 'default': '1024Mi', 'description': '内存资源限制'}
            }
        }
        
        # 验证阶段配置有效性
        valid_stages = ['compile', 'build', 'deploy']
        updated_configs = {}
        
        for stage_name, config in stage_configs.items():
            if stage_name not in valid_stages:
                return jsonify({
                    'success': False,
                    'error': f'无效的阶段名称: {stage_name}。支持的阶段: {", ".join(valid_stages)}'
                }), 400
            
            if not isinstance(config, dict):
                return jsonify({
                    'success': False,
                    'error': f'{stage_name}阶段配置必须是对象类型'
                }), 400
            
            # 验证和处理配置参数
            stage_mapping = maven_config_mapping[stage_name]
            processed_config = {}
            
            for param_name, param_value in config.items():
                if param_name not in stage_mapping:
                    return jsonify({
                        'success': False,
                        'error': f'{stage_name}阶段不支持参数: {param_name}'
                    }), 400
                
                # 参数类型转换和验证
                param_info = stage_mapping[param_name]
                if param_name == 'CTPORT' and param_value is not None:
                    try:
                        param_value = int(param_value)
                        if param_value <= 0 or param_value > 65535:
                            raise ValueError('端口号必须在1-65535之间')
                    except (ValueError, TypeError):
                        return jsonify({
                            'success': False,
                            'error': f'无效的端口号: {param_value}'
                        }), 400
                
                processed_config[param_name] = param_value
            
            updated_configs[stage_name] = processed_config
        
        # 更新YAML文件中的配置
        update_results = []
        all_updates = {}
        
        # 收集所有需要更新的变量
        for stage_name, config in updated_configs.items():
            for param_name, param_value in config.items():
                all_updates[param_name] = param_value
                update_results.append({
                    'stage': stage_name,
                    'parameter': param_name,
                    'value': param_value,
                    'description': maven_config_mapping[stage_name][param_name]['description']
                })
        
        # 一次性更新所有变量
        print(f"准备更新YAML文件: {yaml_file}")
        print(f"更新的变量: {all_updates}")
        success = yaml_parser.update_variables(str(yaml_file), all_updates)
        print(f"YAML文件更新结果: {success}")
        
        if not success:
            return jsonify({
                'success': False,
                'error': '更新YAML文件失败'
            }), 500
        
        # 验证更新后的内容
        try:
            updated_variables = yaml_parser.get_variables(str(yaml_file))
            print(f"更新后的YAML变量: {updated_variables}")
        except Exception as e:
            print(f"读取更新后的YAML变量失败: {e}")
        
        # 更新数据库中的阶段配置
        try:
            # 查找对应的pipeline和task
            pipeline = db_manager.execute_query(
                "SELECT id FROM pipelines WHERE project_id = %s AND branch = %s",
                params=(project_id, branch),
                fetch_one=True
            )
            
            if pipeline:
                task = db_manager.execute_query(
                    "SELECT id FROM pipeline_tasks WHERE pipeline_id = %s AND name = %s",
                    params=(pipeline['id'], task_name),
                    fetch_one=True
                )
                
                if task:
                    for stage_name, config in updated_configs.items():
                        # 更新或插入阶段配置
                        existing_stage = db_manager.execute_query(
                            "SELECT id, config FROM pipeline_task_stages WHERE task_id = %s AND type = %s",
                            params=(task['id'], stage_name),
                            fetch_one=True
                        )
                        
                        if existing_stage:
                            # 更新现有阶段配置
                            current_config = existing_stage['config'] if existing_stage['config'] else {}
                            if isinstance(current_config, str):
                                current_config = json.loads(current_config)
                            
                            current_config.update(config)
                            current_config['template_type'] = 'maven'
                            current_config['last_updated'] = datetime.now().isoformat()
                            
                            db_manager.execute_update(
                                "UPDATE pipeline_task_stages SET config = %s, template_type = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                                params=(json.dumps(current_config), 'maven', existing_stage['id'])
                            )
                        else:
                            # 创建新的阶段配置
                            stage_config = config.copy()
                            stage_config['template_type'] = 'maven'
                            stage_config['created'] = datetime.now().isoformat()
                            
                            db_manager.execute_insert(
                                """INSERT INTO pipeline_task_stages (task_id, type, name, order_index, config, template_type)
                                   VALUES (%s, %s, %s, %s, %s, %s)""",
                                params=(
                                    task['id'], 
                                    stage_name, 
                                    stage_name, 
                                    0 if stage_name == 'compile' else 1 if stage_name == 'build' else 2,
                                    json.dumps(stage_config),
                                    'maven'
                                )
                            )
        except Exception as db_error:
            print(f"数据库更新失败: {db_error}")
            # 数据库更新失败不影响主要功能
        
        # 同步到GitLab
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                updated_params = [f"{r['parameter']}={r['value']}" for r in update_results]
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=f"更新{task_name}的Maven配置参数: {', '.join(updated_params)}"
                )
            except Exception as e:
                return jsonify({
                    'success': True,
                    'message': 'Maven配置更新成功，但GitLab同步失败',
                    'updated_configs': update_results,
                    'warning': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': 'Maven配置更新成功',
            'updated_configs': update_results,
            'validation_result': validation_result,
            'project_id': project_id,
            'branch': branch,
            'task_name': task_name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/maven_config', methods=['GET'])
def get_maven_config():
    """
    获取Maven配置参数API
    
    功能描述：获取指定任务的Maven配置参数
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - stage_type: 阶段类型（可选，不指定则返回所有阶段）
    
    返回参数：
    - maven_configs: Maven配置参数
    - success: 操作是否成功
    """
    try:
        project_id = request.args.get('project_id')
        branch = request.args.get('branch', 'develop')
        task_name = request.args.get('task_name')
        stage_type = request.args.get('stage_type')
        
        # 参数验证
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 读取当前配置
        variables = yaml_parser.get_variables(str(yaml_file))
        
        # Maven配置参数列表
        maven_parameters = {
            'compile': ['JDKVERSION', 'CODEPATH', 'TARGETDIR', 'BUILDFORMAT', 'BUILDCMD'],
            'build': ['HARBORNAME', 'BUILDDIR', 'PLATFORM', 'SERVICENAME'],
            'deploy': ['NAMESPACE', 'SERVICENAME', 'CTPORT', 'K8S', 'INGRESS', 'LIMITSCPU', 'LIMITSMEM']
        }
        
        maven_configs = {}
        
        # 如果指定了阶段类型，只返回该阶段的配置
        if stage_type:
            if stage_type not in maven_parameters:
                return jsonify({
                    'success': False,
                    'error': f'无效的阶段类型: {stage_type}'
                }), 400
            
            config = {}
            for param in maven_parameters[stage_type]:
                config[param] = variables.get(param, '')
            maven_configs[stage_type] = config
        else:
            # 返回所有阶段的配置
            for stage, params in maven_parameters.items():
                config = {}
                for param in params:
                    config[param] = variables.get(param, '')
                maven_configs[stage] = config
        
        return jsonify({
            'success': True,
            'maven_configs': maven_configs,
            'project_id': project_id,
            'branch': branch,
            'task_name': task_name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/npm_config', methods=['POST'])
def npm_config():
    """
    NPM模板配置参数API
    
    功能描述：更新NPM项目的阶段配置参数，支持编译、构建、部署三个阶段的参数配置
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - stage_configs: 阶段配置对象，包含以下可选阶段：
      * compile: 编译阶段配置
        - NODEVERSION: Node.js版本（默认14.18）
        - PNPMVERSION: PNPM版本（默认7.33.7）
        - CODEPATH: 代码路径（默认空）
        - BUILDCMD: 编译命令（默认pnpm run build）
        - NPMDIR: 制品发布目录（默认dist）
      * build: 构建阶段配置
        - HARBORNAME: Harbor项目名称（默认devops）
        - BUILDDIR: Dockerfile路径（默认.）
        - PLATFORM: 镜像架构（默认linux/amd64）
        - INGRESS: 是否启用Ingress（默认yes）
      * deploy: 部署阶段配置
        - NAMESPACE: 命名空间（默认app-dev）
        - SERVICENAME: 服务名（默认$CI_PROJECT_NAME）
        - CTPORT: 应用端口（默认80）
        - K8S: 发布集群（默认K8S_cmdicncf_jkyw）
        - REQUESTSCPU: CPU请求资源（默认100m）
        - REQUESTSMEM: 内存请求资源（默认128Mi）
        - LIMITSCPU: CPU资源限制（默认500m）
        - LIMITSMEM: 内存资源限制（默认256Mi）
    - sync_to_gitlab: 是否同步到GitLab（默认true）
    
    返回参数：
    - message: 操作结果消息
    - success: 操作是否成功
    - updated_configs: 更新的配置信息
    """
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        stage_configs = data.get('stage_configs', {})
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        # 参数验证
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        if not stage_configs:
            return jsonify({
                'success': False,
                'error': '缺少配置参数: stage_configs'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 定义NPM配置参数映射
        npm_config_mapping = {
            'compile': {
                'NODEVERSION': {'required': False, 'default': '14.18', 'description': 'Node.js版本'},
                'PNPMVERSION': {'required': False, 'default': '7.33.7', 'description': 'PNPM版本'},
                'CODEPATH': {'required': False, 'default': '', 'description': '代码路径'},
                'BUILDCMD': {'required': False, 'default': 'pnpm run build', 'description': '编译命令'},
                'NPMDIR': {'required': False, 'default': 'dist', 'description': '制品发布目录'}
            },
            'build': {
                'HARBORNAME': {'required': False, 'default': 'devops', 'description': 'Harbor项目名称'},
                'BUILDDIR': {'required': False, 'default': '.', 'description': 'Dockerfile路径'},
                'PLATFORM': {'required': False, 'default': 'linux/amd64', 'description': '镜像架构'},
                'INGRESS': {'required': False, 'default': 'yes', 'description': '是否启用Ingress'}
            },
            'deploy': {
                'NAMESPACE': {'required': False, 'default': 'app-dev', 'description': '命名空间'},
                'SERVICENAME': {'required': False, 'default': '$CI_PROJECT_NAME', 'description': '服务名'},
                'CTPORT': {'required': False, 'default': 80, 'description': '应用端口'},
                'K8S': {'required': False, 'default': 'K8S_cmdicncf_jkyw', 'description': '发布集群'},
                'REQUESTSCPU': {'required': False, 'default': '100m', 'description': 'CPU请求资源'},
                'REQUESTSMEM': {'required': False, 'default': '128Mi', 'description': '内存请求资源'},
                'LIMITSCPU': {'required': False, 'default': '500m', 'description': 'CPU资源限制'},
                'LIMITSMEM': {'required': False, 'default': '256Mi', 'description': '内存资源限制'}
            }
        }
        
        # 验证阶段配置有效性
        valid_stages = ['compile', 'build', 'deploy']
        updated_configs = {}
        
        for stage_name, config in stage_configs.items():
            if stage_name not in valid_stages:
                return jsonify({
                    'success': False,
                    'error': f'无效的阶段名称: {stage_name}。支持的阶段: {", ".join(valid_stages)}'
                }), 400
            
            if not isinstance(config, dict):
                return jsonify({
                    'success': False,
                    'error': f'{stage_name}阶段配置必须是对象类型'
                }), 400
            
            # 验证和处理配置参数
            stage_mapping = npm_config_mapping[stage_name]
            processed_config = {}
            
            for param_name, param_value in config.items():
                if param_name not in stage_mapping:
                    return jsonify({
                        'success': False,
                        'error': f'{stage_name}阶段不支持参数: {param_name}'
                    }), 400
                
                # 参数类型转换和验证
                param_info = stage_mapping[param_name]
                
                # 端口号验证
                if param_name == 'CTPORT' and param_value is not None:
                    try:
                        param_value = int(param_value)
                        if param_value <= 0 or param_value > 65535:
                            raise ValueError('端口号必须在1-65535之间')
                    except (ValueError, TypeError):
                        return jsonify({
                            'success': False,
                            'error': f'无效的端口号: {param_value}'
                        }), 400
                
                # Node.js版本验证
                if param_name == 'NODEVERSION' and param_value:
                    # 基本的版本格式验证
                    if not str(param_value).replace('.', '').replace('-', '').replace('v', '').replace('lts', '').isalnum():
                        return jsonify({
                            'success': False,
                            'error': f'无效的Node.js版本格式: {param_value}'
                        }), 400
                
                # PNPM版本验证
                if param_name == 'PNPMVERSION' and param_value:
                    # 基本的版本格式验证
                    if not str(param_value).replace('.', '').isdigit():
                        return jsonify({
                            'success': False,
                            'error': f'无效的PNPM版本格式: {param_value}'
                        }), 400
                
                processed_config[param_name] = param_value
            
            updated_configs[stage_name] = processed_config
        
        # 更新YAML文件中的配置
        update_results = []
        all_updates = {}
        
        # 收集所有需要更新的变量
        for stage_name, config in updated_configs.items():
            for param_name, param_value in config.items():
                all_updates[param_name] = param_value
                update_results.append({
                    'stage': stage_name,
                    'parameter': param_name,
                    'value': param_value,
                    'description': npm_config_mapping[stage_name][param_name]['description']
                })
        
        # 一次性更新所有变量
        success = yaml_parser.update_variables(str(yaml_file), all_updates)
        if not success:
            return jsonify({
                'success': False,
                'error': '更新YAML文件失败'
            }), 500
        
        # 更新数据库中的阶段配置
        try:
            # 查找对应的pipeline和task
            pipeline = db_manager.execute_query(
                "SELECT id FROM pipelines WHERE project_id = %s AND branch = %s",
                params=(project_id, branch),
                fetch_one=True
            )
            
            if pipeline:
                task = db_manager.execute_query(
                    "SELECT id FROM pipeline_tasks WHERE pipeline_id = %s AND name = %s",
                    params=(pipeline['id'], task_name),
                    fetch_one=True
                )
                
                if task:
                    for stage_name, config in updated_configs.items():
                        # 更新或插入阶段配置
                        existing_stage = db_manager.execute_query(
                            "SELECT id, config FROM pipeline_task_stages WHERE task_id = %s AND type = %s",
                            params=(task['id'], stage_name),
                            fetch_one=True
                        )
                        
                        if existing_stage:
                            # 更新现有阶段配置
                            current_config = existing_stage['config'] if existing_stage['config'] else {}
                            if isinstance(current_config, str):
                                current_config = json.loads(current_config)
                            
                            current_config.update(config)
                            current_config['template_type'] = 'npm'
                            current_config['last_updated'] = datetime.now().isoformat()
                            
                            db_manager.execute_update(
                                "UPDATE pipeline_task_stages SET config = %s, template_type = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                                params=(json.dumps(current_config), 'npm', existing_stage['id'])
                            )
                        else:
                            # 创建新的阶段配置
                            stage_config = config.copy()
                            stage_config['template_type'] = 'npm'
                            stage_config['created'] = datetime.now().isoformat()
                            
                            db_manager.execute_insert(
                                """INSERT INTO pipeline_task_stages (task_id, type, name, order_index, config, template_type)
                                   VALUES (%s, %s, %s, %s, %s, %s)""",
                                params=(
                                    task['id'], 
                                    stage_name, 
                                    stage_name, 
                                    0 if stage_name == 'compile' else 1 if stage_name == 'build' else 2,
                                    json.dumps(stage_config),
                                    'npm'
                                )
                            )
        except Exception as db_error:
            print(f"数据库更新失败: {db_error}")
            # 数据库更新失败不影响主要功能
        
        # 同步到GitLab
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                updated_params = [f"{r['parameter']}={r['value']}" for r in update_results]
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=f"更新{task_name}的NPM配置参数: {', '.join(updated_params)}"
                )
            except Exception as e:
                return jsonify({
                    'success': True,
                    'message': 'NPM配置更新成功，但GitLab同步失败',
                    'updated_configs': update_results,
                    'warning': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': 'NPM配置更新成功',
            'updated_configs': update_results,
            'project_id': project_id,
            'branch': branch,
            'task_name': task_name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/npm_config', methods=['GET'])
def get_npm_config():
    """
    获取NPM配置参数API
    
    功能描述：获取指定任务的NPM配置参数
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - stage_type: 阶段类型（可选，不指定则返回所有阶段）
    
    返回参数：
    - npm_configs: NPM配置参数
    - success: 操作是否成功
    """
    try:
        project_id = request.args.get('project_id')
        branch = request.args.get('branch', 'develop')
        task_name = request.args.get('task_name')
        stage_type = request.args.get('stage_type')
        
        # 参数验证
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 读取当前配置
        variables = yaml_parser.get_variables(str(yaml_file))
        
        # NPM配置参数列表
        npm_parameters = {
            'compile': ['NODEVERSION', 'PNPMVERSION', 'CODEPATH', 'BUILDCMD', 'NPMDIR'],
            'build': ['HARBORNAME', 'BUILDDIR', 'PLATFORM', 'INGRESS'],
            'deploy': ['NAMESPACE', 'SERVICENAME', 'CTPORT', 'K8S', 'REQUESTSCPU', 'REQUESTSMEM', 'LIMITSCPU', 'LIMITSMEM']
        }
        
        npm_configs = {}
        
        # 如果指定了阶段类型，只返回该阶段的配置
        if stage_type:
            if stage_type not in npm_parameters:
                return jsonify({
                    'success': False,
                    'error': f'无效的阶段类型: {stage_type}'
                }), 400
            
            config = {}
            for param in npm_parameters[stage_type]:
                config[param] = variables.get(param, '')
            npm_configs[stage_type] = config
        else:
            # 返回所有阶段的配置
            for stage, params in npm_parameters.items():
                config = {}
                for param in params:
                    config[param] = variables.get(param, '')
                npm_configs[stage] = config
        
        return jsonify({
            'success': True,
            'npm_configs': npm_configs,
            'project_id': project_id,
            'branch': branch,
            'task_name': task_name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/deploy_config', methods=['POST'])
def deploy_config():
    """
    通用部署阶段配置参数API
    
    功能描述：更新任何项目类型的部署阶段配置参数，支持Maven、NPM等多种项目类型的统一部署配置管理
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - template_type: 模板类型（maven/npm，可选，用于获取默认值）
    - deploy_config: 部署配置对象，包含以下可选参数：
      * NAMESPACE: 命名空间（必填）
      * SERVICENAME: 服务名（必填）
      * CTPORT: 应用端口（默认80，范围1-65535）
      * K8S: 发布集群（默认K8S_cmdicncf_jkyw）
      * INGRESS: 是否启用Ingress（默认yes，可选值：yes/no）
      * LIMITSCPU: CPU资源限制（默认1000m）
      * LIMITSMEM: 内存资源限制（默认1024Mi）
      * REQUESTSCPU: CPU请求资源（默认100m，仅NPM项目）
      * REQUESTSMEM: 内存请求资源（默认128Mi，仅NPM项目）
    - resource_conversion: 是否启用资源单位自动转换（默认true）
    - sync_to_gitlab: 是否同步到GitLab（默认true）
    
    返回参数：
    - message: 操作结果消息
    - success: 操作是否成功
    - updated_configs: 更新的配置信息
    - converted_resources: 资源单位转换信息（如果启用转换）
    """
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        template_type = data.get('template_type', 'maven')  # 默认maven类型
        deploy_config = data.get('deploy_config', {})
        resource_conversion = data.get('resource_conversion', True)
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        # 参数验证
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        if not deploy_config:
            return jsonify({
                'success': False,
                'error': '缺少配置参数: deploy_config'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 定义部署配置参数映射（根据模板类型）
        deploy_config_mapping = {
            'maven': {
                'NAMESPACE': {'required': True, 'default': 'app-dev', 'description': '命名空间'},
                'SERVICENAME': {'required': True, 'default': 'app', 'description': '服务名'},
                'CTPORT': {'required': False, 'default': 80, 'description': '应用端口'},
                'K8S': {'required': False, 'default': 'K8S_cmdicncf_jkyw', 'description': '发布集群'},
                'INGRESS': {'required': False, 'default': 'yes', 'description': '是否启用Ingress'},
                'LIMITSCPU': {'required': False, 'default': '1000m', 'description': 'CPU资源限制'},
                'LIMITSMEM': {'required': False, 'default': '1024Mi', 'description': '内存资源限制'}
            },
            'npm': {
                'NAMESPACE': {'required': True, 'default': 'app-dev', 'description': '命名空间'},
                'SERVICENAME': {'required': True, 'default': '$CI_PROJECT_NAME', 'description': '服务名'},
                'CTPORT': {'required': False, 'default': 80, 'description': '应用端口'},
                'K8S': {'required': False, 'default': 'K8S_cmdicncf_jkyw', 'description': '发布集群'},
                'REQUESTSCPU': {'required': False, 'default': '100m', 'description': 'CPU请求资源'},
                'REQUESTSMEM': {'required': False, 'default': '128Mi', 'description': '内存请求资源'},
                'LIMITSCPU': {'required': False, 'default': '500m', 'description': 'CPU资源限制'},
                'LIMITSMEM': {'required': False, 'default': '256Mi', 'description': '内存资源限制'}
            }
        }
        
        # 获取对应模板类型的配置映射
        config_mapping = deploy_config_mapping.get(template_type, deploy_config_mapping['maven'])
        
        # 验证和处理配置参数
        processed_config = {}
        converted_resources = []
        
        for param_name, param_value in deploy_config.items():
            if param_name not in config_mapping:
                return jsonify({
                    'success': False,
                    'error': f'不支持的部署参数: {param_name}。模板类型 {template_type} 支持的参数: {", ".join(config_mapping.keys())}'
                }), 400
            
            param_info = config_mapping[param_name]
            
            # 必填参数验证
            if param_info['required'] and (param_value is None or str(param_value).strip() == ''):
                return jsonify({
                    'success': False,
                    'error': f'必填参数不能为空: {param_name}'
                }), 400
            
            # 端口号验证
            if param_name == 'CTPORT' and param_value is not None:
                try:
                    param_value = int(param_value)
                    if param_value <= 0 or param_value > 65535:
                        raise ValueError('端口号必须在1-65535之间')
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': f'无效的端口号: {param_value}'
                    }), 400
            
            # Ingress验证
            if param_name == 'INGRESS' and param_value is not None:
                if str(param_value).lower() not in ['yes', 'no', 'true', 'false']:
                    return jsonify({
                        'success': False,
                        'error': f'INGRESS参数值无效: {param_value}，仅支持: yes, no, true, false'
                    }), 400
                # 标准化为yes/no
                param_value = 'yes' if str(param_value).lower() in ['yes', 'true'] else 'no'
            
            # 资源单位转换
            if resource_conversion and param_name in ['LIMITSCPU', 'REQUESTSCPU', 'LIMITSMEM', 'REQUESTSMEM']:
                original_value = param_value
                
                if 'CPU' in param_name:
                    # CPU资源转换：支持数字转毫核、保持现有格式
                    try:
                        if isinstance(param_value, (int, float)):
                            converted_value = f"{int(param_value * 1000)}m"
                            converted_resources.append({
                                'parameter': param_name,
                                'original': original_value,
                                'converted': converted_value,
                                'unit': 'CPU cores to millicores'
                            })
                            param_value = converted_value
                        elif str(param_value).replace('.', '').isdigit():
                            # 纯数字字符串
                            converted_value = f"{int(float(param_value) * 1000)}m"
                            converted_resources.append({
                                'parameter': param_name,
                                'original': original_value,
                                'converted': converted_value,
                                'unit': 'CPU cores to millicores'
                            })
                            param_value = converted_value
                    except (ValueError, TypeError):
                        pass  # 保持原值，可能已经是正确格式
                        
                elif 'MEM' in param_name:
                    # 内存资源转换：支持数字转Mi、保持现有格式
                    try:
                        if isinstance(param_value, (int, float)):
                            converted_value = f"{int(param_value * 1024)}Mi"
                            converted_resources.append({
                                'parameter': param_name,
                                'original': original_value,
                                'converted': converted_value,
                                'unit': 'GB to MiB'
                            })
                            param_value = converted_value
                        elif str(param_value).replace('.', '').isdigit():
                            # 纯数字字符串
                            converted_value = f"{int(float(param_value) * 1024)}Mi"
                            converted_resources.append({
                                'parameter': param_name,
                                'original': original_value,
                                'converted': converted_value,
                                'unit': 'GB to MiB'
                            })
                            param_value = converted_value
                    except (ValueError, TypeError):
                        pass  # 保持原值，可能已经是正确格式
            
            processed_config[param_name] = param_value
        
        # 更新YAML文件中的配置
        update_results = []
        
        # 收集所有需要更新的变量
        for param_name, param_value in processed_config.items():
            update_results.append({
                'parameter': param_name,
                'value': param_value,
                'description': config_mapping[param_name]['description']
            })
        
        # 一次性更新所有变量
        success = yaml_parser.update_variables(str(yaml_file), processed_config)
        if not success:
            return jsonify({
                'success': False,
                'error': '更新YAML文件失败'
            }), 500
        
        # 更新数据库中的阶段配置
        try:
            # 查找对应的pipeline和task
            pipeline = db_manager.execute_query(
                "SELECT id FROM pipelines WHERE project_id = %s AND branch = %s",
                params=(project_id, branch),
                fetch_one=True
            )
            
            if pipeline:
                task = db_manager.execute_query(
                    "SELECT id FROM pipeline_tasks WHERE pipeline_id = %s AND name = %s",
                    params=(pipeline['id'], task_name),
                    fetch_one=True
                )
                
                if task:
                    # 更新或插入部署阶段配置
                    existing_stage = db_manager.execute_query(
                        "SELECT id, config FROM pipeline_task_stages WHERE task_id = %s AND type = %s",
                        params=(task['id'], 'deploy'),
                        fetch_one=True
                    )
                    
                    if existing_stage:
                        # 更新现有阶段配置
                        current_config = existing_stage['config'] if existing_stage['config'] else {}
                        if isinstance(current_config, str):
                            current_config = json.loads(current_config)
                        
                        current_config.update(processed_config)
                        current_config['template_type'] = template_type
                        current_config['last_updated'] = datetime.now().isoformat()
                        current_config['resource_conversions'] = converted_resources if converted_resources else []
                        
                        db_manager.execute_update(
                            "UPDATE pipeline_task_stages SET config = %s, template_type = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                            params=(json.dumps(current_config), template_type, existing_stage['id'])
                        )
                    else:
                        # 创建新的阶段配置
                        stage_config = processed_config.copy()
                        stage_config['template_type'] = template_type
                        stage_config['created'] = datetime.now().isoformat()
                        stage_config['resource_conversions'] = converted_resources if converted_resources else []
                        
                        db_manager.execute_insert(
                            """INSERT INTO pipeline_task_stages (task_id, type, name, order_index, config, template_type)
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            params=(
                                task['id'],
                                'deploy',
                                'deploy',
                                2,  # 部署阶段通常是第3个阶段
                                json.dumps(stage_config),
                                template_type
                            )
                        )
        except Exception as db_error:
            print(f"数据库更新失败: {db_error}")
            # 数据库更新失败不影响主要功能
        
        # 同步到GitLab
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                updated_params = [f"{r['parameter']}={r['value']}" for r in update_results]
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=f"更新{task_name}的部署配置参数({template_type}): {', '.join(updated_params)}"
                )
            except Exception as e:
                return jsonify({
                    'success': True,
                    'message': '部署配置更新成功，但GitLab同步失败',
                    'updated_configs': update_results,
                    'converted_resources': converted_resources,
                    'warning': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': f'部署配置更新成功 (模板类型: {template_type})',
            'updated_configs': update_results,
            'converted_resources': converted_resources,
            'template_type': template_type,
            'project_id': project_id,
            'branch': branch,
            'task_name': task_name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/deploy_config', methods=['GET'])
def get_deploy_config():
    """
    获取部署配置参数API
    
    功能描述：获取指定任务的部署配置参数，支持不同模板类型的配置获取
    
    入参：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - template_type: 模板类型（可选，用于确定返回哪些参数）
    
    返回参数：
    - deploy_config: 部署配置参数
    - template_type: 检测到的模板类型
    - success: 操作是否成功
    """
    try:
        project_id = request.args.get('project_id')
        branch = request.args.get('branch', 'develop')
        task_name = request.args.get('task_name')
        template_type = request.args.get('template_type')
        
        # 参数验证
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 读取当前配置
        variables = yaml_parser.get_variables(str(yaml_file))
        
        # 如果未指定模板类型，尝试自动检测
        if not template_type:
            # 检测模板类型的逻辑：根据特有参数判断
            if 'NODEVERSION' in variables or 'PNPMVERSION' in variables or 'NPMDIR' in variables:
                template_type = 'npm'
            elif 'JDKVERSION' in variables or 'BUILDFORMAT' in variables or 'TARGETDIR' in variables:
                template_type = 'maven'
            else:
                # 默认使用maven类型
                template_type = 'maven'
        
        # 部署配置参数列表（根据模板类型）
        deploy_parameters = {
            'maven': ['NAMESPACE', 'SERVICENAME', 'CTPORT', 'K8S', 'INGRESS', 'LIMITSCPU', 'LIMITSMEM'],
            'npm': ['NAMESPACE', 'SERVICENAME', 'CTPORT', 'K8S', 'REQUESTSCPU', 'REQUESTSMEM', 'LIMITSCPU', 'LIMITSMEM']
        }
        
        # 获取对应的参数列表
        params = deploy_parameters.get(template_type, deploy_parameters['maven'])
        
        # 提取部署配置
        deploy_config = {}
        for param in params:
            deploy_config[param] = variables.get(param, '')
        
        return jsonify({
            'success': True,
            'deploy_config': deploy_config,
            'template_type': template_type,
            'project_id': project_id,
            'branch': branch,
            'task_name': task_name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/deploy_config/batch', methods=['POST'])
def batch_deploy_config():
    """
    批量部署配置更新API
    
    功能描述：批量更新多个任务的部署配置，支持跨项目、跨分支的批量操作
    
    入参：
    - tasks: 任务列表，每个任务包含：
      * project_id: 项目ID
      * branch: 分支名（可选，默认develop）
      * task_name: 任务名称
      * template_type: 模板类型（可选，默认maven）
      * deploy_config: 部署配置对象
    - global_config: 全局配置（可选），会应用到所有任务
    - resource_conversion: 是否启用资源单位自动转换（默认true）
    - sync_to_gitlab: 是否同步到GitLab（默认true）
    
    返回参数：
    - success: 总体操作是否成功
    - results: 每个任务的处理结果
    - summary: 处理摘要统计
    """
    try:
        data = request.json
        tasks = data.get('tasks', [])
        global_config = data.get('global_config', {})
        resource_conversion = data.get('resource_conversion', True)
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        
        if not tasks:
            return jsonify({
                'success': False,
                'error': '缺少任务列表: tasks'
            }), 400
        
        results = []
        success_count = 0
        error_count = 0
        
        for task in tasks:
            try:
                # 准备单个任务的请求数据
                task_config = task.get('deploy_config', {})
                
                # 合并全局配置
                if global_config:
                    merged_config = global_config.copy()
                    merged_config.update(task_config)
                    task_config = merged_config
                
                request_data = {
                    'project_id': task.get('project_id'),
                    'branch': task.get('branch', 'develop'),
                    'task_name': task.get('task_name'),
                    'template_type': task.get('template_type', 'maven'),
                    'deploy_config': task_config,
                    'resource_conversion': resource_conversion,
                    'sync_to_gitlab': sync_to_gitlab
                }
                
                # 直接调用部署配置更新逻辑
                try:
                    # 模拟单个任务的配置更新
                    project_id = task.get('project_id')
                    branch = task.get('branch', 'develop')
                    task_name = task.get('task_name')
                    template_type = task.get('template_type', 'maven')
                    deploy_config_data = task_config
                    
                    # 参数验证
                    if not all([project_id, task_name]):
                        raise ValueError('缺少必要参数: project_id, task_name')
                    
                    if not deploy_config_data:
                        raise ValueError('缺少配置参数: deploy_config')
                    
                    # 构建文件路径
                    yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
                    
                    if not yaml_file.exists():
                        raise FileNotFoundError(f'YAML文件不存在: {yaml_file}')
                    
                    # 定义部署配置参数映射（根据模板类型）
                    deploy_config_mapping = {
                        'maven': {
                            'NAMESPACE': {'required': True, 'default': 'app-dev', 'description': '命名空间'},
                            'SERVICENAME': {'required': True, 'default': 'app', 'description': '服务名'},
                            'CTPORT': {'required': False, 'default': 80, 'description': '应用端口'},
                            'K8S': {'required': False, 'default': 'K8S_cmdicncf_jkyw', 'description': '发布集群'},
                            'INGRESS': {'required': False, 'default': 'yes', 'description': '是否启用Ingress'},
                            'LIMITSCPU': {'required': False, 'default': '1000m', 'description': 'CPU资源限制'},
                            'LIMITSMEM': {'required': False, 'default': '1024Mi', 'description': '内存资源限制'}
                        },
                        'npm': {
                            'NAMESPACE': {'required': True, 'default': 'app-dev', 'description': '命名空间'},
                            'SERVICENAME': {'required': True, 'default': '$CI_PROJECT_NAME', 'description': '服务名'},
                            'CTPORT': {'required': False, 'default': 80, 'description': '应用端口'},
                            'K8S': {'required': False, 'default': 'K8S_cmdicncf_jkyw', 'description': '发布集群'},
                            'REQUESTSCPU': {'required': False, 'default': '100m', 'description': 'CPU请求资源'},
                            'REQUESTSMEM': {'required': False, 'default': '128Mi', 'description': '内存请求资源'},
                            'LIMITSCPU': {'required': False, 'default': '500m', 'description': 'CPU资源限制'},
                            'LIMITSMEM': {'required': False, 'default': '256Mi', 'description': '内存资源限制'}
                        }
                    }
                    
                    # 获取对应模板类型的配置映射
                    config_mapping = deploy_config_mapping.get(template_type, deploy_config_mapping['maven'])
                    
                    # 验证和处理配置参数
                    processed_config = {}
                    converted_resources = []
                    
                    for param_name, param_value in deploy_config_data.items():
                        if param_name not in config_mapping:
                            raise ValueError(f'不支持的部署参数: {param_name}。模板类型 {template_type} 支持的参数: {", ".join(config_mapping.keys())}')
                        
                        param_info = config_mapping[param_name]
                        
                        # 必填参数验证
                        if param_info['required'] and (param_value is None or str(param_value).strip() == ''):
                            raise ValueError(f'必填参数不能为空: {param_name}')
                        
                        # 端口号验证
                        if param_name == 'CTPORT' and param_value is not None:
                            try:
                                param_value = int(param_value)
                                if param_value <= 0 or param_value > 65535:
                                    raise ValueError('端口号必须在1-65535之间')
                            except (ValueError, TypeError):
                                raise ValueError(f'无效的端口号: {param_value}')
                        
                        # Ingress验证
                        if param_name == 'INGRESS' and param_value is not None:
                            if str(param_value).lower() not in ['yes', 'no', 'true', 'false']:
                                raise ValueError(f'INGRESS参数值无效: {param_value}，仅支持: yes, no, true, false')
                            # 标准化为yes/no
                            param_value = 'yes' if str(param_value).lower() in ['yes', 'true'] else 'no'
                        
                        # 资源单位转换
                        if resource_conversion and param_name in ['LIMITSCPU', 'REQUESTSCPU', 'LIMITSMEM', 'REQUESTSMEM']:
                            original_value = param_value
                            
                            if 'CPU' in param_name:
                                # CPU资源转换：支持数字转毫核、保持现有格式
                                try:
                                    if isinstance(param_value, (int, float)):
                                        converted_value = f"{int(param_value * 1000)}m"
                                        converted_resources.append({
                                            'parameter': param_name,
                                            'original': original_value,
                                            'converted': converted_value,
                                            'unit': 'CPU cores to millicores'
                                        })
                                        param_value = converted_value
                                    elif str(param_value).replace('.', '').isdigit():
                                        # 纯数字字符串
                                        converted_value = f"{int(float(param_value) * 1000)}m"
                                        converted_resources.append({
                                            'parameter': param_name,
                                            'original': original_value,
                                            'converted': converted_value,
                                            'unit': 'CPU cores to millicores'
                                        })
                                        param_value = converted_value
                                except (ValueError, TypeError):
                                    pass  # 保持原值，可能已经是正确格式
                                    
                            elif 'MEM' in param_name:
                                # 内存资源转换：支持数字转Mi、保持现有格式
                                try:
                                    if isinstance(param_value, (int, float)):
                                        converted_value = f"{int(param_value * 1024)}Mi"
                                        converted_resources.append({
                                            'parameter': param_name,
                                            'original': original_value,
                                            'converted': converted_value,
                                            'unit': 'GB to MiB'
                                        })
                                        param_value = converted_value
                                    elif str(param_value).replace('.', '').isdigit():
                                        # 纯数字字符串
                                        converted_value = f"{int(float(param_value) * 1024)}Mi"
                                        converted_resources.append({
                                            'parameter': param_name,
                                            'original': original_value,
                                            'converted': converted_value,
                                            'unit': 'GB to MiB'
                                        })
                                        param_value = converted_value
                                except (ValueError, TypeError):
                                    pass  # 保持原值，可能已经是正确格式
                        
                        processed_config[param_name] = param_value
                    
                    # 更新YAML文件中的配置
                    update_results = []
                    
                    # 收集所有需要更新的变量
                    for param_name, param_value in processed_config.items():
                        update_results.append({
                            'parameter': param_name,
                            'value': param_value,
                            'description': config_mapping[param_name]['description']
                        })
                    
                    # 一次性更新所有变量
                    success = yaml_parser.update_variables(str(yaml_file), processed_config)
                    if not success:
                        raise Exception('更新YAML文件失败')
                    
                    # 成功处理
                    success_count += 1
                    task_result = {
                        'project_id': task.get('project_id'),
                        'branch': task.get('branch', 'develop'),
                        'task_name': task.get('task_name'),
                        'success': True,
                        'message': f'部署配置更新成功 (模板类型: {template_type})',
                        'status_code': 200,
                        'updated_configs': update_results,
                        'converted_resources': converted_resources,
                        'template_type': template_type
                    }
                    
                    results.append(task_result)
                    
                except Exception as task_update_error:
                    error_count += 1
                    results.append({
                        'project_id': task.get('project_id'),
                        'branch': task.get('branch', 'develop'),
                        'task_name': task.get('task_name'),
                        'success': False,
                        'error': str(task_update_error),
                        'status_code': 500
                    })
                    
            except Exception as task_error:
                error_count += 1
                results.append({
                    'project_id': task.get('project_id'),
                    'branch': task.get('branch', 'develop'),
                    'task_name': task.get('task_name'),
                    'success': False,
                    'error': str(task_error),
                    'status_code': 500
                })
        
        # 生成处理摘要
        summary = {
            'total_tasks': len(tasks),
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': f"{(success_count / len(tasks) * 100):.1f}%" if tasks else "0%"
        }
        
        return jsonify({
            'success': error_count == 0,
            'message': f'批量部署配置处理完成：成功 {success_count} 个，失败 {error_count} 个',
            'results': results,
            'summary': summary
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 

# ============ TASK009: 任务配置获取API增强 ============

@task_config_bp.route('/<int:pipeline_id>/<task_name>', methods=['GET'])
def get_enhanced_task_config(pipeline_id, task_name):
    """
    TASK009: 增强的任务配置获取API
    
    功能描述：
    - 扩展原有的任务配置获取API
    - 支持按阶段过滤配置参数
    - 返回结构化的配置数据，按阶段分组
    - 支持配置参数的默认值填充
    - 添加配置完整性检查
    
    路径参数：
    - pipeline_id: 流水线ID
    - task_name: 任务名称
    
    查询参数：
    - stage_type: 阶段过滤（可选）：compile, build, deploy, all
    - branch: 分支名（默认develop）
    - include_defaults: 是否包含默认值（默认true）
    - format: 返回格式（grouped/flat，默认grouped）
    - completeness_check: 是否进行完整性检查（默认true）
    
    返回参数：
    - config: 配置数据（按阶段分组或扁平结构）
    - metadata: 元数据信息（模板类型、完整性状态等）
    - defaults: 默认值信息（如果include_defaults=true）
    - completeness: 完整性检查结果（如果completeness_check=true）
    """
    try:
        # 获取查询参数
        stage_type = request.args.get('stage_type', 'all')
        branch = request.args.get('branch', 'develop')
        include_defaults = request.args.get('include_defaults', 'true').lower() == 'true'
        response_format = request.args.get('format', 'grouped')
        completeness_check = request.args.get('completeness_check', 'true').lower() == 'true'
        
        # 参数验证
        valid_stages = ['compile', 'build', 'deploy', 'all']
        if stage_type not in valid_stages:
            return jsonify({
                'success': False,
                'error': f'无效的阶段类型。支持的阶段: {", ".join(valid_stages)}'
            }), 400
            
        valid_formats = ['grouped', 'flat']
        if response_format not in valid_formats:
            return jsonify({
                'success': False,
                'error': f'无效的返回格式。支持的格式: {", ".join(valid_formats)}'
            }), 400
        
        # 查找流水线信息
        pipeline = db_manager.execute_query(
            "SELECT * FROM pipelines WHERE id = %s",
            params=(pipeline_id,),
            fetch_one=True
        )
        
        if not pipeline:
            return jsonify({
                'success': False,
                'error': f'流水线不存在: {pipeline_id}'
            }), 404
        
        # 构建YAML文件路径
        project_id = pipeline['project_id']
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        # 检查任务是否存在
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'任务配置文件不存在: {task_name}',
                'file_path': str(yaml_file)
            }), 404
        
        # 获取YAML配置
        try:
            variables = yaml_parser.get_variables(str(yaml_file))
            yaml_config = yaml_parser.load_yaml_file(str(yaml_file))
        except Exception as yaml_error:
            return jsonify({
                'success': False,
                'error': f'读取YAML配置失败: {str(yaml_error)}'
            }), 500
        
        # 检测模板类型
        template_type = _detect_template_type(variables)
        
        # 定义各阶段的配置参数定义
        stage_definitions = _get_stage_definitions(template_type)
        
        # 按阶段分组配置
        grouped_config = {}
        flat_config = {}
        missing_configs = []
        
        # 处理各个阶段
        stages_to_process = [stage_type] if stage_type != 'all' else ['compile', 'build', 'deploy']
        
        for stage in stages_to_process:
            if stage not in stage_definitions:
                continue
                
            stage_config = {}
            stage_defaults = {}
            stage_missing = []
            
            # 获取阶段开关状态
            stage_enabled = variables.get(stage, 'off') == 'on'
            stage_config['enabled'] = stage_enabled
            stage_defaults['enabled'] = False
            
            # 处理阶段参数
            for param_name, param_info in stage_definitions[stage].items():
                param_value = variables.get(param_name)
                default_value = param_info.get('default')
                
                if param_value is not None:
                    # 类型转换
                    if param_info.get('type') == 'int':
                        try:
                            param_value = int(param_value)
                        except (ValueError, TypeError):
                            pass
                    elif param_info.get('type') == 'bool':
                        param_value = str(param_value).lower() in ['true', 'yes', 'on']
                    
                    stage_config[param_name] = param_value
                else:
                    # 参数缺失
                    if param_info.get('required', False):
                        stage_missing.append({
                            'parameter': param_name,
                            'description': param_info.get('description', ''),
                            'default': default_value
                        })
                    
                    # 如果需要包含默认值
                    if include_defaults and default_value is not None:
                        stage_config[param_name] = default_value
                
                # 记录默认值信息
                if include_defaults:
                    stage_defaults[param_name] = {
                        'value': default_value,
                        'description': param_info.get('description', ''),
                        'required': param_info.get('required', False),
                        'type': param_info.get('type', 'string')
                    }
            
            # 存储结果
            grouped_config[stage] = stage_config
            if include_defaults:
                grouped_config[f'{stage}_defaults'] = stage_defaults
            
            # 扁平结构
            for key, value in stage_config.items():
                flat_config[f'{stage}_{key}'] = value
            
            # 记录缺失配置
            if stage_missing:
                missing_configs.extend([{**item, 'stage': stage} for item in stage_missing])
        
        # 添加通用配置信息
        metadata = {
            'template_type': template_type,
            'pipeline_id': pipeline_id,
            'project_id': project_id,
            'task_name': task_name,
            'branch': branch,
            'yaml_file_path': str(yaml_file),
            'last_modified': yaml_file.stat().st_mtime if yaml_file.exists() else None
        }
        
        # 完整性检查
        completeness_result = {}
        if completeness_check:
            total_required = sum(
                len([p for p in stage_definitions.get(stage, {}).values() if p.get('required', False)])
                for stage in stages_to_process if stage in stage_definitions
            )
            
            completeness_result = {
                'total_required_params': total_required,
                'missing_required_params': len([item for item in missing_configs if item.get('required', False)]),
                'missing_params': missing_configs,
                'completeness_percentage': (
                    ((total_required - len(missing_configs)) / total_required * 100) 
                    if total_required > 0 else 100
                ),
                'is_complete': len(missing_configs) == 0
            }
        
        # 构建响应数据
        response_data = {
            'success': True,
            'config': grouped_config if response_format == 'grouped' else flat_config,
            'metadata': metadata
        }
        
        if include_defaults:
            response_data['defaults_included'] = True
        
        if completeness_check:
            response_data['completeness'] = completeness_result
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/<int:pipeline_id>/<task_name>/stage/<stage_type>', methods=['GET'])
def get_stage_specific_config(pipeline_id, task_name, stage_type):
    """
    获取特定阶段的配置信息
    
    功能描述：
    - 针对单个阶段的详细配置获取
    - 包含参数验证和类型转换
    - 提供参数描述和使用建议
    
    路径参数：
    - pipeline_id: 流水线ID
    - task_name: 任务名称
    - stage_type: 阶段类型（compile/build/deploy）
    
    查询参数：
    - branch: 分支名（默认develop）
    - include_schema: 是否包含参数模式定义（默认false）
    """
    try:
        # 获取查询参数
        branch = request.args.get('branch', 'develop')
        include_schema = request.args.get('include_schema', 'false').lower() == 'true'
        
        # 参数验证
        valid_stages = ['compile', 'build', 'deploy']
        if stage_type not in valid_stages:
            return jsonify({
                'success': False,
                'error': f'无效的阶段类型。支持的阶段: {", ".join(valid_stages)}'
            }), 400
        
        # 查找流水线信息
        pipeline = db_manager.execute_query(
            "SELECT * FROM pipelines WHERE id = %s",
            params=(pipeline_id,),
            fetch_one=True
        )
        
        if not pipeline:
            return jsonify({
                'success': False,
                'error': f'流水线不存在: {pipeline_id}'
            }), 404
        
        # 构建YAML文件路径
        project_id = pipeline['project_id']
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        # 检查任务是否存在
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'任务配置文件不存在: {task_name}',
                'file_path': str(yaml_file)
            }), 404
        
        # 获取YAML配置
        try:
            variables = yaml_parser.get_variables(str(yaml_file))
            yaml_config = yaml_parser.load_yaml_file(str(yaml_file))
        except Exception as yaml_error:
            return jsonify({
                'success': False,
                'error': f'读取YAML配置失败: {str(yaml_error)}'
            }), 500
        
        # 检测模板类型
        template_type = _detect_template_type(variables)
        
        # 获取阶段定义
        stage_definitions = _get_stage_definitions(template_type)
        
        if stage_type not in stage_definitions:
            return jsonify({
                'success': False,
                'error': f'模板类型 {template_type} 不支持阶段: {stage_type}'
            }), 400
        
        # 获取阶段配置
        stage_config = {}
        stage_defaults = {}
        stage_missing = []
        
        # 获取阶段开关状态
        stage_enabled = variables.get(stage_type, 'off') == 'on'
        stage_config['enabled'] = stage_enabled
        stage_defaults['enabled'] = False
        
        # 处理阶段参数
        for param_name, param_info in stage_definitions[stage_type].items():
            param_value = variables.get(param_name)
            default_value = param_info.get('default')
            
            if param_value is not None:
                # 类型转换
                if param_info.get('type') == 'int':
                    try:
                        param_value = int(param_value)
                    except (ValueError, TypeError):
                        pass
                elif param_info.get('type') == 'bool':
                    param_value = str(param_value).lower() in ['true', 'yes', 'on']
                
                stage_config[param_name] = param_value
            else:
                # 参数缺失
                if param_info.get('required', False):
                    stage_missing.append({
                        'parameter': param_name,
                        'description': param_info.get('description', ''),
                        'default': default_value,
                        'stage': stage_type
                    })
                
                # 包含默认值
                if default_value is not None:
                    stage_config[param_name] = default_value
            
            # 记录默认值信息
            stage_defaults[param_name] = {
                'value': default_value,
                'description': param_info.get('description', ''),
                'required': param_info.get('required', False),
                'type': param_info.get('type', 'string')
            }
        
        # 构建响应
        stage_response = {
            'success': True,
            'stage_type': stage_type,
            'config': stage_config,
            'defaults': stage_defaults,
            'metadata': {
                'template_type': template_type,
                'pipeline_id': pipeline_id,
                'project_id': project_id,
                'task_name': task_name,
                'branch': branch,
                'yaml_file_path': str(yaml_file)
            },
            'enabled': stage_enabled,
            'completeness': {
                'missing_params': stage_missing,
                'is_complete': len(stage_missing) == 0
            }
        }
        
        # 包含模式定义
        if include_schema:
            stage_response['schema'] = stage_definitions.get(stage_type, {})
        
        return jsonify(stage_response)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_config_bp.route('/templates', methods=['GET'])
def get_config_templates():
    """
    获取配置模板信息
    
    功能描述：
    - 返回Maven和NPM模板的参数定义
    - 包含参数类型、默认值、描述信息
    - 支持前端动态生成配置表单
    
    查询参数：
    - template_type: 模板类型（maven/npm/all，默认all）
    """
    try:
        template_type = request.args.get('template_type', 'all')
        
        # 获取模板定义
        if template_type == 'all':
            templates = {
                'maven': _get_stage_definitions('maven'),
                'npm': _get_stage_definitions('npm')
            }
        elif template_type in ['maven', 'npm']:
            templates = {
                template_type: _get_stage_definitions(template_type)
            }
        else:
            return jsonify({
                'success': False,
                'error': f'无效的模板类型。支持的类型: maven, npm, all'
            }), 400
        
        return jsonify({
            'success': True,
            'templates': templates,
            'metadata': {
                'total_templates': len(templates),
                'available_stages': ['compile', 'build', 'deploy']
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============ TASK009辅助函数 ============

def _detect_template_type(variables):
    """检测模板类型"""
    # Maven特征参数
    maven_indicators = ['JDKVERSION', 'BUILDFORMAT', 'TARGETDIR', 'BUILDCMD']
    # NPM特征参数
    npm_indicators = ['NODEVERSION', 'PNPMVERSION', 'NPMDIR']
    
    maven_score = sum(1 for indicator in maven_indicators if indicator in variables)
    npm_score = sum(1 for indicator in npm_indicators if indicator in variables)
    
    if maven_score > npm_score:
        return 'maven'
    elif npm_score > maven_score:
        return 'npm'
    else:
        # 默认返回Maven类型，或根据其他特征判断
        return 'maven'

def _get_stage_definitions(template_type):
    """获取阶段参数定义"""
    if template_type == 'maven':
        return {
            'compile': {
                'JDKVERSION': {
                    'description': 'JDK版本',
                    'type': 'string',
                    'default': '8',
                    'required': True,
                    'options': ['8', '11', '17', '21']
                },
                'CODEPATH': {
                    'description': '代码路径',
                    'type': 'string',
                    'default': '',
                    'required': False
                },
                'TARGETDIR': {
                    'description': '制品路径',
                    'type': 'string',
                    'default': 'target',
                    'required': False
                },
                'BUILDFORMAT': {
                    'description': '制品格式',
                    'type': 'string',
                    'default': 'jar',
                    'required': False,
                    'options': ['jar', 'war']
                },
                'BUILDCMD': {
                    'description': '编译命令',
                    'type': 'string',
                    'default': 'mvn clean package -Dmaven.test.skip=true -U',
                    'required': False
                }
            },
            'build': {
                'HARBORNAME': {
                    'description': 'Harbor项目名称',
                    'type': 'string',
                    'default': 'devops',
                    'required': True
                },
                'BUILDDIR': {
                    'description': 'Dockerfile路径',
                    'type': 'string',
                    'default': '.',
                    'required': False
                },
                'PLATFORM': {
                    'description': '镜像架构',
                    'type': 'string',
                    'default': 'linux/amd64',
                    'required': False,
                    'options': ['linux/amd64', 'linux/arm64']
                },
                'SERVICENAME': {
                    'description': '服务名',
                    'type': 'string',
                    'default': 'app',
                    'required': True
                }
            },
            'deploy': {
                'NAMESPACE': {
                    'description': '命名空间',
                    'type': 'string',
                    'default': 'app-dev',
                    'required': True
                },
                'SERVICENAME': {
                    'description': '服务名',
                    'type': 'string',
                    'default': 'app',
                    'required': True
                },
                'CTPORT': {
                    'description': '应用端口',
                    'type': 'int',
                    'default': 80,
                    'required': False
                },
                'K8S': {
                    'description': '发布集群',
                    'type': 'string',
                    'default': 'K8S_cmdicncf_jkyw',
                    'required': False
                },
                'INGRESS': {
                    'description': '是否启用Ingress',
                    'type': 'string',
                    'default': 'yes',
                    'required': False,
                    'options': ['yes', 'no']
                },
                'LIMITSCPU': {
                    'description': 'CPU资源限制',
                    'type': 'string',
                    'default': '1000m',
                    'required': False
                },
                'LIMITSMEM': {
                    'description': '内存资源限制',
                    'type': 'string',
                    'default': '1024Mi',
                    'required': False
                }
            }
        }
    elif template_type == 'npm':
        return {
            'compile': {
                'NODEVERSION': {
                    'description': 'Node.js版本',
                    'type': 'string',
                    'default': '14.18',
                    'required': True
                },
                'PNPMVERSION': {
                    'description': 'PNPM版本',
                    'type': 'string',
                    'default': '7.33.7',
                    'required': True
                },
                'CODEPATH': {
                    'description': '代码路径',
                    'type': 'string',
                    'default': '',
                    'required': False
                },
                'BUILDCMD': {
                    'description': '编译命令',
                    'type': 'string',
                    'default': 'pnpm run build',
                    'required': False
                },
                'NPMDIR': {
                    'description': '制品发布目录',
                    'type': 'string',
                    'default': 'dist',
                    'required': False
                }
            },
            'build': {
                'HARBORNAME': {
                    'description': 'Harbor项目名称',
                    'type': 'string',
                    'default': 'devops',
                    'required': True
                },
                'BUILDDIR': {
                    'description': 'Dockerfile路径',
                    'type': 'string',
                    'default': '.',
                    'required': False
                },
                'PLATFORM': {
                    'description': '镜像架构',
                    'type': 'string',
                    'default': 'linux/amd64',
                    'required': False,
                    'options': ['linux/amd64', 'linux/arm64']
                },
                'INGRESS': {
                    'description': '是否启用Ingress',
                    'type': 'string',
                    'default': 'yes',
                    'required': False,
                    'options': ['yes', 'no']
                }
            },
            'deploy': {
                'NAMESPACE': {
                    'description': '命名空间',
                    'type': 'string',
                    'default': 'app-dev',
                    'required': True
                },
                'SERVICENAME': {
                    'description': '服务名',
                    'type': 'string',
                    'default': '$CI_PROJECT_NAME',
                    'required': True
                },
                'CTPORT': {
                    'description': '应用端口',
                    'type': 'int',
                    'default': 80,
                    'required': False
                },
                'K8S': {
                    'description': '发布集群',
                    'type': 'string',
                    'default': 'K8S_cmdicncf_jkyw',
                    'required': False
                },
                'REQUESTSCPU': {
                    'description': 'CPU请求资源',
                    'type': 'string',
                    'default': '100m',
                    'required': False
                },
                'REQUESTSMEM': {
                    'description': '内存请求资源',
                    'type': 'string',
                    'default': '128Mi',
                    'required': False
                },
                'LIMITSCPU': {
                    'description': 'CPU资源限制',
                    'type': 'string',
                    'default': '500m',
                    'required': False
                },
                'LIMITSMEM': {
                    'description': '内存资源限制',
                    'type': 'string',
                    'default': '256Mi',
                    'required': False
                }
            }
        }
    else:
        return {}

@task_config_bp.route('/batch_update', methods=['POST'])
def batch_update_config():
    """
    批量配置更新API (TASK010)
    
    功能描述：支持一次性更新任务的所有阶段配置
    
    入参：
    {
        "project_id": "项目ID",
        "branch": "分支名（默认develop）",
        "task_name": "任务名称",
        "template_type": "模板类型（maven/npm）",
        "stage_config": {
            "compile": {
                "enabled": true,
                "config": {"JDKVERSION": "8", ...}
            },
            "build": {
                "enabled": true,  
                "config": {"HARBORNAME": "devops", ...}
            },
            "deploy": {
                "enabled": true,
                "config": {"NAMESPACE": "app-dev", ...}
            }
        },
        "sync_to_gitlab": true,
        "validation_level": "normal"
    }
    
    返回参数：
    - success: 操作是否成功
    - message: 操作结果消息
    - updated_stages: 更新的阶段列表
    - validation_results: 参数验证结果
    - sync_status: GitLab同步状态
    """
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        template_type = data.get('template_type')
        stage_config = data.get('stage_config', {})
        sync_to_gitlab = data.get('sync_to_gitlab', True)
        validation_level = data.get('validation_level', 'normal')
        
        # 参数验证
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        if not template_type:
            return jsonify({
                'success': False,
                'error': '缺少模板类型参数: template_type (maven/npm)'
            }), 400
        
        if template_type not in ['maven', 'npm']:
            return jsonify({
                'success': False,
                'error': 'template_type 只支持 maven 或 npm'
            }), 400
        
        if not stage_config:
            return jsonify({
                'success': False,
                'error': '缺少阶段配置参数: stage_config'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 获取当前配置
        current_variables = yaml_parser.get_variables(str(yaml_file))
        
        # 批量验证所有配置参数
        validation_results = {}
        validator = ConfigValidator()
        
        # 合并所有配置进行验证
        all_config = {}
        for stage_name, stage_data in stage_config.items():
            if stage_data.get('config'):
                all_config.update(stage_data['config'])
        
        if all_config:
            validation_result = validator.validate_complete_config(
                config=all_config,
                template_type=template_type
            )
            validation_results['batch_validation'] = validation_result
            
            # 如果严格模式下有错误，直接返回
            if validation_level == 'strict' and not validation_result['is_valid']:
                return jsonify({
                    'success': False,
                    'error': '配置验证失败',
                    'validation_results': validation_results
                }), 400
        
        # 开始事务性更新
        updated_stages = []
        update_errors = []
        updated_variables = current_variables.copy()
        
        # 处理每个阶段的配置
        for stage_name in ['compile', 'build', 'deploy']:
            if stage_name not in stage_config:
                continue
            
            stage_data = stage_config[stage_name]
            stage_enabled = stage_data.get('enabled', False)
            stage_config_params = stage_data.get('config', {})
            
            try:
                # 更新阶段开关
                updated_variables[stage_name] = "on" if stage_enabled else "off"
                
                # 更新阶段配置参数
                if stage_config_params:
                    # 验证阶段特定配置
                    stage_validation = validator.validate_complete_config(
                        config=stage_config_params,
                        template_type=template_type
                    )
                    validation_results[f'{stage_name}_validation'] = stage_validation
                    
                    # 更新变量
                    for param_name, param_value in stage_config_params.items():
                        updated_variables[param_name] = param_value
                
                updated_stages.append({
                    'stage': stage_name,
                    'enabled': stage_enabled,
                    'config_count': len(stage_config_params)
                })
                
            except Exception as stage_error:
                update_errors.append({
                    'stage': stage_name,
                    'error': str(stage_error)
                })
        
        # 如果有更新错误，返回错误信息
        if update_errors:
            return jsonify({
                'success': False,
                'error': '部分阶段更新失败',
                'update_errors': update_errors,
                'validation_results': validation_results
            }), 500
        
        # 批量更新YAML文件
        try:
            success = yaml_parser.update_variables(str(yaml_file), updated_variables)
            if not success:
                return jsonify({
                    'success': False,
                    'error': '批量更新YAML文件失败'
                }), 500
        except Exception as yaml_error:
            return jsonify({
                'success': False,
                'error': f'YAML文件更新异常: {str(yaml_error)}'
            }), 500
        
        # 更新数据库配置
        db_update_status = []
        try:
            # 查找对应的pipeline和task
            pipeline = db_manager.execute_query(
                "SELECT id FROM pipelines WHERE project_id = %s AND branch = %s",
                params=(project_id, branch),
                fetch_one=True
            )
            
            if pipeline:
                task = db_manager.execute_query(
                    "SELECT id FROM pipeline_tasks WHERE pipeline_id = %s AND name = %s",
                    params=(pipeline['id'], task_name),
                    fetch_one=True
                )
                
                if task:
                    for stage_name in ['compile', 'build', 'deploy']:
                        if stage_name not in stage_config:
                            continue
                        
                        stage_data = stage_config[stage_name]
                        
                        # 查找现有阶段配置
                        existing_stage = db_manager.execute_query(
                            "SELECT id, config FROM pipeline_task_stages WHERE task_id = %s AND type = %s",
                            params=(task['id'], stage_name),
                            fetch_one=True
                        )
                        
                        # 构建配置数据
                        config_data = {
                            'enabled': stage_data.get('enabled', False),
                            'status': "on" if stage_data.get('enabled', False) else "off",
                            'type': stage_name,
                            'template_type': template_type,
                            'parameters': stage_data.get('config', {}),
                            'last_updated': datetime.now().isoformat()
                        }
                        
                        if existing_stage:
                            # 更新现有配置
                            db_manager.execute_update(
                                "UPDATE pipeline_task_stages SET config = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                                params=(json.dumps(config_data), existing_stage['id'])
                            )
                            db_update_status.append(f"{stage_name}: 更新成功")
                        else:
                            # 创建新配置
                            order_index = 0 if stage_name == 'compile' else 1 if stage_name == 'build' else 2
                            db_manager.execute_insert(
                                """INSERT INTO pipeline_task_stages (task_id, type, name, order_index, config)
                                   VALUES (%s, %s, %s, %s, %s)""",
                                params=(task['id'], stage_name, stage_name, order_index, json.dumps(config_data))
                            )
                            db_update_status.append(f"{stage_name}: 创建成功")
                            
        except Exception as db_error:
            print(f"数据库批量更新失败: {db_error}")
            db_update_status.append(f"数据库更新失败: {str(db_error)}")
        
        # GitLab同步
        sync_status = "跳过"
        if sync_to_gitlab:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                gitlab_file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                
                # 生成详细的提交消息
                commit_message_parts = [f"批量更新{task_name}配置"]
                for stage_info in updated_stages:
                    stage_status = "启用" if stage_info['enabled'] else "禁用"
                    commit_message_parts.append(f"{stage_info['stage']}阶段{stage_status}")
                
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path=gitlab_file_path,
                    content=content,
                    branch="main",
                    commit_message=" | ".join(commit_message_parts)
                )
                sync_status = "成功"
                
            except Exception as sync_error:
                sync_status = f"失败: {str(sync_error)}"
        
        # 构建响应
        response_data = {
            'success': True,
            'message': f'批量配置更新成功，共更新{len(updated_stages)}个阶段',
            'updated_stages': updated_stages,
            'validation_results': validation_results,
            'sync_status': sync_status,
            'database_update': db_update_status,
            'updated_variables_count': len(updated_variables)
        }
        
        # 如果有警告，添加到响应中
        warnings = []
        for result in validation_results.values():
            if 'warnings' in result and result['warnings']:
                warnings.extend(result['warnings'])
        
        if warnings:
            response_data['warnings'] = warnings
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'批量配置更新异常: {str(e)}'
        }), 500

@task_config_bp.route('/batch_update/status', methods=['GET'])
def get_batch_update_status():
    """
    获取批量更新状态API
    
    功能描述：获取任务的批量配置更新历史和状态
    
    参数：
    - project_id: 项目ID
    - branch: 分支名（默认develop）
    - task_name: 任务名称
    - limit: 返回记录数量限制（默认10）
    
    返回参数：
    - success: 操作是否成功
    - current_config: 当前配置状态
    - update_history: 更新历史记录
    - stage_summary: 阶段配置摘要
    """
    try:
        project_id = request.args.get('project_id')
        branch = request.args.get('branch', 'develop')
        task_name = request.args.get('task_name')
        limit = int(request.args.get('limit', 10))
        
        if not all([project_id, task_name]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 获取当前配置
        current_variables = yaml_parser.get_variables(str(yaml_file))
        current_config = {
            'compile': {
                'enabled': current_variables.get('compile', 'off') == 'on',
                'status': current_variables.get('compile', 'off')
            },
            'build': {
                'enabled': current_variables.get('build', 'off') == 'on',
                'status': current_variables.get('build', 'off')
            },
            'deploy': {
                'enabled': current_variables.get('deploy', 'off') == 'on',
                'status': current_variables.get('deploy', 'off')
            }
        }
        
        # 获取数据库中的配置历史
        update_history = []
        stage_summary = {}
        
        try:
            # 查找对应的pipeline和task
            pipeline = db_manager.execute_query(
                "SELECT id FROM pipelines WHERE project_id = %s AND branch = %s",
                params=(project_id, branch),
                fetch_one=True
            )
            
            if pipeline:
                task = db_manager.execute_query(
                    "SELECT id FROM pipeline_tasks WHERE pipeline_id = %s AND name = %s",
                    params=(pipeline['id'], task_name),
                    fetch_one=True
                )
                
                if task:
                    # 获取所有阶段配置
                    stages = db_manager.execute_query(
                        """SELECT type, name, config, created_at, updated_at 
                           FROM pipeline_task_stages 
                           WHERE task_id = %s 
                           ORDER BY order_index, updated_at DESC
                           LIMIT %s""",
                        params=(task['id'], limit),
                        fetch_all=True
                    )
                    
                    for stage in stages:
                        stage_config = json.loads(stage['config']) if stage['config'] else {}
                        stage_info = {
                            'stage_type': stage['type'],
                            'stage_name': stage['name'],
                            'enabled': stage_config.get('enabled', False),
                            'template_type': stage_config.get('template_type', 'unknown'),
                            'parameter_count': len(stage_config.get('parameters', {})),
                            'last_updated': stage['updated_at'].isoformat() if stage['updated_at'] else None,
                            'created_at': stage['created_at'].isoformat() if stage['created_at'] else None
                        }
                        
                        update_history.append(stage_info)
                        stage_summary[stage['type']] = {
                            'enabled': stage_config.get('enabled', False),
                            'parameter_count': len(stage_config.get('parameters', {})),
                            'last_updated': stage['updated_at'].isoformat() if stage['updated_at'] else None
                        }
                        
        except Exception as db_error:
            print(f"数据库查询失败: {db_error}")
            # 数据库查询失败不影响主要功能
        
        return jsonify({
            'success': True,
            'current_config': current_config,
            'update_history': update_history,
            'stage_summary': stage_summary,
            'yaml_file_path': str(yaml_file),
            'total_variables': len(current_variables)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取批量更新状态失败: {str(e)}'
        }), 500

@task_config_bp.route('/batch_update/preview', methods=['POST'])
def preview_batch_update():
    """
    批量更新预览API
    
    功能描述：预览批量配置更新的影响，不实际执行更新
    
    入参：与batch_update_config相同
    
    返回参数：
    - success: 操作是否成功
    - preview_summary: 更新预览摘要
    - changes: 具体变更列表
    - validation_results: 参数验证结果
    - affected_variables: 受影响的变量列表
    """
    try:
        data = request.json
        project_id = data.get('project_id')
        branch = data.get('branch', 'develop')
        task_name = data.get('task_name')
        template_type = data.get('template_type')
        stage_config = data.get('stage_config', {})
        validation_level = data.get('validation_level', 'normal')
        
        # 参数验证
        if not all([project_id, task_name, template_type]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数: project_id, task_name, template_type'
            }), 400
        
        # 构建文件路径
        yaml_file = WORKSPACE_PATH / str(project_id) / branch / task_name / 'gitlab-ci.yml'
        
        if not yaml_file.exists():
            return jsonify({
                'success': False,
                'error': f'YAML文件不存在: {yaml_file}'
            }), 404
        
        # 获取当前配置
        current_variables = yaml_parser.get_variables(str(yaml_file))
        
        # 预览更新变更
        changes = []
        affected_variables = []
        validation_results = {}
        
        # 准备新配置
        new_variables = current_variables.copy()
        
        validator = ConfigValidator()
        
        # 处理每个阶段的预览
        for stage_name in ['compile', 'build', 'deploy']:
            if stage_name not in stage_config:
                continue
            
            stage_data = stage_config[stage_name]
            stage_enabled = stage_data.get('enabled', False)
            stage_config_params = stage_data.get('config', {})
            
            # 阶段开关变更
            old_stage_value = current_variables.get(stage_name, 'off')
            new_stage_value = "on" if stage_enabled else "off"
            
            if old_stage_value != new_stage_value:
                changes.append({
                    'type': 'stage_toggle',
                    'stage': stage_name,
                    'variable': stage_name,
                    'old_value': old_stage_value,
                    'new_value': new_stage_value,
                    'change_type': '启用' if stage_enabled else '禁用'
                })
                affected_variables.append(stage_name)
            
            new_variables[stage_name] = new_stage_value
            
            # 配置参数变更
            if stage_config_params:
                # 验证阶段配置
                stage_validation = validator.validate_complete_config(
                    config=stage_config_params,
                    template_type=template_type
                )
                validation_results[f'{stage_name}_validation'] = stage_validation
                
                for param_name, param_value in stage_config_params.items():
                    old_value = current_variables.get(param_name, '')
                    
                    if str(old_value) != str(param_value):
                        changes.append({
                            'type': 'parameter',
                            'stage': stage_name,
                            'variable': param_name,
                            'old_value': old_value,
                            'new_value': param_value,
                            'change_type': '新增' if param_name not in current_variables else '修改'
                        })
                        affected_variables.append(param_name)
                    
                    new_variables[param_name] = param_value
        
        # 整体配置验证
        all_new_config = {}
        for stage_name, stage_data in stage_config.items():
            if stage_data.get('config'):
                all_new_config.update(stage_data['config'])
        
        if all_new_config:
            batch_validation = validator.validate_complete_config(
                config=all_new_config,
                template_type=template_type
            )
            validation_results['batch_validation'] = batch_validation
        
        # 生成预览摘要
        preview_summary = {
            'total_changes': len(changes),
            'stage_toggles': len([c for c in changes if c['type'] == 'stage_toggle']),
            'parameter_changes': len([c for c in changes if c['type'] == 'parameter']),
            'affected_stages': list(set([c['stage'] for c in changes])),
            'validation_passed': all(result.get('is_valid', True) for result in validation_results.values()),
            'has_warnings': any(result.get('warnings') for result in validation_results.values()),
            'template_type': template_type
        }
        
        return jsonify({
            'success': True,
            'preview_summary': preview_summary,
            'changes': changes,
            'validation_results': validation_results,
            'affected_variables': list(set(affected_variables)),
            'current_variables_count': len(current_variables),
            'new_variables_count': len(new_variables)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'批量更新预览失败: {str(e)}'
        }), 500