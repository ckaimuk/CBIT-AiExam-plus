/**
 * 全站多语言支持模块
 * 统一管理所有页面的多语言翻译
 */

class I18nManager {
    constructor() {
        this.translations = {};
        this.currentLanguage = 'en';
        this.systemConfig = {};
        this.initialized = false;
    }

    // 初始化多语言管理器
    async init() {
        try {
            // 加载翻译
            await this.loadTranslations();
            
            // 加载系统配置
            await this.loadSystemConfig();
            
            // 设置语言
            const savedLanguage = localStorage.getItem('language') || this.systemConfig.language || 'en';
            this.setLanguage(savedLanguage);
            
            this.initialized = true;
            
            // 触发初始化完成事件
            document.dispatchEvent(new CustomEvent('i18n:initialized'));
            
        } catch (error) {
            console.error('多语言初始化失败:', error);
        }
    }

    // 加载翻译
    async loadTranslations() {
        try {
            const response = await fetch('/api/translations');
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.translations = result.translations;
                }
            }
        } catch (error) {
            console.error('加载翻译失败:', error);
        }
    }

    // 加载系统配置
    async loadSystemConfig() {
        try {
            const response = await fetch('/api/system-config');
            if (response.ok) {
                const config = await response.json();
                if (config.success) {
                    this.systemConfig = config.data;
                }
            }
        } catch (error) {
            console.error('加载系统配置失败:', error);
        }
    }

    // 设置语言
    setLanguage(lang) {
        this.currentLanguage = lang;
        
        // 更新HTML lang属性
        document.documentElement.lang = lang;
        
        // 更新所有翻译元素
        this.updateAllTranslations();
        
        // 保存语言偏好（除非强制统一语言）
        if (!(this.systemConfig.enforceLanguage === true || this.systemConfig.enforceLanguage === 'true')) {
            localStorage.setItem('language', lang);
        }
        
        // 触发语言改变事件
        document.dispatchEvent(new CustomEvent('i18n:languageChanged', { 
            detail: { language: lang } 
        }));
    }

    // 更新所有翻译元素
    updateAllTranslations() {
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.translate(key);
            if (translation) {
                element.textContent = translation;
            }
        });
        
        // 更新placeholder属性
        const placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
        placeholderElements.forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            const translation = this.translate(key);
            if (translation) {
                element.placeholder = translation;
            }
        });
    }

    // 翻译单个key
    translate(key, defaultValue = '') {
        if (this.translations[this.currentLanguage] && this.translations[this.currentLanguage][key]) {
            return this.translations[this.currentLanguage][key];
        }
        return defaultValue || key;
    }

    // 切换语言
    toggleLanguage() {
        // 检查是否强制统一语言
        if (this.systemConfig.enforceLanguage === true || this.systemConfig.enforceLanguage === 'true') {
            return false; // 不允许切换
        }
        
        const newLang = this.currentLanguage === 'en' ? 'zh' : 'en';
        this.setLanguage(newLang);
        return true;
    }

    // 获取当前语言
    getCurrentLanguage() {
        return this.currentLanguage;
    }

    // 检查是否允许语言切换
    isLanguageSwitchAllowed() {
        return !(this.systemConfig.enforceLanguage === true || this.systemConfig.enforceLanguage === 'true');
    }

    // 应用系统配置
    applySystemConfig() {
        // 应用系统名称
        if (this.systemConfig.systemName) {
            const systemNameElements = document.querySelectorAll('#systemName, .system-name');
            systemNameElements.forEach(el => {
                el.textContent = this.systemConfig.systemName;
            });
            
            // 更新页面标题
            if (document.getElementById('pageTitle')) {
                document.getElementById('pageTitle').textContent = this.systemConfig.systemName;
            } else {
                document.title = this.systemConfig.systemName;
            }
        }

        // 应用logo
        if (this.systemConfig.logo) {
            const logoElements = document.querySelectorAll('#systemLogo, .system-logo');
            logoElements.forEach(el => {
                el.src = this.systemConfig.logo;
                el.className = 'h-10 object-contain'; // 移除尺寸限制
            });
        }

        // 应用favicon
        if (this.systemConfig.favicon) {
            const faviconLink = document.getElementById('faviconLink') || 
                              document.querySelector('link[rel="icon"]');
            if (faviconLink) {
                faviconLink.href = this.systemConfig.favicon;
            }
        }

        // 应用页脚文本
        if (this.systemConfig.footerText) {
            const footerElements = document.querySelectorAll('#footerCopyright, .footer-copyright');
            footerElements.forEach(el => {
                el.textContent = this.systemConfig.footerText;
            });
        }

        // 控制语言切换按钮显示
        const languageToggleElements = document.querySelectorAll('#languageToggle, .language-toggle');
        languageToggleElements.forEach(el => {
            if (this.systemConfig.enforceLanguage === true || this.systemConfig.enforceLanguage === 'true') {
                el.style.display = 'none';
            } else {
                el.style.display = '';
            }
        });
    }

    // 获取系统配置
    getSystemConfig() {
        return this.systemConfig;
    }
}

// 创建全局实例
window.i18n = new I18nManager();

// 页面加载完成后自动初始化
document.addEventListener('DOMContentLoaded', async () => {
    await window.i18n.init();
    
    // 应用系统配置
    window.i18n.applySystemConfig();
    
    // 绑定语言切换按钮
    const languageToggleButtons = document.querySelectorAll('#languageToggle, .language-toggle');
    languageToggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            console.log('🌐 i18n.js 中的语言切换按钮被点击');
            if (window.i18n.toggleLanguage()) {
                // 更新按钮文本
                const currentLang = window.i18n.getCurrentLanguage();
                const langDisplay = button.querySelector('.language-display');
                if (langDisplay) {
                    langDisplay.textContent = currentLang === 'zh' ? '中' : 'EN';
                    console.log('✅ i18n.js 更新按钮文本为:', langDisplay.textContent);
                }
            }
        });
        
        // 初始化按钮文本
        const currentLang = window.i18n.getCurrentLanguage();
        const langDisplay = button.querySelector('.language-display');
        if (langDisplay) {
            langDisplay.textContent = currentLang === 'zh' ? '中' : 'EN';
        }
    });
});

// 辅助函数：获取翻译
function t(key, defaultValue = '') {
    return window.i18n ? window.i18n.translate(key, defaultValue) : (defaultValue || key);
}

// 辅助函数：格式化翻译（支持参数替换）
function tf(key, params = {}, defaultValue = '') {
    let translation = t(key, defaultValue);
    
    // 替换参数
    Object.keys(params).forEach(param => {
        translation = translation.replace(`{${param}}`, params[param]);
    });
    
    return translation;
}
