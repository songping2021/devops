// 任务管理模块
class TaskManager {
    constructor() {
        this.taskList = document.querySelector('.task-list');
        this.taskModal = document.getElementById('taskModal');
        this.taskNameInput = document.getElementById('taskName');
        this.taskTypeSelect = document.getElementById('taskType');
        this.confirmTaskBtn = document.getElementById('confirmTask');
        this.cancelTaskBtn = document.getElementById('cancelTask');
        this.addTaskBtn = document.querySelector('.btn-add-task');
        this.currentTaskItem = null;
        this.editingPipelineId = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // 添加任务按钮
        this.addTaskBtn.addEventListener('click', () => {
            this.showAddTaskModal();
        });

        // 确认添加任务
        this.confirmTaskBtn.addEventListener('click', async () => {
            await this.handleConfirmTask();
        });

        // 取消添加任务
        this.cancelTaskBtn.addEventListener('click', () => {
            this.closeTaskModal();
        });

        // 关闭模态框
        document.querySelector('#taskModal .btn-close').addEventListener('click', () => {
            this.closeTaskModal();
        });

        // 任务操作处理
        this.taskList.addEventListener('click', (e) => {
            const target = e.target;
            if (target.classList.contains('edit-task')) {
                const taskItem = target.closest('.task-item');
                this.editTask(taskItem);
            } else if (target.classList.contains('delete-task')) {
                const taskItem = target.closest('.task-item');
                this.deleteTask(taskItem);
            }
        });
    }

    showAddTaskModal() {
        showModal('taskModal');
        this.taskNameInput.value = '';
        this.taskTypeSelect.value = '';
        this.currentTaskItem = null;
    }

    closeTaskModal() {
        hideModal('taskModal');
    }

    async handleConfirmTask() {
        const taskName = this.taskNameInput.value.trim();
        const taskType = this.taskTypeSelect.value;
        const projectIdInput = document.getElementById('projectId');
        const branchInput = document.getElementById('branch');
        const projectId = projectIdInput.value.trim();
        const branchName = branchInput.value.trim();

        if (!taskName || !taskType || !projectId || !branchName) {
            alert('请填写完整信息');
            return;
        }

        try {
            const apiBaseUrl = window.API_BASE_URL || 'http://localhost:5000/api';
            const response = await fetch(`${apiBaseUrl}/pipeline/task`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    projectId,
                    taskName,
                    taskType,
                    branchName
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '添加任务失败');
            }

            const result = await response.json();
            
            if (result.task && result.task.operation) {
                alert(`成功${result.task.operation}任务: ${taskName}`);
            } else {
                alert(`成功创建任务: ${taskName}`);
            }
            
            // 如果是编辑模式，更新现有任务
            if (this.currentTaskItem) {
                this.updateTaskItem(this.currentTaskItem, taskName, taskType);
            } else {
                // 添加新任务到列表
                this.addTaskToList(taskName, taskType);
            }
            
            this.closeTaskModal();
        } catch (error) {
            console.error('任务操作失败:', error);
            alert('任务操作失败: ' + error.message);
        }
    }

    addTaskToList(taskName, taskType) {
        const taskCount = this.taskList.children.length + 1;
        const taskTypeText = getTaskTypeText(taskType);
        const taskId = `task_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
        
        const taskHtml = `
        <div class="task-item" data-task-type="${taskType}" data-task-id="${taskId}">
            <div class="task-header">
                <span class="task-title">任务${taskCount}: ${taskName}</span>
                <span class="task-type-badge">${taskTypeText}</span>
                <div class="task-actions">
                    <button class="btn-icon edit-task">✏️</button>
                    <button class="btn-icon delete-task">❌</button>
                </div>
            </div>
            <div class="stage-list">
                <button class="btn-add-stage">添加阶段</button>
            </div>
        </div>
        `;
        this.taskList.insertAdjacentHTML('beforeend', taskHtml);
        return this.taskList.lastElementChild;
    }

    updateTaskItem(taskItem, taskName, taskType) {
        const taskTitle = taskItem.querySelector('.task-title');
        const taskTypeBadge = taskItem.querySelector('.task-type-badge');
        const taskNumber = taskTitle.textContent.split(':')[0];
        
        taskTitle.textContent = `${taskNumber}: ${taskName}`;
        taskTypeBadge.textContent = getTaskTypeText(taskType);
        taskItem.dataset.taskType = taskType;
    }

    editTask(taskItem) {
        const taskTitle = taskItem.querySelector('.task-title').textContent;
        const taskName = taskTitle.split(': ')[1];
        const taskType = taskItem.dataset.taskType;

        this.taskNameInput.value = taskName;
        this.taskTypeSelect.value = taskType;
        this.currentTaskItem = taskItem;

        showModal('taskModal');
    }

    async deleteTask(taskItem) {
        const taskTitle = taskItem.querySelector('.task-title').textContent;
        const taskName = taskTitle.split(': ')[1];
        const projectIdInput = document.getElementById('projectId');
        const branchInput = document.getElementById('branch');
        const projectId = projectIdInput.value.trim();
        const branch = branchInput.value.trim();
        
        if (confirm(`确定要删除任务"${taskName}"吗？这将同时删除本地和GitLab仓库中的对应文件夹！`)) {
            if (this.editingPipelineId && projectId && branch && taskName) {
                try {
                    await this.deleteTaskFolder(projectId, branch, taskName);
                    taskItem.remove();
                } catch (error) {
                    console.error('删除任务文件夹失败:', error);
                    alert(`界面上已删除任务，但删除文件夹失败: ${error.message}`);
                    taskItem.remove();
                }
            } else {
                taskItem.remove();
            }
        }
    }

    async deleteTaskFolder(projectId, branch, taskName) {
        const apiBaseUrl = window.API_BASE_URL || 'http://localhost:5000/api';
        const response = await fetch(`${apiBaseUrl}/pipeline/task/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                projectId,
                branchName: branch,
                taskName
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '删除任务文件夹失败');
        }
        
        return await response.json();
    }

    setEditingPipelineId(id) {
        this.editingPipelineId = id;
    }

    clearTasks() {
        this.taskList.innerHTML = '';
    }
} 