"""
导出API路由测试

作者：Qoder
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient

from presentation.api.routers.export import router, _validate_file_path, EXPORTS_DIR
from presentation.api.dependencies import get_export_service
from application.services.export_service import ExportService
from application.dto.response_dto import ExportResponse


class TestExportRouter:
    """导出路由测试"""

    @pytest.fixture
    def mock_export_service(self):
        """创建模拟导出服务"""
        service = Mock(spec=ExportService)
        return service

    @pytest.fixture
    def app(self, mock_export_service):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_export_service] = lambda: mock_export_service
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_export_novel_success(self, client, mock_export_service, tmp_path):
        """测试导出小说 - 成功"""
        mock_response = ExportResponse(
            mode="file",
            scope="full",
            file_path=str(tmp_path / "test.md"),
            format="markdown",
            word_count=1000,
            chapter_count=10
        )
        
        mock_export_service.export_novel.return_value = mock_response

        response = client.post("/export/", json={
            "novel_id": "novel_001",
            "output_path": str(tmp_path / "test.md"),
            "format": "markdown"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "markdown"
        assert data["word_count"] == 1000
        assert data["mode"] == "file"

    def test_export_novel_by_chapter_success(self, client, mock_export_service, tmp_path):
        mock_response = ExportResponse(
            mode="directory",
            scope="by_chapter",
            directory_path="chapter_exports",
            file_count=12,
            format="txt",
            word_count=2000,
            chapter_count=12
        )
        mock_export_service.export_novel.return_value = mock_response
        response = client.post("/export/", json={
            "novel_id": "novel_001",
            "output_path": "chapter_exports",
            "format": "txt",
            "scope": "by_chapter"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "directory"
        assert data["file_count"] == 12

    def test_export_novel_validation_error(self, client, mock_export_service):
        """测试导出小说 - 验证错误"""
        client.app.dependency_overrides[get_export_service] = lambda: mock_export_service
        mock_export_service.export_novel.side_effect = ValueError("?????")

        response = client.post("/export/", json={
            "novel_id": "nonexistent",
            "output_path": "/path/to/file.md",
            "format": "markdown"
        })

        assert response.status_code == 400

    def test_validate_file_path_success(self, tmp_path):
        """测试验证文件路径 - 成功"""
        # 创建测试文件
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        test_file = exports_dir / "test.md"
        test_file.write_text("test content")
        
        with patch('presentation.api.routers.export.EXPORTS_DIR', exports_dir):
            result = _validate_file_path("test.md")
            assert result.name == "test.md"

    def test_validate_file_path_not_exists(self, tmp_path):
        """测试验证文件路径 - 文件不存在"""
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        
        with patch('presentation.api.routers.export.EXPORTS_DIR', exports_dir):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                _validate_file_path("nonexistent.md")
            assert exc_info.value.status_code == 404

    def test_validate_file_path_traversal_attack(self, tmp_path):
        """测试验证文件路径 - 路径遍历攻击"""
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        
        with patch('presentation.api.routers.export.EXPORTS_DIR', exports_dir):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                _validate_file_path("../../../etc/passwd")
            assert exc_info.value.status_code == 403

    def test_download_file_success(self, client, tmp_path):
        """测试下载文件 - 成功"""
        # 创建测试文件
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()
        test_file = exports_dir / "test.md"
        test_file.write_text("# Test Novel\n\nChapter 1 content...")
        
        with patch('presentation.api.routers.export.EXPORTS_DIR', exports_dir):
            response = client.get("/export/download/test.md")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/octet-stream"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
