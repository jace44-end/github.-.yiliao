# -*- coding: utf-8 -*-
"""安全模块：口令哈希校验与 HMAC 签名令牌（不引入额外依赖，全部使用标准库）。"""  # 模块级说明

import hashlib  # 引入 hashlib，用于 SHA-256 口令哈希与 HMAC 签名
import hmac  # 引入 hmac，用于常量时间比较与令牌签名
import time  # 引入 time，用于令牌过期时间戳

from .config import CONFIG  # 引入全局配置（密钥、有效期都来自 config.yaml）


def hash_password(password: str, salt: str) -> str:
    """对口令做加盐 SHA-256 哈希。

    入参：password —— 用户明文口令；salt —— 盐值（来自 config.yaml 或用户行）。
    出参：str —— 十六进制哈希串。
    失败时的行为：无失败路径（哈希对任意字符串都可计算）。
    """
    # 把 盐+口令 拼接后按 UTF-8 编码再做 SHA-256，防止相同口令在不同系统产生相同哈希
    return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()  # 返回哈希十六进制串


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """校验用户输入口令是否与库中哈希一致。

    入参：password —— 用户输入的明文口令；salt —— 盐值；password_hash —— 库中存储的哈希串。
    出参：bool —— 一致返回 True，否则 False。
    失败时的行为：输入为 None 等异常情况按"不匹配"处理，不抛异常（登录失败不该暴露系统内部错误）。
    """
    # 防御空输入：任何空值直接判定不匹配，避免 None 拼接报错
    if not password or not salt or not password_hash:  # 空值检查
        # 直接返回不匹配
        return False  # 空输入一律视为校验失败
    # 用常量时间比较（hmac.compare_digest）防止时序攻击逐字节猜测哈希
    return hmac.compare_digest(hash_password(password, salt), password_hash)  # 常量时间比较结果


def create_token(username: str, role: str) -> str:
    """为登录用户签发 HMAC-SHA256 签名令牌。

    入参：username —— 用户名；role —— 角色标识（config.yaml roles 中的一个键）。
    出参：str —— 格式为 "username|role|过期时间戳|签名" 的令牌字符串。
    失败时的行为：无失败路径。
    """
    # 读取令牌有效期（分钟）并换算成秒
    expire_seconds = int(CONFIG["security"]["token_expire_minutes"]) * 60  # 分钟转秒
    # 计算过期时间戳
    expire_at = int(time.time()) + expire_seconds  # 当前时间加有效期
    # 组装未签名的载荷（用竖线分隔，载荷中不含口令等敏感信息，符合 f45 不记录口令的要求）
    payload = f"{username}|{role}|{expire_at}"  # 载荷字符串
    # 用 config.yaml 中的密钥做 HMAC-SHA256 签名（密钥不写死在代码里）
    signature = hmac.new(CONFIG["security"]["secret_key"].encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()  # 计算签名
    # 拼接载荷与签名形成最终令牌
    return f"{payload}|{signature}"  # 返回完整令牌


def parse_token(token: str):
    """校验并解析令牌。

    入参：token —— 请求头中携带的令牌字符串。
    出参：dict —— {"username": ..., "role": ...}；令牌无效/过期时返回 None。
    失败时的行为：任何格式错误、签名不符、过期都不抛异常，统一返回 None（由权限层转成 AUTH 错误码）。
    """
    # 防御空令牌
    if not token:  # 空值检查
        # 返回 None 表示无效
        return None  # 空令牌无效
    # 按竖线切分，期望四段：用户名、角色、过期时间、签名
    parts = token.split("|")  # 切分令牌
    # 段数不对直接判定无效
    if len(parts) != 4:  # 格式检查
        # 返回 None 表示无效
        return None  # 格式错误无效
    # 解构四段
    username, role, expire_at, signature = parts  # 取出各段
    # 重新计算载荷签名并与令牌内签名做常量时间比较，防止伪造
    expected = hmac.new(CONFIG["security"]["secret_key"].encode("utf-8"), f"{username}|{role}|{expire_at}".encode("utf-8"), hashlib.sha256).hexdigest()  # 重算签名
    # 签名不一致说明令牌被篡改或密钥已更换
    if not hmac.compare_digest(expected, signature):  # 常量时间比较签名
        # 返回 None 表示无效
        return None  # 签名不符无效
    # 校验过期时间：令牌过期必须失效，防止旧令牌长期可用（权限时效控制）
    if int(time.time()) > int(expire_at):  # 过期检查
        # 返回 None 表示无效
        return None  # 已过期无效
    # 校验角色必须是 config.yaml 中定义的合法角色，防止令牌内塞入越权角色名
    if role not in CONFIG["roles"]:  # 合法角色检查
        # 返回 None 表示无效
        return None  # 非法角色无效
    # 全部校验通过，返回用户身份
    return {"username": username, "role": role}  # 返回身份字典
