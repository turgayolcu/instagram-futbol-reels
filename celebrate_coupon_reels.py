"""
Günün Banko Kuponu Tuttu! (4'te 4 Tam İsabet Kutlama Reels Üreticisi - 1080x1920 @ 30fps)
- %100 Erkek Spiker Seslendirmesi (tr-TR-AhmetNeural) + Hareketli Kutlama Müziği
- Altın konfeti yağmuru, her maça sırayla vurulan yeşil 'KAZANDI' damgası,
  biten maç skorları ve sonunda 2 aşamalı Kayıtlı Bayim (304168) rehberi.
"""

import asyncio
import math
import random
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

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
WIN_GREEN = (16, 215, 90)
WIN_DARK_GREEN = (6, 95, 38)
GOLD = (255, 215, 35)

FONTS = {
    "banner": load_font(32, True),
    "cta": load_font(24, True),
    "hero_big": load_font(42, True),
    "hero_sub": load_font(25, True),
    "league": load_font(20, True),
    "match": load_font(27, True),
    "pick": load_font(23, True),
    "odd": load_font(28, True),
    "stamp": load_font(24, True),
    "tot_lbl": load_font(32, True),
    "tot_val": load_font(44, True),
    "badge18": load_font(26, True),
    "disc": load_font(25, True),
}

WON_COUPON: List[Dict[str, str]] = [
    {
        "league": "Konferans Ligi  •  MS: 2 - 4",
        "home": "Kuopion",
        "away": "Trabzonspor",
        "pick": "MS 2",
        "odd": "1.47",
    },
    {
        "league": "Avrupa Ligi  •  MS: 2 - 3",
        "home": "Hoffenheim",
        "away": "Beşiktaş",
        "pick": "KG VAR",
        "odd": "1.37",
    },
    {
        "league": "Konferans Ligi  •  MS: 1 - 2",
        "home": "CSKA Sofya",
        "away": "Monaco",
        "pick": "MS 2",
        "odd": "1.36",
    },
    {
        "league": "Avrupa Ligi  •  MS: 0 - 4",
        "home": "Lech Poznan",
        "away": "B. Leverkusen",
        "pick": "MS 2",
        "odd": "1.41",
    },
]

CELEBRATION_VOICEOVER = (
    "Tebrikler! Bugün paylaştığımız günün banko kuponu dörtte dört tam isabetle tuttu! "
    "Kuopion Trabzonspor maçı Maç Sonu 2, Hoffenheim Beşiktaş maçı Karşılıklı Gol Var, "
    "CSKA Sofya Monaco maçı Maç Sonu 2 ve Lech Poznan Bayer Leverkusen maçı Maç Sonu 2 "
    "tahminlerimizle toplam 3 nokta 86 oran kazandı! Değerlendiren herkese bol kazançlar!"
)


