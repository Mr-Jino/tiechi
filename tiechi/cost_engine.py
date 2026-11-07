# -*- coding: utf-8 -*-
"""
cost_engine —— 成本计算引擎
==========================================

【总公式】
    总成本   = 材料费 + 折弯费 + 焊接费 + 表面费 + 包装费 + 物流费 + 安装费
    建议报价 = 总成本 × (1 + 成本加成率)     ← 默认口径（30% 加成 = 23.1% 实际利润率）
               或 总成本 / (1 - 销售利润率)  ← 若价表里"销售利润率"填了数
    物流费   = max(体积 × 体积单价, 重量 × 重量单价, 最低一票)   ← 泡货取大

【置信度】（confidence_level，V1 只有两档）
    低 = 用的还是出厂默认价表（数字是推导/占位值，只能看个大概）
    中 = 用户在"报价参数设置"里改过价表（更贴近自己工厂的实际成本）
    （"高" 留给做过实单回填校验、偏差 <5% 后给价表打 calibrated 标记的情况）

【本模块不持有任何单价】所有价格一律从 pricebook 查，改价只改 pricebook.json。
"""
import math

from . import geometry
from .pricebook import (load_pricebook, is_customized, thickness_key)

# 不锈钢密度：每平米、每毫米厚 ≈ 7.93 kg（算物流重量用）
_DENSITY_KG_PER_M2_MM = 7.93


def default_inputs():
    """默认输入 = UI 输入框/下拉框的初始值。前端直接读 ui_bridge.INPUT_SCHEMA。"""
    return {
        # ---- 尺寸 ----
        "opening_w": 900.0,        # 洞口宽 mm
        "opening_h": 2100.0,       # 洞口高 mm
        "wall_d": 240.0,           # 墙厚 mm（决定抱墙折边，价差主因）
        "quantity": 1,             # 套数（批量摊薄物流与差旅）
        # ---- 品类 ----
        "product": "门套",          # 门套 / 窗套 / 装饰线条（壁龛、屏风待接）
        "has_window_sill": False,  # 窗套是否含窗台板
        # ---- 装饰线条（仅 product=装饰线条 时生效）----
        "line_dev_w": 40.0,        # 摊平宽 mm（板料摊开总宽）
        "line_len_m": 3.0,         # 每条长 m
        "line_count": 10,          # 条数
        # ---- 材质 / 厚度 / 表面 / 造型 ----
        "material": "304",          # 201 / 304 / 316L（各自一张实价表）
        "thickness": 1.0,           # 0.6 / 0.8 / 1.0 / 1.2 mm
        "surface": "拉丝",          # 无处理2B/拉丝/磨砂/喷涂/镜面8K/镀钛
        "shape": "直边",            # 直边 / 上圆角 / 半圆拱 / 异形
        "arc_radius": 60.0,         # 上圆角半径 mm
        # ---- 工艺 ----
        "manufacture_type": "拼焊",  # 拼焊 / 整包
        "weld_mode": "拼角焊",       # 拼角焊 / 满焊无缝
        "wrap": "双包",              # 单包 / 双包
        "bend_count": 1,             # 折边道数：1=L型 2=U型（拼焊用）
        "face_width": 60.0,          # 套线可见面宽 mm
        "install_leg": 20.0,         # 安装折脚 mm
        "end_allowance": 15.0,       # 端头余量 mm
        "reveal_cap": 40.0,          # 单包抱墙深度上限 mm
        "head_extra_mode": "c",      # 横边加长：c=直角对接 / 2c=45°拼角
        "grooved": False,            # 刨槽工艺：折弯前开V槽，内角近直角（槽长≈折弯米数另计费）
        # ---- 商务 / 物流 ----
        "pricing_mode": "加成",       # 加成=成本×(1+加成率)；延米价=按目标延米售价直接报价
        "target_linear_price": 0.0,  # 延米价模式：目标售价 元/延米（老板脑中的市场锚）
        "include_install": True,     # 是否含安装
        "dest_city": "",             # 目的城市（自由填写，存档用，不参与计价）
        "freight_mode": "模板估算",   # 模板估算 / 手动填写
        "freight_manual": 0.0,       # 手动填写的整单运费（元）
        "same_city": True,           # 是否同城（异地加差旅）
    }


