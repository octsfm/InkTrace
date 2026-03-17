"""
项目管理服务单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_project_service.py


import unittest
from unittest.mock import MagicMock

from application.services.project_service import ProjectService
from domain.types import GenreType


class TestProjectService(unittest.TestCase):
    """测试ProjectService"""

    def setUp(self):
        """测试前置设置"""
# 文件：模块：test_project_service

        self.mock_project_repo = MagicMock()
        self.mock_novel_repo = MagicMock()
        self.service = ProjectService(self.mock_project_repo, self.mock_novel_repo)

    def test_create_project(self):
        """测试创建项目"""
        self.mock_novel_repo.save = MagicMock()
        self.mock_project_repo.save = MagicMock()
        
        project = self.service.create_project(
            name="测试项目",
            genre=GenreType.XUANHUAN,
            target_words=8000000
        )
        
        self.assertIsNotNone(project)
        self.assertEqual(project.name, "测试项目")
        self.assertEqual(project.config.genre, GenreType.XUANHUAN)
        self.mock_novel_repo.save.assert_called_once()
        self.mock_project_repo.save.assert_called_once()

    def test_get_project(self):
        """测试获取项目"""
# 文件：模块：test_project_service

        from domain.entities.project import Project, ProjectConfig
        from domain.types import ProjectId, NovelId
        
        mock_project = Project(
            id=ProjectId("proj_001"),
            name="测试项目",
            novel_id=NovelId("novel_001"),
            config=ProjectConfig()
        )
        self.mock_project_repo.find_by_id = MagicMock(return_value=mock_project)
        
        found = self.service.get_project(ProjectId("proj_001"))
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "测试项目")

    def test_get_project_not_found(self):
        """测试获取不存在的项目"""
        self.mock_project_repo.find_by_id = MagicMock(return_value=None)
        
        from domain.types import ProjectId
        found = self.service.get_project(ProjectId("non-existent-id"))
        self.assertIsNone(found)

    def test_list_projects(self):
        """测试列出项目"""
# 文件：模块：test_project_service

        self.mock_project_repo.find_all = MagicMock(return_value=[])
        
        projects = self.service.list_projects()
        self.assertEqual(len(projects), 0)

    def test_list_active_projects(self):
        """测试列出活跃项目"""
        from domain.types import ProjectStatus
        self.mock_project_repo.find_all = MagicMock(return_value=[])
        
        projects = self.service.list_active_projects()
        self.mock_project_repo.find_all.assert_called_with(ProjectStatus.ACTIVE)

    def test_delete_project(self):
        """测试删除项目"""
# 文件：模块：test_project_service

        from domain.entities.project import Project, ProjectConfig
        from domain.types import ProjectId, NovelId
        
        mock_project = Project(
            id=ProjectId("proj_001"),
            name="测试项目",
            novel_id=NovelId("novel_001"),
            config=ProjectConfig()
        )
        self.mock_project_repo.find_by_id = MagicMock(return_value=mock_project)
        self.mock_project_repo.delete = MagicMock()
        self.mock_novel_repo.delete = MagicMock()
        
        self.service.delete_project(ProjectId("proj_001"))
        self.mock_project_repo.delete.assert_called_once()
        self.mock_novel_repo.delete.assert_called_once()

    def test_archive_project(self):
        """测试归档项目"""
        from domain.entities.project import Project, ProjectConfig
        from domain.types import ProjectId, NovelId, ProjectStatus
        
        mock_project = Project(
            id=ProjectId("proj_001"),
            name="测试项目",
            novel_id=NovelId("novel_001"),
            config=ProjectConfig()
        )
        self.mock_project_repo.find_by_id = MagicMock(return_value=mock_project)
        self.mock_project_repo.save = MagicMock()
        
        archived = self.service.archive_project(ProjectId("proj_001"))
        self.assertEqual(archived.status, ProjectStatus.ARCHIVED)


if __name__ == '__main__':
    unittest.main()
