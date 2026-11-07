# -*- coding: utf-8 -*-
"""
figures —— 生成 docs/figures 下的工程图
=====================================
数字全部由 tiechi 现算，图只负责画。改了价表或算法，重跑一次图就跟着变，
不会出现"文档里的数字和代码不一致"。

依赖：本机 Edge（无头截图）。不需要 playwright / PIL。
    python tools/figures.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TIECHI_PRICEBOOK", str(Path(tempfile.gettempdir()) / "tiechi-figures-pricebook.json"))

from tiechi import calculate  # noqa: E402

EDGE = next((p for p in [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
] if Path(p).exists()), None)

OUT = ROOT / "docs" / "figures"
TMP = Path(tempfile.mkdtemp(prefix="tiechi-fig-"))

# ---------------------------------------------------------------- 数据
BASE = {"opening_w": 1000, "opening_h": 2100, "wall_d": 240,
        "material": "304", "thickness": 1.0, "surface": "拉丝",
        "wrap": "双包", "manufacture_type": "拼焊", "shape": "直边"}

A = calculate(dict(BASE))                                  # 拼焊（双包）
B = calculate({**BASE, "manufacture_type": "整包", "wrap": "单包"})   # 整包（单面）
SINGLE = calculate({**BASE, "wrap": "单包"})               # 单包拼焊
PZ = calculate({**BASE, "wrap": "单包"})                   # 图二用：同为单包口径对比

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  --paper:#fbfbf8; --ink:#17191d; --mute:#6d7176; --line:#d9d6cd;
  --rust:#a8351a; --blue:#1c4f75; --sand:#efece3;
}
body {
  width:1600px; background:var(--paper); color:var(--ink);
  font-family:"Microsoft YaHei","PingFang SC",sans-serif;
  -webkit-font-smoothing:antialiased;
}
.page { padding:64px 72px 56px; position:relative; }
.mono { font-family:Consolas,"Cascadia Mono",monospace; font-variant-numeric:tabular-nums; }
.kicker { font-size:15px; letter-spacing:.22em; color:var(--mute); text-transform:uppercase; }
h1 { font-size:34px; font-weight:600; margin-top:10px; letter-spacing:.01em; }
.sub { font-size:17px; color:var(--mute); margin-top:12px; line-height:1.7; }
.rule { height:1px; background:var(--line); margin:26px 0; }
.foot {
  position:absolute; left:72px; right:72px; bottom:34px; display:flex;
  justify-content:space-between; font-size:13px; color:var(--mute);
  border-top:1px solid var(--line); padding-top:12px;
}
.tag { display:inline-block; font-size:12.5px; letter-spacing:.14em; color:var(--mute);
  border:1px solid var(--line); padding:3px 9px; margin-right:8px; }
"""


def page(title, sub, body, foot_left, w=1600, h=1050):
    return f"""<!doctype html><meta charset="utf-8"><style>{CSS}</style>
<body><div class="page" style="height:{h}px">
  <div class="kicker">tiechi · 报价引擎</div>
  <h1>{title}</h1>
  <div class="sub">{sub}</div>
  <div class="rule"></div>
  {body}
  <div class="foot"><span>{foot_left}</span><span class="mono">tiechi 1.0.0 · 出厂示例价表</span></div>
</div></body>"""


