# ARCH_AI小说自动编写助手_架构设计文档

**项目名称**: AI小说自动编写助手 (InkTrace Novel AI)  
**阶段**: Phase 2 - Architect 架构设计  
**作者**: 孔利群  
**日期**: 2026-03-12  

---

## 一、架构概览

### 1.1 分层架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Presentation Layer                             │
│                              (表现层)                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Web API   │  │   WebSocket │  │   Static    │  │    CLI      │    │
│  │  (FastAPI)  │  │  (实时通信)  │  │   (前端)    │  │  (命令行)   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Application Layer                               │
│                              (应用层)                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Project   │  │   Content   │  │   Writing   │  │   Export    │    │
│  │  Service    │  │  Service    │  │  Service    │  │  Service    │    │
│  │ (项目管理)  │  │ (内容管理)  │  │ (续写服务)  │  │ (导出服务)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                             Domain Layer                                 │
│                              (领域层)                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        聚合根 (Aggregate Root)                    │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │  Novel    │  │  Chapter  │  │  Outline  │  │ Character │    │   │
│  │  │  (小说)   │  │  (章节)   │  │  (大纲)   │  │  (人物)   │    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        实体 (Entity)                              │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │  Plot     │  │ Timeline  │  │  Foreshad │  │WorldView  │    │   │
│  │  │  (剧情)   │  │ (时间线)  │  │ (伏笔)    │  │(世界观)   │    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        值对象 (Value Object)                      │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │StyleProfile│ │CharacterSt│  │PlotNode   │  │WritingConf│    │   │
│  │  │(文风特征) │  │ate(人物状态)│ │(剧情节点) │  │ig(写作配置)│   │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      领域服务 (Domain Service)                    │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │StyleAnalyz│ │PlotAnalyzr│  │ConsistChk │  │WritingEng │    │   │
│  │  │er(文风分析)│ │(剧情分析) │  │(连贯性检查)│ │(写作引擎) │    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      仓储接口 (Repository Interface)              │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │INovelRepo │ │IChapterRep│  │IOutlineRep│  │ICharacterR│    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Infrastructure Layer                              │
│                              (基础设施层)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   LLM       │  │   File      │  │   Database  │  │   Cache     │    │
│  │  Adapter    │  │  Adapter    │  │  Adapter    │  │  Adapter    │    │
│  │ (大模型适配)│  │ (文件适配)  │  │ (数据库适配)│  │ (缓存适配)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │  DeepSeek   │  │    Kimi     │  │   SQLite    │                     │
│  │  Client     │  │   Client    │  │  /JSON      │                     │
│  └─────────────┘  └─────────────┘  └─────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术选型 | 说明 |
|-----|---------|-----|
| 表现层 | FastAPI + WebSocket + Vue3 | Web应用，支持实时通信 |
| 应用层 | Python 3.11+ | 业务逻辑编排 |
| 领域层 | Python + Pydantic | 领域模型，纯Python实现 |
| 基础设施层 | httpx + SQLite + Redis | 外部依赖适配 |
| 大模型 | DeepSeek API + Kimi API | 主备模型 |
| 测试 | pytest + pytest-cov | 单元测试，覆盖率≥80% |

---

## 二、模块设计

### 2.1 模块总览

