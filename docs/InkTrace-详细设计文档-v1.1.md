# InkTrace 详细设计文档（v1.1）

更新时间：2026-04-27
适用阶段：当前版本

---

## 1. 详细设计目标

基于架构设计文档（v1.1），本详细设计文档旨在将架构蓝图拆解为具体的**组件级实现方案、接口通信协议及核心算法伪代码**。本设计将作为开发阶段的直接实现依据，确保所有模块遵循“简单、可靠、容错”的核心原则。

---

## 2. 后端详细设计 (FastAPI + SQLAlchemy)

### 2.1 数据库与 ORM 模型

为实现 `R-SAVE-04` (乐观锁) 和性能目标，数据库引擎使用 SQLite 并配置 WAL 模式。

#### 2.1.1 数据库连接配置 (`database/session.py`)

在 FastAPI 启动生命周期（`lifespan`）中配置引擎参数：

```python
from sqlalchemy import create_engine, event

# 启用 WAL 模式以提升并发读写性能
engine = create_engine(
    "sqlite:///./inktrace.db",
    connect_args={"check_same_thread": False}, # 允许 FastAPI 的多线程访问
    pool_size=5,
    max_overflow=10
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000") # 5秒超时，防止锁定
    cursor.close()
```

#### 2.1.2 核心 ORM 模型 (`database/models.py`)

详细 ORM 定义（仅展示关键部分）：

```python
class ChapterModel(Base):
    __tablename__ = "chapters"
    
    id = Column(String(36), primary_key=True)
    work_id = Column(String(36), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="")
    content = Column(Text, nullable=False, default="")
    order_index = Column(Integer, nullable=False, index=True) # 用于快速排序
    version = Column(Integer, nullable=False, default=1)      # 乐观锁
    
    # ... 其他基础字段 ...
```

### 2.2 核心业务服务 (Service Layer)

#### 2.2.1 保存章节与乐观锁校验 (`application/services/chapter_service.py`)

实现带版本控制的正文保存，处理并发冲突。

```python
from sqlalchemy.orm import Session
from fastapi import HTTPException

def update_chapter_content(db: Session, chapter_id: str, title: str, content: str, client_version: int, force_override: bool = False):
    chapter = db.query(ChapterModel).filter(ChapterModel.id == chapter_id).first()
    
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # 乐观锁校验
    if not force_override and chapter.version != client_version:
        raise HTTPException(
            status_code=409, 
            detail={"message": "Version conflict", "server_version": chapter.version}
        )

    # 执行更新
    chapter.title = title
    chapter.content = content
    # 重新计算字数（服务端也需校验）
    chapter.word_count = len(re.sub(r'\s+', '', content)) 
    chapter.version += 1 # 版本递增
    
    db.commit()
    return chapter # 返回更新后的实体，包含新 version
```

#### 2.2.2 原子化全量调序 (`application/services/chapter_service.py`)

确保拖拽排序的数据一致性。

```python
def reorder_chapters(db: Session, work_id: str, order_mapping: list[dict]):
    """
    order_mapping: [{"id": "uuid1", "order_index": 1}, {"id": "uuid2", "order_index": 2}]
    """
    try:
        # 在一个事务中执行所有更新
        for mapping in order_mapping:
            db.query(ChapterModel).filter(
                ChapterModel.id == mapping["id"], 
                ChapterModel.work_id == work_id
            ).update({"order_index": mapping["order_index"]})
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Reorder failed, transaction rolled back.")
```

### 2.3 TXT 导入策略 (`application/services/io_service.py`)

实现 `R-DATA-03`：采用非中断的正则分割。

```python
import re
import uuid

def import_txt(db: Session, file_content: str, work_title: str):
    work_id = str(uuid.uuid4())
    work = WorkModel(id=work_id, title=work_title)
    db.add(work)

    # 匹配 "第XXX章" 及其标题，支持卷/部，但统一视为章
    pattern = re.compile(r'(第[零一二三四五六七八九十百千0-9]+[章卷部].*?\n)')
    
    # split 会返回: [前言, 标题1, 内容1, 标题2, 内容2...]
    parts = pattern.split(file_content)
    
    chapters_to_insert = []
    order_idx = 1
    
    # 兜底：如果没有匹配到任何章节
    if len(parts) <= 1:
         chapters_to_insert.append(ChapterModel(
             id=str(uuid.uuid4()), work_id=work_id, 
             title="全本导入", content=file_content, order_index=order_idx
         ))
    else:
        # parts[0] 可能是前言或空字符串
        if parts[0].strip():
            chapters_to_insert.append(ChapterModel(
                id=str(uuid.uuid4()), work_id=work_id, 
                title="前言", content=parts[0], order_index=order_idx
            ))
            order_idx += 1
            
        # 遍历标题和内容对
        for i in range(1, len(parts), 2):
            title = parts[i].strip()
            content = parts[i+1] if i+1 < len(parts) else ""
            
            chapters_to_insert.append(ChapterModel(
                id=str(uuid.uuid4()), work_id=work_id, 
                title=title, content=content, order_index=order_idx
            ))
            order_idx += 1

    db.add_all(chapters_to_insert)
    db.commit()
```

