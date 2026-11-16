"""
30-FPS Broadcast Graph-Motion Video Engine (graph_motion_engine.py)
- Statik poster zoom yerine gerçek spor televizyonu (Sky Sports / ESPN / Tifo) tarzı
  hareketli grafikler (Motion Graphics / Graph Motion) üretir:
  * Kinetik diyagonal ışık çizgileri ve canlı ses ekolayzır (waveform) barları
  * Çerçeve içi bağımsız Ken Burns kamera hareketi + parlayan altın çerçeve
  * Whip-in (hızlı kayarak giren) manşet kartları ve sırayla açılan zaman tüneli (timeline) bilgi kartları
  * Maç önü / maç sonu ekranlarında 0'dan büyüyen canlı karşılaştırma grafik barları (Tug-of-War Graph Bars),
    sayarak artan istatistik rakamları ve tek tek patlayarak açılan G/B/M form rozetleri
  * Alt bantta 30 FPS akıcı kayan spor bülteni şeridi (Live News Ticker)
  * Sahneler arası hızlı whip-pan (yatay kamera savurma) geçişi
"""

import asyncio
import datetime
import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from auto_manset_reels import ASSETS_DIR, FPS, HEIGHT, OUTPUT_DIR, WIDTH, load_impact_font, tr_upper
from motion_reels import ease_out_back, ease_out_cubic, generate_tts, get_audio_duration, load_font

BG_TOP = (7, 13, 28)
BG_BOT = (3, 6, 14)
CARD_NAVY = (13, 23, 45)
CARD_DARK = (9, 17, 34)
ACCENT_RED = (230, 34, 56)
ACCENT_GOLD = (250, 204, 21)
ACCENT_CYAN = (56, 189, 248)
ACCENT_GREEN = (34, 197, 94)
ACCENT_AMBER = (245, 158, 11)
TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (172, 189, 214)

SUBSCRIBE_VOICEOVER = "Güncel futbol haberleri ve analizler için kanala abone olup videoyu beğenmeyi unutmayın!"


def _clamp01(v: float) -> float:
    return 0.0 if v <= 0.0 else (1.0 if v >= 1.0 else v)


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: Any, max_w: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        tb = draw.textbbox((0, 0), cand, font=font)
        if tb[2] - tb[0] <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _make_base_gradient(hero_photo: Optional[Image.Image] = None) -> Image.Image:
    bg = Image.new("RGB", (WIDTH, HEIGHT), BG_BOT)
    d = ImageDraw.Draw(bg)
    for y in range(HEIGHT):
        r_ratio = y / HEIGHT
        r = int(BG_TOP[0] * (1 - r_ratio) + BG_BOT[0] * r_ratio)
        g = int(BG_TOP[1] * (1 - r_ratio) + BG_BOT[1] * r_ratio)
        b = int(BG_TOP[2] * (1 - r_ratio) + BG_BOT[2] * r_ratio)
        d.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    if hero_photo is not None:
        blurred = hero_photo.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(radius=36))
        bg = Image.blend(bg, blurred, 0.18)
    return bg


def _make_ticker_strip(ticker_text: str, accent: Tuple[int, int, int]) -> Image.Image:
    f_tick = load_font(24, True)
    unit = f"   >>>   {tr_upper(ticker_text)}   •   CANLI SPOR GRAFİK EKRANI   •   ABONE OLMAYI UNUTMAYIN   "
    dummy = Image.new("RGB", (10, 10))
    dd = ImageDraw.Draw(dummy)
    tb = dd.textbbox((0, 0), unit, font=f_tick)
    uw = max(600, tb[2] - tb[0])
    repeats = (WIDTH * 3 // uw) + 3
    full_w = uw * repeats
    strip = Image.new("RGB", (full_w, 72), (5, 10, 22))
    sd = ImageDraw.Draw(strip)
    sd.rectangle([0, 0, full_w, 4], fill=accent)
    for i in range(repeats):
        sd.text((i * uw, 21), unit, font=f_tick, fill=TEXT_WHITE)
    return strip


def _make_card_sprite(w: int, h: int, bg_col: Tuple[int, int, int], border_col: Tuple[int, int, int], border_w: int = 3, radius: int = 22) -> Image.Image:
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=(*bg_col, 242), outline=(*border_col, 255), width=border_w)
    return im


