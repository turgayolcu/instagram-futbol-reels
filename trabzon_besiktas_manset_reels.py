"""
İDDAALIYIZ TV — Trabzonspor 2-0 Beşiktaş Maç Sonu Sanatsal Manşet Reels Üreticisi (1080x1920 @ 30fps)
Mackolik Teyitli Maç Detayları (19 Ekim 2026, Trendyol Süper Lig):
- Skor: TRABZONSPOR 2 - 0 BEŞİKTAŞ (İlk Yarı: 1-0)
- Goller: 21' Ozan Tufan, 71' Mohamed Salah (Asist: Franculino)
- Yıldızlar: Mohamed Salah (Trabzonspor Bordo-Mavi Çubuklu Forma) & Leandro Trossard (Beşiktaş Siyah-Beyaz Çubuklu Forma)
- Özellikler: Gece stadyum projektör ışıklandırması, 3D yırtık kağıt dergi kolajı,
  +18 SORUMLU OYUN rozeti, erkek spiker seslendirmesi ve 2 adımlı Kayıtlı Bayim (304168) kapanışı.
"""

import asyncio
import math
import random
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageOps

from motion_reels import (
    ASSETS_DIR,
    FPS,
    HEIGHT,
    LOGO_PATH,
    OUTPUT_DIR,
    OUTRO_STEP1_PATH,
    OUTRO_STEP2_PATH,
    OUTRO_VOICEOVER_STEP1,
    OUTRO_VOICEOVER_STEP2,
    STATIC_OUTRO1_MP3,
    STATIC_OUTRO2_MP3,
    WIDTH,
    build_base_gradient,
    draw_header_and_footer,
    generate_tts,
    get_audio_duration,
    render_outro_scene,
)

GLOBAL_MUSIC_PATH = ASSETS_DIR / "global_trend_music.mp3"
NEON_YELLOW = (246, 232, 24)

TRABZON_BJK_VOICEOVER = (
    "Trabzon'da fırtına esti, derbide Salah imzası! "
    "Trendyol Süper Lig'de gecenin dev randevusunda Trabzonspor, sahasında Beşiktaş'ı 2 0 mağlup etti! "
    "Yirmi birinci dakikada Ozan Tufan'ın golüyle perdeyi açan bordo mavililerde, "
    "yetmiş birinci dakikada Franculino'nun asistinde sahneye çıkan Mohamed Salah fişi çekti! "
    "Beşiktaş'ta Leandro Trossard ve arkadaşları skoru değiştiremezken, "
    "dev derbide bizim maçın adamı Mohamed Salah!"
)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    main_mp3 = OUTPUT_DIR / "vo_ts_bjk_manset_main.mp3"
    outro1_mp3 = OUTPUT_DIR / "vo_ts_bjk_manset_o1.mp3"
    outro2_mp3 = OUTPUT_DIR / "vo_ts_bjk_manset_o2.mp3"
    tts_mp3 = OUTPUT_DIR / "vo_ts_bjk_manset_full.mp3"

    print("[1/3] Erkek spiker Trabzonspor - Beşiktaş Manşet seslendirmesi üretiliyor...")
    asyncio.run(generate_tts(TRABZON_BJK_VOICEOVER, main_mp3))

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

    mixed_audio = OUTPUT_DIR / "mixed_ts_bjk_manset.m4a"
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

    print("[2/3] Sanatsal Salah & Trossard derbi manşet posteri yükleniyor...")
    master_poster_file = ASSETS_DIR / "trabzon_besiktas_salah_trossard_poster.jpg"
    if not master_poster_file.exists():
        raise FileNotFoundError(f"Poster bulunamadı: {master_poster_file}")

    master_poster = ImageOps.fit(
        Image.open(master_poster_file).convert("RGBA"),
        (WIDTH, HEIGHT),
        method=Image.Resampling.LANCZOS,
    )

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
        "title": "DERBİDE SALAH İMZASI",
        "coupon_title": "DERBİDE SALAH İMZASI",
        "results_title": "DERBİDE SALAH İMZASI",
        "disclaimer": "+18 | SORUMLU OYUN | Sadece bilgilendirme amaçlıdır.",
    }
    cta_text = "Hemen oynamak için iddaa.com'a gir bayi kodunu 304168 yap"

    video_path = OUTPUT_DIR / "reels_trabzon_besiktas_manset.mp4"
    poster_path = OUTPUT_DIR / "reels_trabzon_besiktas_manset.png"
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
        (rng_sp.randint(40, WIDTH - 40), rng_sp.randint(180, 1280), rng_sp.uniform(35, 85), rng_sp.randint(2, 4))
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
            proc.stdin.write(frame_rgb.tobytes())
            continue

        # Sinematik hafif nefes alma (push-in) ve gece stadyum projektör ışıltısı
        zoom = 1.0 + 0.018 * math.sin(t * 0.42)
        zw, zh = int(WIDTH * zoom), int(HEIGHT * zoom)
        scaled = master_poster.resize((zw, zh), Image.Resampling.BILINEAR)
        ox = (zw - WIDTH) // 2
        oy = (zh - HEIGHT) // 2
        canvas = scaled.crop((ox, oy, ox + WIDTH, oy + HEIGHT))

        p_draw = ImageDraw.Draw(canvas)
        for px0, py0, spd, pr in particles:
            py = int((py0 - t * spd) % 1100) + 180
            px = px0 + int(math.sin(t * 2.2 + py0) * 12)
            p_draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(*NEON_YELLOW, 125))

        proc.stdin.write(canvas.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {proc.returncode}")

    print(f"[3/3] Trabzonspor - Beşiktaş Manşet Reels hazır: {video_path}")


if __name__ == "__main__":
    main()
