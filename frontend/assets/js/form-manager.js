// 表单管理模块
class FormManager {
    constructor() {
        this.steps = document.querySelectorAll('.step');
        this.formSections = document.querySelectorAll('.form-section');
        this.submitBtn = document.getElementById('submitForm');
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.showSection('basicInfo');
        this.updateStepStatus(document.querySelector('.step[data-section="basicInfo"]'));
    }

    bindEvents() {
        // 步骤点击处理
        document.querySelector('.steps').addEventListener('click', (e) => {
            const stepElement = e.target.closest('.step');
            if (stepElement) {
                const sectionId = stepElement.dataset.section;
                if (sectionId) {
                    this.showSection(sectionId);
                    this.updateStepStatus(stepElement);
                }
            }
        });

        // 监听触发方式变化
        document.querySelectorAll('input[name="triggerType"]').forEach(radio => {
            radio.addEventListener('change', () => {
                this.handleTriggerTypeChange(radio.value);
            });
        });
    }

    showSection(sectionId) {
        this.formSections.forEach(section => {
            section.classList.toggle('active', section.id === sectionId);
        });
    }

    updateStepStatus(activeStep) {
        this.steps.forEach(step => {
            step.classList.remove('active');
        });
        activeStep.classList.add('active');
    }

    handleTriggerTypeChange(triggerType) {
        const autoConfig = document.getElementById('autoTriggerConfig');
        const scheduleConfig = document.getElementById('scheduleTriggerConfig');
        
        autoConfig.style.display = triggerType === 'auto' ? 'block' : 'none';
        scheduleConfig.style.display = triggerType === 'schedule' ? 'block' : 'none';
    }

    validateForm() {
        const projectIdInput = document.getElementById('projectId');
        const branchInput = document.getElementById('branch');
        let isValid = true;

        // 验证项目ID
        if (!projectIdInput.value.trim()) {
            isValid = false;
            projectIdInput.classList.add('error');
        } else {
            projectIdInput.classList.remove('error');
        }

        // 验证分支
        if (!branchInput.value.trim()) {
            isValid = false;
            branchInput.classList.add('error');
        } else {
            branchInput.classList.remove('error');
        }

        if (!isValid) {
            alert('请填写项目ID和分支');
            this.showSection('basicInfo');
            this.updateStepStatus(document.querySelector('.step[data-section="basicInfo"]'));
        }

        return isValid;
    }

    collectFormData() {
        const projectIdInput = document.getElementById('projectId');
        const branchInput = document.getElementById('branch');
        
        // 收集任务和阶段数据
        const taskList = document.querySelector('.task-list');
        const tasksData = Array.from(taskList.children).map(taskItem => {
            const taskTitle = taskItem.querySelector('.task-title').textContent;
            const taskName = taskTitle.split(': ')[1];
            const taskType = taskItem.dataset.taskType;
            const taskId = taskItem.dataset.taskId || Date.now().toString();
            
            if (!taskItem.dataset.taskId) {
                taskItem.dataset.taskId = taskId;
            }
            
            const stages = Array.from(taskItem.querySelectorAll('.stage-item')).map(stage => {
                const stageType = stage.dataset.stageType;
                const stageName = stage.textContent.trim();
                
                let stageConfig = {};
                
                if (stage.dataset.stageConfig) {
                    try {
                        stageConfig = JSON.parse(stage.dataset.stageConfig);
                        
                        if (stageType === 'build' || stageType === 'deploy') {
                            stageConfig.taskId = taskId;
                            stageConfig.taskName = taskName;
                        }
                    } catch (e) {
                        console.error('解析阶段配置数据失败:', e);
                    }
                } else {
                    stageConfig = this.getDefaultStageConfig(stageType, taskType, taskId, taskName);
                }
                
                return {
                    type: stageType,
                    name: stageName,
                    config: stageConfig
                };
            });

            return {
                name: taskName,
                type: taskType,
                id: taskId,
                stages: stages
            };
        });

        // 收集触发方式数据
        const triggerType = document.querySelector('input[name="triggerType"]:checked').value;
        const triggerConfig = {};
        
        if (triggerType === 'auto') {
            triggerConfig.events = Array.from(document.querySelectorAll('input[name="triggerEvent"]:checked'))
                .map(checkbox => checkbox.value);
        } else if (triggerType === 'schedule') {
            triggerConfig.scheduleType = document.getElementById('scheduleType').value;
            triggerConfig.scheduleTime = document.getElementById('scheduleTime').value;
        }

        // 收集成员数据
        const members = Array.from(document.querySelectorAll('.member-item')).map(item => ({
            name: item.querySelector('span:first-child').textContent,
            role: item.querySelector('span:last-child').textContent
        }));

        return {
            project_id: projectIdInput.value.trim(),
            branch: branchInput.value.trim(),
            task: JSON.stringify(tasksData),
            stage: JSON.stringify(tasksData.map(task => task.stages.map(stage => stage.type))),
            trigger_type: triggerType,
            trigger_config: JSON.stringify(triggerConfig),
            members: JSON.stringify(members),
            updated_by: 'system'
        };
    }