```
ink-trace/
├── domain/                    # 领域层
│   ├── entities/              # 实体
│   │   ├── novel.py           # 小说聚合根
│   │   ├── chapter.py         # 章节实体
│   │   ├── outline.py         # 大纲聚合根
│   │   ├── character.py       # 人物实体
│   │   ├── plot.py            # 剧情实体
│   │   ├── timeline.py        # 时间线实体
│   │   ├── foreshadowing.py   # 伏笔实体
│   │   └── worldview.py       # 世界观实体
│   ├── value_objects/         # 值对象
│   │   ├── style_profile.py   # 文风特征
│   │   ├── character_state.py # 人物状态
│   │   ├── plot_node.py       # 剧情节点
│   │   └── writing_config.py  # 写作配置
│   ├── services/              # 领域服务
│   │   ├── style_analyzer.py  # 文风分析服务
│   │   ├── plot_analyzer.py   # 剧情分析服务
│   │   ├── consistency_checker.py  # 连贯性检查服务
│   │   └── writing_engine.py  # 写作引擎服务
│   ├── repositories/          # 仓储接口
│   │   ├── novel_repository.py
│   │   ├── chapter_repository.py
│   │   ├── outline_repository.py
│   │   └── character_repository.py
│   └── events/                # 领域事件
│       └── domain_events.py
│
├── application/               # 应用层
│   ├── services/              # 应用服务
│   │   ├── project_service.py     # 项目管理服务
│   │   ├── content_service.py     # 内容管理服务
│   │   ├── writing_service.py     # 续写服务
│   │   └── export_service.py      # 导出服务
│   ├── dto/                   # 数据传输对象
│   │   ├── request_dto.py
│   │   └── response_dto.py
│   └── use_cases/             # 用例
│       ├── import_novel.py
│       ├── analyze_novel.py
│       ├── generate_chapter.py
│       └── export_novel.py
│
├── infrastructure/            # 基础设施层
│   ├── llm/                   # 大模型适配
│   │   ├── base_client.py     # 基础客户端接口
│   │   ├── deepseek_client.py # DeepSeek客户端
│   │   ├── kimi_client.py     # Kimi客户端
│   │   └── llm_factory.py     # 客户端工厂
│   ├── persistence/           # 持久化适配
│   │   ├── sqlite_novel_repo.py
│   │   ├── sqlite_chapter_repo.py
│   │   ├── sqlite_outline_repo.py
│   │   └── sqlite_character_repo.py
│   ├── file/                  # 文件适配
│   │   ├── txt_parser.py      # TXT解析器
│   │   ├── markdown_exporter.py  # Markdown导出
│   │   └── file_watcher.py    # 文件监控
│   └── cache/                 # 缓存适配
│       └── redis_cache.py
│
├── presentation/              # 表现层
│   ├── api/                   # REST API
│   │   ├── routers/
│   │   │   ├── novel.py
│   │   │   ├── chapter.py
│   │   │   ├── writing.py
│   │   │   └── export.py
│   │   └── dependencies.py
│   ├── websocket/             # WebSocket
│   │   └── ws_handler.py
│   └── static/                # 前端静态文件
│       └── (Vue3应用)
│
├── data/                      # 数据目录
│   └── novel/                 # 小说文件
│
├── tests/                     # 测试
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   └── fixtures/              # 测试数据
│
└── docs/                      # 文档
```

---

## 三、领域模型

### 3.1 聚合设计

#### 3.1.1 Novel聚合（小说聚合根）

```python
@dataclass
class Novel:
    """小说聚合根"""
    id: NovelId
    title: str                    # 小说标题
    author: str                   # 作者
    genre: str                    # 题材
    target_word_count: int        # 目标字数
    current_word_count: int       # 当前字数
    chapters: List[Chapter]       # 章节列表
    outline: Outline              # 大纲
    characters: List[Character]   # 人物列表
    worldview: WorldView          # 世界观
    style_profile: StyleProfile   # 文风特征
    created_at: datetime
    updated_at: datetime
```

#### 3.1.2 Chapter实体（章节）

```python
@dataclass
class Chapter:
    """章节实体"""
    id: ChapterId
    number: int                   # 章节号
    title: str                    # 章节标题
    content: str                  # 章节内容
    word_count: int               # 字数
    summary: str                  # 章节摘要
    characters_involved: List[CharacterId]  # 涉及人物
    plot_nodes: List[PlotNode]    # 剧情节点
    foreshadowings: List[Foreshadowing]  # 伏笔
    status: ChapterStatus         # 状态：draft/published
    created_at: datetime
    updated_at: datetime
```

#### 3.1.3 Outline聚合（大纲聚合根）

```python
@dataclass
class Outline:
    """大纲聚合根"""
    id: OutlineId
    novel_id: NovelId
    premise: str                  # 核心设定
    story_background: str         # 故事背景
    world_setting: str            # 世界观设定
    main_plot: List[PlotNode]     # 主线剧情
    sub_plots: List[PlotNode]     # 支线剧情
    volumes: List[VolumeOutline]  # 分卷大纲
    created_at: datetime
    updated_at: datetime

@dataclass
class VolumeOutline:
    """分卷大纲"""
    number: int                   # 卷号
    title: str                    # 卷名
    summary: str                  # 卷摘要
    target_word_count: int        # 目标字数
    plot_nodes: List[PlotNode]    # 剧情节点
```

#### 3.1.4 Character实体（人物）

