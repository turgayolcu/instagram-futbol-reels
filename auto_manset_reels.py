"""
Otomatik Sabah 09:00 "VS Manşet" ve Öğlen 14:00 "Son 5 Maç Karnesi" Reels Üretim Motoru
- Saat 09:00 (--mode vs):
  * O gün Beşiktaş (3), Galatasaray (1) veya Fenerbahçe'nin (2) maçı varsa, maçı olan her büyük
    Türk takımı için rakibiyle VS temalı sanatsal dergi manşeti Reels hazırlar (birden fazlaysa 15 dk arayla paylaşır).
  * O gün büyük Türk takımının maçı yoksa, 3 FARKLI LİGDEN 3 büyük Avrupa maçını seçer ve
    15 dakika arayla VS temalı manşet Reels olarak paylaşır.
- Saat 14:00 (--mode last5):
  * O gün maçı olan büyük Türk takımının (yoksa günün en büyük Avrupa devinin) resmi armasıyla
    SON 5 MAÇ KARNESİNİ (skorlar, rakip armaları, G/B/M form durumu ve bugünkü maç oranları) manşet yapar.
- Seslendirme: %100 Yerel Türkçe Erkek Spiker (tr-TR-AhmetNeural).
- Kapanış: 2 aşamalı Kayıtlı Bayim (304168) ekranı ve +18 SORUMLU OYUN rozeti.
"""

import argparse
import asyncio
import concurrent.futures
import datetime
import io
import math
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://arsiv.mackolik.com/",
}
LIVEDATA_URL = "https://vd.mackolik.com/livedata?date={date}"


def is_basketball_or_other_sport(country: str, league: str, code: str, home: str, away: str) -> bool:
    combined = f"{country} {league} {code} {home} {away}".lower()
    bball_kw = [
        "basket", "euroleague", "eurocup", "nba", "bsl", "tb2l", "wnba", "fibaeurope",
        "anadolu efes", "fenerbahçe beko", "türk telekom", "bahçeşehir", "karşıyaka",
        "galatasaray mct", "çağdaş", "voleybol", "hentbol", "tenis", "snooker",
    ]
    return any(k in combined for k in bball_kw)


def is_excluded_football_category(country: str, league: str, code: str, home: str, away: str) -> bool:
    combined = f"{country} {league} {code} {home} {away}".lower()
    excl_kw = [
        "(k)", "kadın", "women", "u19", "u20", "u21", "u18", "u17",
        "genç", "youth", "rezerv", "reserve", "amatör", "Bölgesel",
    ]
    return any(k in combined for k in excl_kw)
from motion_reels import (
    ASSETS_DIR,
    BASE_DIR,
    FPS,
    HEIGHT,
    OUTRO_STEP1_PATH,
    OUTRO_STEP2_PATH,
    OUTRO_VOICEOVER_STEP1,
    OUTRO_VOICEOVER_STEP2,
    OUTPUT_DIR,
    STATIC_OUTRO1_MP3,
    STATIC_OUTRO2_MP3,
    WIDTH,
    ease_out_back,
    ease_out_cubic,
    expand_betting_terms_for_speech,
    generate_tts,
    get_audio_duration,
    load_font,
    render_outro_scene,
)
from upload_instagram import upload_reel

CRESTS_DIR = ASSETS_DIR / "crests"
CRESTS_DIR.mkdir(parents=True, exist_ok=True)

# Mackolik Büyük Türk Takımları ID'leri
TURKISH_GIANTS = {
    1: "Galatasaray",
    2: "Fenerbahçe",
    3: "Beşiktaş",
}

# Avrupa devleri ve önemli kulüpler (Türk takımı olmadığında öncelikli seçilecek takımlar)
EUROPEAN_GIANTS_KEYWORDS = [
    "Real Madrid", "Barcelona", "Atletico Madrid", "Atl. Madrid",
    "Man. City", "Manchester City", "Arsenal", "Liverpool", "Chelsea", "Man. Utd", "Tottenham", "Newcastle", "Aston Villa",
    "Bayern Münih", "B. Münih", "Dortmund", "B. Dortmund", "Leverkusen", "B. Leverkusen", "Leipzig",
    "Inter", "Milan", "Juventus", "Napoli", "Roma", "Atalanta", "Lazio",
    "PSG", "Paris Saint-Germain", "Marsilya", "Monaco", "Lille", "Lyon",
    "Benfica", "Sporting", "Porto", "Ajax", "PSV", "Feyenoord",
    "Trabzonspor",
]


