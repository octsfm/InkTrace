import { describe, expect, it } from 'vitest'

import {
  SOFT_LIMIT_CHARACTER_COUNT,
  countEffectiveCharacters,
  exceedsSoftLimit
} from '../textMetrics'

describe('textMetrics', () => {
  it('removes invisible whitespace before counting characters', () => {
    expect(countEffectiveCharacters('你 好\nInk\tTrace')).toBe(10)
  })

  it('handles empty values', () => {
    expect(countEffectiveCharacters('')).toBe(0)
    expect(countEffectiveCharacters(null)).toBe(0)
  })

  it('keeps visible punctuation', () => {
    expect(countEffectiveCharacters('第1章：开始。')).toBe(7)
  })

  it('checks the soft limit against body text only', () => {
    expect(exceedsSoftLimit('字'.repeat(SOFT_LIMIT_CHARACTER_COUNT + 1))).toBe(true)
    expect(exceedsSoftLimit('字'.repeat(SOFT_LIMIT_CHARACTER_COUNT))).toBe(false)
  })
})
