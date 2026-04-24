# InkTrace 基础方案开发落地计划 (v1.1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根据《InkTrace 基础方案落地文档（v1.1）》重构系统，交付一个稳定可用的长篇纯文本小说写作工具，支持持续编辑、可靠保存、异常可恢复。

**Architecture:** 
- 前端使用 Vue3 + Pinia，舍弃复杂的 Workspace 壳，仅保留“书架 (WorksList)”与“写作页 (WritingStudio)”。
- 后端使用 FastAPI + SQLite，移除 AI 和复杂工作流，强化核心 CRUD 链路。
- 引入乐观锁（`version`）和本地缓存（`localStorage` LRU）保证数据安全与离线可用。

**Tech Stack:** Vue3, Pinia, FastAPI, SQLite, SQLAlchemy

---

## 阶段一：数据模型与后端核心重构 (P0)

### Task 1: 数据库模型重构

**Files:**
- Modify: `infrastructure/database/models.py`
- Modify: `domain/entities.py`
- Create: `migrations/versions/v1.1_schema.py`

- [ ] **Step 1: 更新 Work 和 Chapter 模型**

修改 `models.py` 中的表结构，对齐 v1.1 需求：

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from infrastructure.database.session import Base
from datetime import datetime

class WorkModel(Base):
    __tablename__ = "works"
    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    author = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    chapters = relationship("ChapterModel", back_populates="work", cascade="all, delete-orphan")
    session = relationship("EditSessionModel", back_populates="work", uselist=False, cascade="all, delete-orphan")

class ChapterModel(Base):
    __tablename__ = "chapters"
    id = Column(String(36), primary_key=True)
    work_id = Column(String(36), ForeignKey("works.id"), nullable=False)
    chapter_no = Column(String(50), nullable=True) # 保留字段，不参与排序
    title = Column(String(255), nullable=False, default="")
    content = Column(Text, nullable=False, default="")
    word_count = Column(Integer, default=0)
    order_index = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    work = relationship("WorkModel", back_populates="chapters")

class EditSessionModel(Base):
    __tablename__ = "edit_sessions"
    work_id = Column(String(36), ForeignKey("works.id"), primary_key=True)
    last_open_chapter_id = Column(String(36), nullable=True)
    cursor_position = Column(Integer, default=0)
    scroll_top = Column(Integer, default=0)
    last_opened_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    work = relationship("WorkModel", back_populates="session")
```

- [ ] **Step 2: 编写数据库迁移脚本**

（在实际项目中通过 alembic revision 自动生成或手动编写对应的 CREATE TABLE 语句）。

- [ ] **Step 3: 更新实体类**

修改 `domain/entities.py`，保持与 Model 一致的字段。

### Task 2: 作品 (Work) 核心 CRUD API

**Files:**
- Create: `presentation/api/routers/works.py`
- Modify: `application/services/work_service.py`
- Modify: `presentation/api/app.py`

- [ ] **Step 1: 编写 WorkService**

实现新建作品的业务逻辑。必须遵守 `R-CH-04`：新建作品时系统静默创建空章节“第1章”。

```python
from sqlalchemy.orm import Session
import uuid
from infrastructure.database.models import WorkModel, ChapterModel, EditSessionModel

def create_work(db: Session, title: str, author: str = None):
    work_id = str(uuid.uuid4())
    chapter_id = str(uuid.uuid4())
    
    work = WorkModel(id=work_id, title=title, author=author)
    db.add(work)
    
    # 遵守 R-CH-04
    first_chapter = ChapterModel(
        id=chapter_id,
        work_id=work_id,
        title="第1章",
        content="",
        order_index=1,
        version=1
    )
    db.add(first_chapter)
    
    # 初始化会话
    session_info = EditSessionModel(
        work_id=work_id,
        last_open_chapter_id=chapter_id
    )
    db.add(session_info)
    
    db.commit()
    return work
