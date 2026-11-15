"""
GitHub Actions Zamanlayıcı Yedek Bekçisi (cloud_schedule_watchdog.py)
- GitHub'ın ücretsiz cron sunucusu yoğunluk nedeniyle gecikirse veya atlarsa,
  son 35 dakikada bulut çalışması başlamamışsa otomatik olarak GitHub Actions iş akışını tetikler.
- İçinde hiçbir gizli anahtar barındırmaz; yerel Windows Git kimlik bilgisini kullanır.
"""

import datetime
import subprocess
import sys
import requests

REPO = "turgayolcu/instagram-futbol-reels"
WORKFLOW_FILE = "youtube_shorts_cron.yml"


def get_github_token() -> str:
    out = subprocess.check_output(
        ["git", "credential", "fill"],
        input=b"protocol=https\nhost=github.com\n\n",
    ).decode("utf-8", errors="ignore")
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GitHub kimlik bilgisi bulunamadı.")


def pick_mode_for_hour(hour: int) -> str:
    if hour < 10:
        return "headlines"
    if hour < 12:
        return "biography"
    if hour < 15:
        return "breaking"
    if hour < 18:
        return "trivia"
    if hour < 21:
        return "pre_match"
    return "post_match"


def main() -> None:
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

    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    hour_tr = datetime.datetime.now(tz_tr).hour
    mode = sys.argv[1] if len(sys.argv) > 1 else pick_mode_for_hour(hour_tr)

    disp = requests.post(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches",
        headers=headers,
        json={"ref": "master", "inputs": {"mode": mode}},
        timeout=15,
    )
    print(f"[TETİKLENDİ] GitHub Actions '{mode}' yayını başlatıldı (HTTP {disp.status_code}).")


if __name__ == "__main__":
    main()
