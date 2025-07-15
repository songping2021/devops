// 主入口文件
// 初始化应用并加载所有必要的模块

// 确保API_BASE_URL全局可用
window.API_BASE_URL = window.API_BASE_URL || 'http://localhost:5000/api';

// 导入API模块
import { 
    getPipelineList, 
    searchPipelinesByProject, 
    deletePipeline, 
    executePipeline 
} from './pipeline-api.js';

// 导入工具函数
import { 
    formatDateDisplay, 
    parseTaskDisplay,
    showConfirmDialog,
    showMessage 
} from './utils.js';

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 加载流水线数据
    loadPipelines();
    
    // 绑定事件监听器
    bindEventListeners();
});

/**
 * 加载流水线数据
 * 功能描述：从API获取流水线列表并更新页面显示
 * 入参：无
 * 返回参数：无
 */
async function loadPipelines() {
    try {
        const data = await getPipelineList();
        
        if (data.pipelines) {
            updateTableWithPipelines(data.pipelines);
        }
    } catch (error) {
        console.error('加载流水线数据失败:', error);
        showMessage('加载流水线数据失败，请检查网络连接或联系管理员', 'error');
    }
}

// 更新表格数据
function updateTableWithPipelines(pipelines) {
    const tableBody = document.getElementById('pipelineTableBody');
    if (pipelines.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">暂无数据</td></tr>';
        return;
    }
    
    tableBody.innerHTML = pipelines.map(pipeline => `
        <tr>
            <td><input type="checkbox"></td>
            <td>${pipeline.project_id || ''}</td>
            <td>${pipeline.branch || ''}</td>
            <td>${getTaskName(pipeline.task)}</td>
            <td>${pipeline.stage || ''}</td>
            <td>${formatDate(pipeline.updated_at)}</td>
            <td>${pipeline.updated_by || ''}</td>
            <td>
                <button class="btn-execute" onclick="executePipelineHandler(${pipeline.id})">执行</button>
                <button class="btn-edit" onclick="editPipeline(${pipeline.id})">修改</button>
                <button class="btn-delete" onclick="deletePipelineHandler(${pipeline.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

// 格式化日期（使用工具函数）
function formatDate(dateString) {
    return formatDateDisplay(dateString);
}

// 获取任务名称（使用工具函数）
function getTaskName(taskString) {
    return parseTaskDisplay(taskString);
}

// 绑定事件监听器
function bindEventListeners() {
    // 搜索按钮点击事件
    document.querySelector('.btn-search').addEventListener('click', function() {
        const projectId = document.getElementById('projectId').value.trim();
        searchPipelines(projectId);
    });

    // 重置按钮点击事件
    document.querySelector('.btn-reset').addEventListener('click', function() {
        document.getElementById('projectId').value = '';
        loadPipelines();
    });

    // 新建按钮点击事件
    document.getElementById('newPipeline').addEventListener('click', function() {
        window.location.href = 'pipeline-edit.html';
    });
}

/**
 * 搜索流水线
 * 功能描述：根据项目ID搜索流水线
 * 入参：projectId (string)
 * 返回参数：无
 */
async function searchPipelines(projectId) {
    if (!projectId) {
        showMessage('请输入项目ID', 'warning');
        return;
    }
    
    try {
        const data = await searchPipelinesByProject(projectId);
        
        if (data.pipelines) {
            // 客户端过滤，实际上应该在服务端处理
            const filteredPipelines = data.pipelines.filter(pipeline => 
                pipeline.project_id.toLowerCase().includes(projectId.toLowerCase())
            );
            updateTableWithPipelines(filteredPipelines);
        }
    } catch (error) {
        console.error('搜索流水线失败:', error);
        showMessage('搜索失败，请检查网络连接或联系管理员', 'error');
    }
}

/**
 * 执行流水线
 * 功能描述：启动指定流水线的执行
 * 入参：id (number)
 * 返回参数：无
 */
async function executePipelineHandler(id) {
    try {
        const result = await executePipeline(id);
        showMessage(result.message || `开始执行流水线 ${id}`, 'success');
        console.log('流水线执行启动:', result);
    } catch (error) {
        console.error('执行流水线失败:', error);
        showMessage('执行失败，请检查网络连接或联系管理员', 'error');
    }
}

// 编辑流水线
function editPipeline(id) {
    window.location.href = `pipeline-edit.html?id=${id}`;
}

/**
 * 删除流水线
 * 功能描述：删除指定的流水线及相关资源
 * 入参：id (number)
 * 返回参数：无
 */
async function deletePipelineHandler(id) {
    if (showConfirmDialog('确定要删除这个流水线吗？这将同时删除本地文件夹和GitLab仓库项目！')) {
        try {
            const result = await deletePipeline(id);
            showMessage(result.message || '删除成功', 'success');
            loadPipelines(); // 重新加载列表
        } catch (error) {
            console.error('删除流水线失败:', error);
            showMessage('删除失败，请检查网络连接或联系管理员', 'error');
        }
    }
}

// 分页相关函数
function changePage(page) {
    console.log('切换到页码:', page);
    // 这里可以添加分页逻辑
}

// 将函数添加到全局作用域，以便HTML中的onclick可以访问
window.executePipelineHandler = executePipelineHandler;
window.editPipeline = editPipeline;
window.deletePipelineHandler = deletePipelineHandler;
window.changePage = changePage; 