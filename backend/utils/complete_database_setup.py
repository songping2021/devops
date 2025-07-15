#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime
from backend.utils.database import db_manager

class CompleteDatabaseSetup:
    """完整的数据库初始化设置"""
    
    def __init__(self):
        pass
    
    def create_base_tables(self):
        """创建基础表结构"""
        print("开始创建基础表结构...")
        
        # 1. 创建pipelines表
        print("创建pipelines表...")
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS pipelines (
                id SERIAL PRIMARY KEY,
                project_id VARCHAR(100) NOT NULL,
                branch VARCHAR(100) NOT NULL DEFAULT 'develop',
                task TEXT,
                stage TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100) DEFAULT 'system',
                updated_by VARCHAR(100) DEFAULT 'system',
                UNIQUE(project_id, branch)
            )
        """)
        
        # 2. 创建pipeline_tasks表
        print("创建pipeline_tasks表...")
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS pipeline_tasks (
                id SERIAL PRIMARY KEY,
                pipeline_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                type VARCHAR(50) NOT NULL DEFAULT 'maven',
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
            )
        """)
        
        # 3. 创建pipeline_task_stages表（增强版）
        print("创建pipeline_task_stages表...")
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS pipeline_task_stages (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                type VARCHAR(50) NOT NULL,
                name VARCHAR(100) NOT NULL,
                order_index INTEGER DEFAULT 0,
                config JSONB DEFAULT '{}',
                template_type VARCHAR(50) DEFAULT 'custom',
                version INTEGER DEFAULT 1,
                enabled BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100) DEFAULT 'system',
                updated_by VARCHAR(100) DEFAULT 'system',
                FOREIGN KEY (task_id) REFERENCES pipeline_tasks(id) ON DELETE CASCADE
            )
        """)
        
        # 4. 创建stage_config_templates表
        print("创建stage_config_templates表...")
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS stage_config_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                stage_type VARCHAR(50) NOT NULL,
                template_type VARCHAR(50) NOT NULL DEFAULT 'maven',
                config_schema JSONB NOT NULL DEFAULT '{}',
                default_config JSONB NOT NULL DEFAULT '{}',
                is_system BOOLEAN DEFAULT false,
                is_active BOOLEAN DEFAULT true,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100) DEFAULT 'system',
                updated_by VARCHAR(100) DEFAULT 'system',
                UNIQUE(name, stage_type, template_type, version)
            )
        """)
        
        # 5. 创建stage_config_history表
        print("创建stage_config_history表...")
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS stage_config_history (
                id SERIAL PRIMARY KEY,
                stage_id INTEGER NOT NULL,
                config_before JSONB,
                config_after JSONB NOT NULL,
                change_reason VARCHAR(255),
                changed_by VARCHAR(100) DEFAULT 'system',
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stage_id) REFERENCES pipeline_task_stages(id) ON DELETE CASCADE
            )
        """)
        
        # 6. 创建数据库迁移记录表
        print("创建database_migrations表...")
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS database_migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        
        print("基础表结构创建完成！")
    
    def create_indexes(self):
        """创建性能优化索引"""
        print("开始创建索引...")
        
        indexes = [
            # pipelines表索引
            "CREATE INDEX IF NOT EXISTS idx_pipelines_project_id ON pipelines(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_pipelines_branch ON pipelines(branch)",
            "CREATE INDEX IF NOT EXISTS idx_pipelines_project_branch ON pipelines(project_id, branch)",
            
            # pipeline_tasks表索引
            "CREATE INDEX IF NOT EXISTS idx_pipeline_tasks_pipeline_id ON pipeline_tasks(pipeline_id)",
            "CREATE INDEX IF NOT EXISTS idx_pipeline_tasks_name ON pipeline_tasks(name)",
            "CREATE INDEX IF NOT EXISTS idx_pipeline_tasks_type ON pipeline_tasks(type)",
            
            # pipeline_task_stages表索引
            "CREATE INDEX IF NOT EXISTS idx_pipeline_task_stages_task_id ON pipeline_task_stages(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_pipeline_task_stages_type ON pipeline_task_stages(type)",
            "CREATE INDEX IF NOT EXISTS idx_pipeline_task_stages_enabled ON pipeline_task_stages(enabled)",
            "CREATE INDEX IF NOT EXISTS idx_pipeline_task_stages_template_type ON pipeline_task_stages(template_type)",
            
            # stage_config_templates表索引
            "CREATE INDEX IF NOT EXISTS idx_stage_config_templates_stage_type ON stage_config_templates(stage_type)",
            "CREATE INDEX IF NOT EXISTS idx_stage_config_templates_template_type ON stage_config_templates(template_type)",
            "CREATE INDEX IF NOT EXISTS idx_stage_config_templates_is_active ON stage_config_templates(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_stage_config_templates_is_system ON stage_config_templates(is_system)",
            
            # stage_config_history表索引
            "CREATE INDEX IF NOT EXISTS idx_stage_config_history_stage_id ON stage_config_history(stage_id)",
            "CREATE INDEX IF NOT EXISTS idx_stage_config_history_changed_at ON stage_config_history(changed_at)",
        ]
        
        for sql in indexes:
            try:
                db_manager.execute_query(sql)
                print(f"创建索引成功: {sql.split()[-1]}")
            except Exception as e:
                print(f"创建索引失败: {e}")
        
        print("索引创建完成！")
    
    def insert_default_templates(self):
        """插入默认配置模板"""
        print("开始插入默认配置模板...")
        
        # Maven模板配置
        maven_templates = [
            {
                'name': 'Maven编译阶段默认配置',
                'stage_type': 'compile',
                'template_type': 'maven',
                'description': 'Maven项目编译阶段的默认配置模板',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'JDKVERSION': {'type': 'string', 'default': '8', 'description': 'JDK版本'},
                        'CODEPATH': {'type': 'string', 'default': '', 'description': '代码路径'},
                        'TARGETDIR': {'type': 'string', 'default': 'target', 'description': '制品路径'},
                        'BUILDFORMAT': {'type': 'string', 'default': 'jar', 'description': '制品格式'},
                        'BUILDCMD': {'type': 'string', 'default': 'mvn clean package -Dmaven.test.skip=true -U', 'description': '编译命令'}
                    },
                    'required': ['JDKVERSION', 'BUILDCMD']
                },
                'default_config': {
                    'JDKVERSION': '8',
                    'CODEPATH': '',
                    'TARGETDIR': 'target',
                    'BUILDFORMAT': 'jar',
                    'BUILDCMD': 'mvn clean package -Dmaven.test.skip=true -U'
                }
            },
            {
                'name': 'Maven构建阶段默认配置',
                'stage_type': 'build',
                'template_type': 'maven',
                'description': 'Maven项目构建阶段的默认配置模板',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'HARBORNAME': {'type': 'string', 'default': 'devops', 'description': 'Harbor项目名称'},
                        'BUILDDIR': {'type': 'string', 'default': '.', 'description': 'Dockerfile路径'},
                        'PLATFORM': {'type': 'string', 'default': 'linux/amd64', 'description': '镜像架构'},
                        'SERVICENAME': {'type': 'string', 'default': 'app', 'description': '服务名'}
                    },
                    'required': ['HARBORNAME']
                },
                'default_config': {
                    'HARBORNAME': 'devops',
                    'BUILDDIR': '.',
                    'PLATFORM': 'linux/amd64',
                    'SERVICENAME': 'app'
                }
            },
            {
                'name': 'Maven部署阶段默认配置',
                'stage_type': 'deploy',
                'template_type': 'maven',
                'description': 'Maven项目部署阶段的默认配置模板',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'NAMESPACE': {'type': 'string', 'default': 'app-dev', 'description': '命名空间'},
                        'SERVICENAME': {'type': 'string', 'default': 'app', 'description': '服务名'},
                        'CTPORT': {'type': 'integer', 'default': 80, 'description': '应用端口'},
                        'K8S': {'type': 'string', 'default': 'K8S_cmdicncf_jkyw', 'description': '发布集群'},
                        'INGRESS': {'type': 'string', 'default': 'yes', 'description': '是否启用Ingress'},
                        'LIMITSCPU': {'type': 'string', 'default': '1000m', 'description': 'CPU资源限制'},
                        'LIMITSMEM': {'type': 'string', 'default': '1024Mi', 'description': '内存资源限制'}
                    },
                    'required': ['NAMESPACE', 'SERVICENAME']
                },
                'default_config': {
                    'NAMESPACE': 'app-dev',
                    'SERVICENAME': 'app',
                    'CTPORT': 80,
                    'K8S': 'K8S_cmdicncf_jkyw',
                    'INGRESS': 'yes',
                    'LIMITSCPU': '1000m',
                    'LIMITSMEM': '1024Mi'
                }
            }
        ]
        
        # NPM模板配置
        npm_templates = [
            {
                'name': 'NPM编译阶段默认配置',
                'stage_type': 'compile',
                'template_type': 'npm',
                'description': 'NPM项目编译阶段的默认配置模板',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'NODEVERSION': {'type': 'string', 'default': '14.18', 'description': 'Node.js版本'},
                        'PNPMVERSION': {'type': 'string', 'default': '7.33.7', 'description': 'PNPM版本'},
                        'CODEPATH': {'type': 'string', 'default': '', 'description': '代码路径'},
                        'BUILDCMD': {'type': 'string', 'default': 'pnpm run build', 'description': '编译命令'},
                        'NPMDIR': {'type': 'string', 'default': 'dist', 'description': '制品发布目录'}
                    },
                    'required': ['NODEVERSION', 'BUILDCMD']
                },
                'default_config': {
                    'NODEVERSION': '14.18',
                    'PNPMVERSION': '7.33.7',
                    'CODEPATH': '',
                    'BUILDCMD': 'pnpm run build',
                    'NPMDIR': 'dist'
                }
            },
            {
                'name': 'NPM构建阶段默认配置',
                'stage_type': 'build',
                'template_type': 'npm',
                'description': 'NPM项目构建阶段的默认配置模板',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'HARBORNAME': {'type': 'string', 'default': 'devops', 'description': 'Harbor项目名称'},
                        'BUILDDIR': {'type': 'string', 'default': '.', 'description': 'Dockerfile路径'},
                        'PLATFORM': {'type': 'string', 'default': 'linux/amd64', 'description': '镜像架构'},
                        'INGRESS': {'type': 'string', 'default': 'yes', 'description': '是否启用Ingress'}
                    },
                    'required': ['HARBORNAME']
                },
                'default_config': {
                    'HARBORNAME': 'devops',
                    'BUILDDIR': '.',
                    'PLATFORM': 'linux/amd64',
                    'INGRESS': 'yes'
                }
            },
            {
                'name': 'NPM部署阶段默认配置',
                'stage_type': 'deploy',
                'template_type': 'npm',
                'description': 'NPM项目部署阶段的默认配置模板',
                'config_schema': {
                    'type': 'object',
                    'properties': {
                        'NAMESPACE': {'type': 'string', 'default': 'app-dev', 'description': '命名空间'},
                        'SERVICENAME': {'type': 'string', 'default': '$CI_PROJECT_NAME', 'description': '服务名'},
                        'CTPORT': {'type': 'integer', 'default': 80, 'description': '应用端口'},
                        'K8S': {'type': 'string', 'default': 'K8S_cmdicncf_jkyw', 'description': '发布集群'},
                        'REQUESTSCPU': {'type': 'string', 'default': '100m', 'description': 'CPU请求资源'},
                        'REQUESTSMEM': {'type': 'string', 'default': '128Mi', 'description': '内存请求资源'},
                        'LIMITSCPU': {'type': 'string', 'default': '500m', 'description': 'CPU资源限制'},
                        'LIMITSMEM': {'type': 'string', 'default': '256Mi', 'description': '内存资源限制'}
                    },
                    'required': ['NAMESPACE', 'SERVICENAME']
                },
                'default_config': {
                    'NAMESPACE': 'app-dev',
                    'SERVICENAME': '$CI_PROJECT_NAME',
                    'CTPORT': 80,
                    'K8S': 'K8S_cmdicncf_jkyw',
                    'REQUESTSCPU': '100m',
                    'REQUESTSMEM': '128Mi',
                    'LIMITSCPU': '500m',
                    'LIMITSMEM': '256Mi'
                }
            }
        ]
        
        # 插入所有模板
        all_templates = maven_templates + npm_templates
        inserted_count = 0
        
        for template in all_templates:
            try:
                # 检查是否已存在
                existing = db_manager.execute_query(
                    "SELECT id FROM stage_config_templates WHERE name = %s AND stage_type = %s AND template_type = %s",
                    params=(template['name'], template['stage_type'], template['template_type']),
                    fetch_one=True
                )
                
                if not existing:
                    db_manager.execute_insert(
                        """INSERT INTO stage_config_templates 
                           (name, description, stage_type, template_type, config_schema, default_config, is_system)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        params=(
                            template['name'],
                            template['description'],
                            template['stage_type'],
                            template['template_type'],
                            json.dumps(template['config_schema']),
                            json.dumps(template['default_config']),
                            True
                        )
                    )
                    print(f"插入模板成功: {template['name']}")
                    inserted_count += 1
                else:
                    print(f"模板已存在，跳过: {template['name']}")
            except Exception as e:
                print(f"插入模板失败 {template['name']}: {e}")
        
        print(f"默认模板插入完成，成功插入 {inserted_count} 个模板")
    
    def create_sample_data(self):
        """创建示例数据"""
        print("开始创建示例数据...")
        
        try:
            # 创建示例流水线
            pipeline = db_manager.execute_insert(
                """INSERT INTO pipelines (project_id, branch, task, stage, created_by)
                   VALUES (%s, %s, %s, %s, %s)""",
                params=(
                    '666',
                    'develop',
                    json.dumps([{'name': '123', 'type': 'maven', 'stages': []}]),
                    json.dumps(['compile', 'build', 'deploy']),
                    'system'
                ),
                return_id=True
            )
            
            if pipeline:
                pipeline_id = pipeline['id']
                print(f"创建示例流水线成功: {pipeline_id}")
                
                # 创建示例任务
                task = db_manager.execute_insert(
                    """INSERT INTO pipeline_tasks (pipeline_id, name, type, order_index)
                       VALUES (%s, %s, %s, %s)""",
                    params=(pipeline_id, '123', 'maven', 0),
                    return_id=True
                )
                
                if task:
                    task_id = task['id']
                    print(f"创建示例任务成功: {task_id}")
                    
                    # 创建示例阶段
                    stages = [
                        {'type': 'compile', 'name': 'compile', 'order_index': 0},
                        {'type': 'build', 'name': 'build', 'order_index': 1},
                        {'type': 'deploy', 'name': 'deploy', 'order_index': 2}
                    ]
                    
                    for stage in stages:
                        stage_record = db_manager.execute_insert(
                            """INSERT INTO pipeline_task_stages (task_id, type, name, order_index, config, enabled)
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            params=(
                                task_id,
                                stage['type'],
                                stage['name'],
                                stage['order_index'],
                                json.dumps({}),
                                stage['type'] == 'compile'  # 默认只启用编译阶段
                            ),
                            return_id=True
                        )
                        
                        if stage_record:
                            print(f"创建示例阶段成功: {stage['type']}")
        
        except Exception as e:
            print(f"创建示例数据失败: {e}")
        
        print("示例数据创建完成！")
    
    def setup_complete_database(self):
        """完整的数据库设置"""
        print("="*60)
        print("开始完整的数据库初始化设置...")
        print("="*60)
        
        try:
            # 1. 创建基础表结构
            self.create_base_tables()
            
            # 2. 创建索引
            self.create_indexes()
            
            # 3. 插入默认模板
            self.insert_default_templates()
            
            # 4. 创建示例数据
            self.create_sample_data()
            
            print("="*60)
            print("数据库初始化完成！")
            print("="*60)
            
            # 记录初始化完成
            try:
                db_manager.execute_insert(
                    "INSERT INTO database_migrations (name, description) VALUES (%s, %s)",
                    params=('complete_database_setup', 'TASK006完整数据库初始化')
                )
            except:
                pass  # 如果已存在则忽略
            
            return True
            
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            return False

def run_complete_setup():
    """运行完整的数据库设置"""
    setup = CompleteDatabaseSetup()
    return setup.setup_complete_database()

if __name__ == "__main__":
    run_complete_setup() 