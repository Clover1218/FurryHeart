<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'send', message: string): void
}>()

const inputText = ref('2')

const handleSend = () => {
  if (inputText.value.trim()) {
    emit('send', inputText.value)
    inputText.value = ''
  }
}

const handleKeyPress = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="input-box">
    <input
      type="text"
      v-model="inputText"
      placeholder="输入消息..."
      @keypress="handleKeyPress"
    />
    <button @click="handleSend">发送</button>
  </div>
</template>

<style scoped>
.input-box {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid rgba(0,0,0,0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
}

input:focus {
  border-color: rgba(0,0,0,0.2);
  box-shadow: 0 0 0 2px rgba(0,0,0,0.05);
}

button {
  padding: 12px 20px;
  border: none;
  border-radius: 18px;
  background: rgba(0,0,0,0.8);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

button:hover {
  background: rgba(0,0,0,0.9);
  transform: translateY(-1px);
}

button:active {
  transform: translateY(0);
}
</style>
