# -*- coding: utf-8 -*-
"""
door_window —— 门套 / 窗套展开几何（核心几何）
==========================================================

【两种制造工艺】（manufacture_type）
    拼焊：立边、横边分别下料折弯，到现场/车间拼角焊接。
          —— 件多、焊缝多，但单件短，不挑板幅。
    整包：一块长板连续折弯成"П"形整圈包住洞口（单面包），
          双包 = 里外各一块。
          —— 无拼角焊缝、外观整体感好，但板要够长（基本必接料）。

【两种包法】（wrap）
    单包：一面包。抱墙折边深度 = min(墙厚, reveal_cap=40mm)。
    双包：两面包。每面各抱满墙厚 D，面积整体翻倍。

【公式速查】
    拼焊摊平宽度 Wd = 可见面宽c + 折边道数k × 抱墙a + 安装折脚 − k×0.5×板厚
    整包摊平宽度 Wd = c + 墙厚D + 安装折脚 − 2×0.5×板厚   （按拍板口径，不是 2c+D）
    整包板长 L      = 2H + W + 2D + 2×端头余量            （单面包；双包 ×2 块）

【焊缝米数口径】（按米计价，不再是按处）
    拼角焊（默认）：焊缝 = 拼角处数 × 摊平宽度 + 接料缝（每处也是摊平宽度长）
    整包：无拼角焊缝，只有接料缝
    满焊无缝（高端单）：焊缝 = 全部展开总长（把所有拼缝焊满后打磨到看不出）
"""
import math

from ..pricebook import thickness_key


# ---------------------------------------------------------------------
# 第一步：算摊平宽度（一条板子摊开后的宽度，单位 mm）
# ---------------------------------------------------------------------
def _plain_deduction(inp, pb, t):
    """常规（不刨槽）每道折弯的展开扣减 mm。
    优先级：价表「折弯扣减mm按板厚」指定该板厚 > 指定"默认" > 老口径 折弯扣减系数×板厚。
    价表没配按板厚扣减时走老口径 —— 老报价数字一个不变。"""
    tmap = pb["折弯"].get("折弯扣减mm按板厚") or {}
    v = tmap.get(thickness_key(t), tmap.get("默认"))
    return float(v) if v is not None else pb["折弯"]["折弯扣减系数"] * t


def _developed_width(inp, pb, ded):
    """ded = 每道折弯的展开扣减 mm（刨槽折弯传 0：内角近直角几乎不占料）。"""
    c = inp["face_width"]            # 套线可见面宽（正面看得到的宽度）

    if inp["manufacture_type"] == "整包":
        # 拍板口径：整包摊平宽度 = 可见面c + 墙厚D + 安装折脚 − 2道折弯扣减（不是 2c+D）
        a = inp["wall_d"]            # 抱墙 = 整墙厚
        k = 2                        # 剖面折两道（正面→墙厚面→折脚）
        wd = c + a + inp["install_leg"] - k * ded
    else:
        k = inp["bend_count"]        # 拼焊：1=L型，2=U型，由用户选
        if inp["wrap"] == "双包":
            a = inp["wall_d"]        # 双包拼焊：每面各抱满墙厚
        else:
            a = min(inp["wall_d"], inp["reveal_cap"])   # 单包：抱墙深度封顶 40mm
        wd = c + k * a + inp["install_leg"] - k * ded
    return wd, a, k


