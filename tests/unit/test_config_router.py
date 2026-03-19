"""
配置管理API路由测试

作者：Qoder
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient

from presentation.api.routers.config import router, get_config_service
from application.services.config_service import ConfigService


class TestConfigRouter:
    """配置管理路由测试"""

    @pytest.fixture
    def mock_config_service(self):
        """创建模拟配置服务"""
        service = Mock(spec=ConfigService)
        return service

    @pytest.fixture
    def app(self, mock_config_service):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_config_service] = lambda: mock_config_service
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_get_llm_config_success(self, client, mock_config_service):
        """测试获取LLM配置 - 成功"""
        mock_config = Mock()
        mock_config.created_at = datetime.now()
        mock_config.updated_at = datetime.now()
        
        mock_config_service.get_config.return_value = mock_config
        mock_config_service.get_decrypted_config.return_value = ("deepseek_key", "kimi_key")
        
        response = client.get("/api/config/llm")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deepseek_api_key"] == "deepseek_key"
        assert data["kimi_api_key"] == "kimi_key"
        assert data["has_config"] is True

    def test_get_llm_config_not_found(self, client, mock_config_service):
        """测试获取LLM配置 - 不存在"""
        mock_config_service.get_config.return_value = None
        
        response = client.get("/api/config/llm")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deepseek_api_key"] == ""
        assert data["kimi_api_key"] == ""
        assert data["has_config"] is False

    def test_get_llm_config_decrypt_failed(self, client, mock_config_service):
        """测试获取LLM配置 - 解密失败"""
        mock_config = Mock()
        mock_config.created_at = datetime.now()
        mock_config.updated_at = datetime.now()
        
        mock_config_service.get_config.return_value = mock_config
        mock_config_service.get_decrypted_config.return_value = None
        
        response = client.get("/api/config/llm")
        
        assert response.status_code == 500

    def test_update_llm_config_success(self, client, mock_config_service):
        """测试更新LLM配置 - 成功"""
        mock_config = Mock()
        mock_config.id = 1
        mock_config.created_at = datetime.now()
        mock_config.updated_at = datetime.now()
        
        mock_config_service.validate_config.return_value = True
        mock_config_service.save_config.return_value = mock_config
        
        response = client.post("/api/config/llm", json={
            "deepseek_api_key": "test_deepseek",
            "kimi_api_key": "test_kimi"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "配置保存成功"

    def test_update_llm_config_validation_failed(self, client, mock_config_service):
        """测试更新LLM配置 - 验证失败"""
        mock_config_service.validate_config.return_value = False
        
        response = client.post("/api/config/llm", json={
            "deepseek_api_key": "",
            "kimi_api_key": ""
        })
        
        assert response.status_code == 400

    def test_test_llm_config_success(self, client, mock_config_service):
        """测试测试LLM配置 - 成功"""
        mock_config_service.validate_config.return_value = True
        mock_config_service.test_connection.return_value = {
            "deepseek": {"success": True},
            "kimi": {"success": True}
        }
        
        response = client.post("/api/config/llm/test", json={
            "deepseek_api_key": "test_deepseek",
            "kimi_api_key": "test_kimi"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["deepseek"]["success"] is True
        assert data["kimi"]["success"] is True

    def test_delete_llm_config_success(self, client, mock_config_service):
        """测试删除LLM配置 - 成功"""
        mock_config_service.delete_config.return_value = True
        
        response = client.delete("/api/config/llm")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "配置删除成功"

    def test_delete_llm_config_not_exists(self, client, mock_config_service):
        """测试删除LLM配置 - 不存在"""
        mock_config_service.delete_config.return_value = False
        
        response = client.delete("/api/config/llm")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "配置不存在"

    def test_check_config_exists_true(self, client, mock_config_service):
        """测试检查配置存在"""
        mock_config_service.config_exists.return_value = True
        
        response = client.get("/api/config/llm/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True

    def test_check_config_exists_false(self, client, mock_config_service):
        """测试检查配置不存在"""
        mock_config_service.config_exists.return_value = False
        
        response = client.get("/api/config/llm/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
