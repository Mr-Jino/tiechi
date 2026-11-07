# -*- coding: utf-8 -*-
"""
cli —— 命令行入口
=================

    tiechi quote --w 1000 --h 2100 --d 240 --surface 拉丝
    tiechi quote --preset 电梯门套 --detail
    tiechi quote --set pricing_mode=延米价 --set target_linear_price=420
    tiechi cases                 # 跑内置样例单，看引擎是否正常
    tiechi book show             # 打印当前价表路径与关键单价
    tiechi book set 焊接.焊缝元每米=55
    tiechi book reset
"""
import argparse
import json
import sys
import unicodedata

from .cost_engine import calculate, default_inputs
from .pricebook import load_pricebook, reset_pricebook, default_path, update_price_params
from .schema import INPUT_SCHEMA, OUTPUT_DISCLAIMER

# 控制台中文：Windows 默认 cp936 打不全，能改就改
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


PRESETS = {
    "标准门套": {},
    "电梯门套": {"opening_w": 1000, "opening_h": 2100, "face_width": 120,
                 "thickness": 1.2, "material": "304", "surface": "拉丝"},
    "整包窗套": {"product": "窗套", "manufacture_type": "整包", "wrap": "单包",
                 "opening_w": 1500, "opening_h": 1600, "wall_d": 200},
    "装饰线条": {"product": "装饰线条", "line_dev_w": 40, "line_len_m": 3, "line_count": 10},
}


def _money(x):
    return f"￥{x:,.2f}"


