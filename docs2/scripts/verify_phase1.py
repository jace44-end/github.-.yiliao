# -*- coding: utf-8 -*-
"""Phase 1 验证脚本：端到端验证登录、统一返回结构、RBAC 权限拦截。

运行前提：服务已按下方命令启动。
运行方式：python scripts/verify_phase1.py
"""  # 模块级说明

import sys  # 引入 sys，用于退出码

import httpx  # 引入 httpx，发送 HTTP 请求
import yaml  # 引入 yaml，读取服务地址配置

# 读取 config.yaml 拿服务地址（与被测服务同一份配置，避免脚本里写死地址）
with open("config.yaml", "r", encoding="utf-8") as f:  # 打开配置文件
    # 解析配置
    _cfg = yaml.safe_load(f)  # 配置字典

# 拼接服务基地址
BASE = f"http://{_cfg['server']['host']}:{_cfg['server']['port']}"  # 基地址
# 演示账号口令（与 app/db/seed.py 中的 DEMO_PASSWORD 保持一致）
DEMO_PASSWORD = "Demo@123456"  # 演示口令

# 通过计数器
passed = 0  # 通过数
# 失败明细列表
failed = []  # 失败列表


def check(name, condition, detail=""):
    """记录单项验证结果。

    入参：name —— 用例名；condition —— 是否通过；detail —— 失败明细。
    出参：无（更新全局计数）。
    失败时的行为：失败项追加到 failed 列表，脚本结束统一汇报。
    """
    # 引用全局计数
    global passed  # 全局变量
    # 通过则计数加一
    if condition:  # 结果判断
        # 通过计数
        passed += 1  # 计数
        # 打印通过标记
        print(f"[PASS] {name}")  # 输出
    else:  # 未通过
        # 记录失败明细
        failed.append(f"{name} {detail}")  # 记录
        # 打印失败标记
        print(f"[FAIL] {name} {detail}")  # 输出


def main():
    """执行全部 Phase 1 验证用例。

    入参：无。
    出参：无（进程退出码 0=全部通过，1=有失败）。
    失败时的行为：任一用例失败最终退出码为 1。
    """
    # 引用全局计数
    global passed  # 全局变量
    # 创建 HTTP 客户端（trust_env=False 忽略系统代理，避免本机回环请求被代理劫持）
    client = httpx.Client(timeout=10, trust_env=False)  # 客户端

    # 用例 1：健康自检 —— 服务可达
    try:  # 网络请求可能失败
        # 请求身份自检接口（不带令牌，应返回 401 类业务错误）
        r = client.get(f"{BASE}/api/audit/me")  # 发请求
        # 解析返回体
        body = r.json()  # JSON
        # 断言统一返回结构与 AUTH_002 错误码
        check("未登录访问受限接口返回统一结构", body.get("ok") is False and body.get("error", {}).get("code") == "AUTH_002", f"实际返回 {body}")  # 校验
    except Exception as e:  # 网络异常
        # 记录失败
        check("服务可达", False, f"异常 {e}")  # 记录
        # 直接退出（服务不可达，后续用例无意义）
        sys.exit(1)  # 退出

    # 用例 2：错误口令登录被拒（AUTH_001）
    r = client.post(f"{BASE}/api/auth/login", json={"username": "demo_qc", "password": "wrong"})  # 错误口令登录
    # 解析返回体
    body = r.json()  # JSON
    # 断言失败结构
    check("错误口令登录返回 AUTH_001", body.get("ok") is False and body.get("error", {}).get("code") == "AUTH_001", f"实际返回 {body}")  # 校验

    # 用例 3：正确口令登录成功且返回角色
    r = client.post(f"{BASE}/api/auth/login", json={"username": "demo_qc", "password": DEMO_PASSWORD})  # 正确登录
    # 解析返回体
    body = r.json()  # JSON
    # 断言成功结构与角色绑定
    qc_ok = body.get("ok") is True and body.get("data", {}).get("role") == "qc" and bool(body.get("data", {}).get("token"))  # 校验条件
    # 校验登录
    check("质控账号登录成功并返回 token", qc_ok, f"实际返回 {body}")  # 校验
    # 取出令牌供后续用例
    qc_token = body.get("data", {}).get("token", "") if qc_ok else ""  # 令牌

    # 用例 4：护士账号登录成功（六角色均可登录）
    r = client.post(f"{BASE}/api/auth/login", json={"username": "demo_nurse", "password": DEMO_PASSWORD})  # 护士登录
    # 解析返回体
    body = r.json()  # JSON
    # 断言护士登录
    check("护士账号登录成功", body.get("ok") is True and body.get("data", {}).get("role") == "nurse", f"实际返回 {body}")  # 校验
    # 取护士令牌
    nurse_token = body.get("data", {}).get("token", "") if body.get("ok") else ""  # 令牌

    # 用例 5：质控角色可访问审计接口（白名单内）
    qc_headers = {"Authorization": f"Bearer {qc_token}"} if qc_token else {"Authorization": "Bearer none"}  # 组装请求头（空令牌兜底防协议错误）
    r = client.get(f"{BASE}/api/audit/list", headers=qc_headers)  # 质控查审计
    # 解析返回体
    body = r.json()  # JSON
    # 断言访问成功
    check("质控角色可查询审计列表", body.get("ok") is True and isinstance(body.get("data"), list), f"实际返回 {body}")  # 校验

    # 用例 6：护士角色访问审计接口被拒（AUTH_003 越权拦截）
    nurse_headers = {"Authorization": f"Bearer {nurse_token}"} if nurse_token else {"Authorization": "Bearer none"}  # 组装请求头（空令牌兜底防协议错误）
    r = client.get(f"{BASE}/api/audit/list", headers=nurse_headers)  # 护士查审计
    # 解析返回体
    body = r.json()  # JSON
    # 断言越权拦截
    check("护士角色查审计被拒(AUTH_003)", body.get("ok") is False and body.get("error", {}).get("code") == "AUTH_003", f"实际返回 {body}")  # 校验

    # 用例 7：伪造令牌被拒（签名校验）
    r = client.get(f"{BASE}/api/audit/me", headers={"Authorization": "Bearer fake|qc|9999999999|deadbeef"})  # 伪造令牌
    # 解析返回体
    body = r.json()  # JSON
    # 断言伪造令牌拦截
    check("伪造令牌被拒(AUTH_002)", body.get("ok") is False and body.get("error", {}).get("code") == "AUTH_002", f"实际返回 {body}")  # 校验

    # 汇总输出
    print(f"\n合计 {passed} 项通过，{len(failed)} 项失败")  # 汇总
    # 有失败则退出码 1
    sys.exit(1 if failed else 0)  # 退出码


# 脚本入口
if __name__ == "__main__":  # 入口判断
    # 执行主流程
    main()  # 运行
