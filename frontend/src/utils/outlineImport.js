const MAX_OUTLINE_IMPORT_FILE_SIZE = 2 * 1024 * 1024
const OUTLINE_IMPORT_RECOMMEND_THRESHOLD = 20000
const OUTLINE_IMPORT_RISK_THRESHOLD = 50000
const ALLOWED_OUTLINE_IMPORT_EXTENSIONS = ['.txt', '.md']

const normalizeText = (value) => String(value ?? '')

const stripUtf8Bom = (text) => normalizeText(text).replace(/^\uFEFF/, '')

const getFileExtension = (fileName) => {
  const normalized = String(fileName || '').trim().toLowerCase()
  if (!normalized.includes('.')) return ''
  return normalized.slice(normalized.lastIndexOf('.'))
}

const validateOutlineImportFile = (file) => {
  const extension = getFileExtension(file?.name)
  if (!ALLOWED_OUTLINE_IMPORT_EXTENSIONS.includes(extension)) {
    throw new Error('仅支持导入 TXT 或 Markdown 文件。')
  }
  if (Number(file?.size || 0) > MAX_OUTLINE_IMPORT_FILE_SIZE) {
    throw new Error('导入文件不能超过 2MB。')
  }
}

const decodeOutlineImportBuffer = (buffer) => {
  try {
    const decoder = new TextDecoder('utf-8', { fatal: true })
    return stripUtf8Bom(decoder.decode(buffer))
  } catch (error) {
    throw new Error('文件编码不受支持，请使用 UTF-8 或 UTF-8 with BOM。')
  }
}

const ensureNonEmptyOutlineText = (text) => {
  if (!normalizeText(text).trim()) {
    throw new Error('导入内容不能为空。')
  }
}

const countOutlineImportCharacters = (text) => normalizeText(text).length

const mergeOutlineImportText = (currentText, importedText, mode = 'replace') => {
  const baseText = normalizeText(currentText)
  const nextText = normalizeText(importedText)
  if (mode !== 'append') {
    return nextText
  }
  if (!baseText || !nextText) {
    return `${baseText}${nextText}`
  }
  return `${baseText}\n\n${nextText}`
}

const readOutlineImportFile = async (file) => {
  validateOutlineImportFile(file)
  const buffer = await file.arrayBuffer()
  const text = decodeOutlineImportBuffer(buffer)
  ensureNonEmptyOutlineText(text)
  return text
}

export {
  ALLOWED_OUTLINE_IMPORT_EXTENSIONS,
  MAX_OUTLINE_IMPORT_FILE_SIZE,
  OUTLINE_IMPORT_RECOMMEND_THRESHOLD,
  OUTLINE_IMPORT_RISK_THRESHOLD,
  countOutlineImportCharacters,
  ensureNonEmptyOutlineText,
  mergeOutlineImportText,
  readOutlineImportFile
}
