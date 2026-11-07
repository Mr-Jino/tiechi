# -*- coding: utf-8 -*-
"""
geometry —— 展开几何（按品类分文件）
====================================

【这个包是干什么的】
    把"尺寸 + 工艺"翻译成"要用多少板、折多少弯、焊多少米"。
    它只管几何和米数，不算钱 —— 算钱是 cost_engine 的事。

【统一的输出格式】（每个品类模块的 build() 都返回这个结构）
    pieces        件清单：每条料的名称/条数/长度/摊平宽度/折边道数/是否滚弯
                  —— 这是给车间下料用的，也是给客户看"钱花在哪"用的
    area_m2       单套净展开面积（㎡），双包已翻倍
    total_len_m   单套展开总长（米）
    bend_m        单套直边折弯米数（米）—— 折边道数 × 长度 累加
    roll_m        单套滚弯米数（米）—— 弧形/拱形单独计
    corner_weld_m 单套拼角焊缝米数（米）—— 拼焊才有，整包为 0
    n_corners     拼角处数（门套 2 处、窗套 4 处）
    dev_w         摊平宽度（mm）
    reveal        抱墙折边深度（mm）
    joints        拼板/接料处数（板幅超限时产生）
    warnings      工艺告警列表

【加一个品类】
    1. 在本目录新建 foo.py，实现 build(inp, pb) 返回上面那套键；
    2. 在下面 CATEGORY_MODULES 里加一行 "品类名": foo。
    其余代码一行不用改 —— 壁龛、屏风、栏杆、铝板吊顶都按这个方式接。
"""
from . import door_window
from . import lines

CATEGORY_MODULES = {
    "门套": door_window,
    "窗套": door_window,   # 门套/窗套共用一套几何逻辑（窗套多一条下横边+可选窗台板）
    "装饰线条": lines,      # 收边条/嵌条/框线，按米卖的万能项
}


def build(product, inp, pb):
    """按品类分发到对应模块。品类没注册会明确报错，而不是算出错误数字。"""
    mod = CATEGORY_MODULES.get(product)
    if mod is None:
        raise ValueError(
            f"品类「{product}」还没有几何模块。已支持：{list(CATEGORY_MODULES)}。"
            f"请在 tiechi/geometry/ 下新增模块并注册到 CATEGORY_MODULES。")
    return mod.build(inp, pb)