def _w(s):
    """显示宽度：中日韩全角字符算 2 列，否则表格永远对不齐。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def _pad(s, width, right=False):
    """按显示宽度补空格。right=True 右对齐。"""
    gap = max(0, width - _w(s))
    return " " * gap + str(s) if right else str(s) + " " * gap


def _set_kv(pairs, inp):
    """--set a=1 --set b.c=2 → 支持点号路径写进参数字典。"""
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"--set 需要 key=value 形式，收到：{p}")
        k, v = p.split("=", 1)
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            pass                      # 不是数字/布尔就按字符串
        inp[k] = v
    return inp


def cmd_quote(args):
    inp = dict(default_inputs())
    inp.update(PRESETS.get(args.preset, {}))
    if args.preset and args.preset not in PRESETS:
        raise SystemExit(f"没有这个预设：{args.preset}，可用：{', '.join(PRESETS)}")

    flag_map = {
        "w": "opening_w", "h": "opening_h", "d": "wall_d", "qty": "quantity",
        "product": "product", "material": "material", "thickness": "thickness",
        "surface": "surface", "wrap": "wrap", "shape": "shape",
        "face": "face_width", "arc": "arc_radius",
    }
    for flag, key in flag_map.items():
        val = getattr(args, flag, None)
        if val is not None:
            inp[key] = val
    if args.process:
        # "拼焊" / "整包" / "满焊" → 两个引擎参数
        if args.process == "满焊":
            inp["manufacture_type"], inp["weld_mode"] = "拼焊", "满焊无缝"
        elif args.process == "整包":
            inp["manufacture_type"] = "整包"
        else:
            inp["manufacture_type"] = "拼焊"
    _set_kv(args.set, inp)

    r = calculate(inp)

    print()
    print("─" * 62)
    print(f"  {r['输入回显']['product']} · {r['输入回显']['material']}"
          f" · {r['输入回显']['thickness']}mm · {r['输入回显']['surface']}"
          f" · {r['工艺口径']['包法']} · {r['工艺口径']['实际工艺']}")
    print(f"  洞口 {r['输入回显']['opening_w']:g}×{r['输入回显']['opening_h']:g}mm"
          f"  墙厚 {r['输入回显']['wall_d']:g}mm  ×{r['套数']} 套"
          f"  延米 {r['延米数']:.2f}m")
    print("─" * 62)
    print(f"  {_pad('总成本', 12)}{_money(r['总成本']):>14}   单套 {_money(r['单套成本'])}")
    print(f"  {_pad('建议报价', 12)}{_money(r['建议报价合计']):>14}   单套 {_money(r['单套报价'])}")
    print(f"  {_pad('毛利', 12)}{_money(r['毛利合计']):>14}   利润率 {r['实际利润率'] * 100:.1f}%")
    print(f"  {_pad('延米参考价', 12)}{_money(r['延米参考价']):>14}/m")
    print(f"  {_pad('置信度', 12)}{_pad(r['confidence_level'], 14, right=True)}"
          f"   （低=出厂价表 / 中=改过价 / 高=实单校准过）")
    print("─" * 62)
    print("  成本明细")
    for k, v in r["成本明细"].items():
        if v:
            share = v / r["总成本"] * 100 if r["总成本"] else 0
            bar = "█" * max(1, round(share / 4))
            print(f"    {_pad(k, 10)}{_money(v):>12}  {share:5.1f}%  {bar}")
    if args.detail:
        print("─" * 62)
        print("  算式")
        for s in r["算式"]:
            amt = _money(s["金额"]) if s["金额"] is not None else "—"
            print(f"    {_pad(s['名称'], 8)}{amt:>12}  {s['算式']}")
        print("─" * 62)
        print("  件清单（车间下料用）")
        for p in r["件清单"]:
            width = p.get("摊平宽度mm", p.get("摊平宽mm"))
            print(f"    {_pad(p['件名'], 9)}×{_pad(p['条数'], 3)}"
                  f" 长 {p['单条长mm']:>7.1f}mm  摊平宽 {width:>6.1f}mm"
                  f"  展开 {p['展开面积㎡']:.3f}㎡")
    if r["告警"]:
        print("─" * 62)
        print("  工艺告警")
        for w in r["告警"]:
            print(f"    ! {w}")
    print("─" * 62)
    print(f"  {OUTPUT_DISCLAIMER}")
    print()
    return 0


def cmd_cases(args):
    from .cost_engine import calculate as calc
    cases = {
        "标准双包门套": {},
        "同尺寸整包对比": {"manufacture_type": "整包"},
        "满焊无缝高端单": {"weld_mode": "满焊无缝"},
        "单包201_0.8_喷涂_跨城": {"material": "201", "thickness": 0.8, "wrap": "单包",
                                  "surface": "喷涂", "opening_w": 1000, "opening_h": 2200,
                                  "wall_d": 200, "dest_city": "大连"},
        "窗套5套_上圆角镀钛_含窗台": {"product": "窗套", "has_window_sill": True,
                                      "shape": "上圆角", "arc_radius": 80, "surface": "镀钛",
                                      "material": "304", "thickness": 1.2, "wrap": "双包",
                                      "opening_w": 1500, "opening_h": 1600, "wall_d": 280,
                                      "quantity": 5, "face_width": 80, "head_extra_mode": "2c",
                                      "dest_city": "北京"},
        "告警用例_薄板宽套线超板幅": {"material": "201", "thickness": 0.6, "surface": "镀钛",
                                       "shape": "半圆拱", "opening_w": 2600, "opening_h": 2800,
                                       "wall_d": 500, "face_width": 260, "wrap": "单包",
                                       "dest_city": "乌鲁木齐", "same_city": False},
    }
    print(f"\n  {'样例':<26}{'总成本':>12}{'单套报价':>12}  告警")
    print("  " + "─" * 60)
    for name, cfg in cases.items():
        r = calc(cfg)
        print(f"  {name:<26}{_money(r['总成本']):>12}{_money(r['单套报价']):>12}"
              f"  {len(r['告警'])} 条")
    print()
    return 0


def cmd_book(args):
    if args.action == "show":
        pb = load_pricebook()
        print(f"\n  价表路径：{default_path()}")
        print(f"  板材单价（元/㎡）")
        for m, tmap in pb["板材单价"].items():
            print(f"    {m:<5}" + "  ".join(f"{t}mm={v:g}" for t, v in tmap.items()))
        print(f"  焊缝 {pb['焊接']['焊缝元每米']:g} 元/m"
              f" · 折弯 {pb['折弯']['直边折边元每米']:g} 元/m"
              f" · 加成 {pb['商务']['成本加成率'] * 100:g}%")
        print(f"  状态：{'改过价' if pb['meta']['modified'] else '出厂默认'}"
              f"{' · 已校准' if pb['meta']['calibrated'] else ''}\n")
    elif args.action == "set":
        if not args.pairs:
            raise SystemExit("用法：tiechi book set 焊接.焊缝元每米=55")
        changes = {}
        for p in args.pairs:
            if "=" not in p:
                raise SystemExit(f"需要 key=value，收到：{p}")
            path, raw = p.split("=", 1)
            try:
                val = json.loads(raw)
            except json.JSONDecodeError:
                val = raw
            node = changes
            parts = path.split(".")
            for seg in parts[:-1]:
                node = node.setdefault(seg, {})
            node[parts[-1]] = val
        update_price_params(changes)
        print(f"  已保存到 {default_path()}，置信度变为「中」")
    elif args.action == "reset":
        reset_pricebook()
        print(f"  已恢复出厂价表：{default_path()}")
    return 0


def cmd_schema(args):
    if args.json:
        print(json.dumps(INPUT_SCHEMA, ensure_ascii=False, indent=2))
    else:
        for f in INPUT_SCHEMA:
            unit = f.get("unit", "")
            print(f"  {f['group']:<4}{f['label']:<10}{f['key']:<22}"
                  f"{f['default']}{unit:<5} {f.get('help', '')}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="tiechi", description="不锈钢板金定制品报价引擎（门套/窗套/装饰线条）")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("quote", help="算一单")
    q.add_argument("--preset", help=f"预设：{', '.join(PRESETS)}")
    q.add_argument("--w", type=float, help="洞口宽 mm")
    q.add_argument("--h", type=float, help="洞口高 mm")
    q.add_argument("--d", type=float, help="墙厚 mm")
    q.add_argument("--qty", type=int, help="套数")
    q.add_argument("--product", help="门套/窗套/装饰线条")
    q.add_argument("--material", help="201/304/316L")
    q.add_argument("--thickness", type=float, help="板厚 mm")
    q.add_argument("--surface", help="无处理2B/拉丝/磨砂/喷涂/镜面8K/镀钛")
    q.add_argument("--wrap", help="单包/双包")
    q.add_argument("--shape", help="直边/上圆角/半圆拱")
    q.add_argument("--face", type=float, help="套线可见面宽 mm")
    q.add_argument("--arc", type=float, help="圆角半径 mm")
    q.add_argument("--process", help="拼焊/整包/满焊")
    q.add_argument("--set", action="append", metavar="K=V", help="其他参数，可多次")
    q.add_argument("--detail", action="store_true", help="打印算式与件清单")
    q.set_defaults(func=cmd_quote)

    c = sub.add_parser("cases", help="跑内置样例单")
    c.set_defaults(func=cmd_cases)

    b = sub.add_parser("book", help="价表")
    b.add_argument("action", choices=["show", "set", "reset"])
    b.add_argument("pairs", nargs="*", help="set 用：路径=值，如 焊接.焊缝元每米=55")
    b.set_defaults(func=cmd_book)

    s = sub.add_parser("schema", help="打印输入字段定义")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_schema)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
