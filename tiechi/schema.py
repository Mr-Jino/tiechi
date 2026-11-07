# -*- coding: utf-8 -*-
"""
schema —— 输入字段定义（给界面/CLI 生成表单用）
==============================================

一个字段一个 dict：key / label / type / unit / default / group / help / options。
写界面的照着渲染就行，写脚本的照着拼参数就行 —— 文档和代码不会各说一套。

    from tiechi.schema import INPUT_SCHEMA, defaults
    defaults()        # {'opening_w': 900.0, ...}
"""
from .cost_engine import default_inputs

INPUT_SCHEMA = [
    # ---- 尺寸 ----
    {"key": "opening_w", "label": "洞口宽", "type": "number", "unit": "mm", "default": 900,
     "group": "尺寸", "help": "墙上开口的净宽（不含套线），下料尺寸的源头，量错就废"},
    {"key": "opening_h", "label": "洞口高", "type": "number", "unit": "mm", "default": 2100,
     "group": "尺寸", "help": "地面到洞口顶的净高；半圆拱造型填含拱的总高"},
    {"key": "wall_d", "label": "墙厚", "type": "number", "unit": "mm", "default": 240,
     "group": "尺寸", "help": "决定抱墙折边深度，是价差主因，填错包不上墙（常见 120/200/240/370）"},
    {"key": "quantity", "label": "套数", "type": "number", "unit": "套", "default": 1,
     "group": "尺寸", "help": "本次做几套；批量会摊薄物流和差旅"},

    # ---- 品类 ----
    {"key": "product", "label": "品类", "type": "select",
     "options": ["门套", "窗套", "装饰线条"], "default": "门套", "group": "品类",
     "help": "门套包门洞、窗套包窗洞（可带窗台板）、装饰线条=收边条/嵌条按米卖"},
    {"key": "has_window_sill", "label": "含窗台板", "type": "switch", "default": False,
     "group": "品类", "help": "窗套带窗台板（两侧耳朵、前出檐、挡水沿），费用单独算"},

    # ---- 装饰线条专用 ----
    {"key": "line_dev_w", "label": "摊平宽", "type": "number", "unit": "mm", "default": 40,
     "group": "尺寸", "help": "板料完全摊开的总宽（含折边），比成品看面宽"},
    {"key": "line_len_m", "label": "每条长", "type": "number", "unit": "m", "default": 3,
     "group": "尺寸", "help": "单条长度；超过板料长度会自动提示接料"},
    {"key": "line_count", "label": "条数", "type": "number", "unit": "条", "default": 10,
     "group": "尺寸", "help": "本次要多少条；总延米=条数×每条长"},

    # ---- 材料 ----
    {"key": "material", "label": "材质", "type": "select",
     "options": ["201", "304", "316L"], "default": "304", "group": "材料",
     "help": "201 易锈（室内干燥处）、304 常规首选、316L 耐蚀（户外/沿海）；各材质各自实价表"},
    {"key": "thickness", "label": "板厚", "type": "select",
     "options": [0.6, 0.8, 1.0, 1.2, 1.5], "default": 1.0, "group": "材料",
     "help": "越厚越贵越挺；0.6 做宽套线容易出波浪纹，引擎会自动提醒"},
    {"key": "surface", "label": "表面处理", "type": "select",
     "options": ["无处理2B", "拉丝", "磨砂", "喷涂", "镜面8K", "镀钛"], "default": "拉丝",
     "group": "材料", "help": "2B 最省、拉丝最常用、镜面/镀钛偏高端（黑钛/灰钛/玫瑰金同价）"},

    # ---- 工艺 ----
    {"key": "manufacture_type", "label": "制造工艺", "type": "select",
     "options": ["拼焊", "整包"], "default": "拼焊", "group": "工艺",
     "help": "拼焊=分件下料拼角焊；整包=一块长板折成 П 形整圈包住洞口（只支持直边）"},
    {"key": "weld_mode", "label": "焊接口径", "type": "select",
     "options": ["拼角焊", "满焊无缝"], "default": "拼角焊", "group": "工艺",
     "help": "拼角焊=只焊拼角；满焊无缝=所有拼缝焊满再打磨到看不出（贵，焊缝=全部展开总长）"},
    {"key": "wrap", "label": "包法", "type": "select",
     "options": ["单包", "双包"], "default": "双包", "group": "工艺",
     "help": "单包=只包洞口一面；双包=里外两面都包，展开面积翻倍"},
    {"key": "shape", "label": "造型", "type": "select",
     "options": ["直边", "上圆角", "半圆拱"], "default": "直边", "group": "工艺",
     "help": "直边最常规；上圆角需填半径；半圆拱=拱形顶。造型越复杂损耗越高"},
    {"key": "arc_radius", "label": "圆角半径", "type": "number", "unit": "mm", "default": 60,
     "group": "工艺", "help": "上圆角的弧度半径；低于 20×板厚 会开裂，引擎自动拦"},
    {"key": "grooved", "label": "刨槽工艺", "type": "switch", "default": False,
     "group": "工艺", "help": "折弯前开 V 槽，内角近直角、拼角挺直（电梯门套/精装常用），槽费按槽长另计"},

    # ---- 高级 ----
    {"key": "face_width", "label": "套线可见面宽", "type": "number", "unit": "mm", "default": 60,
     "group": "高级", "help": "套线正面的看面宽（客户常叫包边/翻边），常用 26/40/60/80"},
    {"key": "bend_count", "label": "折边道数", "type": "select", "options": [1, 2], "default": 1,
     "group": "高级", "help": "1=单折（L 型断面）；2=双折（U 型）"},
    {"key": "install_leg", "label": "安装折脚", "type": "number", "unit": "mm", "default": 20,
     "group": "高级", "help": "背后打胶/卡装用的折边宽度，影响展开面积"},
    {"key": "end_allowance", "label": "端头余量", "type": "number", "unit": "mm", "default": 15,
     "group": "高级", "help": "两端预留的裁切搭接余量，防安装时尺寸不够"},
    {"key": "reveal_cap", "label": "单包抱墙上限", "type": "number", "unit": "mm", "default": 40,
     "group": "高级", "help": "单包时抱墙折边的最大深度；墙厚超出太多会提醒改双包"},
    {"key": "head_extra_mode", "label": "横边加长口径", "type": "select",
     "options": ["c", "2c"], "default": "c", "group": "高级",
     "help": "c=横边按套线宽直角对接；2c=两端各加长一个套线宽（45° 拼角）"},

    # ---- 商务 / 物流 ----
    {"key": "pricing_mode", "label": "定价模式", "type": "select",
     "options": ["加成", "延米价"], "default": "加成", "group": "商务",
     "help": "加成=成本×(1+加成率)；延米价=按行情填多少钱一米，反推毛利"},
    {"key": "target_linear_price", "label": "目标延米价", "type": "number", "unit": "元/米",
     "default": 0, "group": "商务", "help": "延米价模式的市场锚（如 304 拉丝门套 420/米）；低于成本会告警"},
    {"key": "include_install", "label": "含安装", "type": "switch", "default": True,
     "group": "商务", "help": "含安装=报给客户的价含安装费；不含=只报出厂价"},
    {"key": "dest_city", "label": "目的城市", "type": "text", "default": "",
     "group": "商务", "help": "自由填写，存档用，不参与计价"},
    {"key": "freight_mode", "label": "运费方式", "type": "select",
     "options": ["模板估算", "手动填写"], "default": "模板估算", "group": "商务",
     "help": "模板估算=体积/重量取大自动算；手动=按物流报价直接填"},
    {"key": "freight_manual", "label": "运费（元）", "type": "number", "unit": "元", "default": 0,
     "group": "商务", "help": "手动模式的整单运费"},
    {"key": "same_city", "label": "同城安装", "type": "switch", "default": True,
     "group": "商务", "help": "非同城则每套加异地差旅"},
]

OUTPUT_DISCLAIMER = "本报价为参考值，实际报价请根据工厂核算调整。"


def defaults():
    """所有字段的默认值（不含 schema 里的界面专用键）。"""
    return default_inputs()


def by_group(group):
    """取某一组字段，写界面时按组渲染。"""
    return [f for f in INPUT_SCHEMA if f["group"] == group]


def as_dict():
    """{key: field} 便于按 key 查定义。"""
    return {f["key"]: f for f in INPUT_SCHEMA}
