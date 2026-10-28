<template>
  <div class="app">
    <!-- 深色侧边栏 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>
          </svg>
        </div>
        <div class="brand-text">
          <div class="brand-name">智旅规划</div>
          <div class="brand-sub">AI Travel Planner</div>
        </div>
      </div>

      <button class="btn-new" @click="newSession">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
        新建规划
      </button>

      <div class="side-section">
        <div class="side-title">
          历史方案
          <span class="count-badge">{{ plans.length }}</span>
        </div>
        <div class="plan-list">
          <div v-if="plans.length === 0" class="side-empty">暂无历史方案</div>
          <div
            v-for="p in plans"
            :key="p.id"
            class="plan-item"
            :class="{ active: activePlanId === p.id }"
            @click="openPlan(p.id)"
          >
            <div class="plan-dest">{{ p.title }}</div>
            <div class="plan-meta">
              <span class="days-badge">{{ p.days }} 天</span>
              <span class="plan-date">{{ p.created_at }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="side-footer">LangGraph · Redis · MySQL</div>
    </aside>

    <!-- 主内容区 -->
    <main class="main">
      <header class="topbar">
        <div class="topbar-left">
          <h1 class="topbar-title">智能行程规划助手</h1>
          <span class="topbar-divider"></span>
          <span class="topbar-desc">多节点工作流 · 逐日行程 · 预算建议</span>
        </div>
        <div class="topbar-status" :class="{ offline: !serviceOk }">
          <span class="status-dot"></span>
          {{ serviceOk ? '服务正常' : '服务异常' }}
        </div>
      </header>

      <div ref="msgBox" class="messages">
        <!-- 欢迎页 -->
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-badge">AI 驱动</div>
          <h2 class="welcome-title">开始规划你的下一次旅行</h2>
          <p class="welcome-sub">告诉我目的地、天数、预算与偏好,智能工作流将为你生成完整的逐日旅行方案</p>
          <img class="welcome-hero" :src="heroUrl" alt="旅行风景" />
          <div class="prompt-cards">
            <div
              v-for="(t, i) in templates"
              :key="i"
              class="prompt-card"
              @click="useTemplate(t)"
            >
              <div class="prompt-card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l2.4 7.2H22l-6 4.4 2.3 7.4-6.3-4.6-6.3 4.6L8 13.6 2 9.2h7.6z"/></svg>
              </div>
              <div class="prompt-card-title">{{ t.title }}</div>
              <div class="prompt-card-desc">{{ t.text }}</div>
            </div>
          </div>

        </div>

        <!-- 消息列表 -->
        <div v-for="(m, i) in messages" :key="i" :class="['msg-row', m.role]">
          <div class="avatar" :class="m.role">{{ m.role === 'user' ? '我' : 'AI' }}</div>
          <div class="msg-body">
            <div v-if="m.role === 'user'" class="bubble user-bubble">{{ m.content }}</div>
            <div v-else class="bubble ai-bubble markdown" v-html="renderMd(m.content)"></div>
          </div>
        </div>

        <!-- 加载态 -->
        <div v-if="loading" class="msg-row assistant">
          <div class="avatar assistant">AI</div>
          <div class="bubble ai-bubble loading-bubble">
            <span class="typing"><i></i><i></i><i></i></span>
            <span>正在调用规划工作流,通常需要 1-2 分钟,请稍候...</span>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="composer">
        <div class="composer-box" :class="{ focused: composerFocused }">
          <textarea
            v-model="input"
            rows="2"
            placeholder="例如:我想去云南玩 5 天,预算 5000,喜欢美食和摄影"
            @focus="composerFocused = true"
            @blur="composerFocused = false"
            @keydown.enter.exact.prevent="send"
          ></textarea>
          <button class="btn-send" :disabled="loading || !input.trim()" @click="send">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg>
            发送
          </button>
        </div>
        <div class="composer-hint">Enter 发送 · Shift + Enter 换行</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { marked } from 'marked'
import { getHistory, getPlan, listPlans } from './api'
import axios from 'axios'

const templates = [
  { title: '经典打卡', text: '我想去云南玩 5 天,预算 5000,喜欢美食和摄影' },
  { title: '亲子出行', text: '暑假带孩子去成都 4 天,预算 8000,想看大熊猫和科技馆' },
  { title: '周末短途', text: '周末去苏州玩 2 天,预算 1500,偏好园林和古镇' },
]

function getOrCreateSession() {
  let id = localStorage.getItem('travel_session_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('travel_session_id', id)
  }
  return id
}

const sessionId = ref(getOrCreateSession())
const messages = ref([])
const plans = ref([])
const input = ref('')
const loading = ref(false)
const msgBox = ref(null)
const activePlanId = ref(null)
const serviceOk = ref(true)
const composerFocused = ref(false)

const renderMd = (text) => marked.parse(text || '')

// 欢迎页主视觉图(AI 生成,本地资源)
const heroUrl = '/scenery/hero.jpg'

async function scrollBottom() {
  await nextTick()
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
}

function useTemplate(t) {
  input.value = t.text
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  input.value = ''
  activePlanId.value = null
  messages.value.push({ role: 'user', content: text })
  // 先插入一条空的 assistant 消息,流式往里面追加
  messages.value.push({ role: 'assistant', content: '' })
  const msgIndex = messages.value.length - 1
  scrollBottom()
  loading.value = true
  try {
    const resp = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value, message: text })
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let firstToken = true

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''
      for (const raw of events) {
        if (!raw.startsWith('data:')) continue
        const data = raw.slice(5).trim()
        if (!data || data === '[DONE]') continue
        const ev = JSON.parse(data)
        if (ev.type === 'meta' || ev.type === 'token') {
          if (firstToken) {
            loading.value = false  // 首个 token 到达,隐藏 typing 动画
            firstToken = false
          }
          messages.value[msgIndex].content += ev.content
          scrollBottom()
        } else if (ev.type === 'saved') {
          activePlanId.value = ev.plan_id
          loadPlans()
        } else if (ev.type === 'error') {
          messages.value[msgIndex].content += `\n\n**出错了**\n\n${ev.detail}`
        }
      }
    }
  } catch (e) {
    messages.value[msgIndex].content += `\n\n**出错了**\n\n${e.message}`
  } finally {
    loading.value = false
    scrollBottom()
  }
}

async function openPlan(id) {
  try {
    const plan = await getPlan(id)
    activePlanId.value = id
    messages.value.push({ role: 'assistant', content: plan.content })
    scrollBottom()
  } catch (e) {
    console.error(e)
  }
}

async function loadPlans() {
  try {
    plans.value = await listPlans()
  } catch (e) {
    console.error(e)
  }
}

function newSession() {
  const id = crypto.randomUUID()
  localStorage.setItem('travel_session_id', id)
  sessionId.value = id
  messages.value = []
  activePlanId.value = null
}

async function checkHealth() {
  try {
    await axios.get('/api/health', { timeout: 5000 })
    serviceOk.value = true
  } catch {
    serviceOk.value = false
  }
}

onMounted(async () => {
  loadPlans()
  checkHealth()
  try {
    const { messages: history } = await getHistory(sessionId.value)
    messages.value = history
    scrollBottom()
  } catch (e) {
    console.error(e)
  }
})
</script>