def tr_upper(text: str) -> str:
    """Türkçe karakter duyarlı büyük harf dönüştürücü (i -> İ, ı -> I)."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def load_impact_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return load_font(size, True)


def fetch_team_crest(team_id: int, target_size: int = 220) -> Image.Image:
    """
    Mackolik'ten takımın resmi armasını indirir, şeffaf RGBA olarak temizler
    ve target_size boyutuna tam ölçekleyerek (upscale + keskinleştirme) döndürür.
    """
    cache_path = CRESTS_DIR / f"crest_{team_id}.png"
    img: Optional[Image.Image] = None
    if cache_path.exists() and cache_path.stat().st_size > 300:
        try:
            img = Image.open(cache_path).convert("RGBA")
        except Exception:
            img = None

    if img is None:
        url = f"https://im.mackolik.com/img/logo/buyuk/{team_id}.gif"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 200:
                raw_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                rw, rh = raw_img.size
                # Köşelerden floodfill ile SADECE dış beyaz arka planı şeffaf yap
                # (Kalkanın içindeki beyaz Beşiktaş/kulüp şeritleri siyah çerçeveyle korunduğu için %100 beyaz kalır!)
                for cx, cy in [(0, 0), (rw - 1, 0), (0, rh - 1), (rw - 1, rh - 1)]:
                    px = raw_img.getpixel((cx, cy))
                    if px[3] > 200 and px[0] > 235 and px[1] > 235 and px[2] > 235:
                        ImageDraw.floodfill(raw_img, (cx, cy), (0, 0, 0, 0), thresh=28)
                img = raw_img
                bbox = img.getbbox()
                if bbox:
                    img = img.crop(bbox)
                img.save(cache_path)
        except Exception as e:
            print(f"[UYARI] Arma indirilemedi (ID={team_id}): {e}")

    if img is None:
        img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([10, 10, 190, 190], fill=(15, 75, 42, 255), outline=(229, 230, 25, 255), width=8)

    # Boş kenarları tekrar kontrol et ve target_size'ın %82'sini dolduracak şekilde LANCZOS ile büyüt
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    inner_max = int(target_size * 0.84)
    w, h = img.size
    scale = min(inner_max / max(1, w), inner_max / max(1, h))
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if scale > 1.3:
        resized = resized.filter(ImageFilter.UnsharpMask(radius=1.4, percent=135, threshold=2))

    canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
    ox = (target_size - new_w) // 2
    oy = (target_size - new_h) // 2
    canvas.paste(resized, (ox, oy), resized)
    return canvas


def parse_today_football_matches(target_date: datetime.date) -> List[Dict[str, Any]]:
    date_str = target_date.strftime("%d/%m/%Y")
    resp = requests.get(LIVEDATA_URL.format(date=date_str), headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    raw_matches = data.get("m", [])

    parsed: List[Dict[str, Any]] = []
    for m in raw_matches:
        if not isinstance(m, list) or len(m) < 37:
            continue
        sport_type = m[5] if len(m) > 5 else 0
        if sport_type not in (0, 1, "0", "1"):
            # Mackolik'te futbol dışı branşları filtrele
            pass
        league_info = m[36] if isinstance(m[36], list) and len(m[36]) > 3 else [0, "Futbol", 0, ""]
        country_name = str(league_info[1]).strip()
        league_name = str(league_info[3]).strip()
        league_code = str(league_info[9]).strip() if len(league_info) > 9 else ""
        home_id = int(m[1]) if str(m[1]).isdigit() else 0
        home_name = str(m[2]).strip()
        away_id = int(m[3]) if str(m[3]).isdigit() else 0
        away_name = str(m[4]).strip()
        kickoff = str(m[16]).strip()

        if is_basketball_or_other_sport(country_name, league_name, league_code, home_name, away_name):
            continue
        if is_excluded_football_category(country_name, league_name, league_code, home_name, away_name):
            continue

        ms1 = str(m[18]).strip() if len(m) > 18 and m[18] else "-"
        ms0 = str(m[19]).strip() if len(m) > 19 and m[19] else "-"
        ms2 = str(m[20]).strip() if len(m) > 20 and m[20] else "-"
        alt25 = str(m[21]).strip() if len(m) > 21 and m[21] else "-"
        ust25 = str(m[22]).strip() if len(m) > 22 and m[22] else "-"

        # Oranı olmayan basketbol/diğer maçları atla (Büyük Türk takımları hariç)
        has_valid_odds = ms1 not in ("", "-", "0.00", "0") and ms2 not in ("", "-", "0.00", "0")
        is_turkish_giant = (
            home_id in TURKISH_GIANTS
            or away_id in TURKISH_GIANTS
            or any(g.lower() == home_name.lower() or g.lower() == away_name.lower() for g in TURKISH_GIANTS.values())
        )
        # EuroLeague basketbol maçlarında (Anadolu Efes vs Beşiktaş gibi) oran 0.00 olur, bunları kesinlikle ele
        if not has_valid_odds:
            continue

        full_league = f"{country_name} - {league_name}" if league_name and league_name != country_name else country_name

        # Önem puanı hesapla
        priority = 10
        if is_turkish_giant:
            priority += 1000
        if any(k in country_name.upper() for k in ["ŞAMPİYONLAR", "AVRUPA LİGİ", "KONFERANS"]):
            priority += 300
        elif any(k in country_name.upper() for k in ["TÜRKİYE", "İNGİLTERE", "İSPANYA", "İTALYA", "ALMANYA", "FRANSA"]):
            priority += 200
        if any(k.lower() in home_name.lower() or k.lower() in away_name.lower() for k in EUROPEAN_GIANTS_KEYWORDS):
            priority += 150

        parsed.append({
            "match_id": m[0],
            "home_id": home_id,
            "home": home_name,
            "away_id": away_id,
            "away": away_name,
            "time": kickoff,
            "date": date_str,
            "country": country_name,
            "league_sub": league_name,
            "league": full_league,
            "ms1": ms1,
            "ms0": ms0,
            "ms2": ms2,
            "alt25": alt25,
            "ust25": ust25,
            "is_turkish_giant": is_turkish_giant,
            "priority": priority,
        })

    parsed.sort(key=lambda x: (-x["priority"], x["time"]))
    return parsed


def select_morning_vs_matches(all_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sabah 09:00 kuralı:
    1) O gün Beşiktaş, Galatasaray veya Fenerbahçe'nin maçı varsa: kimin maçı varsa onları seç (en fazla 3'ü).
    2) Büyük Türk takımının maçı yoksa: 3 FARKLI LİGDEN en büyük 3 Avrupa maçını seç.
    """
    tr_giant_matches = []
    seen_tr_ids = set()
    for m in all_matches:
        for gid, gname in TURKISH_GIANTS.items():
            if (m["home_id"] == gid or m["away_id"] == gid or m["home"].lower() == gname.lower() or m["away"].lower() == gname.lower()):
                if gid not in seen_tr_ids:
                    seen_tr_ids.add(gid)
                    m_copy = dict(m)
                    m_copy["featured_team_id"] = gid
                    m_copy["featured_team_name"] = gname
                    tr_giant_matches.append(m_copy)

    if tr_giant_matches:
        return tr_giant_matches[:3]

    # Büyük Türk takımı yoksa 3 farklı ligden 3 büyük Avrupa maçı seç
    selected_euro = []
    seen_leagues = set()
    for m in all_matches:
        lg_key = f"{m['country']}_{m['league_sub']}".upper()
        if lg_key not in seen_leagues:
            seen_leagues.add(lg_key)
            selected_euro.append(m)
            if len(selected_euro) == 3:
                break

    # Eğer 3 farklı lig çıkmadıysa kalan en popüler maçlarla tamamla
    if len(selected_euro) < 3:
        for m in all_matches:
            if m not in selected_euro:
                selected_euro.append(m)
                if len(selected_euro) == 3:
                    break

    return selected_euro[:3]


