#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Union
import json

class YamlConfigParser:
    """
    GitLab CI YAML配置文件解析器
    支持动态修改gitlab-ci.yml文件中的variables部分
    """
    
    def __init__(self):
        """初始化解析器"""
        self.template_path = Path("templates")
        self.workspace_path = Path("workspace")
    
    def load_yaml_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        加载YAML文件
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            dict: 解析后的YAML内容
            
        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML格式错误
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"YAML文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"YAML文件格式错误: {e}")
    
    def save_yaml_file(self, file_path: Union[str, Path], data: Dict[str, Any]) -> bool:
        """
        保存YAML文件，保持原有格式和注释
        
        Args:
            file_path: YAML文件路径
            data: 要保存的数据
            
        Returns:
            bool: 保存是否成功
        """
        file_path = Path(file_path)
        
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取原文件内容以保持注释
            original_content = ""
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as file:
                    original_content = file.read()
            
            # 使用自定义方法保持注释
            new_content = self._preserve_comments_while_updating(original_content, data)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            
            return True
            
        except Exception as e:
            print(f"保存YAML文件失败: {e}")
            return False
    
    def _preserve_comments_while_updating(self, original_content: str, new_data: Dict[str, Any]) -> str:
        """
        在更新YAML内容时保持注释
        
        Args:
            original_content: 原始文件内容
            new_data: 新的数据
            
        Returns:
            str: 更新后的内容
        """
        if not original_content or 'variables:' not in original_content:
            # 如果没有原内容或没有variables节，使用标准YAML格式
            return yaml.dump(new_data, default_flow_style=False, allow_unicode=True)
        
        lines = original_content.split('\n')
        new_lines = []
        in_variables_section = False
        variables_processed = False
        
        for line in lines:
            stripped_line = line.strip()
            
            # 检测variables节的开始
            if stripped_line == 'variables:':
                in_variables_section = True
                new_lines.append(line)
                
                # 添加新的variables内容（替换整个variables节）
                if 'variables' in new_data:
                    for key, value in new_data['variables'].items():
                        # 检查原文件中是否有这个变量的注释
                        comment = self._find_comment_for_variable(lines, key)
                        if comment:
                            new_lines.append(f"  {comment}")
                        # 确保value是字符串格式，如果是数字则不加引号
                        if isinstance(value, (int, float)):
                            new_lines.append(f"  {key}: {value}")
                        else:
                            new_lines.append(f"  {key}: \"{value}\"")
                
                variables_processed = True
                continue
            
            # 检测variables节的结束（下一个顶级节点或文件结束）
            if in_variables_section and line and not line.startswith(' ') and not line.startswith('\t') and stripped_line:
                in_variables_section = False
            
            # 如果在variables节内，跳过原有的变量定义（保留注释和空行）
            if in_variables_section:
                if stripped_line.startswith('#'):
                    # 跳过注释行（已经在上面处理）
                    continue
                elif ':' in stripped_line and not stripped_line.startswith('#'):
                    # 跳过变量定义行
                    continue
                elif not stripped_line:
                    # 保留空行
                    new_lines.append(line)
                # 其他行也跳过，因为我们已经重新生成了完整的variables节
            else:
                # 不在variables节内，保留原行
                new_lines.append(line)
        
        # 如果没有找到variables节，添加到文件末尾
        if not variables_processed and 'variables' in new_data:
            new_lines.append('')
            new_lines.append('variables:')
            for key, value in new_data['variables'].items():
                new_lines.append(f"  {key}: \"{value}\"")
        
        return '\n'.join(new_lines)
    
    def _find_comment_for_variable(self, lines: list, variable_name: str) -> str:
        """
        查找变量对应的注释
        
        Args:
            lines: 文件行列表
            variable_name: 变量名
            
        Returns:
            str: 注释内容
        """
        for i, line in enumerate(lines):
            if f"{variable_name}:" in line:
                # 查找前一行是否是注释
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line.startswith('#'):
                        return prev_line
        return ""
    
    def update_variables(self, file_path: Union[str, Path], variables: Dict[str, Any]) -> bool:
        """
        更新YAML文件中的variables部分
        
        Args:
            file_path: YAML文件路径
            variables: 要更新的变量字典
            
        Returns:
            bool: 更新是否成功
        """
        try:
            print(f"[DEBUG] 开始更新YAML文件: {file_path}")
            print(f"[DEBUG] 要更新的变量: {variables}")
            
            # 加载现有文件
            yaml_data = self.load_yaml_file(file_path)
            print(f"[DEBUG] 加载的YAML数据: {yaml_data}")
            
            # 确保variables节存在
            if 'variables' not in yaml_data:
                yaml_data['variables'] = {}
            
            # 更新变量
            original_vars = yaml_data['variables'].copy()
            yaml_data['variables'].update(variables)
            print(f"[DEBUG] 原始variables: {original_vars}")
            print(f"[DEBUG] 更新后variables: {yaml_data['variables']}")
            
            # 保存文件
            result = self.save_yaml_file(file_path, yaml_data)
            print(f"[DEBUG] 文件保存结果: {result}")
            return result
            
        except Exception as e:
            print(f"更新variables失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_variables(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        获取YAML文件中的variables部分
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            dict: variables内容
        """
        try:
            yaml_data = self.load_yaml_file(file_path)
            return yaml_data.get('variables', {})
        except Exception as e:
            print(f"获取variables失败: {e}")
            return {}
    
    def update_stage_toggle(self, file_path: Union[str, Path], stage_name: str, enabled: bool) -> bool:
        """
        更新阶段开关状态
        
        Args:
            file_path: YAML文件路径
            stage_name: 阶段名称 (compile, build, deploy)
            enabled: 是否启用
            
        Returns:
            bool: 更新是否成功
        """
        stage_value = "on" if enabled else "off"
        return self.update_variables(file_path, {stage_name: stage_value})
    
    def update_maven_config(self, file_path: Union[str, Path], config: Dict[str, Any]) -> bool:
        """
        更新Maven模板配置
        
        Args:
            file_path: YAML文件路径
            config: Maven配置参数
            
        Returns:
            bool: 更新是否成功
        """
        # Maven配置参数映射
        maven_vars = {}
        
        config_mapping = {
            'jdk_version': 'JDKVERSION',
            'code_path': 'CODEPATH',
            'target_dir': 'TARGETDIR',
            'build_format': 'BUILDFORMAT',
            'build_cmd': 'BUILDCMD',
            'harbor_name': 'HARBORNAME',
            'build_dir': 'BUILDDIR',
            'platform': 'PLATFORM',
            'service_name': 'SERVICENAME'
        }
        
        for key, yaml_key in config_mapping.items():
            if key in config:
                maven_vars[yaml_key] = str(config[key])
        
        return self.update_variables(file_path, maven_vars)
    
    def update_npm_config(self, file_path: Union[str, Path], config: Dict[str, Any]) -> bool:
        """
        更新NPM模板配置
        
        Args:
            file_path: YAML文件路径
            config: NPM配置参数
            
        Returns:
            bool: 更新是否成功
        """
        # NPM配置参数映射
        npm_vars = {}
        
        config_mapping = {
            'node_version': 'NODEVERSION',
            'pnpm_version': 'PNPMVERSION',
            'code_path': 'CODEPATH',
            'build_cmd': 'BUILDCMD',
            'npm_dir': 'NPMDIR',
            'harbor_name': 'HARBORNAME',
            'build_dir': 'BUILDDIR',
            'platform': 'PLATFORM'
        }
        
        for key, yaml_key in config_mapping.items():
            if key in config:
                npm_vars[yaml_key] = str(config[key])
        
        return self.update_variables(file_path, npm_vars)
    
    def update_deploy_config(self, file_path: Union[str, Path], config: Dict[str, Any]) -> bool:
        """
        更新部署配置
        
        Args:
            file_path: YAML文件路径
            config: 部署配置参数
            
        Returns:
            bool: 更新是否成功
        """
        # 部署配置参数映射
        deploy_vars = {}
        
        config_mapping = {
            'namespace': 'NAMESPACE',
            'service_name': 'SERVICENAME',
            'port': 'CTPORT',
            'k8s_cluster': 'K8S',
            'ingress_enabled': 'INGRESS',
            'cpu_limit': 'LIMITSCPU',
            'memory_limit': 'LIMITSMEM',
            'cpu_request': 'REQUESTSCPU',
            'memory_request': 'REQUESTSMEM'
        }
        
        for key, yaml_key in config_mapping.items():
            if key in config:
                if key == 'ingress_enabled':
                    # 布尔值转换为yes/no
                    deploy_vars[yaml_key] = "yes" if config[key] else "no"
                elif key in ['cpu_limit', 'cpu_request']:
                    # CPU资源单位转换：如果是数字则转换为毫核
                    value = config[key]
                    if isinstance(value, (int, float)):
                        deploy_vars[yaml_key] = f"{int(value * 1000)}m"
                    else:
                        deploy_vars[yaml_key] = str(value)
                elif key in ['memory_limit', 'memory_request']:
                    # 内存资源单位转换：如果是数字则转换为Mi
                    value = config[key]
                    if isinstance(value, (int, float)):
                        deploy_vars[yaml_key] = f"{int(value * 1024)}Mi"
                    else:
                        deploy_vars[yaml_key] = str(value)
                else:
                    deploy_vars[yaml_key] = str(config[key])
        
        return self.update_variables(file_path, deploy_vars)
    
    def get_task_gitlab_ci_path(self, project_id: str, branch: str, task_name: str) -> Path:
        """
        获取任务的gitlab-ci.yml文件路径
        
        Args:
            project_id: 项目ID
            branch: 分支名
            task_name: 任务名
            
        Returns:
            Path: gitlab-ci.yml文件路径
        """
        return self.workspace_path / str(project_id) / branch / task_name / "gitlab-ci.yml"
    
    def validate_yaml_structure(self, file_path: Union[str, Path]) -> tuple[bool, str]:
        """
        验证YAML文件结构
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        try:
            yaml_data = self.load_yaml_file(file_path)
            
            # 检查必要的结构
            if not isinstance(yaml_data, dict):
                return False, "YAML文件必须是字典格式"
            
            if 'variables' not in yaml_data:
                return False, "YAML文件缺少variables节"
            
            if not isinstance(yaml_data['variables'], dict):
                return False, "variables节必须是字典格式"
            
            return True, "YAML文件结构有效"
            
        except Exception as e:
            return False, f"YAML文件验证失败: {e}" 