```python
@dataclass
class Character:
    """人物实体"""
    id: CharacterId
    name: str                     # 姓名
    aliases: List[str]            # 别名/绰号
    role: CharacterRole           # 角色：protagonist/antagonist/supporting
    background: str               # 背景故事
    personality: str              # 性格特点
    abilities: List[str]          # 能力/功法
    relationships: List[CharacterRelationship]  # 人物关系
    current_state: CharacterState # 当前状态
    appearance_count: int         # 出场次数
    first_appearance: ChapterId   # 首次出场
    created_at: datetime
    updated_at: datetime
```

### 3.2 值对象设计

#### 3.2.1 StyleProfile（文风特征）

```python
@dataclass(frozen=True)
class StyleProfile:
    """文风特征值对象"""
    vocabulary_stats: Dict[str, float]    # 词汇统计
    sentence_patterns: List[str]          # 句式模板
    rhetoric_stats: Dict[str, int]        # 修辞统计
    dialogue_style: str                   # 对话风格
    narrative_voice: str                  # 叙述视角
    pacing: str                           # 节奏特点
    sample_sentences: List[str]           # 示例句子
```

#### 3.2.2 CharacterState（人物状态）

```python
@dataclass(frozen=True)
class CharacterState:
    """人物状态值对象"""
    character_id: CharacterId
    location: str                  # 当前位置
    cultivation_level: str         # 修为境界
    health_status: str             # 健康状态
    emotional_state: str           # 情绪状态
    possessions: List[str]         # 持有物品
    active_goals: List[str]        # 当前目标
    chapter_id: ChapterId          # 状态所在章节
```

#### 3.2.3 PlotNode（剧情节点）

```python
@dataclass(frozen=True)
class PlotNode:
    """剧情节点值对象"""
    id: str
    title: str                     # 节点标题
    description: str               # 节点描述
    type: PlotType                 # 类型：main/sub/foreshadowing
    status: PlotStatus             # 状态：planned/ongoing/completed
    start_chapter: Optional[int]   # 开始章节
    end_chapter: Optional[int]     # 结束章节
    involved_characters: List[CharacterId]  # 涉及人物
    dependencies: List[str]        # 依赖节点
```

### 3.3 领域服务设计

#### 3.3.1 StyleAnalyzer（文风分析服务）

```python
class StyleAnalyzer:
    """文风分析领域服务"""
    
    def analyze(self, chapters: List[Chapter]) -> StyleProfile:
        """分析章节文风，生成文风特征"""
        pass
    
    def analyze_vocabulary(self, text: str) -> Dict[str, float]:
        """分析词汇特征"""
        pass
    
    def analyze_sentence_patterns(self, text: str) -> List[str]:
        """分析句式模板"""
        pass
    
    def analyze_rhetoric(self, text: str) -> Dict[str, int]:
        """分析修辞手法"""
        pass
```

#### 3.3.2 PlotAnalyzer（剧情分析服务）

```python
class PlotAnalyzer:
    """剧情分析领域服务"""
    
    def analyze(self, novel: Novel) -> PlotAnalysisResult:
        """分析小说剧情结构"""
        pass
    
    def extract_characters(self, chapters: List[Chapter]) -> List[Character]:
        """提取人物信息"""
        pass
    
    def build_timeline(self, chapters: List[Chapter]) -> Timeline:
        """构建时间线"""
        pass
    
    def extract_foreshadowings(self, chapters: List[Chapter]) -> List[Foreshadowing]:
        """提取伏笔"""
        pass
```

#### 3.3.3 ConsistencyChecker（连贯性检查服务）

```python
class ConsistencyChecker:
    """连贯性检查领域服务"""
    
    def check(self, new_chapter: Chapter, novel: Novel) -> ConsistencyReport:
        """检查新章节与已有内容的连贯性"""
        pass
    
    def check_character_state(self, character: Character, chapter: Chapter) -> List[Inconsistency]:
        """检查人物状态一致性"""
        pass
    
    def check_timeline(self, timeline: Timeline, chapter: Chapter) -> List[Inconsistency]:
        """检查时间线一致性"""
        pass
    
    def check_foreshadowing(self, foreshadowings: List[Foreshadowing], chapter: Chapter) -> List[Inconsistency]:
        """检查伏笔回收"""
        pass
```

#### 3.3.4 WritingEngine（写作引擎服务）

