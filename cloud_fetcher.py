"""
Resmi iddaa.com Canlı Bülten & Oran Çekici (sportsbookv2.iddaa.com)
Maçları, saatleri, ligleri ve MS 1 / X / 2, 2.5 ÜST, KG VAR oranlarını doğrudan
resmi https://sportsbookv2.iddaa.com/sportsbook/events?st=1&type=0&version=0 API'sinden çeker.
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

TURKISH_SUPER_LIG_TEAMS = {
    "Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor", "Başakşehir",
    "Samsunspor", "Göztepe", "Eyüpspor", "Konyaspor", "Antalyaspor",
    "Alanyaspor", "Çaykur Rizespor", "Rizespor", "Kasımpaşa", "Gaziantep FK",
    "Kayserispor", "Sivasspor", "Gençlerbirliği",
}

EURO_CHAMPIONS = {
    "Real Madrid", "Barcelona", "Atletico Madrid",
    "Manchester City", "Liverpool", "Arsenal", "Manchester United", "Chelsea",
    "AC Milan", "Milan", "Juventus", "Napoli", "Roma", "Lazio",
    "Bayern Münih", "Borussia Dortmund", "B. Dortmund", "B. Leverkusen", "Bayer Leverkusen",
    "PSG", "Paris Saint-Germain", "Marsilya", "Lyon", "Monaco",
    "Benfica", "Porto", "Sporting CP", "Ajax", "PSV", "Feyenoord", "Celtic",
}

MONTHS_TR = [
    "", "OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN",
    "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"
]
DAYS_TR = [
    "PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"
]


def fetch_json(url: str) -> Any:
    import time
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == 3:
                raise e
            time.sleep(1.0)


def clean_league_name(full_name: str, short_name: str) -> str:
    if "Şampiyonlar Ligi" in full_name:
        return "Şampiyonlar Ligi"
    if "Avrupa Ligi" in full_name:
        return "Avrupa Ligi"
    if "Konferans Ligi" in full_name:
        return "Konferans Ligi"
    if "Türkiye Süper Lig" in full_name:
        return "Süper Lig"
    if "İngiltere Premier Lig" in full_name:
        return "Premier Lig"
    if "İspanya La Liga" in full_name or "LaLiga" in full_name:
        return "La Liga"
    if "İtalya Serie A" in full_name:
        return "Serie A"
    if "Almanya Bundesliga" in full_name:
        return "Bundesliga"
    if "Fransa Ligue 1" in full_name:
        return "Ligue 1"
    return short_name.strip() or full_name[:18]


def is_euro_giant(team_name: str) -> bool:
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


def update_from_official_iddaa() -> None:
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    now_tr = datetime.datetime.now(tz_tr)
    today_date = now_tr.date()

    comp_map = get_competitions_map()
    ev_data = fetch_json(EVENTS_URL)
    events = ev_data.get("data", {}).get("events", [])

    todays_events: List[Dict[str, Any]] = []

    for ev in events:
        ts = ev.get("d", 0)
        dt_tr = datetime.datetime.fromtimestamp(ts, tz=tz_tr)
        if dt_tr.date() != today_date:
            continue

        odds = extract_iddaa_odds(ev.get("m", []))
        if odds["ms1"] == "-":
            continue

        ci = int(ev.get("ci", 0))
        comp = comp_map.get(ci, {})
        league_full = str(comp.get("n", "Futbol"))
        league_clean = clean_league_name(league_full, str(comp.get("sn", "")))
        comp_prio = int(comp.get("p", 9999))

        hn = str(ev.get("hn", "")).strip()
        an = str(ev.get("an", "")).strip()

        score_prio = 0
        if any(t.lower() in hn.lower() or t.lower() in an.lower() for t in TURKISH_SUPER_LIG_TEAMS):
            score_prio += 6000
        if "Türkiye Süper Lig" in league_full:
            score_prio += 4000
        if any(k in league_full for k in ("Şampiyonlar Ligi", "Avrupa Ligi", "Konferans Ligi")):
            score_prio += 3000
        if is_euro_giant(hn) or is_euro_giant(an):
            score_prio += 1500
        score_prio += max(0, 500 - comp_prio)

        todays_events.append(
            {
                "prio": score_prio,
                "time": dt_tr.strftime("%H:%M"),
                "league": league_clean,
                "home": hn,
                "away": an,
                "ms1": odds["ms1"],
                "msx": odds["msx"],
                "ms2": odds["ms2"],
                "over25": odds["over25"],
                "btts": odds["btts"],
                "score": "0 - 0",
            }
        )

    todays_events.sort(key=lambda x: (-x["prio"], x["time"]))
    selected = todays_events[:12]

    if not selected:
        print("[BİLGİ] Bugün için bültende maç bulunamadı.")
        return

    coupon_items = []
    total_odd = 1.0
    for m in selected[:4]:
        f1 = float(m["ms1"])
        f2 = float(m["ms2"])
        if f1 <= 1.65:
            pick, odd = "MS 1", f1
        elif f2 <= 1.75:
            pick, odd = "MS 2", f2
        elif m["btts"]:
            pick, odd = "KG VAR", float(m["btts"])
        elif m["over25"]:
            pick, odd = "2.5 ÜST", float(m["over25"])
        else:
            pick, odd = ("MS 1", f1) if f1 <= f2 else ("MS 2", f2)
        total_odd *= odd
        coupon_items.append(
            {
                "time": m["time"],
                "league": m["league"],
                "home": m["home"],
                "away": m["away"],
                "pick": pick,
                "odd": f"{odd:.2f}",
            }
        )

    subtitle_date = f"{now_tr.day} {MONTHS_TR[now_tr.month]} {DAYS_TR[now_tr.weekday()]}"
    fetched_time_str = now_tr.strftime("%d.%m.%Y - %H:%M")
    payload = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
    payload["subtitle"] = f"{subtitle_date}  •  RESMİ İDDAA.COM BÜLTENİ"
    payload["odds_fetched_at"] = fetched_time_str
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

    DEFAULT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Resmi iddaa.com API'sinden {subtitle_date} tarihli {len(selected)} maç ve gerçek oranlar çekildi!")
    for idx, m in enumerate(selected, 1):
        print(f"  {idx:2d}. [{m['time']} | {m['league']}] {m['home']} - {m['away']} -> MS1:{m['ms1']} X:{m['msx']} MS2:{m['ms2']}")


if __name__ == "__main__":
    update_from_official_iddaa()
