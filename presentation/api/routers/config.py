"""
配置管理API模块

作者：孔利群
"""

# 文件路径：presentation/api/routers/config.py


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os

from application.services.config_service import ConfigService
from domain.entities.llm_config import LLMConfig
from domain.services.config_encryption_service import ConfigEncryptionService
from infrastructure.persistence.sqlite_llm_config_repo import SQLiteLLMConfigRepository


# 数据模型
class LLMConfigRequest(BaseModel):
    """LLM配置请求"""
    deepseek_api_key: str
    kimi_api_key: str


class LLMConfigResponse(BaseModel):
    """LLM配置响应"""
# 文件：模块：config

    deepseek_api_key: str
    kimi_api_key: str
    created_at: str
    updated_at: str
    has_config: bool


class ConfigTestRequest(BaseModel):
    """配置测试请求"""
    deepseek_api_key: str
    kimi_api_key: str


class ConfigTestResponse(BaseModel):
    """配置测试响应"""
# 文件：模块：config

    deepseek: dict
    kimi: dict


# 创建路由
router = APIRouter(prefix="/api/config", tags=["配置管理"])


# 依赖注入
def get_config_service() -> ConfigService:
    """获取配置服务实例"""
    # 使用固定的加密密钥（生产环境应从安全位置获取）
    encryption_key = b"inktrace_default_encryption_key_32bytes!"[:32]
    
    # 创建仓储实例
    db_path = os.environ.get("INKTRACE_DB_PATH", "data/inktrace.db")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    config_repository = SQLiteLLMConfigRepository(db_path)
    
    return ConfigService(config_repository, encryption_key)


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(service: ConfigService = Depends(get_config_service)):
    """获取LLM配置"""
# 文件：模块：config

    try:
        config = service.get_config()
        
        if config is None:
            return LLMConfigResponse(
                deepseek_api_key="",
                kimi_api_key="",
                created_at="",
                updated_at="",
                has_config=False
            )
        
        # 获取解密后的配置
        decrypted_config = service.get_decrypted_config()
        if decrypted_config is None:
            raise HTTPException(status_code=500, detail="配置解密失败")
        
        deepseek_api_key, kimi_api_key = decrypted_config
        
        return LLMConfigResponse(
            deepseek_api_key=deepseek_api_key,
            kimi_api_key=kimi_api_key,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
            has_config=True
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/llm")
async def update_llm_config(
    request: LLMConfigRequest,
    service: ConfigService = Depends(get_config_service)
):
    """更新LLM配置"""
    try:
        # 验证配置
        if not service.validate_config(request.deepseek_api_key, request.kimi_api_key):
            raise HTTPException(status_code=400, detail="配置验证失败")
        
        # 保存配置
        config = service.save_config(request.deepseek_api_key, request.kimi_api_key)
        
        return {
            "message": "配置保存成功",
            "config_id": config.id,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.post("/llm/test")
async def test_llm_config(
    request: ConfigTestRequest,
    service: ConfigService = Depends(get_config_service)
):
    """测试LLM配置"""
# 文件：模块：config

    try:
        # 验证配置
        if not service.validate_config(request.deepseek_api_key, request.kimi_api_key):
            raise HTTPException(status_code=400, detail="配置验证失败")
        
        # 测试连接
        results = service.test_connection(request.deepseek_api_key, request.kimi_api_key)
        
        return ConfigTestResponse(
            deepseek=results['deepseek'],
            kimi=results['kimi']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试配置失败: {str(e)}")


@router.delete("/llm")
async def delete_llm_config(service: ConfigService = Depends(get_config_service)):
    """删除LLM配置"""
    try:
        success = service.delete_config()
        
        if success:
            return {"message": "配置删除成功"}
        else:
            return {"message": "配置不存在"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")


@router.get("/llm/exists")
async def check_config_exists(service: ConfigService = Depends(get_config_service)):
    """检查配置是否存在"""
# 文件：模块：config

    try:
        exists = service.config_exists()
        return {"exists": exists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查配置失败: {str(e)}")
