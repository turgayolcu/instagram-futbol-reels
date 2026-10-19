"""
Resmi iddaa.com Canlı Bülten & Oran Çekici + Mackolik Maç Sonuçları Teyit Motoru
- Sabah (odds) ve Öğlen (coupon) için maçları ve oranları resmi sportsbookv2.iddaa.com API'sinden çeker.
- Akşam (results) Günün Maç Sonuçları için biten maçları ve gerçek skorları doğrudan
  Mackolik (https://vd.mackolik.com/livedata?date=GG/AA/YYYY) servisinden çekip teyit eder.
  Asla teyitsiz '0 - 0' başlangıç skoru paylaşmaz.
"""

import datetime
import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_JSON = BASE_DIR / "default_data.json"

EVENTS_URL = "https://sportsbookv2.iddaa.com/sportsbook/events?st=1&type=0&version=0"
COMPETITIONS_URL = "https://sportsbookv2.iddaa.com/sportsbook/competitions"
MACKOLIK_DATE_URL = "https://vd.mackolik.com/livedata?date={date_str}"
MACKOLIK_LIVE_URL = "https://vd.mackolik.com/livedata?group=0"

TURKISH_SUPER_LIG_TEAMS = {
    "Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor", "Başakşehir",
    "Samsunspor", "Göztepe", "Eyüpspor", "Konyaspor", "Antalyaspor",
    "Alanyaspor", "Çaykur Rizespor", "Rizespor", "Kasımpaşa", "Gaziantep FK",
    "Kayserispor", "Sivasspor", "Gençlerbirliği", "Çorum FK", "Kocaelispor",
}

TURKISH_GIANTS = {
    "Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor"
}

EURO_CHAMPIONS = {
    "Real Madrid", "Barcelona", "Atletico Madrid",
    "Manchester City", "Liverpool", "Arsenal", "Manchester United", "Chelsea",
    "AC Milan", "Milan", "Juventus", "Napoli", "Roma", "Lazio", "Inter",
    "Bayern Münih", "Borussia Dortmund", "B. Dortmund", "B. Leverkusen", "Bayer Leverkusen",
    "PSG", "Paris Saint-Germain", "Marsilya", "Lyon", "Monaco",
    "Benfica", "Porto", "Sporting CP", "Ajax", "PSV", "Feyenoord", "Celtic",
}

# Kendi liginde şampiyonluk yaşamış devler ve kupa sayıları
CLUB_CHAMPIONSHIPS = {
    # Türkiye
    "Galatasaray": 24, "Fenerbahçe": 19, "Beşiktaş": 16, "Trabzonspor": 7, "Başakşehir": 1, "Bursaspor": 1,
    # İspanya
    "Real Madrid": 36, "Barcelona": 27, "Atletico Madrid": 11, "Athletic Bilbao": 8, "Valencia": 6, "Real Sociedad": 2, "Sevilla": 1, "Real Betis": 1, "Deportivo": 1,
    # İtalya
    "Juventus": 36, "Inter": 20, "AC Milan": 19, "Genoa": 9, "Torino": 7, "Bologna": 7, "Roma": 3, "AS Roma": 3, "Napoli": 3, "Lazio": 2, "Fiorentina": 2,
    # İngiltere
    "Manchester United": 20, "Liverpool": 19, "Arsenal": 13, "Manchester City": 10, "Everton": 9, "Aston Villa": 7, "Chelsea": 6, "Newcastle": 4, "Leeds United": 3, "Tottenham": 2, "Nottingham Forest": 1,
    # Almanya
    "Bayern Münih": 33, "Borussia Dortmund": 8, "B. Dortmund": 8, "Schalke": 7, "Hamburger SV": 6, "VfB Stuttgart": 5, "Borussia Mönchengladbach": 8, "Monchengladbach": 8, "B. Leverkusen": 10, "Bayer Leverkusen": 10, "Werder Bremen": 4, "Köln": 3, "Wolfsburg": 1, "Eintracht Frankfurt": 1,
    # Fransa
    "PSG": 12, "Paris Saint-Germain": 12, "Saint-Etienne": 10, "Marsilya": 9, "Marseille": 9, "Monaco": 8, "Nantes": 8, "Lyon": 7, "Bordeaux": 6, "Lille": 4, "Nice": 4, "Lens": 1, "RC Lens": 1, "Strasbourg": 1, "Rennes": 0, "Montpellier": 1, "AJ Auxerre": 1,
    # Diğer
    "Benfica": 38, "Porto": 30, "Sporting CP": 20, "Ajax": 36, "PSV": 25, "Feyenoord": 16, "Celtic": 54, "Rangers": 55, "Anderlecht": 34, "Club Brugge": 19, "Olympiacos": 47, "Panathinaikos": 20,
}

