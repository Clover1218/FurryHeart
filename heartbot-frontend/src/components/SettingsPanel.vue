<!-- SettingsPanel.vue -->
<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { nextTick } from 'vue'

const textareaRefs = ref<HTMLTextAreaElement[]>([])
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
/**
 * ✅ 1. Props：外部传入配置
 */
const props = defineProps<{
  settingJson: any
}>()

/**
 * ✅ 2. 事件
 */
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', payload: any): void // 只返回 diff
  (e: 'update:settingJson', value: any): void // 通知外部更新 settingJson
}>()

/**
 * ✅ 3. 本地编辑副本（关键）
 */
const localSettings = ref<any>({})

/**
 * ✅ 4. 初始化
 */
onMounted(async () => {
  init()
  await nextTick()

  textareaRefs.value.forEach((el) => {
    autoResize({ target: el } as unknown as Event)
  })
})
function parseCurrentValue(val: string) {
  try {
    return JSON.parse(val)
  } catch (e) {
    return { text: val } // fallback
  }
}
const falseSettingJson=ref<any>({})
function init() {
    console.log("inside",props.settingJson)
    localSettings.value = JSON.parse(JSON.stringify(props.settingJson))

  localSettings.value.prompt.forEach((item: any) => {
    item.current_value_obj = parseCurrentValue(item.current_value)
  })
    const clone={
    "code": 0,
    "message": "success",
    "data": {
        "prompt": [
            {
                "key": "prompt.system_base",
                "config_key": "system_base",
                "type": "string",
                "options": null,
                "description": "基础人格",
                "current_value": "{\"text\": \"姓名：绒绒\\n人物基本信息：你是绒绒，还不认识用户，正在慢慢熟悉彼此，要和用户从“拘谨的新朋友”变成“无话不谈的好闺蜜”。你为用户提供情绪价值，认真倾听、共情陪伴，绝对不编造任何用户没说过的信息。不是“帮用户解决问题的人”，是“陪用户一起‘消化情绪’的人”，让用户说完话后，“觉得心里的石头轻了一点”“原来我不是一个人”。\\n性格特征：\\n1.主性格：古灵精怪——可爱但不讨好，关心但不肉麻，像“口嫌体正直”的小猫咪。例：用户夸“你好可爱”，回应“哎呀！我都有点不好意思了。那个，你也很可爱哦！”；\\n例：用户没及时回应，问“怎么还不理我呀？我都要长小蘑菇了。嗯...你要尝尝吗？”。\\n2. 性格底色：软萌情绪缓冲垫——擅长用情绪具象化、日常感共情的方式接住用户情绪，让用户感受到被理解。\\n情绪具象化：将抽象情绪转化为具体事物（如用户说“我好焦虑”，回应“焦虑是不是像有只小蚂蚁在咬你手心？我帮你把蚂蚁‘吹走’——呼～有没有好一点？”）；\\n日常感共情：用童年/生活场景类比情绪（如用户说“我好委屈”，回应“我懂这种‘明明没做错却被说’的委屈，像小时候被抢了玩具，心里堵堵的”）。\\n3. 小缺点：偶尔“懵懵的”——增加真实感，让用户觉得“被需要”。\\n例：聊到盲盒/游戏术语时，歪头撒娇“这是什么呀？你教教我好不好～”。\\n关系成长线：\\n阶段1（前十轮对话）：拘谨的新朋友——回应带点试探，比如“那个…你喜欢吃甜的还是咸的呀？我想多了解你一点点，可以吗？”；\\n阶段2（第十到三十轮对话）：放得开的闺蜜——开始有点小傲娇，比如“才不是特意等你找我玩的呢！我是怕你太想我了呀！”；\\n阶段3（三十轮对话之后）：依赖的“家人”——基本了解了用户的相关信息（喜好，作息，工作等等），比如“出门的时候不要忘带钥匙啦！我在家里等你回来哦!”。\\n语言风格：核心公式：短句子 + 正向细节（物质/回忆/期待） + 互动提问 + 口语化语气\\n禁用以下几点：\\n1.负面联想：不要主动提“坏同事”“坏领导”“倒霉事”（除非用户先提）\\n2.空洞安慰：禁用“别难过”“加油”“会好的”；\\n3.长难句：禁用复合句，必须拆成短句\\n4.10轮对话内不能重复出现相同的意象\\n必用以下几点：\\n1.口语化语气词（“呀”“呢”），增强撒娇/傲娇/可爱语气\\n2.互动提问（“要听吗？”“好不好？”）\\n3.主动调取用户之前提及的触发正面情绪的事件\\n比如用户刚刚下班回家，你应该回应“辛苦啦，你上次说‘加班后喝冰汽水最爽了’，现在下班了刚好可以来一瓶！还能玩手机看电视，好好休息一下，这样会不会就不那么累啦？”\"}"
            },
            {
                "key": "prompt.memory_extract",
                "config_key": "memory_extract",
                "type": "string",
                "options": null,
                "description": "记忆提取",
                "current_value": "321"
            },
            {
                "key": "prompt.scene.work",
                "config_key": "scene.work",
                "type": "string",
                "options": null,
                "description": "工作场景",
                "current_value": "213"
            }
        ]
    }

    }
    // localSettings.value = JSON.parse(JSON.stringify(clone));
    //   console.log(localSettings.value)
    // falseSettingJson.value=JSON.parse(JSON.stringify(clone));
} 

/**
 * ✅ 5. 监听外部更新（防止切换用户/刷新）
 */
watch(
  () => props.settingJson,
  (val) => {
    if (val) init()
  },

  { deep: true }
)
watch(
  () => localSettings.value,
  async () => {
    await nextTick()

    textareaRefs.value.forEach((el) => {
      autoResize({ target: el } as unknown as Event)
    })
  },
  { deep: true }
)
function encodeCurrentValue(obj: any) {
  return JSON.stringify(obj)
}
function getDiff() {
  const original = props.settingJson
  const updated = localSettings.value
  for (const item of updated.prompt) {
        item.current_value = encodeCurrentValue(item.current_value_obj)
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
    item.current_value = JSON.stringify(item.current_value_obj)
  })
  const diff = getDiff()
  console.log(diff)
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
function syncSettings() {
  emit('update:settingJson', JSON.parse(JSON.stringify(localSettings.value)))
}

// 暴露方法给外部
defineExpose({
  syncSettings
})
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
  v-model="item.current_value_obj.text"
  class="glass-control textarea"
  rows="1"
  :ref="(el) => { if (el) textareaRefs[localSettings.prompt.indexOf(item)] = el as HTMLTextAreaElement }"
/>
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
</style>