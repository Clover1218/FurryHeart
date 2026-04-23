<script setup lang="ts">
import { nextTick, ref } from 'vue'

import ChatLayer from "@/components/ChatLayer.vue"
import InputBox from '@/components/InputBox.vue'
import { loginApi } from '@/utils/auth'
import { setToken, removeToken } from '@/utils/token'
import { chatApi, getHistoryApi } from '@/utils/chat'
import LoginWidget from '@/components/LoginWidget.vue'

const messages = ref([
  { role: 'assistant', text: '你来了。' },
])

const nextCursor = ref<string>('')
const chatLayerRef = ref<any>(null)
const isFetchingHistory = ref(false)
/**
 * 发送消息
 */
const handleSendMessage = async (message: string) => {
  // 👉 先判断是否在底部（关键）
  const shouldScroll = chatLayerRef.value?.isAtBottom?.()

  messages.value.push({
    role: 'user',
    text: message
  })

  await nextTick()

  if (shouldScroll) {
    chatLayerRef.value?.scrollToBottom()
  }

  const result = await chatApi(message)

  messages.value.push({
    role: 'ai',
    text: result.reply
  })

  await nextTick()

  // 👉 AI回复也同样判断
  if (shouldScroll) {
    chatLayerRef.value?.scrollToBottom()
  }
}

/**
 * 登录
 */
const handleLogin = async (openId: string) => {
  const result = await loginApi(openId)
  setToken(result.token)

  const res = await getHistoryApi(nextCursor.value)
  messages.value=[]
  messages.value.push(...res.messages)
  nextCursor.value = res.next_cursor || ''

  await nextTick()
  chatLayerRef.value?.scrollToBottom()
}

/**
 * 退出
 */
const handleLogout = () => {
  removeToken()
  messages.value=[]
}

/**
 * 上拉加载
 */
const handleLoadMore = async () => {
  if (!nextCursor.value || isFetchingHistory.value) return

  isFetchingHistory.value = true

  chatLayerRef.value?.recordHeight()

  try {
    const result = await getHistoryApi(nextCursor.value)

    messages.value.unshift(...result.messages)
    nextCursor.value = result.next_cursor || ''
  } finally {
    await nextTick()

    chatLayerRef.value?.restoreScroll()

    isFetchingHistory.value = false
  }
}
</script>

<template>
  <div class="index-page">
    <div class="overlay">

      <LoginWidget
        @login="handleLogin"
        @logout="handleLogout"
      />

      <div class="center-column">

        <ChatLayer
          ref="chatLayerRef"
          :messages="messages"
          @load-more="handleLoadMore"
        />

        <InputBox @send="handleSendMessage" />

      </div>

    </div>
  </div>
</template>

<style scoped>
.index-page {
  position: fixed;
  inset: 0;

  background-image: url('@/resources/background.png');
  background-size: auto 100vh;
  background-position: center;
  background-repeat: no-repeat;
}

.overlay {
  position: absolute;
  inset: 0;

  display: flex;
  justify-content: center;
}

.center-column {
  width: 600px;
  max-width: 90vw;

  display: flex;
  flex-direction: column;

  height:80%;
  overflow: hidden;
  min-height: 0;

  padding-top: 100px;
  padding-bottom: 40px;
}
</style>