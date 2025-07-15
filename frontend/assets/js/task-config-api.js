// 任务配置API模块
// 提供任务配置相关的API操作功能

// 获取API基础URL
const getApiBaseUrl = () => window.API_BASE_URL || 'http://localhost:5000/api';

/**
 * 获取任务配置
 * 功能描述：获取指定任务的配置信息
 * 入参：pipelineId (number), taskName (string), options (object)
 * 返回参数：Promise<{config: object}>
 */
async function getTaskConfig(pipelineId, taskName, options = {}) {
    try {
        const queryParams = new URLSearchParams();
        
        if (options.stageType) {
            queryParams.append('stage_type', options.stageType);
        }
        if (options.format) {
            queryParams.append('format', options.format);
        }
        if (options.includeDefaults !== undefined) {
            queryParams.append('include_defaults', options.includeDefaults);
        }
        
        const url = `${getApiBaseUrl()}/task_config/${pipelineId}/${encodeURIComponent(taskName)}${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                return { success: false, error: '任务配置不存在', status: 404 };
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('获取任务配置失败:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 更新Maven配置
 * 功能描述：更新Maven项目的配置参数
 * 入参：configData (object)
 * 返回参数：Promise<{success: boolean}>
 */
async function updateMavenConfig(configData) {
    try {
        console.log('=== Maven配置API调用 ===');
        console.log('发送的数据:', JSON.stringify(configData, null, 2));
        console.log('数据类型:', typeof configData);
        console.log('stage_configs类型:', typeof configData.stage_configs);
        console.log('stage_configs内容:', configData.stage_configs);
        
        const response = await fetch(`${getApiBaseUrl()}/task_config/maven_config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });

        console.log('响应状态:', response.status);
        console.log('响应头:', Object.fromEntries(response.headers.entries()));

        if (!response.ok) {
            const errorText = await response.text();
            console.log('错误响应内容:', errorText);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('成功响应:', data);
        return { success: true, data };
    } catch (error) {
        console.error('更新Maven配置失败:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 更新NPM配置
 * 功能描述：更新NPM项目的配置参数
 * 入参：configData (object)
 * 返回参数：Promise<{success: boolean}>
 */
async function updateNpmConfig(configData) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/task_config/npm_config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('更新NPM配置失败:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 更新部署配置
 * 功能描述：更新部署阶段的配置参数
 * 入参：configData (object)
 * 返回参数：Promise<{success: boolean}>
 */
async function updateDeployConfig(configData) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/task_config/deploy_config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('更新部署配置失败:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 阶段开关控制
 * 功能描述：控制compile、build、deploy三个阶段的启用/禁用状态
 * 入参：toggleData (object)
 * 返回参数：Promise<{success: boolean}>
 */
async function toggleStage(toggleData) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/task_config/stage_toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(toggleData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('阶段开关控制失败:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 获取阶段状态
 * 功能描述：获取所有阶段的启用/禁用状态
 * 入参：projectId (string), branch (string), taskName (string)
 * 返回参数：Promise<{stages: object}>
 */
async function getStageStatus(projectId, branch, taskName) {
    try {
        const queryParams = new URLSearchParams({
            project_id: projectId,
            branch: branch || 'develop',
            task_name: taskName
        });
        
        const url = `${getApiBaseUrl()}/task_config/stage_status?${queryParams.toString()}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('获取阶段状态失败:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 批量更新配置
 * 功能描述：批量更新任务的所有阶段配置
 * 入参：configData (object)
 * 返回参数：Promise<{success: boolean}>
 */
async function batchUpdateConfig(configData) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/task_config/batch_update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('批量更新配置失败:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 获取配置模板
 * 功能描述：获取可用的配置模板列表
 * 入参：templateType (string, optional)
 * 返回参数：Promise<{templates: Array}>
 */
async function getConfigTemplates(templateType) {
    try {
        const queryParams = new URLSearchParams();
        
        if (templateType) {
            queryParams.append('template_type', templateType);
        }
        
        const url = `${getApiBaseUrl()}/task_config/templates${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return { success: true, data };
    } catch (error) {
        console.error('获取配置模板失败:', error);
        return { success: false, error: error.message };
    }
}

/**
 * 根据项目信息构建配置参数
 * 功能描述：从项目ID和分支信息构建配置参数对象
 * 入参：projectId (string), branch (string), taskName (string), stageType (string), configData (object)
 * 返回参数：object - 完整的配置参数对象
 */
function buildConfigParams(projectId, branch, taskName, stageType, configData) {
    return {
        project_id: projectId,
        branch: branch || 'develop',
        task_name: taskName,
        stage_configs: {
            [stageType]: configData
        },
        sync_to_gitlab: true
    };
}

/**
 * 统一的配置保存方法
 * 功能描述：根据任务类型选择合适的API进行配置保存
 * 入参：taskType (string), projectId (string), branch (string), taskName (string), stageType (string), configData (object)
 * 返回参数：Promise<{success: boolean}>
 */
async function saveStageConfiguration(taskType, projectId, branch, taskName, stageType, configData) {
    try {
        // 将前端表单字段映射到后端API期望的字段名
        let mappedConfig = {};
        
        if (stageType === 'compile') {
            if (taskType === 'npm') {
                // NPM编译阶段字段映射
                mappedConfig = {
                    NODEVERSION: configData.nodeVersion || '14.18',
                    PNPMVERSION: configData.pnpmVersion || '7.33.7',
                    CODEPATH: configData.codePath || '',
                    NPMDIR: configData.distPath || 'dist',
                    BUILDCMD: configData.buildCommand || 'pnpm run build'
                };
            } else {
                // Maven编译阶段字段映射
                console.log('Maven编译阶段字段映射 - 原始configData:', configData);
                mappedConfig = {
                    JDKVERSION: configData.jdkVersion || '8',
                    CODEPATH: configData.codePath || '',
                    TARGETDIR: configData.artifactPath || 'target',
                    BUILDFORMAT: configData.artifactFormat || 'jar',
                    BUILDCMD: configData.buildCommand || 'mvn clean package -Dmaven.test.skip=true -U'
                };
                console.log('Maven编译阶段字段映射 - 映射后mappedConfig:', mappedConfig);
            }
        } else if (stageType === 'build') {
            // 构建阶段字段映射
            mappedConfig = {
                HARBORNAME: configData.repository || 'devops',
                BUILDDIR: configData.dockerfilePath || '.',
                PLATFORM: configData.architecture ? `linux/${configData.architecture}` : 'linux/amd64',
                SERVICENAME: configData.serviceName || '$CI_PROJECT_NAME'
            };
        } else if (stageType === 'deploy') {
            // 部署阶段字段映射
            mappedConfig = {
                NAMESPACE: configData.namespace || 'app-dev',
                SERVICENAME: configData.serviceName || '$CI_PROJECT_NAME',
                CTPORT: parseInt(configData.port) || 80,
                K8S: configData.cluster || 'K8S_cmdicncf_jkyw',
                INGRESS: configData.enableIngress ? 'yes' : 'no',
                LIMITSCPU: configData.cpu ? `${parseInt(configData.cpu) * 1000}m` : '1000m',
                LIMITSMEM: configData.memory ? `${parseInt(configData.memory) * 1024}Mi` : '1024Mi'
            };
        }
        
        if (stageType === 'compile') {
            if (taskType === 'npm') {
                const params = {
                    project_id: projectId,
                    branch: branch || 'develop',
                    task_name: taskName,
                    stage_configs: { compile: mappedConfig },
                    sync_to_gitlab: true
                };
                return await updateNpmConfig(params);
            } else {
                const params = {
                    project_id: projectId,
                    branch: branch || 'develop',
                    task_name: taskName,
                    stage_configs: { compile: mappedConfig },
                    sync_to_gitlab: true
                };
                console.log('调用updateMavenConfig的参数:', params);
                const result = await updateMavenConfig(params);
                console.log('updateMavenConfig返回结果:', result);
                return result;
            }
        } else if (stageType === 'deploy') {
            // 修复部署配置的数据格式
            const params = {
                project_id: projectId,
                branch: branch || 'develop',
                task_name: taskName,
                template_type: taskType,
                deploy_config: mappedConfig,  // 注意：这里是deploy_config，不是stage_configs
                sync_to_gitlab: true
            };
            return await updateDeployConfig(params);
        } else {
            // 对于构建阶段，使用批量更新API
            return await batchUpdateConfig({
                project_id: projectId,
                branch: branch || 'develop',
                task_name: taskName,
                template_type: taskType,
                stage_config: {
                    [stageType]: {
                        enabled: true,
                        config: mappedConfig
                    }
                },
                sync_to_gitlab: true
            });
        }
    } catch (error) {
        console.error('保存阶段配置失败:', error);
        return { success: false, error: error.message };
    }
}

// 将函数暴露到全局作用域，以便其他模块使用
window.TaskConfigAPI = {
    getTaskConfig,
    updateMavenConfig,
    updateNpmConfig,
    updateDeployConfig,
    toggleStage,
    getStageStatus,
    batchUpdateConfig,
    getConfigTemplates,
    buildConfigParams,
    saveStageConfiguration
};
