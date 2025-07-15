// 阶段管理模块
class StageManager {
    constructor() {
        this.currentTaskItem = null;
        this.currentStageItem = null;
        this.editingPipelineId = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // 添加阶段按钮点击处理
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-add-stage')) {
                this.currentTaskItem = e.target.closest('.task-item');
                this.currentStageItem = null;
                showModal('stageModal');
            }
        });

        // 阶段选择处理
        document.querySelectorAll('.stage-option').forEach(option => {
            option.addEventListener('click', (e) => {
                this.handleStageSelection(e.target.closest('.stage-option'));
            });
        });

        // 阶段点击事件处理
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('stage-item')) {
                this.handleStageClick(e.target);
            }
        });

        // 侧边栏相关事件
        this.bindSidebarEvents();

        // 删除阶段按钮事件
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-delete-stage') || e.target.closest('.btn-delete-stage')) {
                this.deleteCurrentStage();
            }
        });
    }

    bindSidebarEvents() {
        // 点击背景关闭
        document.getElementById('sidebarBackdrop').addEventListener('click', () => {
            this.hideSidebarConfig(false);
        });

        // 取消按钮
        document.getElementById('cancelSidebarConfig').addEventListener('click', () => {
            this.hideSidebarConfig(false);
        });

        // 保存按钮
        document.getElementById('saveSidebarConfig').addEventListener('click', () => {
            this.handleSaveConfig();
        });

        // 阶段开关控制
        document.getElementById('stageEnabledToggle').addEventListener('change', (e) => {
            this.handleStageToggle(e.target.checked);
        });
    }

    handleStageSelection(stageOption) {
        const stageType = stageOption.dataset.stage;
        
        if (!stageType || stageType === 'undefined' || stageType === 'unknown') {
            alert('无效的阶段类型，请选择有效的阶段');
            return;
        }
        
        if (this.currentTaskItem) {
            const stageList = this.currentTaskItem.querySelector('.stage-list');
            const stageName = getStageTitle(stageType);
            const stageId = `stage_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
            const stageHtml = `<div class="stage-item" data-stage-type="${stageType}" data-stage-id="${stageId}">${stageName}</div>`;
            const addStageBtn = stageList.querySelector('.btn-add-stage');
            addStageBtn.insertAdjacentHTML('beforebegin', stageHtml);
            
            this.currentStageItem = addStageBtn.previousElementSibling;
        }
        
        hideModal('stageModal');
        this.showSidebarConfig(stageType, false);
    }

    handleStageClick(stageElement) {
        const stageType = stageElement.dataset.stageType;
        if (stageType) {
            const validStageTypes = ['compile', 'build', 'deploy'];
            if (!validStageTypes.includes(stageType)) {
                alert(`未知的阶段类型: ${stageType}，无法编辑。`);
                return;
            }
            
            this.currentTaskItem = stageElement.closest('.task-item');
            this.currentStageItem = stageElement;
            
            const taskType = this.currentTaskItem.dataset.taskType;
            this.loadStageConfigData(this.currentStageItem, taskType, stageType);
            
            this.showSidebarConfig(stageType, true);
        }
    }

    showSidebarConfig(stageType, isEdit = false) {
        const sidebarTitle = document.getElementById('sidebarStageTitle');
        const configs = document.querySelectorAll('#sidebarStageConfig .stage-config');
        
        configs.forEach(config => {
            if (config) {
                config.style.display = 'none';
            }
        });
        
        const configMap = {
            'compile': '编译阶段',
            'build': '构建阶段',
            'deploy': '部署阶段'
        };
        
        sidebarTitle.textContent = (isEdit ? '编辑' : '配置') + (configMap[stageType] || '未知阶段');
        
        const taskType = this.currentTaskItem ? this.currentTaskItem.dataset.taskType : '';
        
        let configId = '';
        if (stageType === 'compile') {
            if (taskType === 'npm') {
                configId = 'sidebarNpmCompileConfig';
            } else {
                configId = 'sidebarCompileConfig';
            }
        } else if (stageType === 'build') {
            configId = 'sidebarBuildConfig';
        } else if (stageType === 'deploy') {
            configId = 'sidebarDeployConfig';
        }
        
        const configElement = document.getElementById(configId);
        if (configElement) {
            configElement.style.display = 'block';
            this.addRealTimeSaveListeners(configElement, stageType);
        } else {
            console.warn(`找不到阶段配置元素: ${configId}`);
        }
        
        // 加载阶段状态
        this.loadStageStatus(stageType);
        
        document.getElementById('sidebarBackdrop').classList.add('active');
        document.getElementById('sidebarStageConfig').classList.add('active');
        
        document.querySelectorAll('.btn-delete-stage').forEach(btn => {
            btn.removeEventListener('click', this.deleteCurrentStage);
            btn.addEventListener('click', this.deleteCurrentStage.bind(this));
        });
    }

    addRealTimeSaveListeners(configElement, stageType) {
        if (!configElement.hasAttribute('data-listeners-added')) {
            const inputs = configElement.querySelectorAll('input, select');
            inputs.forEach(input => {
                ['input', 'change', 'blur'].forEach(eventType => {
                    input.addEventListener(eventType, (event) => {
                        console.log(`检测到${eventType}事件，元素:`, event.target, '值:', event.target.value);
                        if (this.currentTaskItem && this.currentStageItem) {
                            clearTimeout(window.realTimeSaveTimeout);
                            window.realTimeSaveTimeout = setTimeout(() => {
                                console.log('开始实时保存配置...');
                                this.saveStageConfig(this.currentTaskItem, this.currentStageItem, stageType);
                                console.log('实时保存完成');
                            }, 300);
                        } else {
                            console.warn('实时保存失败：缺少currentTaskItem或currentStageItem');
                        }
                    });
                });
            });
            
            configElement.setAttribute('data-listeners-added', 'true');
            console.log('已为配置面板添加实时保存监听器');
        }
    }

    hideSidebarConfig(shouldSave = true) {
        if (shouldSave && this.currentTaskItem && this.currentStageItem) {
            const stageType = this.currentStageItem.dataset.stageType;
            if (stageType) {
                this.saveStageConfig(this.currentTaskItem, this.currentStageItem, stageType);
            }
        }
        
        document.getElementById('sidebarBackdrop').classList.remove('active');
        document.getElementById('sidebarStageConfig').classList.remove('active');
    }

    handleSaveConfig() {
        console.log('用户点击了保存按钮，强制收集配置数据');
        if (this.currentTaskItem && this.currentStageItem) {
            const stageType = this.currentStageItem.dataset.stageType;
            if (stageType) {
                this.saveStageConfig(this.currentTaskItem, this.currentStageItem, stageType);
                console.log('已保存阶段配置到DOM');
            }
        }
        this.hideSidebarConfig(false);
    }

    deleteCurrentStage() {
        if (this.currentStageItem) {
            this.currentStageItem.remove();
            this.hideSidebarConfig();
        }
    }

    saveStageConfig(taskItem, stageElement, stageType) {
        if (!taskItem || !stageElement || !stageType) {
            console.warn('保存阶段配置失败：缺少必要参数');
            return;
        }
        
        const taskName = taskItem.querySelector('.task-title').textContent.split(': ')[1];
        const taskType = taskItem.dataset.taskType;
        const taskId = taskItem.dataset.taskId;
        const pipelineId = this.editingPipelineId;
        
        console.log('保存阶段配置参数:', { taskName, taskType, taskId, stageType, pipelineId });
        
        let configData = {};
        
        // 收集配置数据
        if (stageType === 'compile') {
            if (taskType === 'npm') {
                const form = document.querySelector('#sidebarNpmCompileConfig');
                if (form) {
                    const safeGetValue = (selector, defaultValue = '') => {
                        const element = form.querySelector(selector);
                        return element ? element.value : defaultValue;
                    };
                    
                    configData = {
                        taskId: taskId,
                        taskName: taskName,
                        stageId: stageElement.dataset.stageId,
                        nodeVersion: safeGetValue('select:nth-of-type(1)', '14.18'),
                        pnpmVersion: safeGetValue('select:nth-of-type(2)', '7.33.7'),
                        codePath: safeGetValue('input[type="text"]:nth-of-type(1)', ''),
                        distPath: safeGetValue('input[type="text"]:nth-of-type(2)', 'dist'),
                        buildCommand: safeGetValue('input[type="text"]:nth-of-type(3)', 'pnpm run build')
                    };
                }
            } else {
                const form = document.querySelector('#sidebarCompileConfig');
                if (form) {
                    const safeGetValue = (selector, defaultValue = '') => {
                        const element = form.querySelector(selector);
                        return element ? element.value : defaultValue;
                    };
                    
                    // 添加调试信息
                    console.log('Maven编译配置表单调试:');
                    form.querySelectorAll('input[type="text"]').forEach((input, index) => {
                        console.log(`input[${index + 1}]:`, input, '值:', input.value, 'placeholder:', input.placeholder);
                    });
                    
                    const codePathInput = form.querySelector('input[placeholder*="代码路径"]') || form.querySelector('input[type="text"]:nth-of-type(1)');
                    console.log('代码路径输入框:', codePathInput, '值:', codePathInput?.value);
                    
                    configData = {
                        taskId: taskId,
                        taskName: taskName,
                        stageId: stageElement.dataset.stageId,
                        mavenVersion: safeGetValue('select:nth-of-type(1)', '3.8.1'),
                        jdkVersion: safeGetValue('select:nth-of-type(2)', '11'),
                        codePath: safeGetValue('input[placeholder*="代码路径"], input[type="text"]:nth-of-type(1)', ''),
                        artifactPath: safeGetValue('input[placeholder*="制品路径"], input[type="text"]:nth-of-type(2)', ''),
                        artifactFormat: safeGetValue('select:nth-of-type(3)', 'jar'),
                        buildCommand: safeGetValue('input[type="text"]:nth-of-type(3)', 'mvn clean package -Dmaven.test.skip=true -U')
                    };
                }
            }
        } else if (stageType === 'build') {
            const form = document.querySelector('#sidebarBuildConfig');
            if (form) {
                const safeGetValue = (selector, defaultValue = '') => {
                    const element = form.querySelector(selector);
                    return element ? element.value : defaultValue;
                };
                
                configData = {
                    taskId: taskId,
                    taskName: taskName,
                    stageId: stageElement.dataset.stageId,
                    taskType: taskType,
                    repository: safeGetValue('input[type="text"]:nth-of-type(1)', ''),
                    dockerfilePath: safeGetValue('input[type="text"]:nth-of-type(2)', ''),
                    architecture: safeGetValue('select', 'amd64')
                };
            }
        } else if (stageType === 'deploy') {
            const form = document.querySelector('#sidebarDeployConfig');
            if (form) {
                const safeGetValue = (selector, defaultValue = '') => {
                    const element = form.querySelector(selector);
                    return element ? element.value : defaultValue;
                };
                
                const safeGetChecked = (selector, defaultValue = false) => {
                    const element = form.querySelector(selector);
                    return element ? element.checked : defaultValue;
                };
                
                const resourceInputs = form.querySelector('.resource-inputs');
                const cpuInput = resourceInputs ? resourceInputs.querySelector('input[type="number"]:nth-of-type(1)') : null;
                const memoryInput = resourceInputs ? resourceInputs.querySelector('input[type="number"]:nth-of-type(2)') : null;
                
                const namespaceInput = form.querySelector('input[placeholder*="命名空间"]') || form.querySelector('input[type="text"]:nth-of-type(1)');
                const serviceNameInput = form.querySelector('input[placeholder*="服务名"]') || form.querySelector('input[type="text"]:nth-of-type(2)');
                const portInput = form.querySelector('input[placeholder*="端口"]') || form.querySelector('input[type="text"]:nth-of-type(3)');
                
                configData = {
                    taskId: taskId,
                    taskName: taskName,
                    stageId: stageElement.dataset.stageId,
                    taskType: taskType,
                    namespace: namespaceInput ? namespaceInput.value : '',
                    serviceName: serviceNameInput ? serviceNameInput.value : '',
                    port: portInput ? portInput.value : '',
                    cluster: safeGetValue('select', 'K8S_cmdicncf_jkyw'),
                    enableIngress: safeGetChecked('input[type="checkbox"]', true),
                    cpu: cpuInput ? cpuInput.value : '',
                    memory: memoryInput ? memoryInput.value : ''
                };
                
                console.log('部署配置 - 收集到的数据:', {
                    namespace: namespaceInput?.value,
                    serviceName: serviceNameInput?.value,
                    port: portInput?.value,
                    cpu: cpuInput?.value,
                    memory: memoryInput?.value
                });
                
                // 添加调试信息：列出所有输入框和选择器找到的元素
                console.log('部署表单中的所有文本输入框:');
                form.querySelectorAll('input[type="text"]').forEach((input, index) => {
                    console.log(`input[${index + 1}]:`, input, '值:', input.value, 'placeholder:', input.placeholder);
                });
                console.log('部署表单中的所有数字输入框:');
                form.querySelectorAll('input[type="number"]').forEach((input, index) => {
                    console.log(`number input[${index + 1}]:`, input, '值:', input.value, 'placeholder:', input.placeholder);
                });
                console.log('部署选择器匹配结果:');
                console.log('namespaceInput:', namespaceInput);
                console.log('serviceNameInput:', serviceNameInput);
                console.log('portInput:', portInput);
                console.log('cpuInput:', cpuInput);
                console.log('memoryInput:', memoryInput);
                console.log('resourceInputs container:', resourceInputs);
                
                if (!taskItem.dataset.taskId) {
                    taskItem.dataset.taskId = configData.taskId;
                }
            }
        }
        
        // 始终保存到DOM中
        stageElement.dataset.stageConfig = JSON.stringify(configData);
        console.log(`保存阶段配置 - 任务: ${taskName}, 阶段: ${stageType}`, configData);
        console.log(`配置数据已保存到DOM元素:`, stageElement.dataset.stageConfig);
        
        // 检查是否应该调用后端API
        // 优先使用pipeline ID和task ID，如果没有则尝试使用项目基本信息
        let shouldCallAPI = false;
        let projectId = null;
        let branch = null;
        
        if (pipelineId && taskId && window.TaskConfigAPI) {
            // 任务已保存到数据库的情况
            shouldCallAPI = true;
            projectId = this.getProjectIdFromPipeline(pipelineId);
            branch = this.getBranchFromPipeline(pipelineId);
            console.log('任务已保存到数据库，使用pipeline信息调用API');
        } else if (window.TaskConfigAPI) {
            // 首次创建任务的情况，尝试从页面获取项目信息
            const projectIdInput = document.getElementById('projectId');
            const branchInput = document.getElementById('branch');
            
            if (projectIdInput && branchInput && projectIdInput.value && branchInput.value) {
                shouldCallAPI = true;
                projectId = projectIdInput.value.trim();
                branch = branchInput.value.trim();
                console.log('首次创建任务，使用页面项目信息调用API', { projectId, branch, taskName });
            }
        }
        
        if (shouldCallAPI && projectId && branch) {
            console.log('调用后端API同步配置', { projectId, branch, taskName, stageType });
            
            // 使用新的API模块保存配置
            window.TaskConfigAPI.saveStageConfiguration(
                taskType, 
                projectId, 
                branch, 
                taskName, 
                stageType, 
                configData
            ).then(result => {
                if (result.success) {
                    console.log('配置数据保存成功:', result.data);
                    this.showSaveSuccess();
                } else {
                    console.error('保存配置数据失败:', result.error);
                    this.showSaveError(result.error);
                }
            }).catch(error => {
                console.error('保存配置数据失败:', error);
                this.showSaveError(error.message);
            });
        } else {
            console.log('无法调用后端API，配置仅保存到DOM中');
            if (!window.TaskConfigAPI) {
                console.log('原因：TaskConfigAPI不可用');
            } else if (!projectId || !branch) {
                console.log('原因：缺少项目信息', { projectId, branch });
            }
        }
    }

    loadStageConfigData(stageElement, taskType, stageType) {
        const taskItem = this.currentTaskItem;
        const taskName = taskItem ? taskItem.querySelector('.task-title').textContent.split(': ')[1] : '';
        
        if (stageElement.dataset.stageConfig) {
            try {
                const config = JSON.parse(stageElement.dataset.stageConfig);
                this.fillFormWithConfig(config, taskType, stageType);
                return;
            } catch (e) {
                console.error('解析DOM配置数据失败:', e);
            }
        }
        
        if (this.editingPipelineId && taskName && stageType && window.TaskConfigAPI) {
            // 使用新的API模块加载配置
            window.TaskConfigAPI.getTaskConfig(this.editingPipelineId, taskName, { stageType: stageType })
                .then(result => {
                    if (result.success && result.data && result.data.stages && result.data.stages[stageType]) {
                        const stageConfig = result.data.stages[stageType];
                        stageElement.dataset.stageConfig = JSON.stringify(stageConfig);
                        this.fillFormWithConfig(stageConfig, taskType, stageType);
                    } else {
                        console.log('从服务器加载配置失败，使用默认配置:', result.error);
                        this.loadDefaultConfig(taskType, stageType);
                    }
                })
                .catch(error => {
                    console.log('从服务器加载配置失败，使用默认配置:', error);
                    this.loadDefaultConfig(taskType, stageType);
                });
        } else {
            this.loadDefaultConfig(taskType, stageType);
        }
    }

    loadDefaultConfig(taskType, stageType) {
        let defaultConfig = {};
        
        if (stageType === 'compile') {
            if (taskType === 'npm') {
                defaultConfig = {
                    nodeVersion: '14.18',
                    pnpmVersion: '7.33.7',
                    codePath: '.',
                    distPath: 'dist',
                    buildCommand: 'pnpm run build'
                };
            } else {
                defaultConfig = {
                    mavenVersion: '3.8.1',
                    jdkVersion: '11',
                    codePath: '.',
                    artifactPath: 'target/*.jar',
                    artifactFormat: 'jar',
                    buildCommand: 'mvn clean package -Dmaven.test.skip=true -U'
                };
            }
        } else if (stageType === 'build') {
            defaultConfig = {
                repository: 'harbor.example.com/project/app',
                dockerfilePath: './Dockerfile',
                architecture: 'amd64'
            };
        } else if (stageType === 'deploy') {
            defaultConfig = {
                namespace: 'default',
                serviceName: '$CI_PROJECT_NAME',
                port: '80',
                cluster: 'K8S_cmdicncf_jkyw',
                enableIngress: true,
                cpu: '1',
                memory: '1'
            };
        }
        
        this.fillFormWithConfig(defaultConfig, taskType, stageType);
    }

    fillFormWithConfig(config, taskType, stageType) {
        const taskItem = this.currentTaskItem;
        const taskName = taskItem ? taskItem.querySelector('.task-title').textContent.split(': ')[1] : '';
        const taskId = taskItem ? taskItem.dataset.taskId : '';
        
        if (stageType === 'compile') {
            if (taskType === 'npm') {
                const form = document.querySelector('#sidebarNpmCompileConfig');
                if (form && config) {
                    const nodeVersionSelect = form.querySelector('select:nth-of-type(1)');
                    if (nodeVersionSelect && config.nodeVersion) {
                        nodeVersionSelect.value = config.nodeVersion;
                    }
                    
                    const pnpmVersionSelect = form.querySelector('select:nth-of-type(2)');
                    if (pnpmVersionSelect && config.pnpmVersion) {
                        pnpmVersionSelect.value = config.pnpmVersion;
                    }
                    
                    const codePathInput = form.querySelector('input[type="text"]:nth-of-type(1)');
                    if (codePathInput && config.codePath !== undefined) {
                        codePathInput.value = config.codePath;
                    }
                    
                    const distPathInput = form.querySelector('input[type="text"]:nth-of-type(2)');
                    if (distPathInput && config.distPath !== undefined) {
                        distPathInput.value = config.distPath;
                    }
                    
                    const buildCommandInput = form.querySelector('input[type="text"]:nth-of-type(3)');
                    if (buildCommandInput && config.buildCommand !== undefined) {
                        buildCommandInput.value = config.buildCommand;
                    }
                }
            } else {
                const form = document.querySelector('#sidebarCompileConfig');
                if (form && config) {
                    const mavenVersionSelect = form.querySelector('select:nth-of-type(1)');
                    if (mavenVersionSelect && config.mavenVersion) {
                        mavenVersionSelect.value = config.mavenVersion;
                    }
                    
                    const jdkVersionSelect = form.querySelector('select:nth-of-type(2)');
                    if (jdkVersionSelect && config.jdkVersion) {
                        jdkVersionSelect.value = config.jdkVersion;
                    }
                    
                    // 使用更精确的选择器，与saveStageConfig方法保持一致
                    const codePathInput = form.querySelector('input[placeholder*="代码路径"]') || form.querySelector('input[type="text"]:nth-of-type(1)');
                    if (codePathInput && config.codePath !== undefined) {
                        codePathInput.value = config.codePath;
                    }
                    
                    const artifactPathInput = form.querySelector('input[placeholder*="制品路径"]') || form.querySelector('input[type="text"]:nth-of-type(2)');
                    if (artifactPathInput && config.artifactPath !== undefined) {
                        artifactPathInput.value = config.artifactPath;
                    }
                    
                    const artifactFormatSelect = form.querySelector('select:nth-of-type(3)');
                    if (artifactFormatSelect && config.artifactFormat) {
                        artifactFormatSelect.value = config.artifactFormat;
                    }
                    
                    const buildCommandInput = form.querySelector('input.input-with-default[placeholder*="mvn clean"]') || form.querySelector('input[type="text"]:nth-of-type(3)');
                    if (buildCommandInput && config.buildCommand !== undefined) {
                        buildCommandInput.value = config.buildCommand;
                    }
                }
            }
        } else if (stageType === 'build') {
            const form = document.querySelector('#sidebarBuildConfig');
            if (form && config) {
                if ((taskId && config.taskId === taskId) || 
                    (taskName && config.taskName === taskName) || 
                    (!config.taskId && !config.taskName)) {
                    
                    // 使用更精确的选择器，与saveStageConfig方法保持一致
                    const repositoryInput = form.querySelector('input[placeholder*="镜像仓库名称"]') || form.querySelector('input[type="text"]:nth-of-type(1)');
                    if (repositoryInput && config.repository !== undefined) {
                        repositoryInput.value = config.repository;
                    }
                    
                    const dockerfilePathInput = form.querySelector('input[placeholder*="Dockerfile路径"]') || form.querySelector('input[type="text"]:nth-of-type(2)');
                    if (dockerfilePathInput && config.dockerfilePath !== undefined) {
                        dockerfilePathInput.value = config.dockerfilePath;
                    }
                    
                    const architectureSelect = form.querySelector('select');
                    if (architectureSelect && config.architecture) {
                        architectureSelect.value = config.architecture;
                    }
                    
                    if (config.taskId && taskItem && !taskItem.dataset.taskId) {
                        taskItem.dataset.taskId = config.taskId;
                    }
                }
            }
        } else if (stageType === 'deploy') {
            const form = document.querySelector('#sidebarDeployConfig');
            if (form && config) {
                if ((taskId && config.taskId === taskId) || 
                    (taskName && config.taskName === taskName) || 
                    (!config.taskId && !config.taskName)) {
                    
                    // 使用更精确的选择器，与saveStageConfig方法保持一致
                    const namespaceInput = form.querySelector('input[placeholder*="命名空间"]') || form.querySelector('input[type="text"]:nth-of-type(1)');
                    if (namespaceInput && config.namespace !== undefined) {
                        namespaceInput.value = config.namespace;
                    }
                    
                    const serviceNameInput = form.querySelector('input[placeholder*="服务名"]') || form.querySelector('input[type="text"]:nth-of-type(2)');
                    if (serviceNameInput && config.serviceName !== undefined) {
                        serviceNameInput.value = config.serviceName;
                    }
                    
                    const portInput = form.querySelector('input[placeholder*="应用端口"]') || form.querySelector('input[type="text"]:nth-of-type(3)');
                    if (portInput && config.port !== undefined) {
                        portInput.value = config.port;
                    }
                    
                    const clusterSelect = form.querySelector('select');
                    if (clusterSelect && config.cluster) {
                        clusterSelect.value = config.cluster;
                    }
                    
                    const ingressCheckbox = form.querySelector('#enableIngressSidebar');
                    if (ingressCheckbox && config.enableIngress !== undefined) {
                        ingressCheckbox.checked = config.enableIngress;
                    }
                    
                    // 资源限制字段的精确选择器，与saveStageConfig方法保持一致
                    const resourceInputs = form.querySelector('.resource-inputs');
                    const cpuInput = resourceInputs ? (resourceInputs.querySelector('.resource-item:nth-of-type(1) input[type="number"]') || resourceInputs.querySelector('input[type="number"]:nth-of-type(1)')) : null;
                    if (cpuInput && config.cpu !== undefined) {
                        cpuInput.value = config.cpu;
                    }
                    
                    const memoryInput = resourceInputs ? (resourceInputs.querySelector('.resource-item:nth-of-type(2) input[type="number"]') || resourceInputs.querySelector('input[type="number"]:nth-of-type(2)')) : null;
                    if (memoryInput && config.memory !== undefined) {
                        memoryInput.value = config.memory;
                    }
                    
                    if (config.taskId && taskItem && !taskItem.dataset.taskId) {
                        taskItem.dataset.taskId = config.taskId;
                    }
                }
            }
        }
    }

    setEditingPipelineId(id) {
        this.editingPipelineId = id;
    }

    setCurrentItems(taskItem, stageItem) {
        this.currentTaskItem = taskItem;
        this.currentStageItem = stageItem;
    }

    /**
     * 从流水线ID中提取项目ID
     * 临时实现，实际应该从流水线数据中获取
     */
    getProjectIdFromPipeline(pipelineId) {
        // 临时方案：从表单中获取项目ID
        const projectIdInput = document.getElementById('projectId');
        if (projectIdInput && projectIdInput.value) {
            return projectIdInput.value;
        }
        
        // 默认返回流水线ID作为项目ID
        return pipelineId.toString();
    }

    /**
     * 从流水线ID中提取分支名
     * 临时实现，实际应该从流水线数据中获取
     */
    getBranchFromPipeline(pipelineId) {
        // 临时方案：从表单中获取分支名
        const branchInput = document.getElementById('branch');
        if (branchInput && branchInput.value) {
            return branchInput.value;
        }
        
        // 默认返回develop
        return 'develop';
    }

    /**
     * 显示保存成功提示
     */
    showSaveSuccess() {
        // 简单的成功提示，可以后续优化为更好的UI提示
        const existingAlert = document.querySelector('.save-success-alert');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        const alert = document.createElement('div');
        alert.className = 'save-success-alert';
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 10000;
            font-size: 14px;
        `;
        alert.textContent = '配置保存成功';
        document.body.appendChild(alert);
        
        setTimeout(() => {
            if (alert && alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 3000);
    }

    /**
     * 显示保存错误提示
     */
    showSaveError(errorMessage) {
        // 简单的错误提示，可以后续优化为更好的UI提示
        const existingAlert = document.querySelector('.save-error-alert');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        const alert = document.createElement('div');
        alert.className = 'save-error-alert';
        alert.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f44336;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 10000;
            font-size: 14px;
            max-width: 300px;
        `;
        alert.textContent = `保存失败: ${errorMessage}`;
        document.body.appendChild(alert);
        
        setTimeout(() => {
            if (alert && alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }

    /**
     * 处理阶段开关切换
     */
    handleStageToggle(enabled) {
        if (!this.currentTaskItem || !this.currentStageItem) {
            console.warn('无法处理阶段开关：缺少当前任务或阶段信息');
            return;
        }

        const taskName = this.currentTaskItem.querySelector('.task-title').textContent.split(': ')[1];
        const stageType = this.currentStageItem.dataset.stageType;
        const projectId = this.getProjectIdFromPipeline(this.editingPipelineId);
        const branch = this.getBranchFromPipeline(this.editingPipelineId);

        if (!taskName || !stageType || !projectId) {
            console.warn('无法处理阶段开关：缺少必要参数', { taskName, stageType, projectId });
            return;
        }

        // 调用API切换阶段状态
        if (window.TaskConfigAPI) {
            const toggleData = {
                project_id: projectId,
                branch: branch,
                task_name: taskName,
                stage_name: stageType,
                enabled: enabled,
                sync_to_gitlab: true
            };

            window.TaskConfigAPI.toggleStage(toggleData)
                .then(result => {
                    if (result.success) {
                        console.log('阶段开关切换成功:', result.data);
                        this.updateStageVisualState(enabled);
                        this.showSaveSuccess();
                    } else {
                        console.error('阶段开关切换失败:', result.error);
                        this.showSaveError(result.error);
                        // 恢复开关状态
                        document.getElementById('stageEnabledToggle').checked = !enabled;
                    }
                })
                .catch(error => {
                    console.error('阶段开关切换失败:', error);
                    this.showSaveError(error.message);
                    // 恢复开关状态
                    document.getElementById('stageEnabledToggle').checked = !enabled;
                });
        }
    }

    /**
     * 更新阶段的视觉状态
     */
    updateStageVisualState(enabled) {
        if (this.currentStageItem) {
            if (enabled) {
                this.currentStageItem.classList.remove('stage-disabled');
                this.currentStageItem.style.opacity = '1';
            } else {
                this.currentStageItem.classList.add('stage-disabled');
                this.currentStageItem.style.opacity = '0.5';
            }
        }
    }

    /**
     * 加载阶段状态
     */
    loadStageStatus(stageType) {
        const taskName = this.currentTaskItem ? this.currentTaskItem.querySelector('.task-title').textContent.split(': ')[1] : '';
        const projectId = this.getProjectIdFromPipeline(this.editingPipelineId);
        const branch = this.getBranchFromPipeline(this.editingPipelineId);

        if (window.TaskConfigAPI && taskName && projectId) {
            window.TaskConfigAPI.getStageStatus(projectId, branch, taskName)
                .then(result => {
                    if (result.success && result.data && result.data.stages) {
                        const stageStatus = result.data.stages[stageType];
                        const isEnabled = stageStatus === 'on';
                        document.getElementById('stageEnabledToggle').checked = isEnabled;
                        this.updateStageVisualState(isEnabled);
                    }
                })
                .catch(error => {
                    console.log('加载阶段状态失败，使用默认状态:', error);
                    // 默认启用
                    document.getElementById('stageEnabledToggle').checked = true;
                    this.updateStageVisualState(true);
                });
        } else {
            // 默认启用
            document.getElementById('stageEnabledToggle').checked = true;
            this.updateStageVisualState(true);
        }
    }
} 