<template>
  <el-container class="layout">
    <el-aside width="220px">
      <div class="logo">🛒 电商客服</div>
      <el-menu :default-active="route.path" router :collapse="false" background-color="#304156" text-color="#bfcbd9" active-text-color="#409eff">
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon><span>运营概览</span></el-menu-item>
        <el-menu-item index="/tickets"><el-icon><Ticket /></el-icon><span>工单管理</span></el-menu-item>
        <el-menu-item index="/conversations"><el-icon><ChatDotRound /></el-icon><span>对话历史</span></el-menu-item>
        <el-menu-item index="/users"><el-icon><User /></el-icon><span>用户管理</span></el-menu-item>
        <el-menu-item index="/billing"><el-icon><Coin /></el-icon><span>用量计费</span></el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon><span>系统设置</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <span class="title">{{ route.meta.title || '后台管理' }}</span>
        <div class="topbar-right">
          <span class="user-info">{{ auth.user?.phone || 'Admin' }}</span>
          <el-button text @click="auth.logout()">退出</el-button>
        </div>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
const route = useRoute()
const auth = useAuthStore()
</script>

<style scoped>
.layout { height: 100vh; }
.el-aside { background: #304156; overflow-x: hidden; }
.logo { color: #fff; text-align: center; padding: 16px; font-size: 16px; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,.1); }
.topbar { background: #fff; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e6e6e6; padding: 0 20px; }
.topbar .title { font-size: 18px; font-weight: 500; }
.topbar-right { display: flex; align-items: center; gap: 12px; }
.user-info { color: #606266; }
.el-main { background: #f5f7fa; padding: 20px; }
</style>
