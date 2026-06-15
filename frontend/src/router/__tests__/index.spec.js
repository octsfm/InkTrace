import { describe, expect, it } from 'vitest'

import router from '../index'

describe('router', () => {
  it('keeps works, settings and workspace as user routes', () => {
    const paths = router.getRoutes().map((route) => route.path)

    expect(paths).toContain('/')
    expect(paths).toContain('/works/:id')
    expect(paths).toContain('/works')
    expect(paths).toContain('/settings')
    expect(paths).not.toContain('/novel/:id')
    expect(paths).not.toContain('/novel/:id/write')
    expect(paths).not.toContain('/novel/:id/chapters/:chapterId/edit')
  })

  it('redirects disabled p2 routes back to works', async () => {
    if (!router.hasRoute('P2GuardProbe')) {
      router.addRoute({
        path: '/__p2_guard__',
        name: 'P2GuardProbe',
        component: { template: '<div>probe</div>' },
        meta: {
          title: 'P2 Guard Probe',
          p2FeatureFlag: 'enable_multi_chapter'
        }
      })
    }

    await router.push('/__p2_guard__')

    expect(router.currentRoute.value.path).toBe('/works')
  })
})
