"""產生各桌點餐 QR Code。

每張 QR Code 編碼的網址：{FRONTEND_BASE}/order?table={桌號}
顧客手機掃碼 → 開啟 OrderView → 自動依桌號開桌點餐。

用法：
    python gen_qrcodes.py
    python gen_qrcodes.py --base https://your-frontend.onrender.com --tables 1-20
"""
from __future__ import annotations

import argparse
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

FRONTEND_BASE = "https://food-order-system-front.onrender.com"
OUT_DIR = Path(__file__).resolve().parents[1].parent / "qrcodes"


def parse_tables(spec: str) -> list[str]:
    """支援 "1-10" 或 "1,2,5" 或混合 "1-3,7"。"""
    out: list[str] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-")
            out.extend(str(n) for n in range(int(lo), int(hi) + 1))
        elif part:
            out.append(part)
    return out


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("msjh.ttc", "msjhbd.ttc", "msyh.ttc", "simhei.ttf",
                 "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_card(table_no: str, base: str) -> Image.Image:
    url = f"{base}/order?table={table_no}"

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    qw, qh = qr_img.size
    pad, label_h = 40, 90
    card = Image.new("RGB", (qw + pad * 2, qh + pad + label_h), "white")
    card.paste(qr_img, (pad, pad))

    draw = ImageDraw.Draw(card)
    big = load_font(48)
    small = load_font(22)

    title = f"桌號 {table_no}"
    tb = draw.textbbox((0, 0), title, font=big)
    draw.text(((card.width - (tb[2] - tb[0])) / 2, qh + pad + 6),
              title, fill="black", font=big)

    tip = "掃描開始點餐"
    sb = draw.textbbox((0, 0), tip, font=small)
    draw.text(((card.width - (sb[2] - sb[0])) / 2, qh + pad + 58),
              tip, fill="#666666", font=small)

    return card


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=FRONTEND_BASE, help="前端網址（不含結尾斜線）")
    ap.add_argument("--tables", default="1-10", help='桌號範圍，例 "1-10" 或 "1,2,5"')
    ap.add_argument("--out", default=str(OUT_DIR), help="輸出資料夾")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for t in parse_tables(args.tables):
        card = make_card(t, base)
        path = out_dir / f"table-{t}.png"
        card.save(path)
        print(f"  [OK] {path}  ->  {base}/order?table={t}")

    print(f"\nDone! QR codes saved to: {out_dir}")


if __name__ == "__main__":
    main()
