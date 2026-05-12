<template>
  <div class="memory-fullscreen">
    <div class="memory-header">
      <h2>记忆图谱</h2>
      <button class="close-btn" @click="cancel">✕</button>
    </div>

    <!-- content -->
    <div class="memory-content">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error">
        <span>{{ error }}</span>
        <button class="retry-btn" @click="loadGraphData">重试</button>
      </div>

      <!-- 图谱视图 -->
      <MemoryGraph v-else-if="graphData" :graph-data="graphData" />

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <span>暂无记忆数据</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import MemoryGraph from './MemoryGraph.vue'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const loading = ref(false)
const error = ref('')
const graphData = ref<any>(null)

// 加载图谱数据
const loadGraphData = async () => {
  loading.value = true
  error.value = ''

  try {
    // 动态导入 API
    const { getMemoryGraphApi } = await import('@/utils/chat')
    const result = await getMemoryGraphApi()

    if (result.code === 0 && result.data) {
      console.log(1)
      graphData.value = result.data
      console.log(graphData.value)
    } else {
      error.value = result.message || '获取数据失败'
    }
  } catch (e: any) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}

const cancel = () => {
  emit('close')
}

onMounted(() => {
  loadGraphData()
})
</script>

<style scoped>
.memory-fullscreen {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(12px);
  color: white;
  display: flex;
  flex-direction: column;
  z-index: 20;
  overflow: hidden;
}

.memory-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
}

.memory-header h2 {
  margin: 0;
  font-size: 1.8rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: white;
  cursor: pointer;
  opacity: 0.7;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  opacity: 1;
}

.memory-content {
  flex: 1;

  min-height: 0;

  display: flex;

  overflow: hidden;
}
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: #ef4444;
}

.retry-btn {
  padding: 10px 24px;
  border-radius: 40px;
  background: #3b82f6;
  color: white;
  border: none;
  cursor: pointer;
}

.empty-state {
  color: #64748b;
  font-size: 1.2rem;
}
</style>
