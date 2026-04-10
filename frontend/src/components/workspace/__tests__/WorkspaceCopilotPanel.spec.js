import { defineComponent, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import WorkspaceCopilotPanel from '../WorkspaceCopilotPanel.vue'

describe('WorkspaceCopilotPanel.vue', () => {
  const mountPanel = () => mount(WorkspaceCopilotPanel, {
    props: {
      modelValue: 'context',
      currentView: 'structure',
      currentObject: {
        type: 'plot_arc',
        arcId: 'arc-1',
        title: '主线追踪'
      },
      currentChapterTitle: '风暴将至',
      activeArcs: [
        { arc_id: 'arc-1', title: '主线追踪', current_stage: 'escalation', priority: 'core' }
      ],
      memoryView: {
        current_progress: '主线推进到关键节点。',
        current_state: '角色关系张力增强。',
        main_plot_lines: ['主角已经发现异常', '下一步应推进冲突升级']
      },
      organizeProgress: {},
      suggestedActions: []
    },
    global: {
      stubs: ['el-button', 'el-icon', 'el-tag']
    }
  })

  it('renders current object summary in context tab', () => {
    const wrapper = mountPanel()
    expect(wrapper.text()).toContain('当前对象')
    expect(wrapper.text()).toContain('主线追踪')
    expect(wrapper.text()).toContain('剧情弧对象')
  })

  it('emits structure action when clicking memory item', async () => {
    const wrapper = mountPanel()
    const memoryItem = wrapper.find('.memory-item')
    expect(memoryItem.exists()).toBe(true)
    await memoryItem.trigger('click')
    expect(wrapper.emitted('trigger')).toBeTruthy()
    expect(wrapper.emitted('trigger')[0][0]).toEqual({
      type: 'section',
      section: 'structure',
      object: {
        type: 'story_model'
      }
    })
  })

  it('renders chat shell and emits draft/submit events', async () => {
    const Harness = defineComponent({
      components: { WorkspaceCopilotPanel },
      setup() {
        const draft = ref('')
        const messages = ref([])
        const submits = ref([])
        const handleSubmit = (content) => {
          submits.value.push(content)
          messages.value = [
            ...messages.value,
            { role: 'user', content },
            { role: 'assistant', content: '测试回复' }
          ]
          draft.value = ''
        }
        return { draft, messages, submits, handleSubmit }
      },
      template: `
        <WorkspaceCopilotPanel
          model-value="chat"
          current-view="writing"
          :current-object="{ type: 'chapter', id: 'ch-1', title: '风暴将至' }"
          current-chapter-title="风暴将至"
          :active-arcs="[]"
          :memory-view="{ current_progress: '主线进入冲突升级阶段。', current_state: '当前需要处理角色冲突。', main_plot_lines: ['下一步应推进冲突升级'] }"
          :organize-progress="{}"
          :suggested-actions="[]"
          :chat-draft="draft"
          :chat-messages="messages"
          @update:chatDraft="draft = $event"
          @chat-submit="handleSubmit"
        />
      `
    })

    const wrapper = mount(Harness, {
      global: {
        stubs: ['el-button', 'el-icon', 'el-tag']
      }
    })

    expect(wrapper.text()).toContain('围绕当前对象提问')
    await wrapper.find('.prompt-chip').trigger('click')
    expect(wrapper.find('.chat-input').element.value).not.toBe('')
    await wrapper.find('.send-button').trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('我')
    expect(wrapper.text()).toContain('Copilot')
    expect(wrapper.text()).toContain('测试回复')
  })

  it('injects object prompt into draft when clicking inject', async () => {
    const Harness = defineComponent({
      components: { WorkspaceCopilotPanel },
      setup() {
        const draft = ref('')
        return { draft }
      },
      template: `
        <WorkspaceCopilotPanel
          model-value="chat"
          current-view="writing"
          :current-object="{ type: 'chapter', id: 'ch-1', title: '风暴将至' }"
          current-chapter-title="风暴将至"
          :active-arcs="[]"
          :memory-view="{ current_progress: '主线进入冲突升级阶段。', current_state: '当前需要处理角色冲突。', main_plot_lines: ['下一步应推进冲突升级'] }"
          :organize-progress="{}"
          :suggested-actions="[]"
          :chat-draft="draft"
          :chat-messages="[]"
          @update:chatDraft="draft = $event"
        />
      `
    })

    const wrapper = mount(Harness, {
      global: {
        stubs: ['el-button', 'el-icon', 'el-tag']
      }
    })

    const injectButton = wrapper.find('.object-prompt-card .prompt-action-button')
    expect(injectButton.exists()).toBe(true)
    await injectButton.trigger('click')
    expect(wrapper.find('.chat-input').element.value).toContain('当前章节「风暴将至」')
  })

  it('emits direct submit when clicking object prompt primary action', async () => {
    const wrapper = mount(WorkspaceCopilotPanel, {
      props: {
        modelValue: 'chat',
        currentView: 'writing',
        currentObject: {
          type: 'chapter',
          id: 'ch-1',
          title: '风暴将至'
        },
        currentChapterTitle: '风暴将至',
        activeArcs: [],
        memoryView: {
          current_progress: '主线进入冲突升级阶段。',
          current_state: '当前需要处理角色冲突。',
          main_plot_lines: ['下一步应推进冲突升级']
        },
        organizeProgress: {},
        suggestedActions: [],
        chatDraft: '',
        chatMessages: []
      },
      global: {
        stubs: ['el-button', 'el-icon', 'el-tag']
      }
    })

    const sendNowButton = wrapper.findAll('.object-prompt-card .prompt-action-button').find((node) => node.text().includes('立即发送'))
    expect(sendNowButton).toBeTruthy()
    await sendNowButton.trigger('click')
    expect(wrapper.emitted('chat-submit')).toBeTruthy()
    expect(wrapper.emitted('chat-submit')[0][0]).toContain('当前章节「风暴将至」')
  })

  it('renders chat sessions and emits session change', async () => {
    const wrapper = mount(WorkspaceCopilotPanel, {
      props: {
        modelValue: 'chat',
        currentView: 'writing',
        currentObject: {
          type: 'chapter',
          id: 'ch-1',
          title: '风暴将至'
        },
        currentChapterTitle: '风暴将至',
        activeArcs: [],
        memoryView: {
          current_progress: '主线进入冲突升级阶段。',
          current_state: '当前需要处理角色冲突。',
          main_plot_lines: ['下一步应推进冲突升级']
        },
        organizeProgress: {},
        suggestedActions: [],
        chatDraft: '',
        chatMessages: [],
        chatSessions: [
          { key: 'writing::chapter:ch-1', label: '风暴将至', summary: '这一章正在推进冲突升级。', metaText: '4 条消息 · 3 分钟前' },
          { key: 'structure::arc:arc-1', label: '主线追踪' }
        ],
        currentChatSessionKey: 'writing::chapter:ch-1',
        recentPrompts: ['上一章的伏笔有没有回收？']
      },
      global: {
        stubs: ['el-button', 'el-icon', 'el-tag']
      }
    })

    expect(wrapper.text()).toContain('对象会话')
    expect(wrapper.text()).toContain('最近问题')
    expect(wrapper.text()).toContain('这一章正在推进冲突升级。')
    expect(wrapper.text()).toContain('4 条消息 · 3 分钟前')
    expect(wrapper.text()).toContain('当前')
    const sessionButton = wrapper.findAll('.session-chip')[1]
    await sessionButton.trigger('click')
    expect(wrapper.emitted('chat-session-change')).toBeTruthy()
    expect(wrapper.emitted('chat-session-change')[0][0]).toBe('structure::arc:arc-1')
  })

  it('prefers parent-provided context summary and prompt cards', () => {
    const wrapper = mount(WorkspaceCopilotPanel, {
      props: {
        modelValue: 'chat',
        currentView: 'overview',
        currentObject: null,
        currentChapterTitle: '',
        activeArcs: [],
        memoryView: {},
        organizeProgress: {},
        suggestedActions: [],
        chatDraft: '',
        chatMessages: [],
        contextSummary: {
          currentObjectTitle: '父层对象摘要',
          progressText: '父层状态摘要'
        },
        chatPrompts: ['父层推荐问题'],
        objectPromptCards: [
          {
            title: '父层动作卡',
            tag: '概览',
            description: '来自父层的对象动作。',
            prompt: '请根据父层卡片继续处理。'
          }
        ]
      },
      global: {
        stubs: ['el-button', 'el-icon', 'el-tag']
      }
    })

    expect(wrapper.text()).toContain('父层对象摘要')
    expect(wrapper.text()).toContain('父层状态摘要')
    expect(wrapper.text()).toContain('父层推荐问题')
    expect(wrapper.text()).toContain('父层动作卡')
  })
})
