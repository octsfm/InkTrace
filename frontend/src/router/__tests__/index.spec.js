import { describe, expect, it } from 'vitest'

import router from '../index'

describe('router', () => {
  it('keeps only works list and workspace as user routes', () => {
    const paths = router.getRoutes().map((route) => route.path)

    expect(paths).toContain('/')
    expect(paths).toContain('/works/:id')
    expect(paths).toContain('/works')
    expect(paths).not.toContain('/novel/:id')
    expect(paths).not.toContain('/novel/:id/write')
    expect(paths).not.toContain('/novel/:id/chapters/:chapterId/edit')
  })
})
