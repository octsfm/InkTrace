"""
项目实体单元测试

作者：孔利群
"""

import unittest
from datetime import datetime

from domain.entities.project import Project, ProjectConfig
from domain.types import ProjectId, NovelId, ProjectStatus, GenreType


class TestProjectConfig(unittest.TestCase):
    """项目配置值对象测试"""
    
    def test_create_default_config(self):
        """测试创建默认配置"""
        config = ProjectConfig()
        self.assertEqual(config.genre, GenreType.XUANHUAN)
        self.assertEqual(config.target_words, 8000000)
        self.assertEqual(config.chapter_words, 2100)
        self.assertEqual(config.style_intensity, 0.8)
        self.assertTrue(config.check_consistency)
    
    def test_create_custom_config(self):
        """测试创建自定义配置"""
        config = ProjectConfig(
            genre=GenreType.XIANXIA,
            target_words=5000000,
            chapter_words=3000,
            style_intensity=0.9,
            check_consistency=False
        )
        self.assertEqual(config.genre, GenreType.XIANXIA)
        self.assertEqual(config.target_words, 5000000)
        self.assertEqual(config.chapter_words, 3000)
        self.assertEqual(config.style_intensity, 0.9)
        self.assertFalse(config.check_consistency)
    
    def test_config_to_dict(self):
        """测试配置转字典"""
        config = ProjectConfig(genre=GenreType.DUSHI, target_words=3000000)
        data = config.to_dict()
        self.assertEqual(data["genre"], "dushi")
        self.assertEqual(data["target_words"], 3000000)
    
    def test_config_from_dict(self):
        """测试从字典创建配置"""
        data = {"genre": "kehuan", "target_words": 2000000, "chapter_words": 2500}
        config = ProjectConfig.from_dict(data)
        self.assertEqual(config.genre, GenreType.KEHUAN)
        self.assertEqual(config.target_words, 2000000)
        self.assertEqual(config.chapter_words, 2500)


class TestProject(unittest.TestCase):
    """项目实体测试"""
    
    def setUp(self):
        """测试前置"""
        self.project_id = ProjectId("proj_001")
        self.novel_id = NovelId("novel_001")
        self.project = Project(
            id=self.project_id,
            name="测试项目",
            novel_id=self.novel_id
        )
    
    def test_create_project(self):
        """测试创建项目"""
        self.assertEqual(str(self.project.id), "proj_001")
        self.assertEqual(self.project.name, "测试项目")
        self.assertEqual(str(self.project.novel_id), "novel_001")
        self.assertEqual(self.project.status, ProjectStatus.ACTIVE)
    
    def test_is_active(self):
        """测试活跃状态检查"""
        self.assertTrue(self.project.is_active())
        self.assertFalse(self.project.is_archived())
    
    def test_archive_project(self):
        """测试归档项目"""
        self.project.archive()
        self.assertEqual(self.project.status, ProjectStatus.ARCHIVED)
        self.assertTrue(self.project.is_archived())
        self.assertFalse(self.project.is_active())
    
    def test_archive_already_archived(self):
        """测试归档已归档项目"""
        self.project.archive()
        with self.assertRaises(ValueError):
            self.project.archive()
    
    def test_activate_project(self):
        """测试激活项目"""
        self.project.archive()
        self.project.activate()
        self.assertEqual(self.project.status, ProjectStatus.ACTIVE)
        self.assertTrue(self.project.is_active())
    
    def test_activate_already_active(self):
        """测试激活已激活项目"""
        with self.assertRaises(ValueError):
            self.project.activate()
    
    def test_update_config(self):
        """测试更新配置"""
        new_config = ProjectConfig(genre=GenreType.LISHI, target_words=4000000)
        self.project.update_config(new_config)
        self.assertEqual(self.project.config.genre, GenreType.LISHI)
        self.assertEqual(self.project.config.target_words, 4000000)
    
    def test_update_name(self):
        """测试更新名称"""
        self.project.update_name("新项目名")
        self.assertEqual(self.project.name, "新项目名")
    
    def test_update_empty_name(self):
        """测试更新空名称"""
        with self.assertRaises(ValueError):
            self.project.update_name("")
        with self.assertRaises(ValueError):
            self.project.update_name("   ")
    
    def test_project_to_dict(self):
        """测试项目转字典"""
        data = self.project.to_dict()
        self.assertEqual(data["id"], "proj_001")
        self.assertEqual(data["name"], "测试项目")
        self.assertEqual(data["novel_id"], "novel_001")
        self.assertEqual(data["status"], "active")
    
    def test_project_from_dict(self):
        """测试从字典创建项目"""
        data = {
            "id": "proj_002",
            "name": "字典项目",
            "novel_id": "novel_002",
            "config": {"genre": "xianxia", "target_words": 6000000},
            "status": "archived",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-02T00:00:00"
        }
        project = Project.from_dict(data)
        self.assertEqual(str(project.id), "proj_002")
        self.assertEqual(project.name, "字典项目")
        self.assertEqual(project.status, ProjectStatus.ARCHIVED)
        self.assertEqual(project.config.genre, GenreType.XIANXIA)


if __name__ == "__main__":
    unittest.main()
