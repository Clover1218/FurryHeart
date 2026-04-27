<!-- SettingsPanel.vue -->
<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { nextTick } from 'vue'

const textareaRefs = ref(new Set<HTMLTextAreaElement>())

function register(el: HTMLTextAreaElement | null) {
  if (el) textareaRefs.value.add(el)
}
function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  if (!el) return

  el.style.height = 'auto'

  const max = 140
  el.style.height = Math.min(el.scrollHeight, max) + 'px'
  const scrollHeight = el.scrollHeight
    if (scrollHeight <= max) {
    el.style.height = scrollHeight + 'px'
    el.style.overflowY = 'hidden'
  } else {
    el.style.height = max + 'px'
    el.style.overflowY = 'auto'
  }
}
const props = defineProps<{
  settingJson: any
}>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', payload: any): void // 只返回 diff
  (e: 'update:settingJson', value: any): void // 通知外部更新 settingJson
}>()
const localSettings = ref<any>({})
onMounted(async () => {
  await init()
  await nextTick()

  textareaRefs.value.forEach((el) => {
    autoResize({ target: el } as unknown as Event)
  })
})
function parseCurrentValue(val: string, type: string) {
  try {
    const parsed = JSON.parse(val)

    if (type === 'list') {
      return Array.isArray(parsed) ? parsed : []
    }

    return parsed
  } catch (e) {
    if (type === 'list') return []
    return { text: val }
  }
}
const falseSettingJson=ref<any>({})

async function init() {
  const raw = props.settingJson
  if (!raw) return

  // ❗️只做一次深拷贝
  const copy =JSON.parse(JSON.stringify(raw))

  localSettings.value = copy

  localSettings.value.prompt.forEach((item: any) => {
    item.current_value_obj = parseCurrentValue(item.current_value, item.type)
  })

  await nextTick()

    // const list = document.querySelectorAll('.auto-textarea')

    // list.forEach((el) => {
    //   autoResize({ target: el } as unknown as Event)
    // })
    // localSettings.value = JSON.parse(JSON.stringify(clone));
    //   console.log(localSettings.value)
    // falseSettingJson.value=JSON.parse(JSON.stringify(clone));
} 

const initialized = ref(false)

watch(
  () => props.settingJson,
  async (val) => {
    if (!val || initialized.value) return

    await init()
  },
  { immediate: true }
)


// watch(
//   () => localSettings.value,
//   async () => {
//     await nextTick()

//     textareaRefs.value.forEach((el) => {
//       autoResize({ target: el } as unknown as Event)
//     })
//   },
//   { deep: true }
// )
function encodeCurrentValue(obj: any, type: string) {
  if (type === 'list') {
    return JSON.stringify(obj)
  }
  return JSON.stringify(obj)
}
function getDiff() {
  const original = props.settingJson
  const updated = localSettings.value
  for (const item of updated.prompt) {
        item.current_value = encodeCurrentValue(item.current_value_obj,item.type)
    }
  console.log(original)
  console.log(updated)
  console.log(original==updated)
  const diff: any = {}

  if (!original?.prompt) return diff

  const origMap = new Map(
    original.prompt.map((i: any) => [i.key, i.current_value])
  )

  const updatedList = updated.prompt

  for (const item of updatedList) {
    const oldVal = origMap.get(item.key)

    if (oldVal !== item.current_value) {
      diff[item.key] = item.current_value
    }
  }
  console.log(diff)
  return diff
}

/**
 * ✅ 7. 保存（只提交变更）
 */
function saveSettings() {
  localSettings.value.prompt.forEach((item: any) => {
    item.current_value = encodeCurrentValue(
      item.current_value_obj,
      item.type
    )
  })

  const diff = getDiff()
  emit('save', diff)
}

/**
 * 取消
 */
function cancel() {
  emit('close')
}

/**
 * 同步设置（当外部保存成功时调用）
 */
let syncing= false
function syncSettings() {
  syncing = true
  emit('update:settingJson', JSON.parse(JSON.stringify(localSettings.value)))

  nextTick(() => {
    syncing = false
  })
}

// 暴露方法给外部
defineExpose({
  syncSettings
})
function addListItem(item: any) {
  if (!item.current_value_obj.length) {
    item.current_value_obj.push({})
    return
  }

  const template = item.current_value_obj[0]

  const newItem: any = {}

  Object.keys(template).forEach((key) => {
    newItem[key] = ''
  })

  item.current_value_obj.push(newItem)
}
</script>