```

- [ ] **Step 2: 注册 API 路由**

在 `presentation/api/routers/works.py` 中编写 `POST /api/works`，并在 `app.py` 中注册该 Router。

### Task 3: 章节 (Chapter) 管理与并发保存 API

**Files:**
- Create: `presentation/api/routers/chapters.py`
- Modify: `application/services/chapter_service.py`

- [ ] **Step 1: 实现新建与调序 API**

根据 `R-CH-02` (新建默认插入后方) 和 `R-CH-05` (拖拽调序必须原子提交)，在 `chapter_service.py` 实现逻辑。

```python
def reorder_chapters(db: Session, work_id: str, ordered_ids: list[str]):
    # 遵守 R-CH-05：全量更新 order_index
    chapters = db.query(ChapterModel).filter(ChapterModel.work_id == work_id).all()
    chapter_map = {c.id: c for c in chapters}
    
    for idx, cid in enumerate(ordered_ids, start=1):
        if cid in chapter_map:
            chapter_map[cid].order_index = idx
            
    db.commit()
```

- [ ] **Step 2: 实现带有乐观锁的正文保存 API**

遵守 `R-SAVE-01`（同时保存标题与正文）和 `R-SAVE-04`（乐观锁版本控制）。

```python
from fastapi import HTTPException

