/*!
 * API Helper Functions
 * 处理API相关的错误提醒和跳转
 */

/**
 * 处理AI生题API错误
 * @param {Object} error - 错误对象
 * @param {Function} onRedirect - 跳转回调函数
 */
function handleAiGenerationError(error, onRedirect) {
    if (error.error_type === 'api_not_configured') {
        // 显示API未配置的提醒
        showApiConfigurationPrompt(error.message, error.redirect_to, onRedirect);
    } else if (error.error_type === 'api_check_failed') {
        // 显示API检查失败的提醒
        showApiErrorPrompt(error.message, error.redirect_to, onRedirect);
    } else {
        // 显示通用错误
        showGeneralError(error.message || '生成题目失败，请重试');
    }
}

/**
 * 显示API配置提醒对话框
 * @param {string} message - 错误消息
 * @param {string} redirectTo - 跳转URL
 * @param {Function} onRedirect - 跳转回调函数
 */
function showApiConfigurationPrompt(message, redirectTo, onRedirect) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white rounded-lg p-6 max-w-md mx-4 shadow-xl">
            <div class="flex items-center mb-4">
                <i class="ri-settings-3-line text-blue-500 text-xl mr-3"></i>
                <h3 class="text-lg font-medium text-gray-900">需要配置API</h3>
            </div>
            <div class="mb-6">
                <p class="text-gray-600">${message}</p>
                <div class="mt-4 p-3 bg-blue-50 rounded-lg">
                    <p class="text-sm text-blue-700">
                        <i class="ri-information-line mr-1"></i>
                        您可以配置以下任一API提供商：
                    </p>
                    <ul class="mt-2 text-sm text-blue-600 list-disc list-inside">
                        <li>OpenRouter - 多模型聚合平台</li>
                        <li>OpenAI - GPT模型官方API</li>
                        <li>Anthropic - Claude模型官方API</li>
                    </ul>
                </div>
            </div>
            <div class="flex space-x-3">
                <button id="configureApiBtn" class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    <i class="ri-settings-3-line mr-2"></i>去配置API
                </button>
                <button id="cancelApiBtn" class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
                    取消
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 绑定事件
    document.getElementById('configureApiBtn').addEventListener('click', () => {
        document.body.removeChild(modal);
        if (onRedirect) {
            onRedirect(redirectTo);
        } else {
            window.location.href = redirectTo;
        }
    });
    
    document.getElementById('cancelApiBtn').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    // 点击遮罩关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

/**
 * 显示API错误提醒对话框
 * @param {string} message - 错误消息
 * @param {string} redirectTo - 跳转URL
 * @param {Function} onRedirect - 跳转回调函数
 */
function showApiErrorPrompt(message, redirectTo, onRedirect) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white rounded-lg p-6 max-w-md mx-4 shadow-xl">
            <div class="flex items-center mb-4">
                <i class="ri-error-warning-line text-yellow-500 text-xl mr-3"></i>
                <h3 class="text-lg font-medium text-gray-900">API异常</h3>
            </div>
            <div class="mb-6">
                <p class="text-gray-600">${message}</p>
                <div class="mt-4 p-3 bg-yellow-50 rounded-lg">
                    <p class="text-sm text-yellow-700">
                        <i class="ri-information-line mr-1"></i>
                        请检查以下可能的问题：
                    </p>
                    <ul class="mt-2 text-sm text-yellow-600 list-disc list-inside">
                        <li>API密钥是否正确配置</li>
                        <li>网络连接是否正常</li>
                        <li>API额度是否充足</li>
                    </ul>
                </div>
            </div>
            <div class="flex space-x-3">
                <button id="checkApiBtn" class="flex-1 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors">
                    <i class="ri-settings-3-line mr-2"></i>检查设置
                </button>
                <button id="retryBtn" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    重试
                </button>
                <button id="cancelErrorBtn" class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
                    取消
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 绑定事件
    document.getElementById('checkApiBtn').addEventListener('click', () => {
        document.body.removeChild(modal);
        if (onRedirect) {
            onRedirect(redirectTo);
        } else {
            window.location.href = redirectTo;
        }
    });
    
    document.getElementById('retryBtn').addEventListener('click', () => {
        document.body.removeChild(modal);
        // 重试逻辑由调用方处理
    });
    
    document.getElementById('cancelErrorBtn').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    // 点击遮罩关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

/**
 * 显示通用错误提醒
 * @param {string} message - 错误消息
 */
function showGeneralError(message) {
    // 如果页面有现成的提示系统，使用现成的
    if (typeof showMessage === 'function') {
        showMessage(message, 'error');
        return;
    }
    
    // 否则创建简单的错误提示
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 max-w-sm';
    toast.innerHTML = `
        <div class="flex items-center">
            <i class="ri-error-warning-line mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (toast.parentNode) {
            document.body.removeChild(toast);
        }
    }, 3000);
}

/**
 * 检查API状态并显示状态信息
 * @param {Function} onSuccess - 成功回调
 * @param {Function} onError - 错误回调
 */
async function checkApiStatus(onSuccess, onError) {
    try {
        const response = await fetch('/api/admin/api-status');
        const result = await response.json();
        
        if (result.success && result.status.available) {
            if (onSuccess) onSuccess(result.status);
        } else {
            if (onError) onError(result.status);
        }
    } catch (error) {
        console.error('检查API状态失败:', error);
        if (onError) onError({
            available: false,
            message: '无法获取API状态'
        });
    }
}

// 导出函数供全局使用
window.ApiHelper = {
    handleAiGenerationError,
    showApiConfigurationPrompt,
    showApiErrorPrompt,
    showGeneralError,
    checkApiStatus
};
