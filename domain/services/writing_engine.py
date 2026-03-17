"""
写作引擎领域服务模块

作者：孔利群
"""

# 文件路径：domain/services/writing_engine.py


from typing import List, Dict, Optional
from dataclasses import dataclass

from domain.entities.outline import Outline, PlotNode
from domain.value_objects.style_profile import StyleProfile
from domain.value_objects.writing_config import WritingConfig
from domain.types import PlotType, PlotStatus


@dataclass
class WritingContext:
    """写作上下文"""
    novel_title: str
    outline_summary: str
    previous_chapters: List[str]
    plot_direction: str
    characters_involved: List[str] = None
    current_chapter_number: int = 0


class WritingEngine:
    """
# 文件：模块：writing_engine

    写作引擎领域服务
    
    负责章节生成、剧情规划、文风应用。
    """

    def __init__(self, llm_client, style_profile: StyleProfile):
        """
# 文件：模块：writing_engine

        初始化写作引擎
        
        Args:
            llm_client: 大模型客户端
            style_profile: 文风特征
        """
        self.llm_client = llm_client
        self.style_profile = style_profile

    def generate_chapter(
        self, 
        context: WritingContext, 
        config: WritingConfig
    ) -> str:
        """
# 文件：模块：writing_engine

        生成章节内容
        
        Args:
            context: 写作上下文
            config: 写作配置
            
        Returns:
            生成的章节内容
        """
        prompt = self._build_generation_prompt(context, config)
        
        if hasattr(self.llm_client, 'generate'):
            import asyncio
            content = asyncio.run(self.llm_client.generate(prompt))
        else:
            content = self.llm_client.generate(prompt)
        
        if config.enable_style_mimicry:
            content = self.apply_style(content, self.style_profile)
        
        return content

    def plan_plot(
        self, 
        outline: Outline, 
        chapter_count: int,
        direction: str
    ) -> List[PlotNode]:
        """
# 文件：模块：writing_engine

        规划剧情走向
        
        Args:
            outline: 大纲
            chapter_count: 章节数量
            direction: 剧情方向
            
        Returns:
            剧情节点列表
        """
        plot_nodes = []
        
        for i in range(chapter_count):
            node = PlotNode(
                id=f"plot-{i:03d}",
                title=f"剧情节点{i+1}",
                description=f"根据方向'{direction}'生成的剧情节点",
                type=PlotType.MAIN if i == 0 else PlotType.SUB,
                status=PlotStatus.PLANNED
            )
            plot_nodes.append(node)
        
        return plot_nodes

    def apply_style(
        self, 
        content: str, 
        style_profile: StyleProfile
    ) -> str:
        """
# 文件：模块：writing_engine

        应用文风特征
        
        Args:
            content: 原始内容
            style_profile: 文风特征
            
        Returns:
            应用文风后的内容
        """
        styled_content = content
        
        if style_profile.sample_sentences:
            pass
        
        return styled_content

    def _build_generation_prompt(
        self, 
        context: WritingContext, 
        config: WritingConfig
    ) -> str:
        """
# 文件：模块：writing_engine

        构建生成提示词
        
        Args:
            context: 写作上下文
            config: 写作配置
            
        Returns:
            提示词
        """
        prompt_parts = [
            f"# 小说信息",
            f"小说标题：{context.novel_title}",
            f"",
            f"# 大纲摘要",
            context.outline_summary,
            f"",
            f"# 剧情方向",
            context.plot_direction,
            f"",
            f"# 前文提要",
        ]
        
        if context.previous_chapters:
            for i, chapter in enumerate(context.previous_chapters[-3:], 1):
                prompt_parts.append(f"第{len(context.previous_chapters) - 3 + i}章摘要：{chapter[:200]}...")
        
        prompt_parts.extend([
            f"",
            f"# 写作要求",
            f"请续写一章，字数约{config.target_word_count}字。",
            f"保持文风一致，延续剧情发展。",
            f"",
            f"# 章节内容",
            f"请直接输出章节内容，不要添加任何说明文字："
        ])
        
        return "\n".join(prompt_parts)