def update_chapter_content(db: Session, chapter_id: str, title: str, content: str, word_count: int, version: int, force_override: bool = False):
    chapter = db.query(ChapterModel).filter(ChapterModel.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
        
    if not force_override and chapter.version != version:
        raise HTTPException(status_code=409, detail=f"Version conflict. Server version: {chapter.version}")
        
    chapter.title = title
    chapter.content = content
    chapter.word_count = word_count
    chapter.version += 1  # 版本递增
    
    db.commit()
    return chapter
```

---

## 阶段二：前端核心页面与本地缓存机制 (P0 & P1)

### Task 4: Pinia Store 状态与本地 LRU 缓存管理

**Files:**
- Create: `frontend/src/stores/workStore.js`
- Create: `frontend/src/stores/chapterStore.js`
- Create: `frontend/src/utils/localCache.js`

- [ ] **Step 1: 实现 LRU 本地缓存**

遵守 `R-SAVE-07`，容量受控在 10MB 左右，淘汰旧数据。

```javascript
// frontend/src/utils/localCache.js
const CACHE_PREFIX = 'inktrace_draft_';

export function saveLocalDraft(chapterId, title, content, cursorPosition, scrollTop) {
    const key = CACHE_PREFIX + chapterId;
    const payload = {
        title, content, cursorPosition, scrollTop, 
        timestamp: Date.now()
    };
    
    try {
        localStorage.setItem(key, JSON.stringify(payload));
    } catch (e) {
        // 如果触发 QuotaExceededError，执行清理逻辑
        cleanupOldCaches();
        localStorage.setItem(key, JSON.stringify(payload));
    }
}

function cleanupOldCaches() {
    const keys = Object.keys(localStorage).filter(k => k.startsWith(CACHE_PREFIX));
    if (keys.length === 0) return;
    
    const items = keys.map(k => ({
        key: k,
        timestamp: JSON.parse(localStorage.getItem(k)).timestamp || 0
    })).sort((a, b) => a.timestamp - b.timestamp);
    
    // 删除最旧的
    localStorage.removeItem(items[0].key);
}
```

- [ ] **Step 2: ChapterStore 状态机与乐观锁处理**

```javascript
// frontend/src/stores/chapterStore.js
import { defineStore } from 'pinia';
import { updateChapterApi } from '@/api/chapters';
import { saveLocalDraft } from '@/utils/localCache';

export const useChapterStore = defineStore('chapter', {
    state: () => ({
        activeChapter: null,
        saveState: '已保存', // '保存中', '已保存', '保存失败'
        isOffline: !navigator.onLine
    }),
    actions: {
        async saveContent(title, content, wordCount, version, forceOverride = false) {
            this.saveState = '保存中';
            saveLocalDraft(this.activeChapter.id, title, content, 0, 0); // 优先写本地
            
            if (this.isOffline) {
                this.saveState = '保存失败'; // 离线模式暂存本地
                return;
            }
            
            try {
                const res = await updateChapterApi(this.activeChapter.id, title, content, wordCount, version, forceOverride);
                this.activeChapter.version = res.version;
                this.saveState = '已保存';
                // 成功后可清理对应本地缓存
                localStorage.removeItem('inktrace_draft_' + this.activeChapter.id);
            } catch (err) {
                if (err.response?.status === 409) {
                    // R-SAVE-08: 触发冲突，必须保留本地缓存，等待用户决策
                    this.saveState = '保存失败';
                    throw new Error('VERSION_CONFLICT');
                }
                this.saveState = '保存失败';
            }
        }
    }
});
```

### Task 5: 基础 UI 框架：书架与写作页

**Files:**
- Create: `frontend/src/views/WorksList.vue`
- Create: `frontend/src/views/WritingStudio.vue`
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: 路由配置**

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import WorksList from '../views/WorksList.vue'
import WritingStudio from '../views/WritingStudio.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: WorksList },
    { path: '/work/:id', component: WritingStudio, props: true }
  ]
})
export default router
```

- [ ] **Step 2: 写作页 (WritingStudio.vue) 布局与纯文本编辑器**

必须遵守 `R-EDIT-04`：仅支持纯文本，以及 `R-UI-02`：仅显示三态提示。

```vue
<template>
  <div class="writing-studio">
    <div class="sidebar">
      <!-- 虚拟列表渲染章节 -->
      <ChapterList :workId="workId" />
    </div>
    <div class="editor-area">
      <div class="status-bar">
        <span>{{ saveState }}</span>
        <span v-if="isOffline" class="offline-badge">离线模式</span>
      </div>
      <input v-model="title" class="title-input" placeholder="未命名章节" @input="triggerAutoSave" />
      <textarea 
        v-model="content" 
        class="content-textarea" 
        @input="handleInput"
        @paste="handlePaste"
        ref="editorRef"
      ></textarea>
      <div class="footer">字数: {{ wordCount }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
// ... 引入 store ...

const handlePaste = (e) => {
    // 强制纯文本粘贴
    e.preventDefault();
    const text = (e.originalEvent || e).clipboardData.getData('text/plain');
    document.execCommand('insertText', false, text);
};

const wordCount = computed(() => {
    // R-EDIT-02: 仅统计有效字符数，剔除不可见字符
    return content.value.replace(/\s+/g, '').length;
});
</script>
```

### Task 6: TXT 导入与导出链路 (P2)

**Files:**
- Create: `presentation/api/routers/io.py`
- Modify: `application/services/io_service.py`

- [ ] **Step 1: TXT 导入解析**

遵守 `R-DATA-03`：导入绝不中断，未识别则整本入单章。

```python
import re

def import_txt_to_work(db: Session, file_content: str, title: str):
    work = create_work(db, title=title)
    
    # 简单的章节正则匹配：第XXX章
    pattern = re.compile(r'(第[零一二三四五六七八九十百千0-9]+章.*)')
    parts = pattern.split(file_content)
    
    if len(parts) <= 1:
        # 未识别出任何章节，整本塞入
        update_chapter_content(db, work.chapters[0].id, title="全本导入", content=file_content, word_count=len(file_content.strip()), version=1)
        return work
        
    # 如果识别出章节，解析 parts 并按序生成 ChapterModel
    # ... 省略具体字符串拼接逻辑 ...
    db.commit()
    return work
```

- [ ] **Step 2: TXT 导出**

遵守 `R-DATA-04`：按 `order_index` 拼接导出。

```python
def export_work_to_txt(db: Session, work_id: str) -> str:
    chapters = db.query(ChapterModel).filter(ChapterModel.work_id == work_id).order_by(ChapterModel.order_index).all()
    
    result = []
    for ch in chapters:
        result.append(f"{ch.title}\n\n{ch.content}\n\n")
        
    return "".join(result)
```

---

## 总结与下一步

计划已就绪。这个计划将原本过度设计的 AI 工作流彻底精简为 **稳定可靠的数据 CRUD** + **健壮的纯文本编辑体验**。

您可以选择：
1. **确认该计划**，然后我们进入具体的代码修改与测试环节。
2. **提出修改意见**，我们可以调整具体的实现细节。