# ---------------------------------------------------------------------
# 第二步：生成件清单（pieces）
# ---------------------------------------------------------------------
def build(inp, pb):
    W, H, D = inp["opening_w"], inp["opening_h"], inp["wall_d"]
    c, t = inp["face_width"], inp["thickness"]
    ea = inp["end_allowance"]        # 端头裁切/搭接余量
    shape = inp["shape"]             # 直边 / 上圆角 / 半圆拱 / 异形
    faces = 2 if inp["wrap"] == "双包" else 1   # 双包 = 两块（里外各一）
    warnings = []
    pieces = []

    # 整包只支持直边：弧形要滚弯，整板连续折弯做不了，自动降级为拼焊并提醒
    mode = inp["manufacture_type"]
    if mode == "整包" and shape != "直边":
        mode = "拼焊"
        warnings.append("整包工艺只支持直边；当前造型为" + shape + "，已自动按拼焊计算，请人工确认")

    wd, a, k = _developed_width(inp, pb, 0.0 if inp.get("grooved") else _plain_deduction(inp, pb, t))
    if inp.get("grooved"):
        # 刨槽只作用于直边折弯件；滚弯/弧形件开不了槽，摊平宽度仍按常规扣减
        wd_roll = _developed_width(inp, pb, _plain_deduction(inp, pb, t))[0]
        warnings.append("刨槽折弯：内角近直角（R≈0），拼角外观更挺直；注意槽位与折刀对位")
        if shape != "直边":
            warnings.append("刨槽只对直边折弯件有效；滚弯/弧形件无法开槽，已按常规扣减下料")
    else:
        wd_roll = wd
    head_extra = c if inp["head_extra_mode"] == "c" else 2 * c   # 横边加长：直角对接=c，45°拼角=2c

    if mode == "整包":
        # ---- 整包：每面一块"П"形长板 ----
        L = 2 * H + W + 2 * D + 2 * ea
        pieces.append({"name": "整包板", "n": faces, "L": L, "Wd": wd,
                       "bends": 0, "roll": 0, "profile_folds": 2})
        n_corners = 0                # 整包没有拼角焊缝
    else:
        # ---- 拼焊：立边 + 横边分开下料 ----
        if shape == "半圆拱":
            R = (W + head_extra) / 2.0              # 拱半径
            L_side = max(H - R, 1.0) + ea           # 立边只做到起拱线
        else:
            L_side = H + c + ea                     # 立边 = 洞高 + 套线宽 + 余量
            if shape == "上圆角":
                L_side -= inp["arc_radius"]         # 圆角吃掉立边顶上一段直线
        pieces.append({"name": "立边", "n": 2 * faces, "L": L_side, "Wd": wd,
                       "bends": k, "roll": 0})

        n_head = 2 if inp["product"] == "窗套" else 1   # 窗套上下各一条横边
        if shape == "半圆拱":
            arc = math.pi * R                        # 半拱中心线弧长
            pieces.append({"name": "拱顶弧边", "n": faces, "L": arc, "Wd": wd_roll,
                           "bends": 0, "roll": 1})
        elif shape == "上圆角":
            R = inp["arc_radius"]
            pieces.append({"name": "顶横边", "n": n_head * faces,
                           "L": (W + head_extra - 2 * R) + ea, "Wd": wd,
                           "bends": k, "roll": 0})
            pieces.append({"name": "顶部圆角弧", "n": 2 * faces,
                           "L": math.pi / 2 * R, "Wd": wd_roll, "bends": 0, "roll": 1})
        else:
            pieces.append({"name": "顶横边", "n": n_head * faces,
                           "L": (W + head_extra) + ea, "Wd": wd, "bends": k, "roll": 0})
        n_corners = 2 if inp["product"] == "门套" else 4   # 拼角焊缝处数

    # ---- 窗台板（仅窗套可选）：含两侧耳朵、前出檐，前挡水沿单独一条 ----
    if inp["product"] == "窗套" and inp["has_window_sill"]:
        ear, nose, drip = 30.0, 25.0, 20.0
        pieces.append({"name": "窗台板", "n": 1, "L": W + 2 * ear,
                       "Wd": D + nose, "bends": 1, "roll": 0})
        pieces.append({"name": "窗台前沿", "n": 1, "L": W + 2 * ear,
                       "Wd": drip, "bends": 1, "roll": 0})

    # -----------------------------------------------------------------
    # 第三步：汇总米数、面积
    # -----------------------------------------------------------------
    total_len_m = sum(p["n"] * p["L"] for p in pieces) / 1000.0
    area_m2 = sum(p["n"] * p["L"] * p["Wd"] for p in pieces) / 1e6

    # 折弯米数：
    #   拼焊件：每条料沿长度方向折 k 道 → 长度 × 折边道数
    #   整包板：两道纵向通长折（正面→墙厚→折脚）+ 顶部两个转角折（每个转角折的长度=摊平宽度）
    bend_m = 0.0
    for p in pieces:
        if p.get("profile_folds"):
            bend_m += p["n"] * (p["profile_folds"] * p["L"] + 2 * p["Wd"]) / 1000.0
        else:
            bend_m += p["n"] * p["L"] * p["bends"] / 1000.0

    roll_m = sum(p["n"] * p["L"] * p["roll"] for p in pieces) / 1000.0
    corner_weld_m = n_corners * wd / 1000.0    # 每处拼角的焊缝长度 = 摊平宽度

    # 折弯总道数（按道计价用）：普通件 = 条数×折边道数；整包板 = 2道通长折 + 2道端头折
    bend_count_total = sum(
        p["n"] * (p["profile_folds"] + 2) if p.get("profile_folds") else p["n"] * p["bends"]
        for p in pieces)

    # -----------------------------------------------------------------
    # 第四步：板幅校验（超宽要拼板、超长要接料，都会加钱加损耗）
    # -----------------------------------------------------------------
    joints = 0
    max_w = max(pb["板幅"]["标准板宽mm"])
    max_l = max(pb["板幅"]["标准板长mm"])
    if wd > max_w:
        joints += math.ceil(wd / max_w) - 1
        warnings.append(f"摊平宽度 {wd:.0f}mm 超最大板宽 {max_w}mm，需拼板")
    for p in pieces:
        if p["L"] > max_l:
            joints += 1
            warnings.append(f"{p['name']} 长 {p['L']:.0f}mm 超最大板长 {max_l}mm，需接料")

    return {
        "pieces": pieces,
        "manufacture_type": mode,        # 实际采用的工艺（可能从整包降级为拼焊）
        "area_m2": area_m2,
        "total_len_m": total_len_m,
        "bend_m": bend_m,
        "roll_m": roll_m,
        "bend_count_total": bend_count_total,
        "corner_weld_m": corner_weld_m,
        "n_corners": n_corners,
        "dev_w": wd,
        "reveal": a,
        "joints": joints,
        "warnings": warnings,
    }