MONTHS_TR = [
    "", "OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN",
    "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"
]
DAYS_TR = [
    "PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"
]


def fetch_json(url: str, referer: str = "") -> Any:
    import time
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8", "ignore"))
        except Exception as e:
            if attempt == 3:
                raise e
            time.sleep(1.0)


def clean_league_name(full_name: str, short_name: str) -> str:
    if "UEFA Şampiyonlar Ligi" in full_name or "Şampiyonlar Ligi" in full_name:
        return "Şampiyonlar Ligi"
    if "UEFA Avrupa Ligi" in full_name or "Avrupa Ligi" in full_name:
        return "Avrupa Ligi"
    if "UEFA Konferans Ligi" in full_name or "Konferans Ligi" in full_name:
        return "Konferans Ligi"
    if "Türkiye Süper Lig" in full_name:
        return "Süper Lig"
    if "Türkiye 1. Lig" in full_name:
        return "1. Lig"
    if "İngiltere Premier Lig" in full_name and "2" not in full_name and "U21" not in full_name:
        return "Premier Lig"
    if "İspanya La Liga" in full_name or "LaLiga" in full_name:
        return "La Liga"
    if "İtalya Serie A" in full_name:
        return "Serie A"
    if "Almanya Bundesliga" in full_name and "2." not in full_name:
        return "Bundesliga"
    if "Fransa Ligue 1" in full_name:
        return "Ligue 1"
    if "Süper Lig" in full_name or short_name.strip() in ("Süper Lig", "Superliga"):
        prefix = full_name.split()[0] if full_name else ""
        return f"{prefix} Ligi"[:18]
    return short_name.strip() or full_name[:18]


def is_youth_or_reserve(name: str) -> bool:
    low = f" {name.lower().strip()} "
    youth_tokens = (
        " u21 ", " u19 ", " u20 ", " u23 ", " u18 ", " u17 ", " u16 ", " ii ", " (k) ",
        " kadın ", " genç ", " reserve ", " bölgesel ", " amatör ", " b ", " (b) "
    )
    return any(tok in low for tok in youth_tokens)


def is_euro_giant(team_name: str) -> bool:
    if is_youth_or_reserve(team_name):
        return False
    t_low = team_name.lower().strip()
    if t_low == "inter":
        return True
    for g in EURO_CHAMPIONS:
        if g.lower() == t_low or (len(g) > 5 and g.lower() in t_low):
            return True
    return False


def get_competitions_map() -> Dict[int, Dict[str, Any]]:
    data = fetch_json(COMPETITIONS_URL)
    comp_map: Dict[int, Dict[str, Any]] = {}
    for c in data.get("data", []):
        cid = c.get("i")
        if cid is not None:
            comp_map[int(cid)] = c
    return comp_map


def extract_iddaa_odds(markets: List[Dict[str, Any]]) -> Dict[str, str]:
    res = {"ms1": "-", "msx": "-", "ms2": "-", "over25": "", "btts": ""}
    for m in markets:
        st = m.get("st")
        sov = str(m.get("sov", ""))
        outcomes = m.get("o", [])
        if st == 1 and len(outcomes) >= 3:
            for o in outcomes:
                name = str(o.get("n", ""))
                odd_val = f"{float(o.get('odd', 0)):.2f}"
                if name == "1":
                    res["ms1"] = odd_val
                elif name in ("0", "X"):
                    res["msx"] = odd_val
                elif name == "2":
                    res["ms2"] = odd_val
        elif st == 101 and sov == "2.5":
            for o in outcomes:
                if "Üst" in str(o.get("n", "")) or o.get("no") == 2:
                    res["over25"] = f"{float(o.get('odd', 0)):.2f}"
        elif st == 89:
            for o in outcomes:
                if str(o.get("n", "")) == "Var" or o.get("no") == 1:
                    res["btts"] = f"{float(o.get('odd', 0)):.2f}"
    return res


