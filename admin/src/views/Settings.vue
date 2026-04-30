<template>
  <div>
    <el-card header="租户信息" style="margin-bottom:20px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="租户ID">default</el-descriptions-item>
        <el-descriptions-item label="名称">默认租户</el-descriptions-item>
        <el-descriptions-item label="API Key">default-key</el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag type="success">启用</el-tag></el-descriptions-item>
      </el-descriptions>
    </el-card>
    <el-card header="微信配置">
      <el-form label-width="120px">
        <el-form-item label="公众号 Token"><el-input value="(未配置)" disabled /></el-form-item>
        <el-form-item label="AppID"><el-input value="(未配置)" disabled /></el-form-item>
        <el-form-item label="回调 URL"><el-input value="http://YOUR_HOST/api/v1/wechat/callback" disabled /></el-form-item>
      </el-form>
    </el-card>
    <el-card header="通知设置" style="margin-top:20px">
      <el-form label-width="120px">
        <el-form-item label="新工单通知"><el-switch model-value /></el-form-item>
        <el-form-item label="异常告警"><el-switch /></el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
