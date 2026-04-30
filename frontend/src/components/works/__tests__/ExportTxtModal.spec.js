import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(resolve(__dirname, '../ExportTxtModal.vue'), 'utf8')

describe('ExportTxtModal source contract', () => {
  it('renders txt export options required by Stage 2', () => {
    expect(source).toContain('导出 TXT')
    expect(source).toContain('包含章节标题')
    expect(source).toContain(':value="0"')
    expect(source).toContain(':value="1"')
    expect(source).toContain(':value="2"')
  })

  it('calls v1 io export API with snake_case options', () => {
    expect(source).toContain('v1IOApi.exportTxt')
    expect(source).toContain('include_titles: includeTitles.value')
    expect(source).toContain('gap_lines: gapLines.value')
  })

  it('downloads a txt blob without mutating work data', () => {
    expect(source).toContain('new Blob')
    expect(source).toContain('triggerDownload')
    expect(source).toContain('link.download')
    expect(source).toContain('window.URL.revokeObjectURL')
    expect(source).toContain('resolveFileNameFromDisposition')
    expect(source).toContain("response?.headers?.['content-disposition']")
  })

  it('emits exported and closes after success', () => {
    expect(source).toContain("emit('exported', props.work)")
    expect(source).toContain("emit('update:modelValue', false)")
  })
})
