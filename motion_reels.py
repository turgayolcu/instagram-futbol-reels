"""
Motion Graphics + Türkçe Spiker Seslendirmeli (edge-tts) + Arka Plan Müzikli
Instagram Reels Üretim Motoru (1080x1920 @ 30fps)
"""

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import edge_tts
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
DEFAULT_JSON = BASE_DIR / "default_data.json"
LOGO_PATH = ASSETS_DIR / "iddaa_logo.png"

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
}


def build_voiceover_text(payload: Dict[str, Any], mode: str, category: str) -> str:
    custom_key = f"voiceover_{mode}"
    if payload.get(custom_key):
        return str(payload[custom_key])

    cta_speech = {
        "spor": "Hemen oynamak için iddaa nokta com'a gir, bayi kodunu 304 168 yap!",
        "tjk": "Hemen oynamak için TJK bayi kodunu 1607 yap!",
        "millipiyango": "Hemen oynamak için Milli Piyango bayi kodunu 117 718 yap!",
    }.get(category, "Hemen oynamak için iddaa nokta com'a gir, bayi kodunu 304 168 yap!")

    if mode == "odds":
        matches = payload.get("matches", [])[:12]
        top_pairs = [f"{m['home']} - {m['away']}" for m in matches[:3]]
        featured = ", ".join(top_pairs)
        return (
            f"Günün maçları ve iddaa oranları belli oldu! "
            f"Bültenin zirvesinde {featured} karşılaşmaları dikkat çekiyor. "
            f"{cta_speech}"
        )
    elif mode == "coupon":
        items = payload.get("coupon", [])[:6]
        picks = [f"{c['home']} {c['away']} maçı {c['pick']}" for c in items[:3]]
        picks_str = ", ".join(picks)
        tot = payload.get("total_odd", "")
        return (
            f"Günün banko kuponu hazır! "
            f"Kuponumuzda {picks_str} seçimleriyle toplam oran {tot}! "
            f"{cta_speech}"
        )
    else:
        # Akşam maç sonuçları -> "Hemen oyna" kesinlikle söylenmez!
        matches = payload.get("matches", [])[:12]
        res_list = [f"{m['home']} {m['score'].replace('-', '')} {m['away']}" for m in matches[:3]]
        res_str = ", ".join(res_list)
        return (
            f"Günün maç sonuçları! "
            f"Bugün tamamlanan karşılaşmalarda {res_str} skorları kaydedildi. "
            f"Tüm maç sonuçları ekranınızda."
        )


async def generate_tts(text: str, out_mp3: Path, voice: str = "tr-TR-AhmetNeural") -> None:
    communicate = edge_tts.Communicate(text, voice=voice, rate="+8%", pitch="-2Hz")
    await communicate.save(str(out_mp3))


def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe.exe",
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


