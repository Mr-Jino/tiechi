# -*- coding: utf-8 -*-
"""
moments —— 生成朋友圈四宫格（1080×1080 @2x）
==========================================
版式沿用仓库里的数据表风格：纸白底、细线、等宽数字。数字全部由引擎现算。

叙事线（v3，对齐"模糊才是利润来源"的口径）：
  1 报价单上缺的那几行      —— 提出问题：总价是确定的，其余全空着
  2 缺的三个数字值多少      —— 洞口 2.10㎡ / 展开 3.47㎡，同价两种单价差 1.65 倍
  3 同一句话，差 423 元     —— 工艺口径不明，差价藏在"单包"这句里
  4 七项成本，逐项带算式    —— 把洞填上

    python tools/moments.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TIECHI_PRICEBOOK", str(Path(tempfile.gettempdir()) / "tiechi-moments-pricebook.json"))

from tiechi import calculate  # noqa: E402

EDGE = next((p for p in [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
] if Path(p).exists()), None)
OUT = ROOT / "docs" / "moments"
TMP = Path(tempfile.mkdtemp(prefix="tiechi-mom-"))

BASE = {"opening_w": 1000, "opening_h": 2100, "wall_d": 240,
        "material": "304", "thickness": 1.0, "surface": "拉丝", "shape": "直边"}
A = calculate({**BASE, "wrap": "双包", "manufacture_type": "拼焊"})
PZ = calculate({**BASE, "wrap": "单包", "manufacture_type": "拼焊"})
ZB = calculate({**BASE, "wrap": "单包", "manufacture_type": "整包"})

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--paper:#fbfbf8;--ink:#17191d;--mute:#6d7176;--line:#d9d6cd;--rust:#a8351a;--blue:#1c4f75;--sand:#efece3}
body{width:1080px;background:var(--paper);color:var(--ink);
  font-family:"Microsoft YaHei","PingFang SC",sans-serif;-webkit-font-smoothing:antialiased}
.card{width:1080px;height:1080px;padding:62px 64px;position:relative}
.mono{font-family:Consolas,"Cascadia Mono",monospace;font-variant-numeric:tabular-nums}
.kicker{font-size:20px;letter-spacing:.2em;color:var(--mute)}
h1{font-size:74px;font-weight:700;line-height:1.28;letter-spacing:.01em}
h2{font-size:44px;font-weight:600;line-height:1.35}
.sub{font-size:26px;color:var(--mute);line-height:1.75}
.rule{height:1px;background:var(--line);margin:26px 0}
.foot{position:absolute;left:64px;right:64px;bottom:44px;font-size:19px;color:var(--mute);
  border-top:1px solid var(--line);padding-top:16px;display:flex;justify-content:space-between}
.blank{display:inline-block;border-bottom:2px dashed var(--line);width:132px;height:2px;
  vertical-align:middle;margin-bottom:6px}
"""


def card(body, left, right="tiechi · MIT"):
    return f"""<!doctype html><meta charset="utf-8"><style>{CSS}</style>
<body><div class="card">{body}
<div class="foot"><span>{left}</span><span class="mono">{right}</span></div></div></body>"""


# ------------------------------------------------------------------ 1 封面
def c1():
    def line(name, val, fixed=False):
        return f"""
      <div style="display:flex;justify-content:space-between;align-items:baseline;
                  padding:17px 0;border-bottom:1px solid var(--line);">
        <div style="font-size:27px;{'font-weight:600' if fixed else 'color:var(--mute)'}">{name}</div>
        <div class="mono" style="font-size:{31 if fixed else 25}px;
             {'color:var(--ink)' if fixed else 'color:var(--mute)'}">{val}</div>
      </div>"""

    body = f"""
  <div class="kicker">T I E C H I</div>
  <h1 style="margin-top:30px;">报价单上<br>缺的那几行。</h1>
  <div style="margin-top:46px;border:1px solid var(--line);background:#fff;padding:8px 30px 22px;">
    <div class="mono" style="font-size:19px;color:var(--mute);padding:16px 0 8px;
         border-bottom:2px solid var(--ink);letter-spacing:.12em;">不锈钢门套报价单 · 1000×2100</div>
    {line("展开面积", '<span class="blank"></span> ㎡')}
    {line("焊缝米数", '<span class="blank"></span> m')}
    {line("损耗率", '<span class="blank"></span> %')}
    {line("单价口径", "按洞口 / 按展开")}
    {line("总价", f"￥{A['单套报价']:,.0f}", fixed=True)}
  </div>
  <div style="margin-top:34px;font-size:25px;line-height:1.85;">
    五个格子里，只有一个数是真的。<br>
    <span style="color:var(--rust);">缺的那四行，正好是能验算的那四行。</span>
  </div>"""
    return card(body, "github.com/Mr-Jino/tiechi", "纯 Python · 无依赖")


