# -*- coding: utf-8 -*-
"""
moments —— 生成朋友圈四宫格（1080×1080 @2x）
==========================================
版式沿用仓库里的数据表风格：纸白底、细线、等宽数字。数字全部由引擎现算。
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
"""


def card(body, left, right="tiechi · MIT"):
    return f"""<!doctype html><meta charset="utf-8"><style>{CSS}</style>
<body><div class="card">{body}
<div class="foot"><span>{left}</span><span class="mono">{right}</span></div></div></body>"""


# ------------------------------------------------------------------ 1 封面
def c1():
    body = f"""
  <div class="kicker">T I E C H I</div>
  <h1 style="margin-top:34px;">报一个价，<br>得拿得出算式。</h1>
  <div class="sub" style="margin-top:30px;">
    门套 · 窗套 · 装饰线条<br>七项成本 · 展开几何 · 工艺告警
  </div>
  <div style="margin-top:56px;border:1px solid var(--line);padding:26px 28px;background:#fff;">
    <div class="mono" style="font-size:21px;color:var(--mute);">$ tiechi quote --w 1000 --h 2100 --d 240</div>
    <div class="mono" style="font-size:28px;margin-top:16px;">总成本 ￥{A['总成本']:,.2f}</div>
    <div class="mono" style="font-size:28px;margin-top:8px;">
      报　价 ￥{A['建议报价合计']:,.0f}
      <span style="color:var(--rust);font-size:22px;">利润率 {A['实际利润率']*100:.1f}%</span>
    </div>
  </div>
  <div style="margin-top:44px;font-size:23px;line-height:2;color:var(--mute);">
    31 条断言 · 移植自一套在用的生产报价系统<br>
    开源前做过逐位对照：6 样例 × 8 字段，差异 0
  </div>"""
    return card(body, "github.com/Mr-Jino/tiechi", "纯 Python · 无依赖")


# ------------------------------------------------------------------ 2 成本
def c2():
    items = sorted([(k, v) for k, v in A["成本明细"].items() if v > 0], key=lambda x: -x[1])
    total = A["总成本"]
    rows = "".join(f"""
      <div style="display:grid;grid-template-columns:150px 1fr 138px;align-items:center;gap:16px;margin-bottom:22px;">
        <div style="font-size:27px;">{k}</div>
        <div style="position:relative;height:30px;background:var(--sand);">
          <div style="position:absolute;inset:0 auto 0 0;width:{v/total*100:.2f}%;
                      background:{'var(--rust)' if v/total > 0.2 else 'var(--blue)'};"></div>
        </div>
        <div class="mono" style="font-size:25px;text-align:right;">{v:,.2f}</div>
      </div>""" for k, v in items)
    body = f"""
  <h2>一件门套，钱花在哪</h2>
  <div class="sub" style="margin-top:14px;font-size:23px;">
    1000×2100 · 墙厚 240 · 304/1.0 · 拉丝 · 双包 · 拼焊
  </div>
  <div class="rule"></div>
  {rows}
  <div style="display:flex;justify-content:space-between;align-items:baseline;
              border-top:2px solid var(--ink);margin-top:20px;padding-top:18px;">
    <div style="font-size:30px;">总成本</div>
    <div class="mono" style="font-size:52px;">￥{total:,.2f}</div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:12px;">
    <div style="font-size:22px;color:var(--mute);">× (1 + 加成 30%)，取整到元</div>
    <div class="mono" style="font-size:34px;color:var(--rust);">报价 ￥{A['建议报价合计']:,.0f}</div>
  </div>"""
    return card(body, "材料含算料损耗 · 物流泡重取大")


# ------------------------------------------------------------------ 3 工艺
def c3():
    def block(r, name, note, color, big):
        g = r["几何"]
        return f"""
      <div style="flex:1;border:1px solid var(--line);padding:26px 26px 22px;background:#fff;">
        <div style="display:flex;align-items:baseline;gap:12px;">
          <div style="font-size:32px;font-weight:700;color:{color}">{name}</div>
          <div style="font-size:20px;color:var(--mute)">{note}</div>
        </div>
        <div class="mono" style="font-size:{big}px;margin-top:14px;">￥{r['单套报价']:,.0f}</div>
        <div style="margin-top:14px;font-size:21px;color:var(--mute);line-height:2;" class="mono">
          展开 {g['单套展开面积㎡']:.3f} ㎡<br>
          拼角 {r['工艺口径']['拼角处数']} 处 · 接料 {g['拼板接料处数']} 处<br>
          焊缝 {r['工艺口径']['焊缝米数']:.3f} m
        </div>
      </div>"""

    d_cost = ZB["总成本"] - PZ["总成本"]
    body = f"""
  <h2>同一洞口，改整包多付 {d_cost:,.0f} 元</h2>
  <div class="sub" style="margin-top:12px;font-size:23px;">同为单包口径，变量只有工艺</div>
  <div style="display:flex;gap:22px;margin-top:32px;">
    {block(PZ, "拼焊", "分件下料 · 拼角焊", "var(--ink)", 44)}
    {block(ZB, "整包", "一块板折成 П 形", "var(--blue)", 44)}
  </div>
  <div style="margin-top:30px;font-size:23px;line-height:1.95;">
    买的是"没有拼角焊缝"。<br>
    <span style="color:var(--mute);">代价：整包板长 2×2100+1000+2×240+30 = 5710mm，<br>
    标准板最长 3000mm，必然接料 —— 所以整包不是"高端就选它"。</span>
  </div>"""
    return card(body, "值不值由客户定，但价格得报得出来")


# ------------------------------------------------------------------ 4 加成
def c4():
    cost, price = A["总成本"], A["建议报价合计"]
    p30 = cost / 0.7
    def bar(label, p, expr, real, top):
        return f"""
      <div style="margin-top:{top}px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;">
          <div style="font-size:25px;">{label}</div>
          <div class="mono" style="font-size:28px;">￥{p:,.2f}</div>
        </div>
        <div style="display:flex;height:34px;margin-top:12px;">
          <div style="width:{cost/p*100:.1f}%;background:var(--ink);"></div>
          <div style="width:{(p-cost)/p*100:.1f}%;background:var(--rust);opacity:.75;"></div>
        </div>
        <div class="mono" style="font-size:19px;color:var(--mute);margin-top:9px;">
          {expr} · 实际利润率 {real:.1f}%
        </div>
      </div>"""
    body = f"""
  <h2>加成 30% 不是利润 30%</h2>
  <div class="sub" style="margin-top:12px;font-size:23px;">行业里最常见的报亏原因</div>
  <div class="mono" style="font-size:76px;margin-top:36px;">0.30 <span style="color:var(--mute);font-size:44px;">÷ 1.30</span>
    <span style="color:var(--rust)">= 23.1%</span></div>
  {bar("成本加成 30%", price, "成本 × 1.30", (price-cost)/price*100, 34)}
  {bar("按利润 30% 反算", p30, "成本 ÷ (1−0.30)", (p30-cost)/p30*100, 26)}
  <div style="margin-top:32px;font-size:23px;line-height:1.9;">
    同样的活，两个口径差 <b class="mono" style="color:var(--rust)">￥{p30-price:,.0f}</b> / 套<br>
    <span style="color:var(--mute);">按 100 万成本量级，差 ￥{(p30-price)/cost*1e6:,.0f}，账上却一直是"赚的"。</span>
  </div>"""
    return card(body, "github.com/Mr-Jino/tiechi", "价表请自己回填")


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