def render_frame(
    base_bg: Image.Image,
    logo_img: Image.Image,
    payload: Dict[str, Any],
    mode: str,
    cta_text: str,
    t: float,
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

    # 2) Üst Header Animasyonu (Slide Down: 0.0s -> 0.45s)
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

    # 3) Üst Şerit: Sabah ve Öğlen postlarında CTA Banner (Pop-in + Shine Sweep), Akşam Sonuçlarında sadece Tarih/Bülten
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

            # Parlama (shine) efekti
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

    # 4) Sütun Başlıkları (0.4s -> 0.7s)
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

    # 5) Staggered (Sıralı) Kart Animasyonları
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

            # İlk 2 satır (Türk takımları) için hafif nabız çerçeve parlaması
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
        # Mode == 'coupon' (Öğlen 15:00 Günün Banko Kuponu)
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

            # Tahmin Kutusu
            px = x1 + 560
            draw.rounded_rectangle(
                [px, y1 + 35, px + 225, y1 + 111],
                radius=12,
                fill=IDDAA_ODD_BOX_BG,
                outline=IDDAA_CARD_BORDER,
                width=2,
            )
            draw.text((px + 20, y1 + 56), str(c["pick"]), font=FONTS["odd"], fill=WHITE)

            # Oran Kutusu
            ox = x1 + 805
            draw.rounded_rectangle([ox, y1 + 35, ox + 135, y1 + 111], radius=12, fill=IDDAA_YELLOW)
            draw.text((ox + 32, y1 + 52), str(c["odd"]), font=FONTS["big_odd"], fill=DARK_GREEN_TEXT)

        # Toplam Oran Kutusu (Pop-in + Nabız Efekti)
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

    # 6) Alt +18 Bilgilendirme Bandı & İlerleme Çubuğu (Progress Bar)
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
    draw.text((178, fy + 18), payload["disclaimer"], font=FONTS["disc"], fill=IDDAA_YELLOW)

    # Dinamik Süre Çubuğu
    bar_w = int((WIDTH - 110) * min(1.0, t / max(0.1, total_dur)))
    if bar_w > 4:
        draw.rounded_rectangle([55, fy - 12, 55 + bar_w, fy - 5], radius=3, fill=IDDAA_YELLOW)

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
    vo_text = build_voiceover_text(payload, args.mode, args.category)
    tts_mp3 = OUTPUT_DIR / f"vo_{args.mode}.mp3"
    print(f"[1/3] Türkçe spiker seslendirmesi üretiliyor: \"{vo_text}\"")
    asyncio.run(generate_tts(vo_text, tts_mp3))

    vo_dur = get_audio_duration(tts_mp3)
    total_dur = max(8.0, min(15.0, vo_dur + 1.4))
    total_frames = int(total_dur * FPS)

    # 2) Ses Miksajı (Spiker Sesi + Arka Plan Müziği)
    mixed_audio = OUTPUT_DIR / f"mixed_{args.mode}.m4a"
    custom_music = ASSETS_DIR / "bg_music.mp3"
    if custom_music.exists():
        audio_cmd = [
            "ffmpeg.exe", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(tts_mp3),
            "-stream_loop", "-1", "-i", str(custom_music),
            "-filter_complex",
            f"[0:a]volume=1.35,apad[vo];[1:a]volume=0.16,afade=t=in:st=0:d=0.6,afade=t=out:st={total_dur-1.2}:d=1.2[bg];[vo][bg]amix=inputs=2:duration=shortest[a]",
            "-map", "[a]", "-t", f"{total_dur:.2f}", "-c:a", "aac", "-b:a", "192k",
            str(mixed_audio),
        ]
    else:
        af_synth = (
            f"aevalsrc='0.14*sin(2*PI*73.42*t)+0.11*sin(2*PI*110*t)+0.09*sin(2*PI*146.83*t)"
            f"+0.08*sin(2*PI*220*t)*(0.55+0.45*sin(2*PI*2.0*t))':s=44100:d={total_dur:.2f}"
        )
        audio_cmd = [
            "ffmpeg.exe", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(tts_mp3),
            "-f", "lavfi", "-i", af_synth,
            "-filter_complex",
            f"[0:a]volume=1.40,apad[vo];[1:a]volume=0.22,afade=t=in:st=0:d=0.5,afade=t=out:st={total_dur-1.2}:d=1.2[bg];[vo][bg]amix=inputs=2:duration=shortest[a]",
            "-map", "[a]", "-t", f"{total_dur:.2f}", "-c:a", "aac", "-b:a", "192k",
            str(mixed_audio),
        ]
    subprocess.run(audio_cmd, check=True)

    # 3) 30 FPS Motion Graphics Karelerini FFmpeg'e Akıt (Pipe)
    poster_path = OUTPUT_DIR / f"reels_{args.mode}_latest.png"
    video_path = OUTPUT_DIR / f"reels_{args.mode}_latest.mp4"

    base_bg = build_base_gradient()
    logo_img = Image.open(LOGO_PATH).convert("RGB").resize((305, 80)) if LOGO_PATH.exists() else None

    print(f"[2/3] 30 FPS Motion Graphics kareleri işleniyor ({total_frames} kare, {total_dur:.1f} sn)...")
    ffmpeg_cmd = [
        "ffmpeg.exe", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        "-i", str(mixed_audio),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest",
        str(video_path),
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    last_frame = None
    for f_idx in range(total_frames):
        t = f_idx / FPS
        frame = render_frame(base_bg, logo_img, payload, args.mode, cta_text, t, total_dur)
        proc.stdin.write(frame.tobytes())
        if f_idx == total_frames - 1:
            last_frame = frame

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg video birleştirme hatası: {proc.returncode}")

    if last_frame is not None:
        last_frame.save(poster_path)

    print(f"[3/3] Motion Graphics + Seslendirmeli Reels hazır: {video_path}")


if __name__ == "__main__":
    main()
