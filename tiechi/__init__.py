# -*- coding: utf-8 -*-
"""
tiechi —— 不锈钢板金定制品报价引擎
==================================

输入一组尺寸 + 工艺参数，输出一份能直接给客户看的报价：
材料费、折弯费、焊接费、表面费、包装费、物流费、安装费逐项拆开，
外加"这一单有什么坑"的工艺告警。

    from tiechi import calculate
    r = calculate({"opening_w": 1000, "opening_h": 2100, "wall_d": 240})
    print(r["单套报价"], r["告警"])

模块：
    pricebook    单价表（外置 pricebook.json，改价不改代码）
    geometry/    展开面积计算（按品类分文件）
    cost_engine  成本计算（7 项成本 + 报价 + 置信度）
    schema       输入字段定义（给 UI / CLI 生成表单用）

口径说明见 docs/成本模型.md 与 docs/工艺与几何.md。
"""
from .cost_engine import calculate, default_inputs
from .pricebook import (
    load_pricebook,
    save_pricebook,
    update_price_params,
    reset_pricebook,
    calibrate_pricebook,
)

__version__ = "1.0.0"

__all__ = [
    "calculate", "default_inputs",
    "load_pricebook", "save_pricebook", "update_price_params",
    "reset_pricebook", "calibrate_pricebook",
]