def fetch_mackolik_verified_results(target_date: datetime.date) -> List[Dict[str, str]]:
    """
    Mackolik'ten (vd.mackolik.com/livedata?date=GG/AA/YYYY) o günkü BİTEN (MS)
    futbol maçlarının gerçek skorlarını çeker. Eğer gece yarısından hemen sonra çalışırsa
    veya bugün henüz yeterli biten maç yoksa bir önceki günün biten maçlarını da kontrol eder.
    """
    dates_to_try = [
        target_date.strftime("%d/%m/%Y"),
        (target_date - datetime.timedelta(days=1)).strftime("%d/%m/%Y"),
    ]

    for d_str in dates_to_try:
        try:
            url = MACKOLIK_DATE_URL.format(date_str=d_str)
            data = fetch_json(url, referer="https://arsiv.mackolik.com/Canli-Sonuclar")
        except Exception as e:
            print(f"[UYARI] Mackolik ({d_str}) çekilemedi: {e}")
            continue

        finished_list: List[Dict[str, Any]] = []
        for idx, m in enumerate(data.get("m", [])):
            if len(m) < 37:
                continue
            comp = m[36]
            # comp[11] == 1 -> Futbol
            if len(comp) < 12 or comp[11] != 1:
                continue

            status_str = str(m[6]).strip().upper()
            status_code = m[5]
            # Sadece gerçekten bitmiş (MS / UZ / PEN) futbol maçlarını al
            if status_str not in ("MS", "UZ", "PEN") and status_code != 4:
                continue

            country = str(comp[1]).strip()
            league_raw = str(comp[3]).strip()
            home = str(m[2]).strip()
            away = str(m[4]).strip()
            if is_youth_or_reserve(home) or is_youth_or_reserve(away) or is_youth_or_reserve(league_raw):
                continue

            h_score = m[12]
            a_score = m[13]
            score_str = f"{h_score} - {a_score}"

            full_lg = f"{country} {league_raw}".strip()
            clean_lg = clean_league_name(full_lg, league_raw)

            # Mackolik dizilim sırası zaten popüler ligleri en üste koyar (idx küçükse daha popüler)
            prio = max(0, 1000 - idx * 2)
            if ("Türkiye" in country and ("Süper Lig" in league_raw or "1. Lig" in league_raw)) or any(
                t.lower() in home.lower() or t.lower() in away.lower() for t in TURKISH_SUPER_LIG_TEAMS
            ):
                prio += 6000
            if country == "Avrupa" and any(k in full_lg for k in ("Şampiyonlar Ligi", "Avrupa Ligi", "Konferans Ligi")):
                prio += 4500
            if country in ("İngiltere", "İspanya", "İtalya", "Almanya", "Fransa", "Hollanda", "Portekiz"):
                prio += 2500
            if is_euro_giant(home) or is_euro_giant(away):
                prio += 1500

            finished_list.append(
                {
                    "prio": prio,
                    "time": "MS",
                    "league": clean_lg[:18],
                    "home": home,
                    "away": away,
                    "score": score_str,
                    "date_str": d_str,
                }
            )

        euro_tr_count = sum(1 for x in finished_list if x["prio"] >= 2000)
        if euro_tr_count >= 5 or (d_str == dates_to_try[-1] and len(finished_list) >= 6):
            finished_list.sort(key=lambda x: -x["prio"])
            selected_res = finished_list[:12]
            print(f"[OK] Mackolik'ten ({d_str}) {len(selected_res)} BİTEN maç sonucu teyit edildi:")
            for i, r in enumerate(selected_res, 1):
                print(f"  {i:2d}. [MS | {r['league']}] {r['home']} {r['score']} {r['away']}")
            return [
                {
                    "time": "MS",
                    "league": r["league"],
                    "home": r["home"],
                    "away": r["away"],
                    "ms1": "-",
                    "msx": "-",
                    "ms2": "-",
                    "score": r["score"],
                }
                for r in selected_res
            ]

    return []


