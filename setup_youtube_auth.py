"""
Tek Seferlik YouTube OAuth 2.0 Yetkilendirme Aracı (setup_youtube_auth.py)
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_DEST = BASE_DIR / "client_secret.json"
TOKEN_PATH = BASE_DIR / "youtube_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def find_client_secret_file(custom_arg: Optional[str] = None) -> Optional[Path]:
    if custom_arg:
        p = Path(custom_arg).expanduser().resolve()
        if p.exists():
            return p
    if CLIENT_SECRET_DEST.exists():
        return CLIENT_SECRET_DEST
    local_matches = sorted(BASE_DIR.glob("client_secret*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    if local_matches:
        return local_matches[0]
    home = Path.home()
    for folder in [home / "Downloads", home / "Desktop"]:
        if folder.exists():
            matches = sorted(folder.glob("client_secret*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
            if matches:
                return matches[0]
    return None


def main() -> None:
    arg_path = sys.argv[1] if len(sys.argv) > 1 else None
    secret_file = find_client_secret_file(arg_path)
    if secret_file is None:
        print("[HATA] client_secret.json bulunamadı!", flush=True)
        sys.exit(1)

    if secret_file.resolve() != CLIENT_SECRET_DEST.resolve():
        shutil.copyfile(secret_file, CLIENT_SECRET_DEST)
        print(f"[OK] İndirilen dosya kopyalandı: {secret_file.name} -> client_secret.json", flush=True)

    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_DEST), SCOPES)
    print("[1/2] Yerel OAuth sunucusu başlatılıyor (port 8090)...", flush=True)
    creds = flow.run_local_server(
        host="localhost",
        port=8090,
        authorization_prompt_message="AUTH_URL: {url}",
        success_message="Harika! YouTube kanal baglantisi tamamlandi. Bu sekmeyi kapatip sohbete donebilirsiniz.",
        open_browser=False,
        prompt="consent",
        access_type="offline",
    )

    token_data = json.loads(creds.to_json())
    TOKEN_PATH.write_text(json.dumps(token_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[2/2] Kalıcı YouTube oturum anahtarı kaydedildi: {TOKEN_PATH}", flush=True)

    yt = build("youtube", "v3", credentials=creds)
    resp = yt.channels().list(part="snippet,statistics", mine=True).execute()
    items = resp.get("items", [])
    if items:
        ch = items[0]
        title = ch["snippet"]["title"]
        ch_id = ch["id"]
        subs = ch["statistics"].get("subscriberCount", "0")
        print(f"[BAŞARILI] Bağlanan YouTube Kanalı: {title} (ID: {ch_id} | Abone: {subs})", flush=True)
    else:
        print("[UYARI] Bu Google hesabına bağlı aktif bir YouTube kanalı görünmedi.", flush=True)


if __name__ == "__main__":
    main()