def fetch_team_last_5_matches(team_id: int, team_name: str, before_date: datetime.date) -> List[Dict[str, Any]]:
    """
    Mackolik livedata arşivinden ilgili takımın son 5 tamamlanmış futbol maçını çeker.
    """
    dates = [(before_date - datetime.timedelta(days=i)).strftime("%d/%m/%Y") for i in range(1, 65)]

    def check_day(d_str: str) -> List[Dict[str, Any]]:
        try:
            r = requests.get(LIVEDATA_URL.format(date=d_str), headers=HEADERS, timeout=7).json()
            found = []
            for x in r.get("m", []):
                if not isinstance(x, list) or len(x) < 37:
                    continue
                h_id = int(x[1]) if str(x[1]).isdigit() else 0
                a_id = int(x[3]) if str(x[3]).isdigit() else 0
                h_name = str(x[2]).strip()
                a_name = str(x[4]).strip()
                if h_id != team_id and a_id != team_id:
                    continue
                status = str(x[6]).strip()
                if status not in ("MS", "Uz.", "Pen.", "Bitti"):
                    continue
                lg = x[36] if isinstance(x[36], list) and len(x[36]) > 3 else [0, "Futbol", 0, ""]
                c_name = str(lg[1]).strip()
                l_name = str(lg[3]).strip()
                if is_basketball_or_other_sport(c_name, l_name, "", h_name, a_name):
                    continue
                if "(K)" in h_name or "(K)" in a_name or "U19" in h_name or "U21" in h_name:
                    continue
                hg = int(x[12]) if str(x[12]).isdigit() else 0
                ag = int(x[13]) if str(x[13]).isdigit() else 0

                is_home = (h_id == team_id)
                if is_home:
                    res_code = "G" if hg > ag else ("B" if hg == ag else "M")
                else:
                    res_code = "G" if ag > hg else ("B" if hg == ag else "M")

                found.append({
                    "date": d_str[:5],  # GG/AA
                    "full_date": d_str,
                    "home_id": h_id,
                    "home": h_name,
                    "away_id": a_id,
                    "away": a_name,
                    "home_goals": hg,
                    "away_goals": ag,
                    "score": f"{hg} - {ag}",
                    "result": res_code,
                    "league": c_name,
                })
            return found
        except Exception:
            return []

    results: List[Dict[str, Any]] = []
    # İlk 35 günü tara, 5 maç dolmazsa kalan günleri tara
    for chunk in (dates[:35], dates[35:]):
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            for day_list in ex.map(check_day, chunk):
                for item in day_list:
                    results.append(item)
        if len(results) >= 5:
            break

    return results[:5]


