# -*- coding: utf-8 -*-
"""审计路由：审计记录查询接口（仅质控专员与运营主任可访问）。"""  # 模块级说明

from fastapi import APIRouter, Depends  # 引入路由器与依赖注入

from ..core.deps import get_identity, require_roles  # 引入权限依赖
from ..core.response import ok  # 引入统一返回
from ..db.models import AuditLog, SessionLocal  # 引入审计模型与会话工厂

# 创建路由器（挂在 /api/audit 前缀下）
router = APIRouter(prefix="/api/audit", tags=["audit"])  # 路由器


@router.get("/list")
def list_audit(identity: dict = Depends(require_roles("qc", "director"))):
    """审计记录列表：按业务编号维度返回全部留痕记录。

    入参：无（identity 由权限依赖注入）。
    出参：统一结构 {"ok": True, "data": [审计记录字典...]}，按时间倒序。
    失败时的行为：角色非 qc/director 时由权限依赖抛 AppError(AUTH_003)；数据库异常由全局处理器转 SYS_001。
    """
    # 打开数据库会话
    session = SessionLocal()  # 会话
    try:  # 保证会话关闭
        # 查询全部审计记录并按创建时间倒序
        rows = session.query(AuditLog).order_by(AuditLog.created_at.desc()).all()  # 查询记录
        # 转成字典列表（只返回 f45 规定的字段，不含口令与不必要个人信息）
        data = [  # 列表推导
            {  # 单条记录字典
                "id": row.id,  # 记录 ID
                "business_id": row.business_id,  # 业务编号
                "data_version": row.data_version,  # 资料版本
                "fact_refs": row.fact_refs,  # 事实引用
                "suggestion": row.suggestion,  # 建议结果
                "manual_change": row.manual_change,  # 人工改动
                "signer": row.signer,  # 签核人
                "created_at": row.created_at.isoformat(),  # 记录时间（ISO 字符串）
            }  # 结束单条
            for row in rows  # 遍历记录
        ]  # 结束推导
        # 返回统一成功结构
        return ok(data)  # 成功返回
    finally:  # 无论成败都执行
        # 关闭会话
        session.close()  # 关闭会话


@router.get("/me")
def who_am_i(identity: dict = Depends(get_identity)):
    """身份自检接口：返回当前令牌对应的身份（供验证脚本确认登录态）。

    入参：无（identity 由权限依赖注入）。
    出参：统一结构 {"ok": True, "data": {"username", "role"}}。
    失败时的行为：未登录/令牌无效时由 get_identity 抛 AppError(AUTH_002)。
    """
    # 返回当前身份
    return ok({"username": identity["username"], "role": identity["role"]})  # 成功返回