# ---------------------------------------------------------------- 图一：成本结构
def fig_cost():
    items = [(k, v) for k, v in A["成本明细"].items() if v > 0]
    items.sort(key=lambda x: -x[1])
    total = A["总成本"]
    exprs = {s["名称"]: s["算式"] for s in A["算式"]}
    rows = []
    for name, val in items:
        pct = val / total * 100
        rows.append(f"""
      <div style="display:grid;grid-template-columns:110px 1fr 120px 66px;align-items:center;
                  gap:18px;margin-bottom:19px;">
        <div style="font-size:19px;">{name}</div>
        <div style="position:relative;height:26px;background:var(--sand);">
          <div style="position:absolute;left:0;top:0;bottom:0;width:{pct:.2f}%;
                      background:{'var(--rust)' if pct > 20 else 'var(--blue)'};"></div>
        </div>
        <div class="mono" style="font-size:20px;text-align:right;">{val:,.2f}</div>
        <div class="mono" style="font-size:15px;text-align:right;color:var(--mute);">{pct:.1f}%</div>
      </div>""")

    g = A["几何"]
    facts = [
        ("单套展开面积", f"{g['单套展开面积㎡']:.3f} ㎡"),
        ("含损耗用料", f"{g['含损耗用料面积㎡合计']:.3f} ㎡"),
        ("折弯米数", f"{g['折弯米数m合计']:.2f} m"),
        ("焊缝米数", f"{A['工艺口径']['焊缝米数']:.3f} m"),
        ("重量", f"{g['重量kg合计']:.1f} kg"),
        ("板材", f"{g['板材张数']} 张 / 利用率 {g['板材利用率']*100:.0f}%"),
    ]
    facts_html = "".join(
        f"""<div style="display:flex;justify-content:space-between;padding:9px 0;
                    border-bottom:1px dotted var(--line);font-size:15px;">
              <span style="color:var(--mute)">{k}</span>
              <span class="mono">{v}</span></div>""" for k, v in facts)

    body = f"""
  <div style="display:grid;grid-template-columns:1fr 400px;gap:64px;">
    <div>
      <div style="display:flex;justify-content:space-between;font-size:13px;color:var(--mute);
                  letter-spacing:.1em;margin-bottom:16px;border-bottom:1px solid var(--line);padding-bottom:8px;">
        <span>成本项</span><span>金额（元）</span><span>占比</span>
      </div>
      {''.join(rows)}
      <div style="display:flex;justify-content:space-between;margin-top:26px;padding-top:16px;
                  border-top:2px solid var(--ink);">
        <div style="font-size:22px;">总成本</div>
        <div class="mono" style="font-size:30px;">￥{total:,.2f}</div>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:10px;">
        <div style="font-size:17px;color:var(--mute)">×（1 + 加成 30%），取整到元</div>
        <div class="mono" style="font-size:24px;color:var(--rust);">报价 ￥{A['建议报价合计']:,.0f}</div>
      </div>
      <div style="margin-top:22px;font-size:14.5px;color:var(--mute);line-height:2;">
        {'<br>'.join(f'<span class="mono">{exprs[k]}</span>' for k, _ in items[:3])}
      </div>
    </div>
    <div>
      <div style="font-size:13px;letter-spacing:.1em;color:var(--mute);margin-bottom:10px;
                  border-bottom:1px solid var(--line);padding-bottom:8px;">几何口径</div>
      {facts_html}
      <div style="margin-top:26px;font-size:13px;letter-spacing:.1em;color:var(--mute);margin-bottom:10px;
                  border-bottom:1px solid var(--line);padding-bottom:8px;">件清单（车间下料）</div>
      {''.join(f'''<div style="display:flex;justify-content:space-between;padding:7px 0;font-size:14.5px;">
        <span>{p['件名']} ×{p['条数']}</span>
        <span class="mono" style="color:var(--mute)">{p['单条长mm']:.0f}×{p['摊平宽mm']:.1f}mm</span></div>'''
        for p in A['件清单'])}
    </div>
  </div>"""
    return page("一件门套的七项成本", "洞口 1000×2100mm · 墙厚 240mm · 304 / 1.0mm · 拉丝 · 双包 · 拼焊 · 1 套",
                body, "python -m tiechi.cli quote --w 1000 --h 2100 --d 240 --detail")


