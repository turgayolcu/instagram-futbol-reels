"""
İDDAALIYIZ TV — Romelu Lukaku Dergi Kapak / Poster Kalitesinde Manşet Reels Üreticisi (1080x1920 @ 30fps)
Referans tasarım ('ROMA'DA ARDA İMZASI!') birebir temel alınarak:
- Üstte yeşil iddaa şeridi + dev sarı/beyaz grunge 'İDDAALIYIZ TV' başlığı ve stadyum spot ışıkları
- Arka planda siyah-beyaz ikincil Lukaku pozları + yırtık kağıt (torn paper) kolaj geçişleri + kulüp logoları
- Sağ üstte eğimli 'BİZİM MAÇIN ADAMI: ROMELU LUKAKU (Editoryal seçim)' mühür rozeti
- Merkezde dev gerçek Romelu Lukaku dekupe (cutout) portresi
- Ortada eğimli dev 'KADIKÖY'DE / LUKAKU İMZASI!' manşet tipografisi
- Altta yırtık kağıt efektli skor ve 3 sütunlu istatistik paneli (FENERBAHÇE 3-0 ALANYASPOR)
- Kayıtlı Bayim (304168) kısmı gelene kadar sinematik Lukaku posteri üzerinden ilerler,
  sonunda 2 aşamalı Kayıtlı Bayim (304168) animasyonu ve erkek spiker dış sesi yer alır.
"""

import asyncio
import math
import os
import random
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from motion_reels import (
    ASSETS_DIR,
    FPS,
    HEIGHT,
    IDDAA_PRIMARY_GREEN,
    LOGO_PATH,
    OUTPUT_DIR,
    OUTRO_STEP1_PATH,
    OUTRO_STEP2_PATH,
    OUTRO_VOICEOVER_STEP1,
    OUTRO_VOICEOVER_STEP2,
    STATIC_OUTRO1_MP3,
    STATIC_OUTRO2_MP3,
    WIDTH,
    WHITE,
    build_base_gradient,
    draw_header_and_footer,
    ease_out_back,
    ease_out_cubic,
    generate_tts,
    get_audio_duration,
    load_font,
    render_outro_scene,
)

GLOBAL_MUSIC_PATH = ASSETS_DIR / "global_trend_music.mp3"
NEON_YELLOW = (246, 232, 24)
DARK_EMERALD = (4, 34, 18)
DEEP_BLACK_GREEN = (3, 18, 10)
PAPER_WHITE = (238, 242, 238)
PAPER_SHADOW = (15, 25, 20)

LUKAKU_POSTER_VOICEOVER = (
    "Kadıköy'de Lukaku imzası! "
    "Trendyol Süper Lig'de Fenerbahçe, sahasında Alanyaspor'u 3 0 mağlup ederken "
    "gecenin mimarı Romelu Lukaku oldu! "
    "Kırkıncı dakikada Levent Mercan'ın asistinde kilidi açan golü kaydeden Belçikalı yıldız, "
    "seksen bir dakika sahada kalarak rakip savunmayı adeta dağıttı! "
    "İkinci yarıda Kerem Aktürkoğlu ve Vedat Muriqi'nin golleriyle farka giden sarı lacivertlilerde "
    "bizim maçın adamı Romelu Lukaku!"
)


def load_impact_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\bahnschrift.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return load_font(size, True)


def load_italic_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\arialbi.ttf" if bold else r"C:\Windows\Fonts\ariali.ttf",
        r"C:\Windows\Fonts\segoeuiz.ttf" if bold else r"C:\Windows\Fonts\segoeuii.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return load_font(size, bold)


def make_torn_edge_points(y_base: int, x_start: int, x_end: int, amp: int, seed: int) -> List[Tuple[int, int]]:
    rng = random.Random(seed)
    pts = []
    x = x_start
    while x <= x_end:
        dy = rng.randint(-amp, amp)
        pts.append((x, y_base + dy))
        x += rng.randint(14, 32)
    if pts[-1][0] < x_end:
        pts.append((x_end, y_base + rng.randint(-amp, amp)))
    return pts


