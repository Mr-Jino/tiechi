# -*- coding: utf-8 -*-
"""
引擎断言：只锁"业务上讲得通"的不变量。
跑法：python -m pytest -q   或   python -m unittest discover -s tests -v
"""
import math
import os
import tempfile
import unittest
from pathlib import Path

# 测试用独立价表，别污染 ~/.tiechi
_TMP = Path(tempfile.mkdtemp(prefix="tiechi-test-"))
os.environ["TIECHI_PRICEBOOK"] = str(_TMP / "pricebook.json")

from tiechi import calculate, default_inputs, load_pricebook, reset_pricebook, update_price_params  # noqa: E402
from tiechi.pricebook import DEFAULT_PRICEBOOK, thickness_key  # noqa: E402

BASE = {"opening_w": 1000, "opening_h": 2100, "wall_d": 240, "quantity": 1,
        "material": "304", "thickness": 1.0, "surface": "拉丝"}


def q(**kw):
    return calculate({**BASE, **kw})


class TestGeometry(unittest.TestCase):
    def test_摊平宽度含折弯扣减(self):
        """拼焊单折：Wd = c + 1×a + 折脚 − 1×(0.5×t)；a = min(墙厚, 抱墙上限)。"""
        r = q(wrap="单包", face_width=60, install_leg=20, reveal_cap=40, thickness=1.0)
        self.assertAlmostEqual(r["几何"]["摊平宽度mm"], 60 + 40 + 20 - 0.5, places=3)

    def test_双包比单包面积更大(self):
        a, b = q(wrap="单包"), q(wrap="双包")
        self.assertGreater(b["几何"]["单套展开面积㎡"], a["几何"]["单套展开面积㎡"])

    def test_件清单展开面积合计等于总展开面积(self):
        r = q(shape="上圆角", arc_radius=80)
        s = sum(p["展开面积㎡"] for p in r["件清单"])
        self.assertAlmostEqual(s, r["几何"]["单套展开面积㎡"], places=3)

    def test_整包没有拼角焊缝(self):
        """整包是一块板连续折弯，不存在拼角焊缝；只有板幅不够时的接料缝。"""
        r = q(manufacture_type="整包", wrap="单包")
        self.assertEqual(r["工艺口径"]["拼角处数"], 0)
        g = r["几何"]
        self.assertAlmostEqual(r["工艺口径"]["焊缝米数"],
                               g["拼板接料处数"] * g["摊平宽度mm"] / 1000.0, places=3)

    def test_整包遇弧形自动降级为拼焊并告警(self):
        r = q(manufacture_type="整包", shape="上圆角", arc_radius=80)
        self.assertEqual(r["工艺口径"]["实际工艺"], "拼焊")
        self.assertTrue(any("只支持直边" in w for w in r["告警"]))

    def test_窗套比门套多一条横边且四处拼角(self):
        door, win = q(product="门套"), q(product="窗套")
        self.assertEqual(door["工艺口径"]["拼角处数"], 2)
        self.assertEqual(win["工艺口径"]["拼角处数"], 4)
        heads = [p for p in win["件清单"] if "横边" in p["件名"]][0]
        self.assertEqual(heads["条数"], 4)      # 上下各一条 × 双包两面

    def test_窗套可带窗台板(self):
        r = q(product="窗套", has_window_sill=True)
        names = [p["件名"] for p in r["件清单"]]
        self.assertIn("窗台板", names)
        self.assertIn("窗台前沿", names)

    def test_装饰线条按条数乘每米(self):
        r = q(product="装饰线条", line_dev_w=40, line_len_m=3, line_count=10)
        self.assertAlmostEqual(r["延米数"], 30.0, places=6)
        # 每条折 2 道边 → 折弯 60 米
        self.assertAlmostEqual(r["几何"]["折弯米数m合计"], 60.0, places=6)

    def test_超板幅产生接料处数(self):
        r = q(shape="半圆拱", opening_w=2600, opening_h=2800, wall_d=500, face_width=260, wrap="单包")
        self.assertGreaterEqual(r["几何"]["拼板接料处数"], 1)
        self.assertTrue(any("接料" in w or "拼板" in w for w in r["告警"]))


