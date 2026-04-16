"""
配置管理模块

使用 Pydantic Settings 进行类型安全的配置管理
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置

    所有配置项都可以通过环境变量或 .env 文件设置
    环境变量名使用大写，如 DASHSCOPE_API_KEY
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==================== 应用配置 ====================

    app_name: str = Field(default="fitness-agent", description="应用名称")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", description="运行环境"
    )
    app_debug: bool = Field(default=False, description="调试模式")
    app_host: str = Field(default="0.0.0.0", description="监听地址")
    app_port: int = Field(default=8000, ge=1, le=65535, description="监听端口")

    # ==================== LLM 配置 ====================

    dashscope_api_key: str = Field(default="", description="通义千问 API Key")
    llm_model_name: str = Field(default="qwen-max", description="LLM 模型名称")
    llm_temperature: float = Field(default=0.7, ge=0, le=2, description="生成温度")
    llm_max_tokens: int = Field(default=2000, ge=1, le=32000, description="最大生成 token 数")
    llm_timeout: int = Field(default=60, ge=1, description="LLM 调用超时时间(秒)")
    llm_cache_ttl: int = Field(default=3600, ge=0, description="LLM 响应缓存 TTL(秒)")

    # ==================== Redis 配置 ====================

    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis 连接地址"
    )
    redis_password: str = Field(default="", description="Redis 密码")
    redis_session_ttl: int = Field(
        default=604800, ge=60, description="会话 TTL (秒), 默认 7 天"
    )
    redis_max_connections: int = Field(default=20, ge=1, description="Redis 最大连接数")

    # ==================== 数据库配置 ====================

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/fitness_agent",
        description="数据库连接地址",
    )
    database_pool_size: int = Field(default=10, ge=1, description="数据库连接池大小")
    database_max_overflow: int = Field(default=20, ge=0, description="数据库连接池最大溢出")
    database_echo: bool = Field(default=False, description="是否打印 SQL")

    # ==================== 向量数据库配置 ====================

    chroma_persist_dir: str = Field(
        default="./data/chroma", description="Chroma 持久化目录"
    )
    chroma_collection_name: str = Field(
        default="fitness_knowledge", description="Chroma 集合名称"
    )
    embedding_model: str = Field(
        default="text-embedding-v3", description="嵌入模型名称"
    )
    embedding_batch_size: int = Field(
        default=10, ge=1, le=25, description="嵌入批处理大小"
    )

    # ==================== JWT 配置 ====================

    jwt_secret_key: str = Field(
        default="change_this_in_production", description="JWT 密钥"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT 算法")
    jwt_access_token_expire_minutes: int = Field(
        default=120, ge=1, description="Access Token 过期时间(分钟)"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, ge=1, description="Refresh Token 过期时间(天)"
    )

    # ==================== 限流配置 ====================

    rate_limit_enabled: bool = Field(default=True, description="是否启用限流")
    rate_limit_requests: int = Field(default=60, ge=1, description="限流请求数")
    rate_limit_period: int = Field(default=60, ge=1, description="限流周期(秒)")

    # ==================== 日志配置 ====================

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="日志级别"
    )
    log_format: Literal["json", "text"] = Field(default="json", description="日志格式")

    # ==================== MCP 配置 ====================

    mcp_enabled: bool = Field(default=False, description="是否启用 MCP")
    mcp_exercise_lib_url: str = Field(
        default="http://localhost:8001", description="动作库 MCP 服务地址"
    )
    mcp_fitness_data_url: str = Field(
        default="http://localhost:8002", description="健身数据 MCP 服务地址"
    )
    mcp_nutrition_url: str = Field(
        default="http://localhost:8003", description="营养分析 MCP 服务地址"
    )

    # ==================== 计算属性 ====================

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "development"

    @property
    def is_staging(self) -> bool:
        """是否为预发布环境"""
        return self.app_env == "staging"

    # ==================== 验证器 ====================

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """验证 JWT 密钥"""
        if v == "change_this_in_production":
            import warnings
            warnings.warn(
                "JWT_SECRET_KEY 使用默认值，生产环境必须修改！",
                UserWarning,
            )
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """验证生产环境配置"""
        if self.is_production:
            if not self.dashscope_api_key:
                raise ValueError("生产环境必须设置 DASHSCOPE_API_KEY")
            if self.jwt_secret_key == "change_this_in_production":
                raise ValueError("生产环境必须修改 JWT_SECRET_KEY")
        return self


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（带缓存）"""
    return Settings()


# 全局配置实例
settings = get_settings()