def calculate(inp=None, pb=None):
    """
    主入口：输入一个参数字典，返回完整报价结果。
    inp 缺省时用 default_inputs()（即"标准双包门套"的默认单）。
    """
    inp = {**default_inputs(), **(inp or {})}
    pb = pb or load_pricebook()          # 价表没传就现读 JSON
    q = inp["quantity"]
    t = inp["thickness"]
    material = inp["material"]

    # ---------- 0. 几何展开（米数、面积、拼板处数全在这算） ----------
    geo = geometry.build(inp["product"], inp, pb)
    warnings = list(geo["warnings"])

    # ---------- 1. 材料费 ----------
    tk = thickness_key(t)                                  # 1.0 → "1.0"
    try:
        price_per_m2 = pb["板材单价"][material][tk]          # 直接查实价表，不再乘系数
    except KeyError:
        raise ValueError(
            f"价表里查不到 {material} / {tk}mm 的板材单价，"
            f"请在 pricebook.json 的「板材单价」里补上这一行")
    wastage = pb["损耗率"][inp["shape"]] + (pb["损耗率"]["拼板附加"] if geo["joints"] else 0)
    net_area = geo["area_m2"] * q                          # 净展开面积（合计）
    mat_area = net_area * (1 + wastage)                    # 含损耗用料面积
    c_material = mat_area * price_per_m2

    # ---------- 2. 折弯费（元每米 / 元每道 两种计价方式，滚弯始终按米） ----------
    bend_cfg = pb["折弯"]
    bend_mode = bend_cfg.get("计价方式", "元每米")
    if bend_mode == "元每道":
        # 按道计价（行业常见 1~3 元/道）：直边折弯按道数，滚弯没有"道"的概念仍按米
        c_bend = (geo["bend_count_total"] * bend_cfg.get("直边折弯元每道", 0.0)
                  + geo["roll_m"] * bend_cfg.get("滚弯元每米", 0.0)) * q
    else:
        c_bend = (geo["bend_m"] * bend_cfg["直边折边元每米"]
                  + geo["roll_m"] * bend_cfg["滚弯元每米"]) * q

    # ---------- 2.5 刨槽费：槽长 ≈ 折弯米数，刨槽后内角近直角 ----------
    c_groove = 0.0
    if inp.get("grooved"):
        c_groove = geo["bend_m"] * bend_cfg.get("刨槽元每米", 0.0) * q

    # ---------- 3. 焊接费（按焊缝米数计价） ----------
    if inp["product"] == "装饰线条":
        # 线条不整条焊（对拼即可），只算接料缝：每处缝长 = 摊平宽
        weld_m = geo["corner_weld_m"] + geo["joints"] * geo["dev_w"] / 1000.0
    elif inp["weld_mode"] == "满焊无缝":
        weld_m = geo["total_len_m"]                        # 所有拼缝焊满：全部展开总长
    else:
        weld_m = geo["corner_weld_m"] + geo["joints"] * geo["dev_w"] / 1000.0
        # 拼角焊缝 + 接料缝（每处接料缝长度 = 摊平宽度）；整包的 corner_weld_m = 0
    c_weld = weld_m * pb["焊接"]["焊缝元每米"] * q \
        + geo["joints"] * pb["焊接"]["拼板接料元每处"] * q

    # ---------- 4. 表面处理费 ----------
    uplift = (pb["表面处理"]["弧形难度系数"]
              if inp["shape"] in ("上圆角", "半圆拱", "异形") else 1.0)
    c_surface = (net_area * pb["表面处理单价"][inp["surface"]]
                 * pb["表面处理"]["计价面数"] * uplift)

    # ---------- 5. 重量与打包体积（物流计费用） ----------
    weight_kg = mat_area * _DENSITY_KG_PER_M2_MM * t * 1.10     # +10% 辅料/焊材
    max_len_m = max(p["L"] for p in geo["pieces"]) / 1000.0
    flat_w_m = sum(p["n"] * p["Wd"] for p in geo["pieces"]) / 1000.0
    bundles = max(1, math.ceil(flat_w_m / pb["物流"]["打包捆宽米"]))
    volume_m3 = (bundles * pb["物流"]["打包捆宽米"] * pb["物流"]["打包捆高米"]
                 * max_len_m + 0.02) * q

    # ---------- 6. 包装费 ----------
    c_pack = (pb["包装"]["单套基础费"] + net_area / q * pb["包装"]["每平米护边费"]) * q

    # ---------- 7. 物流费 ----------
    # 两种口径：
    #   手动填写：客服按物流实际报价直接填整单运费（同城/异地都适用）
    #   模板估算：泡货按体积、重货按重量取大（单价在参数设置里改），再兜最低一票
    logistics = pb["物流"]
    vol_rate = logistics.get("体积元每立方米", 180.0)
    if isinstance(vol_rate, dict):          # 兼容旧价表的区间字典
        vol_rate = vol_rate.get("默认") or next(iter(vol_rate.values()))
    if inp.get("freight_mode") == "手动填写" and (inp.get("freight_manual") or 0) > 0:
        c_freight = float(inp["freight_manual"])
    else:
        c_freight = max(volume_m3 * vol_rate,
                        weight_kg * logistics.get("重量元每公斤", 1.0),
                        logistics.get("最低一票", 45.0))

    # ---------- 8. 安装费（装饰线条等没有安装价的品类自动为 0） ----------
    c_install = 0.0
    if inp["include_install"]:
        inst_unit = pb["安装"].get(inp["product"] + "元每套")
        if inst_unit:
            c_install = inst_unit * q
            if not inp["same_city"]:
                c_install += pb["安装"]["异地差旅元每套"] * q

    # ---------- 9. 延米数（先算：延米价定价模式要用） ----------
    # 口径：延米 = 客户口中的"米"
    #   门套无下框 = 宽 + 2×高；窗套四面合围 = 2×(宽 + 高)
    #   装饰线条 = 条数 × 每条长（按米卖的活儿，延米就是它本身）
    if inp["product"] == "装饰线条":
        linear_m = inp.get("line_count", 0) * inp.get("line_len_m", 0)
    elif inp["product"] == "窗套":
        linear_m = 2 * (inp["opening_w"] + inp["opening_h"]) / 1000.0
    else:
        linear_m = (inp["opening_w"] + 2 * inp["opening_h"]) / 1000.0

    # ---------- 10. 总成本 / 定价 / 报价 ----------
    total_cost = (c_material + c_bend + c_groove + c_weld + c_surface
                  + c_pack + c_freight + c_install)
    biz = pb["商务"]
    rt = biz["取整元"]
    pricing_mode = inp.get("pricing_mode", "加成")
    tlp = float(inp.get("target_linear_price") or 0)
    if pricing_mode == "延米价" and tlp > 0:
        # 延米价模式：老板拍板的市场锚（如"304拉丝门套=420/米"）
        # 报价 = 目标延米价 × 延米数，取整；毛利/利润率反推展示（不再乘加成率和税点，
        #       老板填的延米价就是他自己口径的最终价）
        raw = tlp * linear_m
        price_total = math.ceil(raw / rt) * rt if rt else raw
        if price_total < total_cost:
            warnings.append(
                f"延米价 ￥{tlp:g}/米 × 延米 {linear_m:.2f}m = ￥{price_total:g}，"
                f"低于总成本 ￥{total_cost:,.2f}，亏本单，请老板确认")
    else:
        if pricing_mode == "延米价" and tlp <= 0:
            warnings.append("选了延米价模式但目标延米价没填，已按成本加成口径计算")
            pricing_mode = "加成"
        if biz["销售利润率"]:
            suggested = total_cost / (1 - biz["销售利润率"])   # 利润率口径
        else:
            suggested = total_cost * (1 + biz["成本加成率"])   # 加成率口径（默认）
        suggested *= (1 + biz["税率"])
        price_total = math.ceil(suggested / rt) * rt if rt else suggested
    unit_cost = total_cost / q
    unit_price = price_total / q
    gross_unit = unit_price - unit_cost
    gross_total = price_total - total_cost

    # ---------- 10.5 延米参考价 ----------
    # 微信里客户必问"多少钱一米"。延米价 = 单套报价 ÷ 延米数，仅供客户横向比价。
    linear_price = round(unit_price / linear_m, 2) if linear_m > 0 else 0.0

    # ---------- 10.6 板材张数估算（备料/采购口径） ----------
    # 按最小标准板幅（1.22×2.44，最常用最便宜）整张估算，含损耗面积除以单张面积向上取整
    sheet_area = min(pb["板幅"]["标准板宽mm"]) * min(pb["板幅"]["标准板长mm"]) / 1e6
    sheets = math.ceil(mat_area / sheet_area) if mat_area > 0 else 0
    sheet_util = net_area / (sheets * sheet_area) if sheets else 0.0
    if sheets and sheet_util < 0.55:
        warnings.append(
            f"板材利用率约 {sheet_util * 100:.0f}%（{sheet_area:.2f}㎡/张 × {sheets} 张），"
            f"建议多件套裁下料提高利用率")

    # ---------- 10. 工艺告警（自动跑，不靠人记） ----------
    if material == "201" and inp["surface"] == "镀钛":
        warnings.append("201 镀钛附着力与耐蚀差，建议改 304")
    if inp["shape"] in ("上圆角", "半圆拱"):
        rmin = max(25.0, 20 * t)
        head_extra = inp["face_width"] if inp["head_extra_mode"] == "c" else 2 * inp["face_width"]
        r = (inp["arc_radius"] if inp["shape"] == "上圆角"
             else (inp["opening_w"] + head_extra) / 2.0)
        if r < rmin:
            warnings.append(f"弯曲半径 {r:.0f}mm 低于冷弯极限 {rmin:.0f}mm（≈20×板厚），会开裂")
    if inp["wrap"] == "单包" and inp["wall_d"] > inp["reveal_cap"] + 30:
        warnings.append("墙厚较大而单包抱边浅，另一面建议配收边条或改双包")
    if t <= 0.6 and geo["dev_w"] > 150:
        warnings.append("0.6mm + 宽套线平整度风险（波浪纹），建议 ≥0.8mm")
    if inp["surface"] == "镜面8K" and inp["shape"] in ("上圆角", "半圆拱"):
        warnings.append("滚弯后镜面需重新抛光，表面费已按难度系数上浮")

    # ---------- 11. 置信度 + 固定提示语 ----------
    # 高 = 价表做过实单回填校准（calibrated）
    # 中 = 用户改过价表（贴近自己工厂实际成本）
    # 低 = 还在用出厂默认价表（推导/占位值，只能看个大概）
    if pb.get("meta", {}).get("calibrated"):
        confidence = "高"
    elif is_customized(pb):
        confidence = "中"
    else:
        confidence = "低"

    # ---------- 12. 算式明细（老板面计算书：每一分钱怎么来的） ----------
    def _m(x):
        """金额/单价显示：去尾 0，最多两位小数"""
        return f"{x:,.2f}".rstrip("0").rstrip(".")

    if bend_mode == "元每道":
        bend_expr = f"折弯 {geo['bend_count_total']} 道 × {_m(bend_cfg.get('直边折弯元每道', 0))} 元/道"
    else:
        bend_expr = f"折弯 {geo['bend_m'] * q:,.2f}m × {_m(bend_cfg['直边折边元每米'])} 元/m"
    if geo["roll_m"] * q > 0:
        bend_expr += f" + 滚弯 {geo['roll_m'] * q:,.2f}m × {_m(bend_cfg.get('滚弯元每米', 0))} 元/m"

    weld_expr = f"焊缝 {weld_m * q:,.2f}m × {_m(pb['焊接']['焊缝元每米'])} 元/m"
    if geo["joints"]:
        weld_expr += f" + 接料 {geo['joints'] * q} 处 × {_m(pb['焊接']['拼板接料元每处'])} 元"

    surface_expr = (f"{net_area:,.2f}㎡ × {_m(pb['表面处理单价'][inp['surface']])} 元/㎡"
                    f" × {pb['表面处理']['计价面数']}面")
    if uplift != 1.0:
        surface_expr += f" × 弧形难度 {_m(uplift)}"

    if inp.get("freight_mode") == "手动填写" and (inp.get("freight_manual") or 0) > 0:
        freight_expr = "运费按物流实际报价手动填写"
    else:
        freight_expr = (f"max(体积 {volume_m3:,.2f}m³ × {_m(vol_rate)} 元/m³,"
                        f" 重量 {weight_kg:,.1f}kg × {_m(logistics.get('重量元每公斤', 1.0))} 元/kg,"
                        f" 最低一票 {_m(logistics.get('最低一票', 45.0))} 元)")

    install_expr = ""
    if c_install:
        install_expr = f"{q} 套 × {_m(pb['安装'].get(inp['product'] + '元每套', 0))} 元/套"
        if not inp["same_city"]:
            install_expr += f" + 差旅 {_m(pb['安装']['异地差旅元每套'])} 元/套"

    steps = [
        {"名称": "材料费",
         "算式": f"净面积 {net_area:,.2f}㎡ × (1 + 损耗 {wastage * 100:g}%) = 含损耗 {mat_area:,.2f}㎡"
                 f" × 板价 {_m(price_per_m2)} 元/㎡",
         "金额": round(c_material, 2)},
        {"名称": "折弯费", "算式": bend_expr, "金额": round(c_bend, 2)},
    ]
    if c_groove:
        steps.append({"名称": "刨槽费",
                      "算式": f"槽长 ≈ 折弯 {geo['bend_m'] * q:,.2f}m × {_m(bend_cfg.get('刨槽元每米', 0))} 元/m",
                      "金额": round(c_groove, 2)})
    steps.append({"名称": "焊接费", "算式": weld_expr, "金额": round(c_weld, 2)})
    steps.append({"名称": "表面处理费", "算式": surface_expr, "金额": round(c_surface, 2)})
    steps.append({"名称": "包装费",
                  "算式": f"基础 {_m(pb['包装']['单套基础费'])} 元/套 × {q} + 护边 {net_area:,.2f}㎡"
                          f" × {_m(pb['包装']['每平米护边费'])} 元/㎡",
                  "金额": round(c_pack, 2)})
    steps.append({"名称": "物流费", "算式": freight_expr, "金额": round(c_freight, 2)})
    if install_expr:
        steps.append({"名称": "安装费", "算式": install_expr, "金额": round(c_install, 2)})
    # 信息行（金额 None = 不是钱，是备料口径）
    steps.append({"名称": "板材张数",
                  "算式": f"含损耗 {mat_area:,.2f}㎡ ÷ 单张 {sheet_area:,.2f}㎡ ≈ {sheets} 张"
                          f"（利用率 {sheet_util * 100:.0f}%）",
                  "金额": None})
    if pricing_mode == "延米价" and tlp > 0:
        price_expr = (f"目标延米价 {_m(tlp)} 元/m × 延米数 {linear_m:,.2f}m"
                      + (f"，取整到 {_m(rt)} 元" if rt else ""))
    else:
        markup = (f"÷ (1 − 销售利润率 {_m(biz['销售利润率'])})"
                  if biz["销售利润率"] else f"× (1 + 成本加成 {_m(biz['成本加成率'])})")
        price_expr = (f"总成本 {_m(total_cost)} {markup}"
                      + (f" × (1 + 税点 {_m(biz['税率'])})" if biz["税率"] else "")
                      + (f"，取整到 {_m(rt)} 元" if rt else ""))
    steps.append({"名称": "建议报价", "算式": price_expr, "金额": round(price_total, 2)})

    return {
        "输入回显": inp,
        "定价模式": pricing_mode,
        "工艺口径": {"实际工艺": geo["manufacture_type"], "焊接口径": inp["weld_mode"],
                     "包法": inp["wrap"], "拼角处数": geo["n_corners"],
                     "焊缝米数": round(weld_m, 3),
                     "折弯计价": bend_mode, "折弯总道数": geo["bend_count_total"]},
        "件清单": [{"件名": p["name"], "条数": p["n"],
                   "单条长mm": round(p["L"], 1), "摊平宽mm": round(p["Wd"], 1),
                   "展开面积㎡": round(p["n"] * p["L"] * p["Wd"] / 1e6, 4),
                   "折边道数": p["bends"], "滚弯": bool(p["roll"])}
                  for p in geo["pieces"]],
        "几何": {"单套展开面积㎡": round(geo["area_m2"], 4),
                 "净展开面积㎡合计": round(net_area, 4),
                 "含损耗用料面积㎡合计": round(mat_area, 4),
                 "摊平宽度mm": round(geo["dev_w"], 1),
                 "抱墙折边mm": round(geo["reveal"], 1),
                 "单套展开总长m": round(geo["total_len_m"], 3),
                 "折弯米数m合计": round(geo["bend_m"] * q, 3),
                 "滚弯米数m合计": round(geo["roll_m"] * q, 3),
                 "损耗率": round(wastage, 3),
                 "重量kg合计": round(weight_kg, 2),
                 "打包体积m3合计": round(volume_m3, 3),
                 "拼板接料处数": geo["joints"],
                 "板材张数": sheets,
                 "板材利用率": round(sheet_util, 3)},
        "成本明细": {k: round(v, 2) for k, v in {
            "材料费": c_material, "折弯费": c_bend, "刨槽费": c_groove,
            "焊接费": c_weld, "表面处理费": c_surface, "包装费": c_pack,
            "物流费": c_freight, "安装费": c_install}.items()},
        "算式": steps,
        "套数": q,
        "总成本": round(total_cost, 2),
        "单套成本": round(unit_cost, 2),
        "建议报价合计": round(price_total, 2),
        "单套报价": round(unit_price, 2),
        "延米数": round(linear_m, 3),
        "延米参考价": linear_price,
        "单套毛利": round(gross_unit, 2),
        "毛利合计": round(gross_total, 2),
        "实际利润率": round(gross_total / price_total, 3) if price_total else 0,
        "confidence_level": confidence,
        "提示": "本报价为参考值，实际报价请根据工厂核算调整。",
        "告警": warnings,
    }
