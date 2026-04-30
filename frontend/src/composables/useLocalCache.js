import { localCache, SOFT_LIMIT_BYTES } from '../utils/localCache'

export const DRAFT_KEY_PREFIX = 'draft'
export const ASSET_DRAFT_KEY_PREFIX = 'asset_draft'
export const CACHE_SOFT_LIMIT_BYTES = SOFT_LIMIT_BYTES

export function buildDraftKey(workId, chapterId) {
  return `${DRAFT_KEY_PREFIX}:${String(workId || '').trim()}:${String(chapterId || '').trim()}`
}

export function buildAssetDraftKey(assetType, assetId) {
  return `${ASSET_DRAFT_KEY_PREFIX}:${String(assetType || '').trim()}:${String(assetId || '').trim()}`
}

export function createDraftPayload({
  workId,
  chapterId,
  title = '',
  content = '',
  version = 1,
  cursorPosition = 0,
  scrollTop = 0,
  timestamp = Date.now()
}) {
  return {
    workId,
    chapterId,
    title,
    content,
    version,
    cursorPosition,
    scrollTop,
    timestamp
  }
}

export function createAssetDraftPayload({
  assetType,
  assetId,
  payload = {},
  version = 1,
  timestamp = Date.now()
}) {
  return {
    assetType,
    assetId,
    payload,
    version,
    timestamp
  }
}

export function validateDraftPayload(payload) {
  return Boolean(
    payload &&
    payload.workId &&
    payload.chapterId &&
    Object.prototype.hasOwnProperty.call(payload, 'title') &&
    Object.prototype.hasOwnProperty.call(payload, 'content') &&
    Number.isInteger(Number(payload.version)) &&
    Number.isInteger(Number(payload.cursorPosition)) &&
    Number.isInteger(Number(payload.scrollTop)) &&
    Number.isInteger(Number(payload.timestamp))
  )
}

export function validateAssetDraftPayload(payload) {
  return Boolean(
    payload &&
    payload.assetType &&
    payload.assetId &&
    Object.prototype.hasOwnProperty.call(payload, 'payload') &&
    Number.isInteger(Number(payload.version)) &&
    Number.isInteger(Number(payload.timestamp))
  )
}

export function useLocalCache() {
  return {
    buildDraftKey,
    buildAssetDraftKey,
    createDraftPayload,
    createAssetDraftPayload,
    validateDraftPayload,
    validateAssetDraftPayload,
    localCache
  }
}
