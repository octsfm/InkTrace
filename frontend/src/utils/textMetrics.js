export const SOFT_LIMIT_CHARACTER_COUNT = 200000

const INVISIBLE_CHARACTER_PATTERN = /[\s\u200B-\u200D\uFEFF]/g

export const countEffectiveCharacters = (text) => (
  String(text || '').replace(INVISIBLE_CHARACTER_PATTERN, '').length
)

export const exceedsSoftLimit = (text, limit = SOFT_LIMIT_CHARACTER_COUNT) => (
  countEffectiveCharacters(text) > Number(limit || SOFT_LIMIT_CHARACTER_COUNT)
)
