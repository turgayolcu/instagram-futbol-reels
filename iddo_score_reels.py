"""
İDDAALIYIZ TV — "İddo'nun Skor Tahmini" Özel Seri Reels Üreticisi (1080x1920 @ 30fps)
Trabzonspor - Beşiktaş derbisi için 8 farklı skor tahmini:
1-0, 0-1, 1-1, 2-1, 1-2, 3-1, 1-3, 2-2

Özellikler:
- Sabit 3D Baş Analist Karakterimiz: İDDO (kemik gözlüklü, takım elbiseli, 40 yaşlarında karizmatik 3D karakter)
- Üstte yeşil iddaa şeridi + stadyum projektörleri + dev grunge 'İDDAALIYIZ TV'
- Köşede sabit '+18 | SORUMLU OYUN' rozeti (bundan sonra tüm Reels videolarında standart)
- Dev 'İDDO'NUN SKOR TAHMİNİ' başlığı
- Trabzonspor ve Beşiktaş resmi armaları + Dev Skor (örn. 1 - 0) + DEV ORAN kutusu
- Görsel üzerinde yasal sorumluluk reddi uyarısı ('Bu içerik tamamen istatistiksel bir tahmindir, kesinlik içermez. Olası kayıplardan sorumluluk kabul edilmez.')
- %100 erkek spiker seslendirmesi (tr-TR-AhmetNeural) + 2 adımlı Kayıtlı Bayim (304168) kapanışı.
"""

import argparse
import asyncio
import math
import os
import random
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
GOLD_ACCENT = (255, 205, 45)
DARK_EMERALD = (4, 34, 18)

# Trabzonspor - Beşiktaş Maç Skoru Tahminleri ve iddaa Kral Oranları
SCORE_PREDICTIONS: List[Dict[str, str]] = [
    {"score": "1-0", "home": "1", "away": "0", "odds": "7.80", "spoken_score": "bir sıfır", "spoken_odds": "yedi seksen", "note": "Trabzonspor tek golle kilidi açar"},
    {"score": "0-1", "home": "0", "away": "1", "odds": "8.40", "spoken_score": "sıfır bir", "spoken_odds": "sekiz kırk", "note": "Beşiktaş deplasmanda tek golle kazanır"},
    {"score": "1-1", "home": "1", "away": "1", "odds": "6.20", "spoken_score": "bir bir", "spoken_odds": "altı yirmi", "note": "Karşılıklı gollerle dengeli derbi"},
    {"score": "2-1", "home": "2", "away": "1", "odds": "8.90", "spoken_score": "iki bir", "spoken_odds": "sekiz doksan", "note": "Trabzonspor evinde gol düellosunu kazanır"},
    {"score": "1-2", "home": "1", "away": "2", "odds": "9.40", "spoken_score": "bir iki", "spoken_odds": "dokuz kırk", "note": "Beşiktaş deplasmanda geri dönüşe imza atar"},
    {"score": "3-1", "home": "3", "away": "1", "odds": "18.50", "spoken_score": "üç bir", "spoken_odds": "on sekiz elli", "note": "Trabzonspor hücum hattı derbide şov yapar"},
    {"score": "1-3", "home": "1", "away": "3", "odds": "21.00", "spoken_score": "bir üç", "spoken_odds": "yirmi bir sıfır sıfır", "note": "Beşiktaş deplasmanda farklı galibiyete uzanır"},
    {"score": "2-2", "home": "2", "away": "2", "odds": "12.50", "spoken_score": "iki iki", "spoken_odds": "on iki elli", "note": "Dört gollü nefes kesen derbi beraberliği"},
]


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
        x += rng.randint(12, 26)
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
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    top_pts = make_torn_edge_points(y_pos, 0, WIDTH, amp=13, seed=seed)
    bot_pts = [(x, y + thickness) for (x, y) in reversed(top_pts)]

    shadow_pts = [(x, y - 6) for (x, y) in top_pts] + [(x, y + thickness + 8) for (x, y) in reversed(top_pts)]
    d.polygon(shadow_pts, fill=(0, 0, 0, 165))

    if fill_below is not None:
        below_poly = top_pts + [(WIDTH, HEIGHT), (0, HEIGHT)]
        d.polygon(below_poly, fill=fill_below)

    d.polygon(top_pts + bot_pts, fill=(238, 242, 239, 248))
    inner_pts = [(x, y + 5) for (x, y) in top_pts] + [(x, y + thickness - 3) for (x, y) in reversed(top_pts)]
    d.polygon(inner_pts, fill=(198, 206, 200, 215))

    img.alpha_composite(overlay)


