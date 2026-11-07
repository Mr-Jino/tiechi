# -*- coding: utf-8 -*-
"""
pricebook —— 单价表（引擎的"价格参数中心"）
================================================

【这个文件是干什么的】
    所有跟"钱"有关的参数集中在这里，一处改、处处生效。
    程序启动时读取外部 pricebook.json；文件不存在就用本文件的
    DEFAULT_PRICEBOOK 自动生成一份。

【三条铁律】
    1. 绝不在计算代码里写死任何单价 —— 计算模块只来这里查价。
    2. 价表按"材质 × 板厚"直接建实价二维表（元/㎡），
       不用"基准价 × 材质系数"的乘法（系数会漂移，老版本踩过坑）。
    3. 用户改过任何单价 → meta.modified 自动变 true →
       报价置信度从"低"升为"中"。

【文件放哪】
    1) 环境变量 TIECHI_PRICEBOOK 指向的路径；
    2) 当前目录下的 pricebook.json；
    3) 都没有 → 写到家目录 ~/.tiechi/pricebook.json。
    想给不同客户/工厂各存一套价，就用环境变量切。
"""
import copy
import json
import os
from pathlib import Path

# =====================================================================
# 出厂默认价表（示例值，可直接改；带 ★ 的是推导/占位值）
# 这些数字是 2026 年东北市场的量级参考，用之前请按自己工厂的
# 实际采购价 + 加工费回填 —— 引擎只保证算法对，不保证价格对。
# =====================================================================
DEFAULT_PRICEBOOK = {
    # ---------------- meta：价表自身的状态标记 ----------------
    "meta": {
        "version": "1.0",           # 价表版本号
        "modified": False,          # 用户是否手动改过价（改过→置信度"中"）
        "calibrated": False,        # 是否用实单回填校验过（校准过→置信度"高"）
        "calibrated_at": None,      # 上次校准时间
        "note": "所有单价均可修改；带★的为推导参考值，请按工厂实际成本回填。",
    },

    # ---------------- 工厂信息：报价单抬头用（改成你自己的） ----------------
    "工厂信息": {
        "名称": "示例不锈钢加工厂",
        "电话": "",
        "地址": "",
        "备注": "不锈钢定制 · 门套/窗套/壁龛/屏风/垭口套",
        "生产周期": "3-5天",
    },

    # ---------------- 板材单价：材质 × 板厚 → 元/㎡展开（含税、含开料剪板） ----------------
    # 注意：这是"实价表"，不同材质各一张，不乘任何系数。
    "板材单价": {
        "201":  {"0.6": 105.0, "0.8": 118.0, "1.0": 130.0, "1.2": 155.0, "1.5": 190.0},
        # 304：按 304/2B 约 15190 元/吨（1.0mm≈122.5 元/㎡ 纯板）
        # 加开料剪板约 50 元/㎡ 推导 ★；1.5 为外推值 ★
        "304":  {"0.6": 123.5, "0.8": 148.0, "1.0": 172.5, "1.2": 197.0, "1.5": 234.0},
        # 316L：沿海/化工场景，按 304 上浮约 30% 推导 ★；1.5 为外推值 ★
        "316L": {"0.6": 160.0, "0.8": 195.0, "1.0": 225.0, "1.2": 255.0, "1.5": 295.0},
    },

    # ---------------- 表面处理单价：元/㎡（基准为 2B 工业面，这里全是"增量加工费"） ----------------
    "表面处理单价": {
        "无处理2B": 0.0,    # 就用原板面，不加钱
        "拉丝": 28.0,
        "磨砂": 32.0,
        "喷涂": 40.0,
        "镜面8K": 48.0,
        "镀钛": 118.0,      # 黑钛/灰钛/玫瑰金/香槟金等彩色镀钛同价
    },
    "表面处理": {
        "计价面数": 1,          # 1=只算外露面；2=里外两面都做表面
        "弧形难度系数": 1.15,    # 弧形/异形滚弯后表面要返工，费用上浮 15%
    },

    # ---------------- 折弯：按米或按道计价 + 刨槽 ----------------
    "折弯": {
        "直边折边元每米": 14.0,   # 1.0mm 板市场价 12~16 元/米，取中值
        "滚弯元每米": 45.0,       # 弧形/拱形走滚弯机，比直边折弯贵
        "加强筋元每米": 18.0,     # 异形件背面加筋防变形（预留）
        "折弯扣减系数": 0.5,      # 每道折弯展开长度少半个板厚（板料中性轴），数学修正用
        # ---- 缺键自动迁移，老价表数字不受影响 ----
        "计价方式": "元每米",      # 元每米=按折弯米数计价（默认，老口径）｜元每道=按折弯道数计价
        "直边折弯元每道": 2.0,     # 按道计价时的单价（行业常见 1~3 元/道，滚弯仍按米）
        "刨槽元每米": 12.0,       # 刨 V 槽单价；槽长 ≈ 折弯米数，刨槽后内角近直角
        "折弯扣减mm按板厚": {},    # 指定板厚的每道扣减 mm（键如"1.0"或"默认"）；留空=用 折弯扣减系数×板厚
    },

    # ---------------- 焊接：按米计价（50 元/米含人工、设备、耗材、打磨） ----------------
    "焊接": {
        "焊缝元每米": 50.0,       # 304 氩弧焊市场价
        "拼板接料元每处": 35.0,   # 板幅不够需要拼接时，每处的额外加工费（焊缝米数另算）
    },

    # ---------------- 损耗率：开料/折弯/滚弯废料比例 ----------------
    "损耗率": {
        "直边": 0.08,
        "上圆角": 0.12,
        "半圆拱": 0.15,
        "异形": 0.15,
        "拼板附加": 0.03,        # 需要拼板时，额外加 3% 损耗
    },

    # ---------------- 包装 ----------------
    "包装": {
        "单套基础费": 60.0,       # 木架/纸箱
        "每平米护边费": 18.0,     # 珍珠棉、护角、护边（按展开面积）
    },

    # ---------------- 物流：泡货按体积、重货按重量，取大 ----------------
    "物流": {
        "体积元每立方米": 180.0,    # 泡货单价（专线零担 165~199 取中值 ★）
        "重量元每公斤": 1.0,        # 重货单价（0.92~1.22 取中值 ★）
        "最低一票": 45.0,           # 兜底：最低一票
        "打包捆宽米": 0.35,         # 打包体积估算：每捆宽
        "打包捆高米": 0.14,         # 打包体积估算：每捆高
        # 手动填运费不走这里：freight_mode="手动填写" 直接填整单金额
    },

    # ---------------- 板幅：标准不锈钢板尺寸（超了就要拼板/接料） ----------------
    "板幅": {
        "标准板宽mm": [1220, 1500],
        "标准板长mm": [2440, 3000],
    },

    # ---------------- 安装 ----------------
    "安装": {
        "门套元每套": 150.0,
        "窗套元每套": 120.0,
        "异地差旅元每套": 300.0,  # 非同城上门安装的差旅补贴
    },

    # ---------------- 商务 ----------------
    "商务": {
        "成本加成率": 0.30,       # 报价 = 成本 × (1 + 30%)。注意：这是"加成率"，
                                  # 对应实际销售利润率只有 23.1%（0.3/1.3）
        "销售利润率": None,       # 想用"利润率"口径就填 0.30，报价 = 成本 / (1-0.30)
        "税率": 0.00,             # 开票加点
        "取整元": 1.0,            # 报价取整到元；改成 5 或 10 就是取整到 5/10 元
        "报价有效期天": 7,         # 报价单锁定后有效天数（钢价周波动，行业常规 7 天）
    },
}


