#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify
import json
import uuid
from datetime import datetime
import sys
import os

# 添加后端路径到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 创建模板配置API蓝图
template_config_bp = Blueprint('template_config', __name__, url_prefix='/api/template_config')

# 稍后在main.py中初始化依赖项
db_manager = None

def init_dependencies(db_mgr):
    """初始化依赖项"""
    global db_manager
    db_manager = db_mgr

@template_config_bp.route('/', methods=['GET'])
def list_templates():
    """
    获取配置模板列表API
    
    功能描述：获取配置模板列表，支持分页和过滤
    
    参数：
    - template_type: 模板类型过滤 (maven/npm)
    - stage_type: 阶段类型过滤 (compile/build/deploy)
    - is_system: 是否系统模板 (true/false)
    - is_active: 是否激活 (true/false, 默认true)
    - page: 页码 (默认1)
    - limit: 每页数量 (默认20)
    - keyword: 关键词搜索 (名称或描述)
    
    返回参数：
    - success: 操作是否成功
    - templates: 模板列表
    - pagination: 分页信息
    - total: 总数量
    """
    try:
        # 获取查询参数
        template_type = request.args.get('template_type')
        stage_type = request.args.get('stage_type')
        is_system = request.args.get('is_system')
        is_active = request.args.get('is_active', 'true')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        keyword = request.args.get('keyword', '').strip()
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if template_type:
            where_conditions.append("template_type = %s")
            params.append(template_type)
        
        if stage_type:
            where_conditions.append("stage_type = %s")
            params.append(stage_type)
        
        if is_system is not None:
            where_conditions.append("is_system = %s")
            params.append(is_system.lower() == 'true')
        
        if is_active is not None:
            where_conditions.append("is_active = %s")
            params.append(is_active.lower() == 'true')
        
        if keyword:
            where_conditions.append("(name ILIKE %s OR description ILIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        # 构建WHERE子句
        where_clause = ""
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)
        
        # 计算总数
        count_query = f"SELECT COUNT(*) as total FROM stage_config_templates{where_clause}"
        total_result = db_manager.execute_query(count_query, params=params, fetch_one=True)
        total = total_result['total'] if total_result else 0
        
        # 计算偏移量
        offset = (page - 1) * limit
        
        # 查询模板列表
        list_query = f"""
            SELECT id, name, description, template_type, stage_type, 
                   default_config, config_schema, version, is_system, 
                   is_active, created_by, created_at, updated_at
            FROM stage_config_templates{where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        templates_raw = db_manager.execute_query(list_query, params=params, fetch_all=True)
        
        # 格式化模板数据
        templates = []
        for template in templates_raw:
            template_data = {
                'id': template['id'],
                'name': template['name'],
                'description': template['description'],
                'template_type': template['template_type'],
                'stage_type': template['stage_type'],
                'version': template['version'],
                'is_system': template['is_system'],
                'is_active': template['is_active'],
                'created_by': template['created_by'],
                'created_at': template['created_at'].isoformat() if template['created_at'] else None,
                'updated_at': template['updated_at'].isoformat() if template['updated_at'] else None,
                'config_count': len(template['default_config'] if template['default_config'] else {}),
                'schema_fields': len(template['config_schema'] if template['config_schema'] else {})
            }
            templates.append(template_data)
        
        # 分页信息
        total_pages = (total + limit - 1) // limit
        pagination = {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
        
        return jsonify({
            'success': True,
            'templates': templates,
            'pagination': pagination,
            'total': total
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取模板列表失败: {str(e)}'
        }), 500

@template_config_bp.route('/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """
    获取单个配置模板详情API
    
    功能描述：根据模板ID获取配置模板的详细信息
    
    参数：
    - template_id: 模板ID
    
    返回参数：
    - success: 操作是否成功
    - template: 模板详细信息
    """
    try:
        # 查询模板详情
        query = """
            SELECT id, name, description, template_type, stage_type,
                   default_config, config_schema, version, is_system,
                   is_active, created_by, created_at, updated_at
            FROM stage_config_templates
            WHERE id = %s
        """
        
        template = db_manager.execute_query(query, params=(template_id,), fetch_one=True)
        
        if not template:
            return jsonify({
                'success': False,
                'error': '模板不存在'
            }), 404
        
        # 解析配置数据 - JSONB字段已经是字典格式，不需要再次解析
        default_config = template['default_config'] if template['default_config'] else {}
        config_schema = template['config_schema'] if template['config_schema'] else {}
        
        template_data = {
            'id': template['id'],
            'name': template['name'],
            'description': template['description'],
            'template_type': template['template_type'],
            'stage_type': template['stage_type'],
            'default_config': default_config,
            'config_schema': config_schema,
            'version': template['version'],
            'is_system': template['is_system'],
            'is_active': template['is_active'],
            'created_by': template['created_by'],
            'created_at': template['created_at'].isoformat() if template['created_at'] else None,
            'updated_at': template['updated_at'].isoformat() if template['updated_at'] else None
        }
        
        return jsonify({
            'success': True,
            'template': template_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取模板详情失败: {str(e)}'
        }), 500

@template_config_bp.route('/', methods=['POST'])
def create_template():
    """
    创建配置模板API
    
    功能描述：创建新的配置模板
    
    入参：
    {
        "name": "模板名称",
        "description": "模板描述",
        "template_type": "maven/npm",
        "stage_type": "compile/build/deploy",
        "default_config": {"JDKVERSION": "11", ...},
        "config_schema": {"JDKVERSION": {"type": "string", ...}},
        "version": "1.0",
        "is_active": true
    }
    
    返回参数：
    - success: 操作是否成功
    - template: 创建的模板信息
    - template_id: 模板ID
    """
    try:
        data = request.json
        
        # 参数验证
        required_fields = ['name', 'template_type', 'stage_type', 'default_config']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'缺少必要参数: {field}'
                }), 400
        
        name = data['name'].strip()
        description = data.get('description', '').strip()
        template_type = data['template_type']
        stage_type = data['stage_type']
        default_config = data['default_config']
        config_schema = data.get('config_schema', {})
        # 处理版本字段 - 转换为整数
        version_input = data.get('version', 1)
        if isinstance(version_input, str):
            # 如果是字符串格式的版本号，转换为整数（去掉小数点）
            try:
                version = int(float(version_input))
            except (ValueError, TypeError):
                version = 1
        else:
            version = int(version_input) if version_input else 1
        is_active = data.get('is_active', True)
        created_by = data.get('created_by', 'system')
        
        # 验证模板类型
        if template_type not in ['maven', 'npm']:
            return jsonify({
                'success': False,
                'error': 'template_type 只支持 maven 或 npm'
            }), 400
        
        if stage_type not in ['compile', 'build', 'deploy']:
            return jsonify({
                'success': False,
                'error': 'stage_type 只支持 compile、build 或 deploy'
            }), 400
        
        # 检查模板名称是否已存在
        existing_query = """
            SELECT id FROM stage_config_templates 
            WHERE name = %s AND template_type = %s AND stage_type = %s AND is_active = true
        """
        existing = db_manager.execute_query(
            existing_query, 
            params=(name, template_type, stage_type), 
            fetch_one=True
        )
        
        if existing:
            return jsonify({
                'success': False,
                'error': f'模板名称 "{name}" 在 {template_type}-{stage_type} 类型中已存在'
            }), 400
        
        # 创建模板
        insert_query = """
            INSERT INTO stage_config_templates 
            (name, description, template_type, stage_type, default_config, 
             config_schema, version, is_system, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = db_manager.execute_insert(
            insert_query,
            params=(
                name, description, template_type, stage_type,
                json.dumps(default_config), json.dumps(config_schema),
                version, False, is_active, created_by
            )
        )
        
        template_id = result['id']
        
        return jsonify({
            'success': True,
            'message': f'配置模板 "{name}" 创建成功',
            'template_id': template_id,
            'template': {
                'id': template_id,
                'name': name,
                'description': description,
                'template_type': template_type,
                'stage_type': stage_type,
                'version': version,
                'is_active': is_active,
                'config_count': len(default_config)
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'创建配置模板失败: {str(e)}'
        }), 500

@template_config_bp.route('/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """
    更新配置模板API
    """
    try:
        data = request.json
        
        # 检查模板是否存在
        existing_query = "SELECT * FROM stage_config_templates WHERE id = %s"
        existing = db_manager.execute_query(existing_query, params=(template_id,), fetch_one=True)
        
        if not existing:
            return jsonify({
                'success': False,
                'error': '模板不存在'
            }), 404
        
        # 检查是否为系统模板
        if existing['is_system']:
            return jsonify({
                'success': False,
                'error': '系统模板无法修改'
            }), 403
        
        # 构建更新字段
        update_fields = []
        params = []
        
        if 'name' in data:
            name = data['name'].strip()
            if name:
                update_fields.append("name = %s")
                params.append(name)
        
        if 'description' in data:
            update_fields.append("description = %s")
            params.append(data['description'].strip())
        
        if 'default_config' in data:
            update_fields.append("default_config = %s")
            params.append(json.dumps(data['default_config']))
        
        if 'config_schema' in data:
            update_fields.append("config_schema = %s")
            params.append(json.dumps(data['config_schema']))
        
        if 'version' in data:
            update_fields.append("version = %s")
            # 处理版本字段
            version_input = data['version']
            if isinstance(version_input, str):
                try:
                    version_val = int(float(version_input))
                except (ValueError, TypeError):
                    version_val = 1
            else:
                version_val = int(version_input) if version_input else 1
            params.append(version_val)
        
        if 'is_active' in data:
            update_fields.append("is_active = %s")
            params.append(data['is_active'])
        
        if not update_fields:
            return jsonify({
                'success': False,
                'error': '没有提供更新字段'
            }), 400
        
        # 添加更新时间
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)
        
        # 执行更新
        update_query = f"""
            UPDATE stage_config_templates 
            SET {', '.join(update_fields)}
            WHERE id = %s
        """
        
        db_manager.execute_update(update_query, params=params)
        
        return jsonify({
            'success': True,
            'message': f'配置模板更新成功'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'更新配置模板失败: {str(e)}'
        }), 500

@template_config_bp.route('/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """
    删除配置模板API
    """
    try:
        force = request.args.get('force', 'false').lower() == 'true'
        
        # 检查模板是否存在
        existing_query = "SELECT * FROM stage_config_templates WHERE id = %s"
        existing = db_manager.execute_query(existing_query, params=(template_id,), fetch_one=True)
        
        if not existing:
            return jsonify({
                'success': False,
                'error': '模板不存在'
            }), 404
        
        # 检查是否为系统模板
        if existing['is_system'] and not force:
            return jsonify({
                'success': False,
                'error': '系统模板无法删除，请使用force=true参数强制删除'
            }), 403
        
        # 逻辑删除（设置为非激活状态）
        delete_query = """
            UPDATE stage_config_templates 
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        
        db_manager.execute_update(delete_query, params=(template_id,))
        
        return jsonify({
            'success': True,
            'message': f'配置模板 "{existing["name"]}" 已删除'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'删除配置模板失败: {str(e)}'
        }), 500

@template_config_bp.route('/import', methods=['POST'])
def import_template():
    """
    导入配置模板API
    
    功能描述：从JSON数据导入配置模板
    
    入参：
    {
        "templates": [
            {
                "name": "模板名称",
                "description": "模板描述",
                "template_type": "maven",
                "stage_type": "compile",
                "default_config": {...},
                "config_schema": {...}
            }
        ],
        "overwrite": false,
        "import_mode": "create_only"  // create_only, update_only, create_or_update
    }
    
    返回参数：
    - success: 操作是否成功
    - import_summary: 导入结果摘要
    - details: 详细结果
    """
    try:
        data = request.json
        templates = data.get('templates', [])
        overwrite = data.get('overwrite', False)
        import_mode = data.get('import_mode', 'create_only')
        
        if not templates:
            return jsonify({
                'success': False,
                'error': '没有提供要导入的模板'
            }), 400
        
        if import_mode not in ['create_only', 'update_only', 'create_or_update']:
            return jsonify({
                'success': False,
                'error': 'import_mode 只支持 create_only、update_only 或 create_or_update'
            }), 400
        
        import_results = []
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for template_data in templates:
            try:
                name = template_data.get('name', '').strip()
                template_type = template_data.get('template_type')
                stage_type = template_data.get('stage_type')
                
                if not all([name, template_type, stage_type]):
                    import_results.append({
                        'name': name or 'Unknown',
                        'status': 'error',
                        'message': '缺少必要字段: name, template_type, stage_type'
                    })
                    error_count += 1
                    continue
                
                # 检查模板是否已存在
                existing_query = """
                    SELECT id FROM stage_config_templates 
                    WHERE name = %s AND template_type = %s AND stage_type = %s
                """
                existing = db_manager.execute_query(
                    existing_query,
                    params=(name, template_type, stage_type),
                    fetch_one=True
                )
                
                if existing:
                    # 模板已存在
                    if import_mode == 'create_only':
                        import_results.append({
                            'name': name,
                            'status': 'skipped',
                            'message': '模板已存在，跳过创建'
                        })
                        skipped_count += 1
                        continue
                    elif import_mode == 'update_only' or (import_mode == 'create_or_update' and overwrite):
                        # 更新现有模板
                        update_fields = []
                        params = []
                        
                        if 'description' in template_data:
                            update_fields.append("description = %s")
                            params.append(template_data['description'])
                        
                        if 'default_config' in template_data:
                            update_fields.append("default_config = %s")
                            params.append(json.dumps(template_data['default_config']))
                        
                        if 'config_schema' in template_data:
                            update_fields.append("config_schema = %s")
                            params.append(json.dumps(template_data['config_schema']))
                        
                        if 'version' in template_data:
                            update_fields.append("version = %s")
                            params.append(template_data['version'])
                        
                        update_fields.append("updated_at = CURRENT_TIMESTAMP")
                        params.append(existing['id'])
                        
                        update_query = f"""
                            UPDATE stage_config_templates 
                            SET {', '.join(update_fields)}
                            WHERE id = %s
                        """
                        
                        db_manager.execute_update(update_query, params=params)
                        
                        import_results.append({
                            'name': name,
                            'status': 'updated',
                            'message': '模板已更新'
                        })
                        updated_count += 1
                    else:
                        import_results.append({
                            'name': name,
                            'status': 'skipped',
                            'message': '模板已存在，未设置覆盖模式'
                        })
                        skipped_count += 1
                else:
                    # 创建新模板
                    if import_mode == 'update_only':
                        import_results.append({
                            'name': name,
                            'status': 'skipped',
                            'message': '模板不存在，跳过更新'
                        })
                        skipped_count += 1
                        continue
                    
                    insert_query = """
                        INSERT INTO stage_config_templates 
                        (name, description, template_type, stage_type, default_config, 
                         config_schema, version, is_system, is_active, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """
                    
                    result = db_manager.execute_insert(
                        insert_query,
                        params=(
                            name,
                            template_data.get('description', ''),
                            template_type,
                            stage_type,
                            json.dumps(template_data.get('default_config', {})),
                            json.dumps(template_data.get('config_schema', {})),
                            template_data.get('version', '1.0'),
                            template_data.get('is_system', False),
                            template_data.get('is_active', True),
                            template_data.get('created_by', 'import')
                        )
                    )
                    
                    import_results.append({
                        'name': name,
                        'status': 'created',
                        'message': f'模板已创建，ID: {result["id"]}',
                        'template_id': result['id']
                    })
                    created_count += 1
                    
            except Exception as template_error:
                import_results.append({
                    'name': template_data.get('name', 'Unknown'),
                    'status': 'error',
                    'message': f'导入失败: {str(template_error)}'
                })
                error_count += 1
        
        import_summary = {
            'total': len(templates),
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': error_count,
            'success_rate': f"{((created_count + updated_count) / len(templates) * 100):.1f}%" if templates else "0%"
        }
        
        return jsonify({
            'success': True,
            'message': f'模板导入完成，共处理{len(templates)}个模板',
            'import_summary': import_summary,
            'details': import_results
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'导入配置模板失败: {str(e)}'
        }), 500

@template_config_bp.route('/export', methods=['GET'])
def export_templates():
    """
    导出配置模板API
    
    功能描述：导出配置模板为JSON格式
    
    参数：
    - template_ids: 模板ID列表 (逗号分隔)
    - template_type: 模板类型过滤
    - stage_type: 阶段类型过滤
    - include_system: 是否包含系统模板 (默认false)
    
    返回参数：
    - success: 操作是否成功
    - templates: 导出的模板数据
    - export_info: 导出信息
    """
    try:
        template_ids = request.args.get('template_ids', '').strip()
        template_type = request.args.get('template_type')
        stage_type = request.args.get('stage_type')
        include_system = request.args.get('include_system', 'false').lower() == 'true'
        
        # 构建查询条件
        where_conditions = ["is_active = true"]
        params = []
        
        if template_ids:
            try:
                ids = [int(id.strip()) for id in template_ids.split(',') if id.strip()]
                if ids:
                    placeholders = ','.join(['%s'] * len(ids))
                    where_conditions.append(f"id IN ({placeholders})")
                    params.extend(ids)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'template_ids 格式错误，应为逗号分隔的数字'
                }), 400
        
        if template_type:
            where_conditions.append("template_type = %s")
            params.append(template_type)
        
        if stage_type:
            where_conditions.append("stage_type = %s")
            params.append(stage_type)
        
        if not include_system:
            where_conditions.append("is_system = false")
        
        where_clause = " WHERE " + " AND ".join(where_conditions)
        
        # 查询模板数据
        export_query = f"""
            SELECT name, description, template_type, stage_type,
                   default_config, config_schema, version, is_system,
                   created_by, created_at
            FROM stage_config_templates{where_clause}
            ORDER BY template_type, stage_type, name
        """
        
        templates_raw = db_manager.execute_query(export_query, params=params, fetch_all=True)
        
        if not templates_raw:
            return jsonify({
                'success': False,
                'error': '没有找到符合条件的模板'
            }), 404
        
        # 格式化导出数据
        export_templates = []
        for template in templates_raw:
            export_data = {
                'name': template['name'],
                'description': template['description'],
                'template_type': template['template_type'],
                'stage_type': template['stage_type'],
                'default_config': json.loads(template['default_config']) if template['default_config'] else {},
                'config_schema': json.loads(template['config_schema']) if template['config_schema'] else {},
                'version': template['version'],
                'is_system': template['is_system'],
                'created_by': template['created_by'],
                'export_time': datetime.now().isoformat()
            }
            export_templates.append(export_data)
        
        export_info = {
            'export_time': datetime.now().isoformat(),
            'total_templates': len(export_templates),
            'template_types': list(set([t['template_type'] for t in export_templates])),
            'stage_types': list(set([t['stage_type'] for t in export_templates])),
            'include_system_templates': include_system
        }
        
        return jsonify({
            'success': True,
            'templates': export_templates,
            'export_info': export_info
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'导出配置模板失败: {str(e)}'
        }), 500

@template_config_bp.route('/<int:template_id>/clone', methods=['POST'])
def clone_template(template_id):
    """
    克隆配置模板API
    
    功能描述：基于现有模板创建新模板
    
    入参：
    {
        "new_name": "新模板名称",
        "description": "新模板描述",
        "version": "1.0",
        "modify_config": {...}  // 要修改的配置项
    }
    
    返回参数：
    - success: 操作是否成功
    - template: 克隆后的模板信息
    - template_id: 新模板ID
    """
    try:
        data = request.json
        new_name = data.get('new_name', '').strip()
        
        if not new_name:
            return jsonify({
                'success': False,
                'error': '缺少新模板名称'
            }), 400
        
        # 获取原模板
        source_query = """
            SELECT * FROM stage_config_templates 
            WHERE id = %s AND is_active = true
        """
        source_template = db_manager.execute_query(source_query, params=(template_id,), fetch_one=True)
        
        if not source_template:
            return jsonify({
                'success': False,
                'error': '源模板不存在'
            }), 404
        
        # 检查新名称是否冲突
        conflict_query = """
            SELECT id FROM stage_config_templates 
            WHERE name = %s AND template_type = %s AND stage_type = %s AND is_active = true
        """
        conflict = db_manager.execute_query(
            conflict_query,
            params=(new_name, source_template['template_type'], source_template['stage_type']),
            fetch_one=True
        )
        
        if conflict:
            return jsonify({
                'success': False,
                'error': f'模板名称 "{new_name}" 已存在'
            }), 400
        
        # 准备新模板数据
        description = data.get('description', source_template['description'])
        version = data.get('version', '1.0')
        modify_config = data.get('modify_config', {})
        
        # 合并配置
        original_config = json.loads(source_template['default_config']) if source_template['default_config'] else {}
        new_config = {**original_config, **modify_config}
        
        # 创建新模板
        insert_query = """
            INSERT INTO stage_config_templates 
            (name, description, template_type, stage_type, default_config, 
             config_schema, version, is_system, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = db_manager.execute_insert(
            insert_query,
            params=(
                new_name, description,
                source_template['template_type'], source_template['stage_type'],
                json.dumps(new_config), source_template['config_schema'],
                version, False, True, data.get('created_by', 'clone')
            )
        )
        
        new_template_id = result['id']
        
        return jsonify({
            'success': True,
            'message': f'模板 "{new_name}" 克隆成功',
            'template_id': new_template_id,
            'template': {
                'id': new_template_id,
                'name': new_name,
                'description': description,
                'template_type': source_template['template_type'],
                'stage_type': source_template['stage_type'],
                'version': version,
                'source_template_id': template_id,
                'config_count': len(new_config)
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'克隆配置模板失败: {str(e)}'
        }), 500 