import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { localCache } from '@/utils/localCache'
import { useWritingAssetStore } from '@/stores/writingAsset'
import CharacterPanel from '../CharacterPanel.vue'

const mockListCharacters = vi.fn()
const mockCreateCharacter = vi.fn()
const mockUpdateCharacter = vi.fn()
const mockDeleteCharacter = vi.fn()

vi.mock('@/api', () => ({
  v1WritingAssetsApi: {
    getWorkOutline: vi.fn(),
    saveWorkOutline: vi.fn(),
    getChapterOutline: vi.fn(),
    saveChapterOutline: vi.fn(),
    listTimeline: vi.fn().mockResolvedValue([]),
    createTimeline: vi.fn(),
    updateTimeline: vi.fn(),
    deleteTimeline: vi.fn(),
    reorderTimeline: vi.fn(),
    listForeshadows: vi.fn().mockResolvedValue([]),
    createForeshadow: vi.fn(),
    updateForeshadow: vi.fn(),
    deleteForeshadow: vi.fn(),
    listCharacters: (...args) => mockListCharacters(...args),
    createCharacter: (...args) => mockCreateCharacter(...args),
    updateCharacter: (...args) => mockUpdateCharacter(...args),
    deleteCharacter: (...args) => mockDeleteCharacter(...args)
  }
}))