# =====================================================================
# 路径与读写
# =====================================================================
def default_path() -> Path:
    """价表路径：环境变量 > 当前目录 > 家目录。"""
    env = os.environ.get("TIECHI_PRICEBOOK")
    if env:
        return Path(env).expanduser()
    local = Path("pricebook.json")
    if local.exists():
        return local.resolve()
    return Path.home() / ".tiechi" / "pricebook.json"


def load_pricebook(path=None):
    """
    读取价表。不存在时用出厂默认值生成一份。

    已存在的旧价表会跟出厂默认值做"合并升级"：
        用户改过的数字保留，代码新增的参数组自动补上 —— 升级不丢配置。
    """
    path = Path(path) if path else default_path()
    if not path.exists():
        save_pricebook(DEFAULT_PRICEBOOK, path, mark_modified=False)
        return copy.deepcopy(DEFAULT_PRICEBOOK)
    with open(path, "r", encoding="utf-8") as f:
        file_data = json.load(f)
    merged = _deep_merge(copy.deepcopy(DEFAULT_PRICEBOOK), file_data)  # 文件里的值优先
    if merged != file_data:          # 有新增键 → 落盘
        save_pricebook(merged, path, mark_modified=False)
    return merged


def save_pricebook(pb, path=None, mark_modified=False):
    """保存价表。mark_modified=True 时把 meta.modified 置 true（置信度→中）。"""
    path = Path(path) if path else default_path()
    data = copy.deepcopy(pb)
    if mark_modified:
        data.setdefault("meta", {})["modified"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _deep_merge(base, patch):
    """把 patch 里的修改合并进 base（只动 patch 里出现的键，其余保留）。"""
    for key, val in patch.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
    return base


def update_price_params(changes, path=None):
    """
    改单价。changes 不用全给，给哪个改哪个：
        {"板材单价": {"304": {"1.0": 168.0}}, "焊接": {"焊缝元每米": 55.0}}
    改完自动保存，并把 meta.modified 置 true（之后报价置信度显示"中"）。
    """
    pb = load_pricebook(path)
    _deep_merge(pb, changes)
    save_pricebook(pb, path, mark_modified=True)
    return pb


def reset_pricebook(path=None):
    """恢复出厂默认价表（置信度回到"低"）。"""
    save_pricebook(DEFAULT_PRICEBOOK, path, mark_modified=False)
    return copy.deepcopy(DEFAULT_PRICEBOOK)


def calibrate_pricebook(path=None):
    """
    标记"价表已用实单校准过"。校准过的价表 → 之后所有报价置信度显示"高"。
    """
    pb = load_pricebook(path)
    pb["meta"]["calibrated"] = True
    pb["meta"]["calibrated_at"] = _now_str()
    save_pricebook(pb, path, mark_modified=False)
    return pb


def _now_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def is_customized(pb):
    """价表是否被用户改过（决定置信度：改过=中，没改过=低）。"""
    return bool(pb.get("meta", {}).get("modified", False))


def thickness_key(t):
    """板厚转价表键名：1.0 → '1.0'，0.6 → '0.6'（统一格式，防止查不到价）。"""
    return str(float(t))
