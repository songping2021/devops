#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import ipaddress
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import semver


class ConfigValidator:
    """
    配置参数验证器
    
    功能描述：提供全面的配置参数验证功能，确保用户输入的配置参数符合规范和要求
    
    支持验证类型：
    - JDK版本有效性验证
    - Node.js和PNPM版本兼容性验证
    - 资源配置合理性验证
    - 路径和命名规范验证
    - 网络配置验证
    - 环境变量验证
    """
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        
        # 支持的JDK版本列表
        self.supported_jdk_versions = [
            '8', '11', '17', '21',
            'jdk-8', 'jdk-11', 'jdk-17', 'jdk-21',
            'openjdk-8', 'openjdk-11', 'openjdk-17', 'openjdk-21'
        ]
        
        # Node.js版本兼容性矩阵
        self.nodejs_compatibility = {
            'lts_versions': ['14.21.3', '16.20.0', '18.17.0', '20.5.0'],
            'min_version': '14.0.0',
            'max_version': '21.0.0'
        }
        
        # PNPM版本兼容性
        self.pnpm_compatibility = {
            'supported_versions': ['6.x', '7.x', '8.x'],
            'min_version': '6.0.0',
            'max_version': '9.0.0'
        }
        
        # 资源限制合理性范围
        self.resource_limits = {
            'cpu': {
                'min_millicores': 10,   # 0.01核
                'max_millicores': 16000,  # 16核
                'recommended_min': 100,   # 0.1核
                'recommended_max': 8000   # 8核
            },
            'memory': {
                'min_mb': 64,      # 64MB
                'max_mb': 65536,   # 64GB
                'recommended_min': 128,  # 128MB
                'recommended_max': 16384  # 16GB
            }
        }
        
        # 网络端口范围
        self.port_ranges = {
            'system_ports': (1, 1023),
            'registered_ports': (1024, 49151),
            'dynamic_ports': (49152, 65535),
            'recommended_min': 8000,
            'recommended_max': 9999
        }
        
        # 路径和命名规范
        self.naming_patterns = {
            'service_name': r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$',
            'namespace': r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$',
            'path': r'^[a-zA-Z0-9._/*?-]+$',
            'docker_image': r'^[a-z0-9]+([._-][a-z0-9]+)*(/[a-z0-9]+([._-][a-z0-9]+)*)*$'
        }
    
    def clear_messages(self):
        """清空验证消息"""
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_jdk_version(self, version: str) -> bool:
        """
        验证JDK版本有效性
        
        Args:
            version: JDK版本字符串
            
        Returns:
            bool: 验证是否通过
        """
        if not version or not isinstance(version, str):
            self.errors.append("JDK版本不能为空")
            return False
        
        version = version.strip().lower()
        
        if version in self.supported_jdk_versions:
            self.info.append(f"JDK版本 {version} 验证通过")
            return True
        
        # 尝试数字版本格式
        if version.isdigit():
            version_num = int(version)
            if version_num in [8, 11, 17, 21]:
                self.info.append(f"JDK版本 {version} 验证通过")
                return True
            else:
                self.warnings.append(f"JDK版本 {version} 不在推荐列表中，建议使用: 8, 11, 17, 21")
                return True
        
        self.errors.append(f"不支持的JDK版本: {version}。支持的版本: {', '.join(self.supported_jdk_versions)}")
        return False
    
    def validate_nodejs_version(self, version: str) -> bool:
        """
        验证Node.js版本有效性和兼容性
        
        Args:
            version: Node.js版本字符串
            
        Returns:
            bool: 验证是否通过
        """
        if not version or not isinstance(version, str):
            self.errors.append("Node.js版本不能为空")
            return False
        
        version = version.strip()
        
        # 移除可能的前缀
        if version.startswith('v'):
            version = version[1:]
        if version.startswith('node-'):
            version = version[5:]
        
        try:
            # 验证语义化版本格式
            parsed_version = semver.VersionInfo.parse(version)
            
            # 检查版本范围
            min_version = semver.VersionInfo.parse(self.nodejs_compatibility['min_version'])
            max_version = semver.VersionInfo.parse(self.nodejs_compatibility['max_version'])
            
            if parsed_version < min_version:
                self.errors.append(f"Node.js版本 {version} 过低，最低支持版本: {self.nodejs_compatibility['min_version']}")
                return False
            
            if parsed_version >= max_version:
                self.warnings.append(f"Node.js版本 {version} 较新，可能存在兼容性问题")
            
            # 检查是否为LTS版本
            is_lts = any(version.startswith(lts.split('.')[0] + '.' + lts.split('.')[1]) 
                        for lts in self.nodejs_compatibility['lts_versions'])
            
            if is_lts:
                self.info.append(f"Node.js版本 {version} 为LTS版本，推荐使用")
            else:
                self.warnings.append(f"Node.js版本 {version} 非LTS版本，建议使用LTS版本以获得更好的稳定性")
            
            return True
            
        except ValueError:
            self.errors.append(f"Node.js版本格式错误: {version}。应使用语义化版本格式，如: 18.17.0")
            return False
    
    def validate_pnpm_version(self, version: str) -> bool:
        """
        验证PNPM版本有效性和兼容性
        
        Args:
            version: PNPM版本字符串
            
        Returns:
            bool: 验证是否通过
        """
        if not version or not isinstance(version, str):
            self.errors.append("PNPM版本不能为空")
            return False
        
        version = version.strip()
        
        # 移除可能的前缀
        if version.startswith('v'):
            version = version[1:]
        
        try:
            # 验证语义化版本格式
            parsed_version = semver.VersionInfo.parse(version)
            
            # 检查版本范围
            min_version = semver.VersionInfo.parse(self.pnpm_compatibility['min_version'])
            max_version = semver.VersionInfo.parse(self.pnpm_compatibility['max_version'])
            
            if parsed_version < min_version:
                self.errors.append(f"PNPM版本 {version} 过低，最低支持版本: {self.pnpm_compatibility['min_version']}")
                return False
            
            if parsed_version >= max_version:
                self.warnings.append(f"PNPM版本 {version} 过新，可能存在兼容性问题")
            
            # 检查主版本兼容性
            major_version = f"{parsed_version.major}.x"
            if major_version in self.pnpm_compatibility['supported_versions']:
                self.info.append(f"PNPM版本 {version} ({major_version}) 兼容性良好")
            else:
                self.warnings.append(f"PNPM主版本 {major_version} 可能存在兼容性问题")
            
            return True
            
        except ValueError:
            self.errors.append(f"PNPM版本格式错误: {version}。应使用语义化版本格式，如: 8.9.0")
            return False
    
    def validate_nodejs_pnpm_compatibility(self, nodejs_version: str, pnpm_version: str) -> bool:
        """
        验证Node.js和PNPM版本兼容性
        
        Args:
            nodejs_version: Node.js版本
            pnpm_version: PNPM版本
            
        Returns:
            bool: 兼容性验证是否通过
        """
        try:
            node_ver = semver.VersionInfo.parse(nodejs_version.lstrip('v'))
            pnpm_ver = semver.VersionInfo.parse(pnpm_version.lstrip('v'))
            
            # 已知兼容性规则
            compatibility_rules = [
                # Node.js 14.x 与 PNPM 6.x-8.x 兼容
                (14, [6, 7, 8]),
                # Node.js 16.x 与 PNPM 6.x-8.x 兼容
                (16, [6, 7, 8]),
                # Node.js 18.x 与 PNPM 7.x-8.x 兼容
                (18, [7, 8]),
                # Node.js 20.x 与 PNPM 8.x 兼容
                (20, [8])
            ]
            
            node_major = node_ver.major
            pnpm_major = pnpm_ver.major
            
            for node_maj, compatible_pnpm in compatibility_rules:
                if node_major == node_maj:
                    if pnpm_major in compatible_pnpm:
                        self.info.append(f"Node.js {node_major}.x 与 PNPM {pnpm_major}.x 兼容性良好")
                        return True
                    else:
                        self.warnings.append(f"Node.js {node_major}.x 与 PNPM {pnpm_major}.x 可能存在兼容性问题")
                        return False
            
            # 对于未知组合，给出警告但不阻止
            self.warnings.append(f"Node.js {node_major}.x 与 PNPM {pnpm_major}.x 的兼容性未经验证")
            return True
            
        except ValueError as e:
            self.errors.append(f"版本兼容性检查失败: {str(e)}")
            return False
    
    def validate_resource_config(self, resource_type: str, value: str, unit: str = None) -> bool:
        """
        验证资源配置合理性
        
        Args:
            resource_type: 资源类型 ('cpu' 或 'memory')
            value: 资源值
            unit: 资源单位 (可选)
            
        Returns:
            bool: 验证是否通过
        """
        if not value:
            self.errors.append(f"{resource_type}资源配置不能为空")
            return False
        
        try:
            if resource_type.lower() == 'cpu':
                return self._validate_cpu_resource(value, unit)
            elif resource_type.lower() == 'memory':
                return self._validate_memory_resource(value, unit)
            else:
                self.errors.append(f"不支持的资源类型: {resource_type}")
                return False
        except Exception as e:
            self.errors.append(f"资源配置验证失败: {str(e)}")
            return False
    
    def _validate_cpu_resource(self, value: str, unit: str = None) -> bool:
        """验证CPU资源配置"""
        # 解析CPU值和单位
        if isinstance(value, (int, float)):
            millicores = int(value * 1000)
            display_value = f"{value}核"
        elif value.endswith('m'):
            millicores = int(value[:-1])
            display_value = value
        elif value.endswith('cores') or value.endswith('core'):
            cores = float(value.replace('cores', '').replace('core', '').strip())
            millicores = int(cores * 1000)
            display_value = f"{cores}核"
        else:
            try:
                cores = float(value)
                millicores = int(cores * 1000)
                display_value = f"{cores}核"
            except ValueError:
                self.errors.append(f"无效的CPU配置格式: {value}")
                return False
        
        # 检查范围
        limits = self.resource_limits['cpu']
        
        if millicores < limits['min_millicores']:
            self.errors.append(f"CPU配置过低: {display_value}，最低要求: {limits['min_millicores']}m")
            return False
        
        if millicores > limits['max_millicores']:
            self.errors.append(f"CPU配置过高: {display_value}，最高限制: {limits['max_millicores']}m")
            return False
        
        if millicores < limits['recommended_min']:
            self.warnings.append(f"CPU配置较低: {display_value}，建议最低: {limits['recommended_min']}m")
        
        if millicores > limits['recommended_max']:
            self.warnings.append(f"CPU配置较高: {display_value}，建议最高: {limits['recommended_max']}m")
        
        self.info.append(f"CPU配置 {display_value} 验证通过")
        return True
    
    def _validate_memory_resource(self, value: str, unit: str = None) -> bool:
        """验证内存资源配置"""
        # 解析内存值和单位
        memory_mb = 0
        display_value = value
        
        if isinstance(value, (int, float)):
            memory_mb = int(value * 1024)  # 假设输入为GB
            display_value = f"{value}GB"
        elif value.endswith('Mi'):
            memory_mb = int(value[:-2])
            display_value = value
        elif value.endswith('Gi'):
            memory_mb = int(float(value[:-2]) * 1024)
            display_value = value
        elif value.endswith('MB') or value.endswith('mb'):
            memory_mb = int(value[:-2])
            display_value = value
        elif value.endswith('GB') or value.endswith('gb'):
            memory_mb = int(float(value[:-2]) * 1024)
            display_value = value
        else:
            try:
                # 尝试解析为数字（默认GB）
                gb = float(value)
                memory_mb = int(gb * 1024)
                display_value = f"{gb}GB"
            except ValueError:
                self.errors.append(f"无效的内存配置格式: {value}")
                return False
        
        # 检查范围
        limits = self.resource_limits['memory']
        
        if memory_mb < limits['min_mb']:
            self.errors.append(f"内存配置过低: {display_value}，最低要求: {limits['min_mb']}MB")
            return False
        
        if memory_mb > limits['max_mb']:
            self.errors.append(f"内存配置过高: {display_value}，最高限制: {limits['max_mb']}MB")
            return False
        
        if memory_mb < limits['recommended_min']:
            self.warnings.append(f"内存配置较低: {display_value}，建议最低: {limits['recommended_min']}MB")
        
        if memory_mb > limits['recommended_max']:
            self.warnings.append(f"内存配置较高: {display_value}，建议最高: {limits['recommended_max']}MB")
        
        self.info.append(f"内存配置 {display_value} 验证通过")
        return True
    
    def validate_port(self, port: Any) -> bool:
        """
        验证端口号配置
        
        Args:
            port: 端口号
            
        Returns:
            bool: 验证是否通过
        """
        try:
            port_num = int(port)
        except (ValueError, TypeError):
            self.errors.append(f"端口号必须为数字: {port}")
            return False
        
        if port_num < 1 or port_num > 65535:
            self.errors.append(f"端口号超出范围: {port_num}，有效范围: 1-65535")
            return False
        
        # 检查端口类型
        if 1 <= port_num <= 1023:
            self.warnings.append(f"端口 {port_num} 为系统保留端口，可能需要管理员权限")
        elif 1024 <= port_num <= 49151:
            self.info.append(f"端口 {port_num} 为注册端口")
        else:
            self.info.append(f"端口 {port_num} 为动态端口")
        
        # 推荐端口范围
        if self.port_ranges['recommended_min'] <= port_num <= self.port_ranges['recommended_max']:
            self.info.append(f"端口 {port_num} 在推荐范围内")
        
        return True
    
    def validate_naming(self, name: str, name_type: str) -> bool:
        """
        验证命名规范
        
        Args:
            name: 名称
            name_type: 名称类型 ('service_name', 'namespace', 'path', 'docker_image')
            
        Returns:
            bool: 验证是否通过
        """
        if not name or not isinstance(name, str):
            self.errors.append(f"{name_type}不能为空")
            return False
        
        if name_type not in self.naming_patterns:
            self.errors.append(f"不支持的命名类型: {name_type}")
            return False
        
        pattern = self.naming_patterns[name_type]
        
        if not re.match(pattern, name):
            self.errors.append(f"{name_type} '{name}' 不符合命名规范")
            return False
        
        # 额外的长度检查
        if name_type in ['service_name', 'namespace']:
            if len(name) > 63:
                self.errors.append(f"{name_type} '{name}' 长度超过63个字符")
                return False
            if len(name) < 3:
                self.warnings.append(f"{name_type} '{name}' 长度较短，建议至少3个字符")
        
        self.info.append(f"{name_type} '{name}' 命名规范验证通过")
        return True
    
    def validate_path(self, path: str, path_type: str = 'general') -> bool:
        """
        验证路径格式和安全性
        
        Args:
            path: 路径字符串
            path_type: 路径类型 ('general', 'dockerfile', 'source_code')
            
        Returns:
            bool: 验证是否通过
        """
        if not path:
            if path_type == 'general':
                # 一般路径可以为空
                return True
            else:
                self.errors.append(f"{path_type}路径不能为空")
                return False
        
        # 安全检查：防止路径穿越
        if '..' in path or path.startswith('/'):
            self.errors.append(f"路径 '{path}' 包含不安全的字符")
            return False
        
        # 检查路径格式
        if not re.match(self.naming_patterns['path'], path):
            self.errors.append(f"路径 '{path}' 包含无效字符")
            return False
        
        # 特定类型的额外检查
        if path_type == 'dockerfile':
            if not path.endswith('.') and not os.path.basename(path).lower() in ['dockerfile', '.']:
                self.warnings.append(f"Dockerfile路径 '{path}' 可能不正确")
        
        if path_type == 'source_code':
            valid_extensions = ['.java', '.js', '.ts', '.py', '.go', '.c', '.cpp', '.h']
            if any(path.endswith(ext) for ext in valid_extensions):
                self.info.append(f"源码路径 '{path}' 格式正确")
        
        self.info.append(f"路径 '{path}' 验证通过")
        return True
    
    def validate_k8s_cluster(self, cluster_name: str) -> bool:
        """
        验证Kubernetes集群名称
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            bool: 验证是否通过
        """
        if not cluster_name:
            self.errors.append("Kubernetes集群名称不能为空")
            return False
        
        # K8s资源名称规范
        if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', cluster_name):
            self.errors.append(f"集群名称 '{cluster_name}' 不符合Kubernetes命名规范")
            return False
        
        if len(cluster_name) > 253:
            self.errors.append(f"集群名称 '{cluster_name}' 长度超过253个字符")
            return False
        
        self.info.append(f"Kubernetes集群名称 '{cluster_name}' 验证通过")
        return True
    
    def validate_ingress_config(self, ingress_enabled: Any) -> bool:
        """
        验证Ingress配置
        
        Args:
            ingress_enabled: Ingress启用状态
            
        Returns:
            bool: 验证是否通过
        """
        if ingress_enabled is None:
            self.warnings.append("Ingress配置为空，将使用默认值")
            return True
        
        valid_values = ['yes', 'no', 'true', 'false', True, False]
        
        if ingress_enabled not in valid_values:
            self.errors.append(f"Ingress配置值无效: {ingress_enabled}。有效值: {valid_values}")
            return False
        
        self.info.append(f"Ingress配置 '{ingress_enabled}' 验证通过")
        return True
    
    def validate_complete_config(self, config: Dict[str, Any], template_type: str = 'maven') -> Dict[str, Any]:
        """
        完整配置验证
        
        Args:
            config: 配置字典
            template_type: 模板类型
            
        Returns:
            Dict: 验证结果
        """
        self.clear_messages()
        
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'info': [],
            'validated_config': config.copy()
        }
        
        # 根据模板类型进行验证
        if template_type == 'maven':
            self._validate_maven_config(config)
        elif template_type == 'npm':
            self._validate_npm_config(config)
        elif template_type == 'deploy':
            self._validate_deploy_config(config)
        
        # 汇总验证结果
        validation_results['errors'] = self.errors.copy()
        validation_results['warnings'] = self.warnings.copy()
        validation_results['info'] = self.info.copy()
        validation_results['is_valid'] = len(self.errors) == 0
        
        return validation_results
    
    def _validate_maven_config(self, config: Dict[str, Any]):
        """验证Maven配置"""
        # JDK版本验证
        if 'JDKVERSION' in config:
            self.validate_jdk_version(config['JDKVERSION'])
        
        # 路径验证
        if 'CODEPATH' in config:
            self.validate_path(config['CODEPATH'], 'source_code')
        
        if 'TARGETDIR' in config:
            self.validate_path(config['TARGETDIR'], 'general')
        
        if 'BUILDDIR' in config:
            self.validate_path(config['BUILDDIR'], 'dockerfile')
        
        # 命名验证
        if 'SERVICENAME' in config:
            self.validate_naming(config['SERVICENAME'], 'service_name')
        
        if 'NAMESPACE' in config:
            self.validate_naming(config['NAMESPACE'], 'namespace')
        
        # 端口验证
        if 'CTPORT' in config:
            self.validate_port(config['CTPORT'])
        
        # 资源验证
        if 'LIMITSCPU' in config:
            self.validate_resource_config('cpu', config['LIMITSCPU'])
        
        if 'LIMITSMEM' in config:
            self.validate_resource_config('memory', config['LIMITSMEM'])
        
        # K8s配置验证
        if 'K8S' in config:
            self.validate_k8s_cluster(config['K8S'])
        
        if 'INGRESS' in config:
            self.validate_ingress_config(config['INGRESS'])
    
    def _validate_npm_config(self, config: Dict[str, Any]):
        """验证NPM配置"""
        # Node.js版本验证
        if 'NODEVERSION' in config:
            self.validate_nodejs_version(config['NODEVERSION'])
        
        # PNPM版本验证
        if 'PNPMVERSION' in config:
            self.validate_pnpm_version(config['PNPMVERSION'])
        
        # 版本兼容性验证
        if 'NODEVERSION' in config and 'PNPMVERSION' in config:
            self.validate_nodejs_pnpm_compatibility(config['NODEVERSION'], config['PNPMVERSION'])
        
        # 路径验证
        if 'CODEPATH' in config:
            self.validate_path(config['CODEPATH'], 'source_code')
        
        if 'NPMDIR' in config:
            self.validate_path(config['NPMDIR'], 'general')
        
        if 'BUILDDIR' in config:
            self.validate_path(config['BUILDDIR'], 'dockerfile')
        
        # 命名验证
        if 'SERVICENAME' in config:
            self.validate_naming(config['SERVICENAME'], 'service_name')
        
        if 'NAMESPACE' in config:
            self.validate_naming(config['NAMESPACE'], 'namespace')
        
        # 端口验证
        if 'CTPORT' in config:
            self.validate_port(config['CTPORT'])
        
        # 资源验证
        if 'REQUESTSCPU' in config:
            self.validate_resource_config('cpu', config['REQUESTSCPU'])
        
        if 'REQUESTSMEM' in config:
            self.validate_resource_config('memory', config['REQUESTSMEM'])
        
        if 'LIMITSCPU' in config:
            self.validate_resource_config('cpu', config['LIMITSCPU'])
        
        if 'LIMITSMEM' in config:
            self.validate_resource_config('memory', config['LIMITSMEM'])
        
        # K8s配置验证
        if 'K8S' in config:
            self.validate_k8s_cluster(config['K8S'])
        
        if 'INGRESS' in config:
            self.validate_ingress_config(config['INGRESS'])
    
    def _validate_deploy_config(self, config: Dict[str, Any]):
        """验证部署配置"""
        # 命名验证
        if 'NAMESPACE' in config:
            self.validate_naming(config['NAMESPACE'], 'namespace')
        
        if 'SERVICENAME' in config:
            self.validate_naming(config['SERVICENAME'], 'service_name')
        
        # 端口验证
        if 'CTPORT' in config:
            self.validate_port(config['CTPORT'])
        
        # 资源验证
        if 'REQUESTSCPU' in config:
            self.validate_resource_config('cpu', config['REQUESTSCPU'])
        
        if 'REQUESTSMEM' in config:
            self.validate_resource_config('memory', config['REQUESTSMEM'])
        
        if 'LIMITSCPU' in config:
            self.validate_resource_config('cpu', config['LIMITSCPU'])
        
        if 'LIMITSMEM' in config:
            self.validate_resource_config('memory', config['LIMITSMEM'])
        
        # K8s配置验证
        if 'K8S' in config:
            self.validate_k8s_cluster(config['K8S'])
        
        if 'INGRESS' in config:
            self.validate_ingress_config(config['INGRESS'])
    
    def get_validation_summary(self) -> str:
        """获取验证结果摘要"""
        total_errors = len(self.errors)
        total_warnings = len(self.warnings)
        total_info = len(self.info)
        
        if total_errors > 0:
            status = "验证失败"
        elif total_warnings > 0:
            status = "验证通过（有警告）"
        else:
            status = "验证通过"
        
        return f"{status} - 错误: {total_errors}, 警告: {total_warnings}, 信息: {total_info}" 