def _prepare_story_sprites(scene: Dict[str, Any]) -> Dict[str, Any]:
    accent = scene.get("accent", ACCENT_RED)
    photo: Optional[Image.Image] = scene.get("photo")
    base_bg = _make_base_gradient(photo)

    # Fotoğrafı çerçeve içi Ken Burns için önceden ölçekle (984 x 555 hedef kutu)
    pw_box, ph_box = WIDTH - 96, 545
    pre_photo = None
    if photo is not None:
        pw, ph = photo.size
        scale = max((pw_box * 1.14) / max(1, pw), (ph_box * 1.14) / max(1, ph))
        nw, nh = int(pw * scale), int(ph * scale)
        pre_photo = ImageEnhance.Contrast(photo.resize((nw, nh), Image.Resampling.LANCZOS)).enhance(1.08)

    photo_mask = Image.new("L", (pw_box, ph_box), 0)
    ImageDraw.Draw(photo_mask).rounded_rectangle([0, 0, pw_box - 1, ph_box - 1], radius=26, fill=255)

    # Manşet Kartı Sprite (984 x 250)
    hl_w, hl_h = WIDTH - 96, 252
    hl_sprite = _make_card_sprite(hl_w, hl_h, CARD_NAVY, ACCENT_GOLD, border_w=3, radius=24)
    hd = ImageDraw.Draw(hl_sprite)
    badge = scene.get("badge", "SPOR GÜNDEMİ")
    f_badge = load_font(22, True)
    btb = hd.textbbox((0, 0), badge, font=f_badge)
    bw = btb[2] - btb[0] + 38
    hd.rounded_rectangle([26, 20, 26 + bw, 64], radius=10, fill=(*accent, 255))
    hd.text((45, 28), badge, font=f_badge, fill=TEXT_WHITE)

    hl_text = tr_upper(scene.get("headline", ""))
    f_hl = load_impact_font(46 if len(hl_text) <= 68 else 39)
    hl_lines = _wrap_lines(hd, hl_text, f_hl, hl_w - 56)[:3]
    cy = 80
    for ln in hl_lines:
        hd.text((28, cy), ln, font=f_hl, fill=ACCENT_GOLD)
        tb = hd.textbbox((0, 0), ln, font=f_hl)
        cy += (tb[3] - tb[1]) + 8

    # Detay Kartları Sprites (2 veya 3 adet, sırayla açılır)
    bullets: List[str] = scene.get("bullets", [])[:3]
    n_b = max(1, len(bullets))
    avail_h = 760
    gap = 18
    card_h = min(260, (avail_h - gap * (n_b - 1)) // n_b)
    bullet_sprites: List[Image.Image] = []
    f_b = load_font(27 if n_b == 3 else 29, True)
    f_num = load_impact_font(34)

    for idx, btxt in enumerate(bullets):
        bs = _make_card_sprite(hl_w, card_h, CARD_DARK, ACCENT_CYAN, border_w=2, radius=20)
        bd = ImageDraw.Draw(bs)
        # Sol numara rozeti
        bd.rounded_rectangle([22, 24, 78, 80], radius=14, fill=(*accent, 255))
        num_s = f"0{idx + 1}"
        ntb = bd.textbbox((0, 0), num_s, font=f_num)
        bd.text((50 - (ntb[2] - ntb[0]) // 2, 31), num_s, font=f_num, fill=TEXT_WHITE)

        max_lines = 4 if n_b <= 2 else 3
        blines = _wrap_lines(bd, btxt, f_b, hl_w - 124)[:max_lines]
        by = 24
        for ln in blines:
            bd.text((98, by), ln, font=f_b, fill=TEXT_WHITE)
            tb = bd.textbbox((0, 0), ln, font=f_b)
            by += (tb[3] - tb[1]) + 8
        bullet_sprites.append(bs)

    ticker = _make_ticker_strip(scene.get("ticker", scene.get("headline", "FUTBOL GÜNDEMİ")), accent)
    return {
        "kind": "story",
        "masthead": scene.get("masthead", "FUTBOL GÜNDEMİ"),
        "accent": accent,
        "base_bg": base_bg,
        "pre_photo": pre_photo,
        "photo_mask": photo_mask,
        "pw_box": pw_box,
        "ph_box": ph_box,
        "hl_sprite": hl_sprite,
        "bullet_sprites": bullet_sprites,
        "card_h": card_h,
        "gap": gap,
        "ticker": ticker,
    }


def _prepare_stats_sprites(scene: Dict[str, Any]) -> Dict[str, Any]:
    accent = scene.get("accent", ACCENT_GOLD)
    base_bg = _make_base_gradient(None)
    ticker = _make_ticker_strip(scene.get("ticker", "MAÇ ANALİZİ VE FORM GRAFİĞİ"), accent)
    return {
        "kind": "stats",
        "masthead": scene.get("masthead", "MAÇ ANALİZİ"),
        "accent": accent,
        "base_bg": base_bg,
        "ticker": ticker,
        "data": scene,
    }


def _draw_common_hud(frame: Image.Image, draw: ImageDraw.ImageDraw, masthead: str, accent: Tuple[int, int, int], t_global: float, progress_ratio: float, ticker: Image.Image) -> None:
    # Arka plan diyagonal hareketli ışık çizgileri
    shift = int(t_global * 90) % 260
    for k in range(-2, 9):
        x0 = k * 260 + shift
        draw.line([(x0, 148), (x0 - 220, 520)], fill=(18, 34, 66), width=2)

    # Üst yayın barı
    draw.rectangle([0, 0, WIDTH, 142], fill=(5, 10, 22))
    draw.rectangle([0, 139, WIDTH, 144], fill=accent)

    # Sol kategori rozeti + canlı kırmızı nokta
    f_cat = load_font(25, True)
    ctb = draw.textbbox((0, 0), masthead, font=f_cat)
    cw = ctb[2] - ctb[0] + 66
    draw.rounded_rectangle([44, 42, 44 + cw, 100], radius=12, fill=accent)
    if int(t_global * 3.2) % 2 == 0:
        draw.ellipse([60, 63, 76, 79], fill=TEXT_WHITE)
    else:
        draw.ellipse([62, 65, 74, 77], fill=(255, 210, 210))
    draw.text((88, 55), masthead, font=f_cat, fill=TEXT_WHITE)

    # Sağ canlı ses ekolayzır (10 bar) + tarih
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    now_str = datetime.datetime.now(tz_tr).strftime("%d.%m.%Y")
    f_dt = load_font(24, True)
    dtb = draw.textbbox((0, 0), now_str, font=f_dt)
    date_x = WIDTH - 48 - (dtb[2] - dtb[0])
    draw.text((date_x, 56), now_str, font=f_dt, fill=ACCENT_GOLD)

    eq_right = date_x - 24
    for bi in range(8):
        amp = 0.35 + 0.65 * abs(math.sin(t_global * (7.5 + bi * 1.3) + bi * 0.9))
        bh = int(10 + 30 * amp)
        bx = eq_right - (8 - bi) * 11
        by1 = 71 - bh // 2
        by2 = 71 + bh // 2
        draw.rounded_rectangle([bx, by1, bx + 6, by2], radius=2, fill=ACCENT_CYAN if bi % 2 == 0 else ACCENT_GOLD)

    # Kayan alt haber şeridi (Live Ticker)
    tw = ticker.size[0]
    tx = int(t_global * 165) % (tw - WIDTH)
    crop_tick = ticker.crop((tx, 0, tx + WIDTH, 72))
    frame.paste(crop_tick, (0, HEIGHT - 72))

    # Altın ilerleme barı
    bar_w = int(WIDTH * _clamp01(progress_ratio))
    if bar_w > 2:
        draw.rectangle([0, HEIGHT - 76, bar_w, HEIGHT - 71], fill=ACCENT_GOLD)


def _render_story_frame(prep: Dict[str, Any], local_t: float, seg_dur: float, global_t: float, total_dur: float) -> Image.Image:
    frame = prep["base_bg"].copy()
    draw = ImageDraw.Draw(frame)
    _draw_common_hud(frame, draw, prep["masthead"], prep["accent"], global_t, global_t / max(0.1, total_dur), prep["ticker"])

    # 1) Fotoğraf Pencereli Ken Burns + Pop-in (0.0 - 0.45s)
    pw_box, ph_box = prep["pw_box"], prep["ph_box"]
    pre_photo: Optional[Image.Image] = prep["pre_photo"]
    if pre_photo is not None:
        p_in = ease_out_cubic(_clamp01(local_t / 0.42))
        pan_ratio = _clamp01(local_t / max(1.0, seg_dur))
        nw, nh = pre_photo.size
        max_ox = max(0, nw - pw_box)
        max_oy = max(0, nh - ph_box)
        ox = int(max_ox * (0.2 + 0.6 * pan_ratio))
        oy = int(max_oy * (0.12 + 0.25 * math.sin(pan_ratio * math.pi)))
        cropped = pre_photo.crop((ox, oy, ox + pw_box, oy + ph_box))

        y_photo = int(168 + (1.0 - p_in) * -45)
        frame.paste(cropped, (48, y_photo), prep["photo_mask"])
        draw.rounded_rectangle([48, y_photo, 48 + pw_box, y_photo + ph_box], radius=26, outline=ACCENT_GOLD, width=4)

        # Parlayan hareketli köşe vurgu çizgisi
        sweep_w = 180
        sx = 68 + int((pw_box - 40 - sweep_w) * (0.5 + 0.5 * math.sin(global_t * 2.6)))
        draw.rounded_rectangle([sx, y_photo - 2, sx + sweep_w, y_photo + 4], radius=3, fill=TEXT_WHITE)

    # 2) Whip-in Manşet Kartı (0.18s - 0.62s)
    hl_prog = ease_out_cubic(_clamp01((local_t - 0.16) / 0.45))
    if hl_prog > 0.01:
        hl_x = int(48 - (1.0 - hl_prog) * (WIDTH + 60))
        frame.paste(prep["hl_sprite"], (hl_x, 735), prep["hl_sprite"])

    # 3) Sırayla Açılan Timeline Bilgi Kartları (Staggered Cascade)
    b_sprites: List[Image.Image] = prep["bullet_sprites"]
    card_h = prep["card_h"]
    gap = prep["gap"]
    n_b = len(b_sprites)

    # Zamanlama: ilk kart 0.65s'de, sonraki kartlar konuşma ilerledikçe açılır
    step_delay = min(2.4, max(1.1, (seg_dur * 0.55) / max(1, n_b)))
    base_y = 1012

    # Sol dikey zaman çizgisi büyümesi
    line_prog = _clamp01((local_t - 0.65) / max(0.5, step_delay * n_b))
    if line_prog > 0.02 and n_b > 1:
        ly2 = int(base_y + 40 + (n_b * (card_h + gap) - gap - 80) * line_prog)
        draw.line([(30, base_y + 40), (30, ly2)], fill=ACCENT_GOLD, width=4)

    for idx, bs in enumerate(b_sprites):
        appear_t = 0.65 + idx * step_delay
        c_prog = ease_out_back(_clamp01((local_t - appear_t) / 0.48))
        if c_prog <= 0.01:
            continue
        cy = base_y + idx * (card_h + gap)
        slide_y = int(cy + (1.0 - min(1.0, c_prog)) * 70)
        slide_x = int(48 + (1.0 - min(1.0, c_prog)) * 90)
        frame.paste(bs, (slide_x, slide_y), bs)

        # Aktif okunan kartta parlayan sol işaretçi
        next_t = appear_t + step_delay
        if appear_t <= local_t < (next_t if idx < n_b - 1 else seg_dur):
            pulse_r = 7 + int(3 * abs(math.sin(global_t * 7.0)))
            draw.ellipse([26 - pulse_r, slide_y + 52 - pulse_r, 26 + pulse_r, slide_y + 52 + pulse_r], fill=ACCENT_GOLD)

    return frame


def _render_stats_frame(prep: Dict[str, Any], local_t: float, seg_dur: float, global_t: float, total_dur: float) -> Image.Image:
    frame = prep["base_bg"].copy()
    draw = ImageDraw.Draw(frame)
    data = prep["data"]
    accent = prep["accent"]
    _draw_common_hud(frame, draw, prep["masthead"], accent, global_t, global_t / max(0.1, total_dur), prep["ticker"])

    # Üst Lig Başlığı
    lg_txt = data.get("sub_header", "")
    f_lg = load_font(26, True)
    ltb = draw.textbbox((0, 0), lg_txt, font=f_lg)
    draw.text(((WIDTH - (ltb[2] - ltb[0])) // 2, 166), lg_txt, font=f_lg, fill=ACCENT_CYAN)

    # Üst Karşılaşma Sahnesi (Takım Armaları Kinetik Giriş + Yüzen Hareket)
    draw.rounded_rectangle([48, 214, WIDTH - 48, 650], radius=26, fill=CARD_NAVY, outline=ACCENT_GOLD, width=3)

    crest_prog = ease_out_back(_clamp01(local_t / 0.55))
    bob = int(5 * math.sin(global_t * 3.2))
    h_crest: Image.Image = data["home_crest"]
    a_crest: Image.Image = data["away_crest"]
    hx = int(-180 + (225 + 180) * crest_prog) - h_crest.size[0] // 2
    ax = int(WIDTH + 180 - (WIDTH + 180 - 855) * crest_prog) - a_crest.size[0] // 2
    frame.paste(h_crest, (hx, 385 - h_crest.size[1] // 2 + bob), h_crest)
    frame.paste(a_crest, (ax, 385 - a_crest.size[1] // 2 - bob), a_crest)
    draw = ImageDraw.Draw(frame)

    f_tn = load_font(30, True)
    for cx, nm in [(225, tr_upper(data["home_name"])[:15]), (855, tr_upper(data["away_name"])[:15])]:
        ntb = draw.textbbox((0, 0), nm, font=f_tn)
        draw.text((cx - (ntb[2] - ntb[0]) // 2, 520), nm, font=f_tn, fill=TEXT_WHITE)

    # Orta VS veya Maç Skoru Slam Animasyonu
    center_label = data.get("center_badge", "VS")
    slam = ease_out_back(_clamp01((local_t - 0.22) / 0.42))
    if slam > 0.05:
        if center_label == "VS":
            r_vs = int(76 * slam)
            pulse_ring = int(84 + 10 * abs(math.sin(global_t * 4.5)))
            draw.ellipse([540 - pulse_ring, 388 - pulse_ring, 540 + pulse_ring, 388 + pulse_ring], outline=ACCENT_GOLD, width=2)
            draw.ellipse([540 - r_vs, 388 - r_vs, 540 + r_vs, 388 + r_vs], fill=ACCENT_RED, outline=ACCENT_GOLD, width=4)
            f_vs = load_impact_font(70)
            vtb = draw.textbbox((0, 0), "VS", font=f_vs)
            draw.text((540 - (vtb[2] - vtb[0]) // 2, 346), "VS", font=f_vs, fill=TEXT_WHITE)
        else:
            bw_s = int(155 * slam)
            bh_s = int(72 * slam)
            draw.rounded_rectangle([540 - bw_s, 388 - bh_s, 540 + bw_s, 388 + bh_s], radius=22, fill=(6, 12, 24), outline=ACCENT_GOLD, width=4)
            f_sc = load_impact_font(86)
            sctb = draw.textbbox((0, 0), center_label, font=f_sc)
            draw.text((540 - (sctb[2] - sctb[0]) // 2, 336), center_label, font=f_sc, fill=ACCENT_GOLD)

    # Son 5 Maç Form Rozetleri (Tek tek patlayarak açılır: G=Yeşil, B=Sarı, M=Kırmızı)
    h_forms: List[str] = data.get("home_forms", [])[:5]
    a_forms: List[str] = data.get("away_forms", [])[:5]
    if h_forms or a_forms:
        f_pill = load_font(22, True)
        for side_idx, forms in enumerate([h_forms, a_forms]):
            start_x = 105 if side_idx == 0 else 735
            for fi, res_ch in enumerate(forms):
                pop_p = ease_out_back(_clamp01((local_t - (0.65 + fi * 0.13)) / 0.3))
                if pop_p <= 0.05:
                    continue
                col = ACCENT_GREEN if res_ch == "G" else (ACCENT_AMBER if res_ch == "B" else ACCENT_RED)
                px = start_x + fi * 50
                py = 582
                pr = int(20 * min(1.08, pop_p))
                draw.rounded_rectangle([px - pr, py - pr, px + pr, py + pr], radius=8, fill=col)
                ctb = draw.textbbox((0, 0), res_ch, font=f_pill)
                draw.text((px - (ctb[2] - ctb[0]) // 2, py - 13), res_ch, font=f_pill, fill=TEXT_WHITE)
    elif data.get("verdict"):
        v_txt = data["verdict"]
        f_v = load_font(26, True)
        vtb = draw.textbbox((0, 0), v_txt, font=f_v)
        draw.text(((WIDTH - (vtb[2] - vtb[0])) // 2, 584), v_txt, font=f_v, fill=ACCENT_CYAN)

    # Alt Bölüm: Ya Canlı Büyüyen Graph Barlar (Pre-Match) ya da Kinetik Skor Satırları (Post-Match)
    bars: List[Dict[str, Any]] = data.get("bars", [])
    other_matches: List[Dict[str, Any]] = data.get("other_matches", [])

    if bars:
        for idx, binfo in enumerate(bars[:4]):
            appear = 1.05 + idx * 0.55
            row_p = ease_out_cubic(_clamp01((local_t - appear) / 0.85))
            if row_p <= 0.01:
                continue

            ry1 = int(682 + idx * 268 + (1.0 - row_p) * 45)
            ry2 = ry1 + 240
            draw.rounded_rectangle([48, ry1, WIDTH - 48, ry2], radius=22, fill=CARD_DARK, outline=(48, 82, 136), width=2)

            lbl = binfo["label"]
            f_lbl = load_font(25, True)
            ltb = draw.textbbox((0, 0), lbl, font=f_lbl)
            draw.text(((WIDTH - (ltb[2] - ltb[0])) // 2, ry1 + 20), lbl, font=f_lbl, fill=ACCENT_GOLD)

            hv = float(binfo["home_val"])
            av = float(binfo["away_val"])
            suffix = binfo.get("suffix", "")
            tot = max(1.0, hv + av)
            h_share = hv / tot
            a_share = av / tot
            # En az %15 görsel bar genişliği
            h_ratio = 0.15 + 0.70 * h_share
            a_ratio = 1.0 - h_ratio

            # Canlı sayarak artan rakamlar
            cur_hv = int(round(hv * row_p))
            cur_av = int(round(av * row_p))
            h_txt = f"{cur_hv}{suffix}"
            a_txt = f"{cur_av}{suffix}"

            f_num = load_impact_font(52)
            htb = draw.textbbox((0, 0), h_txt, font=f_num)
            atb = draw.textbbox((0, 0), a_txt, font=f_num)
            draw.text((86, ry1 + 64), h_txt, font=f_num, fill=ACCENT_GOLD)
            draw.text((WIDTH - 86 - (atb[2] - atb[0]), ry1 + 64), a_txt, font=f_num, fill=ACCENT_CYAN)

            # Tug-of-War İkili Grafik Barı (Ortadan veya iki uçtan büyüyen bar)
            track_x1, track_x2 = 84, WIDTH - 84
            track_w = track_x2 - track_x1
            bar_y1, bar_y2 = ry1 + 148, ry1 + 194
            draw.rounded_rectangle([track_x1, bar_y1, track_x2, bar_y2], radius=14, fill=(18, 30, 56))

            hw_px = int((track_w - 8) * h_ratio * row_p)
            aw_px = int((track_w - 8) * a_ratio * row_p)
            if hw_px > 12:
                draw.rounded_rectangle([track_x1, bar_y1, track_x1 + hw_px, bar_y2], radius=14, fill=ACCENT_GOLD)
            if aw_px > 12:
                draw.rounded_rectangle([track_x2 - aw_px, bar_y1, track_x2, bar_y2], radius=14, fill=ACCENT_CYAN)

    elif other_matches:
        f_sec = load_font(26, True)
        draw.text((56, 682), "GÜNÜN DİĞER TAMAMLANAN KARŞILAŞMALARI", font=f_sec, fill=ACCENT_GOLD)
        for idx, om in enumerate(other_matches[:4]):
            appear = 0.95 + idx * 0.48
            rp = ease_out_back(_clamp01((local_t - appear) / 0.48))
            if rp <= 0.02:
                continue
            sx = int(48 + (1.0 - min(1.0, rp)) * (WIDTH))
            oy1 = 735 + idx * 245
            oy2 = oy1 + 216
            draw.rounded_rectangle([sx, oy1, sx + WIDTH - 96, oy2], radius=20, fill=CARD_DARK, outline=(48, 82, 136), width=2)

            hc: Image.Image = om["home_crest"]
            ac: Image.Image = om["away_crest"]
            frame.paste(hc, (sx + 28, oy1 + 42), hc)
            frame.paste(ac, (sx + WIDTH - 96 - 28 - ac.size[0], oy1 + 42), ac)
            draw = ImageDraw.Draw(frame)

            f_m = load_font(30, True)
            draw.text((sx + 128, oy1 + 64), om["home"][:14], font=f_m, fill=TEXT_WHITE)
            atb = draw.textbbox((0, 0), om["away"][:14], font=f_m)
            draw.text((sx + WIDTH - 96 - 128 - (atb[2] - atb[0]), oy1 + 64), om["away"][:14], font=f_m, fill=TEXT_WHITE)

            draw.rounded_rectangle([sx + 412, oy1 + 42, sx + 572, oy1 + 132], radius=14, fill=CARD_NAVY, outline=ACCENT_GOLD, width=2)
            f_osc = load_impact_font(48)
            ostb = draw.textbbox((0, 0), om["score"], font=f_osc)
            draw.text((sx + 492 - (ostb[2] - ostb[0]) // 2, oy1 + 56), om["score"], font=f_osc, fill=ACCENT_GOLD)

            # Alt gol oranı mini grafik barı
            hg, ag = om["hg"], om["ag"]
            gtot = max(1, hg + ag)
            h_frac = (hg / gtot) if (hg + ag) > 0 else 0.5
            bx1, bx2 = sx + 128, sx + WIDTH - 96 - 128
            bw_tot = bx2 - bx1
            split_x = bx1 + int(bw_tot * h_frac * min(1.0, rp))
            draw.rounded_rectangle([bx1, oy1 + 162, bx2, oy1 + 180], radius=6, fill=ACCENT_CYAN)
            if split_x > bx1 + 6:
                draw.rounded_rectangle([bx1, oy1 + 162, split_x, oy1 + 180], radius=6, fill=ACCENT_GOLD)

    return frame


def _render_outro_frame(outro_bg: Image.Image, elapsed: float) -> Image.Image:
    frame = outro_bg.copy()
    draw = ImageDraw.Draw(frame)
    prog = ease_out_back(_clamp01(elapsed / 0.45))
    cx, cy = WIDTH // 2, HEIGHT // 2
    cw = max(40, int(900 * prog))
    ch = max(40, int(680 * prog))
    x1, y1, x2, y2 = cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2
    draw.rounded_rectangle([x1, y1, x2, y2], radius=36, fill=CARD_NAVY, outline=ACCENT_GOLD, width=5)

    if prog > 0.65:
        pulse = int(10 * math.sin(elapsed * 8.5))
        bx1, by1, bx2, by2 = cx - 290 - pulse, cy - 40 - pulse // 2, cx + 290 + pulse, cy + 95 + pulse // 2
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=28, fill=ACCENT_RED, outline=TEXT_WHITE, width=3)

        f_sub = load_impact_font(68)
        stb = draw.textbbox((0, 0), "ABONE OL", font=f_sub)
        draw.text((cx - (stb[2] - stb[0]) // 2, (by1 + by2) // 2 - 42), "ABONE OL", font=f_sub, fill=TEXT_WHITE)

        t1 = "FUTBOL GÜNDEMİNİ KAÇIRMA!"
        f_t1 = load_impact_font(62)
        tb1 = draw.textbbox((0, 0), t1, font=f_t1)
        draw.text((cx - (tb1[2] - tb1[0]) // 2, y1 + 95), t1, font=f_t1, fill=ACCENT_GOLD)

        t2 = "Her saat başı yeni spor haberleri ve grafik analizler!"
        f_t2 = load_font(30, True)
        tb2 = draw.textbbox((0, 0), t2, font=f_t2)
        draw.text((cx - (tb2[2] - tb2[0]) // 2, by2 + 70), t2, font=f_t2, fill=TEXT_WHITE)

        t3 = "Videoyu beğenip yorum yapmayı unutmayın"
        f_t3 = load_font(27, True)
        tb3 = draw.textbbox((0, 0), t3, font=f_t3)
        draw.text((cx - (tb3[2] - tb3[0]) // 2, by2 + 135), t3, font=f_t3, fill=ACCENT_CYAN)
    return frame


def render_graph_motion_mp4(scene_specs: List[Dict[str, Any]], out_mp4: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    vo_sub_path = OUTPUT_DIR / "vo_subscribe_outro.mp3"
    if not vo_sub_path.exists() or vo_sub_path.stat().st_size < 1000:
        asyncio.run(generate_tts(SUBSCRIBE_VOICEOVER, vo_sub_path))
    outro_dur = max(2.8, get_audio_duration(vo_sub_path) + 0.35)

    prepared_segments: List[Tuple[Dict[str, Any], Path, float]] = []
    for idx, spec in enumerate(scene_specs):
        seg_mp3 = OUTPUT_DIR / f"vo_{out_mp4.stem}_gm_{idx}.mp3"
        asyncio.run(generate_tts(spec["vo"], seg_mp3))
        dur = max(4.5, get_audio_duration(seg_mp3) + 0.4)
        prep = _prepare_stats_sprites(spec) if spec.get("kind") == "stats" else _prepare_story_sprites(spec)
        prepared_segments.append((prep, seg_mp3, dur))

    main_dur = sum(x[2] for x in prepared_segments)
    total_dur = main_dur + outro_dur
    total_frames = int(math.ceil(total_dur * FPS))

    outro_bg = _make_base_gradient(None)

    input_args: List[str] = []
    # Enerjik broadcast ritim + derin bas alt yapısı
    filter_parts: List[str] = [
        f"aevalsrc='0.11*sin(2*PI*62*t)*exp(-3.4*mod(t,0.5))+0.045*sin(2*PI*186*t)*exp(-6.0*mod(t,0.25))'"
        f":s=44100:d={total_dur:.2f}[bgm]"
    ]
    mix_labels = ["[bgm]"]
    cursor = 0.0
    for idx, (_, seg_mp3, seg_dur) in enumerate(prepared_segments):
        input_args.extend(["-i", str(seg_mp3)])
        in_idx = idx + 1
        delay_ms = int(round(cursor * 1000))
        lbl = f"[vo{idx}]"
        if delay_ms > 0:
            filter_parts.append(f"[{in_idx}:a]aresample=44100,volume=1.95,adelay={delay_ms}|{delay_ms}{lbl}")
        else:
            filter_parts.append(f"[{in_idx}:a]aresample=44100,volume=1.95{lbl}")
        mix_labels.append(lbl)
        cursor += seg_dur

    input_args.extend(["-i", str(vo_sub_path)])
    sub_idx = len(prepared_segments) + 1
    sub_delay_ms = int(round(main_dur * 1000))
    filter_parts.append(f"[{sub_idx}:a]aresample=44100,volume=1.95,adelay={sub_delay_ms}|{sub_delay_ms}[vosub]")
    mix_labels.append("[vosub]")
    filter_parts.append(
        f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=first:dropout_transition=0,"
        f"alimiter=limit=0.95[aout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        *input_args,
        "-filter_complex", ";".join(filter_parts),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-t", f"{total_dur:.2f}",
        str(out_mp4),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    bounds: List[Tuple[float, float, Dict[str, Any]]] = []
    ct = 0.0
    for prep, _, seg_dur in prepared_segments:
        bounds.append((ct, ct + seg_dur, prep))
        ct += seg_dur

    for f_idx in range(total_frames):
        t = f_idx / FPS
        if t < main_dur:
            active_i = len(bounds) - 1
            for bi, (st_t, en_t, _) in enumerate(bounds):
                if st_t <= t < en_t:
                    active_i = bi
                    break
            st_t, en_t, prep = bounds[active_i]
            local_t = t - st_t
            seg_len = max(0.2, en_t - st_t)

            cur_frame = (
                _render_stats_frame(prep, local_t, seg_len, t, total_dur)
                if prep["kind"] == "stats"
                else _render_story_frame(prep, local_t, seg_len, t, total_dur)
            )

            # Sahneler arası hızlı Whip-Pan kamera geçişi (0.26 sn)
            if active_i > 0 and local_t < 0.26:
                prev_st, prev_en, prev_prep = bounds[active_i - 1]
                prev_len = max(0.2, prev_en - prev_st)
                prev_frame = (
                    _render_stats_frame(prev_prep, prev_len, prev_len, t, total_dur)
                    if prev_prep["kind"] == "stats"
                    else _render_story_frame(prev_prep, prev_len, prev_len, t, total_dur)
                )
                wp = ease_out_cubic(local_t / 0.26)
                shift_px = int(WIDTH * wp)
                comb = Image.new("RGB", (WIDTH, HEIGHT))
                comb.paste(prev_frame, (-shift_px, 0))
                comb.paste(cur_frame, (WIDTH - shift_px, 0))
                cur_frame = comb

            frame = cur_frame
        else:
            frame = _render_outro_frame(outro_bg, t - main_dur)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    stderr_bytes = proc.stderr.read() if proc.stderr else b""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası:\n{stderr_bytes.decode('utf-8', errors='ignore')}")
    return out_mp4
