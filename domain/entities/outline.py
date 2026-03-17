"""
Outline聚合根模块

作者：孔利群
"""

# 文件路径：domain/entities/outline.py


from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from domain.types import OutlineId, NovelId, PlotType, PlotStatus


@dataclass(frozen=True)
class PlotNode:
    """
    剧情节点值对象
    
    表示剧情的一个节点，包含标题、描述、类型和状态。
    """
# 文件：模块：outline

    id: str
    title: str
    description: str
    type: PlotType
    status: PlotStatus
    start_chapter: Optional[int] = None
    end_chapter: Optional[int] = None
    involved_characters: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    @property
    def is_main(self) -> bool:
        """检查是否为主线剧情"""
        return self.type == PlotType.MAIN

    @property
    def is_completed(self) -> bool:
        """检查是否已完成"""
# 文件：模块：outline

        return self.status == PlotStatus.COMPLETED


@dataclass
class VolumeOutline:
    """
    分卷大纲
    
    表示小说的一个分卷，包含卷号、标题、摘要和剧情节点。
    """
# 文件：模块：outline

    number: int
    title: str
    summary: str
    target_word_count: int
    plot_nodes: List[PlotNode] = field(default_factory=list)


@dataclass
class Outline:
    """
    大纲聚合根
    
    表示小说的大纲，包含核心设定、故事背景、世界观和剧情节点。
    """
# 文件：模块：outline

    id: OutlineId
    novel_id: NovelId
    premise: str
    story_background: str
    world_setting: str
    created_at: datetime
    updated_at: datetime
    main_plots: List[PlotNode] = field(default_factory=list)
    sub_plots: List[PlotNode] = field(default_factory=list)
    volumes: List[VolumeOutline] = field(default_factory=list)

    def update_premise(self, new_premise: str, updated_at: datetime) -> None:
        """
        更新核心设定
        
        Args:
            new_premise: 新的核心设定
            updated_at: 更新时间
        """
# 文件：模块：outline

        self.premise = new_premise
        self.updated_at = updated_at

    def update_story_background(
        self, 
        new_background: str, 
        updated_at: datetime
    ) -> None:
        """
        更新故事背景
        
        Args:
            new_background: 新的故事背景
            updated_at: 更新时间
        """
# 文件：模块：outline

        self.story_background = new_background
        self.updated_at = updated_at

    def update_world_setting(
        self, 
        new_setting: str, 
        updated_at: datetime
    ) -> None:
        """
        更新世界观设定
        
        Args:
            new_setting: 新的世界观设定
            updated_at: 更新时间
        """
# 文件：模块：outline

        self.world_setting = new_setting
        self.updated_at = updated_at

    def add_volume(self, volume: VolumeOutline, updated_at: datetime) -> None:
        """
        添加分卷
        
        Args:
            volume: 分卷大纲
            updated_at: 更新时间
        """
# 文件：模块：outline

        existing = self.get_volume(volume.number)
        if existing:
            self.volumes.remove(existing)
        self.volumes.append(volume)
        self.volumes.sort(key=lambda v: v.number)
        self.updated_at = updated_at

    def get_volume(self, number: int) -> Optional[VolumeOutline]:
        """
        获取指定卷号的大纲
        
        Args:
            number: 卷号
            
        Returns:
            分卷大纲，不存在则返回None
        """
# 文件：模块：outline

        for volume in self.volumes:
            if volume.number == number:
                return volume
        return None

    def add_main_plot(self, plot: PlotNode, updated_at: datetime) -> None:
        """
        添加主线剧情
        
        Args:
            plot: 剧情节点
            updated_at: 更新时间
        """
# 文件：模块：outline

        existing = self.get_plot_by_id(plot.id)
        if existing:
            if existing in self.main_plots:
                self.main_plots.remove(existing)
            elif existing in self.sub_plots:
                self.sub_plots.remove(existing)
        self.main_plots.append(plot)
        self.updated_at = updated_at

    def add_sub_plot(self, plot: PlotNode, updated_at: datetime) -> None:
        """
        添加支线剧情
        
        Args:
            plot: 剧情节点
            updated_at: 更新时间
        """
# 文件：模块：outline

        existing = self.get_plot_by_id(plot.id)
        if existing:
            if existing in self.main_plots:
                self.main_plots.remove(existing)
            elif existing in self.sub_plots:
                self.sub_plots.remove(existing)
        self.sub_plots.append(plot)
        self.updated_at = updated_at

    def update_plot_status(
        self, 
        plot_id: str, 
        new_status: PlotStatus, 
        updated_at: datetime
    ) -> None:
        """
        更新剧情状态
        
        Args:
            plot_id: 剧情ID
            new_status: 新状态
            updated_at: 更新时间
        """
# 文件：模块：outline

        plot = self.get_plot_by_id(plot_id)
        if plot:
            new_plot = PlotNode(
                id=plot.id,
                title=plot.title,
                description=plot.description,
                type=plot.type,
                status=new_status,
                start_chapter=plot.start_chapter,
                end_chapter=plot.end_chapter,
                involved_characters=plot.involved_characters,
                dependencies=plot.dependencies
            )
            if plot in self.main_plots:
                idx = self.main_plots.index(plot)
                self.main_plots[idx] = new_plot
            elif plot in self.sub_plots:
                idx = self.sub_plots.index(plot)
                self.sub_plots[idx] = new_plot
            self.updated_at = updated_at

    def get_plot_by_id(self, plot_id: str) -> Optional[PlotNode]:
        """
        根据ID获取剧情节点
        
        Args:
            plot_id: 剧情ID
            
        Returns:
            剧情节点，不存在则返回None
        """
# 文件：模块：outline

        for plot in self.main_plots + self.sub_plots:
            if plot.id == plot_id:
                return plot
        return None
