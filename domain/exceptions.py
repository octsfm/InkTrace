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
    
    def __init__(self, provider: str, current_tokens: int, max_tokens: int):
        self.provider = provider
        self.current_tokens = current_tokens
        self.max_tokens = max_tokens
        super().__init__(
            f"{provider} Token超限: 当前{current_tokens}tokens, 最大{max_tokens}tokens"
        )