def draw_torn_paper_edge(draw: ImageDraw.ImageDraw, y_center: int, color: Tuple[int, int, int], seed: int = 42, height: int = 16) -> None:
    rng = random.Random(seed)
    pts = [(0, y_center + height)]
    for x in range(0, WIDTH + 20, 18):
        dy = rng.randint(-height // 2, height // 2)
        pts.append((x, y_center + dy))
    pts.append((WIDTH, y_center + height))
    draw.polygon(pts, fill=color)


def draw_editorial_base_and_header(
    accent_color: Tuple[int, int, int] = (0, 165, 80)
) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    """
    Gece stadyum projektör ışıklı, 3D yırtık kağıt dokulu dergi kapağı arka planını
    ve üstteki İDDAALIYIZ TV + iddaa + +18 SORUMLU OYUN başlığını çizer.
    """
    bg = Image.new("RGB", (WIDTH, HEIGHT), (4, 18, 12))
    # Vlahovic / Trabzon posterinden stadyum üst ışık atmosferini yumuşatarak al
    ref_bg_path = ASSETS_DIR / "besiktas_vlahovic_europa_poster.jpg"
    if ref_bg_path.exists():
        try:
            ref_img = Image.open(ref_bg_path).convert("RGB").resize((WIDTH, HEIGHT))
            blurred = ref_img.filter(ImageFilter.GaussianBlur(radius=28))
            dark_overlay = Image.new("RGB", (WIDTH, HEIGHT), (3, 16, 10))
            bg = Image.blend(blurred, dark_overlay, 0.72)
            # Üst projektör ve İDDAALIYIZ TV başlık bölgesini (ilk 235px) doğrudan koru!
            top_crop = ref_img.crop((0, 0, WIDTH, 232))
            bg.paste(top_crop, (0, 0))
        except Exception:
            pass

    draw = ImageDraw.Draw(bg)
    # Alt bilgi şeridi (+18 SORUMLU OYUN)
    draw.rectangle([0, HEIGHT - 78, WIDTH, HEIGHT], fill=(6, 12, 9))
    f_disc = load_font(22, True)
    disc_txt = "+18 • SORUMLU OYUN • Sadece bilgilendirme amaçlıdır.  |  @iddaaliyiz.tv"
    tb = draw.textbbox((0, 0), disc_txt, font=f_disc)
    draw.text(((WIDTH - (tb[2] - tb[0])) // 2, HEIGHT - 52), disc_txt, font=f_disc, fill=(215, 225, 215))
    return bg, draw


def paste_crest_with_glow(
    base_img: Image.Image,
    crest: Image.Image,
    center_xy: Tuple[int, int],
    ring_color: Tuple[int, int, int] = (229, 230, 25),
    draw_ring: bool = True,
) -> None:
    cx, cy = center_xy
    w, h = crest.size
    if draw_ring:
        ring_r = max(w, h) // 2 + 22
        overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse(
            [cx - ring_r - 8, cy - ring_r - 8, cx + ring_r + 8, cy + ring_r + 8],
            fill=(8, 28, 18, 215),
            outline=(ring_color[0], ring_color[1], ring_color[2], 240),
            width=6,
        )
        base_img.paste(Image.alpha_composite(base_img.convert("RGBA"), overlay).convert("RGB"))
    base_img.paste(crest, (cx - w // 2, cy - h // 2), crest)


def build_vs_editorial_poster(match: Dict[str, Any], out_path: Path) -> Path:
    """
    Sabah 09:00 için VS temalı sanatsal dergi manşeti posteri üretir.
    """
    img, draw = draw_editorial_base_and_header()

    # Orta VS Sahnesi için yarı şeffaf stadyum atmosferi + yırtık kağıt kolaj alanı (y=245..960)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 250, WIDTH, 955], fill=(6, 26, 16, 175))
    od.polygon([(0, 255), (440, 255), (540, 955), (0, 955)], fill=(0, 150, 75, 65))
    od.polygon([(WIDTH, 255), (640, 255), (540, 955), (WIDTH, 955)], fill=(229, 230, 25, 45))
    # Ortada çapraz yıldırım / VS enerji çizgisi
    od.polygon([(565, 255), (595, 255), (515, 955), (485, 955)], fill=(229, 230, 25, 210))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw_torn_paper_edge(draw, 245, (238, 238, 232), seed=11, height=18)

    # Üst Lig & Tarih & Saat Rozeti
    lg_banner = f"{tr_upper(match['country'])} • {tr_upper(match['league_sub'])} • SAAT {match['time']}"
    f_lg = load_font(27, True)
    tb = draw.textbbox((0, 0), lg_banner, font=f_lg)
    bw = tb[2] - tb[0] + 64
    bx1 = (WIDTH - bw) // 2
    draw.rounded_rectangle([bx1, 275, bx1 + bw, 333], radius=14, fill=(6, 22, 14), outline=(229, 230, 25), width=3)
    draw.text(((WIDTH - (tb[2] - tb[0])) // 2, 286), lg_banner, font=f_lg, fill=(229, 230, 25))

    # Takım Armalarını İndir ve Yerleştir (Tam Boyutlu)
    home_crest = fetch_team_crest(match["home_id"], target_size=265)
    away_crest = fetch_team_crest(match["away_id"], target_size=265)

    paste_crest_with_glow(img, home_crest, (245, 555), ring_color=(255, 255, 255), draw_ring=True)
    paste_crest_with_glow(img, away_crest, (835, 555), ring_color=(229, 230, 25), draw_ring=True)
    draw = ImageDraw.Draw(img)

    # Ortada Dev VS Rozeti
    draw.ellipse([448, 463, 632, 647], fill=(12, 18, 14), outline=(229, 230, 25), width=7)
    f_vs = load_impact_font(92)
    vs_tb = draw.textbbox((0, 0), "VS", font=f_vs)
    draw.text(
        (540 - (vs_tb[2] - vs_tb[0]) // 2, 550 - (vs_tb[3] - vs_tb[1]) // 2 - 12),
        "VS",
        font=f_vs,
        fill=(229, 230, 25),
    )

    # Takım İsimleri Kutuları (Armaların altında)
    f_tname = load_font(34, True)
    for cx, tname, bg_col, txt_col in [
        (245, tr_upper(match["home"]), (6, 24, 15), (255, 255, 255)),
        (835, tr_upper(match["away"]), (6, 24, 15), (229, 230, 25)),
    ]:
        disp_name = tname if len(tname) <= 16 else tname[:15] + "."
        ntb = draw.textbbox((0, 0), disp_name, font=f_tname)
        nw = max(320, ntb[2] - ntb[0] + 44)
        draw.rounded_rectangle(
            [cx - nw // 2, 740, cx + nw // 2, 812],
            radius=12,
            fill=bg_col,
            outline=(229, 230, 25),
            width=3,
        )
        draw.text((cx - (ntb[2] - ntb[0]) // 2, 754), disp_name, font=f_tname, fill=txt_col)

    # Yırtık Kağıt Ana Manşet Bandı (y=850..1240)
    draw_torn_paper_edge(draw, 848, (238, 238, 232), seed=77, height=20)
    draw.rectangle([0, 858, WIDTH, 1235], fill=(8, 28, 18))
    draw.rounded_rectangle([42, 1045, WIDTH - 42, 1205], radius=16, fill=(229, 230, 25))

    if match.get("is_turkish_giant"):
        gname = tr_upper(match.get("featured_team_name", match["home"]))
        if "BEŞİKTAŞ" in gname:
            hl_line1 = "HAYDİ KARA KARTAL!"
            hl_line2 = "AVRUPA'DA ZAFER GECESİ!" if "AVRUPA" in tr_upper(match["country"]) else "SAHADA MUTLAK GÜÇ!"
        elif "GALATASARAY" in gname:
            hl_line1 = "SALDIR CİMBOM!"
            hl_line2 = "ASLAN SAHNEYE ÇIKIYOR!"
        elif "FENERBAHÇE" in gname:
            hl_line1 = "HAYDİ SARI KANARYA!"
            hl_line2 = "HEDEF MUTLAK GALİBİYET!"
        else:
            hl_line1 = f"HAYDİ {gname}!"
            hl_line2 = "DEV MAÇ BAŞLIYOR!"
    else:
        hl_line1 = "GÜNÜN DEV RANDEVUSU!"
        hl_line2 = f"{tr_upper(match['home'][:10])} - {tr_upper(match['away'][:10])}"

    f_hl1 = load_impact_font(96)
    tb1 = draw.textbbox((0, 0), hl_line1, font=f_hl1)
    while tb1[2] - tb1[0] > WIDTH - 90 and f_hl1.size > 60:
        f_hl1 = load_impact_font(f_hl1.size - 4)
        tb1 = draw.textbbox((0, 0), hl_line1, font=f_hl1)
    draw.text(((WIDTH - (tb1[2] - tb1[0])) // 2 + 4, 892 + 4), hl_line1, font=f_hl1, fill=(0, 0, 0))
    draw.text(((WIDTH - (tb1[2] - tb1[0])) // 2, 892), hl_line1, font=f_hl1, fill=(255, 255, 255))

    f_hl2 = load_impact_font(86)
    tb2 = draw.textbbox((0, 0), hl_line2, font=f_hl2)
    while tb2[2] - tb2[0] > WIDTH - 110 and f_hl2.size > 54:
        f_hl2 = load_impact_font(f_hl2.size - 4)
        tb2 = draw.textbbox((0, 0), hl_line2, font=f_hl2)
    draw.text(((WIDTH - (tb2[2] - tb2[0])) // 2, 1068), hl_line2, font=f_hl2, fill=(8, 24, 14))

    draw_torn_paper_edge(draw, 1235, (238, 238, 232), seed=99, height=18)

    # Alt Kral Oranlar 3 Sütunlu Tablo (y=1265..1825)
    draw.rectangle([0, 1248, WIDTH, HEIGHT - 78], fill=(5, 20, 13))

    sub_title = f"İDDAA KRAL ORANLAR  •  {match['date']}  •  SAAT {match['time']}"
    f_sub = load_font(28, True)
    stb = draw.textbbox((0, 0), sub_title, font=f_sub)
    draw.text(((WIDTH - (stb[2] - stb[0])) // 2, 1280), sub_title, font=f_sub, fill=(165, 245, 195))
    draw.line([(70, 1332), (WIDTH - 70, 1332)], fill=(0, 155, 75), width=2)

    cols = [
        (match["ms1"], f"MS 1 ({tr_upper(match['home'][:11])})", 195),
        (match["ms0"], "MS X (BERABERLİK)", 540),
        (match["ms2"], f"MS 2 ({tr_upper(match['away'][:11])})", 885),
    ]
    f_odd_big = load_impact_font(94)
    f_odd_lbl = load_font(26, True)
    for odd_val, lbl, cx in cols:
        otb = draw.textbbox((0, 0), odd_val, font=f_odd_big)
        draw.text((cx - (otb[2] - otb[0]) // 2, 1365), odd_val, font=f_odd_big, fill=(229, 230, 25))
        ltb = draw.textbbox((0, 0), lbl, font=f_odd_lbl)
        draw.text((cx - (ltb[2] - ltb[0]) // 2, 1490), lbl, font=f_odd_lbl, fill=(255, 255, 255))

    draw.line([(368, 1365), (368, 1535)], fill=(60, 110, 80), width=2)
    draw.line([(712, 1365), (712, 1535)], fill=(60, 110, 80), width=2)

    # Ek Oran Kutusu (2.5 Alt / 2.5 Üst) ve Motivasyon Notu
    draw.rounded_rectangle([75, 1575, WIDTH - 75, 1685], radius=18, fill=(9, 44, 24), outline=(0, 165, 80), width=3)
    extra_txt = f"2.5 GOL ALTI: {match['alt25']}     |     2.5 GOL ÜSTÜ: {match['ust25']}"
    f_ex = load_font(34, True)
    extb = draw.textbbox((0, 0), extra_txt, font=f_ex)
    draw.text(((WIDTH - (extb[2] - extb[0])) // 2, 1608), extra_txt, font=f_ex, fill=(229, 230, 25))

    cta_bottom = "Skor tahminini yorumlara yaz!  •  Kayıtlı Bayim: 304168"
    f_cta_b = load_font(28, True)
    ctb = draw.textbbox((0, 0), cta_bottom, font=f_cta_b)
    draw.text(((WIDTH - (ctb[2] - ctb[0])) // 2, 1725), cta_bottom, font=f_cta_b, fill=(255, 255, 255))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=95)
    return out_path


def build_last5_editorial_poster(
    team_id: int,
    team_name: str,
    last5: List[Dict[str, Any]],
    today_match: Dict[str, Any],
    out_path: Path,
) -> Path:
    """
    Saat 14:00 için takımın resmi armasıyla SON 5 MAÇ KARNESİ dergi manşeti posterini üretir.
    """
    img, draw = draw_editorial_base_and_header()

    # Üst Kahraman Alanı: Takım Arması + Form Özeti Damgası (y=240..660)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 244, WIDTH, 665], fill=(8, 32, 20, 185))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw_torn_paper_edge(draw, 238, (238, 238, 232), seed=21, height=16)

    # Büyük Takım Arması (Sol-Orta)
    main_crest = fetch_team_crest(team_id, target_size=245)
    paste_crest_with_glow(img, main_crest, (235, 455), ring_color=(229, 230, 25), draw_ring=True)
    draw = ImageDraw.Draw(img)

    # Sağ Taraf: Takım Başlığı ve Form İstatistiği
    wins = sum(1 for x in last5 if x["result"] == "G")
    draws = sum(1 for x in last5 if x["result"] == "B")
    losses = sum(1 for x in last5 if x["result"] == "M")
    goals_for = sum(x["home_goals"] if x["home_id"] == team_id else x["away_goals"] for x in last5)
    goals_against = sum(x["away_goals"] if x["home_id"] == team_id else x["home_goals"] for x in last5)

    f_tbig = load_impact_font(78)
    draw.text((430, 285), tr_upper(team_name), font=f_tbig, fill=(255, 255, 255))

    f_tag = load_font(30, True)
    draw.text((432, 382), "MAÇ ÖNCESİ FORM RAPORU", font=f_tag, fill=(229, 230, 25))

    # G / B / M Özet Kutuları
    stat_boxes = [
        (f"{wins} G", (0, 165, 75), 432),
        (f"{draws} B", (215, 165, 15), 612),
        (f"{losses} M", (215, 35, 35), 792),
    ]
    f_sbox = load_font(34, True)
    for stxt, scol, sx in stat_boxes:
        draw.rounded_rectangle([sx, 445, sx + 160, 518], radius=14, fill=scol, outline=(255, 255, 255), width=2)
        stb = draw.textbbox((0, 0), stxt, font=f_sbox)
        draw.text((sx + (160 - (stb[2] - stb[0])) // 2, 460), stxt, font=f_sbox, fill=(255, 255, 255))

    gf_txt = f"Atılan Gol: {goals_for}   •   Yenilen Gol: {goals_against}"
    f_gf = load_font(27, True)
    draw.text((432, 545), gf_txt, font=f_gf, fill=(185, 245, 205))

    # Yırtık Kağıt Manşet Bandı: "SON 5 MAÇ KARNESİ!" (y=660..815)
    draw_torn_paper_edge(draw, 660, (238, 238, 232), seed=55, height=16)
    draw.rectangle([0, 668, WIDTH, 812], fill=(229, 230, 25))
    hl_txt = f"{tr_upper(team_name)} SON 5 MAÇ KARNESİ!"
    f_hl = load_impact_font(76)
    htb = draw.textbbox((0, 0), hl_txt, font=f_hl)
    while htb[2] - htb[0] > WIDTH - 80 and f_hl.size > 50:
        f_hl = load_impact_font(f_hl.size - 4)
        htb = draw.textbbox((0, 0), hl_txt, font=f_hl)
    draw.text(((WIDTH - (htb[2] - htb[0])) // 2, 696), hl_txt, font=f_hl, fill=(6, 22, 14))
    draw_torn_paper_edge(draw, 812, (8, 28, 18), seed=63, height=14)

    # Son 5 Maç Satırları (y=835..1555)
    row_y = 842
    row_h = 126
    f_date = load_font(21, True)
    f_mteam = load_font(28, True)
    f_score = load_impact_font(44)
    f_res = load_font(34, True)

    for idx, m in enumerate(last5[:5]):
        ry1 = row_y + idx * (row_h + 14)
        ry2 = ry1 + row_h
        draw.rounded_rectangle(
            [45, ry1, WIDTH - 45, ry2],
            radius=18,
            fill=(10, 42, 24),
            outline=(0, 145, 70),
            width=2,
        )

        # Tarih rozeti (Sol)
        draw.rounded_rectangle([62, ry1 + 26, 158, ry2 - 26], radius=10, fill=(5, 22, 13))
        dtb = draw.textbbox((0, 0), m["date"], font=f_date)
        draw.text((62 + (96 - (dtb[2] - dtb[0])) // 2, ry1 + 48), m["date"], font=f_date, fill=(165, 245, 195))

        # Ev Sahibi Arma + İsim
        h_crest = fetch_team_crest(m["home_id"], target_size=76)
        img.paste(h_crest, (168, ry1 + (row_h - 76) // 2), h_crest)
        h_disp = m["home"][:12]
        draw.text((254, ry1 + 44), h_disp, font=f_mteam, fill=(255, 255, 255) if m["home_id"] == team_id else (205, 220, 210))

        # Skor Kutusu (Orta)
        sx1, sx2 = 475, 615
        draw.rounded_rectangle([sx1, ry1 + 20, sx2, ry2 - 20], radius=12, fill=(5, 18, 11), outline=(229, 230, 25), width=2)
        sctb = draw.textbbox((0, 0), m["score"], font=f_score)
        draw.text(
            (sx1 + (140 - (sctb[2] - sctb[0])) // 2, ry1 + 34),
            m["score"],
            font=f_score,
            fill=(229, 230, 25),
        )

        # Deplasman İsim + Arma
        a_disp = m["away"][:12]
        atb = draw.textbbox((0, 0), a_disp, font=f_mteam)
        draw.text((834 - (atb[2] - atb[0]), ry1 + 44), a_disp, font=f_mteam, fill=(255, 255, 255) if m["away_id"] == team_id else (205, 220, 210))
        a_crest = fetch_team_crest(m["away_id"], target_size=76)
        img.paste(a_crest, (846, ry1 + (row_h - 76) // 2), a_crest)

        # Sağda G / B / M Form Harfi Rozeti
        rcode = m["result"]
        rcol = (0, 175, 75) if rcode == "G" else ((220, 165, 15) if rcode == "B" else (215, 35, 35))
        draw.rounded_rectangle([940, ry1 + 22, 1018, ry2 - 22], radius=14, fill=rcol)
        rtb = draw.textbbox((0, 0), rcode, font=f_res)
        draw.text((940 + (78 - (rtb[2] - rtb[0])) // 2, ry1 + 40), rcode, font=f_res, fill=(255, 255, 255))

    # Alt Kutu: Bugünkü Maç ve Kral Oranlar (y=1565..1825)
    draw.rounded_rectangle([45, 1562, WIDTH - 45, 1818], radius=22, fill=(6, 26, 16), outline=(229, 230, 25), width=3)
    next_hdr = f"BUGÜN SAAT {today_match['time']}  •  {tr_upper(today_match['home'])} vs {tr_upper(today_match['away'])}"
    f_nhdr = load_font(30, True)
    ntb = draw.textbbox((0, 0), next_hdr, font=f_nhdr)
    draw.text(((WIDTH - (ntb[2] - ntb[0])) // 2, 1584), next_hdr, font=f_nhdr, fill=(229, 230, 25))

    odds_line = f"MS 1: {today_match['ms1']}     |     MS X: {today_match['ms0']}     |     MS 2: {today_match['ms2']}"
    f_oline = load_font(38, True)
    otb = draw.textbbox((0, 0), odds_line, font=f_oline)
    draw.text(((WIDTH - (otb[2] - otb[0])) // 2, 1655), odds_line, font=f_oline, fill=(255, 255, 255))

    sub_cta = "Sizce bu akşam seriyi nasıl sürdürür? Yorumlara yaz!  •  Bayi: 304168"
    f_scta = load_font(24, True)
    sctb = draw.textbbox((0, 0), sub_cta, font=f_scta)
    draw.text(((WIDTH - (sctb[2] - sctb[0])) // 2, 1742), sub_cta, font=f_scta, fill=(165, 245, 195))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=95)
    return out_path


def render_poster_to_reels_mp4(poster_path: Path, vo_script: str, out_mp4: Path) -> Path:
    """
    Verilen sanatsal manşet posterini (VS veya Son 5 Maç) %100 Türkçe erkek spiker sesi
    (tr-TR-AhmetNeural) ve 2 aşamalı Kayıtlı Bayim (304168) kapanışıyla MP4 Reels videosuna dönüştürür.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    vo_main_path = OUTPUT_DIR / f"vo_{out_mp4.stem}.mp3"
    vo_outro1_path = OUTPUT_DIR / "vo_outro_step1.mp3"
    vo_outro2_path = OUTPUT_DIR / "vo_outro_step2.mp3"

    asyncio.run(generate_tts(vo_script, vo_main_path))
    if STATIC_OUTRO1_MP3.exists() and STATIC_OUTRO1_MP3.stat().st_size > 1000:
        shutil.copyfile(STATIC_OUTRO1_MP3, vo_outro1_path)
    else:
        asyncio.run(generate_tts(OUTRO_VOICEOVER_STEP1, vo_outro1_path))

    if STATIC_OUTRO2_MP3.exists() and STATIC_OUTRO2_MP3.stat().st_size > 1000:
        shutil.copyfile(STATIC_OUTRO2_MP3, vo_outro2_path)
    else:
        asyncio.run(generate_tts(OUTRO_VOICEOVER_STEP2, vo_outro2_path))

    main_dur = max(8.5, get_audio_duration(vo_main_path) + 0.8)
    step1_dur = max(3.6, get_audio_duration(vo_outro1_path) + 0.45)
    step2_dur = max(2.6, get_audio_duration(vo_outro2_path) + 0.65)
    outro_dur = step1_dur + step2_dur
    total_dur = main_dur + outro_dur
    total_frames = int(math.ceil(total_dur * FPS))

    poster_base = Image.open(poster_path).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    step1_img = Image.open(OUTRO_STEP1_PATH).convert("RGB")
    step2_img = Image.open(OUTRO_STEP2_PATH).convert("RGB")

    # Kapak fotoğrafını kaydet
    thumb_path = out_mp4.with_suffix(".png")
    poster_base.save(thumb_path)

    step1_ms = int(main_dur * 1000)
    step2_ms = int((main_dur + step1_dur) * 1000)

    filter_complex = (
        f"aevalsrc='0.14*sin(2*PI*55*t)*exp(-3.5*mod(t,0.5))+0.05*sin(2*PI*220*t)*exp(-6*mod(t,0.25))'"
        f":s=44100:d={total_dur:.2f}[bgm];"
        f"[1:a]aresample=44100,volume=1.95[vo_main];"
        f"[2:a]aresample=44100,volume=1.95,adelay={step1_ms}|{step1_ms}[vo_s1];"
        f"[3:a]aresample=44100,volume=1.95,adelay={step2_ms}|{step2_ms}[vo_s2];"
        f"[bgm][vo_main][vo_s1][vo_s2]amix=inputs=4:duration=first:dropout_transition=0,"
        f"alimiter=limit=0.95[aout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", str(vo_main_path),
        "-i", str(vo_outro1_path),
        "-i", str(vo_outro2_path),
        "-filter_complex", filter_complex,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-t", f"{total_dur:.2f}",
        str(out_mp4),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    for f_idx in range(total_frames):
        t = f_idx / FPS
        if t < main_dur:
            zoom = 1.0 + 0.03 * math.sin((t / main_dur) * math.pi)
            zw = int(WIDTH * zoom)
            zh = int(HEIGHT * zoom)
            resized = poster_base.resize((zw, zh), Image.Resampling.BILINEAR)
            ox = (zw - WIDTH) // 2
            oy = (zh - HEIGHT) // 2
            frame = resized.crop((ox, oy, ox + WIDTH, oy + HEIGHT))
            draw = ImageDraw.Draw(frame)
            bar_w = int((WIDTH - 90) * min(1.0, t / max(0.1, total_dur)))
            if bar_w > 4:
                draw.rounded_rectangle([45, HEIGHT - 84, 45 + bar_w, HEIGHT - 78], radius=3, fill=(229, 230, 25))
        else:
            frame = Image.new("RGB", (WIDTH, HEIGHT), (4, 24, 12))
            draw = ImageDraw.Draw(frame)
            outro_elapsed = t - main_dur
            render_outro_scene(frame, draw, step1_img, step2_img, outro_elapsed, step1_dur, step2_dur)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    stderr_bytes = proc.stderr.read() if proc.stderr else b""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası:\n{stderr_bytes.decode('utf-8', errors='ignore')}")

    return out_mp4


def run_vs_mode(target_date: datetime.date, do_upload: bool, interval_sec: int = 900) -> List[Path]:
    matches = parse_today_football_matches(target_date)
    selected = select_morning_vs_matches(matches)
    if not selected:
        print("[UYARI] Bugün için uygun VS maçı bulunamadı.")
        return []

    generated_videos: List[Path] = []
    for idx, m in enumerate(selected):
        slug = f"{m['home_id']}_{m['away_id']}"
        poster_path = ASSETS_DIR / f"auto_vs_poster_{slug}.jpg"
        video_path = OUTPUT_DIR / f"reels_vs_manset_{idx+1}.mp4"

        print(f"[{idx+1}/{len(selected)}] VS Manşet Posteri hazırlanıyor: {m['home']} vs {m['away']} ({m['league']})...")
        build_vs_editorial_poster(m, poster_path)

        vo_script = (
            f"Günün dev karşılaşması! {m['country']} {m['league_sub']} heyecanında bugün saat {m['time']}'de "
            f"{m['home']} ile {m['away']} karşı karşıya geliyor! "
            f"İddaa Kral Oranlarda Maç Sonu 1 {m['ms1']}, Maç Sonu Beraberlik {m['ms0']}, "
            f"Maç Sonu 2 ise {m['ms2']}! "
            f"Sizce bu dev maçı kim kazanır? Skor tahmininizi yorumlara bekliyoruz!"
        )
        render_poster_to_reels_mp4(poster_path, vo_script, video_path)
        generated_videos.append(video_path)

        caption = (
            f"🔥 GÜNÜN DEV MAÇI: {m['home'].upper()} ⚡ VS ⚡ {m['away'].upper()}! ⚽🏆\n\n"
            f"📅 {m['league']} | Saat: {m['time']}\n\n"
            f"📊 İddaa Kral Oranlar:\n"
            f"🔹 MS 1 ({m['home']}): {m['ms1']}\n"
            f"🔹 MS X (Beraberlik): {m['ms0']}\n"
            f"🔹 MS 2 ({m['away']}): {m['ms2']}\n"
            f"🔹 2.5 Alt: {m['alt25']} | 2.5 Üst: {m['ust25']}\n\n"
            f"💬 Sizce bu karşılaşmayı kim kazanır? Skor tahminlerinizi yorumlara yazın! 👇\n\n"
            f"📲 İddaa Resmi Uygulaması üzerinden 'Hesabım -> Kayıtlı Bayim' adımlarını takip ederek 304168 numaralı bayimizi eklemeyi unutmayın! 🤝\n\n"
            f"⚠️ +18 | SORUMLU OYUN\n"
            f"#iddaa #iddaaliyiztv #futbol #kraloran #maçtahmini #reels"
        )

        if do_upload:
            if idx > 0 and interval_sec > 0:
                print(f"[BEKLEME] Sıradaki VS Reels paylaşımı için {interval_sec // 60} dakika ({interval_sec} sn) bekleniyor...")
                time.sleep(interval_sec)
            upload_reel(video_path, caption)

    return generated_videos


def run_last5_mode(target_date: datetime.date, do_upload: bool, interval_sec: int = 900) -> List[Path]:
    matches = parse_today_football_matches(target_date)
    if not matches:
        print("[UYARI] Bugün için maç bulunamadı.")
        return []

    # Önce bugün maçı olan Büyük Türk Takımlarını kontrol et
    target_entries: List[Tuple[int, str, Dict[str, Any]]] = []
    seen_tids = set()
    for m in matches:
        for gid, gname in TURKISH_GIANTS.items():
            if m["home_id"] == gid or m["away_id"] == gid or m["home"].lower() == gname.lower() or m["away"].lower() == gname.lower():
                if gid not in seen_tids:
                    seen_tids.add(gid)
                    target_entries.append((gid, gname, m))

    # O gün Büyük Türk Takımının maçı yoksa günün 1 numaralı dev maçının ev sahibi takımını al
    if not target_entries:
        top_m = matches[0]
        target_entries.append((top_m["home_id"], top_m["home"], top_m))

    generated_videos: List[Path] = []
    for idx, (tid, tname, m) in enumerate(target_entries):
        print(f"[{idx+1}/{len(target_entries)}] {tname} (ID={tid}) için Son 5 Maç Karnesi çekiliyor...")
        last5 = fetch_team_last_5_matches(tid, tname, target_date)
        poster_path = ASSETS_DIR / f"auto_last5_poster_{tid}.jpg"
        video_path = OUTPUT_DIR / f"reels_last5_form_{idx+1}.mp4"

        build_last5_editorial_poster(tid, tname, last5, m, poster_path)

        wins = sum(1 for x in last5 if x["result"] == "G")
        draws = sum(1 for x in last5 if x["result"] == "B")
        losses = sum(1 for x in last5 if x["result"] == "M")

        score_phrases = []
        for x in last5[:3]:
            score_phrases.append(f"{x['home']} {x['home_goals']}, {x['away']} {x['away_goals']}")
        scores_spoken = "; ".join(score_phrases)

        vo_script = (
            f"Maç öncesi form raporu! {tname} son 5 resmi maçında {wins} galibiyet, "
            f"{draws} beraberlik ve {losses} mağlubiyet aldı! "
            f"Son karşılaşmalarında {scores_spoken} sonuçları kaydedildi. "
            f"{tname} bugün saat {m['time']}'de {m['home']} {m['away']} maçında sahaya çıkıyor! "
            f"Maç Sonu 1 oranı {m['ms1']}, Beraberlik {m['ms0']}, Maç Sonu 2 ise {m['ms2']}! "
            f"Sizce {tname} bu akşam nasıl bir skor alır? Yorumlara yazın!"
        )
        render_poster_to_reels_mp4(poster_path, vo_script, video_path)
        generated_videos.append(video_path)

        last5_lines = "\n".join(
            [f"{'🟢' if x['result']=='G' else ('🟡' if x['result']=='B' else '🔴')} {x['date']} | {x['home']} {x['score']} {x['away']} ({x['result']})" for x in last5]
        )
        caption = (
            f"📊 {tname.upper()} SON 5 MAÇ KARNESİ! 🔥⚽\n\n"
            f"Bugün saat {m['time']}'de oynanacak {m['home']} - {m['away']} karşılaşması öncesi {tname} son 5 maçında {wins} Galibiyet, {draws} Beraberlik ve {losses} Mağlubiyet aldı:\n\n"
            f"{last5_lines}\n\n"
            f"📈 Bugünkü Maç İddaa Kral Oranları:\n"
            f"🔹 MS 1 ({m['home']}): {m['ms1']} | MS X: {m['ms0']} | MS 2 ({m['away']}): {m['ms2']}\n\n"
            f"💬 Sizce {tname} bu akşam seriyi nasıl sürdürür? Yorumlara tahminlerinizi bekliyoruz! 👇\n\n"
            f"📲 İddaa Resmi Uygulaması üzerinden 'Hesabım -> Kayıtlı Bayim' adımlarını takip ederek 304168 numaralı bayimizi eklemeyi unutmayın! 🤝\n\n"
            f"⚠️ +18 | SORUMLU OYUN\n"
            f"#iddaa #iddaaliyiztv #{tname.lower().replace(' ', '')} #formdurumu #son5maç #reels"
        )

        if do_upload:
            if idx > 0 and interval_sec > 0:
                print(f"[BEKLEME] Sıradaki Son 5 Maç Reels paylaşımı için {interval_sec // 60} dakika ({interval_sec} sn) bekleniyor...")
                time.sleep(interval_sec)
            upload_reel(video_path, caption)

    return generated_videos


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["vs", "last5"], required=True)
    parser.add_argument("--date", default="", help="GG/AA/YYYY formatında tarih (boşsa bugün TSİ)")
    parser.add_argument("--upload", action="store_true", help="Üretilen videoları Instagram'a yükle")
    parser.add_argument("--interval", type=int, default=900, help="Çoklu paylaşımlar arası bekleme süresi (saniye, varsayılan 900=15dk)")
    args = parser.parse_args()

    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    if args.date:
        target_date = datetime.datetime.strptime(args.date, "%d/%m/%Y").date()
    else:
        target_date = datetime.datetime.now(tz_tr).date()

    if args.mode == "vs":
        run_vs_mode(target_date, do_upload=args.upload, interval_sec=args.interval)
    else:
        run_last5_mode(target_date, do_upload=args.upload, interval_sec=args.interval)


if __name__ == "__main__":
    main()
