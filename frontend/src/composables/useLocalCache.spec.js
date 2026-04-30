import { describe, expect, it } from 'vitest'

import {
  buildAssetDraftKey,
  buildDraftKey,
  createAssetDraftPayload,
  createDraftPayload,
  validateAssetDraftPayload,
  validateDraftPayload
} from './useLocalCache'

describe('useLocalCache baseline helpers', () => {
  it('builds stable draft keys', () => {
    expect(buildDraftKey('work-1', 'chapter-1')).toBe('draft:work-1:chapter-1')
    expect(buildAssetDraftKey('outline', 'asset-1')).toBe('asset_draft:outline:asset-1')
  })

  it('creates and validates body draft payloads', () => {
    const payload = createDraftPayload({
      workId: 'work-1',
      chapterId: 'chapter-1',
      title: '',
      content: '正文',
      version: 1,
      cursorPosition: 2,
      scrollTop: 10,
      timestamp: 100
    })

    expect(validateDraftPayload(payload)).toBe(true)
  })

  it('creates and validates structured asset draft payloads', () => {
    const payload = createAssetDraftPayload({
      assetType: 'outline',
      assetId: 'outline-1',
      payload: { contentText: '大纲' },
      version: 1,
      timestamp: 100
    })

    expect(validateAssetDraftPayload(payload)).toBe(true)
  })
})
