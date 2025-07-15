#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify
from typing import Dict, List, Any
import json

from backend.utils.gitlab_sync_manager import gitlab_sync_manager, SyncStatus
from backend.utils.database import db_manager

# 创建GitLab同步API蓝图
gitlab_sync_bp = Blueprint('gitlab_sync', __name__)


@gitlab_sync_bp.route('/api/gitlab_sync/task_config', methods=['POST'])
def sync_task_config():
    """
    同步单个任务配置到GitLab
    
    请求体:
    {
        "project_id": "666",
        "branch": "develop", 
        "task_name": "123",
        "config_updates": {
            "JDKVERSION": "11",
            "CTPORT": "8080"
        },
        "resolution_strategy": "local_wins"  // 可选: local_wins, remote_wins, merge
    }
    """
    try:
        data = request.get_json()
        
        # 验证必填参数
        required_fields = ['project_id', 'task_name', 'config_updates']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'缺少必填参数: {field}'
                }), 400
        
        project_id = data['project_id']
        branch = data.get('branch', 'main')
        task_name = data['task_name']
        config_updates = data['config_updates']
        resolution_strategy = data.get('resolution_strategy', 'local_wins')
        
        # 执行同步
        result = gitlab_sync_manager.sync_task_config(
            project_id=project_id,
            branch=branch,
            task_name=task_name,
            config_updates=config_updates,
            resolution_strategy=resolution_strategy
        )
        
        return jsonify({
            'success': result.success,
            'operation_id': result.operation_id,
            'status': result.status.value,
            'message': result.message,
            'details': result.details
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'同步任务配置失败: {str(e)}'
        }), 500


@gitlab_sync_bp.route('/api/gitlab_sync/batch_sync', methods=['POST'])
def batch_sync_task_configs():
    """
    批量同步任务配置到GitLab
    
    请求体:
    {
        "sync_requests": [
            {
                "project_id": "666",
                "branch": "develop",
                "task_name": "123", 
                "config_updates": {"JDKVERSION": "11"}
            },
            {
                "project_id": "777",
                "branch": "develop",
                "task_name": "234",
                "config_updates": {"NODEVERSION": "16.18"}
            }
        ]
    }
    """
    try:
        data = request.get_json()
        sync_requests = data.get('sync_requests', [])
        
        if not sync_requests:
            return jsonify({
                'success': False,
                'message': '同步请求列表不能为空'
            }), 400
        
        # 执行批量同步
        results = gitlab_sync_manager.batch_sync_task_configs(sync_requests)
        
        # 统计结果
        total_count = len(results)
        success_count = sum(1 for r in results if r.success)
        failed_count = total_count - success_count
        
        return jsonify({
            'success': failed_count == 0,
            'message': f'批量同步完成，成功: {success_count}, 失败: {failed_count}',
            'summary': {
                'total': total_count,
                'success': success_count,
                'failed': failed_count
            },
            'results': [
                {
                    'operation_id': result.operation_id,
                    'status': result.status.value,
                    'success': result.success,
                    'message': result.message,
                    'details': result.details
                } for result in results
            ]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'批量同步失败: {str(e)}'
        }), 500


@gitlab_sync_bp.route('/api/gitlab_sync/status/<operation_id>', methods=['GET'])
def get_sync_status(operation_id):
    """
    获取同步操作状态
    
    路径参数:
        operation_id: 同步操作ID
    """
    try:
        result = gitlab_sync_manager.get_sync_status(operation_id)
        
        if not result:
            return jsonify({
                'success': False,
                'message': '同步操作不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'operation_id': result.operation_id,
            'status': result.status.value,
            'message': result.message,
            'details': result.details
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取同步状态失败: {str(e)}'
        }), 500


@gitlab_sync_bp.route('/api/gitlab_sync/resolve_conflict', methods=['POST'])
def resolve_sync_conflict():
    """
    解决同步冲突
    
    请求体:
    {
        "operation_id": "abc123def456",
        "resolution_strategy": "local_wins"  // local_wins, remote_wins, merge
    }
    """
    try:
        data = request.get_json()
        operation_id = data.get('operation_id')
        resolution_strategy = data.get('resolution_strategy', 'local_wins')
        
        if not operation_id:
            return jsonify({
                'success': False,
                'message': '缺少操作ID'
            }), 400
        
        # 获取同步操作
        with gitlab_sync_manager.sync_lock:
            operation = gitlab_sync_manager.sync_operations.get(operation_id)
        
        if not operation:
            return jsonify({
                'success': False,
                'message': '同步操作不存在'
            }), 404
        
        if operation.status != SyncStatus.CONFLICT:
            return jsonify({
                'success': False,
                'message': f'操作状态为 {operation.status.value}，不是冲突状态'
            }), 400
        
        # 解决冲突
        resolved_operation = gitlab_sync_manager.resolve_conflict(operation, resolution_strategy)
        
        # 如果解决后需要重新同步，则执行同步
        if resolved_operation.status == SyncStatus.PENDING:
            result = gitlab_sync_manager.atomic_sync_operation(resolved_operation)
        else:
            # 冲突已解决，无需同步
            result = gitlab_sync_manager.get_sync_status(operation_id)
        
        return jsonify({
            'success': result.success,
            'operation_id': result.operation_id,
            'status': result.status.value,
            'message': result.message,
            'details': result.details
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'解决冲突失败: {str(e)}'
        }), 500


