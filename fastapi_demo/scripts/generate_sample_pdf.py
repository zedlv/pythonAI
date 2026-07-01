#!/usr/bin/env python3
"""生成 D1 自测用储能 BMS 故障代码手册 PDF（含中文与表格）"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from config import ASSET_DOC_DIR

OUTPUT = os.path.join(ASSET_DOC_DIR, "BMS故障代码手册.pdf")

PAGES = [
    """第 1 页 | 储能技术手册

BMS 故障代码手册（节选）

设备型号：BMS-X200 / BMS-X500
额定功率：200kW / 500kW
通信协议：CAN 2.0B

故障代码 E001：单体过压
触发条件：单体电压 > 3.65V 持续 3s
建议动作：降低充电电流，检查均衡模块

故障代码 E002：单体欠压
触发条件：单体电压 < 2.80V 持续 3s
建议动作：停止放电，执行补电流程
""",
    """第 2 页 | 储能技术手册

故障代码 E101：PACK 过温
触发条件：模组温度 > 55℃
建议动作：降功率运行，检查风冷系统

故障代码 E203：绝缘阻抗低
触发条件：绝缘电阻 < 500kΩ
建议动作：立即停机，排查直流线缆

故障代码 E305：主控通信中断
触发条件：CAN 总线 5s 无心跳
建议动作：检查终端电阻与接线端子

附表：功率降额建议
50℃ 以上降额至 80%
55℃ 以上降额至 50%
""",
]


def main() -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except ImportError:
        print("请先安装: pip install reportlab")
        sys.exit(1)

    os.makedirs(ASSET_DOC_DIR, exist_ok=True)

    font_candidates = [
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    font_name = "Helvetica"
    for path in font_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("CJK", path))
                font_name = "CJK"
                break
            except Exception:
                continue

    c = canvas.Canvas(OUTPUT, pagesize=A4)
    width, height = A4
    for page_text in PAGES:
        c.setFont(font_name, 11)
        y = height - 50
        for line in page_text.split("\n"):
            if line.strip():
                c.drawString(50, y, line[:90])
            y -= 16
            if y < 50:
                break
        c.showPage()
    c.save()
    print(f"已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
