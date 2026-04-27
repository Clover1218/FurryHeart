<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useDialog ,NButton} from 'naive-ui'
import ChatLayer from "@/components/ChatLayer.vue"
import InputBox from '@/components/InputBox.vue'
import { loginApi, type LoginResponse } from '@/utils/auth'
import { setToken, removeToken } from '@/utils/token'
import { chatApi, clearHistoryApi, getHistoryApi } from '@/utils/chat'
import LoginWidget from '@/components/LoginWidget.vue'
import SettingsPanel from '@/components/SettingsPanel.vue'
import SettingsButton from '@/components/SettingsButton.vue'
import { configUIApi, configUserUpdateApi } from '@/utils/config'
const dialog = useDialog()
const messages = ref([
  { role: 'assistant', text: '你来了。' ,debug_info:""},
])
const handleClearHistory = (e?: MouseEvent) => {
  (e?.currentTarget as HTMLButtonElement)?.blur?.()

  dialog.warning({
    title: '确认清空记录？',
    content: '这个操作不可恢复，确定要删除所有聊天记录吗？',
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        // 👇 这里你自己实现
        const result=await clearHistoryApi()

        // 本地清空
        messages.value=[]

        nextCursor.value = ''

        await nextTick()
        chatLayerRef.value?.scrollToBottom()
      } catch (e) {
        console.error(e)
      }
    }
  })
}
const nextCursor = ref<string>('')
const chatLayerRef = ref<any>(null)
const isFetchingHistory = ref(false)

const showSettings = ref(false)
const settingsPanelRef = ref<InstanceType<typeof SettingsPanel> | null>(null)


const handleSendMessage = async (message: string) => {
  const shouldScroll = chatLayerRef.value?.isAtBottom?.()
  messages.value.push({ role: 'user', text: message ,debug_info:""})
  await nextTick()
  if (shouldScroll) chatLayerRef.value?.scrollToBottom()

  const result = (await chatApi(message)).data
  messages.value.push({ role: 'ai', text: result.reply ,debug_info: result.debug_info})
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
  messages.value.push(...res.messages.map((msg: any) => ({ ...msg, debug_info: msg.debug_info || '' })))
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
    messages.value.unshift(...result.messages.map((msg: any) => ({ ...msg, debug_info: msg.debug_info || '' })))
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
            <n-button
    class="glass-btn danger-btn"
    @click="handleClearHistory"
  >
    清空记录
  </n-button>
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
.danger-btn {
  margin-left: 10px;
  background: rgba(255, 80, 80, 0.7);
  color: black;
  
}
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
</style>