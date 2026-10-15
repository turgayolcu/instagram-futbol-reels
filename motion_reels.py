"""
Motion Graphics + Türkçe Spiker Seslendirmeli (edge-tts) + Arka Plan Müzikli
Instagram Reels Üretim Motoru (1080x1920 @ 30fps)
Sabah (odds) ve Öğlen (coupon) videolarının sonunda 2 aşamalı
"Kayıtlı Bayim (304168)" Motion Graphics rehberi ve seslendirmesi yer alır.
"""

import argparse
import asyncio
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
DEFAULT_JSON = BASE_DIR / "default_data.json"
LOGO_PATH = ASSETS_DIR / "iddaa_logo.png"
OUTRO_STEP1_PATH = ASSETS_DIR / "outro_step1_hesabim.jpg"
OUTRO_STEP2_PATH = ASSETS_DIR / "outro_step2_bayim.jpg"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

# Resmi iddaa.com Renk Paleti
IDDAA_PRIMARY_GREEN = (0, 134, 65)      # #008641
IDDAA_SUBBAR_GREEN = (0, 107, 52)       # #006B34
IDDAA_BG_TOP = (5, 52, 26)
IDDAA_BG_BOTTOM = (3, 22, 11)
IDDAA_CARD_BG = (8, 66, 34)
IDDAA_CARD_BORDER = (0, 155, 75)
IDDAA_ODD_BOX_BG = (0, 92, 45)
IDDAA_YELLOW = (229, 230, 25)           # #E5E619
IDDAA_MINT = (165, 245, 195)
DARK_GREEN_TEXT = (4, 38, 18)
WHITE = (255, 255, 255)
ALERT_RED = (235, 20, 25)
ALERT_RED_GLOW = (255, 95, 95)

OUTRO_VOICEOVER_STEP1 = (
    "Kral oranlardan faydalanmak için iddaa nokta com'a gir, "
    "profil ayarlarından Kayıtlı Bayim kısmına tıkla,"
)
OUTRO_VOICEOVER_STEP2 = "ve fotoğraftaki gibi doldur."


