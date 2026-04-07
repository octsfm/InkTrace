# ARCH_AI小说自动编写助手三期_架构设计文档

**项目名称**: AI小说自动编写助手三期 (InkTrace Novel AI V3)  
**阶段**: Phase 2 - Architect 架构设计  
**作者**: 孔利群  
**日期**: 2026-03-12  

---

## 一、架构概览

### 1.1 分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    表现层 (Presentation)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Novel API  │ │Writing API  │ │ Search API  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐                                            │
│  │  Vue3 UI    │                                            │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │WritingService│ │SearchService│ │RAGService  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐                            │
│  │EmbeddingSvc │ │ForeshadowSvc│                            │
│  └─────────────┘ └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    领域层 (Domain)                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     聚合根                           │    │
│  │  Novel  │  Chapter  │  Character  │  Worldview      │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     值对象                           │    │
│  │ EmbeddingVector │ SearchResult │ RAGContext        │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     领域服务                         │    │
│  │ VectorStore │ EmbeddingEngine │ RAGWriter          │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     仓储接口                         │    │
│  │ IVectorRepository │ IEmbeddingRepository           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  基础设施层 (Infrastructure)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ChromaDB     │ │EmbeddingModel│ │ LLM Client  │            │
│  │VectorStore  │ │text2vec     │ │ DeepSeek    │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐                            │
│  │SQLite Repo  │ │File Parser  │                            │
│  └─────────────┘ └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、模块设计

### 2.1 向量存储模块

```
domain/
├── value_objects/
│   ├── embedding_vector.py    # 向量值对象
│   └── search_result.py       # 搜索结果值对象
├── services/
│   └── vector_store.py        # 向量存储领域服务
└── repositories/
    └── vector_repository.py   # 向量仓储接口

infrastructure/
├── vector/
│   ├── chromadb_store.py      # ChromaDB实现
│   └── embedding_model.py     # 嵌入模型
└── persistence/
    └── sqlite_vector_repo.py  # 向量元数据存储

application/
└── services/
    ├── embedding_service.py   # 向量化服务
    └── search_service.py      # 搜索服务
```

### 2.2 RAG续写模块

```
domain/
├── value_objects/
│   └── rag_context.py         # RAG上下文值对象
├── services/
│   └── rag_writer.py          # RAG续写领域服务

application/
└── services/
    └── rag_service.py         # RAG应用服务

presentation/
└── api/
    └── routers/
        └── rag.py             # RAG API
```

### 2.3 伏笔追踪模块

```
domain/
├── entities/
│   └── foreshadow.py          # 伏笔实体
├── services/
│   └── foreshadow_tracker.py  # 伏笔追踪服务
└── repositories/
    └── foreshadow_repository.py

infrastructure/
├── vector/
│   └── foreshadow_embedder.py # 伏笔向量化
└── persistence/
    └── sqlite_foreshadow_repo.py

application/
└── services/
    └── foreshadow_service.py

presentation/
└── api/
    └── routers/
        └── foreshadow.py
```

---

## 三、领域模型

### 3.1 EmbeddingVector值对象

```python
@dataclass(frozen=True)
class EmbeddingVector:
    """向量值对象"""
    id: str                      # 向量ID
    content: str                 # 原始内容
    vector: List[float]          # 向量数据
    metadata: Dict[str, Any]     # 元数据
    source_type: str             # 来源类型：chapter/character/worldview
    source_id: str               # 来源ID
    created_at: datetime
```

### 3.2 SearchResult值对象

```python
@dataclass
class SearchResult:
    """搜索结果值对象"""
    id: str
    content: str
    score: float                 # 相似度分数
    source_type: str
    source_id: str
    metadata: Dict[str, Any]
```

### 3.3 RAGContext值对象

```python
@dataclass
class RAGContext:
    """RAG上下文值对象"""
    query: str                   # 用户查询
    related_chapters: List[SearchResult]   # 相关章节
    related_characters: List[SearchResult] # 相关人物
    related_worldview: List[SearchResult]  # 相关世界观
    foreshadows: List[SearchResult]        # 相关伏笔
    total_tokens: int            # 总Token数
```

### 3.4 Foreshadow实体

```python
@dataclass
class Foreshadow:
    """伏笔实体"""
    id: ForeshadowId
    novel_id: NovelId
    chapter_id: ChapterId        # 所在章节
    content: str                 # 伏笔内容
    foreshadow_type: str         # 类型：plot/character/item
    status: ForeshadowStatus     # 状态：pending/resolved
    resolved_chapter_id: Optional[ChapterId]  # 回收章节
    embedding_id: Optional[str]  # 向量ID
    created_at: datetime
    updated_at: datetime
```

---

## 四、数据库设计

### 4.1 向量存储（ChromaDB）

```python
# ChromaDB集合设计
collections = {
    "chapters": {
        "description": "章节内容向量",
        "metadata": ["novel_id", "chapter_number", "title"]
    },
    "characters": {
        "description": "人物设定向量",
        "metadata": ["novel_id", "character_id", "role"]
    },
    "worldview": {
        "description": "世界观设定向量",
        "metadata": ["novel_id", "type", "name"]
    },
    "foreshadows": {
        "description": "伏笔向量",
        "metadata": ["novel_id", "chapter_id", "status"]
    }
}
```

### 4.2 SQLite扩展表

```sql
-- 向量元数据表
CREATE TABLE embeddings (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    collection_name TEXT NOT NULL,
    content_hash TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 伏笔表
CREATE TABLE foreshadows (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    content TEXT NOT NULL,
    foreshadow_type TEXT,
    status TEXT DEFAULT 'pending',
    resolved_chapter_id TEXT,
    embedding_id TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels(id),
    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
);

-- 向量化任务表
CREATE TABLE embedding_tasks (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TEXT,
    completed_at TEXT
);
```

---

## 五、API设计

### 5.1 向量化API

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | /api/novels/{id}/embed | 向量化小说内容 |
| GET | /api/novels/{id}/embed/status | 获取向量化状态 |
| DELETE | /api/novels/{id}/embed | 删除向量数据 |

### 5.2 语义搜索API

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | /api/novels/{id}/search | 语义搜索 |
| GET | /api/novels/{id}/similar/{chapterId} | 查找相似章节 |

### 5.3 RAG续写API

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | /api/novels/{id}/rag/write | RAG增强续写 |
| POST | /api/novels/{id}/rag/context | 获取RAG上下文 |

### 5.4 伏笔API

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | /api/novels/{id}/foreshadows | 获取伏笔列表 |
| POST | /api/novels/{id}/foreshadows | 创建伏笔 |
| PUT | /api/novels/{id}/foreshadows/{fid}/resolve | 标记伏笔回收 |
| GET | /api/novels/{id}/foreshadows/pending | 获取未回收伏笔 |

---

## 六、技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 向量数据库 | ChromaDB | 本地轻量级向量数据库 |
| 嵌入模型 | text2vec-chinese | 中文优化嵌入模型 |
| LLM | DeepSeek-V3 | 主力生成模型 |
| 后端 | FastAPI | 沿用 |
| 前端 | Vue3 | 沿用 |
| 存储 | SQLite + ChromaDB | 混合存储 |

---

## 七、依赖安装

```txt
# requirements.txt 新增
chromadb>=0.4.0
sentence-transformers>=2.2.0
text2vec>=0.1.0
```

---

## 八、下一步行动

1. 用户确认架构设计
2. 进入Atomize阶段进行任务拆解

---

**文档状态**: 待确认  
**确认人**: 用户  
**确认日期**: 待填写