---

## 3. 前端详细设计 (Vue3 + Pinia)

### 3.1 本地缓存与 LRU 管理 (`utils/localCache.js`)

实现 Local-First 核心机制，确保容量不超过 10MB。

```javascript
const CACHE_PREFIX = 'inktrace_draft_';
const MAX_CACHE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB 软限制

// 估算字符串字节大小
function getByteLen(normal_val) {
    normal_val = String(normal_val);
    var byteLen = 0;
    for (var i = 0; i < normal_val.length; i++) {
        var c = normal_val.charCodeAt(i);
        byteLen += c < (1 << 7) ? 1 :
                   c < (1 << 11) ? 2 :
                   c < (1 << 16) ? 3 :
                   c < (1 << 21) ? 4 :
                   c < (1 << 26) ? 5 :
                   c < (1 << 31) ? 6 : Number.NaN;
    }
    return byteLen;
}

export function saveLocalDraft(chapterId, payload) {
    const key = `${CACHE_PREFIX}${chapterId}`;
    payload.timestamp = Date.now();
    const payloadStr = JSON.stringify(payload);
    
    // 检查容量并执行 LRU 清理
    enforceCacheQuota(getByteLen(payloadStr));
    
    localStorage.setItem(key, payloadStr);
}

function enforceCacheQuota(newPayloadSize) {
    let currentSize = 0;
    const drafts = [];
    
    // 收集所有草稿信息
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.startsWith(CACHE_PREFIX)) {
            const itemStr = localStorage.getItem(key);
            currentSize += getByteLen(itemStr);
            try {
                const parsed = JSON.parse(itemStr);
                drafts.push({ key, timestamp: parsed.timestamp || 0 });
            } catch(e) {}
        }
    }
    
    // 如果超限，按时间戳升序排序（最旧的在前），逐个删除直到腾出足够空间
    if (currentSize + newPayloadSize > MAX_CACHE_SIZE_BYTES) {
        drafts.sort((a, b) => a.timestamp - b.timestamp);
        
        for (const draft of drafts) {
            const sizeFreed = getByteLen(localStorage.getItem(draft.key));
            localStorage.removeItem(draft.key);
            currentSize -= sizeFreed;
            if (currentSize + newPayloadSize <= MAX_CACHE_SIZE_BYTES) {
                break;
            }
        }
    }
}
```

### 3.2 保存状态机与同步逻辑 (`stores/chapterStore.js`)

处理防抖保存、乐观锁冲突和离线回放。

```javascript
import { defineStore } from 'pinia'
import debounce from 'lodash/debounce'
import { saveLocalDraft } from '@/utils/localCache'
import api from '@/api' // 封装了 axios 的请求实例

export const useChapterStore = defineStore('chapter', {
  state: () => ({
    activeChapter: null, // { id, title, content, version, wordCount }
    saveState: '已保存',  // '已保存' | '保存中' | '保存失败'
    isOffline: !navigator.onLine
  }),
  
  actions: {
    // 每次输入触发此方法
    handleInput(title, content) {
        this.activeChapter.title = title;
        this.activeChapter.content = content;
        this.saveState = '保存中';
        
        // 1. 立即写入本地草稿 (Local-First)
        saveLocalDraft(this.activeChapter.id, {
            title,
            content,
            version: this.activeChapter.version // 记录基于哪个版本修改的
        });
        
        // 2. 触发防抖 API 请求
        this.debouncedSync();
    },
    
    // 防抖 2 秒同步到远端
    debouncedSync: debounce(async function() {
        if (this.isOffline) {
            this.saveState = '保存失败'; // 离线仅写本地
            return;
        }
        
        try {
            const res = await api.put(`/api/chapters/${this.activeChapter.id}`, {
                title: this.activeChapter.title,
                content: this.activeChapter.content,
                version: this.activeChapter.version
            });
            
            // 同步成功：更新本地版本号，清除草稿，更新状态
            this.activeChapter.version = res.data.version;
            localStorage.removeItem(`inktrace_draft_${this.activeChapter.id}`);
            this.saveState = '已保存';
            
        } catch (error) {
            this.saveState = '保存失败';
            
            // 处理乐观锁冲突 (409)
            if (error.response && error.response.status === 409) {
                // 触发 UI 提示冲突，等待用户决策
                this.handleVersionConflict(error.response.data.server_version);
            }
        }
    }, 2000),
    
    // 处理版本冲突
    handleVersionConflict(serverVersion) {
        // 在 UI 层面弹窗或显示通知
        // 如果用户选择覆盖：
        // 1. this.activeChapter.version = serverVersion
        // 2. 发起请求携带 force_override = true
    },
    
    // 网络恢复时的回放逻辑
    async replayOfflineDrafts() {
        if (this.isOffline) return;
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key.startsWith('inktrace_draft_')) {
                const chapterId = key.replace('inktrace_draft_', '');
                const draft = JSON.parse(localStorage.getItem(key));
                
                try {
                    const res = await api.put(`/api/chapters/${chapterId}`, {
                        title: draft.title,
                        content: draft.content,
                        version: draft.version
                    });
                    // 回放成功，清除缓存
                    localStorage.removeItem(key);
                } catch (error) {
                    // 回放冲突或失败，保留缓存
                    console.error(`Replay failed for ${chapterId}`, error);
                }
            }
        }
    }
  }
})
```

