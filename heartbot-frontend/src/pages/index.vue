<script setup lang="ts">
import { nextTick, ref } from 'vue'

import ChatLayer from "@/components/ChatLayer.vue"
import InputBox from '@/components/InputBox.vue'
import { loginApi, type LoginResponse } from '@/utils/auth'
import { setToken, removeToken } from '@/utils/token'
import { chatApi, getHistoryApi } from '@/utils/chat'
import LoginWidget from '@/components/LoginWidget.vue'
import SettingsPanel from '@/components/SettingsPanel.vue'
import SettingsButton from '@/components/SettingsButton.vue'
import { configUIApi, configUserUpdateApi } from '@/utils/config'

const messages = ref([
  { role: 'assistant', text: '你来了。' },
])

const nextCursor = ref<string>('')
const chatLayerRef = ref<any>(null)
const isFetchingHistory = ref(false)

const showSettings = ref(false)
const settingsPanelRef = ref<InstanceType<typeof SettingsPanel> | null>(null)

// 应用设置（示例）
function applySettings(settings: any) {
  document.documentElement.style.fontSize = `${settings.fontSize}px`
  if (settings.theme === 'dark') {
    document.body.classList.add('dark-theme')
  } else {
    document.body.classList.remove('dark-theme')
  }
}

const handleSendMessage = async (message: string) => {
  const shouldScroll = chatLayerRef.value?.isAtBottom?.()
  messages.value.push({ role: 'user', text: message })
  await nextTick()
  if (shouldScroll) chatLayerRef.value?.scrollToBottom()

  const result = (await chatApi(message)).data
  messages.value.push({ role: 'ai', text: result.reply })
  await nextTick()
  if (shouldScroll) chatLayerRef.value?.scrollToBottom()
}
const SettingsJson=ref<any>({})
const handleLogin = async (openId: string) => {
  const result: LoginResponse = (await loginApi(openId)).data
  setToken(result.token)

  SettingsJson.value= (await configUIApi()).data
  console.log("awd",SettingsJson)
  const res = (await getHistoryApi(nextCursor.value)).data
  messages.value = []
  messages.value.push(...res.messages)
  nextCursor.value = res.next_cursor || ''

  await nextTick()
  chatLayerRef.value?.scrollToBottom()

}

const handleLogout = () => {
  removeToken()
  messages.value = []
}

const handleLoadMore = async () => {
  if (!nextCursor.value || isFetchingHistory.value) return

  isFetchingHistory.value = true
  chatLayerRef.value?.recordHeight()

  try {
    const result = (await getHistoryApi(nextCursor.value)).data
    messages.value.unshift(...result.messages)
    nextCursor.value = result.next_cursor || ''
  } finally {
    await nextTick()
    chatLayerRef.value?.restoreScroll()
    isFetchingHistory.value = false
  }
}
const handleSettingsPanelSave=async (diff:any) =>{
  console.log("cnm")
  try {
    const result = (await configUserUpdateApi(diff)).data
    // 保存成功后同步设置
    settingsPanelRef.value?.syncSettings()
  } finally {
    showSettings.value = false;
  }
}
</script>

<template>
  <div class="index-page">
    <div class="overlay">
      <div class="header-bar">
        <div class="settings-wrapper">
          <SettingsButton @click="showSettings = true" />
        </div>
        <div class="login-wrapper">
          <LoginWidget
            @login="handleLogin"
            @logout="handleLogout"
          />
        </div>
      </div>

      <div v-if="!showSettings" class="full-chat-area">
        <div class="center-column">
          <ChatLayer
            ref="chatLayerRef"
            :messages="messages"
            @load-more="handleLoadMore"
          />
          <InputBox @send="handleSendMessage" />
        </div>
      </div>

      <SettingsPanel
        ref="settingsPanelRef"
        :settingJson="SettingsJson"
        v-if="showSettings"
        @close="showSettings = false"
        @save="handleSettingsPanelSave"
        @update:settingJson="(value) => SettingsJson = value"
      />
    </div>
  </div>
</template>

<style scoped>
/* 顶部栏 */
.header-bar {
  position: absolute;
  top: 20px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 44px;
  padding: 0 20px;
  pointer-events: none;
  z-index: 15;
}

/* 左右包装器：统一高度 + 垂直居中 */
.settings-wrapper,
.login-wrapper {
  pointer-events: auto;
  /* height: 44px; */
  display: flex;
  align-items: center;
}

.full-chat-area {
  width: 100%;
  display: flex;
  justify-content: center;
  height: 100%;
  min-height: 0;
}

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
  height: 80%;
  overflow: hidden;
  min-height: 0;
  padding-top: 100px;
  padding-bottom: 40px;
}
</style>