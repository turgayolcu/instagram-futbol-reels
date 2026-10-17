"""
Avrupa Kupalarında (Şampiyonlar Ligi, Avrupa Ligi, Konferans Ligi)
Temsilcilerimizin Hafta İçi Maç Sonuçları ve Son Puan Durumu Özeti Reels Üreticisi (1080x1920 @ 30fps)
- %100 Erkek Spiker Seslendirmesi (tr-TR-AhmetNeural) + Arka Plan Müziği
- Resmi Kulüp Logoları (Beşiktaş, Trabzonspor, Fenerbahçe, Galatasaray)
- Hafta içi oynanan maç skoru + Güncel UEFA Lig Aşaması Sıralama / Puan / Averaj tablosu
- Sonunda 2 Aşamalı Kayıtlı Bayim (304168) Rehberi
"""

import asyncio
import math
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

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
WIN_GREEN = (18, 212, 92)
WIN_DARK_BG = (6, 88, 38)
LOSS_RED = (232, 45, 45)
LOSS_DARK_BG = (92, 16, 20)
UEFA_BLUE_BG = (10, 56, 36)

FONTS = {
    "hero_title": load_font(31, True),
    "tournament": load_font(20, True),
    "team_title": load_font(28, True),
    "match_score": load_font(27, True),
    "badge": load_font(21, True),
    "standings_lbl": load_font(21, True),
    "standings_val": load_font(23, True),
    "summary_title": load_font(27, True),
    "summary_val": load_font(30, True),
}

TURKISH_TEAMS_DATA: List[Dict[str, str]] = [
    {
        "team": "BEŞİKTAŞ",
        "logo": "logo_besiktas.png",
        "tournament": "UEFA AVRUPA LİGİ  •  2. HAFTA",
        "match": "Hoffenheim  2 - 3  Beşiktaş",
        "status": "GALİBİYET",
        "is_win": "1",
        "rank": "4. SIRA",
        "points": "6 PUAN",
        "stats": "2 Maç: 2G 0B 0M  •  Averaj: +4",
    },
    {
        "team": "TRABZONSPOR",
        "logo": "logo_trabzonspor.png",
        "tournament": "UEFA KONFERANS LİGİ  •  1. HAFTA",
        "match": "KuPS Kuopio  2 - 4  Trabzonspor",
        "status": "GALİBİYET",
        "is_win": "1",
        "rank": "3. SIRA",
        "points": "3 PUAN",
        "stats": "1 Maç: 1G 0B 0M  •  Averaj: +2",
    },
    {
        "team": "FENERBAHÇE",
        "logo": "logo_fenerbahce.png",
        "tournament": "UEFA ŞAMPİYONLAR LİGİ  •  2. HAFTA",
        "match": "Aston Villa  6 - 0  Fenerbahçe",
        "status": "MAĞLUBİYET",
        "is_win": "0",
        "rank": "28. SIRA",
        "points": "1 PUAN",
        "stats": "2 Maç: 0G 1B 1M  •  Averaj: -6",
    },
    {
        "team": "GALATASARAY",
        "logo": "logo_galatasaray.png",
        "tournament": "UEFA ŞAMPİYONLAR LİGİ  •  2. HAFTA",
        "match": "Galatasaray  1 - 4  Barcelona",
        "status": "MAĞLUBİYET",
        "is_win": "0",
        "rank": "35. SIRA",
        "points": "0 PUAN",
        "stats": "2 Maç: 0G 0B 2M  •  Averaj: -5",
    },
]

EUROPE_VOICEOVER_TEXT = (
    "Avrupa kupalarında temsilcilerimizin hafta içi maç sonuçları ve puan durumundaki son tablosu! "
    "UEFA Avrupa Ligi'nde Beşiktaş, deplasmanda Hoffenheim'ı 3-2 mağlup ederek 6 puanla dördüncü sıraya yükseldi ve ikide iki yaptı! "
    "Konferans Ligi'nde Trabzonspor, Kuopio deplasmanından 4-2 galibiyetle dönerek 3 puanla üçüncü sıraya yerleşti! "
    "Şampiyonlar Ligi'nde ise Fenerbahçe, Aston Villa deplasmanında mağlup olarak 1 puanla yirmi sekizinci sırada, "
    "Galatasaray ise Barcelona karşısında aldığı yenilgiyle sıfır puanla otuz beşinci sırada yer aldı."
)


def load_club_logos() -> Dict[str, Image.Image]:
    logos: Dict[str, Image.Image] = {}
    for item in TURKISH_TEAMS_DATA:
        p = ASSETS_DIR / item["logo"]
        if p.exists():
            img = Image.open(p).convert("RGBA").resize((108, 108), Image.Resampling.LANCZOS)
            logos[item["logo"]] = img
    return logos


