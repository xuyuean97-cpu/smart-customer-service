// 主要 JavaScript 功能

document.addEventListener('DOMContentLoaded', function() {
    // 移动端导航切换
    initMobileNavigation();
    
    // 平滑滚动
    initSmoothScrolling();
    
    // 页面加载动画
    initLoadAnimations();
    
    // 代码复制功能
    initCodeCopy();
    
    // 主题切换（如果需要）
    // initThemeToggle();
});

// 移动端导航功能
function initMobileNavigation() {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
        
        // 点击菜单项时关闭移动端菜单
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });
        
        // 点击页面其他地方时关闭菜单
        document.addEventListener('click', function(e) {
            if (!hamburger.contains(e.target) && !navMenu.contains(e.target)) {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            }
        });
    }
}

// 平滑滚动功能
function initSmoothScrolling() {
    // 为所有内部链接添加平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                const offsetTop = targetElement.offsetTop - 80; // 考虑固定导航栏的高度
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// 页面加载动画
function initLoadAnimations() {
    // 为特性卡片添加进入动画
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // 观察所有特性卡片
    document.querySelectorAll('.feature-card, .quick-start-item').forEach(card => {
        observer.observe(card);
    });
}

// 代码复制功能
function initCodeCopy() {
    // 为所有代码块添加复制按钮
    document.querySelectorAll('pre[class*="language-"]').forEach(pre => {
        const button = document.createElement('button');
        button.className = 'copy-button';
        button.textContent = '复制';
        button.setAttribute('aria-label', '复制代码');
        
        // 设置按钮样式
        button.style.cssText = `
            position: absolute;
            top: 8px;
            right: 8px;
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        // 设置 pre 容器样式
        pre.style.position = 'relative';
        
        // 添加悬停效果
        pre.addEventListener('mouseenter', () => {
            button.style.opacity = '1';
        });
        
        pre.addEventListener('mouseleave', () => {
            button.style.opacity = '0';
        });
        
        // 复制功能
        button.addEventListener('click', async () => {
            const code = pre.querySelector('code');
            if (code) {
                try {
                    await navigator.clipboard.writeText(code.textContent);
                    button.textContent = '已复制';
                    setTimeout(() => {
                        button.textContent = '复制';
                    }, 2000);
                } catch (err) {
                    console.error('复制失败:', err);
                    // 降级方案
                    const textArea = document.createElement('textarea');
                    textArea.value = code.textContent;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    button.textContent = '已复制';
                    setTimeout(() => {
                        button.textContent = '复制';
                    }, 2000);
                }
            }
        });
        
        pre.appendChild(button);
    });
}

// 主题切换功能（可选）
function initThemeToggle() {
    const themeToggle = document.createElement('button');
    themeToggle.className = 'theme-toggle';
    themeToggle.innerHTML = '🌙';
    themeToggle.setAttribute('aria-label', '切换主题');
    
    // 设置主题切换按钮样式
    themeToggle.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: var(--primary-color);
        color: white;
        border: none;
        font-size: 20px;
        cursor: pointer;
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        transition: all 0.3s ease;
    `;
    
    // 检查保存的主题偏好
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        themeToggle.innerHTML = '☀️';
    }
    
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
        const isDark = document.body.classList.contains('dark-theme');
        themeToggle.innerHTML = isDark ? '☀️' : '🌙';
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
    
    document.body.appendChild(themeToggle);
}

// 工具函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 导航高亮功能（根据当前页面）
function highlightCurrentPage() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath || 
            (currentPath.includes(link.getAttribute('href').replace('.html', '')) && 
             link.getAttribute('href') !== 'index.html')) {
            link.classList.add('active');
        }
    });
}

// 页面滚动时的导航栏效果
function initScrollEffects() {
    const navbar = document.querySelector('.navbar');
    let lastScrollTop = 0;
    
    window.addEventListener('scroll', debounce(() => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // 添加滚动时的背景效果
        if (scrollTop > 100) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        lastScrollTop = scrollTop;
    }, 10));
}

// 表单验证功能（如果页面有表单）
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                    showFieldError(field, '此字段为必填项');
                } else {
                    field.classList.remove('error');
                    hideFieldError(field);
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
}

function showFieldError(field, message) {
    let errorElement = field.parentElement.querySelector('.field-error');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'field-error';
        errorElement.style.cssText = `
            color: var(--danger-color);
            font-size: 0.875rem;
            margin-top: 4px;
        `;
        field.parentElement.appendChild(errorElement);
    }
    errorElement.textContent = message;
}

function hideFieldError(field) {
    const errorElement = field.parentElement.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
}

// 页面性能监控（可选）
function trackPagePerformance() {
    window.addEventListener('load', () => {
        if ('performance' in window) {
            const perfData = performance.getEntriesByType('navigation')[0];
            const loadTime = perfData.loadEventEnd - perfData.loadEventStart;
            console.log(`页面加载时间: ${loadTime}ms`);
        }
    });
}

