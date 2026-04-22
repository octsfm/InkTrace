"""
领域层异常定义

作者：孔利群
"""

# 文件路径：domain/exceptions.py



class DomainException(Exception):
    """领域异常基类"""
    pass


class EntityNotFoundError(DomainException):
    """实体未找到异常"""
    
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type}未找到: {entity_id}")


class InvalidEntityStateError(DomainException):
    """无效实体状态异常"""
    
    def __init__(self, entity_type: str, current_state: str, expected_state: str):
        self.entity_type = entity_type
        self.current_state = current_state
        self.expected_state = expected_state
        super().__init__(
            f"{entity_type}状态无效: 当前状态为{current_state}, 期望状态为{expected_state}"
        )


class InvalidOperationError(DomainException):
    """无效操作异常"""
    
    def __init__(self, message: str):
        super().__init__(message)


class ValidationError(DomainException):
    """验证异常"""
    
    def __init__(self, message: str):
        super().__init__(message)


class LLMClientError(DomainException):
    """LLM客户端基础异常"""
# 文件：模块：exceptions

    pass


class APIKeyError(LLMClientError):
    """API密钥错误"""
    
    def __init__(self, provider: str, message: str = "API密钥无效或未配置"):
        self.provider = provider
        super().__init__(f"{provider} API密钥错误: {message}")


class RateLimitError(LLMClientError):
    """限流错误"""
    
    def __init__(self, provider: str, retry_after: int = None):
        self.provider = provider
        self.retry_after = retry_after
        message = f"{provider} API限流"
        if retry_after:
            message += f", 请在{retry_after}秒后重试"
        super().__init__(message)


class NetworkError(LLMClientError):
    """网络错误"""
    
    def __init__(self, provider: str, original_error: str = None):
        self.provider = provider
        self.original_error = original_error
        message = f"{provider} 网络连接错误"
        if original_error:
            message += f": {original_error}"
        super().__init__(message)


class TokenLimitError(LLMClientError):
    """Token限制错误"""
    
    def __init__(
        self,
        provider: str,
        current_tokens: int | str | None = None,
        max_tokens: int | None = None,
        *,
        stage: str = "",
        model_name: str = "",
        request_id: str = "",
        message: str = "",
    ):
        self.provider = provider
        self.stage = str(stage or "").strip()
        self.model_name = str(model_name or "").strip()
        self.request_id = str(request_id or "").strip()

        # 向后兼容旧调用：TokenLimitError("Kimi", "请求超过上下文限制")
        inferred_message = ""
        normalized_current_tokens: int | None = None
        normalized_max_tokens: int | None = None
        if isinstance(current_tokens, str) and max_tokens is None:
            inferred_message = current_tokens.strip()
        else:
            if current_tokens is not None:
                try:
                    normalized_current_tokens = int(current_tokens)
                except Exception:
                    normalized_current_tokens = None
            if max_tokens is not None:
                try:
                    normalized_max_tokens = int(max_tokens)
                except Exception:
                    normalized_max_tokens = None

        self.current_tokens = normalized_current_tokens
        self.max_tokens = normalized_max_tokens

        final_message = str(message or "").strip() or inferred_message
        if not final_message:
            details = []
            if self.current_tokens is not None:
                details.append(f"current_tokens={self.current_tokens}")
            if self.max_tokens is not None:
                details.append(f"max_tokens={self.max_tokens}")
            if self.stage:
                details.append(f"stage={self.stage}")
            if self.model_name:
                details.append(f"model={self.model_name}")
            if self.request_id:
                details.append(f"request_id={self.request_id}")
            detail_text = ", ".join(details)
            final_message = f"{provider} Token超限"
            if detail_text:
                final_message += f": {detail_text}"
        super().__init__(final_message)
