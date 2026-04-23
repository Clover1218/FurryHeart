<script setup lang="ts">
import { ref, computed } from 'vue'
import { NButton, NModal, NInput, NPopover } from 'naive-ui'

/**
 * ✅ 对外事件
 */
const emit = defineEmits<{
  (e: 'login', openId: string, username: string): void
  (e: 'logout'): void
}>()

/**
 * ✅ 状态（组件内部管理 UI）
 */
const isLogin = ref(false)
const openId = ref('')
const username = ref('')

const showLoginModal = ref(false)
const tempOpenId = ref('')

/**
 * 🔐 登录逻辑
 */
const handleLogin = () => {
  if (!tempOpenId.value.trim()) return

  openId.value = tempOpenId.value
  username.value = `User_${tempOpenId.value.slice(-4)}`
  isLogin.value = true

  emit('login', openId.value, username.value)

  showLoginModal.value = false
}

/**
 * 🚪 登出
 */
const logout = () => {
  isLogin.value = false
  openId.value = ''
  username.value = ''
  tempOpenId.value = ''

  emit('logout')
}

/**
 * 🎯 对外暴露（如果父组件想控制）
 */
defineExpose({
  isLogin,
  openId,
  username
})
</script>

<template>
  <div class="login-widget">

    <!-- 未登录 -->
    <n-button
      v-if="!isLogin"
      class="glass-btn"
      @click="showLoginModal = true"
    >
      未登录
    </n-button>

    <!-- 已登录 -->
    <n-popover v-else trigger="click">
      <template #trigger>
        <n-button class="glass-btn">
          已登录：{{ username }}
        </n-button>
      </template>

      <div class="popover-box">
        <n-button size="small" @click="showLoginModal = true">
          重新登录
        </n-button>

        <n-button size="small" type="error" @click="logout">
          退出登录
        </n-button>
      </div>
    </n-popover>

    <!-- 登录弹窗 -->
    <n-modal v-model:show="showLoginModal">
      <div class="modal-card">
        <div class="modal-title">输入 OpenID</div>

        <n-input
          v-model:value="tempOpenId"
          placeholder="请输入 open_id"
        />

        <div class="modal-actions">
          <n-button @click="showLoginModal = false">
            取消
          </n-button>

          <n-button type="primary" @click="handleLogin">
            登录
          </n-button>
        </div>
      </div>
    </n-modal>

  </div>
</template>

<style scoped>
.login-widget {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 100;
}

/* 🌫 玻璃按钮风格（和你整体 UI 统一） */
.glass-btn {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 12px;
}

/* popover */
.popover-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* modal */
.modal-card {
  width: 320px;
  padding: 20px;

  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(16px);

  border-radius: 16px;
}

.modal-title {
  font-size: 14px;
  margin-bottom: 12px;
  font-weight: 600;
}

.modal-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>