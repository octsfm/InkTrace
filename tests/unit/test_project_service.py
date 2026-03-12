"""
项目管理服务单元测试

作者：孔利群
"""

import unittest
from unittest.mock import MagicMock

from application.services.project_service import ProjectService
from application.dto.request_dto import CreateNovelRequest


class TestProjectService(unittest.TestCase):
    """测试ProjectService"""

    def setUp(self):
        """测试前置设置"""
        self.mock_repo = MagicMock()
        self.service = ProjectService(self.mock_repo)

    def test_create_novel(self):
        """测试创建小说"""
        self.mock_repo.save = MagicMock()
        
        request = CreateNovelRequest(
            title="修仙从逃出生天开始",
            author="孔利群",
            genre="现代修真",
            target_word_count=800000
        )
        
        response = self.service.create_novel(request)
        
        self.assertIsNotNone(response.id)
        self.assertEqual(response.title, "修仙从逃出生天开始")
        self.assertEqual(response.author, "孔利群")

    def test_get_novel(self):
        """测试获取小说"""
        self.mock_repo.find_by_id = MagicMock(return_value=None)
        
        found = self.service.get_novel("non-existent-id")
        self.assertIsNone(found)

    def test_list_novels(self):
        """测试列出小说"""
        self.mock_repo.find_all = MagicMock(return_value=[])
        
        novels = self.service.list_novels()
        self.assertEqual(len(novels), 0)

    def test_delete_novel(self):
        """测试删除小说"""
        self.mock_repo.delete = MagicMock()
        
        self.service.delete_novel("test-id")
        self.mock_repo.delete.assert_called_once()


if __name__ == '__main__':
    unittest.main()
