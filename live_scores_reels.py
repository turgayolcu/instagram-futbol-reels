"""
Mackolik Canlı Skorlar Reels Üreticisi (1080x1920 @ 30fps)
- Verileri doğrudan anlık olarak Mackolik Canlı Sonuçlar servisinden (vd.mackolik.com/livedata) çeker
- Seslendirme YOK (Hareketli global EDM/Dance parçası: 'Everybody Up')
- Şu an oynanan en popüler 6 maçın canlı dakikası, ligi ve anlık skorları
"""

import json
import math
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw

from motion_reels import (
    ALERT_RED,
    ASSETS_DIR,
    FPS,
    HEIGHT,
    IDDAA_CARD_BG,
    IDDAA_CARD_BORDER,
    IDDAA_MINT,
    IDDAA_PRIMARY_GREEN,
    IDDAA_SUBBAR_GREEN,
    IDDAA_YELLOW,
    LOGO_PATH,
    OUTPUT_DIR,
    WIDTH,
    WHITE,
    build_base_gradient,
    ease_out_back,
    ease_out_cubic,
    load_font,
)

GLOBAL_MUSIC_PATH = ASSETS_DIR / "global_trend_music.mp3"
GLOBAL_MUSIC_URL = "https://upload.wikimedia.org/wikipedia/commons/4/4b/Everybody_Up_by_Sascha_Ende.mp3"
MACKOLIK_LIVE_URL = "https://vd.mackolik.com/livedata?group=0"

FONTS = {
    "banner": load_font(32, True),
    "subbar": load_font(24, True),
    "head": load_font(21, True),
    "live_badge": load_font(20, True),
    "league": load_font(20, True),
    "team": load_font(28, True),
    "score": load_font(38, True),
    "badge18": load_font(26, True),
    "disc": load_font(25, True),
}


def fetch_mackolik_live_matches() -> List[Dict[str, str]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9",
        "Referer": "https://arsiv.mackolik.com/Canli-Sonuclar",
    }
    req = urllib.request.Request(MACKOLIK_LIVE_URL, headers=headers)
    raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
    data = json.loads(raw)

    candidates: List[Dict[str, Any]] = []
    for idx, m in enumerate(data.get("m", [])):
        if len(m) < 37:
            continue
        comp = m[36]
        # comp[11] == 1 -> Futbol
        if len(comp) < 12 or comp[11] != 1:
            continue
        status_code = m[5]
        # 1: 1. Devre, 2: Devre Arası (İY), 3: 2. Devre
        if status_code not in (1, 2, 3):
            continue

        country = str(comp[1]).strip()
        league = str(comp[3]).strip()
        home = str(m[2]).strip()
        away = str(m[4]).strip()
        if any(bad in f" {home} {away} {league} " for bad in (" II ", " U21", " U19", " U20", "Bölgesel", " Amatör", "(K)")):
            continue
        minute_raw = str(m[6]).strip()
        if minute_raw == "IY":
            minute_raw = "İY"
        status_txt = f"CANLI {minute_raw}'" if minute_raw.isdigit() else f"CANLI {minute_raw}"
        score_txt = f"{m[12]} - {m[13]}"

        # Popüler lig ve takımlara öncelik puanı
        prio = 1000 - idx
        if "Türkiye" in country:
            prio += 5000
        elif country in ("İngiltere", "İspanya", "İtalya", "Almanya", "Fransa", "Hollanda"):
            prio += 2500
        elif country in ("Avusturya", "Danimarka", "Belçika", "Portekiz"):
            prio += 1500

        if any(t in f"{home} {away}" for t in ("Reims", "Hertha Berlin", "Heerenveen", "Rapid Wien", "Nürnberg", "Rizespor")):
            prio += 800

        candidates.append(
            {
                "prio": prio,
                "status": status_txt,
                "league": f"{country} • {league}",
                "home": home,
                "away": away,
                "score": score_txt,
            }
        )

    candidates.sort(key=lambda x: -x["prio"])
    selected: List[Dict[str, str]] = []
    league_counts: Dict[str, int] = {}
    for c in candidates:
        lg = c["league"]
        if league_counts.get(lg, 0) >= 2 and len(candidates) > 8:
            continue
        league_counts[lg] = league_counts.get(lg, 0) + 1
        selected.append(
            {
                "status": c["status"],
                "league": c["league"],
                "home": c["home"],
                "away": c["away"],
                "score": c["score"],
                "highlight": "true" if len(selected) < 2 else "false",
            }
        )
        if len(selected) == 6:
            break

    return selected


