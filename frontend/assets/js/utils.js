// 工具函数模块
// 提供通用的辅助功能

/**
 * 格式化日期显示
 * 功能描述：将日期字符串格式化为用户友好的显示格式
 * 入参：dateString (string) - 日期字符串
 * 返回参数：string - 格式化后的日期字符串
 */
export function formatDateDisplay(dateString) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return '';
        
        return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    } catch (error) {
        console.warn('日期格式化失败:', error);
        return '';
    }
}

/**
 * 解析任务列表显示
 * 功能描述：解析任务JSON字符串并格式化为显示文本
 * 入参：taskString (string) - 任务JSON字符串
 * 返回参数：string - 格式化后的任务名称
 */
export function parseTaskDisplay(taskString) {
    try {
        if (!taskString) return '';
        
        const tasks = JSON.parse(taskString);
        if (Array.isArray(tasks) && tasks.length > 0) {
            return tasks.map(task => task.name || task).filter(name => name).join('，');
        }
        
        return taskString;
    } catch (error) {
        console.warn('解析任务字段失败:', error);
        return taskString || '';
    }
}

/**
 * 显示确认对话框
 * 功能描述：显示确认对话框并返回用户选择
 * 入参：message (string) - 确认消息
 * 返回参数：boolean - 用户确认结果
 */
export function showConfirmDialog(message) {
    return confirm(message);
}

/**
 * 显示信息提示
 * 功能描述：显示信息提示框
 * 入参：message (string) - 提示消息, type (string) - 消息类型
 * 返回参数：无
 */
export function showMessage(message, type = 'info') {
    // 这里可以扩展为更复杂的消息提示组件
    switch (type) {
        case 'error':
            alert(`错误: ${message}`);
            break;
        case 'success':
            alert(`成功: ${message}`);
            break;
        case 'warning':
            alert(`警告: ${message}`);
            break;
        default:
            alert(message);
    }
}

/**
 * 获取URL参数
 * 功能描述：从URL中获取指定参数的值
 * 入参：paramName (string) - 参数名
 * 返回参数：string|null - 参数值
 */
export function getUrlParameter(paramName) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(paramName);
}

/**
 * 跳转到指定页面
 * 功能描述：导航到指定的页面URL
 * 入参：url (string) - 目标URL
 * 返回参数：无
 */
export function navigateToPage(url) {
    window.location.href = url;
}

/**
 * 防抖函数
 * 功能描述：创建一个防抖函数，在指定延迟后执行
 * 入参：func (function) - 要执行的函数, delay (number) - 延迟时间
 * 返回参数：function - 防抖函数
 */
export function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * 节流函数
 * 功能描述：创建一个节流函数，在指定时间间隔内最多执行一次
 * 入参：func (function) - 要执行的函数, limit (number) - 时间间隔
 * 返回参数：function - 节流函数
 */
export function throttle(func, limit) {
    let inThrottle;
    return function (...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 深拷贝对象
 * 功能描述：创建对象的深拷贝
 * 入参：obj (any) - 要拷贝的对象
 * 返回参数：any - 拷贝后的对象
 */
export function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }
    
    if (obj instanceof Date) {
        return new Date(obj.getTime());
    }
    
    if (obj instanceof Array) {
        return obj.map(item => deepClone(item));
    }
    
    if (typeof obj === 'object') {
        const clonedObj = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clonedObj[key] = deepClone(obj[key]);
            }
        }
        return clonedObj;
    }
} 