#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any
import sys
import os

# 添加后端路径到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.config_validator import ConfigValidator

# 创建Blueprint
validation_bp = Blueprint('config_validation', __name__)


@validation_bp.route('/api/config_validation/validate', methods=['POST'])
def validate_config():
    """
    配置参数验证API
    
    请求参数:
    {
        "config": {配置参数字典},
        "template_type": "模板类型(maven/npm/deploy)",
        "validation_level": "验证级别(strict/normal/lenient)"
    }
    
    返回:
    {
        "success": true/false,
        "is_valid": true/false,
        "validation_result": {
            "errors": ["错误信息列表"],
            "warnings": ["警告信息列表"],
            "info": ["信息列表"],
            "summary": "验证摘要"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        config = data.get('config', {})
        template_type = data.get('template_type', 'maven')
        validation_level = data.get('validation_level', 'normal')
        
        if not config:
            return jsonify({
                'success': False,
                'message': '配置参数不能为空'
            }), 400
        
        if template_type not in ['maven', 'npm', 'deploy']:
            return jsonify({
                'success': False,
                'message': f'不支持的模板类型: {template_type}'
            }), 400
        
        # 创建验证器
        validator = ConfigValidator()
        
        # 执行验证
        validation_result = validator.validate_complete_config(config, template_type)
        
        # 根据验证级别调整结果
        if validation_level == 'lenient':
            # 宽松模式：只有错误才算失败
            validation_result['is_valid'] = len(validation_result['errors']) == 0
        elif validation_level == 'strict':
            # 严格模式：有警告也算失败
            validation_result['is_valid'] = (len(validation_result['errors']) == 0 and 
                                           len(validation_result['warnings']) == 0)
        # normal模式保持默认逻辑
        
        # 添加摘要信息
        validation_result['summary'] = validator.get_validation_summary()
        
        return jsonify({
            'success': True,
            'is_valid': validation_result['is_valid'],
            'validation_result': validation_result
        })
        
    except Exception as e:
        current_app.logger.error(f"配置验证失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'配置验证失败: {str(e)}'
        }), 500


@validation_bp.route('/api/config_validation/validate_single', methods=['POST'])
def validate_single_parameter():
    """
    单个参数验证API
    
    请求参数:
    {
        "parameter_name": "参数名称",
        "parameter_value": "参数值",
        "validation_type": "验证类型(jdk_version/nodejs_version/pnpm_version/resource/port/naming/path)"
    }
    
    返回:
    {
        "success": true/false,
        "is_valid": true/false,
        "validation_result": {
            "errors": ["错误信息列表"],
            "warnings": ["警告信息列表"],
            "info": ["信息列表"]
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        parameter_name = data.get('parameter_name')
        parameter_value = data.get('parameter_value')
        validation_type = data.get('validation_type')
        
        if not all([parameter_name, validation_type]):
            return jsonify({
                'success': False,
                'message': '参数名称和验证类型不能为空'
            }), 400
        
        # 创建验证器
        validator = ConfigValidator()
        
        # 根据验证类型执行相应验证
        is_valid = False
        
        if validation_type == 'jdk_version':
            is_valid = validator.validate_jdk_version(parameter_value)
        elif validation_type == 'nodejs_version':
            is_valid = validator.validate_nodejs_version(parameter_value)
        elif validation_type == 'pnpm_version':
            is_valid = validator.validate_pnpm_version(parameter_value)
        elif validation_type == 'port':
            is_valid = validator.validate_port(parameter_value)
        elif validation_type == 'cpu_resource':
            is_valid = validator.validate_resource_config('cpu', parameter_value)
        elif validation_type == 'memory_resource':
            is_valid = validator.validate_resource_config('memory', parameter_value)
        elif validation_type == 'service_name':
            is_valid = validator.validate_naming(parameter_value, 'service_name')
        elif validation_type == 'namespace':
            is_valid = validator.validate_naming(parameter_value, 'namespace')
        elif validation_type == 'path':
            path_type = data.get('path_type', 'general')
            is_valid = validator.validate_path(parameter_value, path_type)
        elif validation_type == 'k8s_cluster':
            is_valid = validator.validate_k8s_cluster(parameter_value)
        elif validation_type == 'ingress':
            is_valid = validator.validate_ingress_config(parameter_value)
        else:
            return jsonify({
                'success': False,
                'message': f'不支持的验证类型: {validation_type}'
            }), 400
        
        return jsonify({
            'success': True,
            'is_valid': is_valid,
            'validation_result': {
                'errors': validator.errors,
                'warnings': validator.warnings,
                'info': validator.info
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"参数验证失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'参数验证失败: {str(e)}'
        }), 500


@validation_bp.route('/api/config_validation/compatibility_check', methods=['POST'])
def check_compatibility():
    """
    版本兼容性检查API
    
    请求参数:
    {
        "nodejs_version": "Node.js版本",
        "pnpm_version": "PNPM版本"
    }
    
    返回:
    {
        "success": true/false,
        "is_compatible": true/false,
        "compatibility_result": {
            "errors": ["错误信息列表"],
            "warnings": ["警告信息列表"],
            "info": ["信息列表"]
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        nodejs_version = data.get('nodejs_version')
        pnpm_version = data.get('pnpm_version')
        
        if not all([nodejs_version, pnpm_version]):
            return jsonify({
                'success': False,
                'message': 'Node.js版本和PNPM版本不能为空'
            }), 400
        
        # 创建验证器
        validator = ConfigValidator()
        
        # 先验证单个版本
        nodejs_valid = validator.validate_nodejs_version(nodejs_version)
        pnpm_valid = validator.validate_pnpm_version(pnpm_version)
        
        # 然后检查兼容性
        is_compatible = False
        if nodejs_valid and pnpm_valid:
            is_compatible = validator.validate_nodejs_pnpm_compatibility(nodejs_version, pnpm_version)
        
        return jsonify({
            'success': True,
            'is_compatible': is_compatible,
            'compatibility_result': {
                'errors': validator.errors,
                'warnings': validator.warnings,
                'info': validator.info
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"兼容性检查失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'兼容性检查失败: {str(e)}'
        }), 500


@validation_bp.route('/api/config_validation/resource_calculator', methods=['POST'])
def calculate_resources():
    """
    资源配置计算器API
    
    请求参数:
    {
        "cpu_cores": "CPU核心数",
        "memory_gb": "内存GB数"
    }
    
    返回:
    {
        "success": true/false,
        "calculated_resources": {
            "cpu_millicores": "CPU毫核数",
            "memory_mi": "内存Mi数",
            "recommendations": ["推荐配置列表"]
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        cpu_cores = data.get('cpu_cores', 0)
        memory_gb = data.get('memory_gb', 0)
        
        try:
            cpu_cores = float(cpu_cores)
            memory_gb = float(memory_gb)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'CPU核心数和内存GB数必须为数字'
            }), 400
        
        # 计算资源配置
        cpu_millicores = int(cpu_cores * 1000)
        memory_mi = int(memory_gb * 1024)
        
        # 生成推荐配置
        recommendations = []
        
        validator = ConfigValidator()
        limits = validator.resource_limits
        
        # CPU推荐
        if cpu_millicores < limits['cpu']['recommended_min']:
            recommendations.append(f"建议CPU配置至少 {limits['cpu']['recommended_min']}m (0.1核)")
        elif cpu_millicores > limits['cpu']['recommended_max']:
            recommendations.append(f"CPU配置较高，请确认是否需要 {cpu_millicores}m ({cpu_cores}核)")
        else:
            recommendations.append(f"CPU配置 {cpu_millicores}m ({cpu_cores}核) 合理")
        
        # 内存推荐
        if memory_mi < limits['memory']['recommended_min']:
            recommendations.append(f"建议内存配置至少 {limits['memory']['recommended_min']}Mi (128MB)")
        elif memory_mi > limits['memory']['recommended_max']:
            recommendations.append(f"内存配置较高，请确认是否需要 {memory_mi}Mi ({memory_gb}GB)")
        else:
            recommendations.append(f"内存配置 {memory_mi}Mi ({memory_gb}GB) 合理")
        
        # 添加K8s资源配置建议
        if cpu_cores <= 1 and memory_gb <= 1:
            recommendations.append("适合轻量级应用或测试环境")
        elif cpu_cores <= 4 and memory_gb <= 8:
            recommendations.append("适合中等规模应用")
        else:
            recommendations.append("适合大型应用或高负载环境")
        
        return jsonify({
            'success': True,
            'calculated_resources': {
                'cpu_millicores': cpu_millicores,
                'memory_mi': memory_mi,
                'cpu_formatted': f"{cpu_millicores}m",
                'memory_formatted': f"{memory_mi}Mi",
                'recommendations': recommendations
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"资源计算失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'资源计算失败: {str(e)}'
        }), 500


@validation_bp.route('/api/config_validation/validation_rules', methods=['GET'])
def get_validation_rules():
    """
    获取验证规则信息API
    
    返回:
    {
        "success": true,
        "validation_rules": {
            "supported_jdk_versions": ["支持的JDK版本列表"],
            "nodejs_compatibility": "Node.js兼容性信息",
            "pnpm_compatibility": "PNPM兼容性信息",
            "resource_limits": "资源限制信息",
            "port_ranges": "端口范围信息",
            "naming_patterns": "命名规范信息"
        }
    }
    """
    try:
        validator = ConfigValidator()
        
        return jsonify({
            'success': True,
            'validation_rules': {
                'supported_jdk_versions': validator.supported_jdk_versions,
                'nodejs_compatibility': validator.nodejs_compatibility,
                'pnpm_compatibility': validator.pnpm_compatibility,
                'resource_limits': validator.resource_limits,
                'port_ranges': validator.port_ranges,
                'naming_patterns': validator.naming_patterns
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取验证规则失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取验证规则失败: {str(e)}'
        }), 500 