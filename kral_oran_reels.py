"""
iddaa.com'a Özel "KRAL ORAN & KRAL OYUN" Tanıtım ve Kayıtlı Bayim (304168) Reels Üreticisi (1080x1920 @ 30fps)
- Diğer üçüncü taraf alt bahis firmalarından çok daha yüksek oranlar sunan 'Kral Oran' özelliğini anlatır
- Yan yana Oran Karşılaştırma Tablosu (Diğer Alt Siteler vs iddaa.com Kral Oran)
- Kral Oyun / Kral Oran için Kayıtlı Bayi (304168) zorunluluğunu vurgular
- %100 Erkek Spiker Seslendirmesi (tr-TR-AhmetNeural) + Hareketli Arka Plan Müziği
- Sonunda 2 Aşamalı Animasyonlu 'Kayıtlı Bayim (304168)' Rehberi
"""

import asyncio
import math
import random
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw

from motion_reels import (
    ALERT_RED,
    ASSETS_DIR,
    DARK_GREEN_TEXT,
    FPS,
    HEIGHT,
    IDDAA_CARD_BG,
    IDDAA_MINT,
    IDDAA_PRIMARY_GREEN,
    IDDAA_SUBBAR_GREEN,
    IDDAA_YELLOW,
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
GOLD = (255, 212, 38)
GOLD_LIGHT = (255, 242, 145)
GOLD_DARK = (165, 118, 8)
WIN_GREEN = (18, 215, 92)
WIN_DARK_BG = (6, 88, 38)
LOSS_RED = (232, 48, 48)
LOSS_DARK_BG = (72, 18, 22)

FONTS = {
    "hero_big": load_font(38, True),
    "hero_sub": load_font(22, True),
    "vs_badge": load_font(26, True),
    "box_hdr": load_font(23, True),
    "box_sub": load_font(20, True),
    "odd_old": load_font(44, True),
    "odd_kral": load_font(52, True),
    "diff_badge": load_font(22, True),
    "feat_title": load_font(26, True),
    "feat_desc": load_font(21, False),
    "cta_big": load_font(29, True),
    "cta_sub": load_font(22, True),
}

KRAL_ORAN_VOICEOVER = (
    "Neden diğer alt bahis sitelerinde daha düşük oranlarla oynayasın ki? "
    "Sadece resmi iddaa nokta com'a özel Kral Oran ayrıcalığıyla, "
    "diğer üçüncü taraf bahis firmalarından çok daha yüksek oranlarla kupon yapabilir, "
    "kazancını doğrudan nakit olarak katlayabilirsin! "
    "Üstelik Kral Oyun ve Kral Oran ayrıcalığından faydalanmak için "
    "profilinde bir kayıtlı bayinin olması gerekiyor!"
)


def draw_crown(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0) -> None:
    """Özel vektörel Altın Kral Tacı çizimi"""
    w = int(68 * scale)
    h = int(46 * scale)
    x1, x2 = cx - w, cx + w
    y_bot = cy + h // 2
    y_top = cy - h // 2

    pts = [
        (x1 + int(10 * scale), y_bot),
        (x1, y_top + int(8 * scale)),
        (cx - int(32 * scale), cy + int(4 * scale)),
        (cx, y_top - int(8 * scale)),
        (cx + int(32 * scale), cy + int(4 * scale)),
        (x2, y_top + int(8 * scale)),
        (x2 - int(10 * scale), y_bot),
    ]
    draw.polygon(pts, fill=GOLD, outline=GOLD_LIGHT)
    draw.rounded_rectangle(
        [x1 + int(8 * scale), y_bot - int(10 * scale), x2 - int(8 * scale), y_bot + int(4 * scale)],
        radius=4,
        fill=GOLD_DARK,
        outline=GOLD_LIGHT,
        width=2,
    )
    # Taç mücevherleri
    for jx, jy, col in [
        (x1, y_top + int(8 * scale), GOLD_LIGHT),
        (cx, y_top - int(8 * scale), (255, 60, 60)),
        (x2, y_top + int(8 * scale), GOLD_LIGHT),
    ]:
        r = int(6 * scale)
        draw.ellipse([jx - r, jy - r, jx + r, jy + r], fill=col, outline=WHITE, width=2)


def draw_check(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: Tuple[int, int, int]) -> None:
    p1 = (cx - size, cy)
    p2 = (cx - int(size * 0.25), cy + int(size * 0.75))
    p3 = (cx + size, cy - int(size * 0.75))
    draw.line([p1, p2, p3], fill=color, width=5, joint="curve")


def draw_cross(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: Tuple[int, int, int]) -> None:
    s = int(size * 0.65)
    draw.line([(cx - s, cy - s), (cx + s, cy + s)], fill=color, width=5)
    draw.line([(cx - s, cy + s), (cx + s, cy - s)], fill=color, width=5)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    main_mp3 = OUTPUT_DIR / "vo_kral_main.mp3"
    outro1_mp3 = OUTPUT_DIR / "vo_kral_outro1.mp3"
    outro2_mp3 = OUTPUT_DIR / "vo_kral_outro2.mp3"
    tts_mp3 = OUTPUT_DIR / "vo_kral_full.mp3"

    print(f"[1/3] Erkek spiker Kral Oran seslendirmesi üretiliyor...")
    asyncio.run(generate_tts(KRAL_ORAN_VOICEOVER, main_mp3))

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

    mixed_audio = OUTPUT_DIR / "mixed_kral_oran.m4a"
    bg_music = GLOBAL_MUSIC_PATH if GLOBAL_MUSIC_PATH.exists() else (ASSETS_DIR / "bg_music.mp3")
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(tts_mp3),
            "-stream_loop", "-1", "-i", str(bg_music),
            "-filter_complex",
            f"[0:a]volume=1.50,apad[vo];[1:a]volume=0.14,afade=t=in:st=0:d=0.6,afade=t=out:st={total_dur-1.2}:d=1.2[bg];[vo][bg]amix=inputs=2:duration=shortest:normalize=0[a]",
            "-map", "[a]", "-t", f"{total_dur:.2f}", "-c:a", "aac", "-b:a", "192k",
            str(mixed_audio),
        ],
        check=True,
    )

    base_bg = build_base_gradient()
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
        "title": "İDDAA.COM KRAL ORAN",
        "coupon_title": "İDDAA.COM KRAL ORAN",
        "results_title": "İDDAA.COM KRAL ORAN",
        "disclaimer": "+18 | Sadece bilgilendirme amaçlıdır.",
    }
    cta_text = "Hemen oynamak için iddaa.com'a gir bayi kodunu 304168 yap"

    # Altın ışıltı parçacıkları
    rng = random.Random(304168)
    sparkles = [
        (rng.randint(60, WIDTH - 60), rng.randint(220, 1600), rng.uniform(120, 240), rng.randint(4, 9))
        for _ in range(38)
    ]

    features: List[Tuple[str, str, str]] = [
        (
            "1. EN YÜKSEK ORAN AYRICALIĞI",
            "Diğer üçüncü taraf alt bahis firmalarında olmayan,",
            "sadece resmi iddaa.com'a özel yükseltilmiş Kral Oranlar!",
        ),
        (
            "2. LİMİTSİZ & DOĞRUDAN NAKİT KAZANÇ",
            "Kral Oran farkı hediye puan olarak değil, günlük limit",
            "olmaksızın doğrudan nakit olarak hesabına yatar!",
        ),
        (
            "3. KRAL OYUN İÇİN 'KAYITLI BAYİ' ŞARTI",
            "Kral Oran ayrıcalığını aktif etmek için profilinde",
            "Kayıtlı Bayim (304168) tanımlı olması zorunludur!",
        ),
    ]

    video_path = OUTPUT_DIR / "reels_kral_oran_tanitim.mp4"
    poster_path = OUTPUT_DIR / "reels_kral_oran_tanitim.png"

    print(f"[2/3] 30 FPS Kral Oran Reels işleniyor ({total_frames} kare, {total_dur:.1f} sn)...")
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
        frame = base_bg.copy()
        draw = ImageDraw.Draw(frame)

        # Arka plan altın-yeşil spot ışığı
        sweep_x = int(WIDTH * 0.5 + math.sin(t * 2.2) * 240)
        sweep_y = int(580 + math.cos(t * 1.6) * 160)
        draw.ellipse([sweep_x - 380, sweep_y - 260, sweep_x + 380, sweep_y + 260], fill=(14, 92, 46))

        if t >= main_dur and step1_img is not None and step2_img is not None:
            render_outro_scene(
                frame=frame,
                draw=draw,
                step1_img=step1_img,
                step2_img=step2_img,
                outro_elapsed=t - main_dur,
                step1_dur=step1_dur,
                step2_dur=step2_dur,
            )
            draw_header_and_footer(frame, draw, logo_img, payload_header, "coupon", cta_text, t, total_dur)
            proc.stdin.write(frame.tobytes())
            continue

        # Arka plan yükselen altın ışıltılar
        for sx, sy0, spd, r in sparkles:
            cy = int((sy0 - t * spd) % 1450) + 210
            cx = sx + int(math.sin(t * 3.0 + sy0) * 16)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD_LIGHT if r % 2 == 0 else GOLD)

        # 1) Üst Kral Tacı & Ana Başlık Kutusu
        hero_prog = ease_out_back((t - 0.10) / 0.45)
        if hero_prog > 0.05:
            hy1, hy2 = 220, 382
            pulse = int(math.sin(t * 6.0) * 4)
            draw.rounded_rectangle(
                [55 - pulse, hy1 - pulse, WIDTH - 55 + pulse, hy2 + pulse],
                radius=22,
                fill=(10, 62, 30),
                outline=GOLD,
                width=4,
            )
            draw_crown(draw, 145, 300, scale=0.95)
            draw_crown(draw, WIDTH - 145, 300, scale=0.95)

            t1 = "KRAL ORAN AYRICALIĞI"
            b1 = draw.textbbox((0, 0), t1, font=FONTS["hero_big"])
            draw.text(((WIDTH - (b1[2] - b1[0])) // 2, hy1 + 26), t1, font=FONTS["hero_big"], fill=GOLD)

            t2 = "DİĞER ALT BAHİS FİRMALARINDAN DAHA YÜKSEK ORANLAR!"
            b2 = draw.textbbox((0, 0), t2, font=FONTS["hero_sub"])
            draw.text(((WIDTH - (b2[2] - b2[0])) // 2, hy1 + 98), t2, font=FONTS["hero_sub"], fill=WHITE)

        # 2) Yan Yana Oran Karşılaştırma Kartları (Diğer Alt Siteler vs iddaa.com Kral Oran)
        comp_prog = ease_out_back((t - 0.40) / 0.50)
        if comp_prog > 0.05:
            cy1, cy2 = 408, 760
            # Sol Kart: Diğer Alt Bahis Siteleri (Kırmızı/Gri)
            lx1, lx2 = 55, 505
            draw.rounded_rectangle(
                [lx1, cy1, lx2, cy2],
                radius=22,
                fill=LOSS_DARK_BG,
                outline=LOSS_RED,
                width=3,
            )
            lh1 = "DİĞER ALT SİTELER"
            lb1 = draw.textbbox((0, 0), lh1, font=FONTS["box_hdr"])
            draw.text((lx1 + (450 - (lb1[2] - lb1[0])) // 2, cy1 + 24), lh1, font=FONTS["box_hdr"], fill=(255, 150, 150))

            lh2 = "Standart Bülten Oranı"
            lb2 = draw.textbbox((0, 0), lh2, font=FONTS["box_sub"])
            draw.text((lx1 + (450 - (lb2[2] - lb2[0])) // 2, cy1 + 64), lh2, font=FONTS["box_sub"], fill=(220, 200, 200))

            # Eski Oran Kutusu (Üzeri Çizili)
            draw.rounded_rectangle([lx1 + 45, cy1 + 115, lx2 - 45, cy1 + 235], radius=16, fill=(48, 12, 14), outline=LOSS_RED, width=2)
            old_txt = "3.85"
            ob = draw.textbbox((0, 0), old_txt, font=FONTS["odd_old"])
            ox = lx1 + (450 - (ob[2] - ob[0])) // 2
            oy = cy1 + 142
            draw.text((ox, oy), old_txt, font=FONTS["odd_old"], fill=(195, 165, 165))
            draw.line([(ox - 15, oy + 32), (ox + (ob[2] - ob[0]) + 15, oy + 18)], fill=ALERT_RED, width=7)

            draw_cross(draw, lx1 + 88, cy1 + 292, 13, LOSS_RED)
            draw.text((lx1 + 115, cy1 + 276), "DÜŞÜK KAZANÇ", font=FONTS["diff_badge"], fill=(255, 140, 140))

            # Sağ Kart: iddaa.com KRAL ORAN (Altın & Parlak Yeşil)
            rx1, rx2 = 575, WIDTH - 55
            glow = int(math.sin(t * 7.0) * 5)
            draw.rounded_rectangle(
                [rx1 - glow, cy1 - glow, rx2 + glow, cy2 + glow],
                radius=22,
                fill=WIN_DARK_BG,
                outline=GOLD,
                width=5,
            )
            rh1 = "İDDAA.COM KRAL ORAN"
            rb1 = draw.textbbox((0, 0), rh1, font=FONTS["box_hdr"])
            draw.text((rx1 + (450 - (rb1[2] - rb1[0])) // 2, cy1 + 24), rh1, font=FONTS["box_hdr"], fill=GOLD)

            rh2 = "Aynı 4 Maçlık Kuponda"
            rb2 = draw.textbbox((0, 0), rh2, font=FONTS["box_sub"])
            draw.text((rx1 + (450 - (rb2[2] - rb2[0])) // 2, cy1 + 64), rh2, font=FONTS["box_sub"], fill=IDDAA_MINT)

            # Kral Oran Kutusu
            draw.rounded_rectangle([rx1 + 35, cy1 + 110, rx2 - 35, cy1 + 240], radius=18, fill=GOLD, outline=WHITE, width=3)
            kral_txt = "5.40"
            kb = draw.textbbox((0, 0), kral_txt, font=FONTS["odd_kral"])
            draw.text((rx1 + (450 - (kb[2] - kb[0])) // 2, cy1 + 135), kral_txt, font=FONTS["odd_kral"], fill=DARK_GREEN_TEXT)

            draw_check(draw, rx1 + 65, cy1 + 292, 14, WIN_GREEN)
            draw.text((rx1 + 92, cy1 + 276), "+%40 FAZLA NAKİT!", font=FONTS["diff_badge"], fill=GOLD)

            # Ortadaki VS Dairesi
            draw.ellipse([WIDTH // 2 - 42, (cy1 + cy2) // 2 - 42, WIDTH // 2 + 42, (cy1 + cy2) // 2 + 42], fill=GOLD, outline=WHITE, width=4)
            draw.text((WIDTH // 2 - 22, (cy1 + cy2) // 2 - 18), "VS", font=FONTS["vs_badge"], fill=DARK_GREEN_TEXT)

        # 3) 3 Maddede Kral Oran & Kayıtlı Bayi Avantajları
        start_y = 790
        row_h = 205
        for i, (ftitle, fdesc1, fdesc2) in enumerate(features):
            row_start = 0.75 + i * 0.35
            prog = ease_out_cubic((t - row_start) / 0.48)
            if prog <= 0.02:
                continue

            slide_x = int((1.0 - prog) * -700)
            x1 = 55 + slide_x
            x2 = WIDTH - 55 + slide_x
            y1 = start_y + i * row_h
            y2 = y1 + row_h - 18

            is_last = i == 2
            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=20,
                fill=(12, 74, 38) if is_last else IDDAA_CARD_BG,
                outline=GOLD if is_last else WIN_GREEN,
                width=4 if is_last else 3,
            )

            # Sol İkon Kutusu
            draw.rounded_rectangle([x1 + 24, y1 + 28, x1 + 134, y2 - 28], radius=16, fill=GOLD if is_last else WIN_DARK_BG, outline=GOLD, width=2)
            if is_last:
                draw_crown(draw, x1 + 79, (y1 + y2) // 2, scale=0.62)
            else:
                draw_check(draw, x1 + 79, (y1 + y2) // 2, 22, GOLD)

            # Başlık ve Açıklama
            draw.text((x1 + 160, y1 + 24), ftitle, font=FONTS["feat_title"], fill=GOLD)
            draw.text((x1 + 160, y1 + 76), fdesc1, font=FONTS["feat_desc"], fill=WHITE)
            draw.text((x1 + 160, y1 + 114), fdesc2, font=FONTS["feat_desc"], fill=IDDAA_MINT)

        # 4) Alt Kayıtlı Bayi (304168) Vurgu Kutusu
        bot_start = 1.85
        bot_prog = ease_out_back((t - bot_start) / 0.45)
        if bot_prog > 0.05:
            by1, by2 = 1420, 1575
            pulse = int(math.sin(t * 7.0) * 6)
            draw.rounded_rectangle(
                [55 - pulse, by1 - pulse, WIDTH - 55 + pulse, by2 + pulse],
                radius=22,
                fill=GOLD,
                outline=WHITE,
                width=4,
            )
            c1 = "KRAL ORAN İÇİN KAYITLI BAYİ KODUN: 304168"
            cb1 = draw.textbbox((0, 0), c1, font=FONTS["cta_big"])
            draw.text(((WIDTH - (cb1[2] - cb1[0])) // 2, by1 + 28), c1, font=FONTS["cta_big"], fill=DARK_GREEN_TEXT)

            draw.rounded_rectangle([110, by1 + 88, WIDTH - 110, by2 - 18], radius=12, fill=DARK_GREEN_TEXT)
            c2 = "SEZEK ŞANS OYUNLARI  •  BİRAZDAN ADIM ADIM EKRANDA!"
            cb2 = draw.textbbox((0, 0), c2, font=FONTS["cta_sub"])
            draw.text(((WIDTH - (cb2[2] - cb2[0])) // 2, by1 + 98), c2, font=FONTS["cta_sub"], fill=GOLD)

        draw_header_and_footer(frame, draw, logo_img, payload_header, "coupon", cta_text, t, total_dur)

        if f_idx == int(3.0 * FPS):
            frame.save(poster_path)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {proc.returncode}")

    print(f"[3/3] Kral Oran & Kayıtlı Bayim Reels hazır: {video_path}")


if __name__ == "__main__":
    main()
