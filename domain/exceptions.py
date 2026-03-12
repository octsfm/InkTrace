"""
领域层异常定义

作者：孔利群
"""


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
