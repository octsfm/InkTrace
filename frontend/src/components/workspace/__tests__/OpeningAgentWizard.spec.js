import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OpeningAgentWizard from '../OpeningAgentWizard.vue'

describe('OpeningAgentWizard v2', () => {
  it('starts from the story instead of requiring a reference novel', async () => {
    const wrapper = mount(OpeningAgentWizard, { props: { visible: true } })
    expect(wrapper.text()).toContain('先说说你的故事')
    expect(wrapper.text()).toContain('添加灵感参考（可跳过）')
    expect(wrapper.get('[data-test="opening-create-directions"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-test="opening-story-premise"]').setValue('一个普通人能看见谎言')
    await wrapper.get('[data-test="opening-protagonist-desire"]').setValue('保护家人')
    await wrapper.get('[data-test="opening-third-chapter-expectation"]').setValue('想知道能力来源')
    expect(wrapper.get('[data-test="opening-create-directions"]').attributes('disabled')).toBeUndefined()
    await wrapper.get('[data-test="opening-create-directions"]').trigger('click')
    expect(wrapper.emitted('create-directions')[0][0].storyPremise).toContain('看见谎言')
  })

  it('allows one understandable direction and never offers one-click apply', async () => {
    const directions = [{ direction_id: 'od_1', name: '先给危机', summary: '开场就让主角遇到麻烦', chapter_goals: ['危机', '反击', '新谜团'] }]
    const wrapper = mount(OpeningAgentWizard, { props: { visible: true, directions } })
    expect(wrapper.text()).toContain('选择一个开篇方向')
    expect(wrapper.text()).not.toContain('一键全部应用')
    await wrapper.get('[data-test="opening-direction-od_1"]').trigger('click')
    await wrapper.get('[data-test="opening-confirm-direction"]').trigger('click')
    expect(wrapper.emitted('confirm-direction')[0]).toEqual(['od_1'])
  })

  it('lets the writer change a direction, write their own, or ask for a new batch', async () => {
    const directions = [{
      direction_id: 'od_1', name: '先给危机', summary: '开场遇到麻烦',
      chapter_goals: ['危机', '反击', '谜团'], advantages: ['节奏快'], risks: ['人物铺垫少']
    }]
    const wrapper = mount(OpeningAgentWizard, { props: { visible: true, directions } })

    await wrapper.get('[data-test="opening-new-batch"]').trigger('click')
    expect(wrapper.emitted('refresh-directions')).toHaveLength(1)

    await wrapper.get('[data-test="opening-direction-od_1"]').trigger('click')
    await wrapper.get('[data-test="opening-edit-direction"]').trigger('click')
    await wrapper.get('[data-test="opening-direction-summary-input"]').setValue('先从一件反常的小事开始')
    await wrapper.get('[data-test="opening-save-direction"]').trigger('click')
    expect(wrapper.emitted('revise-direction')[0][0]).toEqual(expect.objectContaining({
      directionId: 'od_1', summary: '先从一件反常的小事开始',
      chapterGoals: ['危机', '反击', '谜团']
    }))

    await wrapper.get('[data-test="opening-write-direction"]').trigger('click')
    expect(wrapper.get('[data-test="opening-direction-name-input"]').element.value).toBe('')
  })

  it('keeps references optional and submits at most three authorized works', async () => {
    const wrapper = mount(OpeningAgentWizard, { props: { visible: true } })
    await wrapper.get('[data-test="opening-story-premise"]').setValue('成长故事')
    await wrapper.get('[data-test="opening-protagonist-desire"]').setValue('离开故乡')
    await wrapper.get('[data-test="opening-third-chapter-expectation"]').setValue('期待远方')

    expect(wrapper.find('[data-test="opening-reference-title-0"]').exists()).toBe(false)
    await wrapper.get('[data-test="opening-add-reference"]').trigger('click')
    await wrapper.get('[data-test="opening-reference-title-0"]').setValue('灵感作品')
    await wrapper.get('[data-test="opening-reference-text-0"]').setValue('第一章参考文本')
    expect(wrapper.get('[data-test="opening-create-directions"]').attributes('disabled')).toBeDefined()

    await wrapper.get('[data-test="opening-rights-confirm"]').setValue(true)
    await wrapper.get('[data-test="opening-create-directions"]').trigger('click')
    const payload = wrapper.emitted('create-directions')[0][0]
    expect(payload.references).toEqual([{ title: '灵感作品', chaptersText: ['第一章参考文本'] }])
    expect(payload.rightsConfirmed).toBe(true)
  })
})
