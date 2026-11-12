# -*- coding: utf-8 -*-
"""统一返回结构与业务异常模块：所有对外接口返回 {"ok", "data", "error"} 三键结构。"""  # 模块级说明


class AppError(Exception):
    """业务异常类：携带统一错误码与中文提示，由全局异常处理器转成统一返回结构。"""  # 类级说明

    def __init__(self, code: str, msg: str, status: int = 200):
        """构造业务异常。

        入参：code —— 错误码字符串（如 AUTH_001）；msg —— 中文错误提示；status —— HTTP 状态码，默认 200。
        出参：无（初始化实例属性）。
        失败时的行为：无额外失败路径。
        """
        # 调用父类构造，保证异常链正常
        super().__init__(msg)  # 把中文提示传给父类
        # 保存错误码，供全局处理器使用
        self.code = code  # 错误码
        # 保存中文提示
        self.msg = msg  # 错误提示
        # 保存 HTTP 状态码
        self.status = status  # HTTP 状态码


def ok(data=None):
    """构造成功返回。

    入参：data —— 任意可 JSON 序列化的业务数据，默认 None。
    出参：dict —— {"ok": True, "data": data, "error": None}。
    失败时的行为：无失败路径。
    """
    # 成功时 error 固定为 None，保证三键结构恒定
    return {"ok": True, "data": data, "error": None}  # 统一成功结构


def err(code: str, msg: str):
    """构造失败返回。

    入参：code —— 错误码字符串；msg —— 中文错误提示。
    出参：dict —— {"ok": False, "data": None, "error": {"code": code, "msg": msg}}。
    失败时的行为：无失败路径。
    """
    # 失败时 data 固定为 None，错误信息只放 error 两键
    return {"ok": False, "data": None, "error": {"code": code, "msg": msg}}  # 统一失败结构