# ------------------------------------------------------------ 2 缺的三个数字
def c2():
    g = A["几何"]
    hole = BASE["opening_w"] * BASE["opening_h"] / 1e6      # 洞口面积 ㎡
    dev = g["单套展开面积㎡"]
    price = A["单套报价"]

    def row(no, ask, val, unit, hidden):
        return f"""
      <div style="border-top:1px solid var(--line);padding:24px 0 20px;">
        <div style="display:flex;align-items:baseline;gap:18px;">
          <div class="mono" style="font-size:21px;color:var(--mute);width:34px;">{no}</div>
          <div style="font-size:32px;font-weight:600;">{ask}</div>
          <div style="flex:1;"></div>
          <div class="mono" style="font-size:42px;">{val}<span style="font-size:22px;color:var(--mute);"> {unit}</span></div>
        </div>
        <div class="mono" style="font-size:19px;color:var(--mute);margin-top:9px;padding-left:52px;">
          {hidden}
        </div>
      </div>"""

    rows = (
        row("01", "展开面积", f"{dev:.3f}", "㎡",
            f"报价只写“按洞口 {hole:.2f} ㎡”—— 摊平后是洞口的 {dev/hole:.2f} 倍")
        + row("02", "焊缝米数", f"{A['工艺口径']['焊缝米数']:.2f}", "m",
              f"报价只写“{A['工艺口径']['拼角处数']} 处拼角”—— 处不是长度，估不出焊接费")
        + row("03", "损耗率", f"{g['损耗率']*100:.0f}", "%",
              f"报价单里没有这一项 —— 它按 {g['含损耗用料面积㎡合计']:.2f} ㎡ 买料，"
              f"按 {dev:.2f} ㎡ 收钱")
    )

    body = f"""
  <h2>缺的这三个数，值多少钱</h2>
  <div class="sub" style="margin-top:12px;font-size:23px;">同一个价格，两种分母，1.65 倍</div>
  {rows}
  <div style="border-top:2px solid var(--ink);padding-top:22px;margin-top:4px;">
    <div style="font-size:23px;line-height:1.95;">
      于是同一个 <span class="mono">￥{price:,.0f}</span>，可以写成
      <b class="mono" style="color:var(--rust)">￥{price/hole:,.0f}/㎡</b>（按洞口），<br>
      也可以说成 <b class="mono" style="color:var(--rust)">￥{price/dev:,.0f}/㎡</b>（按展开）。<br>
      <span style="color:var(--mute);">两家比单价，分母不是一个东西，比的是笔误。</span>
    </div>
  </div>"""
    return card(body, "三个都是硬数，一问就现形", "github.com/Mr-Jino/tiechi")