# ---------------------------------------------------------------- 图二：拼焊 vs 整包
def fig_compare():
    def col(r, label, note, color, sketch):
        g = r["几何"]
        rows = [
            ("展开面积", f"{g['单套展开面积㎡']:.3f} ㎡"),
            ("拼角处数", f"{r['工艺口径']['拼角处数']} 处"),
            ("焊缝米数", f"{r['工艺口径']['焊缝米数']:.3f} m"),
            ("接料处数", f"{g['拼板接料处数']} 处"),
            ("折弯米数", f"{g['折弯米数m合计']:.2f} m"),
            ("总成本", f"￥{r['总成本']:,.2f}"),
            ("单套报价", f"￥{r['单套报价']:,.0f}"),
        ]
        rows_html = "".join(
            f"""<div style="display:flex;justify-content:space-between;padding:10px 0;
                        border-bottom:1px dotted var(--line);font-size:16px;">
                  <span style="color:var(--mute)">{k}</span>
                  <span class="mono">{v}</span></div>""" for k, v in rows)
        return f"""
      <div style="flex:1;">
        <div style="display:flex;align-items:baseline;gap:12px;">
          <div style="font-size:26px;font-weight:600;color:{color}">{label}</div>
          <div style="font-size:15px;color:var(--mute)">{note}</div>
        </div>
        <div style="margin:16px 0 6px;">{sketch}</div>
        {rows_html}
      </div>"""

    # 剖面示意：拼焊三件拼角 / 整包一块板折成 П
    sketch_a = """<svg width="100%" height="120" viewBox="0 0 380 120">
      <g stroke="#17191d" stroke-width="2.4" fill="none">
        <path d="M40 96 V30 H120"/><path d="M120 96 V30"/><path d="M200 96 V30 H280"/>
      </g>
      <g stroke="#a8351a" stroke-width="1" stroke-dasharray="3 3">
        <path d="M120 34 L200 44"/>
      </g>
      <text x="128" y="30" font-size="11" fill="#a8351a" font-family="Consolas">拼角焊缝</text>
      <text x="40" y="114" font-size="11" fill="#6d7176" font-family="Microsoft YaHei">立边</text>
      <text x="205" y="114" font-size="11" fill="#6d7176" font-family="Microsoft YaHei">顶横边</text>
    </svg>"""
    sketch_b = """<svg width="100%" height="120" viewBox="0 0 380 120">
      <g stroke="#1c4f75" stroke-width="2.4" fill="none">
        <path d="M30 96 V26 H330 V96"/>
      </g>
      <g stroke="#a8351a" stroke-width="1" stroke-dasharray="3 3">
        <path d="M180 26 V96"/>
      </g>
      <text x="186" y="46" font-size="11" fill="#a8351a" font-family="Consolas">接料缝（板长超限）</text>
      <text x="30" y="114" font-size="11" fill="#6d7176" font-family="Microsoft YaHei">一块长板连续折弯</text>
    </svg>"""

    delta_cost = B["总成本"] - PZ["总成本"]
    delta_price = B["单套报价"] - PZ["单套报价"]
    body = f"""
  <div style="display:flex;gap:56px;">
    {col(PZ, "拼焊", "分件下料，拼角焊接（同为单包）", "var(--ink)", sketch_a)}
    {col(B, "整包", "一块长板折成 П 形（同为单包）", "var(--blue)", sketch_b)}
  </div>
  <div style="margin-top:30px;border:1px solid var(--line);padding:20px 24px;
              display:flex;justify-content:space-between;align-items:center;">
    <div style="font-size:16px;line-height:1.8;">
      同一洞口同为单包，改整包多付：<b class="mono">￥{delta_cost:,.2f}</b> 成本 ·
      <b class="mono">￥{delta_price:,.0f}</b> 报价<br>
      <span style="color:var(--mute);font-size:14.5px;">
        买的是"没有拼角焊缝"——整包板的长度 = 2H + W + 2D + 端头余量
        = {2*2100+1000+2*240+2*15}mm，必然接料。
      </span>
    </div>
    <div style="text-align:right;font-size:14px;color:var(--mute);line-height:1.7;">
      值不值由客户定<br>但价格得报得出来
    </div>
  </div>"""
    return page("同尺寸两种工艺，差在哪",
                "洞口 1000×2100mm · 墙厚 240mm · 304 / 1.0mm · 拉丝 · 单包 · 1 套",
                body, "python -m tiechi.cli quote --preset 整包窗套 ／ 直接改 manufacture_type",
                h=1000)