    getDefaultStageConfig(stageType, taskType, taskId, taskName) {
        if (stageType === 'compile') {
            if (taskType === 'maven') {
                return {
                    mavenVersion: '3.8.1',
                    jdkVersion: '11',
                    codePath: '',
                    artifactPath: '',
                    artifactFormat: 'jar',
                    buildCommand: 'mvn clean package -Dmaven.test.skip=true -U'
                };
            } else if (taskType === 'npm') {
                return {
                    nodeVersion: '14.18',
                    pnpmVersion: '7.33.7',
                    codePath: '.',
                    distPath: 'dist',
                    buildCommand: 'pnpm run build'
                };
            }
        } else if (stageType === 'build') {
            return {
                taskId: taskId,
                taskName: taskName,
                taskType: taskType,
                repository: '',
                dockerfilePath: '',
                architecture: 'amd64'
            };
        } else if (stageType === 'deploy') {
            return {
                taskId: taskId,
                taskName: taskName,
                taskType: taskType,
                namespace: '',
                serviceName: '$CI_PROJECT_NAME',
                port: '80',
                cluster: 'K8S_cmdicncf_jkyw',
                enableIngress: true,
                cpu: '1',
                memory: '1'
            };
        }
        return {};
    }

    async submitForm(editingPipelineId, stageManager) {
        // 防止重复提交
        if (this.submitBtn.disabled) {
            return;
        }
        
        // 首先保存所有已打开的阶段配置
        if (stageManager.currentTaskItem && stageManager.currentStageItem) {
            const stageType = stageManager.currentStageItem.dataset.stageType;
            if (stageType) {
                stageManager.saveStageConfig(stageManager.currentTaskItem, stageManager.currentStageItem, stageType);
            }
        }
        
        // 确保所有阶段配置都被收集
        const sidebarActive = document.getElementById('sidebarStageConfig').classList.contains('active');
        if (sidebarActive && stageManager.currentTaskItem && stageManager.currentStageItem) {
            const stageType = stageManager.currentStageItem.dataset.stageType;
            if (stageType) {
                console.log('强制收集当前侧边栏配置数据:', stageManager.currentTaskItem, stageManager.currentStageItem, stageType);
                stageManager.saveStageConfig(stageManager.currentTaskItem, stageManager.currentStageItem, stageType);
                stageManager.hideSidebarConfig(false);
            }
        }
        
        if (!sidebarActive && stageManager.currentTaskItem && stageManager.currentStageItem) {
            const stageType = stageManager.currentStageItem.dataset.stageType;
            if (stageType) {
                console.log('强制收集最近编辑的阶段配置数据:', stageManager.currentTaskItem, stageManager.currentStageItem, stageType);
                stageManager.saveStageConfig(stageManager.currentTaskItem, stageManager.currentStageItem, stageType);
            }
        }
        
        // 遍历所有任务和阶段，确保配置数据完整
        const taskList = document.querySelector('.task-list');
        Array.from(taskList.children).forEach(taskItem => {
            const taskType = taskItem.dataset.taskType;
            Array.from(taskItem.querySelectorAll('.stage-item')).forEach(stageElement => {
                const stageType = stageElement.dataset.stageType;
                
                if (!stageElement.dataset.stageConfig && stageType) {
                    console.log('为缺少配置的阶段收集默认配置:', taskItem, stageElement, stageType);
                    
                    const tempCurrentTaskItem = stageManager.currentTaskItem;
                    const tempCurrentStageItem = stageManager.currentStageItem;
                    stageManager.currentTaskItem = taskItem;
                    stageManager.currentStageItem = stageElement;
                    
                    stageManager.saveStageConfig(taskItem, stageElement, stageType);
                    
                    stageManager.currentTaskItem = tempCurrentTaskItem;
                    stageManager.currentStageItem = tempCurrentStageItem;
                } else if (stageElement.dataset.stageConfig) {
                    console.log('阶段已有配置数据:', stageElement.dataset.stageType, JSON.parse(stageElement.dataset.stageConfig));
                }
            });
        });
        
        // 验证表单
        if (!this.validateForm()) {
            return;
        }
        
        // 禁用按钮防止重复提交
        this.submitBtn.disabled = true;
        this.submitBtn.textContent = '保存中...';

        try {
            const formData = this.collectFormData();
            console.log('保存的数据:', formData);
            
            const apiBaseUrl = window.API_BASE_URL || 'http://localhost:5000/api';
            const url = editingPipelineId 
                ? `${apiBaseUrl}/pipelines/${editingPipelineId}`
                : `${apiBaseUrl}/pipelines`;
                
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '保存失败');
            }

            const result = await response.json();
            console.log('流水线保存结果:', result);
            
