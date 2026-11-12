# -*- coding: utf-8 -*-
"""种子数据模块：首次启动时写入六个角色的演示账号（对应访谈中的六个岗位）。"""  # 模块级说明

import uuid  # 引入 uuid，为每个用户生成独立随机盐

from ..core.config import CONFIG  # 引入全局配置（角色清单来自 config.yaml）
from ..core.security import hash_password  # 引入口令哈希函数
from .models import SessionLocal, User  # 引入会话工厂与用户模型

# 演示账号统一初始口令（仅试点演示用，正式上线必须由用户首次登录强制改密）
DEMO_PASSWORD = "Demo@123456"  # 演示口令


def seed_users() -> None:
    """向 users 表写入六个角色账号（幂等：已有账号则跳过）。

    入参：无。
    出参：无。
    失败时的行为：数据库写入失败时抛出原始异常，由启动流程终止。
    """
    # 打开会话
    session = SessionLocal()  # 数据库会话
    try:  # 用 try/finally 保证会话关闭
        # 遍历 config.yaml 中定义的全部角色，逐个建账号
        for role_key in CONFIG["roles"]:  # 角色循环
            # 幂等检查：同名账号已存在则跳过（重复启动不重复插入）
            exists = session.query(User).filter(User.username == f"demo_{role_key}").first()  # 查重
            # 已存在则跳过本轮
            if exists:  # 存在检查
                # 跳过该角色
                continue  # 幂等跳过
            # 为该用户生成独立随机盐（逐用户独立盐，比全局盐更安全）
            salt = uuid.uuid4().hex  # 独立盐
            # 创建用户行：用户名 demo_<角色>，角色绑定唯一（f41 禁止借用账号）
            user = User(username=f"demo_{role_key}", salt=salt, role=role_key, password_hash=hash_password(DEMO_PASSWORD, salt))  # 用户对象
            # 加入会话
            session.add(user)  # 待写入
        # 提交事务
        session.commit()  # 提交
    finally:  # 无论成败都执行
        # 关闭会话释放连接
        session.close()  # 关闭会话
