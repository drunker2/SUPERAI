"""
认证 API 路由
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.auth.service import AuthService, get_auth_service
from app.auth.schemas import UserCreate, UserLogin, Token, UserResponse, UserUpdate
from app.auth.dependencies import CurrentUser, OptionalUser
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="""
创建新用户账户。

## 注册要求
- 用户名：3-50 个字符，建议使用字母、数字、下划线
- 邮箱：有效的邮箱地址，用于找回密码
- 密码：6-100 个字符，建议包含字母和数字

## 返回信息
注册成功后返回用户基本信息（不包含密码）。
""",
    responses={
        201: {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "fitness_user",
                        "email": "user@example.com",
                        "is_active": True,
                        "created_at": "2024-01-15T10:00:00",
                    }
                }
            }
        },
        400: {"description": "用户名或邮箱已存在"},
    },
)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    用户注册

    - **username**: 用户名，3-50 个字符
    - **email**: 邮箱地址
    - **password**: 密码，6-100 个字符
    """
    try:
        user = await auth_service.register_user(db, user_data)
        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
    description="""
使用用户名和密码登录，获取 JWT 访问令牌。

## 认证方式
登录成功后，在后续请求的 Header 中携带令牌：
```
Authorization: Bearer <access_token>
```

## 令牌有效期
- 默认有效期：2 小时
- 可通过 JWT_ACCESS_TOKEN_EXPIRE_MINUTES 配置
""",
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 7200,
                    }
                }
            }
        },
        401: {"description": "用户名或密码错误"},
    },
)
async def login(
    user_data: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    用户登录

    - **username**: 用户名
    - **password**: 密码

    成功后返回 access_token，用于后续 API 认证
    """
    token = await auth_service.login(db, user_data.username, user_data.password)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="""
获取当前登录用户的详细信息。

## 认证要求
需要在请求 Header 中携带有效的 JWT 令牌：
```
Authorization: Bearer <access_token>
```

## 返回信息
- 用户基本信息：ID、用户名、邮箱、激活状态
- 用户画像：年龄、性别、身高、体重、健身目标、健身水平
""",
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "fitness_user",
                        "email": "user@example.com",
                        "is_active": True,
                        "age": 28,
                        "gender": "male",
                        "height": 175.0,
                        "weight": 70.0,
                        "fitness_goal": "减脂",
                        "fitness_level": "中级",
                        "created_at": "2024-01-15T10:00:00",
                    }
                }
            }
        },
        401: {"description": "未登录或 Token 无效"},
    },
)
async def get_me(current_user: CurrentUser):
    """
    获取当前用户信息

    需要在 Header 中携带 Bearer Token
    """
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="更新用户画像",
    description="""
更新当前用户的身体信息和健身目标。

## 用户画像字段
| 字段 | 类型 | 说明 |
|------|------|------|
| age | int | 年龄 (1-120) |
| gender | string | 性别: male/female |
| height | float | 身高 (cm) |
| weight | float | 体重 (kg) |
| fitness_goal | string | 健身目标: 减脂/增肌/塑形/维持 |
| fitness_level | string | 健身水平: 初级/中级/高级 |

## 用途
用户画像用于个性化推荐，如训练计划生成、营养建议等。
只需更新需要修改的字段，其他字段保持不变。
""",
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "fitness_user",
                        "email": "user@example.com",
                        "is_active": True,
                        "age": 28,
                        "gender": "male",
                        "height": 175.0,
                        "weight": 70.0,
                        "fitness_goal": "减脂",
                        "fitness_level": "中级",
                        "created_at": "2024-01-15T10:00:00",
                    }
                }
            }
        },
        401: {"description": "未登录或 Token 无效"},
    },
)
async def update_profile(
    profile_data: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """
    更新用户画像

    - **age**: 年龄 (1-120)
    - **gender**: 性别 (male/female)
    - **height**: 身高 (cm)
    - **weight**: 体重 (kg)
    - **fitness_goal**: 健身目标 (减脂/增肌/塑形/维持)
    - **fitness_level**: 健身水平 (初级/中级/高级)
    """
    user = await auth_service.update_user_profile(
        db,
        current_user.id,
        **profile_data.model_dump(exclude_unset=True),
    )

    return UserResponse.model_validate(user)


@router.get(
    "/verify",
    summary="验证 Token",
    description="""
验证当前 JWT Token 是否有效。

## 用途
- 检查 Token 是否过期
- 获取 Token 对应的用户信息
- 前端应用初始化时验证登录状态

## 返回值
- 有效：返回用户信息
- 无效：返回 valid: false
""",
    responses={
        200: {
            "description": "验证结果",
            "content": {
                "application/json": {
                    "examples": {
                        "valid": {
                            "summary": "Token 有效",
                            "value": {
                                "valid": True,
                                "user_id": 1,
                                "username": "fitness_user",
                            }
                        },
                        "invalid": {
                            "summary": "Token 无效",
                            "value": {
                                "valid": False,
                                "message": "未登录或 Token 无效",
                            }
                        }
                    }
                }
            }
        },
    },
)
async def verify_token(current_user: OptionalUser) -> dict[str, Any]:
    """
    验证 Token

    返回 Token 是否有效以及用户信息。
    不需要强制登录，未登录返回 valid: false
    """
    if current_user is None:
        return {
            "valid": False,
            "message": "未登录或 Token 无效",
        }

    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
    }
