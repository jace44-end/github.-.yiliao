# -*- coding: utf-8 -*-
"""数据模型模块：SQLAlchemy ORM 模型定义（Phase 1：users + audit_logs）。"""  # 模块级说明

import datetime  # 引入 datetime，用于审计记录时间戳

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine  # 引入列类型与建引擎函数
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker  # 引入 ORM 基类与会话工厂

from ..core.config import CONFIG  # 引入全局配置（数据库连接串来自 config.yaml）

# 数据库目录需要预先创建（SQLite 文件所在目录不存在时连接会失败）
_engine_url = CONFIG["database"]["url"]  # 从配置读取连接串，禁止写死在代码里
# 计算数据库文件目录
_db_dir = "app/data"  # 与 config.yaml 中的相对路径保持一致


class Base(DeclarativeBase):
    """全部 ORM 模型的公共基类。"""  # 类级说明

    pass  # 无需额外配置


class User(Base):
    """用户表：账号 + 角色（f41 禁止借用账号，账号绑定唯一角色）。"""  # 类级说明

    # 指定表名
    __tablename__ = "users"  # 表名
    # 主键自增 ID
    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键
    # 用户名（登录凭据，唯一）
    username = Column(String(64), unique=True, nullable=False)  # 用户名
    # 口令哈希（不存明文口令，符合 f45 不记录口令的要求）
    password_hash = Column(String(128), nullable=False)  # 口令哈希
    # 该用户的独立盐（逐用户独立盐比全局盐更抗彩虹表）
    salt = Column(String(64), nullable=False)  # 用户盐
    # 角色标识（config.yaml roles 中的一个键）
    role = Column(String(32), nullable=False)  # 角色标识


class AuditLog(Base):
    """审计留痕表：按 f45 六字段设计，保证可重建处理链。"""  # 类级说明

    # 指定表名
    __tablename__ = "audit_logs"  # 表名
    # 主键自增 ID
    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键
    # 业务编号（跨系统关联的主编号，f33/f45）
    business_id = Column(String(64), nullable=False, index=True)  # 业务编号（建索引支持按编号重建链）
    # 资料版本（处理时使用的资料版本号，f45）
    data_version = Column(String(32), nullable=False)  # 资料版本
    # 事实引用（本次建议引用的访谈/数据事实编号，f45）
    fact_refs = Column(String(256), nullable=False)  # 事实引用
    # 建议结果（智能体给出的建议内容，f45）
    suggestion = Column(Text, nullable=False)  # 建议结果
    # 人工改动（人工修改前后的差异记录，f45）
    manual_change = Column(Text, nullable=False, default="")  # 人工改动
    # 签核人（最终确认该条记录的岗位账号，f45）
    signer = Column(String(64), nullable=False)  # 签核人
    # 记录时间（审计链的时序锚点）
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)  # 创建时间


# 创建数据库引擎（SQLite，check_same_thread=False 允许 FastAPI 多线程访问）
engine = create_engine(_engine_url, connect_args={"check_same_thread": False} if _engine_url.startswith("sqlite") else {})  # 引擎
# 创建会话工厂
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)  # 会话工厂


def init_db() -> None:
    """初始化数据库：建目录、建表。

    入参：无。
    出参：无。
    失败时的行为：目录/表创建失败时抛出原始异常，由启动流程终止（数据库不可用不能带病启动）。
    """
    # 确保数据库目录存在（SQLite 文件的父目录必须预先创建）
    import os  # 局部引入 os，用于建目录
    # 建目录（已存在时跳过）
    os.makedirs(_db_dir, exist_ok=True)  # 建目录
    # 按全部模型建表（已存在的表不会被重建）
    Base.metadata.create_all(engine)  # 建表


def get_session() -> Session:
    """打开一个数据库会话（调用方负责关闭）。

    入参：无。
    出参：Session —— SQLAlchemy 会话对象。
    失败时的行为：连接失败时抛出原始异常，由全局处理器转为 SYS 错误码。
    """
    # 从工厂创建新会话
    return SessionLocal()  # 返回会话
