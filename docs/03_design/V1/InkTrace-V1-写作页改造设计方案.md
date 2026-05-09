# InkTrace V1 写作页改造设计方案（干净正文区）

更新时间：2026-04-29  
适用范围：V1（Web 形态）  
目标：对齐参考写作助手的“沉浸式干净正文区”，同时修复章节创建/聚焦/编号显示与 Header 信息噪音问题。

---

## 1. 改造目标（结果导向）

### 1.1 中间正文区必须极简

中间区域最终只保留：

1. 顶部：居中章节标题输入框（单行，可编辑）
2. 中间：正文输入区（纯文本 textarea，宽边距）
3. 底部：轻量信息（保存状态/本章字数/仅支持纯文本）

禁止常驻出现：
- “编辑区 / 宽边距正文区 / 专注正文创作…”等说明性文字
- “会话已加载 / 光标 / 滚动”等调试信息
- “当前作品：{UUID}”等无意义技术字段

### 1.2 章节创建与聚焦符合写作直觉

- 点击“+ 新章”无论当前选中哪章，都**追加到最后一章**之后
- 创建成功后必须：
  - 自动选中新章
  - 左侧列表滚动到新章
  - 正文区获得焦点

### 1.3 章节编号可见且稳定

- 左侧章节列表必须显示 `第X章`，其中 X = `order_index`
- 标题为空时也必须显示 `第X章`

### 1.4 Header 只显示作品名

- Header 显示 `作品标题（可选作者）`
- 不显示 workId/UUID

### 1.5 右侧栏 V1 默认隐藏

- 右侧 S/T/M 预留栏 V1 默认不渲染或完全隐藏
- 不允许在 V1 展开复杂面板

---

## 2. 现状定位（基于当前代码）

写作页主容器：
- [WritingStudio.vue](file:///workspace/frontend/src/views/WritingStudio.vue)

左侧章节列表组件：
- [ChapterSidebar.vue](file:///workspace/frontend/src/components/workspace/ChapterSidebar.vue)

正文编辑器组件：
- [PureTextEditor.vue](file:///workspace/frontend/src/components/workspace/PureTextEditor.vue)

后端 work 详情接口（可用于 Header 显示作品名）：
- [works.py](file:///workspace/presentation/api/routers/v1/works.py#L48-L61)

---

## 3. 详细交互与规则（写死给开发）

### 3.1 新建章节：一律追加到末尾

#### 规则
- “+ 新章”永远追加到最后一章之后，而不是插在当前激活章节后。

#### 现状问题
当前创建参数使用 `after_chapter_id = activeChapterId`：
- [WritingStudio.vue](file:///workspace/frontend/src/views/WritingStudio.vue#L589-L605)

#### 目标行为
- `after_chapter_id` 固定为 `chapterDataStore.chapters.at(-1)?.id || ''`
- 创建完成后：
  - `activateChapter(createdChapter.id)`
  - 左侧列表 `scrollIntoView(active)`
  - `PureTextEditor` 自动 focus

---

### 3.2 章节编号：显示 order_index（第X章）

#### 规则
- 左侧每项显示：`第{order_index}章` +（可选）空格 + title
- 若 `order_index` 缺失，fallback 为列表 index+1（仅兜底）

#### 现状问题
当前 fallback 使用 `chapter_number || number || 0`：
- [ChapterSidebar.vue](file:///workspace/frontend/src/components/workspace/ChapterSidebar.vue#L37)

---

### 3.3 中间标题输入框：B2（第X章 + 标题）+ 共享 debounce

#### 3.3.1 显示内容（B2）
- 输入框展示：`第{order_index}章` +（若 title 非空）` ${title}`
- `order_index` 从 `chapterDataStore.activeChapter.order_index` 读取

#### 3.3.2 保存字段
后端只存 `title`，不存“第X章”前缀。

保存时提取 `title` 的规则：
- 若输入内容匹配 `^第\\d+章\\s*`，剥离前缀后 trim 作为 title
- 否则整段 trim 作为 title（容错）

#### 3.3.3 与正文共享 debounce 保存（2.5s）
输入触发：
- 标题输入变更：更新内存态 title，并调用现有 `scheduleDraftSync()`
- 正文输入变更：保持现有 `handleDraftChange` 逻辑

flush 时提交 payload：
- `v1ChaptersApi.update(chapterId, { title, content, expected_version })`

要求：
- 标题与正文必须在同一套 debounce 内提交（同一次 flush）
- 这样才能保证“停 3 秒内自动保存完成 → 刷新不丢失”

---

### 3.4 Header：显示作品名，不显示 UUID

#### 规则
- Header 展示：
  - 主标题：作品名
  - 次信息（可选）：作者
- 不显示：
  - “纯文本写作页”
  - “当前作品：{workId}”

#### 数据来源
页面进入时调用 `GET /api/v1/works/{id}` 获取 `title/author`。

---

### 3.5 右侧栏：V1 默认隐藏

#### 规则
- V1 默认不展示右侧栏（rail-column）
- 若保留代码以便未来扩展，至少做到：
  - 默认 `display: none` 或条件渲染为 false
  - 不允许点击展开面板

---

## 4. 视觉规范（对齐参考图）

- 标题输入框：居中、单行、大字号（24–28px），弱边框或无边框，获得焦点时才出现轻微下划线或淡色描边
- 正文区：宽边距（左右 padding 至少 28px，建议更宽），背景纯白，边框极弱或无边框
- 状态信息：不进入正文视线中心，放顶部右侧（StatusBar）或底部轻量行

---

## 5. 验收清单（必须可复现）

- [ ] “+ 新章”在任意选中章下点击，都追加到末尾
- [ ] 创建后左侧列表滚动到新章，新章被高亮，正文区聚焦
- [ ] 左侧列表每项都有 `第X章`，X 与 `order_index` 一致
- [ ] 中间正文区无调试文案/说明文案，仅保留标题输入框 + 正文 + 底部轻量信息
- [ ] Header 显示作品名，不出现 UUID
- [ ] 右侧 S/T/M 默认不显示
- [ ] 标题与正文共享 debounce 保存：停 3 秒刷新后不丢

