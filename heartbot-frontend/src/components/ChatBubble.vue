<template>
  <div class="bubble-wrapper" :class="role">
    <div class="bubble">

      <!-- 正文 -->
      <div class="content">{{ text }}</div>

      <!-- debug 区 -->
      <div v-if="debug_info" class="debug-section">
        
        <div class="debug-toggle" @click="showDebug = !showDebug">
          {{ showDebug ? '收起调试信息' : '查看调试信息' }}
        </div>

        <div v-show="showDebug" class="debug-box">
          <pre class="debug-text">{{ debug_info }}</pre>
<!-- 
          <button class="copy-btn" @click="copyDebug">
            复制
          </button> -->
        </div>

      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps({
  text: String,
  role: {
    type: String,
    default: 'assistant'
  },
  debug_info: {
    type: String,
    default: ''
  }
})

const showDebug = ref(false)

function copyDebug() {
  if (!props.debug_info) return
  navigator.clipboard.writeText(props.debug_info)
}
</script>

<style scoped>
.bubble-wrapper {
  display: flex;
  width: 100%;
  margin: 12px 0;
  animation: fadeInUp 0.4s ease;
}

.bubble-wrapper.user {
  justify-content: flex-end;
}

.bubble-wrapper.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 60%;
  padding: 12px 16px;
  border-radius: 18px;

  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);

  color: #333;
  font-size: 14px;
  line-height: 1.5;
}

.bubble-wrapper.user .bubble {
  background: rgba(255, 255, 255, 0.75);
}

.bubble-wrapper.ai .bubble {
  background: rgba(255, 255, 255, 0.55);
}

/* debug */
.debug-section {
  margin-top: 8px;
}

.debug-toggle {
  font-size: 12px;
  opacity: 0.6;
  cursor: pointer;
  user-select: none;
}

.debug-toggle:hover {
  opacity: 1;
}

.debug-box {
  margin-top: 6px;
  padding: 8px;
  border-radius: 10px;

  background: rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(8px);
}

.debug-text {
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  color: #444;
}

.copy-btn {
  margin-top: 6px;
  font-size: 12px;
  border: none;
  cursor: pointer;

  background: rgba(255,255,255,0.5);
  padding: 4px 8px;
  border-radius: 6px;
}

/* animation */
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