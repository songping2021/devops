// 状态管理模块
// 管理应用的全局状态和数据

class StateManager {
    constructor() {
        this.state = {
            pipelines: [],
            currentPage: 1,
            loading: false,
            filters: {
                projectId: ''
            }
        };
        
        this.listeners = [];
        this.init();
    }

    init() {
        console.log('状态管理器初始化完成');
    }

    /**
     * 获取当前状态
     * 功能描述：获取应用的当前状态
     * 入参：无
     * 返回参数：object - 当前状态对象
     */
    getState() {
        return { ...this.state };
    }

    /**
     * 更新状态
     * 功能描述：更新应用状态并通知监听器
     * 入参：updates (object) - 要更新的状态
     * 返回参数：无
     */
    setState(updates) {
        const oldState = { ...this.state };
        this.state = { ...this.state, ...updates };
        
        // 通知所有监听器状态变化
        this.listeners.forEach(listener => {
            try {
                listener(this.state, oldState);
            } catch (error) {
                console.error('状态监听器执行失败:', error);
            }
        });
    }

    /**
     * 设置流水线数据
     * 功能描述：更新流水线列表数据
     * 入参：pipelines (array) - 流水线数组
     * 返回参数：无
     */
    setPipelines(pipelines) {
        this.setState({ pipelines: pipelines || [] });
    }

    /**
     * 获取流水线数据
     * 功能描述：获取当前流水线列表
     * 入参：无
     * 返回参数：array - 流水线数组
     */
    getPipelines() {
        return this.state.pipelines;
    }

    /**
     * 设置加载状态
     * 功能描述：设置应用的加载状态
     * 入参：loading (boolean) - 是否正在加载
     * 返回参数：无
     */
    setLoading(loading) {
        this.setState({ loading });
    }

    /**
     * 设置筛选条件
     * 功能描述：更新筛选条件
     * 入参：filters (object) - 筛选条件对象
     * 返回参数：无
     */
    setFilters(filters) {
        this.setState({ 
            filters: { ...this.state.filters, ...filters } 
        });
    }

    /**
     * 获取筛选条件
     * 功能描述：获取当前筛选条件
     * 入参：无
     * 返回参数：object - 筛选条件对象
     */
    getFilters() {
        return this.state.filters;
    }
}

// 创建全局状态管理器实例
const stateManager = new StateManager();

// 导出状态管理器实例
export default stateManager; 