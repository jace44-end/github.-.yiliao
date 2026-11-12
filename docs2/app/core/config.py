# -*- coding: utf-8 -*-
"""配置加载模块：统一从 config.yaml 读取全部配置，禁止把密钥/模型地址写死在代码里。"""  # 模块级说明

import os  # 引入 os 模块，用于拼接配置文件路径

import yaml  # 引入 PyYAML，用于解析 config.yaml

# 配置文件固定放在项目根目录的 config.yaml（与 app 包同级）
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.yaml")  # 计算 config.yaml 的绝对路径


def load_config() -> dict:
    """读取并解析 config.yaml。

    入参：无。
    出参：dict —— 整个配置文件的字典结构。
    失败时的行为：文件不存在或 YAML 格式错误时抛出 RuntimeError，拒绝启动（配置缺失不该带病运行）。
    """
    # 先判断配置文件是否存在，缺失时直接报错而不是返回空配置
    if not os.path.exists(_CONFIG_PATH):  # 存在性检查
        # 抛出明确错误，提示配置文件缺失
        raise RuntimeError(f"配置文件不存在：{_CONFIG_PATH}，请在项目根目录放置 config.yaml")
    # 打开并解析 YAML 文件（显式 UTF-8，避免中文注释乱码）
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:  # 以 UTF-8 打开配置文件
        # yaml.safe_load 只产出基础类型，避免反序列化任意对象的安全风险
        return yaml.safe_load(f) or {}  # 返回解析结果；空文件时返回空字典


# 模块加载时读取一次全局配置（本系统配置只读，不提供热更新）
CONFIG = load_config()  # 全局唯一配置对象
