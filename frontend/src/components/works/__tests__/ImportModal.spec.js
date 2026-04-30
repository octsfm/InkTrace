import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(resolve(process.cwd(), 'src/components/works/ImportModal.vue'), 'utf8')

describe('ImportModal contract', () => {
  it('defines txt file selection and upload fields', () => {
    expect(source).toContain('导入 TXT')
    expect(source).toContain('accept=".txt,text/plain"')
    expect(source).toContain('handleFallbackFileChange')
    expect(source).toContain('selectedFileLabel')
  })

  it('calls v1 import api with txt file title and author', () => {
    expect(source).toContain('v1IOApi.importTxt')
    expect(source).toContain('txtFile: selectedFile.value')
    expect(source).toContain('title: form.title.trim()')
    expect(source).toContain('author: form.author.trim()')
  })

  it('emits imported work and closes on success', () => {
    expect(source).toContain("emit('imported', work)")
    expect(source).toContain("emit('update:modelValue', false)")
    expect(source).toContain("ElMessage.success('TXT 导入成功')")
  })

  it('shows explicit warning and error feedback', () => {
    expect(source).toContain("ElMessage.warning('请先选择 TXT 文件。')")
    expect(source).toContain('TXT 导入失败，请检查文件编码或大小后重试。')
    expect(source).toContain('ElMessage.error(detail)')
  })
})
