"""
LLM客户端单元测试模块

作者：孔利群
"""

# 文件路径：tests/unit/test_llm_client_improved.py


import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from domain.exceptions import (
    LLMClientError,
    APIKeyError,
    RateLimitError,
    NetworkError,
    TokenLimitError
)
from infrastructure.llm.deepseek_client import DeepSeekClient
from infrastructure.llm.kimi_client import KimiClient


class TestDeepSeekClient(unittest.TestCase):
    """DeepSeek客户端测试"""

    def setUp(self):
        """测试前准备"""
# 文件：模块：test_llm_client_improved

        self.api_key = "test_api_key_1234567890"
        self.client = DeepSeekClient(api_key=self.api_key)

    def tearDown(self):
        """测试后清理"""
        # 清理资源
        pass

    def test_client_initialization(self):
        """测试客户端初始化"""
# 文件：模块：test_llm_client_improved

        self.assertEqual(self.client.api_key, self.api_key)
        self.assertEqual(self.client.model_name, "deepseek-chat")
        self.assertEqual(self.client.max_context_tokens, 64000)
        self.assertIsNotNone(self.client._client)

    def test_truncate_input(self):
        """测试DeepSeek兼容截断逻辑"""
        short_text = "短文本"
        result = self.client._truncate_input(short_text)
        self.assertEqual(result, short_text)

    @patch('httpx.AsyncClient.post')
    async def test_generate_success(self, mock_post):
        """测试生成成功"""
# 文件：模块：test_llm_client_improved

        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "测试回复"}}]
        }
        mock_post.return_value = mock_response

        result = await self.client.generate("测试提示")
        self.assertEqual(result, "测试回复")

    @patch('httpx.AsyncClient.post')
    async def test_generate_with_system_prompt(self, mock_post):
        """测试带系统提示的生成"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "测试回复"}}]
        }
        mock_post.return_value = mock_response

        result = await self.client.generate(
            "测试提示", 
            system_prompt="你是小说编辑"
        )
        self.assertEqual(result, "测试回复")

    @patch('httpx.AsyncClient.post')
    async def test_api_key_error(self, mock_post):
        """测试API密钥错误"""
# 文件：模块：test_llm_client_improved

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with self.assertRaises(APIKeyError):
            await self.client.generate("测试提示")

    @patch('httpx.AsyncClient.post')
    async def test_rate_limit_error(self, mock_post):
        """测试限流错误"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "60"}
        mock_post.return_value = mock_response

        with self.assertRaises(RateLimitError):
            await self.client.generate("测试提示")

    @patch('httpx.AsyncClient.post')
    async def test_network_error(self, mock_post):
        """测试网络错误"""
# 文件：模块：test_llm_client_improved

        mock_post.side_effect = httpx.NetworkError("网络错误")

        with self.assertRaises(NetworkError):
            await self.client.generate("测试提示")

    async def test_close(self):
        """测试资源清理"""
        await self.client.close()


class TestKimiClient(unittest.TestCase):
    """Kimi客户端测试"""

    def setUp(self):
        """测试前准备"""
        self.api_key = "test_api_key_1234567890"
        self.client = KimiClient(api_key=self.api_key)

    def test_client_initialization(self):
        """测试客户端初始化"""
# 文件：模块：test_llm_client_improved

        self.assertEqual(self.client.api_key, self.api_key)
        self.assertEqual(self.client.model_name, "moonshot-v1-8k")
        self.assertEqual(self.client.max_context_tokens, 8192)

    def test_max_context_tokens_different_models(self):
        """测试不同模型的最大上下文"""
        client_8k = KimiClient(api_key="test", model="moonshot-v1-8k")
        self.assertEqual(client_8k.max_context_tokens, 8192)

        client_32k = KimiClient(api_key="test", model="moonshot-v1-32k")
        self.assertEqual(client_32k.max_context_tokens, 32768)

        client_128k = KimiClient(api_key="test", model="moonshot-v1-128k")
        self.assertEqual(client_128k.max_context_tokens, 131072)

    @patch('httpx.AsyncClient.post')
    async def test_generate_success(self, mock_post):
        """测试生成成功"""
# 文件：模块：test_llm_client_improved

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "测试回复"}}]
        }
        mock_post.return_value = mock_response

        result = await self.client.generate("测试提示")
        self.assertEqual(result, "测试回复")

    @patch('httpx.AsyncClient.post')
    async def test_generate_with_system_prompt(self, mock_post):
        """测试带系统提示的生成"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "测试回复"}}]
        }
        mock_post.return_value = mock_response

        result = await self.client.generate(
            "测试提示", 
            system_prompt="你是小说编辑"
        )
        self.assertEqual(result, "测试回复")


class TestExceptions(unittest.TestCase):
    """异常类测试"""

    def test_llm_client_error(self):
        """测试LLM客户端基础异常"""
        error = LLMClientError("测试错误")
        self.assertEqual(str(error), "测试错误")

    def test_api_key_error(self):
        """测试API密钥错误"""
# 文件：模块：test_llm_client_improved

        error = APIKeyError("DeepSeek", "密钥无效")
        self.assertIn("DeepSeek", str(error))
        self.assertIn("密钥无效", str(error))

    def test_rate_limit_error(self):
        """测试限流错误"""
        error = RateLimitError("DeepSeek", retry_after=60)
        self.assertIn("DeepSeek", str(error))
        self.assertIn("60", str(error))

    def test_network_error(self):
        """测试网络错误"""
# 文件：模块：test_llm_client_improved

        error = NetworkError("Kimi", "连接超时")
        self.assertIn("Kimi", str(error))
        self.assertIn("连接超时", str(error))

    def test_token_limit_error(self):
        """测试Token限制错误"""
        error = TokenLimitError(
            "DeepSeek",
            100000,
            64000,
            stage="global_analysis",
            model_name="deepseek-chat",
            request_id="req-1",
        )
        self.assertIn("DeepSeek", str(error))
        self.assertIn("100000", str(error))
        self.assertIn("64000", str(error))
        self.assertEqual(error.stage, "global_analysis")
        self.assertEqual(error.model_name, "deepseek-chat")
        self.assertEqual(error.request_id, "req-1")


if __name__ == '__main__':
    unittest.main()
