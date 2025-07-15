#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime
from backend.utils.database import db_manager

class DatabaseMigration:
    """数据库迁移管理类"""
    
    def __init__(self):
        self.migration_table = "database_migrations"
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """确保迁移记录表存在"""
        try:
            db_manager.execute_query(f"""
                CREATE TABLE IF NOT EXISTS {self.migration_table} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
        except Exception as e:
            print(f"创建迁移表失败: {e}")
    
    def is_migration_executed(self, migration_name):
        """检查迁移是否已执行"""
        try:
            result = db_manager.execute_query(
                f"SELECT id FROM {self.migration_table} WHERE name = %s",
                params=(migration_name,),
                fetch_one=True
            )
            return result is not None
        except Exception as e:
            print(f"检查迁移状态失败: {e}")
            return False
    
    def record_migration(self, migration_name, description=""):
        """记录迁移执行"""
        try:
            db_manager.execute_insert(
                f"INSERT INTO {self.migration_table} (name, description) VALUES (%s, %s)",
                params=(migration_name, description)
            )
        except Exception as e:
            print(f"记录迁移失败: {e}")
    
    def run_migration(self, migration_name, migration_func, description=""):
        """运行迁移"""
        if self.is_migration_executed(migration_name):
            print(f"迁移 {migration_name} 已执行，跳过")
            return True
        
        try:
            print(f"执行迁移: {migration_name}")
            migration_func()
            self.record_migration(migration_name, description)
            print(f"迁移 {migration_name} 执行成功")
            return True
        except Exception as e:
            print(f"迁移 {migration_name} 执行失败: {e}")
            return False

class TaskConfigMigrations:
    """任务配置相关的数据库迁移"""
    
    def __init__(self):
        self.migration_manager = DatabaseMigration()
    
    def migrate_001_enhance_pipeline_task_stages(self):
        """迁移001: 增强pipeline_task_stages表结构"""
        def migration():
            # 添加新字段
            migrations = [
                # 添加详细配置字段
                "ALTER TABLE pipeline_task_stages ADD COLUMN IF NOT EXISTS template_type VARCHAR(50) DEFAULT 'custom'",
                "ALTER TABLE pipeline_task_stages ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1",
                "ALTER TABLE pipeline_task_stages ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT true",
                "ALTER TABLE pipeline_task_stages ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE pipeline_task_stages ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE pipeline_task_stages ADD COLUMN IF NOT EXISTS created_by VARCHAR(100) DEFAULT 'system'",
                "ALTER TABLE pipeline_task_stages ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100) DEFAULT 'system'",
                
                # 添加索引提高查询性能
                "CREATE INDEX IF NOT EXISTS idx_pipeline_task_stages_task_id ON pipeline_task_stages(task_id)",
                "CREATE INDEX IF NOT EXISTS idx_pipeline_task_stages_type ON pipeline_task_stages(type)",
                "CREATE INDEX IF NOT EXISTS idx_pipeline_task_stages_enabled ON pipeline_task_stages(enabled)",
                "CREATE INDEX IF NOT EXISTS idx_pipeline_task_stages_template_type ON pipeline_task_stages(template_type)",
            ]
            
            for sql in migrations:
                try:
                    db_manager.execute_query(sql)
                    print(f"执行SQL成功: {sql[:50]}...")
                except Exception as e:
                    if "already exists" not in str(e) and "does not exist" not in str(e):
                        print(f"SQL执行警告: {sql[:50]}... - {e}")
        
        return self.migration_manager.run_migration(
            "001_enhance_pipeline_task_stages",
            migration,
            "增强pipeline_task_stages表结构，添加版本控制和性能优化"
        )
    
    def migrate_002_create_stage_config_templates(self):
        """迁移002: 创建阶段配置模板表"""
        def migration():
            # 创建阶段配置模板表
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
            
            # 添加索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_stage_config_templates_stage_type ON stage_config_templates(stage_type)",
                "CREATE INDEX IF NOT EXISTS idx_stage_config_templates_template_type ON stage_config_templates(template_type)",
                "CREATE INDEX IF NOT EXISTS idx_stage_config_templates_is_active ON stage_config_templates(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_stage_config_templates_is_system ON stage_config_templates(is_system)",
            ]
            
            for sql in indexes:
                db_manager.execute_query(sql)
        
        return self.migration_manager.run_migration(
            "002_create_stage_config_templates",
            migration,
            "创建阶段配置模板表，支持配置模板管理"
        )
    
    def migrate_003_create_stage_config_history(self):
        """迁移003: 创建阶段配置历史记录表"""
        def migration():
            # 创建阶段配置历史表
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
            
            # 添加索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_stage_config_history_stage_id ON stage_config_history(stage_id)",
                "CREATE INDEX IF NOT EXISTS idx_stage_config_history_changed_at ON stage_config_history(changed_at)",
            ]
            
            for sql in indexes:
                db_manager.execute_query(sql)
        
        return self.migration_manager.run_migration(
            "003_create_stage_config_history",
            migration,
            "创建阶段配置历史记录表，支持配置变更追踪"
        )
    
    def migrate_004_insert_default_templates(self):
        """迁移004: 插入默认配置模板"""
        def migration():
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
                    else:
                        print(f"模板已存在，跳过: {template['name']}")
                except Exception as e:
                    print(f"插入模板失败 {template['name']}: {e}")
        
        return self.migration_manager.run_migration(
            "004_insert_default_templates",
            migration,
            "插入Maven和NPM的默认配置模板"
        )
    
    def migrate_005_add_updated_at_triggers(self):
        """迁移005: 添加自动更新updated_at字段的触发器"""
        def migration():
            # 创建更新时间戳的函数
            db_manager.execute_query("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """)
            
            # 为相关表添加触发器
            tables = [
                'pipeline_task_stages',
                'stage_config_templates',
                'stage_config_history'
            ]
            
            for table in tables:
                try:
                    # 先删除可能存在的触发器
                    db_manager.execute_query(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")
                    
                    # 创建新触发器
                    db_manager.execute_query(f"""
                        CREATE TRIGGER update_{table}_updated_at
                        BEFORE UPDATE ON {table}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column()
                    """)
                    print(f"为表 {table} 添加updated_at触发器成功")
                except Exception as e:
                    print(f"为表 {table} 添加触发器失败: {e}")
        
        return self.migration_manager.run_migration(
            "005_add_updated_at_triggers",
            migration,
            "添加自动更新updated_at字段的数据库触发器"
        )
    
    def migrate_006_add_gitlab_sync_history_table(self):
        """迁移006: 添加GitLab同步历史表"""
        def migration():
            # 创建GitLab同步历史表
            db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS gitlab_sync_history (
                    id SERIAL PRIMARY KEY,
                    operation_id VARCHAR(32) UNIQUE NOT NULL,
                    project_id VARCHAR(100) NOT NULL,
                    branch VARCHAR(100) NOT NULL DEFAULT 'main',
                    task_name VARCHAR(100) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    sync_status VARCHAR(20) NOT NULL,
                    sync_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    conflict_details JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引优化查询性能
            db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_gitlab_sync_history_operation_id 
                ON gitlab_sync_history(operation_id)
            """)
            
            db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_gitlab_sync_history_project_task 
                ON gitlab_sync_history(project_id, task_name)
            """)
            
            db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_gitlab_sync_history_status 
                ON gitlab_sync_history(sync_status)
            """)
            
            db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_gitlab_sync_history_timestamp 
                ON gitlab_sync_history(sync_timestamp)
            """)
            
            # 创建更新时间戳触发器
            db_manager.execute_query("""
                CREATE OR REPLACE FUNCTION update_gitlab_sync_history_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            db_manager.execute_query("""
                DROP TRIGGER IF EXISTS trigger_update_gitlab_sync_history_updated_at 
                ON gitlab_sync_history
            """)
            
            db_manager.execute_query("""
                CREATE TRIGGER trigger_update_gitlab_sync_history_updated_at
                    BEFORE UPDATE ON gitlab_sync_history
                    FOR EACH ROW
                    EXECUTE FUNCTION update_gitlab_sync_history_updated_at()
            """)
            
            # 记录迁移执行 - 这里由run_migration方法处理，不需要手动插入
        
        return self.migration_manager.run_migration(
            "006_add_gitlab_sync_history_table",
            migration,
            "添加GitLab同步历史表，用于记录GitLab文件同步的历史和状态"
        )
    
    def run_all_migrations(self):
        """运行所有迁移"""
        print("开始执行TASK006数据模型优化迁移...")
        
        migrations = [
            self.migrate_001_enhance_pipeline_task_stages,
            self.migrate_002_create_stage_config_templates,
            self.migrate_003_create_stage_config_history,
            self.migrate_004_insert_default_templates,
            self.migrate_005_add_updated_at_triggers,
            self.migrate_006_add_gitlab_sync_history_table
        ]
        
        success_count = 0
        for migration in migrations:
            if migration():
                success_count += 1
            else:
                print(f"迁移失败，停止后续迁移")
                break
        
        print(f"迁移完成，成功执行 {success_count}/{len(migrations)} 个迁移")
        return success_count == len(migrations)

# 工具函数
def run_task006_migrations():
    """运行TASK006相关的数据库迁移"""
    migration = TaskConfigMigrations()
    return migration.run_all_migrations()

if __name__ == "__main__":
    # 直接运行迁移
    run_task006_migrations() 