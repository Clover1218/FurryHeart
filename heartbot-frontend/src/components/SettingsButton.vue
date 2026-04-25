<!-- components/SettingsButton.vue-->
<script setup lang="ts">
import { NButton } from 'naive-ui'

const emit = defineEmits<{
  (e: 'click'): void
}>()
</script>

<template>
  <n-button class="glass-btn" @click="emit('click')">
    设置
  </n-button>
</template>

<style scoped>
.login-widget {
  display: flex;
  align-items: center;
}

.glass-btn {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

/* popover */
.popover-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style> 