# ---------------------------------------------------------------- 图三：摊平宽度
def fig_width():
    wd_single = SINGLE["几何"]["摊平宽度mm"]
    wd_double = A["几何"]["摊平宽度mm"]
    wd_pack = B["几何"]["摊平宽度mm"]

    def chain(items, total, color="#a8351a"):
        segs = labels = ""
        for i, (name, val) in enumerate(items):
            w = abs(val) / total * 100
            segs += (f'<div style="width:{w}%;background:{color};opacity:{0.30 + 0.22 * i:.2f};'
                     f'border-right:1px solid var(--paper)"></div>')
            label_html = (f'<br>{name}' if w > 9 else '')
            labels += (f'<div style="width:{w}%;font-size:13px;color:var(--mute);padding-top:7px;'
                       f'text-align:center;border-right:1px dotted var(--line);">'
                       f'<span class="mono" style="color:var(--ink)">{"+" if val > 0 else "−"}{abs(val):g}</span>'
                       f'{label_html}</div>')
        return (f'<div style="display:flex;height:26px;">{segs}</div>'
                f'<div style="display:flex;">{labels}</div>')

    rows = [
        ("单包", "抱墙 = min(墙厚, 40)", SINGLE, wd_single,
         [("套线 60", 60), ("抱墙 40", 40), ("折脚 20", 20), ("扣减", -0.5)]),
        ("双包", "每面抱满墙厚 240", A, wd_double,
         [("套线 60", 60), ("抱墙 240", 240), ("折脚 20", 20), ("扣减", -0.5)]),
        ("整包", "c + D + 折脚 − 2×扣减", B, wd_pack,
         [("套线 60", 60), ("墙厚 240", 240), ("折脚 20", 20), ("扣减", -1.0)]),
    ]
    blocks = ""
    for label, note, r, wd, items in rows:
        blocks += f"""
      <div style="margin-bottom:34px;">
        <div style="display:flex;align-items:baseline;gap:14px;margin-bottom:8px;">
          <div style="font-size:21px;font-weight:600;">{label}</div>
          <div style="font-size:14.5px;color:var(--mute)">{note}</div>
          <div style="flex:1"></div>
          <div class="mono" style="font-size:26px;">{wd:.1f}<span style="font-size:15px;color:var(--mute)"> mm</span></div>
        </div>
        {chain(items, wd)}
        <div class="mono" style="font-size:13.5px;color:var(--mute);margin-top:8px;">
          {' + '.join(f'{v:g}' for _, v in items[:-1])} {items[-1][1]:g} = {wd:.1f}
        </div>
      </div>"""

    body = f"""
  <div style="display:grid;grid-template-columns:1fr 360px;gap:56px;">
    <div>{blocks}</div>
    <div style="border-left:1px solid var(--line);padding-left:28px;">
      <div style="font-size:13px;letter-spacing:.1em;color:var(--mute);margin-bottom:14px;">口径</div>
      <div class="mono" style="font-size:14.5px;line-height:2.1;color:var(--ink)">
        拼焊：Wd = c + k×a + 折脚 − k×0.5×t<br>
        整包：Wd = c + D + 折脚 − 2×0.5×t
      </div>
      <div style="margin-top:22px;font-size:14.5px;line-height:1.95;color:var(--mute)">
        k = 折边道数（1=L 型，2=U 型）<br>
        a = 抱墙深度：单包封顶 40mm<br>
        扣减 = 每道折弯让展开少半个板厚
      </div>
      <div style="margin-top:26px;padding:14px 16px;background:var(--sand);font-size:14px;line-height:1.85;">
        单包 240 墙只包得住 40mm，<br>现场靠收边条糊过去——<br>所以墙厚超过 70mm 就该考虑双包。
      </div>
    </div>
  </div>"""
    return page("摊平宽度是怎么来的", "同样是 60mm 套线、240mm 墙、1.0mm 板，三种工艺的展开宽度差 200mm",
                body, "docs/工艺与几何.md · 摊平宽度", h=980)


