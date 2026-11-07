# -*- coding: utf-8 -*-
"""
lines —— 装饰线条展开几何
========================================

【为什么要有装饰线条】
    工厂天天接到"给我报 60 米不锈钢线条"的电话：收边条、嵌条、
    电梯门套线条、背景墙框线、吊顶收口条……这类活儿不按"套"算，
    按米卖 —— 它是「延米价」定价模式最典型的使用场景。

【输入口径】（三条，老板微信里报尺寸就是这个格式）
    摊平宽  line_dev_w  mm   板料摊开的总宽（含折边），如 40mm 收边条
    每条长  line_len_m  m    单条长度，超过板长自动提示接料
    条数    line_count  条   本次要多少条（"套数"固定为 1，不出现在界面）

【几何口径】
    每条折 2 道边（U 型/槽型线条）
    展开面积 = 摊平宽 × 每条长 × 条数
    延米数   = 条数 × 每条长 —— 报价页"延米价"模式直接按这个收钱
    不拼角焊接（对拼即可）；接料缝按焊缝口径另计（每处缝长 = 摊平宽）
"""
import math


def build(inp, pb):
    wd = float(inp.get("line_dev_w", 40.0))         # 摊平宽 mm
    L = float(inp.get("line_len_m", 3.0)) * 1000.0  # 每条长 mm
    n = int(inp.get("line_count", 1))               # 条数
    warnings = []

    if wd <= 0 or L <= 0 or n <= 0:
        raise ValueError("装饰线条的摊平宽 / 每条长 / 条数都必须大于 0")

    pieces = [{"name": "装饰线条", "n": n, "L": L, "Wd": wd, "bends": 2, "roll": 0}]

    # ---- 板幅校验：超宽拼板、超长接料（线条接长最常见） ----
    joints = 0
    max_w = max(pb["板幅"]["标准板宽mm"])
    max_l = max(pb["板幅"]["标准板长mm"])
    if wd > max_w:
        joints += math.ceil(wd / max_w) - 1
        warnings.append(f"摊平宽度 {wd:.0f}mm 超最大板宽 {max_w}mm，需拼板")
    if L > max_l:
        joints += n   # 每条都要接一处
        warnings.append(f"每条长 {L:.0f}mm 超最大板长 {max_l}mm，{n} 条均需接料（焊接接长后打磨）")

    area_m2 = n * L * wd / 1e6
    total_len_m = n * L / 1000.0
    bend_m = n * L * 2 / 1000.0      # 每条 2 道折边

    return {
        "pieces": pieces,
        "manufacture_type": "折弯成型",
        "area_m2": area_m2,
        "total_len_m": total_len_m,
        "bend_m": bend_m,
        "roll_m": 0.0,
        "bend_count_total": n * 2,
        "corner_weld_m": 0.0,
        "n_corners": 0,
        "dev_w": wd,
        "reveal": 0.0,
        "joints": joints,
        "warnings": warnings,
    }
