# ARCH_AI小说自动编写助手二期_架构设计文档

**项目名称**: AI小说自动编写助手二期 (InkTrace Novel AI V2)  
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
│  │  Novel API  │ │Template API │ │Worldview API│            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │Character API│ │ Project API │ │  Vue3 UI    │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ProjectService│ │TemplateService│ │CharacterSvc│           │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐                            │
│  │WorldviewSvc │ │ConsistencySvc│                            │
│  └─────────────┘ └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    领域层 (Domain)                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     聚合根                           │    │
│  │  Novel  │  Project  │  Template  │  Worldview       │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     实体                             │    │
│  │ Character │ Technique │ Faction │ Location │ Item   │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     值对象                           │    │
│  │ CharacterRelation │ TechniqueLevel │ FactionRelation │   │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     领域服务                         │    │
│  │ CharacterAnalyzer │ WorldviewChecker │ TemplateMatcher│   │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     仓储接口                         │    │
│  │ IProjectRepo │ ITemplateRepo │ ICharacterRepo │ IWorldviewRepo│
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  基础设施层 (Infrastructure)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │SQLite Repo  │ │Template File│ │ LLM Client  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐                            │
│  │File Parser  │ │  Exporter   │                            │
│  └─────────────┘ └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、模块设计

### 2.1 多作品支持模块

```
domain/
├── entities/
│   └── project.py          # 项目实体
├── value_objects/
│   └── project_config.py   # 项目配置值对象
└── repositories/
    └── project_repository.py  # 项目仓储接口

infrastructure/
└── persistence/
    └── sqlite_project_repo.py  # SQLite实现

application/
└── services/
    └── project_service.py  # 项目管理服务

presentation/
└── api/
    └── routers/
        └── project.py      # 项目API
```

### 2.2 模板系统模块

```
domain/
├── entities/
│   └── template.py         # 模板实体
├── value_objects/
│   ├── template_config.py  # 模板配置
│   └── genre_type.py       # 题材类型枚举
└── repositories/
    └── template_repository.py

infrastructure/
├── templates/              # 预置模板文件
│   ├── xuanhuan.json       # 玄幻模板
│   ├── xianxia.json        # 仙侠模板
│   ├── dushi.json          # 都市模板
│   ├── lishi.json          # 历史模板
│   └── kehuan.json         # 科幻模板
└── persistence/
    └── sqlite_template_repo.py

application/
└── services/
    └── template_service.py

presentation/
└── api/
    └── routers/
        └── template.py
```

### 2.3 人设管理模块

```
domain/
├── entities/
│   └── character.py        # 扩展人物实体
├── value_objects/
│   ├── character_relation.py  # 人物关系值对象
│   ├── character_state.py     # 人物状态
│   └── character_template.py  # 人物模板
└── services/
    └── character_analyzer.py  # 人物分析服务

infrastructure/
└── persistence/
    └── sqlite_character_repo.py  # 扩展实现

application/
└── services/
    └── character_service.py

presentation/
└── api/
    └── routers/
        └── character.py
```

### 2.4 世界观管理模块

```
domain/
├── entities/
│   ├── technique.py        # 功法实体
│   ├── faction.py          # 势力实体
│   ├── location.py         # 地点实体
│   ├── item.py             # 物品实体
│   └── worldview.py        # 世界观聚合根
├── value_objects/
│   ├── technique_level.py  # 功法等级
│   ├── faction_relation.py # 势力关系
│   └── power_system.py     # 力量体系
├── services/
│   └── worldview_checker.py  # 世界观一致性检查
└── repositories/
    └── worldview_repository.py

infrastructure/
└── persistence/
    └── sqlite_worldview_repo.py

application/
└── services/
    └── worldview_service.py

presentation/
└── api/
    └── routers/
        └── worldview.py
```

---

## 三、领域模型

### 3.1 Project聚合

```python
@dataclass
class Project:
    id: ProjectId
    name: str
    novel_id: NovelId
    genre: GenreType              # 题材类型
    style_config: StyleConfig     # 文风配置
    target_words: int             # 目标字数
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
```

### 3.2 Template聚合

```python
@dataclass
class Template:
    id: TemplateId
    name: str
    genre: GenreType
    description: str
    worldview_framework: dict     # 世界观框架
    character_templates: list     # 人物模板列表
    plot_templates: list          # 剧情模板
    style_reference: dict         # 文风参考
    is_builtin: bool              # 是否内置
```

### 3.3 Character扩展

```python
@dataclass
class Character:
    # 一期已有属性
    id: CharacterId
    novel_id: NovelId
    name: str
    role: CharacterRole
    
    # 二期扩展属性
    appearance: str               # 外貌描述
    personality: str              # 性格特点
    background: str               # 背景故事
    abilities: list[str]          # 能力列表
    techniques: list[TechniqueId] # 掌握功法
    faction: FactionId            # 所属势力
    relationships: list[CharacterRelation]  # 人物关系
    state_history: list[CharacterState]     # 状态历史
```

### 3.4 Worldview聚合