# ---------------------------------------------------------------- 图四：加成 ≠ 利润
def fig_markup():
    cost = A["总成本"]
    price = A["建议报价合计"]
    profit30 = cost / 0.7
    rows = [
        ("成本加成 30%（引擎默认）", cost * 1.3, "成本 × 1.30", (cost * 1.3 - cost) / (cost * 1.3) * 100),
        ("按利润 30% 反算", profit30, "成本 ÷ (1 − 0.30)", (profit30 - cost) / profit30 * 100),
    ]
    bars = ""
    for label, p, expr, real in rows:
        bars += f"""
      <div style="margin-bottom:28px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;">
          <div style="font-size:18px;">{label}</div>
          <div class="mono" style="font-size:22px;">￥{p:,.2f}</div>
        </div>
        <div style="display:flex;height:30px;margin-top:10px;">
          <div style="width:{cost/p*100:.1f}%;background:var(--ink);"></div>
          <div style="width:{(p-cost)/p*100:.1f}%;background:var(--rust);opacity:.75;"></div>
        </div>
        <div class="mono" style="font-size:13px;color:var(--mute);margin-top:7px;">
          {expr} · 实际利润率 {real:.1f}%
        </div>
      </div>"""

    gap = profit30 - cost * 1.3
    body = f"""
  <div style="display:grid;grid-template-columns:1fr 380px;gap:60px;">
    <div>
      {bars}
      <div style="display:flex;gap:26px;font-size:13.5px;color:var(--mute);margin-top:6px;">
        <span><span style="display:inline-block;width:11px;height:11px;background:var(--ink);margin-right:7px;"></span>成本 {cost:,.2f}</span>
        <span><span style="display:inline-block;width:11px;height:11px;background:var(--rust);opacity:.75;margin-right:7px;"></span>毛利</span>
      </div>
      <div style="margin-top:34px;border-top:2px solid var(--ink);padding-top:18px;">
        <div style="font-size:16px;line-height:1.9;">
          同样一件活，两个口径报出来的价差 <b class="mono" style="color:var(--rust)">￥{gap:,.2f}</b><br>
          <span style="color:var(--mute);font-size:14.5px;">按 100 万成本量级，两种口径的报价差 ￥{gap / cost * 1e6:,.0f}，而且账上一直是"赚的"。</span>
        </div>
      </div>
    </div>
    <div style="border-left:1px solid var(--line);padding-left:28px;">
      <div style="font-size:13px;letter-spacing:.1em;color:var(--mute);margin-bottom:14px;">为什么</div>
      <div class="mono" style="font-size:40px;line-height:1.3;">0.30<br><span style="font-size:22px;color:var(--mute)">÷ 1.30</span><br>= 23.1%</div>
      <div style="margin-top:20px;font-size:14.5px;line-height:1.95;color:var(--mute)">
        加成加在成本上，利润率是拿毛利除售价。<br>
        分母不一样，差 6.9 个百分点。
      </div>
      <div style="margin-top:24px;font-size:14px;line-height:1.8;padding:14px 16px;background:var(--sand);">
        价表里两个字段二选一：<br>
        <span class="mono">成本加成率</span> 或 <span class="mono">销售利润率</span>
      </div>
    </div>
  </div>"""
    return page("加成 30% 不是利润 30%", "行业里最常见的报亏原因，也是一条断言（tests/test_engine.py）",
                body, "python -m unittest tests.test_engine.TestCost.test_加成率口径对应利润率不是30",
                h=940)


# ---------------------------------------------------------------- 出图
FIGS = [
    ("01-cost-breakdown", fig_cost, 1600, 820),
    ("02-pinhan-vs-zhengbao", fig_compare, 1600, 880),
    ("03-developed-width", fig_width, 1600, 840),
    ("04-markup-vs-margin", fig_markup, 1600, 900),
]


def main():
    if not EDGE:
        raise SystemExit("没找到 Edge，改 EDGE 常量")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn, w, h in FIGS:
        html = TMP / f"{name}.html"
        html.write_text(fn(), encoding="utf-8")
        png = OUT / f"{name}.png"
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", html.as_uri()],
                       check=True, capture_output=True, timeout=90)
        print(f"{png.name}  {png.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
