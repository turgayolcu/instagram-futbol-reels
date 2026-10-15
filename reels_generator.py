"""
Instagram Futbol Reels Otomasyon Motoru
Konseptler:
1) Sabah 10:00  -> Günün Maçları & iddaa.com MS Oranları (Max 12 Maç)
2) Öğlen 15:00  -> Türkiye Süper Lig Şampiyon Takımlar Günün Haberi (Rotasyonlu)
3) Akşam 23:59 (Hafta İçi) / 22:30 (Hafta Sonu) -> Günün Biten Maç Sonuçları (Max 12 Maç)

Format: 1080x1920 (9:16), Sinematik Metin + Arka Plan Müziği + '+18 | Sadece bilgilendirme amaçlıdır.'
"""

import json
import math
import os
import struct
import subprocess
import sys
import wave
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
STATE_FILE = BASE_DIR / "state.json"

WIDTH = 1080
HEIGHT = 1920
DISCLAIMER_TEXT = "+18 | Sadece bilgilendirme amaçlıdır."

SUPER_LIG_CHAMPIONS = [
    "Galatasaray",
    "Fenerbahçe",
    "Beşiktaş",
    "Trabzonspor",
    "Başakşehir",
    "Bursaspor",
]


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def get_next_rotated_team() -> str:
    """Her gün aynı takımla ilgili haber vermemek için rotasyon yapar."""
    ensure_dirs()
    last_team = None
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            last_team = data.get("last_news_team")
        except Exception:
            pass

    if last_team in SUPER_LIG_CHAMPIONS:
        idx = (SUPER_LIG_CHAMPIONS.index(last_team) + 1) % len(SUPER_LIG_CHAMPIONS)
    else:
        idx = 0

    selected = SUPER_LIG_CHAMPIONS[idx]
    STATE_FILE.write_text(
        json.dumps(
            {
                "last_news_team": selected,
                "updated_at": datetime.now().isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return selected


def load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def create_cinematic_background(theme: str = "default") -> Image.Image:
    """Stadyum ışıkları ve koyu sinematik gradyan arka plan üretir."""
    bg_file = ASSETS_DIR / f"bg_{theme}.png"
    if bg_file.exists():
        return Image.open(bg_file).convert("RGB").resize((WIDTH, HEIGHT))

    img = Image.new("RGB", (WIDTH, HEIGHT), (8, 12, 24))
    draw = ImageDraw.Draw(img)

    # Temaya göre renk paleti (Şampiyonlar Ligi: Lacivert/Altın, Avrupa Ligi: Koyu Turuncu/Siyah, Normal: Zümrüt/Koyu Lacivert)
    if theme == "ucl":
        top_color, bottom_color, glow_color = (6, 15, 45), (3, 6, 18), (30, 90, 220)
    elif theme == "uel":
        top_color, bottom_color, glow_color = (35, 16, 6), (12, 6, 4), (230, 110, 20)
    else:
        top_color, bottom_color, glow_color = (10, 26, 22), (5, 10, 18), (20, 160, 100)

    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Sinematik ışık hüzmesi
    glow = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse(
        [WIDTH // 2 - 420, 120, WIDTH // 2 + 420, 960],
        fill=glow_color,
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=160))
    img = Image.blend(img, glow, alpha=0.28)
    return img


def draw_disclaimer_footer(draw: ImageDraw.ImageDraw) -> None:
    """Her görselin altına zorunlu +18 ve bilgilendirme uyarısını çizer."""
    footer_y = HEIGHT - 130
    draw.rounded_rectangle(
        [70, footer_y, WIDTH - 70, footer_y + 72],
        radius=16,
        fill=(18, 18, 24),
        outline=(220, 50, 50),
        width=2,
    )
    # +18 Rozeti
    draw.rounded_rectangle(
        [90, footer_y + 12, 165, footer_y + 60],
        radius=10,
        fill=(210, 35, 35),
    )
    badge_font = load_font(28, bold=True)
    text_font = load_font(26, bold=False)
    draw.text((102, footer_y + 19), "+18", font=badge_font, fill=(255, 255, 255))
    draw.text(
        (185, footer_y + 21),
        "Sadece bilgilendirme amaçlıdır.",
        font=text_font,
        fill=(230, 230, 235),
    )


def render_matches_poster(
    title: str,
    subtitle: str,
    matches: List[Dict[str, str]],
    mode: str = "odds",
    theme: str = "default",
    output_path: Optional[Path] = None,
) -> Path:
    """
    mode='odds': Sabah 10:00 Günün Maçları + Saat + MS 1 / X / 2 iddaa.com oranları (Max 12 maç)
    mode='results': Akşam Günün Maç Sonuçları (Max 12 maç)
    """
    ensure_dirs()
    img = create_cinematic_background(theme=theme)
    draw = ImageDraw.Draw(img)

    title_font = load_font(54, bold=True)
    sub_font = load_font(28, bold=False)
    header_font = load_font(24, bold=True)
    match_font = load_font(27, bold=True)
    odd_font = load_font(25, bold=True)
    league_font = load_font(20, bold=False)

    # Üst Başlık Alanı
    draw.text((70, 95), title.upper(), font=title_font, fill=(255, 215, 80))
    draw.text((70, 165), subtitle, font=sub_font, fill=(200, 215, 230))
    draw.line([(70, 215), (WIDTH - 70, 215)], fill=(255, 215, 80), width=3)

    if mode == "odds":
        draw.text((70, 230), "SAAT / KARŞILAŞMA", font=header_font, fill=(160, 180, 200))
        draw.text((740, 230), "MS1     X     MS2", font=header_font, fill=(255, 215, 80))
    else:
        draw.text((70, 230), "LİG / KARŞILAŞMA", font=header_font, fill=(160, 180, 200))
        draw.text((850, 230), "SKOR", font=header_font, fill=(255, 215, 80))

    capped_matches = matches[:12]
    start_y = 275
    row_h = 118

    for idx, m in enumerate(capped_matches):
        y = start_y + idx * row_h
        draw.rounded_rectangle(
            [65, y, WIDTH - 65, y + row_h - 12],
            radius=14,
            fill=(16, 24, 38),
            outline=(45, 65, 95),
            width=2,
        )

        league = m.get("league", "")
        time_str = m.get("time", "")
        home = m.get("home", "")
        away = m.get("away", "")

        if mode == "odds":
            meta_line = f"{time_str}  •  {league}"
            draw.text((90, y + 14), meta_line, font=league_font, fill=(130, 190, 255))
            draw.text(
                (90, y + 46),
                f"{home} - {away}"[:32],
                font=match_font,
                fill=(255, 255, 255),
            )
            ms1 = m.get("ms1", "-")
            msx = m.get("msx", "-")
            ms2 = m.get("ms2", "-")
            for j, val in enumerate([ms1, msx, ms2]):
                bx = 720 + j * 95
                draw.rounded_rectangle(
                    [bx, y + 26, bx + 84, y + 80],
                    radius=8,
                    fill=(28, 42, 64),
                    outline=(255, 205, 70),
                    width=1,
                )
                draw.text((bx + 14, y + 39), str(val), font=odd_font, fill=(255, 230, 110))
        else:
            score = m.get("score", "0 - 0")
            draw.text((90, y + 14), f"MS  •  {league}", font=league_font, fill=(130, 230, 165))
            draw.text(
                (90, y + 46),
                f"{home} - {away}"[:34],
                font=match_font,
                fill=(255, 255, 255),
            )
            draw.rounded_rectangle(
                [820, y + 24, 985, y + 82],
                radius=10,
                fill=(25, 85, 55),
                outline=(90, 220, 140),
                width=2,
            )
            draw.text((855, y + 38), score, font=match_font, fill=(255, 255, 255))

    draw_disclaimer_footer(draw)

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"poster_{mode}_{ts}.png"
    img.save(output_path)
    return output_path


def render_news_poster(
    team: str,
    headline: str,
    summary_lines: List[str],
    theme: str = "default",
    output_path: Optional[Path] = None,
) -> Path:
    """Öğlen 15:00 Süper Lig Şampiyon Takım Haberi için sinematik poster üretir."""
    ensure_dirs()
    img = create_cinematic_background(theme=theme)
    draw = ImageDraw.Draw(img)

    badge_font = load_font(30, bold=True)
    title_font = load_font(56, bold=True)
    body_font = load_font(34, bold=False)

    # Üst Kulüp Etiketi
    draw.rounded_rectangle(
        [70, 140, 520, 210],
        radius=14,
        fill=(220, 165, 30),
    )
    draw.text(
        (95, 157),
        f"SÜPER LİG • {team.upper()}",
        font=badge_font,
        fill=(10, 12, 18),
    )

    # Sinematik Haber Kartı
    draw.rounded_rectangle(
        [70, 260, WIDTH - 70, 1620],
        radius=28,
        fill=(14, 22, 36),
        outline=(255, 210, 80),
        width=3,
    )

    # Başlık satır kaydırma
    words = headline.upper().split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if len(test) <= 22:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    y = 330
    for line in lines[:5]:
        draw.text((110, y), line, font=title_font, fill=(255, 220, 90))
        y += 74

    draw.line([(110, y + 25), (WIDTH - 110, y + 25)], fill=(70, 95, 130), width=2)
    y += 75

    for paragraph in summary_lines:
        p_words = paragraph.split()
        p_lines, p_cur = [], ""
        for w in p_words:
            test = f"{p_cur} {w}".strip()
            if len(test) <= 38:
                p_cur = test
            else:
                p_lines.append(p_cur)
                p_cur = w
        if p_cur:
            p_lines.append(p_cur)

        for pl in p_lines:
            draw.text((110, y), pl, font=body_font, fill=(235, 240, 248))
            y += 52
        y += 30

    draw_disclaimer_footer(draw)

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"poster_news_{ts}.png"
    img.save(output_path)
    return output_path


def ensure_background_music(duration_sec: int = 12) -> Path:
    """
    assets/bg_music.mp3 veya .wav varsa onu kullanır;
    yoksa sinematik koyu atmosferik bir arka plan ritmi (WAV) üretir.
    """
    ensure_dirs()
    for ext in ("mp3", "wav", "m4a"):
        custom = ASSETS_DIR / f"bg_music.{ext}"
        if custom.exists():
            return custom

    wav_path = ASSETS_DIR / "cinematic_ambient.wav"
    if wav_path.exists():
        return wav_path

    sample_rate = 44100
    n_samples = sample_rate * duration_sec
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        # Sinematik derin bas + akor pad + nabız ritmi (Dm9 atmosferi)
        freqs = [73.42, 110.0, 146.83, 174.61, 220.0]
        for i in range(n_samples):
            t = i / sample_rate
            pulse = 0.65 + 0.35 * math.sin(2 * math.pi * 1.5 * t)
            fade = min(1.0, t / 1.0, (duration_sec - t) / 1.5)
            val = 0.0
            for f in freqs:
                val += math.sin(2 * math.pi * f * t)
            val = (val / len(freqs)) * pulse * fade * 0.35
            sample = int(max(-1.0, min(1.0, val)) * 32767)
            frames.extend(struct.pack("<hh", sample, sample))
        wf.writeframes(frames)

    return wav_path


def create_reels_video(
    image_path: Path,
    output_video_path: Optional[Path] = None,
    duration_sec: int = 12,
) -> Path:
    """
    Görseli yumuşak sinematik zoom (Ken Burns) ve arka plan müziği ile
    1080x1920 30fps MP4 Reels videosuna dönüştürür.
    """
    ensure_dirs()
    if output_video_path is None:
        output_video_path = image_path.with_suffix(".mp4")

    music_path = ensure_background_music(duration_sec=duration_sec)

    # FFmpeg ile 9:16 sinematik yavaş zoom + fade-in/out + ses birleştirme
    vf_filter = (
        f"scale=1200:2134,"
        f"zoompan=z='min(zoom+0.0004,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={duration_sec * 30}:s=1080x1920:fps=30,"
        f"fade=t=in:st=0:d=0.8,fade=t=out:st={duration_sec - 1}:d=1.0,"
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-i",
        str(music_path),
        "-vf",
        vf_filter,
        "-t",
        str(duration_sec),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_video_path),
    ]
    subprocess.run(cmd, check=True)
    return output_video_path


def publish_to_instagram(video_path: Path, caption: str) -> bool:
    """
    .env veya ortam değişkenlerinde IG_USERNAME ve IG_PASSWORD tanımlıysa
    instagrapi ile Reels olarak paylaşır.
    """
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    username = os.environ.get("IG_USERNAME")
    password = os.environ.get("IG_PASSWORD")
    if not username or not password:
        print(
            f"[BİLGİ] IG_USERNAME / IG_PASSWORD henüz .env dosyasına girilmediği için "
            f"video yerel olarak hazırlandı: {video_path}"
        )
        return False

    from instagrapi import Client

    cl = Client()
    session_file = BASE_DIR / "ig_session.json"
    if session_file.exists():
        cl.load_settings(str(session_file))
    cl.login(username, password)
    cl.dump_settings(str(session_file))
    cl.clip_upload(str(video_path), caption=caption)
    print(f"[BAŞARILI] Reels Instagram'da paylaşıldı: {video_path}")
    return True


if __name__ == "__main__":
    # Örnek test çalıştırması
    sample_matches = [
        {"time": "20:00", "league": "Süper Lig", "home": "Galatasaray", "away": "Antalyaspor", "ms1": "1.28", "msx": "4.60", "ms2": "6.80"},
        {"time": "19:00", "league": "Süper Lig", "home": "Fenerbahçe", "away": "Samsunspor", "ms1": "1.35", "msx": "4.20", "ms2": "5.90"},
        {"time": "22:00", "league": "La Liga", "home": "Real Madrid", "away": "Villarreal", "ms1": "1.42", "msx": "4.10", "ms2": "5.10"},
        {"time": "19:30", "league": "Premier Lig", "home": "Manchester City", "away": "Fulham", "ms1": "1.22", "msx": "5.20", "ms2": "8.40"},
        {"time": "21:45", "league": "Serie A", "home": "Juventus", "away": "Cagliari", "ms1": "1.48", "msx": "3.75", "ms2": "5.40"},
        {"time": "19:30", "league": "Bundesliga", "home": "Bayern Münih", "away": "Stuttgart", "ms1": "1.38", "msx": "4.40", "ms2": "5.60"},
        {"time": "21:45", "league": "Ligue 1", "home": "PSG", "away": "Strasbourg", "ms1": "1.30", "msx": "4.70", "ms2": "6.50"},
    ]
    poster = render_matches_poster(
        title="GÜNÜN MAÇLARI",
        subtitle="15 EKİM • SÜPER LİG & AVRUPA DEVLERİ",
        matches=sample_matches,
        mode="odds",
        theme="default",
    )
    print(f"Poster üretildi: {poster}")
