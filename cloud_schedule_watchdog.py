"""
GitHub Actions Saatlik Zamanlayıcı Yedek Bekçisi (cloud_schedule_watchdog.py)
- 08:00 - 24:00 (00:00) arası her saat başı kontrol yapar;
  GitHub'ın ücretsiz cron sunucusu yoğunluk nedeniyle gecikirse veya atlarsa,
  son 35 dakikada bulut çalışması başlamamışsa otomatik olarak o saatin kategorisini tetikler.
"""

import datetime
import subprocess
import sys
import requests

REPO = "turgayolcu/instagram-futbol-reels"
WORKFLOW_FILE = "youtube_shorts_cron.yml"

HOURLY_MODES = {
    8: "headlines",
    9: "biography",
    10: "breaking",
    11: "trivia",
    12: "headlines",
    13: "biography",
    14: "breaking",
    15: "pre_match",
    16: "trivia",
    17: "breaking",
    18: "biography",
    19: "pre_match",
    20: "headlines",
    21: "trivia",
    22: "post_match",
    23: "breaking",
    0: "post_match",
}


def get_github_token() -> str:
    out = subprocess.check_output(
        ["git", "credential", "fill"],
        input=b"protocol=https\nhost=github.com\n\n",
    ).decode("utf-8", errors="ignore")
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GitHub kimlik bilgisi bulunamadı.")


def main() -> None:
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    now_tr = datetime.datetime.now(tz_tr)
    # :57'de çalıştığında hedef saat bir sonraki saat başıdır (örn. 13:57 -> 14:00)
    target_dt = now_tr + datetime.timedelta(minutes=10) if now_tr.minute >= 50 else now_tr
    hour_tr = target_dt.hour

    # Sadece 08:00 - 00:15 (24:00 kuşağı dahil) saatleri arasında çalış; 01:00 - 07:45 arası gece uykusu
    if 1 <= hour_tr <= 7 and len(sys.argv) <= 1:
        return

    token = get_github_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    runs_resp = requests.get(
        f"https://api.github.com/repos/{REPO}/actions/runs?per_page=3",
        headers=headers,
        timeout=15,
    )
    if runs_resp.status_code == 200:
        for r in runs_resp.json().get("workflow_runs", []):
            created_str = r.get("created_at", "")
            if not created_str:
                continue
            created_dt = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            age_min = (now_utc - created_dt).total_seconds() / 60.0
            if age_min <= 35.0 and r.get("conclusion") != "failure":
                print(f"[OK] Son {age_min:.1f} dk içinde bulut yayını zaten çalışmış (ID: {r.get('id')}).")
                return

    mode = sys.argv[1] if len(sys.argv) > 1 else HOURLY_MODES.get(hour_tr, "headlines")

    disp = requests.post(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches",
        headers=headers,
        json={"ref": "master", "inputs": {"mode": mode}},
        timeout=15,
    )
    print(f"[TETİKLENDİ] GitHub Actions '{mode}' (Saat {hour_tr:02d}:00) yayını başlatıldı (HTTP {disp.status_code}).")


if __name__ == "__main__":
    main()