### 3.3 纯文本编辑器组件 (`components/PureTextEditor.vue`)

实现 `R-EDIT-04`，拦截富文本并统一口径计算字数。

```vue
<template>
  <div class="editor-container">
    <textarea 
      ref="textareaRef"
      v-model="localContent"
      @input="onInput"
      @paste="onPaste"
      class="pure-textarea"
      placeholder="开始创作..."
    ></textarea>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useChapterStore } from '@/stores/chapterStore'

const props = defineProps({
  chapterId: String,
  initialContent: String
})

const store = useChapterStore()
const localContent = ref(props.initialContent)
const textareaRef = ref(null)

// 拦截粘贴，仅提取纯文本
const onPaste = (e) => {
    e.preventDefault();
    // 获取纯文本
    let text = (e.originalEvent || e).clipboardData.getData('text/plain');
    
    // 插入到当前光标位置
    const el = textareaRef.value;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    
    localContent.value = localContent.value.substring(0, start) + text + localContent.value.substring(end);
    
    // 恢复光标位置
    setTimeout(() => {
        el.selectionStart = el.selectionEnd = start + text.length;
        onInput(); // 手动触发保存
    }, 0);
}

const onInput = () => {
    store.handleInput(store.activeChapter.title, localContent.value);
}
</script>

<style scoped>
.pure-textarea {
    width: 100%;
    height: 100%;
    resize: none;
    border: none;
    outline: none;
    font-family: 'Courier New', Courier, monospace; /* 或其他等宽/易读字体 */
    font-size: 16px;
    line-height: 1.6;
}
</style>
```

---

## 4. 关键交互流程与组件间通信

### 4.1 章节切换流程

为满足 `R-SAVE-03`（切章前必须确保可恢复），在用户点击侧边栏的另一章节时：

1. `ChapterSidebar.vue` 触发 `selectChapter(newId)`。
2. `useChapterStore` 检查 `saveState`：
   - 若为 `保存中`，调用 `debouncedSync.flush()` 强制立即执行。
   - 若强制执行后仍失败，检查本地缓存是否存在对应的 `inktrace_draft_ID`。如果存在，则允许切换。
3. 切换前，保存当前光标和滚动位置（`cursor_position`, `scroll_top`）到数据库（或先防抖写入本地缓存）。
4. 加载新章节数据，并恢复其光标与滚动位置。

### 4.2 虚拟列表排序通信

使用 `vuedraggable` 或类似库实现 `DraggableItem.vue`：

1. 用户拖拽结束，组件触发 `@end` 事件，得到新的数组 `newList`。
2. 前端立即使用 `newList` 更新 UI（乐观更新）。
3. 提取映射：`const mapping = newList.map((ch, index) => ({ id: ch.id, order_index: index + 1 }))`。
4. 调用 API：`api.put('/api/chapters/reorder', mapping)`。
5. 若 API 返回 500 失败，捕获异常并将前端列表回滚为拖拽前的状态，并提示用户。

---

## 5. 遗留系统清理说明

在实施本详细设计前，需清理以下不再需要的旧代码和依赖：
- 移除所有与 AI 分析、大纲生成、知识库嵌入相关的路由（`routers/content.py`, `routers/ai.py` 等）。
- 移除 `token_budget_manager.py` 及复杂的依赖注入容器设计。
- 移除前端 `NovelWorkspace.vue` 复杂的卡片切换逻辑，回归传统的 `Sidebar + MainContent` 布局。