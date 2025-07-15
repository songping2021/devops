#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify
from backend.utils.database import db_manager
from backend.utils.gitlab_client import gitlab_client
from backend.config.settings import WORKSPACE_PATH, TEMPLATE_PATH
from pathlib import Path
import shutil
import json
import time

# 创建流水线API蓝图
pipelines_bp = Blueprint('pipelines', __name__, url_prefix='/api/pipelines')

def init_dependencies(db_mgr, gitlab_cli, workspace_path, template_path):
    """初始化依赖项"""
    global db_manager, gitlab_client, WORKSPACE_PATH, TEMPLATE_PATH
    db_manager = db_mgr
    gitlab_client = gitlab_cli
    WORKSPACE_PATH = workspace_path
    TEMPLATE_PATH = template_path

@pipelines_bp.route('', methods=['GET'])
def get_pipelines():
    """获取所有流水线列表"""
    try:
        pipelines = db_manager.execute_query(
            "SELECT * FROM pipelines ORDER BY updated_at DESC",
            fetch_all=True
        )
        return jsonify({'pipelines': pipelines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pipelines_bp.route('/<int:pipeline_id>', methods=['GET'])
def get_pipeline(pipeline_id):
    """获取单个流水线详情"""
    try:
        pipeline = db_manager.execute_query(
            "SELECT * FROM pipelines WHERE id = %s",
            params=(pipeline_id,),
            fetch_one=True
        )
        
        if pipeline is None:
            return jsonify({'error': '流水线不存在'}), 404
            
        return jsonify({'pipeline': pipeline})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pipelines_bp.route('', methods=['POST'])
def create_pipeline():
    """创建新的流水线"""
    data = request.json
    try:
        # 获取任务和阶段数据
        task_data = data.get('task')
        stage_data = data.get('stage')
        project_id = data.get('project_id')
        branch = data.get('branch', 'main')
        
        # 创建项目目录
        project_path = WORKSPACE_PATH / str(project_id)
        project_path.mkdir(exist_ok=True)
        
        # 过滤无效的阶段类型
        if stage_data:
            try:
                stages = json.loads(stage_data) if isinstance(stage_data, str) else stage_data
                # 过滤掉undefined和unknown值
                stages = [s for s in stages if s and s != 'undefined' and s != 'unknown']
                stage_data = json.dumps(stages)
            except Exception as e:
                print(f"处理阶段数据失败: {str(e)}")
            
        # 检查是否已存在相同的项目ID和分支组合
        existing_pipeline = db_manager.execute_query(
            "SELECT id FROM pipelines WHERE project_id = %s AND branch = %s",
            params=(project_id, branch),
            fetch_one=True
        )
        
        if existing_pipeline:
            # 如果已存在，更新现有记录
            pipeline = db_manager.execute_update(
                """UPDATE pipelines 
                   SET task = %s, stage = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE project_id = %s AND branch = %s""",
                params=(task_data, stage_data, data.get('updated_by', 'system'), project_id, branch),
                return_updated=True
            )
            pipeline_id = pipeline['id']
            operation = '更新'
        else:
            # 如果不存在，创建新记录
            pipeline = db_manager.execute_insert(
                """INSERT INTO pipelines (project_id, branch, task, stage, updated_by)
                   VALUES (%s, %s, %s, %s, %s)""",
                params=(project_id, branch, task_data, stage_data, data.get('updated_by', 'system')),
                return_id=True
            )
            pipeline_id = pipeline['id']
            operation = '创建'
        
        # 处理任务数据，保存到新的任务表和阶段表中
        if task_data:
            try:
                # 删除现有的任务和阶段数据（如果是更新操作）
                if existing_pipeline:
                    db_manager.execute_query(
                        "DELETE FROM pipeline_tasks WHERE pipeline_id = %s",
                        params=(pipeline_id,)
                    )
                
                # 尝试解析JSON字符串
                tasks = json.loads(task_data) if isinstance(task_data, str) else task_data
                
                # 处理每个任务
                for index, task in enumerate(tasks):
                    task_name = task.get('name')
                    task_type = task.get('type', 'maven')
                    
                    if task_name:
                        # 插入任务记录
                        task_record = db_manager.execute_insert(
                            """INSERT INTO pipeline_tasks (pipeline_id, name, type, order_index)
                               VALUES (%s, %s, %s, %s)""",
                            params=(pipeline_id, task_name, task_type, index),
                            return_id=True
                        )
                        
                        task_id = task_record['id']
                        
                        # 处理任务的阶段
                        stages = task.get('stages', [])
                        for stage_index, stage in enumerate(stages):
                            stage_type = stage.get('type')
                            stage_name = stage.get('name')
                            stage_config = stage.get('config', {})
                            
                            # 过滤无效的阶段类型
                            if stage_type and stage_type != 'undefined' and stage_type != 'unknown' and stage_name:
                                print(f"保存阶段配置 - 任务: {task_name}, 阶段: {stage_type}, 配置: {stage_config}")
                                db_manager.execute_insert(
                                    """INSERT INTO pipeline_task_stages (task_id, type, name, order_index, config)
                                       VALUES (%s, %s, %s, %s, %s)""",
                                    params=(task_id, stage_type, stage_name, stage_index, json.dumps(stage_config))
                                )
            except Exception as e:
                print(f"保存任务和阶段数据失败: {str(e)}")
        
        # 创建GitLab项目并上传文件
        try:
            # 获取或创建GitLab项目
            gitlab_project = gitlab_client.create_project(project_id)
            
            # 获取工作区中对应分支的路径
            branch_path = WORKSPACE_PATH / str(project_id) / branch
            
            # 确保分支目录存在
            branch_path.mkdir(parents=True, exist_ok=True)
            
            # 处理任务数据，为每个任务创建文件和目录
            if task_data:
                try:
                    # 尝试解析JSON字符串
                    tasks = json.loads(task_data) if isinstance(task_data, str) else task_data
                    
                    # 处理每个任务
                    for task in tasks:
                        task_name = task.get('name')
                        task_type = task.get('type', 'maven')
                        
                        if task_name:
                            # 创建任务目录
                            task_path = branch_path / task_name
                            task_path.mkdir(exist_ok=True)
                            
                            # 获取对应的模板文件
                            template_file = TEMPLATE_PATH / f'{task_type}-template.yml'
                            if template_file.exists():
                                # 创建并写入gitlab-ci.yml文件
                                gitlab_ci_file = task_path / 'gitlab-ci.yml'
                                shutil.copy2(str(template_file), str(gitlab_ci_file))
                except Exception as e:
                    print(f"处理任务数据失败: {str(e)}")
            
            # 将工作区中的分支文件夹上传到GitLab
            gitlab_client.upload_directory(
                project_id=project_id,
                local_path=str(branch_path),
                gitlab_path=branch,
                branch='main'
            )
            
            # 上传cicd.yml文件
            with open('cicd.yml', 'r', encoding='utf-8') as file:
                cicd_content = file.read()
            
            gitlab_client.upload_file(
                project_id=project_id,
                file_path='cicd.yml',
                content=cicd_content,
                branch='main',
                commit_message="添加cicd.yml文件"
            )
            
            return jsonify({
                'message': f'流水线{operation}成功，GitLab项目已同步',
                'pipeline': pipeline,
                'gitlab_project': gitlab_project
            })
        except Exception as e:
            # GitLab操作失败，但数据库操作已成功
            return jsonify({
                'message': f'流水线{operation}成功，但GitLab同步失败',
                'pipeline': pipeline,
                'error': str(e)
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pipelines_bp.route('/<int:pipeline_id>', methods=['PUT', 'POST'])
def update_pipeline(pipeline_id):
    """更新流水线信息"""
    data = request.json
    try:
        print(f"更新流水线 {pipeline_id} 的数据:", data)
        
        # 检查数据格式
        task_data = data.get('task')
        stage_data = data.get('stage')
        
        # 获取项目ID和分支
        project_id = data.get('project_id')
        branch = data.get('branch', 'main')
        
        # 创建项目目录
        project_path = WORKSPACE_PATH / str(project_id)
        project_path.mkdir(exist_ok=True)
        
        # 过滤无效的阶段类型
        if stage_data:
            try:
                stages = json.loads(stage_data) if isinstance(stage_data, str) else stage_data
                stages = [s for s in stages if s and s != 'undefined' and s != 'unknown']
                stage_data = json.dumps(stages)
            except Exception as e:
                print(f"处理阶段数据失败: {str(e)}")
        
        # 首先获取原有的流水线信息
        old_pipeline = db_manager.execute_query(
            "SELECT * FROM pipelines WHERE id = %s",
            params=(pipeline_id,),
            fetch_one=True
        )
        
        if not old_pipeline:
            return jsonify({'error': '流水线不存在'}), 404
        
        # 获取旧的任务数据，用于比较删除不再需要的任务文件夹
        old_tasks = []
        if old_pipeline['task']:
            try:
                old_tasks = json.loads(old_pipeline['task']) if isinstance(old_pipeline['task'], str) else old_pipeline['task']
                if not isinstance(old_tasks, list):
                    old_tasks = []
            except Exception as e:
                print(f"解析旧任务数据失败: {str(e)}")
        
        # 解析新的任务数据
        new_tasks = []
        if task_data:
            try:
                new_tasks = json.loads(task_data) if isinstance(task_data, str) else task_data
                if not isinstance(new_tasks, list):
                    new_tasks = []
            except Exception as e:
                print(f"解析新任务数据失败: {str(e)}")
        
        # 找出被删除的任务
        old_task_names = [task.get('name') for task in old_tasks if task.get('name')]
        new_task_names = [task.get('name') for task in new_tasks if task.get('name')]
        deleted_task_names = [name for name in old_task_names if name not in new_task_names]
        
        # 更新流水线信息
        updated_pipeline = db_manager.execute_update(
            """UPDATE pipelines 
               SET project_id = %s, branch = %s, task = %s, stage = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
               WHERE id = %s""",
            params=(project_id, branch, task_data, stage_data, data.get('updated_by', 'system'), pipeline_id),
            return_updated=True
        )
        
        # 更新任务和阶段表
        db_manager.execute_query(
            "DELETE FROM pipeline_tasks WHERE pipeline_id = %s",
            params=(pipeline_id,)
        )
        
        # 如果任务数据存在，保存到新的任务表和阶段表中
        if task_data:
            try:
                tasks = json.loads(task_data) if isinstance(task_data, str) else task_data
                
                for index, task in enumerate(tasks):
                    task_name = task.get('name')
                    task_type = task.get('type', 'maven')
                    
                    if task_name:
                        task_record = db_manager.execute_insert(
                            """INSERT INTO pipeline_tasks (pipeline_id, name, type, order_index)
                               VALUES (%s, %s, %s, %s)""",
                            params=(pipeline_id, task_name, task_type, index),
                            return_id=True
                        )
                        
                        task_id = task_record['id']
                        
                        stages = task.get('stages', [])
                        for stage_index, stage in enumerate(stages):
                            stage_type = stage.get('type')
                            stage_name = stage.get('name')
                            stage_config = stage.get('config', {})
                            
                            if stage_type and stage_type != 'undefined' and stage_type != 'unknown' and stage_name:
                                print(f"更新阶段配置 - 任务: {task_name}, 阶段: {stage_type}, 配置: {stage_config}")
                                db_manager.execute_insert(
                                    """INSERT INTO pipeline_task_stages (task_id, type, name, order_index, config)
                                       VALUES (%s, %s, %s, %s, %s)""",
                                    params=(task_id, stage_type, stage_name, stage_index, json.dumps(stage_config))
                                )
            except Exception as e:
                print(f"保存任务和阶段数据失败: {str(e)}")
        
        # 同步更新GitLab项目
        try:
            gitlab_project = gitlab_client.create_project(project_id)
            
            branch_path = WORKSPACE_PATH / str(project_id) / branch
            branch_path.mkdir(parents=True, exist_ok=True)
            
            # 删除不再需要的任务文件夹
            for deleted_task_name in deleted_task_names:
                task_path = branch_path / deleted_task_name
                if task_path.exists():
                    shutil.rmtree(str(task_path))
                    print(f"已删除不再需要的本地任务文件夹: {task_path}")
                
                try:
                    gitlab_task_path = f"{branch}/{deleted_task_name}"
                    gitlab_client.delete_directory(project_id, gitlab_task_path)
                    print(f"已删除GitLab仓库中的任务文件夹: {gitlab_task_path}")
                except Exception as e:
                    print(f"删除GitLab仓库中的任务文件夹失败: {str(e)}")
            
            # 处理任务数据，为每个任务创建文件和目录
            if task_data:
                try:
                    tasks = json.loads(task_data) if isinstance(task_data, str) else task_data
                    
                    for task in tasks:
                        task_name = task.get('name')
                        task_type = task.get('type', 'maven')
                        
                        if task_name:
                            task_path = branch_path / task_name
                            task_path.mkdir(exist_ok=True)
                            
                            template_file = TEMPLATE_PATH / f'{task_type}-template.yml'
                            if template_file.exists():
                                gitlab_ci_file = task_path / 'gitlab-ci.yml'
                                shutil.copy2(str(template_file), str(gitlab_ci_file))
                except Exception as e:
                    print(f"处理任务数据失败: {str(e)}")
            
            gitlab_client.upload_directory(
                project_id=project_id,
                local_path=str(branch_path),
                gitlab_path=branch,
                branch='main'
            )
            
            try:
                with open('cicd.yml', 'r', encoding='utf-8') as file:
                    cicd_content = file.read()
                
                gitlab_client.upload_file(
                    project_id=project_id,
                    file_path='cicd.yml',
                    content=cicd_content,
                    branch='main',
                    commit_message="更新cicd.yml文件"
                )
            except Exception as e:
                print(f"更新cicd.yml文件失败: {str(e)}")
            
            return jsonify({
                'message': '流水线更新成功，GitLab项目已同步',
                'pipeline': updated_pipeline
            })
        except Exception as e:
            return jsonify({
                'message': '流水线更新成功，但GitLab同步失败',
                'pipeline': updated_pipeline,
                'error': str(e)
            })
        
    except Exception as e:
        print(f"更新流水线失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@pipelines_bp.route('/<int:pipeline_id>', methods=['DELETE'])
def delete_pipeline(pipeline_id):
    """删除流水线，同时删除本地文件夹和GitLab仓库项目"""
    try:
        # 先获取流水线信息
        pipeline = db_manager.execute_query(
            "SELECT * FROM pipelines WHERE id = %s",
            params=(pipeline_id,),
            fetch_one=True
        )
        
        if pipeline is None:
            return jsonify({'error': '流水线不存在'}), 404
        
        project_id = pipeline['project_id']
        branch = pipeline['branch']
        
        # 从数据库中删除流水线
        deleted_pipeline = db_manager.execute_delete(
            "DELETE FROM pipelines WHERE id = %s",
            params=(pipeline_id,),
            return_deleted=True
        )
        
        # 删除本地文件夹
        try:
            project_path = WORKSPACE_PATH / str(project_id)
            if project_path.exists():
                other_pipelines_count = db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM pipelines WHERE project_id = %s AND id != %s",
                    params=(project_id, pipeline_id),
                    fetch_one=True
                )['count']
                
                if other_pipelines_count == 0:
                    shutil.rmtree(str(project_path), ignore_errors=True)
                    print(f"已删除项目文件夹: {project_path}")
                else:
                    branch_path = project_path / branch
                    if branch_path.exists():
                        shutil.rmtree(str(branch_path), ignore_errors=True)
                        print(f"已删除分支文件夹: {branch_path}")
        except Exception as e:
            print(f"删除本地文件夹失败: {str(e)}")
        
        # 删除GitLab仓库项目
        try:
            other_pipelines_count = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM pipelines WHERE project_id = %s AND id != %s",
                params=(project_id, pipeline_id),
                fetch_one=True
            )['count']
            
            if other_pipelines_count == 0:
                gitlab_client.delete_project(project_id)
                print(f"已删除GitLab项目: {project_id}")
            else:
                gitlab_client.delete_directory(project_id, branch)
                print(f"已删除GitLab项目中的分支目录: {branch}")
        except Exception as e:
            print(f"删除GitLab项目失败: {str(e)}")
            
        return jsonify({
            'message': '流水线删除成功，相关文件和GitLab项目已同步删除',
            'pipeline': deleted_pipeline
        })
    except Exception as e:
        print(f"删除流水线失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@pipelines_bp.route('/<int:pipeline_id>/tasks', methods=['GET'])
def get_pipeline_tasks(pipeline_id):
    """获取流水线的任务和阶段数据"""
    try:
        pipeline_data = db_manager.execute_query(
            "SELECT task, stage FROM pipelines WHERE id = %s",
            params=(pipeline_id,),
            fetch_one=True
        )
        
        if not pipeline_data:
            return jsonify({'tasks': [], 'use_new_structure': False, 'error': '流水线不存在'})
        
        result = []
        
        # 解析task字段
        if pipeline_data['task']:
            try:
                tasks_data = json.loads(pipeline_data['task'])
                if isinstance(tasks_data, list):
                    for task in tasks_data:
                        if isinstance(task, dict) and 'name' in task:
                            task_obj = {
                                'id': task.get('id', f"task_{int(time.time())}_legacy"),
                                'name': task.get('name', '未命名任务'),
                                'type': task.get('type', 'maven'),
                                'stages': []
                            }
                            
                            if 'stages' in task and isinstance(task['stages'], list):
                                for stage in task['stages']:
                                    if isinstance(stage, dict):
                                        stage_obj = {
                                            'id': stage.get('id', f"stage_{int(time.time())}_legacy"),
                                            'type': stage.get('type', 'unknown'),
                                            'name': stage.get('name', stage.get('type', '未知阶段')),
                                            'config': stage.get('config', {})
                                        }
                                        task_obj['stages'].append(stage_obj)
                            
                            result.append(task_obj)
                else:
                    task_names = [tasks_data] if isinstance(tasks_data, str) else []
                    for i, task_name in enumerate(task_names):
                        task_obj = {
                            'id': f"task_legacy_{i}",
                            'name': task_name,
                            'type': 'maven',
                            'stages': []
                        }
                        result.append(task_obj)
            except (json.JSONDecodeError, TypeError):
                task_names = pipeline_data['task'].split(',') if pipeline_data['task'] else []
                for i, task_name in enumerate(task_names):
                    task_obj = {
                        'id': f"task_legacy_{i}",
                        'name': task_name.strip(),
                        'type': 'maven',
                        'stages': []
                    }
                    result.append(task_obj)
        
        if result and any(task.get('stages') for task in result):
            return jsonify({
                'tasks': result,
                'use_new_structure': True
            })
        
        # 如果没有阶段数据，尝试从stage字段解析
        if pipeline_data['stage'] and result:
            try:
                stages_data = json.loads(pipeline_data['stage'])
                if isinstance(stages_data, list):
                    all_stages = []
                    for stage_item in stages_data:
                        if isinstance(stage_item, list):
                            all_stages.extend(stage_item)
                        else:
                            all_stages.append(stage_item)
                    
                    if len(result) == 1:
                        for i, stage_type in enumerate(all_stages):
                            stage_obj = {
                                'id': f"stage_legacy_{i}",
                                'type': stage_type,
                                'name': stage_type,
                                'config': {}
                            }
                            result[0]['stages'].append(stage_obj)
                    else:
                        for i, stage_type in enumerate(all_stages):
                            task_index = i % len(result)
                            stage_obj = {
                                'id': f"stage_legacy_{i}",
                                'type': stage_type,
                                'name': stage_type,
                                'config': {}
                            }
                            result[task_index]['stages'].append(stage_obj)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return jsonify({
            'tasks': result,
            'use_new_structure': len(result) > 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pipelines_bp.route('/task', methods=['POST'])
def create_task():
    """创建或更新任务"""
    try:
        data = request.json
        project_id = data.get('projectId')
        task_name = data.get('taskName')
        task_type = data.get('taskType')
        branch_name = data.get('branchName', 'develop')
        
        if not all([project_id, task_name, task_type]):
            return jsonify({'error': '缺少必要参数: projectId, taskName, taskType'}), 400
        
        # 创建本地文件夹
        try:
            task_path = WORKSPACE_PATH / str(project_id) / branch_name / task_name
            task_path.mkdir(parents=True, exist_ok=True)
            
            # 复制对应的模板文件
            template_file = f"{task_type}-template.yml"
            template_source = TEMPLATE_PATH / template_file
            target_file = task_path / "gitlab-ci.yml"
            
            if template_source.exists():
                shutil.copy2(str(template_source), str(target_file))
                print(f"已复制模板文件 {template_file} 到 {target_file}")
            else:
                # 创建基本的gitlab-ci.yml文件
                basic_content = f"""# {task_type.upper()} 任务配置
variables:
  compile: "on"
  build: "off"
  deploy: "off"

stages:
  - compile
  - build
  - deploy

compile:
  stage: compile
  script:
    - echo "编译阶段"
  only:
    variables:
      - $compile == "on"

build:
  stage: build
  script:
    - echo "构建阶段"
  only:
    variables:
      - $build == "on"

deploy:
  stage: deploy
  script:
    - echo "部署阶段"
  only:
    variables:
      - $deploy == "on"
"""
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(basic_content)
                print(f"已创建基本的gitlab-ci.yml文件: {target_file}")
            
        except Exception as e:
            print(f"创建本地文件夹失败: {str(e)}")
            return jsonify({'error': f'创建本地文件夹失败: {str(e)}'}), 500
        
        # 同步到GitLab
        try:
            # 确保GitLab项目存在
            gitlab_client.create_project(project_id)
            
            # 上传任务文件夹到GitLab
            gitlab_client.upload_directory(
                project_id=project_id,
                local_path=str(task_path),
                gitlab_path=f"{branch_name}/{task_name}",
                branch="main"
            )
            print(f"已将任务文件夹上传到GitLab: {project_id}/{branch_name}/{task_name}")
            
        except Exception as e:
            print(f"GitLab同步失败: {str(e)}")
            # 本地文件夹已创建，GitLab同步失败不影响返回结果
        
        return jsonify({
            'message': '任务创建成功',
            'task': {
                'name': task_name,
                'type': task_type,
                'path': str(task_path),
                'operation': '创建'
            }
        })
        
    except Exception as e:
        print(f"创建任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@pipelines_bp.route('/task/delete', methods=['POST'])
def delete_task():
    """删除任务文件夹"""
    try:
        data = request.json
        project_id = data.get('projectId')
        branch_name = data.get('branchName', 'develop')
        task_name = data.get('taskName')
        
        if not all([project_id, task_name]):
            return jsonify({'error': '缺少必要参数: projectId, taskName'}), 400
        
        # 删除本地文件夹
        try:
            task_path = WORKSPACE_PATH / str(project_id) / branch_name / task_name
            if task_path.exists():
                shutil.rmtree(str(task_path), ignore_errors=True)
                print(f"已删除本地任务文件夹: {task_path}")
            else:
                print(f"本地任务文件夹不存在: {task_path}")
        except Exception as e:
            print(f"删除本地文件夹失败: {str(e)}")
        
        # 从GitLab删除
        try:
            gitlab_client.delete_directory(
                project_id=project_id,
                directory_path=f"{branch_name}/{task_name}"
            )
            print(f"已从GitLab删除任务文件夹: {project_id}/{branch_name}/{task_name}")
        except Exception as e:
            print(f"从GitLab删除失败: {str(e)}")
        
        return jsonify({
            'message': '任务删除成功',
            'task': {
                'name': task_name,
                'project_id': project_id,
                'branch': branch_name
            }
        })
        
    except Exception as e:
        print(f"删除任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500 