"""
大模型客户端单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_llm_client.py


import unittest
from unittest.mock import AsyncMock, patch, MagicMock

from infrastructure.llm.base_client import LLMClient
from infrastructure.llm.deepseek_client import DeepSeekClient
from infrastructure.llm.kimi_client import KimiClient
from infrastructure.llm.llm_factory import LLMFactory, LLMConfig


class MockLLMClient(LLMClient):
    """模拟LLM客户端"""

    @property
    def model_name(self) -> str:
        return "mock-model"

    @property
    def max_context_tokens(self) -> int:
        return 4096

    async def generate(self, prompt: str, max_tokens: int = 4000, temperature: float = 0.7) -> str:
        return "模拟生成内容"

    async def chat(self, messages: list, max_tokens: int = 4000, temperature: float = 0.7) -> str:
        return "模拟对话内容"

    async def is_available(self) -> bool:
        return True


class TestDeepSeekClient(unittest.TestCase):
    """测试DeepSeek客户端"""

    def test_create_client(self):
        """测试创建客户端"""
        client = DeepSeekClient(
            api_key="test-key",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat"
        )
        self.assertEqual(client.model_name, "deepseek-chat")
        self.assertEqual(client.max_context_tokens, 64000)

    def test_max_context_tokens(self):
        """测试最大上下文token数"""
# 文件：模块：test_llm_client

        client = DeepSeekClient(api_key="test-key")
        self.assertEqual(client.max_context_tokens, 64000)


class TestKimiClient(unittest.TestCase):
    """测试Kimi客户端"""

    def test_create_client(self):
        """测试创建客户端"""
# 文件：模块：test_llm_client

        client = KimiClient(
            api_key="test-key",
            base_url="https://api.moonshot.cn/v1",
            model="moonshot-v1-8k"
        )
        self.assertEqual(client.model_name, "moonshot-v1-8k")
        self.assertEqual(client.max_context_tokens, 8192)

    def test_max_context_tokens_32k(self):
        """测试32k模型上下文"""
        client = KimiClient(api_key="test-key", model="moonshot-v1-32k")
        self.assertEqual(client.max_context_tokens, 32768)

    def test_max_context_tokens_128k(self):
        """测试128k模型上下文"""
# 文件：模块：test_llm_client

        client = KimiClient(api_key="test-key", model="moonshot-v1-128k")
        self.assertEqual(client.max_context_tokens, 131072)


class TestLLMFactory(unittest.TestCase):
    """测试LLM工厂"""

    def test_create_factory(self):
        """测试创建工厂"""
# 文件：模块：test_llm_client

        config = LLMConfig(
            deepseek_api_key="deepseek-key",
            kimi_api_key="kimi-key"
        )
        factory = LLMFactory(config)
        self.assertIsNotNone(factory)

    def test_primary_client(self):
        """测试获取主模型客户端"""
        config = LLMConfig(deepseek_api_key="test-key")
        factory = LLMFactory(config)
        client = factory.primary_client
        self.assertIsInstance(client, DeepSeekClient)

    def test_backup_client(self):
        """测试获取备用模型客户端"""
# 文件：模块：test_llm_client

        config = LLMConfig(kimi_api_key="test-key")
        factory = LLMFactory(config)
        client = factory.backup_client
        self.assertIsInstance(client, KimiClient)


class TestLLMClientInterface(unittest.TestCase):
    """测试LLM客户端接口"""

    def test_interface_methods(self):
        """测试接口方法"""
# 文件：模块：test_llm_client

        client = MockLLMClient()
        self.assertEqual(client.model_name, "mock-model")
        self.assertEqual(client.max_context_tokens, 4096)


if __name__ == '__main__':
    unittest.main()
