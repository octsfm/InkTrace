import { describe, expect, it } from 'vitest'

import router from '../index'

describe('workspace compatibility route redirects', () => {
  it('treats /novel/:id as the default workspace entry', async () => {
    await router.push('/novel/novel-1')
    expect(router.currentRoute.value.name).toBe('NovelWorkspace')
    expect(router.currentRoute.value.fullPath).toBe('/novel/novel-1')
  })

  it('redirects write compatibility route into workspace writing section', async () => {
    await router.push('/novel/novel-1/write?targetArcId=arc-1')
    expect(router.currentRoute.value.fullPath).toBe('/novel/novel-1?targetArcId=arc-1&section=writing')
  })

  it('redirects chapter editor compatibility route into workspace writing chapter context', async () => {
    await router.push('/novel/novel-1/chapters/ch-3/edit')
    expect(router.currentRoute.value.fullPath).toBe('/novel/novel-1?section=writing&chapterId=ch-3')
  })
})