def update_from_official_iddaa() -> None:
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    now_tr = datetime.datetime.now(tz_tr)
    today_date = now_tr.date()
    weekday = now_tr.weekday()  # 0: Pazartesi, 1: Salı, 2: Çarşamba, 3: Perşembe, 4: Cuma, 5: Cumartesi, 6: Pazar

    comp_map = get_competitions_map()
    ev_data = fetch_json(EVENTS_URL)
    events = ev_data.get("data", {}).get("events", [])

    # 1) Sadece BUGÜN oynanacak maçları topla (asla ertesi günün maçlarını alma)
    raw_today_events = []
    has_cl_today = False
    has_uel_uecl_today = False

    for ev in events:
        ts = ev.get("d", 0)
        dt_tr = datetime.datetime.fromtimestamp(ts, tz=tz_tr)
        if dt_tr.date() != today_date:
            continue

        ci = int(ev.get("ci", 0))
        comp = comp_map.get(ci, {})
        league_full = str(comp.get("n", "Futbol"))
        hn = str(ev.get("hn", "")).strip()
        an = str(ev.get("an", "")).strip()

        if is_youth_or_reserve(hn) or is_youth_or_reserve(an) or is_youth_or_reserve(league_full):
            continue

        if "UEFA Şampiyonlar Ligi" in league_full or "Şampiyonlar Ligi" in league_full:
            has_cl_today = True
        if "UEFA Avrupa Ligi" in league_full or "UEFA Konferans Ligi" in league_full:
            has_uel_uecl_today = True

        raw_today_events.append((ev, comp, dt_tr, league_full, hn, an))

    # Kural 1: Konsept belirleme
    # - Hafta içi Salı/Çarşamba Şampiyonlar Ligi maçları varsa konsept Şampiyonlar Ligi
    # - Çarşamba/Perşembe UEFA Avrupa ve Konferans Ligi varsa bu ligler
    # - Diğer günlerde Türkiye Süper Lig ve Avrupa'nın 5 büyük ligi
    concept = "SUPER_LIG_BIG5"
    if weekday in (1, 2) and has_cl_today:
        concept = "CHAMPIONS_LEAGUE"
    elif weekday in (2, 3) and has_uel_uecl_today:
        concept = "EUROPA_CONFERENCE"

    target_5_leagues = [
        ("Türkiye Süper Lig", "Süper Lig"),
        ("İngiltere Premier Lig", "Premier Lig"),
        ("İspanya La Liga", "La Liga"),
        ("İtalya Serie A", "Serie A"),
        ("Almanya Bundesliga", "Bundesliga"),
        ("Fransa Ligue 1", "Ligue 1"),
    ]

    tr_matches: List[Dict[str, Any]] = []
    euro_matches: List[Dict[str, Any]] = []
    all_valid_events: List[Dict[str, Any]] = []

    for ev, comp, dt_tr, league_full, hn, an in raw_today_events:
        odds = extract_iddaa_odds(ev.get("m", []))
        if odds["ms1"] == "-":
            continue

        league_clean = clean_league_name(league_full, str(comp.get("sn", "")))
        time_str = dt_tr.strftime("%H:%M")

        match_item = {
            "time": time_str,
            "league": league_clean,
            "home": hn,
            "away": an,
            "ms1": odds["ms1"],
            "msx": odds["msx"],
            "ms2": odds["ms2"],
            "over25": odds["over25"],
            "btts": odds["btts"],
            "score": "-",
        }
        all_valid_events.append(match_item)

        is_turkish = (
            "Türkiye Süper Lig" in league_full
            or ("Süper Lig" in league_clean and ("Türkiye" in league_full or "Turkiye" in league_full))
        )

        if concept == "CHAMPIONS_LEAGUE":
            is_target_league = "Şampiyonlar Ligi" in league_full or is_turkish
            if is_turkish and "Süper Lig" not in match_item["league"]:
                match_item["league"] = "Süper Lig"
        elif concept == "EUROPA_CONFERENCE":
            is_target_league = (
                "UEFA Avrupa Ligi" in league_full
                or "UEFA Konferans Ligi" in league_full
                or is_turkish
            )
            if is_turkish and "Süper Lig" not in match_item["league"]:
                match_item["league"] = "Süper Lig"
        else:
            # Türkiye Süper Lig ve Avrupa'nın 5 büyük ligi
            is_target_league = False
            if is_turkish:
                is_target_league = True
                match_item["league"] = "Süper Lig"
            else:
                for tl_full, tl_short in target_5_leagues:
                    if tl_full in league_full and "2." not in league_full and "La Liga 2" not in league_full:
                        is_target_league = True
                        match_item["league"] = tl_short
                        break

        if not is_target_league:
            continue

        if is_turkish:
            tr_matches.append(match_item)
        else:
            titles = max(CLUB_CHAMPIONSHIPS.get(hn, 0), CLUB_CHAMPIONSHIPS.get(an, 0))
            match_item["titles"] = titles
            euro_matches.append(match_item)

    # Kural 2: Listenin EN BAŞINDA Türk takımları gelecek,
    # ardından kendi liginde en çok şampiyonluk yaşamış popüler takımlar sıralanacak (maksimum 12 maç).
    tr_matches.sort(key=lambda x: x["time"])
    euro_matches.sort(key=lambda x: (-x.get("titles", 0), x["time"]))

    selected = (tr_matches + euro_matches)[:12]

    # Mackolik'ten doğrulanmış biten maç sonuçlarını çek
    verified_results = fetch_mackolik_verified_results(today_date)

    # Eğer bültendeki maçlardan Mackolik'te bitmiş olan varsa skorunu eşleştir
    if verified_results:
        for m in selected:
            h_low = m["home"].lower()[:6]
            a_low = m["away"].lower()[:6]
            for vr in verified_results:
                if h_low in vr["home"].lower() or a_low in vr["away"].lower():
                    m["score"] = vr["score"]
                    break

    coupon_candidates = []
    # Günün maçlarından en güvenilir banko seçimleri hazırla
    for m in selected:
        hn = m["home"]
        an = m["away"]
        f1 = float(m["ms1"]) if m["ms1"] != "-" else 99.0
        f2 = float(m["ms2"]) if m["ms2"] != "-" else 99.0
        o25_val = float(m["over25"]) if m.get("over25") else 0.0

        pick = None
        odd = 1.0
        confidence = 0

        if 1.12 <= f1 <= 1.65:
            pick, odd, confidence = "MS 1", f1, 100 - int(f1 * 15)
        elif 1.15 <= f2 <= 1.65:
            pick, odd, confidence = "MS 2", f2, 100 - int(f2 * 15)
        elif 1.25 <= o25_val <= 1.60:
            pick, odd, confidence = "2.5 ÜST", o25_val, 85 - int(o25_val * 10)

        if pick and odd > 1.0:
            if any(t.lower() in hn.lower() or t.lower() in an.lower() for t in TURKISH_SUPER_LIG_TEAMS):
                confidence += 20
            coupon_candidates.append({
                "match": m,
                "pick": pick,
                "odd": odd,
                "confidence": confidence,
            })

    coupon_candidates.sort(key=lambda x: -x["confidence"])

    coupon_items = []
    total_odd = 1.0
    for c in coupon_candidates[:4]:
        m = c["match"]
        odd = c["odd"]
        total_odd *= odd
        coupon_items.append(
            {
                "time": m["time"],
                "league": m["league"],
                "home": m["home"],
                "away": m["away"],
                "pick": c["pick"],
                "odd": f"{odd:.2f}",
            }
        )

    subtitle_date = f"{now_tr.day} {MONTHS_TR[now_tr.month]} {DAYS_TR[now_tr.weekday()]}"
    fetched_time_str = now_tr.strftime("%d.%m.%Y - %H:%M")
    payload = json.loads(DEFAULT_JSON.read_text(encoding="utf-8")) if DEFAULT_JSON.exists() else {}
    payload.pop("voiceover_results", None)
    payload.pop("voiceover_coupon", None)

    if concept == "CHAMPIONS_LEAGUE":
        payload["title"] = "ŞAMPİYONLAR LİGİ & ORANLAR"
        payload["subtitle"] = f"{subtitle_date}  •  ŞAMPİYONLAR LİGİ BÜLTENİ"
    elif concept == "EUROPA_CONFERENCE":
        payload["title"] = "AVRUPA & KONFERANS LİGİ"
        payload["subtitle"] = f"{subtitle_date}  •  UEFA AVRUPA & KONFERANS BÜLTENİ"
    else:
        payload["title"] = "GÜNÜN MAÇLARI & ORANLAR"
        payload["subtitle"] = f"{subtitle_date}  •  RESMİ İDDAA.COM BÜLTENİ"

    payload["coupon_title"] = "GÜNÜN BANKO KUPONU"
    payload["results_title"] = "GÜNÜN MAÇ SONUÇLARI"
    payload["results_subtitle"] = f"{subtitle_date}  •  KAYNAK: MACKOLİK MAÇ SONUÇLARI"
    payload["cta_spor"] = "Hemen oynamak için iddaa.com'a gir bayi kodunu 304168 yap"
    payload["cta_tjk"] = "Hemen oynamak için bayi kodunu 1607 yap (TJK)"
    payload["cta_mp"] = "Hemen oynamak için Milli Piyango bayi kodunu 117718 yap"
    payload["disclaimer"] = "+18 | Sadece bilgilendirme amaçlıdır."
    payload["odds_fetched_at"] = fetched_time_str

    if selected:
        payload["matches"] = [
            {
                "time": m["time"],
                "league": m["league"],
                "home": m["home"],
                "away": m["away"],
                "ms1": m["ms1"],
                "msx": m["msx"],
                "ms2": m["ms2"],
                "score": m["score"],
            }
            for m in selected
        ]
        payload["coupon"] = coupon_items
        payload["total_odd"] = f"{total_odd:.2f}"

    if verified_results:
        payload["results_matches"] = verified_results

    DEFAULT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Resmi iddaa.com API'sinden {subtitle_date} tarihli {len(selected)} bülten maçı ve Mackolik'ten {len(verified_results)} biten maç sonucu kaydedildi!")


if __name__ == "__main__":
    update_from_official_iddaa()
