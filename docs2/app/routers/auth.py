# -*- coding: utf-8 -*-
"""认证路由：登录接口，登录成功签发绑定角色的令牌。"""  # 模块级说明

from fastapi import APIRouter  # 引入路由器
from pydantic import BaseModel  # 引入请求体模型

from ..core.config import CONFIG  # 引入全局配置
from ..core.response import AppError, ok  # 引入统一返回与业务异常
from ..core.security import create_token, verify_password  # 引入安全函数
from ..db.models import SessionLocal, User  # 引入数据库模型

# 创建路由器（统一挂在 /api/auth 前缀下）
router = APIRouter(prefix="/api/auth", tags=["auth"])  # 路由器


class LoginRequest(BaseModel):
    """登录请求体模型。"""  # 类级说明

    # 用户名
    username: str  # 用户名
    # 口令
    password: str  # 口令


@router.post("/login")
def login(body: LoginRequest):
    """登录接口：校验口令后签发令牌。

    入参：body —— {"username": str, "password": str}。
    出参：统一结构 {"ok": True, "data": {"token", "username", "role", "role_name"}}。
    失败时的行为：用户不存在或口令错误抛 AppError(AUTH_001)；账号口令错误不区分具体原因，避免给撞库者提供信息。
    """
    # 打开数据库会话
    session = SessionLocal()  # 会话
    try:  # 保证会话关闭
        # 按用户名查用户
        user = session.query(User).filter(User.username == body.username).first()  # 查询用户
        # 用户不存在或口令校验失败走同一分支
        # 【为什么这么卡】f41 禁止借用账号：令牌与账号一一绑定，口令校验是账号归属的第一道卡点；
        # 失败提示不区分"用户不存在"和"口令错误"，防止攻击者枚举有效用户名
        if user is None or not verify_password(body.password, user.salt, user.password_hash):  # 凭据校验
            # 抛统一登录失败异常
            raise AppError("AUTH_001", "用户名或口令错误")  # 统一错误码
        # 登录成功，签发绑定角色的令牌（角色来自库内数据而非请求参数，防止请求方自选角色）
        token = create_token(user.username, user.role)  # 签发令牌
        # 返回统一成功结构
        return ok({"token": token, "username": user.username, "role": user.role, "role_name": CONFIG["roles"].get(user.role, user.role)})  # 成功返回
    finally:  # 无论成败都执行
        # 关闭会话
        session.close()  # 关闭会话