def ensure_global_music() -> None:
    if GLOBAL_MUSIC_PATH.exists() and GLOBAL_MUSIC_PATH.stat().st_size > 200000:
        return
    req = urllib.request.Request(GLOBAL_MUSIC_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        GLOBAL_MUSIC_PATH.write_bytes(r.read())
    print(f"[OK] Global hareketli parça indirildi: {GLOBAL_MUSIC_PATH.name}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    ensure_global_music()

    live_matches = fetch_mackolik_live_matches()
    print(f"[OK] Mackolik'ten {len(live_matches)} canlı maç çekildi:")
    for i, m in enumerate(live_matches, 1):
        print(f"  {i}. [{m['status']} | {m['league']}] {m['home']} {m['score']} {m['away']}")

    # JSON olarak da kaydet
    (OUTPUT_DIR / "mackolik_live_latest.json").write_text(
        json.dumps(live_matches, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    total_dur = 13.0
    total_frames = int(total_dur * FPS)

    # 1) Hareketli Global Parça (Seslendirme YOK)
    audio_out = OUTPUT_DIR / "mixed_live_scores.m4a"
    audio_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", "18.0",
        "-i", str(GLOBAL_MUSIC_PATH),
        "-filter_complex",
        f"[0:a]bass=g=4:f=100,treble=g=2,volume=1.25,afade=t=in:st=0:d=0.5,afade=t=out:st={total_dur-1.2}:d=1.2[a]",
        "-map", "[a]", "-t", f"{total_dur:.2f}", "-c:a", "aac", "-b:a", "192k",
        str(audio_out),
    ]
    subprocess.run(audio_cmd, check=True)

    base_bg = build_base_gradient()
    logo_img = Image.open(LOGO_PATH).convert("RGB").resize((305, 80)) if LOGO_PATH.exists() else None

    video_path = OUTPUT_DIR / "reels_mackolik_canli_skorlar.mp4"
    poster_path = OUTPUT_DIR / "reels_mackolik_canli_skorlar.png"

    ffmpeg_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        "-i", str(audio_out),
        "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest",
        str(video_path),
    ]

    print(f"[1/2] Mackolik Canlı Skorlar Reels üretiliyor ({total_frames} kare)...")
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    for f_idx in range(total_frames):
        t = f_idx / FPS
        frame = base_bg.copy()
        draw = ImageDraw.Draw(frame)

        # Hareketli Stadyum Spot Işığı
        sweep_x = int(WIDTH * 0.5 + math.sin(t * 2.2) * 240)
        sweep_y = int(640 + math.cos(t * 1.6) * 180)
        draw.ellipse([sweep_x - 380, sweep_y - 280, sweep_x + 380, sweep_y + 280], fill=(10, 88, 45))

        # Üst Header
        header_prog = ease_out_cubic(t / 0.45)
        hy = int((1.0 - header_prog) * -200)
        draw.rectangle([0, hy, WIDTH, hy + 130], fill=IDDAA_PRIMARY_GREEN)
        draw.rectangle([0, hy + 130, WIDTH, hy + 202], fill=IDDAA_SUBBAR_GREEN)
        if logo_img is not None:
            frame.paste(logo_img, (55, hy + 24))

        draw.text((415, hy + 46), "CANLI MAÇ SKORLARI", font=FONTS["banner"], fill=IDDAA_YELLOW)

        # Canlı Yayın İndikatörü (Üst Alt-Bar)
        pulse_live = int(t * 4) % 2 == 0
        draw.ellipse([60, hy + 152, 84, hy + 176], fill=ALERT_RED if pulse_live else (255, 110, 110))
        draw.text((100, hy + 148), "CANLI SKOR MERKEZİ  •  KAYNAK: MACKOLİK", font=FONTS["subbar"], fill=WHITE)

        # Sütun Başlıkları
        if t > 0.30:
            draw.text((60, 225), "DAKİKA / LİG / KARŞILAŞMA", font=FONTS["head"], fill=IDDAA_MINT)
            draw.text((805, 225), "CANLI SKOR", font=FONTS["head"], fill=IDDAA_YELLOW)

        # 6 Canlı Maç Kartı
        start_y = 270
        row_h = 235
        for i, m in enumerate(live_matches):
            row_start = 0.40 + i * 0.24
            prog = ease_out_back((t - row_start) / 0.48)
            if prog <= 0.02:
                continue

            slide_x = int((1.0 - min(1.0, prog)) * 680)
            x1 = 55 + slide_x
            x2 = WIDTH - 55 + slide_x
            y1 = start_y + i * row_h
            y2 = y1 + row_h - 22

            is_top = m.get("highlight") == "true"
            border_c = IDDAA_YELLOW if (is_top and int(t * 4) % 2 == 0) else IDDAA_CARD_BORDER
            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=20,
                fill=IDDAA_CARD_BG,
                outline=border_c,
                width=4 if is_top else 2,
            )

            # Yanıp sönen Kırmızı CANLI Rozeti
            draw.rounded_rectangle([x1 + 26, y1 + 22, x1 + 176, y1 + 64], radius=10, fill=ALERT_RED)
            dot_c = WHITE if int(t * 5) % 2 == 0 else IDDAA_YELLOW
            draw.ellipse([x1 + 40, y1 + 36, x1 + 54, y1 + 50], fill=dot_c)
            draw.text((x1 + 64, y1 + 29), m["status"], font=FONTS["live_badge"], fill=WHITE)

            # Lig adı
            draw.text((x1 + 194, y1 + 29), f"|   {m['league']}", font=FONTS["league"], fill=IDDAA_MINT)

            # Takımlar
            match_str = f"{m['home']}  -  {m['away']}"[:32]
            draw.text((x1 + 28, y1 + 98), match_str, font=FONTS["team"], fill=WHITE)

            # Skor Kutusu
            sx = x1 + 725
            sy = y1 + 48
            draw.rounded_rectangle(
                [sx, sy, sx + 210, sy + 118],
                radius=18,
                fill=IDDAA_YELLOW if is_top else IDDAA_PRIMARY_GREEN,
                outline=WHITE if is_top else IDDAA_YELLOW,
                width=3,
            )
            sc_txt = m["score"]
            bs = draw.textbbox((0, 0), sc_txt, font=FONTS["score"])
            sw = bs[2] - bs[0]
            draw.text(
                (sx + (210 - sw) // 2, sy + 32),
                sc_txt,
                font=FONTS["score"],
                fill=(6, 40, 18) if is_top else IDDAA_YELLOW,
            )

        # Alt +18 Bilgilendirme Bandı
        fy = HEIGHT - 120
        draw.rounded_rectangle([55, fy, WIDTH - 55, fy + 72], radius=16, fill=IDDAA_SUBBAR_GREEN, outline=IDDAA_YELLOW, width=2)
        draw.rounded_rectangle([75, fy + 12, 159, fy + 60], radius=10, fill=(215, 35, 35))
        draw.text((86, fy + 17), "+18", font=FONTS["badge18"], fill=WHITE)
        draw.text((178, fy + 18), "|  Sadece bilgilendirme amaçlıdır.", font=FONTS["disc"], fill=IDDAA_YELLOW)

        bar_w = int((WIDTH - 110) * min(1.0, t / max(0.1, total_dur)))
        if bar_w > 4:
            draw.rounded_rectangle([55, fy - 12, 55 + bar_w, fy - 5], radius=3, fill=IDDAA_YELLOW)

        if f_idx == int(2.6 * FPS):
            frame.save(poster_path)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {proc.returncode}")

    print(f"[2/2] Mackolik Canlı Skor Reels hazır: {video_path}")


if __name__ == "__main__":
    main()