// 初始化所有功能
document.addEventListener('DOMContentLoaded', function() {
    highlightCurrentPage();
    initScrollEffects();
    initFormValidation();
    trackPagePerformance();
    initMarketingFeatures();
    initAnalytics();
});

// 营销功能初始化
function initMarketingFeatures() {
    // 统计数字动画效果
    initCounterAnimation();
    
    // 客户案例轮播
    initCaseCarousel();
    
    // 表单提交处理
    initBusinessForm();
    
    // 社交分享功能
    initSocialShare();
}

// 统计数字动画效果
function initCounterAnimation() {
    const counters = document.querySelectorAll('.stat-item div:first-child');
    const observerOptions = {
        threshold: 0.5,
        rootMargin: '0px'
    };

    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                counterObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);

    counters.forEach(counter => {
        counterObserver.observe(counter);
    });
}

function animateCounter(element) {
    const text = element.textContent;
    const hasPercent = text.includes('%');
    const hasPlus = text.includes('+');
    const isLessThan = text.includes('<');
    
    let finalValue;
    if (hasPercent) {
        finalValue = parseFloat(text.replace('%', ''));
    } else if (hasPlus) {
        finalValue = parseFloat(text.replace('%', '').replace('+', ''));
    } else if (isLessThan) {
        finalValue = parseFloat(text.replace('<', '').replace('s', ''));
    } else {
        finalValue = parseFloat(text) || 0;
    }

    if (isNaN(finalValue)) return;

    let currentValue = 0;
    const increment = finalValue / 50;
    const timer = setInterval(() => {
        currentValue += increment;
        if (currentValue >= finalValue) {
            currentValue = finalValue;
            clearInterval(timer);
        }
        
        let displayValue;
        if (finalValue >= 100) {
            displayValue = Math.floor(currentValue);
        } else {
            displayValue = currentValue.toFixed(1);
        }
        
        if (hasPercent) {
            element.textContent = displayValue + '%';
        } else if (hasPlus) {
            element.textContent = displayValue + '%+';
        } else if (isLessThan) {
            element.textContent = '<' + displayValue + 's';
        } else if (text === '24/7') {
            element.textContent = '24/7';
        } else {
            element.textContent = displayValue;
        }
    }, 30);
}

// 客户案例轮播
function initCaseCarousel() {
    const caseCards = document.querySelectorAll('.case-card');
    if (caseCards.length === 0) return;
    
    let currentIndex = 0;
    
    // 添加自动轮播效果
    setInterval(() => {
        caseCards.forEach((card, index) => {
            card.style.transform = index === currentIndex ? 'scale(1.05)' : 'scale(1)';
            card.style.zIndex = index === currentIndex ? '10' : '1';
        });
        
        currentIndex = (currentIndex + 1) % caseCards.length;
    }, 5000);
}

// 商务表单处理
function initBusinessForm() {
    const businessForm = document.querySelector('.business-form');
    if (!businessForm) return;
    
    businessForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitButton = this.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        
        // 显示加载状态
        submitButton.textContent = '🔄 提交中...';
        submitButton.disabled = true;
        
        // 收集表单数据
        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());
        
        try {
            // 这里可以接入真实的API
            await simulateFormSubmission(data);
            
            // 成功提示
            showSuccessMessage();
            this.reset();
            
            // 数据分析跟踪
            trackEvent('form_submission', 'business_inquiry', data.company);
            
        } catch (error) {
            showErrorMessage('提交失败，请稍后重试');
        } finally {
            // 恢复按钮状态
            submitButton.textContent = originalText;
            submitButton.disabled = false;
        }
    });
}

async function simulateFormSubmission(data) {
    // 模拟API调用
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (Math.random() > 0.1) { // 90% 成功率
                resolve({ success: true, id: Date.now() });
            } else {
                reject(new Error('Submission failed'));
            }
        }, 2000);
    });
}

function showSuccessMessage() {
    const message = document.createElement('div');
    message.className = 'success-message';
    message.innerHTML = `
        <div style="
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--bg-card);
            padding: 2rem;
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-xl);
            text-align: center;
            z-index: 10000;
            border: 2px solid var(--success-color);
        ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
            <h3 style="color: var(--success-color); margin-bottom: 1rem;">提交成功！</h3>
            <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                我们的销售顾问将在24小时内与您联系<br/>
                感谢您对我们产品的关注！
            </p>
            <button onclick="this.parentElement.parentElement.remove()" 
                    style="background: var(--success-color); color: white; border: none; padding: 0.5rem 1rem; border-radius: var(--radius-md); cursor: pointer;">
                确定
            </button>
        </div>
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 9999;
        " onclick="this.parentElement.remove()"></div>
    `;
    
    document.body.appendChild(message);
    
    // 3秒后自动关闭
    setTimeout(() => {
        if (message.parentElement) {
            message.remove();
        }
    }, 3000);
}