<template>
  <div class="settings-fullscreen">

    <!-- header -->
    <div class="settings-header">
      <h2>设置</h2>
      <button class="close-btn" @click="cancel">✕</button>
    </div>

    <!-- content -->
    <div class="settings-content">

      <!-- prompt 动态渲染 -->
      <div class="setting-group">
        <h3>Prompt 配置</h3>

        <div
          v-for="item in localSettings.prompt"
          :key="item.key"
          class="prompt-item"
        >
        <div class="field">
          <label>
            {{ item.description }}
          </label>

          <textarea
            v-if="item.type === 'string'"
            v-model="item.current_value_obj.text"
            class="glass-control textarea auto-textarea"
            rows="1"
            :ref="(el: any) => register(el)"
            @input="autoResize"

          />

          <!-- ✅ list -->
          <div v-else-if="item.type === 'list'" class="list-editor">
          
            <div
              v-for="(row, rowIndex) in item.current_value_obj"
              :key="rowIndex"
              class="list-item"
            >
              
              <!-- 动态字段 -->
              <div
                v-for="(val, key) in row"
                :key="key"
                class="list-field"
              >
                <label v-if="String(key)== 'scene_name'">场景名称</label>
                <label v-if="String(key)== 'condition'">触发条件</label>
                <label v-if="String(key)== 'response_text'">回复策略</label>
                <textarea
                  v-model="row[key]"
                  :placeholder="String(key)"
                  class="glass-control textarea auto-textarea"
                  :ref="(el: any) => register(el)"
                  @input="autoResize"

                />
              </div>
            
              <!-- 删除 -->
              <button
                class="delete-btn"
                @click="item.current_value_obj.splice(rowIndex, 1)"
              >
                删除
              </button>
            </div>
          
            <!-- 新增 -->
            <button
              class="add-btn"
              @click="addListItem(item)"
            >
              + 添加一项
            </button>
          
          </div>
        </div>
        </div>
      </div>

    </div>

    <!-- footer -->
    <div class="settings-footer">
      <button class="cancel-btn" @click="cancel">取消</button>
      <button class="save-btn" @click="saveSettings">
        保存修改
      </button>
    </div>

  </div>
</template>

<style scoped>
.field {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.settings-fullscreen {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  color: white;
  display: flex;
  flex-direction: column;
  z-index: 20;
  overflow-y: auto;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 1px solid rgba(255,255,255,0.2);
}

.settings-header h2 {
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
}
.close-btn:hover {
  opacity: 1;
}

.settings-content {
  flex: 1;
  max-width: 600px;
  width: 100%;
  margin: 0 auto;
  padding: 30px 20px;
}

.setting-group {
  margin-bottom: 32px;
  background: rgba(255,255,255,0.1);
  border-radius: 16px;
  padding: 20px;
  width: 100%;
  box-sizing: border-box;
}

.setting-group h3 {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 1.3rem;
}

.setting-group label {
  display: block;
  margin: 16px 0 6px 0;
  font-weight: 500;
}

.setting-group select, 
.setting-group input[type="range"] {
  width: 100%;
  padding: 8px;
  border-radius: 8px;
  border: none;
  background: rgba(255,255,255,0.2);
  color: white;
}

.setting-group input[type="checkbox"] {
  width: auto;
  margin-right: 8px;
}

.settings-footer {
  padding: 20px 30px;
  border-top: 1px solid rgba(255,255,255,0.2);
  display: flex;
  justify-content: flex-end;
  gap: 16px;
}

.cancel-btn, .save-btn {
  padding: 10px 24px;
  border-radius: 40px;
  font-size: 1rem;
  cursor: pointer;
  border: none;
}

.cancel-btn {
  background: rgba(255,255,255,0.2);
  color: white;
}
.save-btn {
  background: #007bff;
  color: white;
}
input[type="range"] {
  width: 100%;
}
.glass-control {
  width: 100% !important;
  display: block;
  box-sizing: border-box;
}
.textarea {
  width: 100%;
  box-sizing: border-box;

  padding: 10px 12px;
  border-radius: 2px;

  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.08);

  color: rgba(255, 255, 255, 0.92);
  font-size: 14px;
  line-height: 1.5;

  backdrop-filter: blur(14px);

  resize: none;

  min-height: 44px;
  max-height: 140px;

  transition: all 0.2s ease;
}
.textarea:focus {
  outline: none;

  border-color: rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.12);

  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08);
}
.textarea:hover {
  border-color: rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.1);
}
.textarea::-webkit-scrollbar {
  width: 6px;
}

.textarea::-webkit-scrollbar-track {
  background: transparent;
}

.textarea::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 6px;
}

.textarea::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.35);
}
.textarea::placeholder {
  color: rgba(255, 255, 255, 0.4);
}
.list-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-item {
  padding: 12px;
  border-radius: 10px;
  background: rgba(255,255,255,0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-field input {
  width: 100%;
  padding: 8px;
  border-radius: 6px;
  border: none;
  background: rgba(255,255,255,0.2);
  color: white;
}

.add-btn {
  margin-top: 8px;
  padding: 8px;
  border-radius: 8px;
  background: #28a745;
  color: white;
  border: none;
  cursor: pointer;
}

.delete-btn {
  align-self: flex-end;
  padding: 4px 10px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
</style>