```python
class WritingEngine:
    """写作引擎领域服务"""
    
    def __init__(self, llm_client: LLMClient, style_profile: StyleProfile):
        self.llm_client = llm_client
        self.style_profile = style_profile
    
    def generate_chapter(
        self, 
        context: WritingContext, 
        plot_direction: str,
        target_word_count: int
    ) -> Chapter:
        """生成章节内容"""
        pass
    
    def plan_plot(self, outline: Outline, start_chapter: int, direction: str) -> List[PlotNode]:
        """规划剧情走向"""
        pass
    
    def apply_style(self, content: str, style_profile: StyleProfile) -> str:
        """应用文风"""
        pass
```

---

## 四、仓储接口设计

```python
class INovelRepository(ABC):
    """小说仓储接口"""
    
    @abstractmethod
    def save(self, novel: Novel) -> None:
        pass
    
    @abstractmethod
    def find_by_id(self, novel_id: NovelId) -> Optional[Novel]:
        pass
    
    @abstractmethod
    def find_all(self) -> List[Novel]:
        pass
    
    @abstractmethod
    def delete(self, novel_id: NovelId) -> None:
        pass


class IChapterRepository(ABC):
    """章节仓储接口"""
    
    @abstractmethod
    def save(self, chapter: Chapter) -> None:
        pass
    
    @abstractmethod
    def find_by_id(self, chapter_id: ChapterId) -> Optional[Chapter]:
        pass
    
    @abstractmethod
    def find_by_novel(self, novel_id: NovelId) -> List[Chapter]:
        pass
    
    @abstractmethod
    def find_latest(self, novel_id: NovelId, count: int) -> List[Chapter]:
        pass


class IOutlineRepository(ABC):
    """大纲仓储接口"""
    
    @abstractmethod
    def save(self, outline: Outline) -> None:
        pass
    
    @abstractmethod
    def find_by_novel(self, novel_id: NovelId) -> Optional[Outline]:
        pass


class ICharacterRepository(ABC):
    """人物仓储接口"""
    
    @abstractmethod
    def save(self, character: Character) -> None:
        pass
    
    @abstractmethod
    def find_by_id(self, character_id: CharacterId) -> Optional[Character]:
        pass
    
    @abstractmethod
    def find_by_novel(self, novel_id: NovelId) -> List[Character]:
        pass
```

---

## 五、基础设施适配器设计

### 5.1 大模型客户端接口

```python
class LLMClient(ABC):
    """大模型客户端接口"""
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[Dict], 
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> str:
        """对话生成"""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型名称"""
        pass
    
    @property
    @abstractmethod
    def max_context_tokens(self) -> int:
        """最大上下文token数"""
        pass
```

### 5.2 主备模型切换

```python
class LLMFactory:
    """大模型客户端工厂"""
    
    def __init__(self, config: LLMConfig):
        self.primary_client = DeepSeekClient(config.deepseek)
        self.backup_client = KimiClient(config.kimi)
        self.current_client = self.primary_client
    
    async def get_client(self) -> LLMClient:
        """获取可用客户端，主模型失败时切换备用"""
        try:
            # 检查主模型可用性
            if await self._check_availability(self.primary_client):
                return self.primary_client
        except Exception:
            pass
        
        # 切换到备用模型
        self.current_client = self.backup_client
        return self.backup_client
    
    async def _check_availability(self, client: LLMClient) -> bool:
        """检查客户端可用性"""
        pass
```

### 5.3 文件解析器

```python
class TxtParser:
    """TXT文件解析器"""
    
    def parse_novel(self, file_path: str) -> Tuple[List[Chapter], str]:
        """解析小说文件，返回章节列表和简介"""
        pass
    
    def parse_outline(self, file_path: str) -> Outline:
        """解析大纲文件"""
        pass
    
    def _detect_chapter_pattern(self, text: str) -> Pattern:
        """自动检测章节标题模式"""
        pass
    
    def _extract_chapter_content(self, text: str, pattern: Pattern) -> List[Tuple[str, str]]:
        """提取章节内容"""
        pass
```

---

## 六、API设计

### 6.1 REST API端点

