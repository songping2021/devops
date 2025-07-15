// 流水线数据加载模块
class PipelineLoader {
    constructor() {
        this.editingPipelineId = null;
    }

    async loadPipelineData(id, taskManager, stageManager) {
        try {
            const apiBaseUrl = window.API_BASE_URL || 'http://localhost:5000/api';
            const response = await fetch(`${apiBaseUrl}/pipelines/${id}`);
            if (!response.ok) {
                throw new Error('获取流水线数据失败');
            }
            const data = await response.json();
            console.log('加载的流水线数据:', data);
            
            if (data.pipeline) {
                // 填充基本信息
                const projectIdInput = document.getElementById('projectId');
                const branchInput = document.getElementById('branch');
                projectIdInput.value = data.pipeline.project_id || '';
                branchInput.value = data.pipeline.branch || 'develop';
                
                // 清空现有任务列表
                taskManager.clearTasks();
                
                // 尝试使用新的API获取任务和阶段数据
                try {
                    const tasksResponse = await fetch(`${apiBaseUrl}/pipelines/${id}/tasks`);
                    if (tasksResponse.ok) {
                        const tasksData = await tasksResponse.json();
                        console.log('使用新API加载的任务数据:', tasksData);
                        
                        if (tasksData.tasks && tasksData.tasks.length > 0) {
                            this.loadTasksWithNewAPI(tasksData.tasks, taskManager);
                            return;
                        }
                    }
                } catch (e) {
                    console.warn('使用新API加载任务数据失败，将使用旧格式:', e);
                }
                
                // 如果新API失败或没有数据，使用旧方式处理
                this.loadTasksWithOldAPI(data.pipeline, taskManager);
                
                // 加载触发方式
                this.loadTriggerConfig(data.pipeline);
                
                // 加载成员信息
                this.loadMemberInfo(data.pipeline);
            }
        } catch (error) {
            console.error('加载流水线数据失败:', error);
            alert('加载流水线数据失败，请检查网络连接或联系管理员');
        }
    }

    loadTasksWithNewAPI(tasks, taskManager) {
        tasks.forEach(task => {
            const taskItem = taskManager.addTaskToList(task.name, task.type);
            
            if (task.id) {
                taskItem.dataset.taskId = task.id;
            }
            
            if (task.stages && task.stages.length > 0) {
                const stageList = taskItem.querySelector('.stage-list');
                task.stages.forEach((stage, stageIndex) => {
                    const stageId = stage.id || `stage_loaded_${Date.now()}_${stageIndex}`;
                    const stageHtml = `
                        <div class="stage-item" data-stage-type="${stage.type}" data-stage-id="${stageId}">
                            ${getStageTitle(stage.type)}
                        </div>
                    `;
                    const addStageBtn = stageList.querySelector('.btn-add-stage');
                    addStageBtn.insertAdjacentHTML('beforebegin', stageHtml);
                    
                    const stageElement = addStageBtn.previousElementSibling;
                    if (stage.config) {
                        stageElement.dataset.stageConfig = JSON.stringify(stage.config);
                        console.log(`加载阶段配置 - 任务: ${task.name}, 阶段: ${stage.type}`, stage.config);
                    } else {
                        console.log(`阶段无配置数据 - 任务: ${task.name}, 阶段: ${stage.type}`);
                    }
                });
            }
        });
    }

    loadTasksWithOldAPI(pipeline, taskManager) {
        let tasksData = [];
        if (pipeline.task) {
            try {
                tasksData = JSON.parse(pipeline.task);
                if (!Array.isArray(tasksData)) {
                    tasksData = [{name: pipeline.task, type: 'maven', stages: []}];
                }
            } catch (e) {
                tasksData = pipeline.task.split(',').map(task => ({
                    name: task.trim(),
                    type: 'maven',
                    stages: []
                }));
            }
        }

        if (tasksData.length === 0) {
            tasksData = [{name: '默认任务', type: 'maven', stages: []}];
        }

        if (pipeline.stage) {
            let stages = [];
            try {
                stages = JSON.parse(pipeline.stage);
                if (!Array.isArray(stages)) {
                    stages = [{type: pipeline.stage, name: pipeline.stage}];
                }
            } catch (e) {
                stages = pipeline.stage.split(',').map(stage => ({
                    type: stage.trim(),
                    name: stage.trim()
                }));
            }

            if (tasksData.length === 1) {
                tasksData[0].stages = stages || [];
            } else {
                if (stages && stages.length > 0) {
                    stages.forEach((stage, index) => {
                        const taskIndex = index % tasksData.length;
                        if (!tasksData[taskIndex].stages) {
                            tasksData[taskIndex].stages = [];
                        }
                        tasksData[taskIndex].stages.push(stage);
                    });
                } else {
                    tasksData.forEach(task => {
                        if (!task.stages) {
                            task.stages = [];
                        }
                    });
                }
            }
        }

        tasksData.forEach((task, index) => {
            if (!task.id) {
                task.id = `task_old_${Date.now()}_${index}`;
            }
            
            const taskItem = taskManager.addTaskToList(task.name, task.type || 'maven');
            
            if (task.id) {
                taskItem.dataset.taskId = task.id;
            }
            
            if (task.stages && task.stages.length > 0) {
                const stageList = taskItem.querySelector('.stage-list');
                task.stages.forEach((stage, stageIndex) => {
                    if (stage.type && stage.type !== 'undefined' && stage.type !== 'unknown') {
                        const stageId = stage.id || `stage_old_${Date.now()}_${stageIndex}`;
                        const stageHtml = `
                            <div class="stage-item" data-stage-type="${stage.type}" data-stage-id="${stageId}">
                                ${getStageTitle(stage.type)}
                            </div>
                        `;
                        const addStageBtn = stageList.querySelector('.btn-add-stage');
                        addStageBtn.insertAdjacentHTML('beforebegin', stageHtml);
                        
                        const stageElement = addStageBtn.previousElementSibling;
                        if (stage.config) {
                            stageElement.dataset.stageConfig = JSON.stringify(stage.config);
                            console.log(`加载旧格式阶段配置 - 任务: ${task.name}, 阶段: ${stage.type}`, stage.config);
                        } else {
                            console.log(`旧格式阶段无配置数据 - 任务: ${task.name}, 阶段: ${stage.type}`);
                        }
                    }
                });
            }
        });
    }

    loadTriggerConfig(pipeline) {
        if (pipeline.trigger_type) {
            const triggerRadio = document.querySelector(`input[name="triggerType"][value="${pipeline.trigger_type}"]`);
            if (triggerRadio) {
                triggerRadio.checked = true;
                triggerRadio.dispatchEvent(new Event('change'));
            }
        }
    }

    loadMemberInfo(pipeline) {
        if (pipeline.members) {
            let members = [];
            try {
                members = JSON.parse(pipeline.members);
            } catch (e) {
                members = [{name: '管理员', role: '所有权限'}];
            }

            const memberList = document.querySelector('.member-list');
            members.forEach(member => {
                const memberHtml = `
                    <div class="member-item">
                        <span>${member.name}</span>
                        <span>${member.role}</span>
                    </div>
                `;
                const addMemberBtn = memberList.querySelector('.btn-add-member');
                addMemberBtn.insertAdjacentHTML('beforebegin', memberHtml);
            });
        }
    }

    setEditingPipelineId(id) {
        this.editingPipelineId = id;
    }

    getEditingPipelineId() {
        return this.editingPipelineId;
    }
} 