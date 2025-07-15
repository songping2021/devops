#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from pathlib import Path

from .gitlab_client import GitLabClient, gitlab_client
from .database import db_manager
from .yaml_config_parser import YamlConfigParser


class SyncStatus(Enum):
    """同步状态枚举"""
    PENDING = "pending"      # 等待同步
    IN_PROGRESS = "in_progress"  # 同步中
    SUCCESS = "success"      # 同步成功
    FAILED = "failed"        # 同步失败
    CONFLICT = "conflict"    # 存在冲突
    RETRY = "retry"          # 重试中


@dataclass
class SyncOperation:
    """同步操作定义"""
    operation_id: str
    project_id: str
    branch: str
    task_name: str
    file_path: str
    content: str
    content_hash: str
    timestamp: datetime
    status: SyncStatus
    retry_count: int = 0
    error_message: Optional[str] = None
    conflict_details: Optional[Dict] = None


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    operation_id: str
    status: SyncStatus
    message: str
    details: Optional[Dict] = None


class GitLabSyncManager:
    """GitLab同步管理器 - TASK007实现"""
    
    def __init__(self):
        self.gitlab_client = gitlab_client
        self.yaml_parser = YamlConfigParser()
        self.sync_operations: Dict[str, SyncOperation] = {}
        self.sync_lock = threading.RLock()
        self.max_retry_count = 3
        self.retry_delay_base = 2  # 基础重试延迟（秒）
        self.batch_size = 5  # 批量操作并发数
        
    def generate_operation_id(self, project_id: str, branch: str, task_name: str) -> str:
        """生成同步操作ID"""
        unique_str = f"{project_id}_{branch}_{task_name}_{int(time.time())}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]
        
    def calculate_content_hash(self, content: str) -> str:
        """计算内容哈希值"""
        return hashlib.sha256(content.encode()).hexdigest()
        
    def create_sync_operation(self, project_id: str, branch: str, task_name: str, 
                            file_path: str, content: str) -> SyncOperation:
        """创建同步操作"""
        operation_id = self.generate_operation_id(project_id, branch, task_name)
        content_hash = self.calculate_content_hash(content)
        
        operation = SyncOperation(
            operation_id=operation_id,
            project_id=project_id,
            branch=branch,
            task_name=task_name,
            file_path=file_path,
            content=content,
            content_hash=content_hash,
            timestamp=datetime.now(),
            status=SyncStatus.PENDING
        )
        
        with self.sync_lock:
            self.sync_operations[operation_id] = operation
            
        return operation
        
    def get_remote_file_info(self, project_id: str, file_path: str, branch: str = "main") -> Optional[Dict]:
        """获取远程文件信息"""
        try:
            url = f"{self.gitlab_client.api_url}/projects/{self.gitlab_client.namespace}%2F{project_id}/repository/files/{requests.utils.quote(file_path, safe='')}"
            params = {"ref": branch}
            
            response = requests.get(url, headers=self.gitlab_client.headers, params=params, verify=False)
            
            if response.status_code == 200:
                file_info = response.json()
                # 解码内容并计算哈希
                import base64
                content = base64.b64decode(file_info.get('content', '')).decode('utf-8')
                content_hash = self.calculate_content_hash(content)
                
                return {
                    'content': content,
                    'content_hash': content_hash,
                    'last_commit_id': file_info.get('last_commit_id'),
                    'file_name': file_info.get('file_name'),
                    'file_path': file_info.get('file_path'),
                    'size': file_info.get('size'),
                    'encoding': file_info.get('encoding')
                }
            elif response.status_code == 404:
                return None  # 文件不存在
            else:
                raise Exception(f"获取远程文件信息失败: {response.text}")
                
        except Exception as e:
            print(f"获取远程文件信息时发生错误: {str(e)}")
            return None
            
    def detect_conflict(self, operation: SyncOperation) -> Tuple[bool, Optional[Dict]]:
        """检测配置冲突"""
        try:
            remote_info = self.get_remote_file_info(operation.project_id, operation.file_path, operation.branch)
            
            if not remote_info:
                # 远程文件不存在，无冲突
                return False, None
                
            local_hash = operation.content_hash
            remote_hash = remote_info['content_hash']
            
            if local_hash == remote_hash:
                # 内容相同，无冲突
                return False, None
                
            # 检测是否为YAML配置冲突
            try:
                import yaml
                local_config = yaml.safe_load(operation.content) or {}
                remote_config = yaml.safe_load(remote_info['content']) or {}
                
                # 比较variables部分
                local_vars = local_config.get('variables', {})
                remote_vars = remote_config.get('variables', {})
                
                conflicted_vars = {}
                for key in set(local_vars.keys()) | set(remote_vars.keys()):
                    local_val = local_vars.get(key)
                    remote_val = remote_vars.get(key)
                    if local_val != remote_val:
                        conflicted_vars[key] = {
                            'local': local_val,
                            'remote': remote_val
                        }
                
                if conflicted_vars:
                    conflict_details = {
                        'type': 'variable_conflict',
                        'conflicted_variables': conflicted_vars,
                        'local_hash': local_hash,
                        'remote_hash': remote_hash,
                        'remote_commit': remote_info.get('last_commit_id')
                    }
                    return True, conflict_details
                    
            except Exception as e:
                # YAML解析失败，视为内容冲突
                conflict_details = {
                    'type': 'content_conflict',
                    'local_hash': local_hash,
                    'remote_hash': remote_hash,
                    'remote_commit': remote_info.get('last_commit_id'),
                    'parse_error': str(e)
                }
                return True, conflict_details
                
            return False, None
            
        except Exception as e:
            print(f"冲突检测失败: {str(e)}")
            # 检测失败时，为了安全起见，假设存在冲突
            return True, {
                'type': 'detection_error',
                'error': str(e)
            }
            
    def resolve_conflict(self, operation: SyncOperation, resolution_strategy: str = "local_wins") -> SyncOperation:
        """解决配置冲突"""
        conflict_details = operation.conflict_details
        
        if not conflict_details:
            return operation
            
        if resolution_strategy == "local_wins":
            # 本地配置优先，直接覆盖远程
            operation.status = SyncStatus.PENDING
            operation.conflict_details = None
            
        elif resolution_strategy == "remote_wins":
            # 远程配置优先，获取远程内容
            remote_info = self.get_remote_file_info(operation.project_id, operation.file_path, operation.branch)
            if remote_info:
                operation.content = remote_info['content']
                operation.content_hash = remote_info['content_hash']
                operation.status = SyncStatus.SUCCESS  # 不需要同步
                operation.conflict_details = None
                
        elif resolution_strategy == "merge":
            # 尝试合并配置
            try:
                remote_info = self.get_remote_file_info(operation.project_id, operation.file_path, operation.branch)
                if remote_info and conflict_details.get('type') == 'variable_conflict':
                    import yaml
                    local_config = yaml.safe_load(operation.content) or {}
                    remote_config = yaml.safe_load(remote_info['content']) or {}
                    
                    # 合并variables，本地配置优先
                    merged_vars = remote_config.get('variables', {}).copy()
                    merged_vars.update(local_config.get('variables', {}))
                    
                    # 更新本地配置
                    local_config['variables'] = merged_vars
                    merged_content = yaml.dump(local_config, default_flow_style=False, allow_unicode=True)
                    
                    operation.content = merged_content
                    operation.content_hash = self.calculate_content_hash(merged_content)
                    operation.status = SyncStatus.PENDING
                    operation.conflict_details = None
                else:
                    # 无法合并，回退到本地优先
                    operation.status = SyncStatus.PENDING
                    operation.conflict_details = None
                    
            except Exception as e:
                print(f"合并配置失败: {str(e)}")
                # 合并失败，回退到本地优先
                operation.status = SyncStatus.PENDING
                operation.conflict_details = None
                
        return operation
        
    def atomic_sync_operation(self, operation: SyncOperation) -> SyncResult:
        """原子性同步操作"""
        operation_id = operation.operation_id
        
        try:
            # 更新操作状态为进行中
            with self.sync_lock:
                operation.status = SyncStatus.IN_PROGRESS
                
            # 冲突检测
            has_conflict, conflict_details = self.detect_conflict(operation)
            
            if has_conflict:
                with self.sync_lock:
                    operation.status = SyncStatus.CONFLICT
                    operation.conflict_details = conflict_details
                    
                return SyncResult(
                    success=False,
                    operation_id=operation_id,
                    status=SyncStatus.CONFLICT,
                    message="检测到配置冲突，需要手动解决",
                    details=conflict_details
                )
                
            # 执行GitLab文件上传
            commit_message = f"更新配置: {operation.task_name} ({operation.operation_id})"
            result = self.gitlab_client.upload_file(
                project_id=operation.project_id,
                file_path=operation.file_path,
                content=operation.content,
                branch=operation.branch,
                commit_message=commit_message
            )
            
            # 验证上传结果
            if result:
                # 再次验证远程文件内容
                remote_info = self.get_remote_file_info(operation.project_id, operation.file_path, operation.branch)
                if remote_info and remote_info['content_hash'] == operation.content_hash:
                    with self.sync_lock:
                        operation.status = SyncStatus.SUCCESS
                        
                    # 记录同步成功到数据库
                    self.record_sync_success(operation)
                    
                    return SyncResult(
                        success=True,
                        operation_id=operation_id,
                        status=SyncStatus.SUCCESS,
                        message="同步成功",
                        details={'commit_id': result.get('id')}
                    )
                else:
                    raise Exception("上传后验证失败，远程内容与本地不匹配")
            else:
                raise Exception("GitLab文件上传失败")
                
        except Exception as e:
            error_message = f"同步操作失败: {str(e)}"
            with self.sync_lock:
                operation.status = SyncStatus.FAILED
                operation.error_message = error_message
                
            return SyncResult(
                success=False,
                operation_id=operation_id,
                status=SyncStatus.FAILED,
                message=error_message
            )
            
    def retry_failed_operation(self, operation: SyncOperation) -> SyncResult:
        """重试失败的同步操作"""
        if operation.retry_count >= self.max_retry_count:
            return SyncResult(
                success=False,
                operation_id=operation.operation_id,
                status=SyncStatus.FAILED,
                message=f"重试次数已达上限 ({self.max_retry_count})"
            )
            
        # 指数退避延迟
        delay = self.retry_delay_base ** operation.retry_count
        time.sleep(delay)
        
        with self.sync_lock:
            operation.retry_count += 1
            operation.status = SyncStatus.RETRY
            operation.timestamp = datetime.now()
            
        return self.atomic_sync_operation(operation)
        
    def batch_sync_operations(self, operations: List[SyncOperation]) -> List[SyncResult]:
        """批量同步操作"""
        results = []
        
        # 使用线程池并发执行同步操作
        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            # 提交所有同步任务
            future_to_operation = {}
            for operation in operations:
                future = executor.submit(self.atomic_sync_operation, operation)
                future_to_operation[future] = operation
                
            # 收集结果
            for future in as_completed(future_to_operation):
                operation = future_to_operation[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # 如果失败且可以重试，则加入重试队列
                    if not result.success and result.status == SyncStatus.FAILED:
                        if operation.retry_count < self.max_retry_count:
                            print(f"操作 {operation.operation_id} 失败，将进行重试")
                            
                except Exception as e:
                    error_result = SyncResult(
                        success=False,
                        operation_id=operation.operation_id,
                        status=SyncStatus.FAILED,
                        message=f"批量同步异常: {str(e)}"
                    )
                    results.append(error_result)
                    
        # 处理重试
        retry_operations = [op for op in operations if op.status == SyncStatus.FAILED and op.retry_count < self.max_retry_count]
        
        if retry_operations:
            print(f"开始重试 {len(retry_operations)} 个失败的操作")
            for operation in retry_operations:
                retry_result = self.retry_failed_operation(operation)
                # 更新对应的结果
                for i, result in enumerate(results):
                    if result.operation_id == operation.operation_id:
                        results[i] = retry_result
                        break
                        
        return results
        
    def record_sync_success(self, operation: SyncOperation):
        """记录同步成功到数据库"""
        try:
            # 插入同步历史记录
            db_manager.execute_insert("""
                INSERT INTO gitlab_sync_history 
                (operation_id, project_id, branch, task_name, file_path, content_hash, 
                 sync_status, sync_timestamp, retry_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (operation_id) DO UPDATE SET
                    sync_status = EXCLUDED.sync_status,
                    sync_timestamp = EXCLUDED.sync_timestamp,
                    retry_count = EXCLUDED.retry_count
            """, params=(
                operation.operation_id,
                operation.project_id, 
                operation.branch,
                operation.task_name,
                operation.file_path,
                operation.content_hash,
                operation.status.value,
                operation.timestamp,
                operation.retry_count
            ))
            
        except Exception as e:
            print(f"记录同步历史失败: {str(e)}")
            
    def get_sync_status(self, operation_id: str) -> Optional[SyncResult]:
        """获取同步状态"""
        with self.sync_lock:
            operation = self.sync_operations.get(operation_id)
            
        if not operation:
            return None
            
        return SyncResult(
            success=operation.status == SyncStatus.SUCCESS,
            operation_id=operation_id,
            status=operation.status,
            message=operation.error_message or f"状态: {operation.status.value}",
            details={
                'retry_count': operation.retry_count,
                'timestamp': operation.timestamp.isoformat(),
                'conflict_details': operation.conflict_details
            }
        )
        
    def sync_task_config(self, project_id: str, branch: str, task_name: str, 
                        config_updates: Dict[str, Any], 
                        resolution_strategy: str = "local_wins") -> SyncResult:
        """同步任务配置（主要入口方法）"""
        try:
            # 构建文件路径
            file_path = f"{branch}/{task_name}/gitlab-ci.yml"
            
            # 读取当前配置并应用更新
            workspace_path = Path("workspace") / project_id / branch / task_name
            yaml_file_path = workspace_path / "gitlab-ci.yml"
            
            if yaml_file_path.exists():
                current_config = self.yaml_parser.load_yaml_file(str(yaml_file_path))
            else:
                # 如果本地文件不存在，尝试从远程获取
                remote_info = self.get_remote_file_info(project_id, file_path, branch)
                if remote_info:
                    import yaml
                    current_config = yaml.safe_load(remote_info['content']) or {}
                else:
                    # 远程也不存在，使用默认配置
                    current_config = {'variables': {}}
                    
            # 应用配置更新
            updated_config = current_config.copy()
            if 'variables' not in updated_config:
                updated_config['variables'] = {}
                
            updated_config['variables'].update(config_updates)
            
            # 生成YAML内容
            import yaml
            yaml_content = yaml.dump(updated_config, default_flow_style=False, allow_unicode=True)
            
            # 创建同步操作
            operation = self.create_sync_operation(
                project_id=project_id,
                branch=branch,
                task_name=task_name,
                file_path=file_path,
                content=yaml_content
            )
            
            # 执行同步
            result = self.atomic_sync_operation(operation)
            
            # 如果遇到冲突，尝试解决
            if result.status == SyncStatus.CONFLICT:
                operation = self.resolve_conflict(operation, resolution_strategy)
                if operation.status == SyncStatus.PENDING:
                    result = self.atomic_sync_operation(operation)
                    
            return result
            
        except Exception as e:
            return SyncResult(
                success=False,
                operation_id="",
                status=SyncStatus.FAILED,
                message=f"同步任务配置失败: {str(e)}"
            )
            
    def batch_sync_task_configs(self, sync_requests: List[Dict]) -> List[SyncResult]:
        """批量同步任务配置"""
        operations = []
        
        for request in sync_requests:
            try:
                project_id = request['project_id']
                branch = request.get('branch', 'main')
                task_name = request['task_name']
                config_updates = request['config_updates']
                
                # 为每个请求创建同步操作
                file_path = f"{branch}/{task_name}/gitlab-ci.yml"
                
                # 读取并更新配置
                workspace_path = Path("workspace") / project_id / branch / task_name
                yaml_file_path = workspace_path / "gitlab-ci.yml"
                
                if yaml_file_path.exists():
                    current_config = self.yaml_parser.load_yaml_file(str(yaml_file_path))
                else:
                    current_config = {'variables': {}}
                    
                updated_config = current_config.copy()
                if 'variables' not in updated_config:
                    updated_config['variables'] = {}
                    
                updated_config['variables'].update(config_updates)
                import yaml
                yaml_content = yaml.dump(updated_config, default_flow_style=False, allow_unicode=True)
                
                operation = self.create_sync_operation(
                    project_id=project_id,
                    branch=branch,
                    task_name=task_name,
                    file_path=file_path,
                    content=yaml_content
                )
                
                operations.append(operation)
                
            except Exception as e:
                # 创建失败的操作记录
                error_operation = SyncOperation(
                    operation_id=f"error_{int(time.time())}",
                    project_id=request.get('project_id', ''),
                    branch=request.get('branch', 'main'),
                    task_name=request.get('task_name', ''),
                    file_path='',
                    content='',
                    content_hash='',
                    timestamp=datetime.now(),
                    status=SyncStatus.FAILED,
                    error_message=f"创建同步操作失败: {str(e)}"
                )
                operations.append(error_operation)
                
        # 执行批量同步
        return self.batch_sync_operations(operations)
        
    def cleanup_old_operations(self, days: int = 7):
        """清理旧的同步操作记录"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with self.sync_lock:
            old_operations = [
                op_id for op_id, operation in self.sync_operations.items()
                if operation.timestamp < cutoff_time
            ]
            
            for op_id in old_operations:
                del self.sync_operations[op_id]
                
        print(f"已清理 {len(old_operations)} 个旧的同步操作记录")


# 全局GitLab同步管理器实例
gitlab_sync_manager = GitLabSyncManager()