| 方法 | 路径 | 说明 |
|-----|-----|-----|
| POST | /api/novels | 创建小说项目 |
| GET | /api/novels | 获取小说列表 |
| GET | /api/novels/{id} | 获取小说详情 |
| POST | /api/novels/{id}/import | 导入小说文件 |
| POST | /api/novels/{id}/analyze | 分析小说 |
| GET | /api/novels/{id}/style | 获取文风分析结果 |
| GET | /api/novels/{id}/characters | 获取人物列表 |
| GET | /api/novels/{id}/timeline | 获取时间线 |
| POST | /api/novels/{id}/plan-plot | 规划剧情走向 |
| POST | /api/novels/{id}/generate | 生成章节 |
| GET | /api/chapters/{id} | 获取章节详情 |
| PUT | /api/chapters/{id} | 更新章节 |
| POST | /api/novels/{id}/export | 导出小说 |

### 6.2 WebSocket事件

| 事件 | 方向 | 说明 |
|-----|-----|-----|
| analysis:progress | Server→Client | 分析进度 |
| generation:start | Server→Client | 开始生成 |
| generation:progress | Server→Client | 生成进度 |
| generation:complete | Server→Client | 生成完成 |
| generation:error | Server→Client | 生成错误 |

---

## 七、数据持久化

### 7.1 存储方案

一期采用SQLite + JSON文件混合存储：
- **SQLite**: 结构化数据（小说元信息、章节索引、人物信息）
- **JSON文件**: 分析结果（文风特征、剧情分析结果）
- **文件系统**: 原始文件、生成内容

### 7.2 数据库表设计

```sql
-- 小说表
CREATE TABLE novels (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    genre TEXT,
    target_word_count INTEGER,
    current_word_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 章节表
CREATE TABLE chapters (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    number INTEGER NOT NULL,
    title TEXT,
    word_count INTEGER,
    summary TEXT,
    status TEXT DEFAULT 'draft',
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 人物表
CREATE TABLE characters (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT,
    background TEXT,
    personality TEXT,
    current_state TEXT,
    appearance_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 大纲表
CREATE TABLE outlines (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL UNIQUE,
    premise TEXT,
    story_background TEXT,
    world_setting TEXT,
    main_plot TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);
```

---

## 八、核心流程设计

### 8.1 导入分析流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   上传文件    │────▶│   解析文件    │────▶│  创建Novel   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  保存分析结果 │◀────│  剧情分析    │◀────│  文风分析    │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       │                    ▼                    │
       │             ┌──────────────┐            │
       │             │  提取人物    │            │
       │             └──────────────┘            │
       │                    │                    │
       │                    ▼                    │
       │             ┌──────────────┐            │
       └────────────▶│  构建时间线   │◀───────────┘
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  提取伏笔    │
                     └──────────────┘
```

### 8.2 交互式续写流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  用户提出需求 │────▶│  规划剧情走向 │────▶│  展示给用户  │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                           ┌─────────────────────┘
                           ▼
                    ┌──────────────┐
                    │  用户确认    │
                    └──────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌──────────────┐          ┌──────────────┐
       │ 指定章节数   │          │ 让AI写完剧情  │
       └──────────────┘          └──────────────┘
              │                         │
              └────────────┬────────────┘
                           ▼
                    ┌──────────────┐
                    │  生成章节    │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ 连贯性检查   │
                    └──────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌──────────────┐          ┌──────────────┐
       │  通过检查    │          │  存在问题    │
       └──────────────┘          └──────────────┘
              │                         │
              ▼                         ▼
       ┌──────────────┐          ┌──────────────┐
       │  保存章节    │          │  提示修改    │
       └──────────────┘          └──────────────┘
```

---

## 九、依赖关系

### 9.1 依赖方向（由外向内）

```
Presentation → Application → Domain ← Infrastructure
```

- 领域层无外部依赖，完全独立
- 应用层依赖领域层接口
- 基础设施层实现领域层接口
- 表现层依赖应用层

### 9.2 外部依赖

| 依赖 | 用途 | 版本 |
|-----|-----|-----|
| fastapi | Web框架 | ^0.109.0 |
| uvicorn | ASGI服务器 | ^0.27.0 |
| pydantic | 数据验证 | ^2.5.0 |
| httpx | HTTP客户端 | ^0.26.0 |
| jieba | 中文分词 | ^0.42.1 |
| pytest | 测试框架 | ^8.0.0 |
| pytest-cov | 测试覆盖率 | ^4.1.0 |
| aiocache | 缓存 | ^0.12.0 |

---

## 十、下一步行动

1. **用户确认**: 审阅架构设计，确认技术选型和模块划分
2. **进入Atomize**: 确认后进入任务拆解阶段

---

**文档状态**: 待审批  
**审批人**: 用户  
**审批日期**: 待填写