# ---------------------------------------------------------------- 3 工艺口径
def c3():
    def block(r, name, note, color):
        g = r["几何"]
        return f"""
      <div style="flex:1;border:1px solid var(--line);padding:24px 26px 20px;background:#fff;">
        <div style="display:flex;align-items:baseline;gap:12px;">
          <div style="font-size:31px;font-weight:700;color:{color}">{name}</div>
          <div style="font-size:19px;color:var(--mute)">{note}</div>
        </div>
        <div class="mono" style="font-size:42px;margin-top:12px;">￥{r['单套报价']:,.0f}</div>
        <div style="margin-top:12px;font-size:20px;color:var(--mute);line-height:2;" class="mono">
          展开 {g['单套展开面积㎡']:.3f} ㎡<br>
          拼角 {r['工艺口径']['拼角处数']} 处 · 接料 {g['拼板接料处数']} 处<br>
          焊缝 {r['工艺口径']['焊缝米数']:.3f} m
        </div>
      </div>"""

    d_cost = ZB["总成本"] - PZ["总成本"]
    d_price = ZB["单套报价"] - PZ["单套报价"]
    body = f"""
  <h2>同一句"单包"，差 {d_price:,.0f} 元</h2>
  <div class="sub" style="margin-top:12px;font-size:23px;">
    同一个洞口、同一种材料、同一个包法，变量只有"怎么做"（成本差 {d_cost:,.0f}，加成后 {d_price:,.0f}）
  </div>
  <div style="display:flex;gap:22px;margin-top:30px;">
    {block(PZ, "拼焊", "分件下料 · 拼角焊", "var(--ink)")}
    {block(ZB, "整包", "一块板折成 П 形", "var(--blue)")}
  </div>
  <div style="margin-top:28px;font-size:23px;line-height:1.95;">
    客户买的是"没有拼角焊缝"。<br>
    <span style="color:var(--mute);">代价：整包板长 2×2100+1000+2×240+30 = 5710mm，<br>
    标准板最长 3000mm，必然接料 —— 所以整包不是"高端就选它"。</span><br>
    这句话不写在报价单上，客户就只能比较两个数字。
  </div>"""
    return card(body, "差价不藏在价格里，藏在措辞里")


# ---------------------------------------------------------------- 4 七项成本
def c4():
    rows_src = [s for s in A["算式"] if s["金额"] is not None and s["名称"] != "建议报价"]
    rows = ""
    for s in rows_src:
        rows += f"""
      <div style="display:grid;grid-template-columns:132px 1fr 124px;gap:14px;
                  align-items:baseline;padding:15px 0;border-bottom:1px solid var(--line);">
        <div style="font-size:24px;">{s['名称'].replace('费','')}</div>
        <div class="mono" style="font-size:15.5px;color:var(--mute);line-height:1.55;">{s['算式']}</div>
        <div class="mono" style="font-size:23px;text-align:right;">{s['金额']:,.2f}</div>
      </div>"""

    body = f"""
  <h2>七项成本，逐项带算式</h2>
  <div class="sub" style="margin-top:10px;font-size:22px;">
    1000×2100 · 墙厚 240 · 304/1.0 · 拉丝 · 双包 · 拼焊
  </div>
  <div class="rule" style="margin:20px 0 4px;"></div>
  {rows}
  <div style="display:flex;justify-content:space-between;align-items:baseline;
              border-top:2px solid var(--ink);margin-top:14px;padding-top:14px;">
    <div style="font-size:27px;">总成本</div>
    <div class="mono" style="font-size:38px;">￥{A['总成本']:,.2f}</div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:10px;">
    <div style="font-size:20px;color:var(--mute);">× (1 + 加成 30%)，取整到元</div>
    <div class="mono" style="font-size:31px;color:var(--rust);">报价 ￥{A['单套报价']:,.0f}</div>
  </div>"""
    return card(body, "价表自己回填 · 算式印在结果里")


CARDS = [("tiechi-1", c1), ("tiechi-2", c2), ("tiechi-3", c3), ("tiechi-4", c4)]


def main():
    if not EDGE:
        raise SystemExit("没找到 Edge")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in CARDS:
        html = TMP / f"{name}.html"
        html.write_text(fn(), encoding="utf-8")
        png = OUT / f"{name}.png"
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", "--window-size=1080,1080",
                        f"--screenshot={png}", html.as_uri()],
                       check=True, capture_output=True, timeout=90)
        print(f"{png.name}  {png.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