            // 流水线保存成功后，立即同步DOM中保存的阶段配置到后端
            if (window.TaskConfigAPI && result.success) {
                console.log('开始同步DOM中的阶段配置到后端...');
                
                // 如果是新创建的任务，等待一段时间确保GitLab项目完全创建
                if (!editingPipelineId) {
                    console.log('新创建任务，等待2秒确保GitLab项目创建完成...');
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
                
                await this.syncDOMConfigToBackend(editingPipelineId || result.pipeline_id, stageManager);
            }
            
            if (result.gitlab_project) {
                alert(`流水线创建成功！\n项目ID: ${result.gitlab_project.id}\n项目地址: ${result.gitlab_project.web_url}`);
            } else {
                alert(editingPipelineId ? '更新成功' : '创建成功');
            }
            
            window.location.href = 'index.html';
        } catch (error) {
            console.error('保存失败:', error);
            alert(`保存失败: ${error.message}`);
        } finally {
            this.submitBtn.disabled = false;
            this.submitBtn.textContent = '保存';
        }
    }

    /**
     * 同步DOM中保存的阶段配置到后端API
     */
    async syncDOMConfigToBackend(pipelineId, stageManager) {
        if (!pipelineId || !stageManager) {
            console.warn('无法同步配置：缺少pipeline ID或stage manager');
            return;
        }

        const taskList = document.querySelector('.task-list');
        const projectId = stageManager.getProjectIdFromPipeline(pipelineId);
        const branch = stageManager.getBranchFromPipeline(pipelineId);
        
        console.log('=== 配置同步调试信息 ===');
        console.log('pipelineId:', pipelineId);
        console.log('projectId:', projectId);
        console.log('branch:', branch);
        console.log('projectId输入框存在:', !!document.getElementById('projectId'));
        console.log('projectId输入框值:', document.getElementById('projectId')?.value);
        console.log('branch输入框存在:', !!document.getElementById('branch'));
        console.log('branch输入框值:', document.getElementById('branch')?.value);
        
        if (!projectId || !branch) {
            console.warn('无法同步配置：缺少项目ID或分支信息');
            return;
        }

        console.log('开始同步配置到后端:', { pipelineId, projectId, branch });
        
        const syncPromises = [];
        
        Array.from(taskList.children).forEach(taskItem => {
            const taskName = taskItem.querySelector('.task-title').textContent.split(': ')[1];
            const taskType = taskItem.dataset.taskType;
            
            Array.from(taskItem.querySelectorAll('.stage-item')).forEach(stageElement => {
                const stageType = stageElement.dataset.stageType;
                const stageConfigStr = stageElement.dataset.stageConfig;
                
                if (stageConfigStr && stageType) {
                    try {
                        const stageConfig = JSON.parse(stageConfigStr);
                        console.log(`同步配置 - 任务: ${taskName}, 阶段: ${stageType}`, stageConfig);
                        
                        const syncPromise = window.TaskConfigAPI.saveStageConfiguration(
                            taskType, 
                            projectId, 
                            branch, 
                            taskName, 
                            stageType, 
                            stageConfig
                        ).then(result => {
                            if (result.success) {
                                console.log(`配置同步成功 - ${taskName}.${stageType}:`, result.data);
                            } else {
                                console.error(`配置同步失败 - ${taskName}.${stageType}:`, result.error);
                            }
                            return result;
                        }).catch(async error => {
                            console.error(`配置同步异常 - ${taskName}.${stageType}:`, error);
                            
                            // 添加重试机制，等待1秒后重试一次
                            console.log(`重试配置同步 - ${taskName}.${stageType}...`);
                            await new Promise(resolve => setTimeout(resolve, 1000));
                            
                            try {
                                const retryResult = await window.TaskConfigAPI.saveStageConfiguration(
                                    taskType, 
                                    projectId, 
                                    branch, 
                                    taskName, 
                                    stageType, 
                                    stageConfig
                                );
                                
                                if (retryResult.success) {
                                    console.log(`重试成功 - ${taskName}.${stageType}:`, retryResult.data);
                                } else {
                                    console.error(`重试仍失败 - ${taskName}.${stageType}:`, retryResult.error);
                                }
                                
                                return retryResult;
                            } catch (retryError) {
                                console.error(`重试异常 - ${taskName}.${stageType}:`, retryError);
                                return { success: false, error: retryError.message };
                            }
                        });
                        
                        syncPromises.push(syncPromise);
                    } catch (e) {
                        console.error(`解析配置数据失败 - ${taskName}.${stageType}:`, e);
                    }
                }
            });
        });
        
        if (syncPromises.length > 0) {
            try {
                console.log(`等待 ${syncPromises.length} 个配置同步完成...`);
                const results = await Promise.all(syncPromises);
                const successCount = results.filter(r => r.success).length;
                const failCount = results.length - successCount;
                
                console.log(`配置同步完成: 成功 ${successCount} 个, 失败 ${failCount} 个`);
                
                if (failCount > 0) {
                    console.warn('部分配置同步失败，但不影响主流程');
                }
            } catch (error) {
                console.error('配置同步过程中出现异常:', error);
            }
        } else {
            console.log('没有需要同步的配置数据');
        }
    }
} 