<template>
  <router-view />
</template>

<style>
:root {
  --bg-primary: #0a0a0b;
  --bg-secondary: #111113;
  --bg-tertiary: #18181b;
  --bg-elevated: #1f1f23;
  --border-color: #27272a;
  --border-subtle: #1f1f23;
  --text-primary: #fafafa;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;
  --accent-blue: #3b82f6;
  --accent-blue-hover: #2563eb;
  --accent-green: #22c55e;
  --accent-yellow: #eab308;
  --accent-red: #ef4444;
  --accent-purple: #a855f7;
  --accent-cyan: #06b6d4;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
  background: var(--bg-primary);
}

/* Element Plus Dark Theme Overrides */
.el-card {
  background: var(--bg-secondary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--radius-lg) !important;
  color: var(--text-primary) !important;
  --el-card-padding: 20px;
}

.el-card__header {
  background: transparent !important;
  border-bottom: 1px solid var(--border-color) !important;
  color: var(--text-primary) !important;
  font-weight: 600;
  padding: 16px 20px !important;
}

.el-card__body {
  color: var(--text-primary) !important;
}

.el-table {
  background: transparent !important;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-tertiary);
  --el-table-row-hover-bg-color: var(--bg-tertiary);
  --el-table-border-color: var(--border-color);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-secondary);
}

.el-table th.el-table__cell {
  background: var(--bg-tertiary) !important;
  font-weight: 500 !important;
}

.el-table td.el-table__cell {
  border-bottom-color: var(--border-color) !important;
}

.el-button {
  --el-button-text-color: var(--text-primary);
  --el-button-bg-color: var(--bg-tertiary);
  --el-button-border-color: var(--border-color);
  --el-button-hover-bg-color: var(--bg-elevated);
  --el-button-hover-border-color: var(--border-color);
  border-radius: var(--radius-md) !important;
  font-weight: 500;
}

.el-button--primary {
  --el-button-text-color: #fff;
  --el-button-bg-color: var(--accent-blue);
  --el-button-border-color: var(--accent-blue);
  --el-button-hover-bg-color: var(--accent-blue-hover);
  --el-button-hover-border-color: var(--accent-blue-hover);
}

.el-input__wrapper {
  background: var(--bg-tertiary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: none !important;
}

.el-input__wrapper:hover,
.el-input__wrapper.is-focus {
  border-color: var(--accent-blue) !important;
}

.el-input__inner {
  color: var(--text-primary) !important;
}

.el-input__inner::placeholder {
  color: var(--text-muted) !important;
}

.el-select__wrapper {
  background: var(--bg-tertiary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: none !important;
}

.el-tag {
  border-radius: var(--radius-sm) !important;
  font-weight: 500;
}

.el-tag--success {
  background: rgba(34, 197, 94, 0.15) !important;
  border-color: transparent !important;
  color: var(--accent-green) !important;
}

.el-tag--warning {
  background: rgba(234, 179, 8, 0.15) !important;
  border-color: transparent !important;
  color: var(--accent-yellow) !important;
}

.el-tag--danger {
  background: rgba(239, 68, 68, 0.15) !important;
  border-color: transparent !important;
  color: var(--accent-red) !important;
}

.el-tag--info {
  background: rgba(161, 161, 170, 0.15) !important;
  border-color: transparent !important;
  color: var(--text-secondary) !important;
}

.el-dialog {
  background: var(--bg-secondary) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: var(--radius-lg) !important;
}

.el-dialog__header {
  border-bottom: 1px solid var(--border-color) !important;
}

.el-dialog__title {
  color: var(--text-primary) !important;
  font-weight: 600;
}

.el-form-item__label {
  color: var(--text-secondary) !important;
}

.el-descriptions {
  --el-descriptions-item-bordered-label-background: var(--bg-tertiary);
}

.el-descriptions__label {
  background: var(--bg-tertiary) !important;
  color: var(--text-secondary) !important;
}

.el-descriptions__content {
  background: var(--bg-secondary) !important;
  color: var(--text-primary) !important;
}

.el-descriptions__cell {
  border-color: var(--border-color) !important;
}

.el-radio-button__inner {
  background: var(--bg-tertiary) !important;
  border-color: var(--border-color) !important;
  color: var(--text-secondary) !important;
}

.el-radio-button__original-radio:checked + .el-radio-button__inner {
  background: var(--accent-blue) !important;
  border-color: var(--accent-blue) !important;
  color: #fff !important;
}

.el-tabs__item {
  color: var(--text-secondary) !important;
}

.el-tabs__item.is-active {
  color: var(--text-primary) !important;
}

.el-tabs__active-bar {
  background: var(--accent-blue) !important;
}

.el-switch.is-checked .el-switch__core {
  background-color: var(--accent-blue) !important;
  border-color: var(--accent-blue) !important;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}
</style>