def draw_torn_paper_divider(
    img: Image.Image,
    y_pos: int,
    fill_below: Optional[Tuple[int, int, int, int]] = None,
    seed: int = 42,
    thickness: int = 16,
) -> None:
    """Referans posterdeki tırtıklı beyaz/gri yırtık kağıt (torn paper) geçişini çizer."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    top_pts = make_torn_edge_points(y_pos, 0, WIDTH, amp=14, seed=seed)
    bot_pts = [(x, y + thickness) for (x, y) in reversed(top_pts)]

    # Gölge katmanı
    shadow_pts = [(x, y - 6) for (x, y) in top_pts] + [(x, y + thickness + 8) for (x, y) in reversed(top_pts)]
    d.polygon(shadow_pts, fill=(0, 0, 0, 150))

    if fill_below is not None:
        below_poly = top_pts + [(WIDTH, HEIGHT), (0, HEIGHT)]
        d.polygon(below_poly, fill=fill_below)

    # Beyaz yırtık kağıt dokusu
    d.polygon(top_pts + bot_pts, fill=(235, 240, 236, 245))
    inner_pts = [(x, y + 5) for (x, y) in top_pts] + [(x, y + thickness - 3) for (x, y) in reversed(top_pts)]
    d.polygon(inner_pts, fill=(200, 208, 202, 210))

    img.alpha_composite(overlay)


def draw_stadium_floodlight(canvas: Image.Image, cx: int, cy: int, radius: int = 230) -> None:
    """Üst köşelerdeki stadyum projektör ışık parlamalarını çizer."""
    light = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(light)
    for r in range(radius, 10, -12):
        alpha = int(175 * pow(1.0 - r / radius, 2.2))
        col = (255, 252, 225, alpha) if r < radius * 0.45 else (195, 245, 210, alpha)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    # LED projektör ızgara noktaları
    for gx in range(-2, 3):
        for gy in range(-1, 2):
            px = cx + gx * 22
            py = cy + gy * 22
            d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(255, 255, 255, 235))
    canvas.alpha_composite(light)


def draw_grunge_text_layer(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    shadow_offset: int = 10,
    angle: float = 0.0,
    seed: int = 101,
) -> Image.Image:
    """Referans posterdeki kalın 3D siyah gölgeli, hafif eskitme (grunge) dokulu dev manşet yazısını üretir."""
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0] + 80
    th = bbox[3] - bbox[1] + 80

    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = 40 - bbox[0], 40 - bbox[1]

    # Kalın siyah 3D dış kontur ve alt gölge
    for dx in range(-6, 7, 3):
        for dy in range(-6, 7, 3):
            d.text((ox + dx, oy + dy), text, font=font, fill=(0, 0, 0, 255))
    for s in range(1, shadow_offset + 1):
        d.text((ox + s, oy + s + 2), text, font=font, fill=(0, 0, 0, 255))

    # Ana renk metin
    d.text((ox, oy), text, font=font, fill=(*fill, 255))

    # Hafif grunge eskitme (küçük koyu benekler)
    rng = random.Random(seed)
    for _ in range(140):
        gx = rng.randint(20, tw - 20)
        gy = rng.randint(20, th - 20)
        gr = rng.randint(1, 3)
        d.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=(8, 28, 16, 150))

    if abs(angle) > 0.05:
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    return layer


def build_editorial_badge() -> Image.Image:
    """Sağ üstteki eğimli 'BİZİM MAÇIN ADAMI: ROMELU LUKAKU (Editoryal seçim)' mühür rozetini üretir."""
    size = 330
    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(badge)
    cx, cy = size // 2, size // 2

    # Koyu yeşil iç daire + çift sarı grunge çember
    d.ellipse([14, 14, size - 14, size - 14], fill=(4, 34, 18, 240), outline=(*NEON_YELLOW, 255), width=8)
    d.ellipse([26, 26, size - 26, size - 26], outline=(*NEON_YELLOW, 200), width=3)

    # Küçük taç ikonu
    crown_pts = [
        (cx - 24, 58),
        (cx - 28, 38),
        (cx - 12, 48),
        (cx, 34),
        (cx + 12, 48),
        (cx + 28, 38),
        (cx + 24, 58),
    ]
    d.polygon(crown_pts, outline=(*NEON_YELLOW, 255), fill=(4, 34, 18, 255), width=3)

    f_top = load_impact_font(38)
    f_mid = load_impact_font(42)
    f_name = load_impact_font(38)
    f_sub = load_font(19, True)

    for txt, font, y_pos, col in [
        ("BİZİM", f_top, 68, WHITE),
        ("MAÇIN ADAMI", f_mid, 112, NEON_YELLOW),
        ("ROMELU LUKAKU", f_name, 162, WHITE),
        ("Editoryal seçim", f_sub, 232, (215, 235, 220)),
    ]:
        bb = d.textbbox((0, 0), txt, font=font)
        tw = bb[2] - bb[0]
        d.text(((size - tw) // 2, y_pos), txt, font=font, fill=(*col, 255))

    # Sarı fırça çizgisi (ROMELU LUKAKU altında)
    d.line([(55, 214), (size - 55, 210)], fill=(*NEON_YELLOW, 255), width=6)

    return badge.rotate(6.5, resample=Image.Resampling.BICUBIC, expand=True)


def prepare_bw_duotone_cutout(
    path: Path, target_size: Tuple[int, int], crop_left_ratio: float = 0.0, crop_right_ratio: float = 1.0
) -> Optional[Image.Image]:
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA")
    if crop_left_ratio > 0.0 or crop_right_ratio < 1.0:
        w0, h0 = img.size
        img = img.crop((int(w0 * crop_left_ratio), 0, int(w0 * crop_right_ratio), h0))
    img = ImageOps.contain(img, target_size, method=Image.Resampling.LANCZOS)
    r, g, b, a = img.split()
    gray = ImageOps.grayscale(Image.merge("RGB", (r, g, b)))
    gray = ImageEnhance.Contrast(gray).enhance(1.38)
    duotone = ImageOps.colorize(gray, black="#041A0E", mid="#788A80", white="#F2F7F4")
    out = duotone.convert("RGBA")
    out.putalpha(a)
    return out


def prepare_hero_cutout(path: Path, target_size: Tuple[int, int]) -> Optional[Image.Image]:
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA")
    img = ImageOps.contain(img, target_size, method=Image.Resampling.LANCZOS)
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Contrast(rgb).enhance(1.16)
    rgb = ImageEnhance.Color(rgb).enhance(1.12)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.35)

    # Omuzların sol, sağ ve alt kesim kenarlarını yumuşakça (feather) erit ki sert dikey çizgi kalmasın
    w, h = img.size
    fade_mask = Image.new("L", (w, h), 255)
    fm_pix = fade_mask.load()
    for y in range(h):
        # Sadece omuz seviyesinin altında (y > h * 0.48) yan kenarları yumuşat
        y_factor = max(0.0, (y - h * 0.45) / (h * 0.55))
        bot_fade = 1.0 if y < h * 0.82 else max(0.0, (h - y) / (h * 0.18))
        for x in range(w):
            side_fade = 1.0
            if y_factor > 0.0:
                margin = int(w * 0.16 * y_factor)
                if margin > 4:
                    if x < margin:
                        side_fade = x / margin
                    elif x > w - margin:
                        side_fade = (w - x) / margin
            fm_pix[x, y] = int(255 * min(1.0, side_fade) * bot_fade)

    a = ImageChops.multiply(a, fade_mask)

    canvas = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 210))
    shadow.putalpha(a.point(lambda p: int(p * 0.75)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    canvas.alpha_composite(shadow, (28, 28))

    hero_rgba = rgb.convert("RGBA")
    hero_rgba.putalpha(a)
    canvas.alpha_composite(hero_rgba, (20, 20))
    return canvas


def build_lukaku_master_poster() -> Tuple[Image.Image, Optional[Image.Image], Image.Image]:
    """
    Poster katmanlarını hazırlar:
    1) bg_collage: Gerçek Kadıköy stadyum atmosferi + ikincil siyah-beyaz pozlar + kulüp armaları + üst İDDAALIYIZ TV logosu
    2) hero_cutout: Merkezdeki dev Romelu Lukaku cutout katmanı
    3) fg_overlay: Dev 'KADIKÖY'DE / LUKAKU İMZASI!' manşeti + sağ üst mühür + alt yırtık kağıt skor ve istatistik paneli
    """
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (*DARK_EMERALD, 255))
    bg_draw = ImageDraw.Draw(bg)

    # Koyu zümrüt stadyum gradyanı
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(8 * (1 - ratio) + 2 * ratio)
        g = int(58 * (1 - ratio) + 18 * ratio)
        b = int(30 * (1 - ratio) + 10 * ratio)
        bg_draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # Gerçek Kadıköy Şükrü Saracoğlu Stadyumu fotoğrafını arka plana zümrüt/altın tonlamayla yedir
    stad_path = ASSETS_DIR / "kadikoy_stadium.jpg"
    if stad_path.exists():
        stad = ImageOps.fit(stad_path_img := Image.open(stad_path).convert("RGB"), (WIDTH, 980), method=Image.Resampling.LANCZOS)
        stad_gray = ImageOps.grayscale(stad)
        stad_tinted = ImageOps.colorize(stad_gray, black="#031C0E", mid="#10522B", white="#E8D268").convert("RGBA")
        stad_mask = Image.new("L", (WIDTH, 980), 0)
        sm_draw = ImageDraw.Draw(stad_mask)
        for sy in range(980):
            alpha_v = int(135 * math.sin(math.pi * (sy / 980.0)))
            sm_draw.line([(0, sy), (WIDTH, sy)], fill=alpha_v)
        stad_tinted.putalpha(stad_mask)
        bg.alpha_composite(stad_tinted, (0, 60))

    # Sol ve sağ üst stadyum projektörleri
    draw_stadium_floodlight(bg, 65, 160, radius=235)
    draw_stadium_floodlight(bg, WIDTH - 65, 160, radius=235)

    # 1) ÜST YEŞİL İDDAA ŞERİDİ & BİTİŞİK DEV 'İDDAALIYIZ TV' BAŞLIĞI
    bg_draw.rectangle([355, 0, 725, 74], fill=(*IDDAA_PRIMARY_GREEN, 255))
    if LOGO_PATH.exists():
        iddaa_logo = Image.open(LOGO_PATH).convert("RGBA").resize((240, 62), Image.Resampling.LANCZOS)
        bg.alpha_composite(iddaa_logo, ((WIDTH - 240) // 2, 7))

    f_brand = load_impact_font(134)
    brand_iddaa = draw_grunge_text_layer("İDDAALIYIZ", f_brand, NEON_YELLOW, shadow_offset=9, angle=0.0, seed=11)
    brand_tv = draw_grunge_text_layer("TV", f_brand, WHITE, shadow_offset=9, angle=-2.5, seed=22)

    total_brand_w = brand_iddaa.width + brand_tv.width - 55
    start_bx = (WIDTH - total_brand_w) // 2
    bg.alpha_composite(brand_iddaa, (start_bx, 46))
    bg.alpha_composite(brand_tv, (start_bx + brand_iddaa.width - 55, 44))

    # 'İDDAALIYIZ TV' altındaki sarı grunge fırça darbesi
    bg_draw.polygon([(start_bx + 35, 206), (start_bx + total_brand_w - 30, 194), (start_bx + total_brand_w - 10, 202), (start_bx + 35, 214)], fill=(*NEON_YELLOW, 235))

    # 2) SOL VE SAĞ İKİNCİL SİYAH-BEYAZ LUKAKU POZLARI + YIRTIK KAĞIT KOLAJI
    left_bw = prepare_bw_duotone_cutout(
        ASSETS_DIR / "cutout_lukaku_pose_3.png", (510, 540), crop_left_ratio=0.12, crop_right_ratio=0.98
    )
    if left_bw is not None:
        bg.alpha_composite(left_bw, (-20, 215))

    right_bw = prepare_bw_duotone_cutout(
        ASSETS_DIR / "cutout_lukaku_pose_1.png", (470, 540), crop_left_ratio=0.0, crop_right_ratio=1.0
    )
    if right_bw is not None:
        bg.alpha_composite(right_bw, (615, 285))

    # Sol ve sağ kolaj yırtık kağıt şeritleri
    draw_torn_paper_divider(bg, y_pos=575, fill_below=None, seed=77, thickness=14)

    # Sol ve sağ kulüp armaları
    fb_logo_path = ASSETS_DIR / "logo_fenerbahce.png"
    al_logo_path = ASSETS_DIR / "logo_alanyaspor.png"
    if fb_logo_path.exists():
        fb_big = Image.open(fb_logo_path).convert("RGBA").resize((230, 230), Image.Resampling.LANCZOS)
        fb_tilted = fb_big.rotate(-14, resample=Image.Resampling.BICUBIC, expand=True)
        bg.alpha_composite(fb_tilted, (855, 650))
        fb_left = Image.open(fb_logo_path).convert("RGBA").resize((175, 175), Image.Resampling.LANCZOS).rotate(10, expand=True)
        bg.alpha_composite(fb_left, (22, 600))

    # 3) MERKEZ DEV ROMELU LUKAKU HERO CUTOUT
    hero_path = ASSETS_DIR / "cutout_lukaku_real.png"
    if not hero_path.exists():
        hero_path = ASSETS_DIR / "lukaku_real.jpg"
    hero_cutout = prepare_hero_cutout(hero_path, (880, 1020))

    # 4) ÖN PLAN (FG OVERLAY): SAĞ ÜST MÜHÜR + DEV MANŞET + ALT YIRTIK KAĞIT İSTATİSTİK PANELİ
    fg = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    fg_draw = ImageDraw.Draw(fg)

    # Sağ üst 'BİZİM MAÇIN ADAMI: ROMELU LUKAKU' mühür rozeti
    stamp_img = build_editorial_badge()
    fg.alpha_composite(stamp_img, (695, 198))

    # Manşet arkası koyu zümrüt/sarı fırça alanı ve yırtık kağıt geçişi
    draw_torn_paper_divider(fg, y_pos=965, fill_below=(4, 32, 16, 235), seed=123, thickness=16)

    # Dev Eğimli 'KADIKÖY'DE' ve 'LUKAKU İMZASI!' Manşeti
    f_hl1 = load_impact_font(152)
    f_hl2 = load_impact_font(148)
    hl1_img = draw_grunge_text_layer("KADIKÖY'DE", f_hl1, WHITE, shadow_offset=12, angle=3.2, seed=301)
    hl2_img = draw_grunge_text_layer("LUKAKU İMZASI!", f_hl2, NEON_YELLOW, shadow_offset=12, angle=3.2, seed=302)

    fg.alpha_composite(hl1_img, ((WIDTH - hl1_img.width) // 2, 920))
    fg.alpha_composite(hl2_img, ((WIDTH - hl2_img.width) // 2, 1085))

    # Alt Skor & İstatistik Panelini Ayıran Yırtık Kağıt Şeridi
    draw_torn_paper_divider(fg, y_pos=1330, fill_below=(3, 24, 12, 252), seed=456, thickness=16)

    # Skor Satırı: [FB Logo]  FENERBAHÇE  3-0  ALANYASPOR  [Alanya Logo]
    if fb_logo_path.exists():
        fb_sm = Image.open(fb_logo_path).convert("RGBA").resize((104, 104), Image.Resampling.LANCZOS)
        fg.alpha_composite(fb_sm, (82, 1362))
    if al_logo_path.exists():
        al_sm = Image.open(al_logo_path).convert("RGBA").resize((104, 104), Image.Resampling.LANCZOS)
        fg.alpha_composite(al_sm, (WIDTH - 186, 1362))

    f_team = load_impact_font(50)
    f_score = load_impact_font(88)
    f_date = load_font(21, True)

    fg_draw.text((205, 1378), "FENERBAHÇE", font=f_team, fill=WHITE)
    fg_draw.text((472, 1348), "3-0", font=f_score, fill=NEON_YELLOW)
    fg_draw.text((628, 1378), "ALANYASPOR", font=f_team, fill=WHITE)

    # Tarih ve Lig Alt Çizgisi
    date_txt = "17 EKİM 2026  •  TRENDYOL SÜPER LİG"
    db = fg_draw.textbbox((0, 0), date_txt, font=f_date)
    dw = db[2] - db[0]
    dx = (WIDTH - dw) // 2
    fg_draw.line([(215, 1456), (dx - 18, 1456)], fill=(180, 210, 190, 190), width=2)
    fg_draw.text((dx, 1442), date_txt, font=f_date, fill=(215, 235, 220, 255))
    fg_draw.line([(dx + dw + 18, 1456), (WIDTH - 215, 1456)], fill=(180, 210, 190, 190), width=2)

    # Yatay İnce Çizgi
    fg_draw.line([(85, 1485), (WIDTH - 85, 1485)], fill=(90, 145, 110, 160), width=2)

    # 3 Sütunlu Dev Sarı İstatistik Kutuları (Referans posterdeki '2 ASİST | 3 GOL FIRSATI | 59 OYUNA GİRİŞ' gibi)
    f_stat_num = load_impact_font(82)
    f_stat_lbl = load_impact_font(34)

    cols = [
        ("40'", "KİLİDİ AÇAN GOL", 215),
        ("5", "TOPLAM ŞUT", 540),
        ("81'", "SAHADA KALDI", 865),
    ]
    for num_str, lbl_str, cx_col in cols:
        nb = fg_draw.textbbox((0, 0), num_str, font=f_stat_num)
        nw = nb[2] - nb[0]
        fg_draw.text((cx_col - nw // 2, 1496), num_str, font=f_stat_num, fill=NEON_YELLOW)

        lb = fg_draw.textbbox((0, 0), lbl_str, font=f_stat_lbl)
        lw = lb[2] - lb[0]
        fg_draw.text((cx_col - lw // 2, 1592), lbl_str, font=f_stat_lbl, fill=WHITE)

    # Sütun ayırıcı dikey çizgiler
    fg_draw.line([(378, 1512), (378, 1635)], fill=(160, 195, 175, 180), width=3)
    fg_draw.line([(702, 1512), (702, 1635)], fill=(160, 195, 175, 180), width=3)

    # Alt İtalik Golcüler & Editoryal Slogan
    f_it1 = load_italic_font(29, True)
    f_it2 = load_italic_font(30, True)
    sub1 = "40' Lukaku  •  71' Kerem Aktürkoğlu  •  87' Vedat Muriqi"
    sub2 = "Perdeyi açan gol, Kadıköy'de unutulmaz resital."

    sb1 = fg_draw.textbbox((0, 0), sub1, font=f_it1)
    fg_draw.text(((WIDTH - (sb1[2] - sb1[0])) // 2, 1665), sub1, font=f_it1, fill=WHITE)

    sb2 = fg_draw.textbbox((0, 0), sub2, font=f_it2)
    sw2 = sb2[2] - sb2[0]
    sx2 = (WIDTH - sw2) // 2
    fg_draw.text((sx2, 1708), sub2, font=f_it2, fill=(230, 242, 232))
    # Alt sarı vurgu çizgisi
    fg_draw.line([(sx2 + 10, 1752), (sx2 + sw2 - 10, 1750)], fill=(*NEON_YELLOW, 255), width=6)

    # En Alt Siyah Yırtık Kağıt & +18 / @iddaaliyiz.tv İmza Şeridi
    draw_torn_paper_divider(fg, y_pos=1818, fill_below=(8, 12, 10, 255), seed=999, thickness=12)
    f_foot = load_font(21, True)
    foot_txt = "+18 • Sadece bilgilendirme amaçlıdır.   |   @iddaaliyiz.tv   |   İstatistik: Mackolik"
    fb_box = fg_draw.textbbox((0, 0), foot_txt, font=f_foot)
    fg_draw.text(((WIDTH - (fb_box[2] - fb_box[0])) // 2, 1858), foot_txt, font=f_foot, fill=(210, 220, 215))

    return bg, hero_cutout, fg


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    main_mp3 = OUTPUT_DIR / "vo_lukaku_poster_main.mp3"
    outro1_mp3 = OUTPUT_DIR / "vo_lukaku_poster_o1.mp3"
    outro2_mp3 = OUTPUT_DIR / "vo_lukaku_poster_o2.mp3"
    tts_mp3 = OUTPUT_DIR / "vo_lukaku_poster_full.mp3"

    print("[1/3] Erkek spiker Lukaku Manşet Poster seslendirmesi üretiliyor...")
    asyncio.run(generate_tts(LUKAKU_POSTER_VOICEOVER, main_mp3))

    if STATIC_OUTRO1_MP3.exists() and STATIC_OUTRO1_MP3.stat().st_size > 1000:
        shutil.copyfile(STATIC_OUTRO1_MP3, outro1_mp3)
    else:
        asyncio.run(generate_tts(OUTRO_VOICEOVER_STEP1, outro1_mp3))

    if STATIC_OUTRO2_MP3.exists() and STATIC_OUTRO2_MP3.stat().st_size > 1000:
        shutil.copyfile(STATIC_OUTRO2_MP3, outro2_mp3)
    else:
        asyncio.run(generate_tts(OUTRO_VOICEOVER_STEP2, outro2_mp3))

    d_main = get_audio_duration(main_mp3)
    d_s1 = get_audio_duration(outro1_mp3)
    d_s2 = get_audio_duration(outro2_mp3)

    main_dur = max(8.5, d_main + 0.45)
    step1_dur = max(3.6, d_s1 + 0.25)
    step2_dur = max(3.4, d_s2 + 1.85)
    total_dur = main_dur + step1_dur + step2_dur
    total_frames = int(total_dur * FPS)

    delay_s1_ms = int(main_dur * 1000)
    delay_s2_ms = int((main_dur + step1_dur) * 1000)

    subprocess.run(
        [
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
        ],
        check=True,
    )

    mixed_audio = OUTPUT_DIR / "mixed_lukaku_poster.m4a"
    bg_music = GLOBAL_MUSIC_PATH if GLOBAL_MUSIC_PATH.exists() else (ASSETS_DIR / "bg_music.mp3")
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(tts_mp3),
            "-stream_loop", "-1", "-i", str(bg_music),
            "-filter_complex",
            f"[0:a]volume=1.55,apad[vo];[1:a]volume=0.14,afade=t=in:st=0:d=0.6,afade=t=out:st={total_dur-1.2}:d=1.2[bg];[vo][bg]amix=inputs=2:duration=shortest:normalize=0[a]",
            "-map", "[a]", "-t", f"{total_dur:.2f}", "-c:a", "aac", "-b:a", "192k",
            str(mixed_audio),
        ],
        check=True,
    )

    print("[2/3] Dergi kalitesinde Romelu Lukaku poster katmanları oluşturuluyor...")
    master_poster_file = ASSETS_DIR / "lukaku_editorial_poster_final.jpg"
    if master_poster_file.exists():
        master_poster = ImageOps.fit(
            Image.open(master_poster_file).convert("RGBA"),
            (WIDTH, HEIGHT),
            method=Image.Resampling.LANCZOS,
        )
        # Skor satırındaki Fenerbahçe ve Alanyaspor armalarını %100 vektör netliğinde resmi PNG ile keskinleştir
        fb_logo_path = ASSETS_DIR / "logo_fenerbahce.png"
        al_logo_path = ASSETS_DIR / "logo_alanyaspor.png"
        if fb_logo_path.exists():
            fb_crisp = Image.open(fb_logo_path).convert("RGBA").resize((96, 96), Image.Resampling.LANCZOS)
            master_poster.alpha_composite(fb_crisp, (127, 1465))
        if al_logo_path.exists():
            al_crisp = Image.open(al_logo_path).convert("RGBA").resize((96, 96), Image.Resampling.LANCZOS)
            master_poster.alpha_composite(al_crisp, (860, 1465))
        bg_collage, hero_cutout, fg_overlay = master_poster, None, None
    else:
        bg_collage, hero_cutout, fg_overlay = build_lukaku_master_poster()

    outro_base_bg = build_base_gradient()
    logo_img = Image.open(LOGO_PATH).convert("RGB").resize((305, 80)) if LOGO_PATH.exists() else None
    scale = 1.38
    target_size = (int(503 * scale), int(1024 * scale))
    step1_img: Optional[Image.Image] = (
        Image.open(OUTRO_STEP1_PATH).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
        if OUTRO_STEP1_PATH.exists()
        else None
    )
    step2_img: Optional[Image.Image] = (
        Image.open(OUTRO_STEP2_PATH).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
        if OUTRO_STEP2_PATH.exists()
        else None
    )
    payload_header = {
        "title": "MAÇIN ADAMI: LUKAKU",
        "coupon_title": "MAÇIN ADAMI: LUKAKU",
        "results_title": "MAÇIN ADAMI: LUKAKU",
        "disclaimer": "+18 | Sadece bilgilendirme amaçlıdır.",
    }
    cta_text = "Hemen oynamak için iddaa.com'a gir bayi kodunu 304168 yap"

    video_path = OUTPUT_DIR / "reels_lukaku_manset_poster.mp4"
    poster_path = OUTPUT_DIR / "reels_lukaku_manset_poster.png"

    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        "-i", str(mixed_audio),
        "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest",
        str(video_path),
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    rng_sp = random.Random(90)
    particles = [
        (rng_sp.randint(40, WIDTH - 40), rng_sp.randint(180, 1300), rng_sp.uniform(35, 85), rng_sp.randint(2, 4))
        for _ in range(24)
    ]

    for f_idx in range(total_frames):
        t = f_idx / FPS

        # Kayıtlı Bayim (304168) Kapanış Sahnesi
        if t >= main_dur and step1_img is not None and step2_img is not None:
            frame_rgb = outro_base_bg.copy()
            draw_rgb = ImageDraw.Draw(frame_rgb)
            render_outro_scene(
                frame=frame_rgb,
                draw=draw_rgb,
                step1_img=step1_img,
                step2_img=step2_img,
                outro_elapsed=t - main_dur,
                step1_dur=step1_dur,
                step2_dur=step2_dur,
            )
            draw_header_and_footer(frame_rgb, draw_rgb, logo_img, payload_header, "coupon", cta_text, t, total_dur)
            proc.stdin.write(frame_rgb.tobytes())
            continue

        # Ana Sahne: Kayıtlı Bayim gelene kadar sinematik Lukaku Posteri
        if hero_cutout is None and fg_overlay is None:
            # Master editöryal poster üzerinde çok hafif sinematik nefes alma (push-in) ve projektör ışıltısı
            zoom = 1.0 + 0.018 * math.sin(t * 0.42)
            zw, zh = int(WIDTH * zoom), int(HEIGHT * zoom)
            scaled = bg_collage.resize((zw, zh), Image.Resampling.BILINEAR)
            ox = (zw - WIDTH) // 2
            oy = (zh - HEIGHT) // 2
            canvas = scaled.crop((ox, oy, ox + WIDTH, oy + HEIGHT))
            p_draw = ImageDraw.Draw(canvas)
            for px0, py0, spd, pr in particles:
                py = int((py0 - t * spd) % 1120) + 180
                px = px0 + int(math.sin(t * 2.2 + py0) * 12)
                p_draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(*NEON_YELLOW, 125))
        else:
            canvas = bg_collage.copy()
            p_draw = ImageDraw.Draw(canvas)
            for px0, py0, spd, pr in particles:
                py = int((py0 - t * spd) % 1120) + 180
                px = px0 + int(math.sin(t * 2.5 + py0) * 14)
                p_draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(*NEON_YELLOW, 165))
            if hero_cutout is not None:
                enter_p = ease_out_cubic(min(1.0, t / 0.45))
                zoom = 1.0 + 0.035 * math.sin(t * 0.45)
                hw = int(hero_cutout.width * zoom)
                hh = int(hero_cutout.height * zoom)
                h_scaled = hero_cutout.resize((hw, hh), Image.Resampling.BILINEAR)
                hx = (WIDTH - hw) // 2 - 15
                hy = 185 + int((1.0 - enter_p) * 120) - int((hh - hero_cutout.height) * 0.4)
                canvas.alpha_composite(h_scaled, (hx, hy))
            if fg_overlay is not None:
                canvas.alpha_composite(fg_overlay)

        frame_rgb = canvas.convert("RGB")
        if f_idx == 0:
            bg_collage.convert("RGB").save(poster_path)

        proc.stdin.write(frame_rgb.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {proc.returncode}")

    print(f"[3/3] Lukaku Manşet Poster Reels hazır: {video_path}")


if __name__ == "__main__":
    main()
