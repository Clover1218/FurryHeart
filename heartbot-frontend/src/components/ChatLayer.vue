<script setup lang="ts">
import { ref, nextTick } from 'vue'
import ChatBubble from './ChatBubble.vue'

interface Message {
  role: string
  text: string
}

defineProps<{
  messages: Message[]
}>()

const emit = defineEmits<{
  (e: 'loadMore'): void
}>()

const chatRef = ref<HTMLElement | null>(null)

let prevScrollHeight = 0
let loading = false // ⭐ 防抖锁

const isAtBottom = () => {
  const el = chatRef.value
  if (!el) return true

  return el.scrollTop + el.clientHeight >= el.scrollHeight - 50
}

const scrollToBottom = async () => {
  await nextTick()
  const el = chatRef.value
  if (!el) return

  el.scrollTop = el.scrollHeight
}

const recordHeight = () => {
  const el = chatRef.value
  if (!el) return

  prevScrollHeight = el.scrollHeight
}

const restoreScroll = async () => {
  await nextTick()
  const el = chatRef.value
  if (!el) return

  const newHeight = el.scrollHeight
  el.scrollTop = newHeight - prevScrollHeight

  // ⭐ 解锁
  loading = false
}

const handleScroll = () => {
  const el = chatRef.value
  if (!el) return

  // ⭐ 已在加载中，直接忽略
  if (loading) return

  if (el.scrollTop <= 10) {
    loading = true
    emit('loadMore')
  }
}

defineExpose({
  scrollToBottom,
  recordHeight,
  restoreScroll,
  isAtBottom
})
</script>
<template>
  <div class="chat-layer" ref="chatRef" @scroll="handleScroll">
    <ChatBubble
      v-for="(msg, index) in messages"
      :key="index"
      :text="msg.text"
      :role="msg.role"
    />
  </div>
</template>

<style scoped>
.chat-layer {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  scrollbar-width: none;
  padding: 0 8px;
}
</style>