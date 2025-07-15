// 流水线编辑页面主入口文件
document.addEventListener('DOMContentLoaded', async function() {
    // 全局变量
    let editingPipelineId = null;
    
    // 初始化各个模块
    const taskManager = new TaskManager();
    const stageManager = new StageManager();
    const pipelineLoader = new PipelineLoader();
    const formManager = new FormManager();
    
    // 检查URL参数是否包含pipeline ID
    const urlParams = new URLSearchParams(window.location.search);
    const pipelineId = urlParams.get('id');
    
    if (pipelineId) {
        editingPipelineId = pipelineId;
        
        // 设置各模块的编辑ID
        taskManager.setEditingPipelineId(pipelineId);
        stageManager.setEditingPipelineId(pipelineId);
        pipelineLoader.setEditingPipelineId(pipelineId);
        
        // 加载流水线数据
        await pipelineLoader.loadPipelineData(pipelineId, taskManager, stageManager);
    }
    
    // 绑定保存按钮事件（覆盖FormManager中的默认行为）
    const submitBtn = document.getElementById('submitForm');
    submitBtn.removeEventListener('click', formManager.handleSubmit); // 移除可能的重复监听器
    submitBtn.addEventListener('click', async function() {
        await formManager.submitForm(editingPipelineId, stageManager);
    });
    
    console.log('流水线编辑页面初始化完成');
}); 