def draw_grunge_text_layer(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    shadow_offset: int = 10,
    angle: float = 0.0,
    seed: int = 101,
) -> Image.Image:
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0] + 80
    th = bbox[3] - bbox[1] + 80

    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = 40 - bbox[0], 40 - bbox[1]

    for dx in range(-6, 7, 3):
        for dy in range(-6, 7, 3):
            d.text((ox + dx, oy + dy), text, font=font, fill=(0, 0, 0, 255))
    for s in range(1, shadow_offset + 1):
        d.text((ox + s, oy + s + 2), text, font=font, fill=(0, 0, 0, 255))

    d.text((ox, oy), text, font=font, fill=(*fill, 255))

    rng = random.Random(seed)
    for _ in range(120):
        gx = rng.randint(20, tw - 20)
        gy = rng.randint(20, th - 20)
        gr = rng.randint(1, 3)
        d.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=(8, 28, 16, 145))

    if abs(angle) > 0.05:
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    return layer


def build_iddo_stamp() -> Image.Image:
    """Sağ üstteki eğimli 'BAŞ ANALİST: İDDO (Yapay Zeka & İstatistik)' mühür rozeti."""
    size = 310
    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(badge)
    cx = size // 2

    d.ellipse([12, 12, size - 12, size - 12], fill=(4, 34, 18, 245), outline=(*NEON_YELLOW, 255), width=8)
    d.ellipse([24, 24, size - 24, size - 24], outline=(*NEON_YELLOW, 200), width=3)

    crown_pts = [
        (cx - 24, 54),
        (cx - 28, 34),
        (cx - 12, 44),
        (cx, 30),
        (cx + 12, 44),
        (cx + 28, 34),
        (cx + 24, 54),
    ]
    d.polygon(crown_pts, outline=(*NEON_YELLOW, 255), fill=(4, 34, 18, 255), width=3)

    f_top = load_impact_font(34)
    f_mid = load_impact_font(56)
    f_name = load_impact_font(34)
    f_sub = load_font(18, True)

    for txt, font, y_pos, col in [
        ("BAŞ ANALİST", f_top, 64, WHITE),
        ("İDDO", f_mid, 104, NEON_YELLOW),
        ("ÖZEL SKOR ANALİZİ", f_name, 168, WHITE),
        ("Kral Oran Tahmini", f_sub, 224, (215, 235, 220)),
    ]:
        bb = d.textbbox((0, 0), txt, font=font)
        tw = bb[2] - bb[0]
        d.text(((size - tw) // 2, y_pos), txt, font=font, fill=(*col, 255))

    d.line([(52, 212), (size - 52, 208)], fill=(*NEON_YELLOW, 255), width=5)
    return badge.rotate(6.0, resample=Image.Resampling.BICUBIC, expand=True)


def draw_sorumlu_oyun_badge(canvas: Image.Image, x: int = 28, y: int = 18) -> None:
    """Her Reels'in sol üst köşesinde standart '+18 | SORUMLU OYUN' rozeti."""
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    w, h = 265, 52
    d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=(10, 24, 16, 235), outline=(*NEON_YELLOW, 240), width=3)
    d.rounded_rectangle([x + 6, y + 6, x + 64, y + h - 6], radius=8, fill=(215, 38, 45, 255))
    f_18 = load_impact_font(28)
    f_so = load_impact_font(25)
    d.text((x + 14, y + 9), "+18", font=f_18, fill=(255, 255, 255, 255))
    d.text((x + 74, y + 11), "SORUMLU OYUN", font=f_so, fill=(*NEON_YELLOW, 255))
    canvas.alpha_composite(overlay)


def prepare_iddo_cutout(target_size: Tuple[int, int] = (760, 880)) -> Optional[Image.Image]:
    cutout_path = ASSETS_DIR / "cutout_iddo_3d.png"
    if not cutout_path.exists():
        return None
    img = Image.open(cutout_path).convert("RGBA")
    img = ImageOps.contain(img, target_size, method=Image.Resampling.LANCZOS)
    w, h = img.size

    # Alt kenarı yumuşakça erit
    r, g, b, a = img.split()
    fade_mask = Image.new("L", (w, h), 255)
    fm_pix = fade_mask.load()
    for y in range(h):
        bot_fade = 1.0 if y < h * 0.80 else max(0.0, (h - y) / (h * 0.20))
        for x in range(w):
            fm_pix[x, y] = int(255 * bot_fade)
    a = ImageChops.multiply(a, fade_mask)

    canvas = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 220))
    shadow.putalpha(a.point(lambda p: int(p * 0.8)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(shadow, (28, 28))

    hero_rgba = Image.merge("RGBA", (r, g, b, a))
    canvas.alpha_composite(hero_rgba, (20, 20))
    return canvas


def build_iddo_score_poster(item: Dict[str, str]) -> Tuple[Image.Image, Optional[Image.Image], Image.Image]:
    """
    Sanatsal 3D yırtık kağıt dokulu 'iddo_score_master_template.jpg' üzerine:
    - Trabzonspor ve Beşiktaş resmi armaları
    - Dev Skor Tahmini (örn. 1 - 0)
    - DEV MAÇ SKORU ORANI (örn. ORAN: 7.80)
    - Beyaz yırtık kağıt şeridi üzerine net Yasal Sorumluluk Reddi uyarısı işler.
    """
    template_path = ASSETS_DIR / "iddo_score_master_template.jpg"
    if template_path.exists():
        bg = ImageOps.fit(
            Image.open(template_path).convert("RGBA"),
            (WIDTH, HEIGHT),
            method=Image.Resampling.LANCZOS,
        )
    else:
        bg = Image.new("RGBA", (WIDTH, HEIGHT), (*DARK_EMERALD, 255))

    fg = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    fg_draw = ImageDraw.Draw(fg)

    ts_logo_path = ASSETS_DIR / "logo_trabzonspor.png"
    bjk_logo_path = ASSETS_DIR / "logo_besiktas.png"

    # 1) SOL VE SAĞ TAKIM ARMALARI + İSİMLERİ (y = 1255 .. 1435)
    if ts_logo_path.exists():
        ts_card = Image.open(ts_logo_path).convert("RGBA").resize((142, 142), Image.Resampling.LANCZOS)
        fg.alpha_composite(ts_card, (96, 1248))
    if bjk_logo_path.exists():
        bjk_card = Image.open(bjk_logo_path).convert("RGBA").resize((142, 142), Image.Resampling.LANCZOS)
        fg.alpha_composite(bjk_card, (WIDTH - 238, 1248))

    f_team = load_impact_font(34)
    t1_txt = "TRABZONSPOR"
    t2_txt = "BEŞİKTAŞ"
    t1_b = fg_draw.textbbox((0, 0), t1_txt, font=f_team)
    t2_b = fg_draw.textbbox((0, 0), t2_txt, font=f_team)
    fg_draw.text((167 - (t1_b[2] - t1_b[0]) // 2, 1396), t1_txt, font=f_team, fill=WHITE)
    fg_draw.text((WIDTH - 167 - (t2_b[2] - t2_b[0]) // 2, 1396), t2_txt, font=f_team, fill=WHITE)

    # 2) MERKEZDE DEV SKOR KUTUSU (örn. 1 - 0)
    fg_draw.rounded_rectangle([282, 1248, 798, 1430], radius=24, fill=(4, 28, 14, 235), outline=(*NEON_YELLOW, 255), width=6)
    f_big_score = load_impact_font(156)
    score_str = f"{item['home']} - {item['away']}"
    sb = fg_draw.textbbox((0, 0), score_str, font=f_big_score)
    sw = sb[2] - sb[0]
    sx = (WIDTH - sw) // 2
    fg_draw.text((sx + 7, 1246 + 7), score_str, font=f_big_score, fill=(0, 0, 0, 245))
    fg_draw.text((sx, 1246), score_str, font=f_big_score, fill=(*NEON_YELLOW, 255))

    # 3) DEV ORAN BAR (y = 1445 .. 1572)
    fg_draw.rounded_rectangle([92, 1446, WIDTH - 92, 1572], radius=22, fill=(8, 48, 24, 250), outline=(*NEON_YELLOW, 255), width=6)
    # Sol sarı etiket: MAÇ SKORU DEV ORANI
    fg_draw.rounded_rectangle([104, 1458, 525, 1560], radius=16, fill=(*NEON_YELLOW, 255))
    f_odds_lbl1 = load_impact_font(40)
    f_odds_lbl2 = load_impact_font(44)
    fg_draw.text((158, 1463), "MAÇ SKORU", font=f_odds_lbl1, fill=(4, 26, 12, 255))
    fg_draw.text((146, 1506), "DEV ORANI:", font=f_odds_lbl2, fill=(185, 22, 28, 255))

    # Sağda DEV ORAN DEĞERİ (örn. 7.80)
    f_huge_odds = load_impact_font(118)
    odds_val = item["odds"]
    ob = fg_draw.textbbox((0, 0), odds_val, font=f_huge_odds)
    ow = ob[2] - ob[0]
    ox_odds = 535 + (445 - ow) // 2
    fg_draw.text((ox_odds + 6, 1438 + 6), odds_val, font=f_huge_odds, fill=(0, 0, 0, 245))
    fg_draw.text((ox_odds, 1438), odds_val, font=f_huge_odds, fill=(255, 255, 255, 255))

    # 4) BEYAZ YIRTIK KAĞIT ŞERİDİ ÜZERİNDE YASAL SORUMLULUK REDDİ UYARISI (y = 1585 .. 1682)
    f_disc_title = load_impact_font(27)
    f_disc_body = load_font(20, True)
    d1 = "YASAL UYARI: BU İÇERİK TAMAMEN İSTATİSTİKSEL BİR SKOR TAHMİNİDİR"
    d2 = "Kesinlik içermez. Olası kayıplardan İddaalıyız TV hiçbir şekilde sorumlu tutulamaz."
    d3 = f"SORUMLU OYUN (+18)   •   Kayıtlı Bayim Kodu: 304168   •   {item['note']}"

    b1 = fg_draw.textbbox((0, 0), d1, font=f_disc_title)
    b2 = fg_draw.textbbox((0, 0), d2, font=f_disc_body)
    b3 = fg_draw.textbbox((0, 0), d3, font=f_disc_body)

    fg_draw.text(((WIDTH - (b1[2] - b1[0])) // 2, 1590), d1, font=f_disc_title, fill=(185, 20, 26, 255))
    fg_draw.text(((WIDTH - (b2[2] - b2[0])) // 2, 1624), d2, font=f_disc_body, fill=(15, 28, 20, 255))
    fg_draw.text(((WIDTH - (b3[2] - b3[0])) // 2, 1650), d3, font=f_disc_body, fill=(8, 68, 34, 255))

    return bg, None, fg


def render_single_score_reels(item: Dict[str, str]) -> Tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    slug = f"{item['home']}_{item['away']}"
    main_mp3 = OUTPUT_DIR / f"vo_iddo_{slug}_main.mp3"
    outro1_mp3 = OUTPUT_DIR / f"vo_iddo_{slug}_o1.mp3"
    outro2_mp3 = OUTPUT_DIR / f"vo_iddo_{slug}_o2.mp3"
    tts_mp3 = OUTPUT_DIR / f"vo_iddo_{slug}_full.mp3"

    vo_text = (
        f"İddo'nun skor tahmini! "
        f"Süper Lig'de nefeslerin tutulduğu Trabzonspor Beşiktaş derbisi için "
        f"baş analistimiz İddo'nun özel maç skoru tahmini: {item['spoken_score']}! "
        f"Tam {item['spoken_odds']} dev oranıyla {item['spoken_score']} skoru İddo'nun radarında! "
        f"Unutmayın, bu içerik bir tahmindir, sorumlu oyun kurallarıyla oynayın!"
    )

    print(f"[1/3] ({item['score']}) İddo erkek spiker seslendirmesi üretiliyor...")
    asyncio.run(generate_tts(vo_text, main_mp3))

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

    main_dur = max(8.0, d_main + 0.45)
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

    mixed_audio = OUTPUT_DIR / f"mixed_iddo_{slug}.m4a"
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

    print(f"[2/3] ({item['score']}) İddo'nun Skor Tahmini posteri oluşturuluyor...")
    bg_layer, iddo_hero, fg_overlay = build_iddo_score_poster(item)
    master_poster = bg_layer.copy()
    master_poster.alpha_composite(fg_overlay)

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
        "title": "İDDO'NUN SKOR TAHMİNİ",
        "coupon_title": "İDDO'NUN SKOR TAHMİNİ",
        "results_title": "İDDO'NUN SKOR TAHMİNİ",
        "disclaimer": "+18 | SORUMLU OYUN | Sadece bilgilendirme amaçlıdır.",
    }
    cta_text = "Hemen oynamak için iddaa.com'a gir bayi kodunu 304168 yap"

    video_path = OUTPUT_DIR / f"reels_iddo_skor_{slug}.mp4"
    poster_path = OUTPUT_DIR / f"reels_iddo_skor_{slug}.png"
    master_poster.convert("RGB").save(poster_path)

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
        (rng_sp.randint(40, WIDTH - 40), rng_sp.randint(180, 1220), rng_sp.uniform(35, 80), rng_sp.randint(2, 4))
        for _ in range(24)
    ]

    for f_idx in range(total_frames):
        t = f_idx / FPS

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
            frame_rgba = frame_rgb.convert("RGBA")
            draw_sorumlu_oyun_badge(frame_rgba, x=24, y=14)
            proc.stdin.write(frame_rgba.convert("RGB").tobytes())
            continue

        # Sinematik hafif nefes alma (push-in) + stadyum projektör ışıltısı
        zoom = 1.0 + 0.016 * math.sin(t * 0.44)
        zw, zh = int(WIDTH * zoom), int(HEIGHT * zoom)
        scaled = master_poster.resize((zw, zh), Image.Resampling.BILINEAR)
        ox = (zw - WIDTH) // 2
        oy = (zh - HEIGHT) // 2
        canvas = scaled.crop((ox, oy, ox + WIDTH, oy + HEIGHT))

        p_draw = ImageDraw.Draw(canvas)
        for px0, py0, spd, pr in particles:
            py = int((py0 - t * spd) % 1040) + 180
            px = px0 + int(math.sin(t * 2.2 + py0) * 12)
            p_draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(*NEON_YELLOW, 125))

        proc.stdin.write(canvas.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {proc.returncode}")

    print(f"[3/3] ({item['score']}) İddo Skor Tahmini Reels hazır: {video_path}")
    return video_path, poster_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", type=str, default="1-0", help="Üretilecek skor (örn. 1-0 veya all)")
    args = parser.parse_args()

    if args.score.lower() == "all":
        for item in SCORE_PREDICTIONS:
            render_single_score_reels(item)
    else:
        matched = [x for x in SCORE_PREDICTIONS if x["score"] == args.score]
        if not matched:
            raise ValueError(f"Geçersiz skor: {args.score}")
        render_single_score_reels(matched[0])


if __name__ == "__main__":
    main()
