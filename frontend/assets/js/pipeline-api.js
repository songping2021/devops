// 流水线API模块
// 提供流水线相关的API操作功能

// 获取API基础URL
const getApiBaseUrl = () => window.API_BASE_URL || 'http://localhost:5000/api';

/**
 * 获取流水线列表
 * 功能描述：从服务器获取所有流水线数据
 * 入参：无
 * 返回参数：Promise<{pipelines: Array}>
 */
export async function getPipelineList() {
    try {
        const response = await fetch(`${getApiBaseUrl()}/pipelines`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('获取流水线列表失败:', error);
        throw error;
    }
}

/**
 * 根据项目ID搜索流水线
 * 功能描述：根据项目ID查询匹配的流水线
 * 入参：projectId (string) - 项目ID
 * 返回参数：Promise<{pipelines: Array}>
 */
export async function searchPipelinesByProject(projectId) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/pipelines/search?project_id=${encodeURIComponent(projectId)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('搜索流水线失败:', error);
        throw error;
    }
}

/**
 * 执行流水线
 * 功能描述：启动指定流水线的执行
 * 入参：pipelineId (number) - 流水线ID
 * 返回参数：Promise<{success: boolean, message: string}>
 */
export async function executePipeline(pipelineId) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/pipelines/${pipelineId}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('执行流水线失败:', error);
        throw error;
    }
}

/**
 * 删除流水线
 * 功能描述：删除指定的流水线及相关资源
 * 入参：pipelineId (number) - 流水线ID
 * 返回参数：Promise<{success: boolean, message: string}>
 */
export async function deletePipeline(pipelineId) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/pipelines/${pipelineId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('删除流水线失败:', error);
        throw error;
    }
}

/**
 * 创建新流水线
 * 功能描述：创建一个新的流水线
 * 入参：pipelineData (object) - 流水线配置数据
 * 返回参数：Promise<{success: boolean, pipeline: object}>
 */
export async function createPipeline(pipelineData) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/pipelines`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pipelineData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('创建流水线失败:', error);
        throw error;
    }
}

/**
 * 更新流水线
 * 功能描述：更新现有流水线的配置
 * 入参：pipelineId (number) - 流水线ID, pipelineData (object) - 更新的配置数据
 * 返回参数：Promise<{success: boolean, pipeline: object}>
 */
export async function updatePipeline(pipelineId, pipelineData) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/pipelines/${pipelineId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pipelineData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('更新流水线失败:', error);
        throw error;
    }
}

/**
 * 获取单个流水线详情
 * 功能描述：根据ID获取流水线的详细信息
 * 入参：pipelineId (number) - 流水线ID
 * 返回参数：Promise<{pipeline: object}>
 */
export async function getPipelineById(pipelineId) {
    try {
        const response = await fetch(`${getApiBaseUrl()}/pipelines/${pipelineId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('获取流水线详情失败:', error);
        throw error;
    }
} 