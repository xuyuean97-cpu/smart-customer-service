<template>
  <div class="settings-page">
    <!-- Tenant Info -->
    <div class="settings-section">
      <div class="section-header">
        <div class="section-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div class="section-title">
          <h2>租户信息</h2>
          <p>管理您的租户配置和基本信息</p>
        </div>
      </div>
      <div class="settings-card">
        <div class="info-grid">
          <div class="info-item">
            <label>租户ID</label>
            <div class="info-value">
              <span>default</span>
              <button class="copy-btn" title="复制">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="info-item">
            <label>名称</label>
            <div class="info-value">
              <span>默认租户</span>
            </div>
          </div>
          <div class="info-item">
            <label>API Key</label>
            <div class="info-value secret">
              <span>••••••••••••••••</span>
              <button class="copy-btn" title="显示/复制">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="info-item">
            <label>状态</label>
            <div class="info-value">
              <span class="status-badge active">
                <span class="status-dot"></span>
                启用
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- WeChat Config -->
    <div class="settings-section">
      <div class="section-header">
        <div class="section-icon green">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/>
          </svg>
        </div>
        <div class="section-title">
          <h2>微信配置</h2>
          <p>配置公众号接入参数</p>
        </div>
      </div>
      <div class="settings-card">
        <div class="form-group">
          <label>公众号 Token</label>
          <div class="input-with-status">
            <input type="text" value="(未配置)" disabled class="form-input disabled" />
            <span class="config-status pending">待配置</span>
          </div>
        </div>
        <div class="form-group">
          <label>AppID</label>
          <div class="input-with-status">
            <input type="text" value="(未配置)" disabled class="form-input disabled" />
            <span class="config-status pending">待配置</span>
          </div>
        </div>
        <div class="form-group">
          <label>回调 URL</label>
          <div class="input-with-copy">
            <input type="text" value="http://YOUR_HOST/api/v1/wechat/callback" disabled class="form-input" />
            <button class="copy-btn">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
              </svg>
            </button>
          </div>
          <span class="form-hint">将此 URL 填入微信公众平台服务器配置</span>
        </div>
        <div class="form-actions">
          <button class="primary-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
              <polyline points="17,21 17,13 7,13 7,21"/>
              <polyline points="7,3 7,8 15,8"/>
            </svg>
            保存配置
          </button>
        </div>
      </div>
    </div>

    <!-- Notification Settings -->
    <div class="settings-section">
      <div class="section-header">
        <div class="section-icon yellow">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 01-3.46 0"/>
          </svg>
        </div>
        <div class="section-title">
          <h2>通知设置</h2>
          <p>配置系统通知和告警规则</p>
        </div>
      </div>
      <div class="settings-card">
        <div class="toggle-list">
          <div class="toggle-item">
            <div class="toggle-info">
              <h4>新工单通知</h4>
              <p>当有新工单创建时发送通知</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" checked />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div class="toggle-info">
              <h4>异常告警</h4>
              <p>系统异常或服务中断时发送告警</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div class="toggle-info">
              <h4>每日报告</h4>
              <p>每日发送运营数据汇总报告</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" checked />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div class="toggle-info">
              <h4>用量预警</h4>
              <p>当 API 用量接近限额时提醒</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" checked />
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 800px;
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.section-icon {
  width: 44px;
  height: 44px;
  background: rgba(59, 130, 246, 0.15);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-blue);
  flex-shrink: 0;
}

.section-icon svg {
  width: 22px;
  height: 22px;
}

.section-icon.green {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.section-icon.yellow {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
}

.section-title h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.section-title p {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.settings-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  font-size: 14px;
  color: var(--text-primary);
}

.info-value.secret span {
  letter-spacing: 2px;
}

.copy-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: auto;
  transition: all 0.15s ease;
}

.copy-btn:hover {
  background: var(--bg-elevated);
  color: var(--accent-blue);
}

.copy-btn svg {
  width: 16px;
  height: 16px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}

.status-badge.active {
  color: var(--accent-green);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-green);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.form-group {
  margin-bottom: 20px;
}

.form-group:last-of-type {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  height: 42px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0 14px;
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
}

.form-input:focus {
  border-color: var(--accent-blue);
}

.form-input.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.input-with-status {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-status .form-input {
  padding-right: 100px;
}

.config-status {
  position: absolute;
  right: 12px;
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.config-status.pending {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
}

.config-status.configured {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.input-with-copy {
  display: flex;
  gap: 8px;
}

.input-with-copy .form-input {
  flex: 1;
}

.input-with-copy .copy-btn {
  width: 42px;
  height: 42px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.form-hint {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 8px;
}

.form-actions {
  padding-top: 4px;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  height: 42px;
  background: var(--accent-blue);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.primary-btn:hover {
  background: var(--accent-blue-hover);
}

.primary-btn svg {
  width: 18px;
  height: 18px;
}

.toggle-list {
  display: flex;
  flex-direction: column;
}

.toggle-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
}

.toggle-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.toggle-item:first-child {
  padding-top: 0;
}

.toggle-info h4 {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.toggle-info p {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.toggle-switch {
  position: relative;
  width: 44px;
  height: 24px;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  inset: 0;
  background: var(--bg-tertiary);
  border-radius: 24px;
  transition: all 0.2s ease;
}

.slider::before {
  content: '';
  position: absolute;
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background: var(--text-muted);
  border-radius: 50%;
  transition: all 0.2s ease;
}

.toggle-switch input:checked + .slider {
  background: var(--accent-blue);
}

.toggle-switch input:checked + .slider::before {
  background: white;
  transform: translateX(20px);
}
</style>