describe('CharacterPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localCache.clear()
    mockListCharacters.mockReset()
    mockCreateCharacter.mockReset()
    mockUpdateCharacter.mockReset()
    mockDeleteCharacter.mockReset()
  })

  it('loads characters and supports keyword search', async () => {
    mockListCharacters
      .mockResolvedValueOnce([
        { id: 'c-1', name: '林舟', description: '主角', aliases: ['舟'], version: 1 }
      ])
      .mockResolvedValueOnce([
        { id: 'c-2', name: '苏棠', description: '搭档', aliases: ['糖'], version: 1 }
      ])

    const wrapper = mount(CharacterPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    expect(mockListCharacters).toHaveBeenCalledWith('work-1', '')
    expect(wrapper.find('.character-item').attributes('data-item-id')).toBe('c-1')

    await wrapper.find('[data-testid="character-search"]').setValue('苏')
    await flushPromises()

    expect(mockListCharacters).toHaveBeenCalledWith('work-1', '苏')
    expect(wrapper.find('.character-item').attributes('data-item-id')).toBe('c-2')
  })

  it('creates a character and converts aliases input into array payload', async () => {
    mockListCharacters.mockResolvedValue([])
    mockCreateCharacter.mockResolvedValue({
      id: 'c-3',
      name: '顾遥',
      description: '配角',
      aliases: ['遥', 'gu'],
      version: 1
    })

    const wrapper = mount(CharacterPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('.create-button').trigger('click')
    await wrapper.find('[data-testid="character-name"]').setValue('顾遥')
    await wrapper.find('[data-testid="character-aliases"]').setValue(' 遥 , , gu , GU ')
    await wrapper.find('[data-testid="character-description"]').setValue('配角')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockCreateCharacter).toHaveBeenCalledWith('work-1', {
      name: '顾遥',
      description: '配角',
      aliases: ['遥', 'gu']
    })
    expect(wrapper.find('.character-item').attributes('data-item-id')).toBe('c-3')
  })

  it('shows duplicate warning but still saves existing character', async () => {
    mockListCharacters.mockResolvedValue([
      { id: 'c-1', name: '林舟', description: '主角', aliases: ['舟'], version: 2 },
      { id: 'c-2', name: '苏棠', description: '搭档', aliases: ['糖'], version: 1 }
    ])
    mockUpdateCharacter.mockResolvedValue({
      id: 'c-2',
      name: '林舟',
      description: '搭档',
      aliases: [],
      version: 2
    })

    const wrapper = mount(CharacterPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-item-id="c-2"]').trigger('click')
    await wrapper.find('[data-testid="character-name"]').setValue('林舟')
    expect(wrapper.text()).toContain('Duplicate name detected')

    await wrapper.find('[data-testid="character-aliases"]').setValue('')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    expect(mockUpdateCharacter).toHaveBeenCalledWith('c-2', {
      name: '林舟',
      description: '搭档',
      aliases: [],
      expected_version: 1
    })
  })

  it('keeps local draft and opens conflict modal after 409', async () => {
    mockListCharacters.mockResolvedValue([
      { id: 'c-1', name: '角色', description: '', aliases: [], version: 1 }
    ])
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 2,
      resource_type: 'character',
      resource_id: 'c-1'
    }
    mockUpdateCharacter.mockRejectedValue(conflictError)

    const wrapper = mount(CharacterPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="character-description"]').setValue('本地描述')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    const store = useWritingAssetStore()
    expect(store.assetDrafts['character:c-1']).toMatchObject({
      payload: {
        description: '本地描述'
      }
    })
    expect(wrapper.findComponent({ name: 'AssetConflictModal' }).exists()).toBe(true)
    expect(wrapper.text()).toContain('Asset version conflict')
  })

  it('discards local asset draft and reloads server content after conflict discard', async () => {
    mockListCharacters
      .mockResolvedValueOnce([
        { id: 'c-1', name: '角色', description: '', aliases: [], version: 1 }
      ])
      .mockResolvedValueOnce([
        { id: 'c-1', name: '角色', description: '服务端内容', aliases: ['srv'], version: 2 }
      ])
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 2,
      resource_type: 'character',
      resource_id: 'c-1',
      server_content: '服务端内容'
    }
    mockUpdateCharacter.mockRejectedValue(conflictError)

    const wrapper = mount(CharacterPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="character-description"]').setValue('本地描述')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    const modal = wrapper.find('.modal-footer')
    await modal.findAll('button.ghost-button')[1].trigger('click')
    await flushPromises()

    const store = useWritingAssetStore()
    expect(mockListCharacters).toHaveBeenLastCalledWith('work-1', '')
    expect(store.assetDrafts['character:c-1']).toBeUndefined()
    expect(store.assetConflictPayload).toBeNull()
    expect(wrapper.find('[data-testid="character-description"]').element.value).toBe('服务端内容')
    expect(wrapper.find('[data-testid="character-aliases"]').element.value).toBe('srv')
  })

  it('retries with force_override and clears draft after conflict override succeeds', async () => {
    mockListCharacters.mockResolvedValue([
      { id: 'c-1', name: '角色', description: '', aliases: [], version: 1 }
    ])
    const conflictError = new Error('conflict')
    conflictError.is_version_conflict = true
    conflictError.conflict_payload = {
      detail: 'asset_version_conflict',
      server_version: 2,
      resource_type: 'character',
      resource_id: 'c-1',
      server_content: '服务端内容'
    }
    mockUpdateCharacter
      .mockRejectedValueOnce(conflictError)
      .mockResolvedValueOnce({
        id: 'c-1',
        name: '角色',
        description: '本地描述',
        aliases: ['local'],
        version: 2
      })

    const wrapper = mount(CharacterPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-testid="character-description"]').setValue('本地描述')
    await wrapper.find('[data-testid="character-aliases"]').setValue('local')
    await wrapper.find('.save-button').trigger('click')
    await flushPromises()

    await wrapper.find('.modal-footer button.danger-button').trigger('click')
    await flushPromises()

    const store = useWritingAssetStore()
    expect(mockUpdateCharacter).toHaveBeenNthCalledWith(2, 'c-1', {
      name: '角色',
      description: '本地描述',
      aliases: ['local'],
      expected_version: 1,
      force_override: true
    })
    expect(store.assetDrafts['character:c-1']).toBeUndefined()
    expect(store.assetConflictPayload).toBeNull()
    expect(wrapper.find('[data-testid="character-description"]').element.value).toBe('本地描述')
  })

  it('deletes the current character and removes it from the list', async () => {
    mockListCharacters.mockResolvedValue([
      { id: 'c-1', name: '林舟', description: '', aliases: [], version: 1 },
      { id: 'c-2', name: '苏棠', description: '', aliases: [], version: 1 }
    ])
    mockDeleteCharacter.mockResolvedValue({ ok: true, id: 'c-1' })

    const wrapper = mount(CharacterPanel, {
      props: { workId: 'work-1' }
    })
    await flushPromises()

    await wrapper.find('[data-item-id="c-1"]').trigger('click')
    const deleteButton = wrapper.findAll('button').find((node) => node.text() === 'Delete')
    await deleteButton.trigger('click')
    await flushPromises()

    expect(mockDeleteCharacter).toHaveBeenCalledWith('c-1')
    expect(wrapper.findAll('.character-item')).toHaveLength(1)
    expect(wrapper.find('.character-item').attributes('data-item-id')).toBe('c-2')
  })
})
