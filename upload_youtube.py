"""
Resmi YouTube Data API v3 Spor Medyası Shorts Yükleyici (upload_youtube.py)
- 9:16 dikey (< 60 sn) MP4 videolarını otomatik olarak YouTube Shorts (#Shorts) olarak yükler.
- Sıfır bahis/iddaa ibaresi: %100 saf spor haberi, futbol analizi, biyografi ve genel kültür kanalı formatı.
- Hem yerelde (youtube_token.json) hem GitHub Actions bulutunda (YT_TOKEN_JSON secret)
  otomatik Refresh Token yenilemesiyle şifresiz ve kesintisiz çalışır.
"""

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def ensure_shorts_duration(video_path: Path) -> Path:
    """
    YouTube Shorts algoritmasının videoyu %100 Shorts olarak tanıması için süreyi kontrol eder;
    58.8 saniyeyi aşıyorsa hafif hızlandırarak 57.5 saniyenin altında tutar.
    """
    try:
        res = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        dur = float(res.stdout.strip())
        if dur <= 58.8:
            return video_path

        speed = dur / 57.5
        trimmed_path = video_path.with_name(f"{video_path.stem}_short.mp4")
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(video_path),
                "-filter_complex", f"[0:v]setpts={1.0/speed:.4f}*PTS[v];[0:a]atempo={min(2.0, speed):.4f}[a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                str(trimmed_path),
            ],
            check=True,
        )
        if trimmed_path.exists() and trimmed_path.stat().st_size > 1000:
            return trimmed_path
    except Exception as e:
        print(f"[UYARI] Shorts süre kontrolü atlandı: {e}")
    return video_path


def build_title_and_description(raw_caption: str) -> Tuple[str, str, List[str]]:
    lines = [ln.strip() for ln in raw_caption.strip().splitlines() if ln.strip()]
    first_line = lines[0] if lines else "Günün Futbol Gündemi!"
    clean_first = " ".join(w for w in first_line.split() if not w.startswith("#")).strip()
    if not clean_first:
        clean_first = "Günün Futbol Gündemi!"

    suffix = " #Shorts"
    max_base_len = 100 - len(suffix)
    if len(clean_first) > max_base_len:
        clean_first = clean_first[: max_base_len - 1].rstrip() + "…"
    yt_title = f"{clean_first}{suffix}"

    desc_parts = [
        raw_caption.strip(),
        "🔔 En güncel futbol haberleri, maç önü istatistikleri, maç sonu analizleri, futbolcu hikayeleri ve futbol genel kültürü için kanalımıza abone olmayı unutmayın!",
    ]
    if "#shorts" not in raw_caption.lower():
        desc_parts.append("#Shorts #Futbol #SporHaberleri #SüperLig #ŞampiyonlarLigi #FutbolAnaliz")

    yt_desc = "\n\n".join(desc_parts)[:4900]
    tags = [
        "shorts", "futbol", "spor haberleri", "son dakika spor", "süper lig",
        "futbol genel kültür", "futbolcu hikayeleri", "maç analizi", "galatasaray",
        "fenerbahçe", "beşiktaş", "trabzonspor", "şampiyonlar ligi",
    ]
    return yt_title, yt_desc, tags


def load_youtube_credentials(base_dir: Path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_file = base_dir / "youtube_token.json"
    env_json = os.environ.get("YT_TOKEN_JSON", "").strip()

    token_data = None
    if token_file.exists() and token_file.stat().st_size > 20:
        token_data = json.loads(token_file.read_text(encoding="utf-8"))
    elif env_json:
        token_data = json.loads(env_json)

    if not token_data:
        raise RuntimeError(
            "YouTube oturum anahtarı (youtube_token.json veya YT_TOKEN_JSON) bulunamadı!"
        )

    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        if token_file.exists():
            token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def is_duplicate_recent_short(yt, yt_title: str) -> bool:
    """
    Son 75 dakika içinde kanala zaten bir Shorts yüklendiyse (veya aynı başlık son 6 saatte yüklendiyse)
    mükerrer yüklemeyi ve gereksiz API kotası harcamasını önler.
    """
    if os.environ.get("FORCE_UPLOAD") == "1":
        return False
    try:
        ch_resp = yt.channels().list(part="contentDetails", mine=True).execute()
        items = ch_resp.get("items", [])
        if not items:
            return False
        uploads_pl = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl_resp = yt.playlistItems().list(part="snippet", playlistId=uploads_pl, maxResults=5).execute()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        target_prefix = yt_title.replace("#Shorts", "").strip().lower()[:28]
        for item in pl_resp.get("items", []):
            snip = item.get("snippet", {})
            pub_str = snip.get("publishedAt", "")
            existing_title = snip.get("title", "").lower()
            if not pub_str:
                continue
            pub_dt = datetime.datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            age_sec = (now_utc - pub_dt).total_seconds()
            if age_sec < 75 * 60:
                vid_id = snip.get("resourceId", {}).get("videoId", "")
                print(f"[BİLGİ] Son 75 dk içinde zaten bir Shorts yayınlanmış (ID: {vid_id}). Kota koruması devrede.")
                return True
            if target_prefix and target_prefix in existing_title and age_sec < 6 * 3600:
                vid_id = snip.get("resourceId", {}).get("videoId", "")
                print(f"[BİLGİ] '{yt_title}' son 6 saat içinde zaten yüklenmiş (ID: {vid_id}). Atlandı.")
                return True
    except Exception as e:
        print(f"[UYARI] Son yükleme kontrolü atlandı: {e}")
    return False


def upload_short(video_path: Path, caption: str, privacy_status: str = "public") -> Optional[str]:
    base_dir = Path(__file__).resolve().parent
    creds = load_youtube_credentials(base_dir)

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    yt = build("youtube", "v3", credentials=creds)
    yt_title, yt_desc, tags = build_title_and_description(caption)

    if is_duplicate_recent_short(yt, yt_title):
        return "SKIPPED_DUPLICATE"

    ready_video = ensure_shorts_duration(video_path)
    print(f"[1/2] YouTube Shorts yükleniyor: {ready_video.name} | Başlık: {yt_title}")

    body = {
        "snippet": {
            "title": yt_title,
            "description": yt_desc,
            "tags": tags,
            "categoryId": "17",  # 17 = Sports (Spor)
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(ready_video),
        mimetype="video/mp4",
        chunksize=4 * 1024 * 1024,
        resumable=True,
    )
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  -> Yükleme ilerlemesi: %{pct}")

    video_id = response.get("id", "")
    print(f"[2/2] BAŞARILI! YouTube Shorts yayında: https://www.youtube.com/shorts/{video_id}")
    return video_id


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python upload_youtube.py <video_mp4_yolu> <aciklama_metni>")
        sys.exit(1)

    v_path = Path(sys.argv[1]).resolve()
    cap_text = sys.argv[2]
    if not v_path.exists():
        print(f"[HATA] Video dosyası bulunamadı: {v_path}")
        sys.exit(1)

    upload_short(v_path, cap_text)
