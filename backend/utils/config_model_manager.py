#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.utils.database import db_manager

class ConfigModelManager:
    """配置数据模型管理器"""
    
    def __init__(self):
        pass
    
    def get_stage_config_with_history(self, stage_id: int) -> Dict[str, Any]:
        """获取阶段配置及其历史记录"""
        try:
            # 获取当前配置
            current_config = db_manager.execute_query(
                """SELECT pts.*, pt.name as task_name, pt.type as task_type
                   FROM pipeline_task_stages pts
                   JOIN pipeline_tasks pt ON pts.task_id = pt.id
                   WHERE pts.id = %s""",
                params=(stage_id,),
                fetch_one=True
            )
            
            if not current_config:
                return {'error': '阶段配置不存在'}
            
            return {
                'current_config': dict(current_config),
                'has_history': False
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def update_stage_config_with_history(self, stage_id: int, new_config: Dict[str, Any], 
                                       changed_by: str = 'system', 
                                       change_reason: str = '') -> Dict[str, Any]:
        """更新阶段配置并记录历史"""
        try:
            # 获取现有配置
            existing = db_manager.execute_query(
                "SELECT config FROM pipeline_task_stages WHERE id = %s",
                params=(stage_id,),
                fetch_one=True
            )
            
            if not existing:
                return {'success': False, 'error': '阶段配置不存在'}
            
            old_config = json.loads(existing['config']) if existing['config'] else {}
            
            # 更新配置
            updated_stage = db_manager.execute_update(
                """UPDATE pipeline_task_stages 
                   SET config = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s""",
                params=(json.dumps(new_config), changed_by, stage_id),
                return_updated=True
            )
            
            return {
                'success': True,
                'message': '配置更新成功',
                'updated_config': dict(updated_stage) if updated_stage else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_config_templates(self, stage_type: str = None, 
                           template_type: str = None, 
                           is_active: bool = True) -> List[Dict[str, Any]]:
        """获取配置模板列表"""
        try:
            where_conditions = ["is_active = %s"] if is_active is not None else []
            params = [is_active] if is_active is not None else []
            
            if stage_type:
                where_conditions.append("stage_type = %s")
                params.append(stage_type)
            
            if template_type:
                where_conditions.append("template_type = %s")
                params.append(template_type)
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            templates = db_manager.execute_query(
                f"""SELECT * FROM stage_config_templates{where_clause} 
                   ORDER BY is_system DESC, name ASC""",
                params=params,
                fetch_all=True
            )
            
            return [dict(template) for template in templates] if templates else []
            
        except Exception as e:
            print(f"获取配置模板失败: {e}")
            return []
    
    def apply_template_to_stage(self, stage_id: int, template_id: int, 
                              changed_by: str = 'system') -> Dict[str, Any]:
        """将配置模板应用到阶段"""
        try:
            # 获取模板配置
            template = db_manager.execute_query(
                "SELECT default_config FROM stage_config_templates WHERE id = %s AND is_active = true",
                params=(template_id,),
                fetch_one=True
            )
            
            if not template:
                return {'success': False, 'error': '模板不存在或已禁用'}
            
            default_config = json.loads(template['default_config']) if template['default_config'] else {}
            
            # 应用模板配置
            result = self.update_stage_config_with_history(
                stage_id=stage_id,
                new_config=default_config,
                changed_by=changed_by,
                change_reason=f"应用配置模板 {template_id}"
            )
            
            if result['success']:
                # 更新模板类型
                db_manager.execute_update(
                    "UPDATE pipeline_task_stages SET template_type = 'template' WHERE id = %s",
                    params=(stage_id,)
                )
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_config_template(self, name: str, stage_type: str, template_type: str,
                             config_schema: Dict[str, Any], default_config: Dict[str, Any],
                             description: str = '', created_by: str = 'system') -> Dict[str, Any]:
        """创建新的配置模板"""
        try:
            template = db_manager.execute_insert(
                """INSERT INTO stage_config_templates 
                   (name, description, stage_type, template_type, config_schema, default_config, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                params=(
                    name,
                    description,
                    stage_type,
                    template_type,
                    json.dumps(config_schema),
                    json.dumps(default_config),
                    created_by
                ),
                return_id=True
            )
            
            return {
                'success': True,
                'message': '模板创建成功',
                'template': dict(template)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_stage_config_summary(self, task_id: int) -> Dict[str, Any]:
        """获取任务的所有阶段配置摘要"""
        try:
            stages = db_manager.execute_query(
                """SELECT id, type, name, enabled, template_type, config, version, updated_at
                   FROM pipeline_task_stages 
                   WHERE task_id = %s 
                   ORDER BY order_index""",
                params=(task_id,),
                fetch_all=True
            )
            
            if not stages:
                return {'stages': [], 'total_count': 0}
            
            stage_summaries = []
            for stage in stages:
                config = json.loads(stage['config']) if stage['config'] else {}
                
                stage_summaries.append({
                    'id': stage['id'],
                    'type': stage['type'],
                    'name': stage['name'],
                    'enabled': stage['enabled'],
                    'template_type': stage['template_type'],
                    'config_count': len(config),
                    'version': stage['version'],
                    'last_updated': stage['updated_at'].isoformat() if stage['updated_at'] else None,
                    'has_config': len(config) > 0
                })
            
            return {
                'stages': stage_summaries,
                'total_count': len(stage_summaries),
                'enabled_count': sum(1 for s in stage_summaries if s['enabled']),
                'configured_count': sum(1 for s in stage_summaries if s['has_config'])
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def validate_config_against_template(self, config: Dict[str, Any], 
                                       template_id: int) -> Dict[str, Any]:
        """根据模板验证配置数据"""
        try:
            template = db_manager.execute_query(
                "SELECT config_schema FROM stage_config_templates WHERE id = %s",
                params=(template_id,),
                fetch_one=True
            )
            
            if not template:
                return {'valid': False, 'error': '模板不存在'}
            
            schema = json.loads(template['config_schema']) if template['config_schema'] else {}
            
            # 简单的模式验证（在实际项目中可以使用jsonschema库）
            validation_errors = []
            
            if 'properties' in schema:
                required_fields = schema.get('required', [])
                
                # 检查必填字段
                for field in required_fields:
                    if field not in config:
                        validation_errors.append(f"缺少必填字段: {field}")
                
                # 检查字段类型
                for field, field_schema in schema['properties'].items():
                    if field in config:
                        expected_type = field_schema.get('type')
                        actual_value = config[field]
                        
                        if expected_type == 'string' and not isinstance(actual_value, str):
                            validation_errors.append(f"字段 {field} 应为字符串类型")
                        elif expected_type == 'integer' and not isinstance(actual_value, int):
                            validation_errors.append(f"字段 {field} 应为整数类型")
                        elif expected_type == 'boolean' and not isinstance(actual_value, bool):
                            validation_errors.append(f"字段 {field} 应为布尔类型")
            
            return {
                'valid': len(validation_errors) == 0,
                'errors': validation_errors,
                'schema': schema
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}

# 全局配置模型管理器实例
config_model_manager = ConfigModelManager() 