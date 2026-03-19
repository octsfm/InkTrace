from __future__ import annotations

import logging
from typing import Any, Dict, Optional


class ModelRouter:
    def __init__(self, primary_client=None, backup_client=None):
        self.primary_client = primary_client
        self.backup_client = backup_client
        self.logger = logging.getLogger(__name__)

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1600,
        temperature: float = 0.4
    ) -> Dict[str, Any]:
        self.logger.info(f"[ModelRouter] 开始调用大模型, max_tokens={max_tokens}, temperature={temperature}")
        
        if self.primary_client is not None:
            try:
                self.logger.info(f"[ModelRouter] 尝试使用主模型: {self.primary_client.model_name}")
                text = await self.primary_client.generate(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                self.logger.info(f"[ModelRouter] 主模型调用成功, 返回文本长度: {len(text)}")
                return {"ok": True, "text": text, "route": "primary"}
            except Exception as error:
                primary_error = str(error)
                self.logger.warning(f"[ModelRouter] 主模型调用失败: {primary_error}")
        else:
            primary_error = "primary_unavailable"
            self.logger.warning("[ModelRouter] 主模型不可用")

        if self.backup_client is not None:
            try:
                self.logger.info(f"[ModelRouter] 尝试使用备用模型: {self.backup_client.model_name}")
                text = await self.backup_client.generate(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                self.logger.info(f"[ModelRouter] 备用模型调用成功, 返回文本长度: {len(text)}")
                return {"ok": True, "text": text, "route": "backup"}
            except Exception as error:
                self.logger.error(f"[ModelRouter] 备用模型调用失败: {str(error)}")
                return {"ok": False, "route": "terminate", "error": str(error), "primary_error": primary_error}

        self.logger.error("[ModelRouter] 所有模型都不可用")
        return {"ok": False, "route": "terminate", "error": primary_error}
