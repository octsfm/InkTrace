import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import OutlineImportModal from '../OutlineImportModal.vue'

const createMockFile = (content, name, size = null) => ({
  name,
  size: size ?? new TextEncoder().encode(String(content || '')).byteLength,
  async arrayBuffer() {
    return new TextEncoder().encode(String(content || '')).buffer
  }
})

describe('OutlineImportModal', () => {
  it('renders pasted text preview and emits append import payload when merge mode is selected', async () => {
    const wrapper = mount(OutlineImportModal, {
      props: {
        visible: true,
        currentDraftText: '已有草稿'
      }
    })

    await wrapper.get('[data-testid="outline-import-paste"]').setValue('第一卷\n第二卷')
    expect(wrapper.get('[data-testid="outline-import-preview"]').text()).toContain('第一卷')
    expect(wrapper.get('[data-testid="outline-import-char-count"]').text()).toContain('当前字符数：7')

    await wrapper.get('[data-testid="outline-import-mode-append"]').setValue(true)
    await wrapper.get('[data-testid="outline-import-confirm"]').trigger('click')

    expect(wrapper.emitted('import')?.[0]).toEqual([{
      content: '第一卷\n第二卷',
      mode: 'append'
    }])
  })

  it('reads markdown file as raw text and keeps markdown syntax in preview', async () => {
    const wrapper = mount(OutlineImportModal, {
      props: {
        visible: true,
        currentDraftText: ''
      }
    })

    const file = createMockFile('# 第一卷\n## 第二章', 'outline.md')
    const input = wrapper.get('[data-testid="outline-import-file"]')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [file]
    })
    await input.trigger('change')
    await flushPromises()

    expect(wrapper.get('[data-testid="outline-import-preview"]').text()).toContain('# 第一卷')
    expect(wrapper.find('[data-testid="outline-import-error"]').exists()).toBe(false)

    await wrapper.get('[data-testid="outline-import-confirm"]').trigger('click')
    expect(wrapper.emitted('import')?.[0]).toEqual([{
      content: '# 第一卷\n## 第二章',
      mode: 'replace'
    }])
  })

  it('shows threshold hints based on raw character count', async () => {
    const wrapper = mount(OutlineImportModal, {
      props: {
        visible: true
      }
    })

    await wrapper.get('[data-testid="outline-import-paste"]').setValue('a'.repeat(20000))
    expect(wrapper.text()).toContain('建议控制在 20,000 字以内以获得更好编辑体验。')

    await wrapper.get('[data-testid="outline-import-paste"]').setValue('b'.repeat(50000))
    expect(wrapper.text()).toContain('当前内容较大，可能影响编辑性能。')
  })

  it('blocks invalid file type and empty content import', async () => {
    const wrapper = mount(OutlineImportModal, {
      props: {
        visible: true
      }
    })

    const input = wrapper.get('[data-testid="outline-import-file"]')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [{ name: 'outline.docx', size: 128 }]
    })
    await input.trigger('change')
    await flushPromises()

    expect(wrapper.get('[data-testid="outline-import-error"]').text()).toContain('仅支持导入 TXT 或 Markdown 文件。')
    expect(wrapper.emitted('import')).toBeUndefined()

    const emptyFile = createMockFile(' \n\t ', 'outline.txt')
    Object.defineProperty(input.element, 'files', {
      configurable: true,
      value: [emptyFile]
    })
    await input.trigger('change')
    await flushPromises()

    expect(wrapper.get('[data-testid="outline-import-error"]').text()).toContain('导入内容不能为空。')
  })
})