class TestCost(unittest.TestCase):
    def test_七项成本加总等于总成本(self):
        """明细各自保留两位再加总，允许 5 分以内的取整误差。"""
        r = q()
        s = sum(v for v in r["成本明细"].values())
        self.assertAlmostEqual(s, r["总成本"], delta=0.05)

    def test_物流费是体积重量最低票三者取大(self):
        r = q()
        g = r["几何"]
        vol_rate, kg_rate, floor = 180.0, 1.0, 45.0
        expect = max(g["打包体积m3合计"] * vol_rate, g["重量kg合计"] * kg_rate, floor)
        # 几何量在结果里保留三位小数，允许 0.5 元的换算差
        self.assertAlmostEqual(r["成本明细"]["物流费"], expect, delta=0.5)
        self.assertGreaterEqual(r["成本明细"]["物流费"], floor)

    def test_手动运费直接覆盖估算(self):
        r = q(freight_mode="手动填写", freight_manual=888)
        self.assertAlmostEqual(r["成本明细"]["物流费"], 888.0, places=2)

    def test_满焊无缝的焊缝等于全部展开总长(self):
        r = q(weld_mode="满焊无缝")
        self.assertAlmostEqual(r["工艺口径"]["焊缝米数"], r["几何"]["单套展开总长m"], places=3)

    def test_报价按取整元取整(self):
        r = q()
        self.assertAlmostEqual(r["建议报价合计"] % 1.0, 0.0, places=6)

    def test_加成率口径对应利润率不是30(self):
        """加成 30% ≠ 利润 30%：实际利润率 = 0.3/1.3 ≈ 23.1%。这是最常见的报价亏损原因。"""
        r = q()
        self.assertAlmostEqual(r["实际利润率"], 0.2308, places=3)

    def test_延米价模式按目标价出价(self):
        r = q(pricing_mode="延米价", target_linear_price=420)
        expect = math.ceil(420 * r["延米数"] / 1.0) * 1.0
        self.assertAlmostEqual(r["建议报价合计"], expect, places=2)
        self.assertAlmostEqual(r["延米参考价"], round(r["单套报价"] / r["延米数"], 2), places=2)

    def test_延米价低于成本要报警(self):
        r = q(pricing_mode="延米价", target_linear_price=100)
        self.assertTrue(any("亏本单" in w for w in r["告警"]))

    def test_材质越贵报价越高(self):
        a, b, c = q(material="201"), q(material="304"), q(material="316L")
        self.assertLess(a["建议报价合计"], b["建议报价合计"])
        self.assertLess(b["建议报价合计"], c["建议报价合计"])

    def test_批量摊薄单套物流成本(self):
        one, five = q(quantity=1), q(quantity=5)
        self.assertGreater(five["单套成本"], 0)
        self.assertLess(five["单套成本"] / one["单套成本"], 1.05)

    def test_缺价要明确报错而不是算错(self):
        pb = load_pricebook()
        pb["板材单价"]["304"].pop("1.2", None)
        with self.assertRaises(ValueError) as ctx:
            calculate({**BASE, "thickness": 1.2}, pb)
        self.assertIn("板材单价", str(ctx.exception))


class TestAlerts(unittest.TestCase):
    def test_201镀钛要劝改304(self):
        r = q(material="201", surface="镀钛")
        self.assertTrue(any("建议改 304" in w for w in r["告警"]))

    def test_弯曲半径低于20倍板厚要报开裂(self):
        r = q(shape="上圆角", arc_radius=10, thickness=1.0)
        self.assertTrue(any("开裂" in w for w in r["告警"]))

    def test_薄板宽套线要报波浪纹(self):
        r = q(thickness=0.6, face_width=200)
        self.assertTrue(any("波浪纹" in w for w in r["告警"]))

    def test_单包墙厚大要建议双包(self):
        r = q(wrap="单包", wall_d=500)
        self.assertTrue(any("改双包" in w for w in r["告警"]))

    def test_板材利用率低要提示套裁(self):
        r = q(opening_w=300, opening_h=600)
        self.assertTrue(any("利用率" in w for w in r["告警"]))


class TestPricebook(unittest.TestCase):
    def test_板厚键统一成一位小数(self):
        self.assertEqual(thickness_key(1), "1.0")
        self.assertEqual(thickness_key(0.6), "0.6")
        self.assertEqual(thickness_key("1.20"), "1.2")

    def test_改价后置信度升为中(self):
        reset_pricebook()
        self.assertEqual(q()["confidence_level"], "低")
        update_price_params({"焊接": {"焊缝元每米": 62.0}})
        self.assertEqual(q()["confidence_level"], "中")
        reset_pricebook()
        self.assertEqual(q()["confidence_level"], "低")

    def test_旧价表缺键自动补全新键且保留用户值(self):
        reset_pricebook()
        p = load_pricebook()
        p["板材单价"]["304"]["1.0"] = 999.0
        p.pop("折弯", None)                     # 模拟老价表没有折弯组
        from tiechi.pricebook import save_pricebook
        save_pricebook(p, mark_modified=False)
        again = load_pricebook()
        self.assertEqual(again["板材单价"]["304"]["1.0"], 999.0)   # 用户值保留
        self.assertIn("折弯", again)                               # 新键补回
        reset_pricebook()

    def test_出厂价表结构完整(self):
        for k in ["板材单价", "表面处理单价", "折弯", "焊接", "损耗率",
                  "包装", "物流", "板幅", "安装", "商务", "工厂信息", "meta"]:
            self.assertIn(k, DEFAULT_PRICEBOOK)
        for shape in ["直边", "上圆角", "半圆拱", "异形"]:
            self.assertIn(shape, DEFAULT_PRICEBOOK["损耗率"])


class TestInputs(unittest.TestCase):
    def test_默认输入是标准双包门套(self):
        d = default_inputs()
        self.assertEqual(d["product"], "门套")
        self.assertEqual(d["wrap"], "双包")
        self.assertEqual(d["manufacture_type"], "拼焊")

    def test_不传参也能算(self):
        r = calculate()
        self.assertGreater(r["建议报价合计"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
