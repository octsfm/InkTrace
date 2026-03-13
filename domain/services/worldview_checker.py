"""
世界观一致性检查服务

作者：孔利群
"""

from dataclasses import dataclass
from typing import List, Optional

from domain.entities.worldview import Worldview
from domain.entities.technique import Technique, TechniqueLevel
from domain.entities.faction import Faction, FactionRelation
from domain.entities.character import Character


@dataclass
class ConsistencyIssue:
    """一致性问题"""
    issue_type: str
    severity: str
    description: str
    location: str
    suggestion: str


class WorldviewChecker:
    """世界观一致性检查服务"""
    
    def check_worldview(self, worldview: Worldview) -> List[ConsistencyIssue]:
        """检查世界观一致性"""
        issues = []
        
        issues.extend(self._check_technique_levels(worldview))
        issues.extend(self._check_faction_relations(worldview))
        issues.extend(self._check_location_hierarchy(worldview))
        
        return issues
    
    def check_character_consistency(
        self, 
        character: Character, 
        worldview: Worldview
    ) -> List[ConsistencyIssue]:
        """检查人物与世界观的 consistency"""
        issues = []
        
        issues.extend(self._check_character_techniques(character, worldview))
        issues.extend(self._check_character_faction(character, worldview))
        
        return issues
    
    def _check_technique_levels(self, worldview: Worldview) -> List[ConsistencyIssue]:
        """检查功法等级一致性"""
        issues = []
        
        if not worldview.power_system:
            return issues
        
        valid_levels = worldview.power_system.levels
        
        for technique in worldview.techniques:
            if technique.level and technique.level.name not in valid_levels:
                issues.append(ConsistencyIssue(
                    issue_type="technique_level",
                    severity="warning",
                    description=f"功法【{technique.name}】的等级【{technique.level.name}】不在力量体系等级中",
                    location=f"功法: {technique.name}",
                    suggestion=f"请将功法等级修改为: {', '.join(valid_levels)}"
                ))
        
        return issues
    
    def _check_faction_relations(self, worldview: Worldview) -> List[ConsistencyIssue]:
        """检查势力关系一致性"""
        issues = []
        
        faction_ids = {str(f.id) for f in worldview.factions}
        
        for faction in worldview.factions:
            for relation in faction.relations:
                if str(relation.target_id) not in faction_ids:
                    issues.append(ConsistencyIssue(
                        issue_type="faction_relation",
                        severity="error",
                        description=f"势力【{faction.name}】的关系目标不存在",
                        location=f"势力: {faction.name}",
                        suggestion="请检查势力关系设置，确保目标势力存在"
                    ))
        
        return issues
    
    def _check_location_hierarchy(self, worldview: Worldview) -> List[ConsistencyIssue]:
        """检查地点层级一致性"""
        issues = []
        
        location_ids = {str(l.id) for l in worldview.locations}
        
        for location in worldview.locations:
            if location.parent_id and str(location.parent_id) not in location_ids:
                issues.append(ConsistencyIssue(
                    issue_type="location_hierarchy",
                    severity="warning",
                    description=f"地点【{location.name}】的父级地点不存在",
                    location=f"地点: {location.name}",
                    suggestion="请检查地点层级设置"
                ))
        
        return issues
    
    def _check_character_techniques(
        self, 
        character: Character, 
        worldview: Worldview
    ) -> List[ConsistencyIssue]:
        """检查人物功法一致性"""
        issues = []
        
        technique_ids = {str(t.id) for t in worldview.techniques}
        
        for tech_id in character.techniques:
            if str(tech_id) not in technique_ids:
                issues.append(ConsistencyIssue(
                    issue_type="character_technique",
                    severity="warning",
                    description=f"人物【{character.name}】的功法不存在于世界观中",
                    location=f"人物: {character.name}",
                    suggestion="请检查人物功法设置"
                ))
        
        return issues
    
    def _check_character_faction(
        self, 
        character: Character, 
        worldview: Worldview
    ) -> List[ConsistencyIssue]:
        """检查人物势力一致性"""
        issues = []
        
        if character.faction_id:
            faction_ids = {str(f.id) for f in worldview.factions}
            if str(character.faction_id) not in faction_ids:
                issues.append(ConsistencyIssue(
                    issue_type="character_faction",
                    severity="warning",
                    description=f"人物【{character.name}】的所属势力不存在于世界观中",
                    location=f"人物: {character.name}",
                    suggestion="请检查人物势力设置"
                ))
        
        return issues