```python
@dataclass
class Worldview:
    id: WorldviewId
    novel_id: NovelId
    name: str
    
    # 子实体集合
    techniques: list[Technique]   # 功法列表
    factions: list[Faction]       # 势力列表
    locations: list[Location]     # 地点列表
    items: list[Item]             # 物品列表
    
    # 设定规则
    power_system: PowerSystem     # 力量体系
    currency_system: dict         # 货币体系
    timeline: dict                # 时间线设定
```

---

## 四、数据库设计

### 4.1 新增表结构

```sql
-- 项目表
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    novel_id TEXT NOT NULL,
    genre TEXT NOT NULL,
    style_config TEXT,
    target_words INTEGER DEFAULT 8000000,
    status TEXT DEFAULT 'active',
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 模板表
CREATE TABLE templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    genre TEXT NOT NULL,
    description TEXT,
    worldview_framework TEXT,
    character_templates TEXT,
    plot_templates TEXT,
    style_reference TEXT,
    is_builtin INTEGER DEFAULT 0
);

-- 功法表
CREATE TABLE techniques (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT,
    description TEXT,
    effect TEXT,
    requirement TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 势力表
CREATE TABLE factions (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT,
    description TEXT,
    territory TEXT,
    relations TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 地点表
CREATE TABLE locations (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    faction_id TEXT,
    parent_location_id TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 物品表
CREATE TABLE items (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT,
    description TEXT,
    effect TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 人物关系表
CREATE TABLE character_relations (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    related_character_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels(id),
    FOREIGN KEY (character_id) REFERENCES characters(id),
    FOREIGN KEY (related_character_id) REFERENCES characters(id)
);

-- 世界观表
CREATE TABLE worldviews (
    id TEXT PRIMARY KEY,
    novel_id TEXT NOT NULL,
    name TEXT,
    power_system TEXT,
    currency_system TEXT,
    timeline TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels(id)
);
```

### 4.2 扩展现有表

```sql
-- 扩展人物表
ALTER TABLE characters ADD COLUMN appearance TEXT;
ALTER TABLE characters ADD COLUMN personality TEXT;
ALTER TABLE characters ADD COLUMN background TEXT;
ALTER TABLE characters ADD COLUMN abilities TEXT;
ALTER TABLE characters ADD COLUMN faction_id TEXT;

-- 扩展小说表
ALTER TABLE novels ADD COLUMN project_id TEXT;
ALTER TABLE novels ADD COLUMN genre TEXT;
```

---

## 五、API设计

### 5.1 项目管理API

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/projects | 获取项目列表 |
| POST | /api/projects | 创建新项目 |
| GET | /api/projects/{id} | 获取项目详情 |
| PUT | /api/projects/{id} | 更新项目配置 |
| DELETE | /api/projects/{id} | 删除项目 |
| POST | /api/projects/{id}/archive | 归档项目 |

### 5.2 模板API

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/templates | 获取模板列表 |
| GET | /api/templates/{id} | 获取模板详情 |
| POST | /api/templates | 创建自定义模板 |
| POST | /api/projects/{id}/apply-template | 应用模板到项目 |

### 5.3 人设管理API

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/novels/{id}/characters | 获取人物列表 |
| POST | /api/novels/{id}/characters | 创建人物 |
| GET | /api/novels/{id}/characters/{cid} | 获取人物详情 |
| PUT | /api/novels/{id}/characters/{cid} | 更新人物 |
| DELETE | /api/novels/{id}/characters/{cid} | 删除人物 |
| GET | /api/novels/{id}/characters/{cid}/relations | 获取人物关系 |
| POST | /api/novels/{id}/characters/{cid}/relations | 添加人物关系 |
| GET | /api/novels/{id}/characters/{cid}/states | 获取人物状态历史 |

### 5.4 世界观API

| 方法 | 路径 | 描述 |
|-----|------|------|
| GET | /api/novels/{id}/worldview | 获取世界观 |
| PUT | /api/novels/{id}/worldview | 更新世界观 |
| GET | /api/novels/{id}/techniques | 获取功法列表 |
| POST | /api/novels/{id}/techniques | 创建功法 |
| GET | /api/novels/{id}/factions | 获取势力列表 |
| POST | /api/novels/{id}/factions | 创建势力 |
| GET | /api/novels/{id}/locations | 获取地点列表 |
| POST | /api/novels/{id}/locations | 创建地点 |
| POST | /api/novels/{id}/worldview/check | 检查世界观一致性 |

---

## 六、技术栈

| 层级 | 技术 | 说明 |
|-----|------|------|
| 表现层 | FastAPI + Vue3 | 沿用一期技术栈 |
| 应用层 | Python 3.11+ | 沿用 |
| 领域层 | Python + dataclasses | 沿用 |
| 基础设施层 | SQLite + JSON | 沿用，模板使用JSON文件 |
| 测试 | pytest | 沿用 |

---

## 七、下一步行动

1. 用户确认架构设计
2. 进入Atomize阶段进行任务拆解

---

**文档状态**: 待确认  
**确认人**: 用户  
**确认日期**: 待填写
