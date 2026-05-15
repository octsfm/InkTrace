﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import StatusBar from '../StatusBar.vue'

describe('StatusBar', () => {
  it('renders synced state with word count and session flag', () => {
    const wrapper = mount(StatusBar, {
      props: {
        status: 'synced',
        wordCount: 1234,
        todayWordDelta: 88,
        sessionReady: true
      }
    })

    expect(wrapper.text()).toContain('已保存')
    expect(wrapper.text()).toContain('本章字数 1,234')
    expect(wrapper.text()).toContain('今日新增 88')
    expect(wrapper.text()).toContain('会话已加载')
    expect(wrapper.find('.offline-banner').exists()).toBe(false)
  })

  it('renders saving state with spinning icon', () => {
    const wrapper = mount(StatusBar, {
      props: { status: 'saving' }
    })

    expect(wrapper.text()).toContain('保存中')
    expect(wrapper.find('.status-icon.spinning').exists()).toBe(true)
  })

  it('renders offline state and offline banner', () => {
    const wrapper = mount(StatusBar, {
      props: {
        status: 'offline',
        offline: true,
        offlineMessage: '离线模式，本地已暂存'
      }
    })

    expect(wrapper.text()).toContain('离线模式')
    expect(wrapper.text()).toContain('离线模式，本地已暂存')
    expect(wrapper.find('.offline-banner').exists()).toBe(true)
  })

  it('renders retry metadata and manual retry entry', async () => {
    const wrapper = mount(StatusBar, {
      props: {
        status: 'error',
        retryCount: 3,
        nextRetryAt: '2026-04-28T20:00:00.000Z',
        showManualRetry: true
      }
    })

    expect(wrapper.text()).toContain('保存失败')
    expect(wrapper.text()).toContain('重试次数 3')
    expect(wrapper.text()).toContain('下次重试')
    expect(wrapper.find('.retry-button').exists()).toBe(true)

    await wrapper.find('.retry-button').trigger('click')
    expect(wrapper.emitted('manual-retry')).toHaveLength(1)
  })

  it('renders conflict state explicitly', () => {
    const wrapper = mount(StatusBar, {
      props: {
        status: 'conflict',
        statusDetail: '检测到版本冲突，等待处理'
      }
    })

    expect(wrapper.text()).toContain('检测到冲突')
    expect(wrapper.text()).toContain('检测到版本冲突，等待处理')
    expect(wrapper.find('.status-pill').attributes('data-status')).toBe('conflict')
  })
})