@gitlab_sync_bp.route('/api/gitlab_sync/history', methods=['GET'])
def get_sync_history():
    """
    获取同步历史记录
    
    查询参数:
        project_id: 项目ID（可选）
        task_name: 任务名称（可选）
        status: 同步状态（可选）
        limit: 限制返回数量（默认50）
        offset: 偏移量（默认0）
    """
    try:
        # 获取查询参数
        project_id = request.args.get('project_id')
        task_name = request.args.get('task_name')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if project_id:
            where_conditions.append("project_id = %s")
            params.append(project_id)
        
        if task_name:
            where_conditions.append("task_name = %s")
            params.append(task_name)
        
        if status:
            where_conditions.append("sync_status = %s")
            params.append(status)
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # 查询总数
        count_query = f"SELECT COUNT(*) as total FROM gitlab_sync_history{where_clause}"
        total_result = db_manager.execute_query(count_query, params=params, fetch_one=True)
        total_count = total_result['total'] if total_result else 0
        
        # 查询数据
        query = f"""
            SELECT operation_id, project_id, branch, task_name, file_path, 
                   content_hash, sync_status, sync_timestamp, retry_count,
                   error_message, conflict_details, created_at, updated_at
            FROM gitlab_sync_history
            {where_clause}
            ORDER BY sync_timestamp DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        history_records = db_manager.execute_query(query, params=params, fetch_all=True)
        
        return jsonify({
            'success': True,
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'records': [
                {
                    'operation_id': record['operation_id'],
                    'project_id': record['project_id'],
                    'branch': record['branch'],
                    'task_name': record['task_name'],
                    'file_path': record['file_path'],
                    'content_hash': record['content_hash'],
                    'sync_status': record['sync_status'],
                    'sync_timestamp': record['sync_timestamp'].isoformat(),
                    'retry_count': record['retry_count'],
                    'error_message': record['error_message'],
                    'conflict_details': record['conflict_details'],
                    'created_at': record['created_at'].isoformat(),
                    'updated_at': record['updated_at'].isoformat()
                } for record in history_records
            ]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取同步历史失败: {str(e)}'
        }), 500


@gitlab_sync_bp.route('/api/gitlab_sync/remote_file_info', methods=['GET'])
def get_remote_file_info():
    """
    获取GitLab远程文件信息
    
    查询参数:
        project_id: 项目ID
        file_path: 文件路径
        branch: 分支名（默认main）
    """
    try:
        project_id = request.args.get('project_id')
        file_path = request.args.get('file_path')
        branch = request.args.get('branch', 'main')
        
        if not project_id or not file_path:
            return jsonify({
                'success': False,
                'message': '缺少必填参数: project_id 和 file_path'
            }), 400
        
        # 获取远程文件信息
        remote_info = gitlab_sync_manager.get_remote_file_info(project_id, file_path, branch)
        
        if not remote_info:
            return jsonify({
                'success': False,
                'message': '远程文件不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'remote_file': {
                'content_hash': remote_info['content_hash'],
                'last_commit_id': remote_info['last_commit_id'],
                'file_name': remote_info['file_name'],
                'file_path': remote_info['file_path'],
                'size': remote_info['size'],
                'encoding': remote_info['encoding']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取远程文件信息失败: {str(e)}'
        }), 500


@gitlab_sync_bp.route('/api/gitlab_sync/cleanup', methods=['POST'])
def cleanup_old_operations():
    """
    清理旧的同步操作记录
    
    请求体:
    {
        "days": 7  // 清理多少天前的记录，默认7天
    }
    """
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)
        
        # 执行清理
        gitlab_sync_manager.cleanup_old_operations(days)
        
        return jsonify({
            'success': True,
            'message': f'已清理 {days} 天前的同步操作记录'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清理操作失败: {str(e)}'
        }), 500


@gitlab_sync_bp.route('/api/gitlab_sync/stats', methods=['GET'])
def get_sync_stats():
    """
    获取同步统计信息
    """
    try:
        # 统计各状态的同步操作数量
        status_stats = db_manager.execute_query("""
            SELECT sync_status, COUNT(*) as count
            FROM gitlab_sync_history
            WHERE sync_timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY sync_status
            ORDER BY count DESC
        """, fetch_all=True)
        
        # 统计最近同步的项目
        recent_projects = db_manager.execute_query("""
            SELECT project_id, task_name, COUNT(*) as sync_count,
                   MAX(sync_timestamp) as last_sync
            FROM gitlab_sync_history
            WHERE sync_timestamp >= NOW() - INTERVAL '7 days'
            GROUP BY project_id, task_name
            ORDER BY last_sync DESC
            LIMIT 10
        """, fetch_all=True)
        
        # 统计失败率
        overall_stats = db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_operations,
                SUM(CASE WHEN sync_status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN sync_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN sync_status = 'conflict' THEN 1 ELSE 0 END) as conflict_count
            FROM gitlab_sync_history
            WHERE sync_timestamp >= NOW() - INTERVAL '30 days'
        """, fetch_one=True)
        
        # 计算成功率
        total = overall_stats['total_operations'] or 0
        success_rate = (overall_stats['success_count'] / total * 100) if total > 0 else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'status_distribution': [
                    {
                        'status': record['sync_status'],
                        'count': record['count']
                    } for record in status_stats
                ],
                'recent_projects': [
                    {
                        'project_id': record['project_id'],
                        'task_name': record['task_name'],
                        'sync_count': record['sync_count'],
                        'last_sync': record['last_sync'].isoformat()
                    } for record in recent_projects
                ],
                'overall': {
                    'total_operations': total,
                    'success_count': overall_stats['success_count'],
                    'failed_count': overall_stats['failed_count'],
                    'conflict_count': overall_stats['conflict_count'],
                    'success_rate': round(success_rate, 2)
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计信息失败: {str(e)}'
        }), 500