import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(resolve(process.cwd(), 'src/views/WritingStudio.vue'), 'utf8')

describe('WritingStudio layout contract', () => {
  it('mounts the required writing studio regions and workspace components', () => {
    expect(source).toContain('class="studio-shell"')
    expect(source).toContain('class="sidebar-column"')
    expect(source).toContain('class="editor-column"')
    expect(source).toContain('class="asset-rail-column"')
    expect(source).toContain('<ChapterSidebar')
    expect(source).toContain('<ChapterTitleInput')
    expect(source).toContain('<PureTextEditor')
    expect(source).toContain('<AssetRail')
    expect(source).toContain('<AssetDrawer')
  })

  it('initializes work and session through workspace store while loading chapters from v1 API', () => {
    expect(source).toContain('workspaceStore.initializeWorkspace(workId.value)')
    expect(source).toContain('loadChapters()')
    expect(source).toContain('activateChapter(initialChapterId)')
  })

  it('focuses the pure text editor after the initial chapter is activated', () => {
    expect(source).toContain('await activateChapter(initialChapterId)')
    expect(source).toContain('await focusEditor()')
  })

  it('keeps AssetDrawer as a single active drawer controlled by activeAssetTab', () => {
    expect(source).toContain('const activeAssetTab = ref')
    expect(source).toContain('v-if="activeAssetTab"')
    expect(source).toContain(':active-tab="activeAssetTab"')
    expect(source).toContain('toggleAssetDrawer')
    expect(source).toContain('closeAssetDrawer')
  })

  it('defines header title editing and rename behavior without exposing work id', () => {
    expect(source).toContain('class="work-title-button"')
    expect(source).toContain('@click="startWorkTitleEditing"')
    expect(source).toContain('class="work-title-input"')
    expect(source).toContain('@keydown.enter.prevent="submitWorkTitleEditing"')
    expect(source).toContain('@keydown.esc.prevent="cancelWorkTitleEditing"')
    expect(source).toContain('v1WorksApi.update(workId.value, { title: nextTitle })')
    expect(source).not.toContain('{{ workId }}')
  })

  it('restores editor focus after header title submit or cancel', () => {
    expect(source).toContain('const cancelWorkTitleEditing = async')
    expect(source).toContain('await focusEditor()')
    expect(source).toContain('finally {')
  })

  it('routes Ctrl/Cmd+S from the focused editor to immediate chapter flush', () => {
    expect(source).toContain('window.addEventListener(\'keydown\', handleEditorSaveShortcut)')
    expect(source).toContain('key !== \'s\'')
    expect(source).toContain('activeElement?.closest?.(\'.editor-shell\')')
    expect(source).toContain('event.preventDefault()')
    expect(source).toContain('await flushCurrentDraftNow()')
  })

  it('uses save state store as the local draft boundary', () => {
    expect(source).toContain('saveStateStore.readLocalDraft')
    expect(source).toContain('saveStateStore.writeLocalDraft')
    expect(source).toContain('saveStateStore.clearLocalDraft')
    expect(source).toContain('saveStateStore.collectLocalDrafts')
    expect(source).not.toContain("from '@/utils/localCache'")
  })

  it('switches chapters after writing the current editor content to local cache without waiting for network saving', () => {
    expect(source).toContain('const handleSelectChapter = async')
    expect(source).toContain('writeCachedDraft(currentChapterId, chapterDataStore.activeChapterContent)')
    expect(source).toContain('await activateChapter(nextChapterId)')
    expect(source).toContain('await focusEditor()')
    expect(source).not.toContain("if (saveStateStore.saveStatus === 'saving') {\n    pendingChapterId.value = nextChapterId")
  })

  it('keeps long header titles truncated to one line', () => {
    expect(source).toContain('.work-title-button')
    expect(source).toContain('text-overflow: ellipsis')
    expect(source).toContain('white-space: nowrap')
    expect(source).toContain('overflow: hidden')
  })
})

