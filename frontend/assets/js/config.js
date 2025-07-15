// API基础URL
const API_BASE_URL = 'http://localhost:5000/api';

// 格式化任务显示
function formatTasksForDisplay(tasksJson) {
    try {
        const tasks = JSON.parse(tasksJson);
        return tasks.map(task => task.name).join(', ');
    } catch (e) {
        return tasksJson || '';
    }
}

// 格式化阶段显示
function formatStagesForDisplay(stagesJson) {
    try {
        const stages = JSON.parse(stagesJson);
        return stages.map(stage => stage.name).join(', ');
    } catch (e) {
        return stagesJson || '';
    }
}

// 获取任务类型显示文本
function getTaskTypeText(taskType) {
    const taskTypes = {
        'maven': 'Maven打包发布',
        'npm': 'NPM打包发布',
        'scan': '代码扫描'
    };
    return taskTypes[taskType] || taskType;
}

// 获取阶段标题
function getStageTitle(stageType) {
    const stageTitles = {
        'compile': '编译',
        'build': '构建',
        'deploy': '部署'
    };
    return stageTitles[stageType] || stageType;
}

// 获取阶段类型
function getStageType(stageName) {
    const stageTypes = {
        '编译阶段': 'compile',
        '构建阶段': 'build',
        '部署阶段': 'deploy',
        '编译': 'compile',
        '构建': 'build',
        '部署': 'deploy'
    };
    return stageTypes[stageName] || 'unknown';
}

// 模态框显示/隐藏
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('active');
    if (modalId === 'stageModal' || modalId === 'taskModal') {
        modal.style.display = 'flex';
    } else {
        modal.style.display = 'block';
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('active');
    modal.style.display = 'none';
} 