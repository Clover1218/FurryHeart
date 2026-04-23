<template>
  <div
    class="bubble-wrapper"
    :class="role"
  >
    <div class="bubble">
      <div class="content">{{ text }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  text: String,
  role: {
    type: String, // 'user' | 'ai'
    default: 'assistant'
  }
})
</script>

<style scoped>
.bubble-wrapper {
  display: flex;
  width: 100%;
  margin: 12px 0;
  animation: fadeInUp 0.4s ease;
}

/* 用户靠右 */
.bubble-wrapper.user {
  justify-content: flex-end;
}

/* AI靠左 */
.bubble-wrapper.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 60%;
  padding: 12px 16px;
  border-radius: 18px;

  /* 🌟 核心：融入场景 */
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);

  /* 轻微阴影 */
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);

  color: #333;
  font-size: 14px;
  line-height: 1.5;
}

/* 用户稍微深一点点（但不要太明显） */
.bubble-wrapper.user .bubble {
  background: rgba(255, 255, 255, 0.75);
}

/* AI更柔一点 */
.bubble-wrapper.ai .bubble {
  background: rgba(255, 255, 255, 0.55);
}

/* 动画（很关键，别删） */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>