def ease_out_cubic(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1.0 - pow(1.0 - x, 3)


def ease_out_back(x: float) -> float:
    x = max(0.0, min(1.0, x))
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * pow(x - 1.0, 3) + c1 * pow(x - 1.0, 2)


def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


FONTS = {
    "banner": load_font(32, True),
    "subbar": load_font(25, True),
    "cta": load_font(24, True),
    "head": load_font(20, True),
    "league": load_font(18, True),
    "match": load_font(25, True),
    "odd": load_font(22, True),
    "big_odd": load_font(28, True),
    "tot_label": load_font(32, True),
    "tot_val": load_font(46, True),
    "badge18": load_font(26, True),
    "disc": load_font(25, True),
    "outro_step": load_font(27, True),
}


def build_main_voiceover_text(payload: Dict[str, Any], mode: str) -> str:
    if mode == "odds":
        matches = payload.get("matches", [])[:12]
        top_pairs = [f"{m['home']} - {m['away']}" for m in matches[:3]]
        featured = ", ".join(top_pairs)
        return (
            f"Günün maçları ve iddaa oranları belli oldu! "
            f"Bültenin zirvesinde {featured} karşılaşmaları dikkat çekiyor."
        )
    elif mode == "coupon":
        items = payload.get("coupon", [])[:6]
        picks = [f"{c['home']} {c['away']} maçı {c['pick']}" for c in items[:3]]
        picks_str = ", ".join(picks)
        tot = payload.get("total_odd", "")
        return (
            f"Günün banko kuponu hazır! "
            f"Kuponumuzda {picks_str} seçimleriyle toplam oran {tot}!"
        )
    else:
        matches = payload.get("matches", [])[:12]
        res_list = [f"{m['home']} {m['score'].replace('-', '')} {m['away']}" for m in matches[:3]]
        res_str = ", ".join(res_list)
        return (
            f"Günün maç sonuçları! "
            f"Bugün tamamlanan karşılaşmalarda {res_str} skorları kaydedildi. "
            f"Tüm maç sonuçları ekranınızda."
        )


async def generate_tts(text: str, out_mp3: Path, voice: str = "tr-TR-AhmetNeural") -> None:
    for attempt in range(4):
        try:
            communicate = edge_tts.Communicate(text, voice=voice, rate="+6%")
            await communicate.save(str(out_mp3))
            return
        except Exception as e:
            if attempt == 3:
                # Fallback to gTTS if edge-tts endpoint is temporarily unreachable
                try:
                    from gtts import gTTS
                    tts = gTTS(text=text, lang="tr", slow=False)
                    tts.save(str(out_mp3))
                    return
                except Exception:
                    raise e
            await asyncio.sleep(1.2)


def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def build_base_gradient() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), IDDAA_BG_BOTTOM)
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(IDDAA_BG_TOP[0] * (1 - ratio) + IDDAA_BG_BOTTOM[0] * ratio)
        g = int(IDDAA_BG_TOP[1] * (1 - ratio) + IDDAA_BG_BOTTOM[1] * ratio)
        b = int(IDDAA_BG_TOP[2] * (1 - ratio) + IDDAA_BG_BOTTOM[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return img


def draw_header_and_footer(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    logo_img: Optional[Image.Image],
    payload: Dict[str, Any],
    mode: str,
    cta_text: str,
    t: float,
    total_dur: float,
) -> None:
    # Üst Header Animasyonu (Slide Down: 0.0s -> 0.45s)
    header_prog = ease_out_cubic(t / 0.45)
    header_y_offset = int((1.0 - header_prog) * -210)

    draw.rectangle([0, header_y_offset, WIDTH, header_y_offset + 130], fill=IDDAA_PRIMARY_GREEN)
    draw.rectangle([0, header_y_offset + 130, WIDTH, header_y_offset + 202], fill=IDDAA_SUBBAR_GREEN)

    if logo_img is not None:
        frame.paste(logo_img, (55, header_y_offset + 24))

    header_title = (
        payload["title"]
        if mode == "odds"
        else (payload["coupon_title"] if mode == "coupon" else payload["results_title"])
    )
    title_x = 405 if mode != "coupon" else 430
    draw.text((title_x, header_y_offset + 46), header_title, font=FONTS["banner"], fill=IDDAA_YELLOW)

    if mode in ("odds", "coupon"):
        cta_prog = ease_out_back((t - 0.25) / 0.45)
        if cta_prog > 0.05:
            w_cur = int((WIDTH - 110) * min(1.0, cta_prog))
            cx = WIDTH // 2
            bx1 = cx - w_cur // 2
            bx2 = cx + w_cur // 2
            by1 = header_y_offset + 139
            by2 = by1 + 54
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=12, fill=IDDAA_YELLOW)

            shine_pos = int(((t * 420) % 1400) - 200)
            if bx1 < shine_pos < bx2 - 60:
                draw.rounded_rectangle(
                    [shine_pos, by1 + 4, shine_pos + 55, by2 - 4],
                    radius=6,
                    fill=(250, 252, 160),
                )

            if cta_prog > 0.65:
                bbox = draw.textbbox((0, 0), cta_text, font=FONTS["cta"])
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                draw.text(
                    ((WIDTH - tw) // 2, by1 + (54 - th) // 2 - 2),
                    cta_text,
                    font=FONTS["cta"],
                    fill=DARK_GREEN_TEXT,
                )
    else:
        draw.text((60, header_y_offset + 148), payload.get("subtitle", ""), font=FONTS["subbar"], fill=WHITE)

    # Alt +18 Bilgilendirme Bandı & İlerleme Çubuğu
    fy = HEIGHT - 120
    draw.rounded_rectangle(
        [55, fy, WIDTH - 55, fy + 72],
        radius=16,
        fill=IDDAA_SUBBAR_GREEN,
        outline=IDDAA_YELLOW,
        width=2,
    )
    draw.rounded_rectangle([75, fy + 12, 159, fy + 60], radius=10, fill=(215, 35, 35))
    draw.text((86, fy + 17), "+18", font=FONTS["badge18"], fill=WHITE)
    disc_text = payload.get("disclaimer", "+18 | Sadece bilgilendirme amaçlıdır.")
    if disc_text.startswith("+18"):
        disc_text = disc_text[3:].strip()
    if disc_text.startswith("|"):
        disc_text = disc_text[1:].strip()
    draw.text((178, fy + 18), f"|  {disc_text}", font=FONTS["disc"], fill=IDDAA_YELLOW)

    bar_w = int((WIDTH - 110) * min(1.0, t / max(0.1, total_dur)))
    if bar_w > 4:
        draw.rounded_rectangle([55, fy - 12, 55 + bar_w, fy - 5], radius=3, fill=IDDAA_YELLOW)


def render_outro_scene(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    step1_img: Image.Image,
    step2_img: Image.Image,
    outro_elapsed: float,
    step1_dur: float,
    step2_dur: float,
) -> None:
    """
    Sabah (odds) ve Öğlen (coupon) Reels'lerinin sonunda çalışan 2 aşamalı Motion Graphics rehberi:
    - Aşama 1 (0 -> step1_dur): Görsel 1 (Hesabım) gösterilir ve "Kayıtlı Bayim" satırı
      kırmızı daire (circle/elips) içine alınarak anime edilir.
    - Aşama 2 (step1_dur -> step1_dur + step2_dur): Görsel 2 (Kayıtlı Bayim) gösterilir ve
      sırasıyla "Bayi No (304168)", "Bayi Adı", "Bayi Adresi" altı kırmızı çizgiyle çizilerek anime edilir.
    """
    scale = 1.38
    target_w = int(503 * scale)   # ~694 px
    target_h = int(1024 * scale)  # ~1413 px
    base_x = (WIDTH - target_w) // 2
    base_y = 320

    if outro_elapsed < step1_dur:
        # --- AŞAMA 1: GÖRSEL 1 (HESABIM -> KAYITLI BAYİM KIRMIZI DAİRE ANİMASYONU) ---
        enter_prog = ease_out_back(outro_elapsed / 0.42)
        slide_y = int((1.0 - min(1.0, enter_prog)) * 550)
        img_x = base_x
        img_y = base_y + slide_y

        # Üst Başlık Bandı
        badge_text = "ADIM 1: PROFİL > 'KAYITLI BAYİM' KISMINA TIKLA"
        draw.rounded_rectangle([55, 224, WIDTH - 55, 294], radius=16, fill=IDDAA_CARD_BG, outline=IDDAA_YELLOW, width=3)
        bbox = draw.textbbox((0, 0), badge_text, font=FONTS["outro_step"])
        tw = bbox[2] - bbox[0]
        draw.text(((WIDTH - tw) // 2, 241), badge_text, font=FONTS["outro_step"], fill=IDDAA_YELLOW)

        # Telefon Ekran Çerçevesi ve Görsel 1
        draw.rounded_rectangle(
            [img_x - 12, img_y - 12, img_x + target_w + 12, img_y + target_h + 12],
            radius=26,
            fill=WHITE,
            outline=IDDAA_YELLOW,
            width=5,
        )
        frame.paste(step1_img, (img_x, img_y))

        # "Kayıtlı Bayim" satırı koordinatları (orijinal görselde y: 525..575, x: 12..490)
        circle_start = 0.45
        circle_prog = ease_out_cubic((outro_elapsed - circle_start) / 0.75)
        if circle_prog > 0.02:
            cx1 = img_x + int(10 * scale)
            cy1 = img_y + int(516 * scale)
            cx2 = img_x + int(492 * scale)
            cy2 = img_y + int(582 * scale)

            # Nabız (Pulse) genişlemesi
            pulse = int(math.sin(outro_elapsed * 8.0) * 5) if circle_prog >= 0.95 else 0
            box = [cx1 - pulse, cy1 - pulse, cx2 + pulse, cy2 + pulse]

            end_angle = -90 + int(360 * circle_prog)
            # Dış kırmızı parlama ve ana kırmızı circle (elips) çizimi
            draw.arc(
                [box[0] - 3, box[1] - 3, box[2] + 3, box[3] + 3],
                start=-90,
                end=end_angle,
                fill=ALERT_RED_GLOW,
                width=14,
            )
            draw.arc(
                box,
                start=-90,
                end=end_angle,
                fill=ALERT_RED,
                width=9,
            )
            # İkinci tur el çizimi efekti (daha vurucu kırmızı circle görünümü için)
            if circle_prog > 0.5:
                sub_angle = -90 + int(360 * ((circle_prog - 0.5) / 0.5))
                draw.arc(
                    [box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4],
                    start=-90,
                    end=sub_angle,
                    fill=ALERT_RED,
                    width=5,
                )

    else:
        # --- AŞAMA 2: GÖRSEL 2 (BAYİ NO, BAYİ ADI, BAYİ ADRESİ KIRMIZI ALT ÇİZGİ ANİMASYONU) ---
        s2_t = outro_elapsed - step1_dur
        enter_prog = ease_out_back(s2_t / 0.40)
        slide_x = int((1.0 - min(1.0, enter_prog)) * 600)
        img_x = base_x + slide_x
        img_y = base_y

        badge_text = "ADIM 2: FOTOĞRAFTAKİ GİBİ DOLDUR (KOD: 304168)"
        draw.rounded_rectangle([55, 224, WIDTH - 55, 294], radius=16, fill=IDDAA_CARD_BG, outline=IDDAA_YELLOW, width=3)
        bbox = draw.textbbox((0, 0), badge_text, font=FONTS["outro_step"])
        tw = bbox[2] - bbox[0]
        draw.text(((WIDTH - tw) // 2, 241), badge_text, font=FONTS["outro_step"], fill=IDDAA_YELLOW)

        draw.rounded_rectangle(
            [img_x - 12, img_y - 12, img_x + target_w + 12, img_y + target_h + 12],
            radius=26,
            fill=WHITE,
            outline=IDDAA_YELLOW,
            width=5,
        )
        frame.paste(step2_img, (img_x, img_y))

        # Sırasıyla altı kırmızı çizilecek 3 alan:
        # 1) Bayi No & 304168
        # 2) Bayi Adı & SEZEK ŞANS OYUNLARI İÇ VE DIŞ TİC. LTD.ŞTİ
        # 3) Bayi Adresi & BARIŞ MAHALLESİ PEYAMİ SAFA SOKAK ÇARŞI B NO:1/9 İÇ KAPI NO:41
        underlines: List[Tuple[float, List[Tuple[int, int, int]]]] = [
            # (başlangıç_sn, [(x_start, x_end, y_pos), ...])
            (0.30, [(30, 105, 112), (30, 130, 139)]),
            (0.95, [(30, 108, 177), (30, 382, 207)]),
            (1.60, [(30, 135, 244), (30, 452, 269), (30, 222, 292)]),
        ]

        for start_delay, segs in underlines:
            u_prog = ease_out_cubic((s2_t - start_delay) / 0.50)
            if u_prog <= 0.02:
                continue
            for idx, (ox1, ox2, oy) in enumerate(segs):
                seg_prog = ease_out_cubic((u_prog - idx * 0.15) / max(0.2, 1.0 - idx * 0.15))
                if seg_prog <= 0.02:
                    continue
                lx1 = img_x + int(ox1 * scale)
                lx2 = lx1 + int((ox2 - ox1) * scale * seg_prog)
                ly = img_y + int(oy * scale)

                # Kırmızı parlama + Kalın kırmızı alt çizgi
                draw.line([(lx1, ly), (lx2, ly)], fill=ALERT_RED_GLOW, width=11)
                draw.line([(lx1, ly), (lx2, ly)], fill=ALERT_RED, width=7)
                # Çizgi ucunda hareketli kırmızı nokta
                if seg_prog < 0.98:
                    draw.ellipse([lx2 - 7, ly - 7, lx2 + 7, ly + 7], fill=ALERT_RED)


def render_frame(
    base_bg: Image.Image,
    logo_img: Optional[Image.Image],
    step1_img: Optional[Image.Image],
    step2_img: Optional[Image.Image],
    payload: Dict[str, Any],
    mode: str,
    cta_text: str,
    t: float,
    main_dur: float,
    step1_dur: float,
    step2_dur: float,
    total_dur: float,
) -> Image.Image:
    frame = base_bg.copy()
    draw = ImageDraw.Draw(frame)

    # 1) Hareketli Stadyum Spot Işığı (Motion Background)
    sweep_x = int(WIDTH * 0.5 + math.sin(t * 1.8) * 220)
    sweep_y = int(520 + math.cos(t * 1.3) * 140)
    draw.ellipse(
        [sweep_x - 360, sweep_y - 260, sweep_x + 360, sweep_y + 260],
        fill=(9, 82, 42),
    )

    # Sabah (odds) ve Öğlen (coupon) modlarında main_dur sonrasında Outro Rehber Sahnesi devreye girer
    if mode in ("odds", "coupon") and t >= main_dur and step1_img is not None and step2_img is not None:
        render_outro_scene(
            frame=frame,
            draw=draw,
            step1_img=step1_img,
            step2_img=step2_img,
            outro_elapsed=t - main_dur,
            step1_dur=step1_dur,
            step2_dur=step2_dur,
        )
        draw_header_and_footer(frame, draw, logo_img, payload, mode, cta_text, t, total_dur)
        return frame

    # Sütun Başlıkları (0.4s -> 0.7s)
    if t > 0.35:
        if mode == "odds":
            draw.text((60, 215), payload["col_odds_left"], font=FONTS["head"], fill=IDDAA_MINT)
            draw.text((715, 215), payload["col_odds_right"], font=FONTS["head"], fill=IDDAA_YELLOW)
        elif mode == "coupon":
            draw.text((60, 225), payload["col_coupon_left"], font=FONTS["head"], fill=IDDAA_MINT)
            draw.text((650, 225), payload["col_coupon_right"], font=FONTS["head"], fill=IDDAA_YELLOW)
        else:
            draw.text((60, 215), payload["col_res_left"], font=FONTS["head"], fill=IDDAA_MINT)
            draw.text((815, 215), payload["col_res_right"], font=FONTS["head"], fill=IDDAA_YELLOW)

    # Staggered (Sıralı) Kart Animasyonları
    if mode in ("odds", "results"):
        matches: List[Dict[str, Any]] = payload.get("matches", [])[:12]
        start_y = 255
        row_h = 124
        for i, m in enumerate(matches):
            row_start = 0.45 + i * 0.16
            prog = ease_out_cubic((t - row_start) / 0.42)
            if prog <= 0.01:
                continue

            slide_x = int((1.0 - prog) * 650)
            x1 = 55 + slide_x
            x2 = WIDTH - 55 + slide_x
            y1 = start_y + i * row_h
            y2 = y1 + row_h - 12

            is_featured = i < 2
            pulse_border = IDDAA_YELLOW if (is_featured and int(t * 4) % 2 == 0) else IDDAA_CARD_BORDER
            border_w = 3 if is_featured else 2

            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=14,
                fill=IDDAA_CARD_BG,
                outline=pulse_border,
                width=border_w,
            )

            match_str = f"{m['home']} - {m['away']}"[:30]
            if mode == "odds":
                draw.text((x1 + 27, y1 + 12), f"{m['time']}  |  {m['league']}", font=FONTS["league"], fill=IDDAA_YELLOW)
                draw.text((x1 + 27, y1 + 44), match_str, font=FONTS["match"], fill=WHITE)

                odds = [m.get("ms1", "-"), m.get("msx", "-"), m.get("ms2", "-")]
                for j, val in enumerate(odds):
                    odd_prog = ease_out_back((t - (row_start + 0.12 + j * 0.05)) / 0.30)
                    if odd_prog <= 0.05:
                        continue
                    bx = x1 + 645 + j * 104
                    draw.rounded_rectangle(
                        [bx, y1 + 22, bx + 92, y1 + 88],
                        radius=10,
                        fill=IDDAA_ODD_BOX_BG,
                        outline=IDDAA_YELLOW,
                        width=2,
                    )
                    draw.text((bx + 17, y1 + 39), str(val), font=FONTS["odd"], fill=IDDAA_YELLOW)
            else:
                draw.text((x1 + 27, y1 + 12), f"MS  |  {m['league']}", font=FONTS["league"], fill=IDDAA_MINT)
                draw.text((x1 + 27, y1 + 44), match_str, font=FONTS["match"], fill=WHITE)

                sx = x1 + 760
                draw.rounded_rectangle(
                    [sx, y1 + 20, sx + 175, y1 + 88],
                    radius=12,
                    fill=IDDAA_PRIMARY_GREEN,
                    outline=IDDAA_YELLOW,
                    width=2,
                )
                draw.text((sx + 50, y1 + 36), str(m.get("score", "0 - 0")), font=FONTS["match"], fill=IDDAA_YELLOW)

    else:
        items = payload.get("coupon", [])[:8]
        start_y = 270
        row_h = 165
        for i, c in enumerate(items):
            row_start = 0.50 + i * 0.32
            prog = ease_out_cubic((t - row_start) / 0.48)
            if prog <= 0.01:
                continue

            slide_x = int((1.0 - prog) * -700)
            x1 = 55 + slide_x
            x2 = WIDTH - 55 + slide_x
            y1 = start_y + i * row_h
            y2 = y1 + row_h - 18

            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=18,
                fill=IDDAA_CARD_BG,
                outline=IDDAA_YELLOW,
                width=2,
            )

            match_str = f"{c['home']} - {c['away']}"[:28]
            draw.text((x1 + 30, y1 + 22), f"{c['time']}  |  {c['league']}", font=FONTS["league"], fill=IDDAA_MINT)
            draw.text((x1 + 30, y1 + 62), match_str, font=FONTS["match"], fill=WHITE)

            px = x1 + 560
            draw.rounded_rectangle(
                [px, y1 + 35, px + 225, y1 + 111],
                radius=12,
                fill=IDDAA_ODD_BOX_BG,
                outline=IDDAA_CARD_BORDER,
                width=2,
            )
            draw.text((px + 20, y1 + 56), str(c["pick"]), font=FONTS["odd"], fill=WHITE)

            ox = x1 + 805
            draw.rounded_rectangle([ox, y1 + 35, ox + 135, y1 + 111], radius=12, fill=IDDAA_YELLOW)
            draw.text((ox + 32, y1 + 52), str(c["odd"]), font=FONTS["big_odd"], fill=DARK_GREEN_TEXT)

        tot_start = 0.65 + len(items) * 0.32
        tot_prog = ease_out_back((t - tot_start) / 0.50)
        if tot_prog > 0.05:
            tot_y = start_y + len(items) * row_h + 25
            pulse_pad = int(math.sin(t * 6.0) * 6) if t > tot_start + 0.5 else 0
            draw.rounded_rectangle(
                [55 - pulse_pad, tot_y - pulse_pad, WIDTH - 55 + pulse_pad, tot_y + 115 + pulse_pad],
                radius=20,
                fill=IDDAA_YELLOW,
            )
            draw.text((95, tot_y + 34), payload["total_odd_label"], font=FONTS["tot_label"], fill=DARK_GREEN_TEXT)
            draw.text((825, tot_y + 24), str(payload["total_odd"]), font=FONTS["tot_val"], fill=DARK_GREEN_TEXT)

    draw_header_and_footer(frame, draw, logo_img, payload, mode, cta_text, t, total_dur)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["odds", "coupon", "results"], default="odds")
    parser.add_argument("--category", choices=["spor", "tjk", "millipiyango"], default="spor")
    parser.add_argument("--data", default="")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = Path(args.data) if args.data and Path(args.data).exists() else DEFAULT_JSON
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    cta_text = {
        "tjk": payload.get("cta_tjk", ""),
        "millipiyango": payload.get("cta_mp", ""),
        "spor": payload.get("cta_spor", ""),
    }.get(args.category, payload.get("cta_spor", ""))

    # 1) Türkçe Spiker Seslendirmesini (TTS) Üret
    main_vo_text = build_main_voiceover_text(payload, args.mode)
    main_mp3 = OUTPUT_DIR / f"vo_main_{args.mode}.mp3"
    tts_mp3 = OUTPUT_DIR / f"vo_{args.mode}.mp3"

    if args.mode in ("odds", "coupon"):
        outro1_mp3 = OUTPUT_DIR / f"vo_outro1_{args.mode}.mp3"
        outro2_mp3 = OUTPUT_DIR / f"vo_outro2_{args.mode}.mp3"
        print(f"[1/3] Türkçe spiker seslendirmesi üretiliyor ({args.mode} + Kayıtlı Bayim rehberi)...")
        asyncio.run(generate_tts(main_vo_text, main_mp3))
        asyncio.run(generate_tts(OUTRO_VOICEOVER_STEP1, outro1_mp3))
        asyncio.run(generate_tts(OUTRO_VOICEOVER_STEP2, outro2_mp3))

        d_main_vo = get_audio_duration(main_mp3)
        d_outro1_vo = get_audio_duration(outro1_mp3)
        d_outro2_vo = get_audio_duration(outro2_mp3)

        main_dur = max(4.8, d_main_vo + 0.35)
        step1_dur = max(3.6, d_outro1_vo + 0.25)
        step2_dur = max(3.4, d_outro2_vo + 1.85)
        total_dur = main_dur + step1_dur + step2_dur

        # 3 ses parçasını tam zamanlamayla birleştir
        delay_s1_ms = int(main_dur * 1000)
        delay_s2_ms = int((main_dur + step1_dur) * 1000)
        concat_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(main_mp3),
            "-i", str(outro1_mp3),
            "-i", str(outro2_mp3),
            "-filter_complex",
            f"[0:a] volume=1.0 [a0];"
            f"[1:a] adelay={delay_s1_ms}|{delay_s1_ms},volume=1.0 [a1];"
            f"[2:a] adelay={delay_s2_ms}|{delay_s2_ms},volume=1.0 [a2];"
            f"[a0][a1][a2] amix=inputs=3:duration=longest:normalize=0 [out]",
            "-map", "[out]",
            "-t", f"{total_dur:.2f}",
            str(tts_mp3),
        ]
        subprocess.run(concat_cmd, check=True)
    else:
        print(f"[1/3] Türkçe spiker seslendirmesi üretiliyor: \"{main_vo_text}\"")
        asyncio.run(generate_tts(main_vo_text, tts_mp3))
        vo_dur = get_audio_duration(tts_mp3)
        main_dur = max(8.0, min(15.0, vo_dur + 1.4))
        step1_dur = 0.0
        step2_dur = 0.0
        total_dur = main_dur

    total_frames = int(total_dur * FPS)

    # 2) Ses Miksajı (Spiker Sesi + Arka Plan Müziği)
    mixed_audio = OUTPUT_DIR / f"mixed_{args.mode}.m4a"
    custom_music = ASSETS_DIR / "bg_music.mp3"
    if custom_music.exists():
        audio_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(tts_mp3),
            "-stream_loop", "-1", "-i", str(custom_music),
            "-filter_complex",
            f"[0:a]volume=1.45,apad[vo];[1:a]volume=0.15,afade=t=in:st=0:d=0.6,afade=t=out:st={total_dur-1.2}:d=1.2[bg];[vo][bg]amix=inputs=2:duration=shortest:normalize=0[a]",
            "-map", "[a]", "-t", f"{total_dur:.2f}", "-c:a", "aac", "-b:a", "192k",
            str(mixed_audio),
        ]
    else:
        af_synth = (
            f"aevalsrc='0.14*sin(2*PI*73.42*t)+0.11*sin(2*PI*110*t)+0.09*sin(2*PI*146.83*t)"
            f"+0.08*sin(2*PI*220*t)*(0.55+0.45*sin(2*PI*2.0*t))':s=44100:d={total_dur:.2f}"
        )
        audio_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(tts_mp3),
            "-f", "lavfi", "-i", af_synth,
            "-filter_complex",
            f"[0:a]volume=1.45,apad[vo];[1:a]volume=0.20,afade=t=in:st=0:d=0.5,afade=t=out:st={total_dur-1.2}:d=1.2[bg];[vo][bg]amix=inputs=2:duration=shortest:normalize=0[a]",
            "-map", "[a]", "-t", f"{total_dur:.2f}", "-c:a", "aac", "-b:a", "192k",
            str(mixed_audio),
        ]
    subprocess.run(audio_cmd, check=True)

    # 3) 30 FPS Motion Graphics Karelerini FFmpeg'e Akıt (Pipe)
    poster_path = OUTPUT_DIR / f"reels_{args.mode}_latest.png"
    video_path = OUTPUT_DIR / f"reels_{args.mode}_latest.mp4"

    base_bg = build_base_gradient()
    logo_img = Image.open(LOGO_PATH).convert("RGB").resize((305, 80)) if LOGO_PATH.exists() else None

    scale = 1.38
    target_size = (int(503 * scale), int(1024 * scale))
    step1_img = (
        Image.open(OUTRO_STEP1_PATH).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
        if OUTRO_STEP1_PATH.exists()
        else None
    )
    step2_img = (
        Image.open(OUTRO_STEP2_PATH).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
        if OUTRO_STEP2_PATH.exists()
        else None
    )

    # Bülten tablosunun tam halini kapak görseli olarak kaydet
    cover_frame = render_frame(
        base_bg, logo_img, step1_img, step2_img, payload, args.mode, cta_text,
        max(0.5, main_dur - 0.2), main_dur, step1_dur, step2_dur, total_dur
    )
    cover_frame.save(poster_path)

    print(f"[2/3] 30 FPS Motion Graphics kareleri işleniyor ({total_frames} kare, {total_dur:.1f} sn)...")
    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        "-i", str(mixed_audio),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest",
        str(video_path),
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    for f_idx in range(total_frames):
        t = f_idx / FPS
        frame = render_frame(
            base_bg, logo_img, step1_img, step2_img, payload, args.mode, cta_text,
            t, main_dur, step1_dur, step2_dur, total_dur
        )
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg video birleştirme hatası: {proc.returncode}")

    print(f"[3/3] Motion Graphics + Seslendirmeli Reels hazır: {video_path}")


if __name__ == "__main__":
    main()
