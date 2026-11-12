# -*- coding: utf-8 -*-
"""权限依赖模块：FastAPI 依赖注入形式的权限校验，所有受限接口统一从这里卡权限。"""  # 模块级说明

from fastapi import Depends, Header  # 引入 Header 与 Depends，用于读取请求头与级联依赖注入

from .config import CONFIG  # 引入全局配置（角色定义）
from .response import AppError  # 引入业务异常（权限失败统一抛 AUTH 错误码）
from .security import parse_token  # 引入令牌解析函数


def get_identity(authorization: str = Header(default=None)):
    """从请求头解析登录身份。

    入参：authorization —— HTTP 请求头 Authorization 的值（格式 Bearer <token>）。
    出参：dict —— {"username": ..., "role": ...}。
    失败时的行为：令牌缺失/无效/过期时抛 AppError(AUTH_002)，由全局处理器返回统一结构。
    """
    # 请求头缺失时直接按未登录处理
    if not authorization:  # 请求头检查
        # 抛业务异常：未携带登录凭据
        # 【为什么这么卡】f41 禁止借用账号：没有合法令牌就视同未登录，绝不放行匿名请求
        raise AppError("AUTH_002", "未登录或登录态无效，请先登录")  # 统一错误码
    # 去掉 Bearer 前缀取出令牌（大小写兼容处理）
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization  # 提取令牌
    # 解析并校验令牌
    identity = parse_token(token)  # 解析令牌
    # 解析失败统一按登录态无效处理
    if identity is None:  # 令牌校验结果
        # 抛业务异常：令牌无效或过期
        # 【为什么这么卡】签名/过期/角色合法性三重校验在 parse_token 内完成，任何一项不过都不给身份
        raise AppError("AUTH_002", "登录态无效或已过期，请重新登录")  # 统一错误码
    # 返回解析出的身份
    return identity  # {"username", "role"}


def require_roles(*allowed_roles):
    """构造指定角色白名单的权限校验依赖（FastAPI Depends 用）。

    入参：*allowed_roles —— 允许访问该接口的角色标识列表（如 "qc", "director"）。
    出参：依赖函数 —— 接收 identity 并校验角色，通过时返回 identity。
    失败时的行为：角色不在白名单时抛 AppError(AUTH_003)。
    """
    # 定义内层依赖函数（闭包持有白名单；identity 必须用 Depends 级联注入，否则 FastAPI 不会解析请求头）
    def checker(identity: dict = Depends(get_identity)):
        """校验当前身份的角色是否在白名单内。

        入参：identity —— get_identity 解析出的身份字典。
        出参：dict —— 校验通过的身份。
        失败时的行为：角色越权时抛 AppError(AUTH_003)。
        """
        # 【为什么这么卡】f41 只有授权岗位可查看号源、排班、签到叫号时间与分诊规则：
        # 权限校验必须服务端统一做，不能依赖前端隐藏按钮，越权请求在这里被硬拦截
        if identity is None or identity.get("role") not in allowed_roles:  # 白名单校验
            # 抛业务异常：角色越权
            raise AppError("AUTH_003", f"当前角色无权访问该资源（允许角色：{','.join(allowed_roles)}）")  # 统一错误码
        # 校验通过返回身份，供业务函数继续使用
        return identity  # 返回身份
    # 返回内层依赖
    return checker  # 交给 FastAPI Depends 使用


def get_role_display(role: str) -> str:
    """查询角色的中文显示名。

    入参：role —— 角色标识字符串。
    出参：str —— 角色中文名；未定义角色返回原标识。
    失败时的行为：角色未在 config.yaml 定义时回退返回角色标识本身，不抛异常。
    """
    # 从配置读取角色映射
    roles = CONFIG.get("roles", {})  # 角色映射字典
    # 未定义角色回退返回标识本身，避免 None 下游崩溃
    return roles.get(role, role)  # 返回中文显示名