function showErrorMessage(text) {
    const message = document.createElement('div');
    message.className = 'error-message';
    message.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--danger-color);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    message.textContent = text;
    
    document.body.appendChild(message);
    
    // 显示动画
    setTimeout(() => {
        message.style.transform = 'translateX(0)';
    }, 100);
    
    // 3秒后自动隐藏
    setTimeout(() => {
        message.style.transform = 'translateX(100%)';
        setTimeout(() => message.remove(), 300);
    }, 3000);
}

// 社交分享功能
function initSocialShare() {
    // 动态添加分享按钮
    const shareContainer = document.createElement('div');
    shareContainer.className = 'social-share';
    shareContainer.style.cssText = `
        position: fixed;
        right: 20px;
        top: 50%;
        transform: translateY(-50%);
        display: flex;
        flex-direction: column;
        gap: 10px;
        z-index: 1000;
    `;
    
    const shareButtons = [
        { name: '微信', icon: '💬', color: '#07C160', action: 'wechat' },
        { name: '微博', icon: '📱', color: '#E6162D', action: 'weibo' },
        { name: 'QQ', icon: '🐧', color: '#12B7F5', action: 'qq' },
        { name: '复制链接', icon: '🔗', color: '#666', action: 'copy' }
    ];
    
    shareButtons.forEach(button => {
        const btn = document.createElement('button');
        btn.innerHTML = button.icon;
        btn.title = `分享到${button.name}`;
        btn.style.cssText = `
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: none;
            background: ${button.color};
            color: white;
            font-size: 16px;
            cursor: pointer;
            box-shadow: var(--shadow-md);
            transition: all 0.3s ease;
        `;
        
        btn.addEventListener('click', () => shareContent(button.action));
        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'scale(1.1)';
            btn.style.boxShadow = 'var(--shadow-lg)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
            btn.style.boxShadow = 'var(--shadow-md)';
        });
        
        shareContainer.appendChild(btn);
    });
    
    document.body.appendChild(shareContainer);
}

function shareContent(platform) {
    const title = 'AI智能客服系统 - 革命性的平台客户服务解决方案';
    const description = '帮助平台提升服务效率300%，降低人工成本60%，实现24/7无间断智能服务';
    const url = window.location.href;
    
    switch (platform) {
        case 'wechat':
            // 微信分享通常通过二维码
            showQRCode(url, '微信扫码分享');
            break;
        case 'weibo':
            window.open(`https://service.weibo.com/share/share.php?url=${encodeURIComponent(url)}&title=${encodeURIComponent(title + ' ' + description)}`);
            break;
        case 'qq':
            window.open(`https://connect.qq.com/widget/shareqq/index.html?url=${encodeURIComponent(url)}&title=${encodeURIComponent(title)}&summary=${encodeURIComponent(description)}`);
            break;
        case 'copy':
            copyToClipboard(url);
            break;
    }
    
    // 跟踪分享事件
    trackEvent('social_share', platform, url);
}

function showQRCode(url, title) {
    // 这里可以集成二维码生成库
    alert(`${title}\n链接: ${url}\n\n请使用微信扫一扫功能分享`);
}

async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showSuccessMessage('链接已复制到剪贴板');
    } catch (err) {
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showSuccessMessage('链接已复制到剪贴板');
    }
}

// 简单的数据分析跟踪
function initAnalytics() {
    // 页面浏览跟踪
    trackEvent('page_view', 'home', window.location.pathname);
    
    // 滚动深度跟踪
    let maxScroll = 0;
    window.addEventListener('scroll', debounce(() => {
        const scrollPercent = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
        if (scrollPercent > maxScroll) {
            maxScroll = scrollPercent;
            if (maxScroll % 25 === 0) { // 每25%记录一次
                trackEvent('scroll_depth', `${maxScroll}%`, window.location.pathname);
            }
        }
    }, 500));
    
    // 按钮点击跟踪
    document.addEventListener('click', (e) => {
        if (e.target.matches('.btn, button')) {
            const buttonText = e.target.textContent.trim();
            const buttonHref = e.target.href || e.target.dataset.action;
            trackEvent('button_click', buttonText, buttonHref);
        }
    });
}

function trackEvent(category, action, label) {
    // 这里可以接入 Google Analytics, 百度统计等
    console.log('Event tracked:', { category, action, label, timestamp: new Date().toISOString() });
    
    // 示例：发送到自定义分析端点
    if (typeof gtag !== 'undefined') {
        gtag('event', action, {
            event_category: category,
            event_label: label,
            value: 1
        });
    }
}

// 导出功能供其他脚本使用
window.AppUtils = {
    debounce,
    showFieldError,
    hideFieldError,
    trackEvent,
    showSuccessMessage,
    showErrorMessage
};