def draw_checkmark(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: Tuple[int, int, int]) -> None:
    p1 = (cx - int(size * 0.45), cy + int(size * 0.05))
    p2 = (cx - int(size * 0.10), cy + int(size * 0.42))
    p3 = (cx + int(size * 0.50), cy - int(size * 0.38))
    draw.line([p1, p2, p3], fill=color, width=6, joint="curve")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Erkek Spiker Seslendirmesini Hazırla
    main_mp3 = OUTPUT_DIR / "vo_win_main.mp3"
    outro1_mp3 = OUTPUT_DIR / "vo_win_outro1.mp3"
    outro2_mp3 = OUTPUT_DIR / "vo_win_outro2.mp3"
    tts_mp3 = OUTPUT_DIR / "vo_win_full.mp3"

    print("[1/3] Erkek spiker kutlama seslendirmesi üretiliyor...")
    asyncio.run(generate_tts(CELEBRATION_VOICEOVER, main_mp3))

    if STATIC_OUTRO1_MP3.exists() and STATIC_OUTRO1_MP3.stat().st_size > 1000:
        shutil.copyfile(STATIC_OUTRO1_MP3, outro1_mp3)
    else:
        asyncio.run(generate_tts(OUTRO_VOICEOVER_STEP1, outro1_mp3))

    if STATIC_OUTRO2_MP3.exists() and STATIC_OUTRO2_MP3.stat().st_size > 1000:
        shutil.copyfile(STATIC_OUTRO2_MP3, outro2_mp3)
    else:
        asyncio.run(generate_tts(OUTRO_VOICEOVER_STEP2, outro2_mp3))

    d_main = get_audio_duration(main_mp3)
    d_o1 = get_audio_duration(outro1_mp3)
    d_o2 = get_audio_duration(outro2_mp3)

    main_dur = max(6.0, d_main + 0.35)
    step1_dur = max(3.6, d_o1 + 0.25)
    step2_dur = max(3.4, d_o2 + 1.85)
    total_dur = main_dur + step1_dur + step2_dur
    total_frames = int(total_dur * FPS)

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

    # 2) Kutlama Müziği + Erkek Spiker Miksajı
    mixed_audio = OUTPUT_DIR / "mixed_win_coupon.m4a"
    audio_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(tts_mp3),
        "-stream_loop", "-1", "-ss", "18.0", "-i", str(GLOBAL_MUSIC_PATH),
        "-filter_complex",
        f"[0:a]volume=1.45,apad[vo];[1:a]volume=0.22,afade=t=in:st=0:d=0.5,afade=t=out:st={total_dur-1.2}:d=1.2[bg];[vo][bg]amix=inputs=2:duration=shortest:normalize=0[a]",
        "-map", "[a]", "-t", f"{total_dur:.2f}", "-c:a", "aac", "-b:a", "192k",
        str(mixed_audio),
    ]
    subprocess.run(audio_cmd, check=True)

    # 3) Görsel & Konfeti Hazırlığı
    base_bg = build_base_gradient()
    logo_img = Image.open(LOGO_PATH).convert("RGB").resize((305, 80)) if LOGO_PATH.exists() else None
    scale = 1.38
    target_size = (int(503 * scale), int(1024 * scale))
    step1_img = Image.open(OUTRO_STEP1_PATH).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
    step2_img = Image.open(OUTRO_STEP2_PATH).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)

    rng = random.Random(777)
    confetti: List[Tuple[float, float, float, int, Tuple[int, int, int]]] = []
    palette = [IDDAA_YELLOW, WIN_GREEN, GOLD, WHITE, (255, 85, 85)]
    for _ in range(70):
        confetti.append((
            rng.uniform(25, WIDTH - 25),
            rng.uniform(0, HEIGHT),
            rng.uniform(140, 310),
            rng.randint(5, 11),
            rng.choice(palette),
        ))

    payload_header = {
        "title": "BANKO KUPON TUTTU!",
        "coupon_title": "BANKO KUPON TUTTU!",
        "results_title": "BANKO KUPON TUTTU!",
        "disclaimer": "+18 | Sadece bilgilendirme amaçlıdır.",
    }
    cta_text = "Hemen oynamak için iddaa.com'a gir bayi kodunu 304168 yap"

    video_path = OUTPUT_DIR / "reels_banko_kupon_tuttu.mp4"
    poster_path = OUTPUT_DIR / "reels_banko_kupon_tuttu.png"

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

    print(f"[2/3] Banko Kupon Tuttu Kutlama Reels işleniyor ({total_frames} kare, {total_dur:.1f} sn)...")
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    for f_idx in range(total_frames):
        t = f_idx / FPS
        frame = base_bg.copy()
        draw = ImageDraw.Draw(frame)

        # Arka plan parlama
        sweep_x = int(WIDTH * 0.5 + math.sin(t * 2.0) * 240)
        sweep_y = int(580 + math.cos(t * 1.5) * 160)
        draw.ellipse([sweep_x - 380, sweep_y - 280, sweep_x + 380, sweep_y + 280], fill=(12, 95, 48))

        if t >= main_dur:
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

        # Konfeti Yağmuru
        for cx, cy, cspeed, cr, ccol in confetti:
            yy = 200 + ((cy + t * cspeed) % 1580)
            xx = cx + math.sin(t * 3.5 + cy) * 22
            draw.rounded_rectangle([xx - cr, yy - cr // 2, xx + cr, yy + cr // 2], radius=2, fill=ccol)

        # Üst Kutlama Rozeti
        hero_prog = ease_out_back(t / 0.45)
        if hero_prog > 0.05:
            draw.rounded_rectangle(
                [55, 218, WIDTH - 55, 355],
                radius=20,
                fill=WIN_DARK_GREEN,
                outline=GOLD if int(t * 5) % 2 == 0 else WIN_GREEN,
                width=4,
            )
            h1 = "TEBRİKLER! 4'TE 4 TAM İSABET!"
            b1 = draw.textbbox((0, 0), h1, font=FONTS["hero_big"])
            draw.text(((WIDTH - (b1[2] - b1[0])) // 2, 232), h1, font=FONTS["hero_big"], fill=IDDAA_YELLOW)

            h2 = "GÜNÜN BANKO KUPONU KAYIPSIZ KAZANDI!"
            b2 = draw.textbbox((0, 0), h2, font=FONTS["hero_sub"])
            draw.text(((WIDTH - (b2[2] - b2[0])) // 2, 296), h2, font=FONTS["hero_sub"], fill=WHITE)

        # 4 Kazanan Maç Kartı
        start_y = 385
        row_h = 265
        for i, item in enumerate(WON_COUPON):
            row_start = 0.35 + i * 0.28
            prog = ease_out_cubic((t - row_start) / 0.45)
            if prog <= 0.02:
                continue

            slide_x = int((1.0 - prog) * -680)
            x1 = 55 + slide_x
            x2 = WIDTH - 55 + slide_x
            y1 = start_y + i * row_h
            y2 = y1 + row_h - 24

            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=20,
                fill=IDDAA_CARD_BG,
                outline=WIN_GREEN,
                width=4,
            )

            # Lig ve Biten Maç Skoru
            draw.text((x1 + 30, y1 + 24), item["league"], font=FONTS["league"], fill=IDDAA_YELLOW)

            # Takımlar
            m_str = f"{item['home']}  -  {item['away']}"
            draw.text((x1 + 30, y1 + 68), m_str, font=FONTS["match"], fill=WHITE)

            # Tahmin & Oran Alt Şeridi
            draw.rounded_rectangle(
                [x1 + 30, y1 + 135, x1 + 320, y1 + 208],
                radius=12,
                fill=(4, 48, 22),
                outline=IDDAA_MINT,
                width=2,
            )
            draw.text((x1 + 52, y1 + 156), f"TAHMİN:  {item['pick']}", font=FONTS["pick"], fill=WHITE)

            draw.rounded_rectangle(
                [x1 + 340, y1 + 135, x1 + 520, y1 + 208],
                radius=12,
                fill=IDDAA_YELLOW,
            )
            draw.text((x1 + 382, y1 + 153), item["odd"], font=FONTS["odd"], fill=DARK_GREEN_TEXT)

            # Yeşil 'KAZANDI' Damgası + Tik İkonu (Pop-in)
            stamp_prog = ease_out_back((t - (row_start + 0.35)) / 0.40)
            if stamp_prog > 0.05:
                sx1 = x1 + 620
                sy1 = y1 + 55
                sx2 = x1 + 935
                sy2 = y1 + 185
                draw.rounded_rectangle(
                    [sx1, sy1, sx2, sy2],
                    radius=18,
                    fill=WIN_GREEN,
                    outline=WHITE,
                    width=3,
                )
                draw.ellipse([sx1 + 22, sy1 + 33, sx1 + 86, sy1 + 97], fill=WIN_DARK_GREEN)
                draw_checkmark(draw, sx1 + 54, sy1 + 65, 36, IDDAA_YELLOW)
                draw.text((sx1 + 102, sy1 + 48), "KAZANDI!", font=FONTS["stamp"], fill=DARK_GREEN_TEXT)

        # Alt Toplam Kazanan Oran Kutusu
        tot_start = 1.60
        tot_prog = ease_out_back((t - tot_start) / 0.50)
        if tot_prog > 0.05:
            tot_y = 1465
            pulse = int(math.sin(t * 7.0) * 6)
            draw.rounded_rectangle(
                [55 - pulse, tot_y - pulse, WIDTH - 55 + pulse, tot_y + 130 + pulse],
                radius=22,
                fill=IDDAA_YELLOW,
                outline=WIN_GREEN,
                width=5,
            )
            draw.text((90, tot_y + 42), "TOPLAM KAZANAN ORAN", font=FONTS["tot_lbl"], fill=DARK_GREEN_TEXT)
            draw.rounded_rectangle([685, tot_y + 20, 985, tot_y + 110], radius=16, fill=WIN_DARK_GREEN)
            draw.text((730, tot_y + 36), "3.86", font=FONTS["tot_val"], fill=IDDAA_YELLOW)
            draw_checkmark(draw, 915, tot_y + 65, 22, IDDAA_YELLOW, width=6)

        draw_header_and_footer(frame, draw, logo_img, payload_header, "coupon", cta_text, t, total_dur)

        if f_idx == int(3.2 * FPS):
            frame.save(poster_path)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {proc.returncode}")

    print(f"[3/3] Banko Kupon Tuttu Reels hazır: {video_path}")


if __name__ == "__main__":
    main()
