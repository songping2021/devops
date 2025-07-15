# CI/CD流水线管理系统 - JavaScript模块架构

## 概述
本系统采用模块化架构，将功能拆分为多个独立的模块文件，确保代码的可维护性、可扩展性和可重用性。包含流水线列表管理、流水线编辑等功能。

## 核心模块结构

### 主页面模块 (index.html)

#### 1. main.js - 主应用入口
**职责：** 流水线列表页面的主控制器
- 页面初始化和事件绑定
- 流水线数据加载和展示
- 用户交互处理（搜索、执行、删除等）
- 全局函数注册

#### 2. pipeline-api.js - API接口模块
**职责：** 封装所有与后端交互的API调用
- 流水线CRUD操作
- 搜索和筛选功能
- 统一的错误处理
- HTTP请求封装

**主要方法：**
- `getPipelineList()` - 获取流水线列表
- `searchPipelinesByProject()` - 按项目搜索
- `executePipeline()` - 执行流水线
- `deletePipeline()` - 删除流水线
- `createPipeline()` - 创建新流水线
- `updatePipeline()` - 更新流水线

#### 3. state-manager.js - 状态管理模块
**职责：** 管理应用的全局状态
- 流水线数据状态管理
- 筛选条件状态管理
- 加载状态管理
- 状态变化监听

#### 4. utils.js - 工具函数模块
**职责：** 提供通用的辅助功能
- 日期格式化
- 数据解析和转换
- 消息提示封装
- URL参数处理
- 防抖和节流函数

### 流水线编辑模块 (pipeline-edit.html)

### 1. config.js - 配置和公共函数
- API基础URL配置
- 格式化函数 (formatTasksForDisplay, formatStagesForDisplay)
- 工具函数 (getTaskTypeText, getStageTitle, getStageType)
- 模态框控制函数 (showModal, hideModal)

### 2. task-manager.js - 任务管理模块
**职责：** 管理任务的增删改查操作
- 添加新任务
- 编辑现有任务
- 删除任务（包括远程文件夹删除）
- 任务列表渲染

**主要方法：**
- `addTaskToList()` - 添加任务到界面
- `editTask()` - 编辑任务
- `deleteTask()` - 删除任务
- `deleteTaskFolder()` - 删除远程任务文件夹

### 3. stage-manager.js - 阶段管理模块
**职责：** 管理流水线阶段的配置和操作
- 添加新阶段
- 配置阶段参数
- 删除阶段
- 阶段配置的保存和加载

**主要方法：**
- `showSidebarConfig()` - 显示阶段配置侧边栏
- `saveStageConfig()` - 保存阶段配置
- `loadStageConfigData()` - 加载阶段配置数据
- `fillFormWithConfig()` - 用配置数据填充表单

### 4. pipeline-loader.js - 数据加载模块
**职责：** 处理流水线数据的加载和解析
- 从服务器加载现有流水线数据
- 解析新旧API数据格式
- 初始化任务和阶段数据

**主要方法：**
- `loadPipelineData()` - 加载流水线数据
- `loadTasksWithNewAPI()` - 使用新API加载任务
- `loadTasksWithOldAPI()` - 使用旧API加载任务
- `loadTriggerConfig()` - 加载触发配置
- `loadMemberInfo()` - 加载成员信息

### 5. form-manager.js - 表单管理模块
**职责：** 处理表单验证、数据收集和提交
- 步骤导航控制
- 表单验证
- 数据收集和格式化
- 表单提交

**主要方法：**
- `showSection()` - 显示表单节
- `validateForm()` - 验证表单
- `collectFormData()` - 收集表单数据
- `submitForm()` - 提交表单

### 6. pipeline-edit-main.js - 主入口文件
**职责：** 应用程序的主入口点
- **唯一的DOMContentLoaded事件监听器**
- 模块初始化和协调
- URL参数处理
- 全局事件绑定

## 文件加载顺序

### 主页面 (index.html)
```html
<script src="js/config.js"></script>
<script type="module" src="js/main.js"></script>
```

### 流水线编辑页面 (pipeline-edit.html)
```html
<script src="js/config.js"></script>
<script src="js/task-manager.js"></script>
<script src="js/stage-manager.js"></script>
<script src="js/pipeline-loader.js"></script>
<script src="js/form-manager.js"></script>
<script src="js/pipeline-edit-main.js"></script>
```

## DOMContentLoaded事件管理
- **主页面：** `main.js` 包含主页面的初始化逻辑
- **编辑页面：** `pipeline-edit-main.js` 包含编辑页面的初始化逻辑
- 每个页面只有一个DOMContentLoaded事件监听器，避免冲突

## 模块间通信
- 通过构造函数参数传递依赖
- 通过方法调用进行模块间通信
- 使用共享的DOM元素进行数据交换

## 优势
1. **模块化：** 每个文件职责单一，便于维护
2. **可测试性：** 每个模块可以独立测试
3. **可扩展性：** 容易添加新功能而不影响现有代码
4. **避免冲突：** 每个页面只有一个DOMContentLoaded事件
5. **代码重用：** 模块可以在其他页面复用
6. **ES6模块支持：** 使用现代JavaScript模块系统
7. **状态管理：** 统一的状态管理机制

## 新功能说明
- **主页面功能完整实现：** 流水线列表查看、搜索、执行、删除
- **API模块化：** 统一的API调用封装
- **工具函数集成：** 通用功能的统一管理
- **状态管理：** 应用状态的集中管理

## 迁移说明
- 原始的 `script.js` 已被迁移到模块化架构
- 所有功能保持兼容，增强了可维护性
- 新建按钮功能正常，可正确跳转到流水线编辑页面 