def draw_check_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple, width: int = 4) -> None:
    p1 = (cx - size, cy)
    p2 = (cx - int(size * 0.25), cy + int(size * 0.75))
    p3 = (cx + size, cy - int(size * 0.75))
    draw.line([p1, p2, p3], fill=color, width=width, joint="curve")


def draw_cross_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple, width: int = 4) -> None:
    s = int(size * 0.65)
    draw.line([(cx - s, cy - s), (cx + s, cy + s)], fill=color, width=width)
    draw.line([(cx - s, cy + s), (cx + s, cy - s)], fill=color, width=width)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    main_mp3 = OUTPUT_DIR / "vo_main_europe.mp3"
    outro1_mp3 = OUTPUT_DIR / "vo_outro1_europe.mp3"
    outro2_mp3 = OUTPUT_DIR / "vo_outro2_europe.mp3"
    tts_mp3 = OUTPUT_DIR / "vo_europe_full.mp3"

    print(f"[1/3] Erkek spiker seslendirmesi üretiliyor: \"{EUROPE_VOICEOVER_TEXT}\"")
    asyncio.run(generate_tts(EUROPE_VOICEOVER_TEXT, main_mp3))

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

    mixed_audio = OUTPUT_DIR / "mixed_europe.m4a"
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
    club_logos = load_club_logos()

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
        "title": "AVRUPA'DA TEMSİLCİLERİMİZ",
        "coupon_title": "AVRUPA'DA TEMSİLCİLERİMİZ",
        "results_title": "AVRUPA'DA TEMSİLCİLERİMİZ",
        "disclaimer": "+18 | Sadece bilgilendirme amaçlıdır.",
    }
    cta_text = "Hemen oynamak için iddaa.com'a gir bayi kodunu 304168 yap"

    video_path = OUTPUT_DIR / "reels_avrupa_temsilcilerimiz.mp4"
    poster_path = OUTPUT_DIR / "reels_avrupa_temsilcilerimiz.png"

    print(f"[2/3] 30 FPS Avrupa Temsilcilerimiz Reels işleniyor ({total_frames} kare, {total_dur:.1f} sn)...")
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

        # Arka plan ışık efekti
        sweep_x = int(WIDTH * 0.5 + math.sin(t * 2.0) * 240)
        sweep_y = int(600 + math.cos(t * 1.5) * 160)
        draw.ellipse([sweep_x - 380, sweep_y - 260, sweep_x + 380, sweep_y + 260], fill=(10, 88, 45))

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

        # Üst Alt-Başlık Şeridi
        hero_prog = ease_out_back((t - 0.15) / 0.45)
        if hero_prog > 0.05:
            draw.rounded_rectangle(
                [55, 216, WIDTH - 55, 294],
                radius=16,
                fill=IDDAA_SUBBAR_GREEN,
                outline=IDDAA_YELLOW,
                width=3,
            )
            h_txt = "HAFTA İÇİ MAÇ SONUÇLARI & PUAN DURUMU"
            hb = draw.textbbox((0, 0), h_txt, font=FONTS["hero_title"])
            draw.text(((WIDTH - (hb[2] - hb[0])) // 2, 237), h_txt, font=FONTS["hero_title"], fill=IDDAA_YELLOW)

        # 4 Temsilcimizin Kartları
        start_y = 314
        row_h = 282
        for i, item in enumerate(TURKISH_TEAMS_DATA):
            row_start = 0.35 + i * 0.30
            prog = ease_out_cubic((t - row_start) / 0.48)
            if prog <= 0.01:
                continue

            slide_x = int((1.0 - prog) * (-700 if i % 2 == 0 else 700))
            x1 = 55 + slide_x
            x2 = WIDTH - 55 + slide_x
            y1 = start_y + i * row_h
            y2 = y1 + row_h - 20

            is_win = item["is_win"] == "1"
            border_col = WIN_GREEN if is_win else LOSS_RED

            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=22,
                fill=IDDAA_CARD_BG,
                outline=border_col,
                width=4,
            )

            # Sol Kulüp Logosu Alanı
            logo_box_x = x1 + 22
            logo_box_y = y1 + 24
            draw.rounded_rectangle(
                [logo_box_x, logo_box_y, logo_box_x + 124, logo_box_y + 124],
                radius=18,
                fill=(255, 255, 255),
                outline=IDDAA_YELLOW,
                width=3,
            )
            c_logo = club_logos.get(item["logo"])
            if c_logo is not None:
                frame.paste(c_logo, (logo_box_x + 8, logo_box_y + 8), c_logo)

            # Turnuva Başlığı & Takım
            tx = x1 + 168
            draw.text((tx, y1 + 20), item["tournament"], font=FONTS["tournament"], fill=IDDAA_MINT)
            draw.text((tx, y1 + 52), item["match"], font=FONTS["match_score"], fill=WHITE)

            # Sağ Üst Sonuç Rozeti (GALİBİYET / MAĞLUBİYET)
            badge_prog = ease_out_back((t - (row_start + 0.25)) / 0.35)
            if badge_prog > 0.05:
                bx1 = x2 - 250
                by1 = y1 + 32
                bx2 = x2 - 22
                by2 = by1 + 58
                draw.rounded_rectangle(
                    [bx1, by1, bx2, by2],
                    radius=14,
                    fill=WIN_DARK_BG if is_win else LOSS_DARK_BG,
                    outline=border_col,
                    width=3,
                )
                if is_win:
                    draw_check_icon(draw, bx1 + 28, by1 + 29, 11, WIN_GREEN, width=4)
                    draw.text((bx1 + 50, by1 + 15), item["status"], font=FONTS["badge"], fill=WIN_GREEN)
                else:
                    draw_cross_icon(draw, bx1 + 28, by1 + 29, 11, LOSS_RED, width=4)
                    draw.text((bx1 + 48, by1 + 15), item["status"], font=FONTS["badge"], fill=(255, 130, 130))

            # Alt Puan Durumu & Sıralama Şeridi
            bar_y1 = y1 + 164
            bar_y2 = y2 - 16
            draw.rounded_rectangle(
                [x1 + 22, bar_y1, x2 - 22, bar_y2],
                radius=14,
                fill=UEFA_BLUE_BG,
                outline=(0, 140, 75),
                width=2,
            )

            # Sıra Rozeti
            draw.rounded_rectangle(
                [x1 + 34, bar_y1 + 12, x1 + 195, bar_y2 - 12],
                radius=10,
                fill=IDDAA_YELLOW if is_win else (35, 95, 62),
            )
            rank_col = DARK_GREEN_TEXT if is_win else WHITE
            rb = draw.textbbox((0, 0), item["rank"], font=FONTS["standings_val"])
            draw.text(
                (x1 + 34 + (161 - (rb[2] - rb[0])) // 2, bar_y1 + 20),
                item["rank"],
                font=FONTS["standings_val"],
                fill=rank_col,
            )

            # Puan Rozeti
            draw.rounded_rectangle(
                [x1 + 210, bar_y1 + 12, x1 + 365, bar_y2 - 12],
                radius=10,
                fill=WIN_DARK_BG if is_win else LOSS_DARK_BG,
                outline=border_col,
                width=2,
            )
            pb = draw.textbbox((0, 0), item["points"], font=FONTS["standings_val"])
            draw.text(
                (x1 + 210 + (155 - (pb[2] - pb[0])) // 2, bar_y1 + 20),
                item["points"],
                font=FONTS["standings_val"],
                fill=IDDAA_YELLOW,
            )

            # Maç & Averaj Detayı
            draw.text(
                (x1 + 388, bar_y1 + 22),
                item["stats"],
                font=FONTS["standings_lbl"],
                fill=WHITE,
            )

        # En Alt Haftalık Bilanço Kutusu
        sum_start = 1.65
        sum_prog = ease_out_back((t - sum_start) / 0.45)
        if sum_prog > 0.05:
            sy1 = 1455
            sy2 = 1575
            pulse = int(math.sin(t * 6.0) * 5)
            draw.rounded_rectangle(
                [55 - pulse, sy1 - pulse, WIDTH - 55 + pulse, sy2 + pulse],
                radius=20,
                fill=IDDAA_YELLOW,
                outline=WHITE,
                width=3,
            )
            draw.text((82, sy1 + 42), "HAFTALIK AVRUPA BİLANÇOMUZ:", font=FONTS["summary_title"], fill=DARK_GREEN_TEXT)
            draw.rounded_rectangle([580, sy1 + 20, 995, sy2 - 20], radius=14, fill=DARK_GREEN_TEXT)
            s_txt = "2 GALİBİYET  •  2 YENİLGİ"
            sb = draw.textbbox((0, 0), s_txt, font=FONTS["summary_title"])
            draw.text((580 + (415 - (sb[2] - sb[0])) // 2, sy1 + 41), s_txt, font=FONTS["summary_title"], fill=IDDAA_YELLOW)

        draw_header_and_footer(frame, draw, logo_img, payload_header, "coupon", cta_text, t, total_dur)

        if f_idx == int(3.0 * FPS):
            frame.save(poster_path)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {proc.returncode}")

    print(f"[3/3] Temsilcilerimiz Avrupa Özeti Reels hazır: {video_path}")


if __name__ == "__main__":
    main()
