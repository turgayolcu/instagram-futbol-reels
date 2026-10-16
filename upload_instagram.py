"""
Oturum Kayıtlı (ig_session.json) Instagram Reels Yükleyici (instagrapi)
Her postun açıklamasına:
1) Oranların iddaa.com'dan çekildiği saati ve kaynak bilgisini,
2) Zorunlu İddaa / TJK / Milli Piyango bayi kodlarını otomatik ekler.
"""

import datetime
import json
import os
import sys
from pathlib import Path

MANDATORY_DEALER_BLOCK = (
    "İddaa Bayi Kod : 304168\n"
    "Tjk Bayi Kod : 1607\n"
    "Milli Piyango Bayi Kod : 117718"
)


def load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()


def get_fetched_timestamp(base_dir: Path) -> str:
    data_file = base_dir / "default_data.json"
    if data_file.exists():
        try:
            payload = json.loads(data_file.read_text(encoding="utf-8"))
            if payload.get("odds_fetched_at"):
                return str(payload["odds_fetched_at"])
        except Exception:
            pass
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    return datetime.datetime.now(tz_tr).strftime("%d.%m.%Y - %H:%M")


def format_caption(raw_caption: str, base_dir: Path) -> str:
    caption = raw_caption.strip()
    fetched_at = get_fetched_timestamp(base_dir)
    if "sonuç" in caption.lower() or "results" in caption.lower():
        source_line = f"📌 Kaynak: iddaa.com (Bilgilendirme Saati: {fetched_at} TSİ | +18 Sadece bilgilendirme amaçlıdır.)"
    else:
        source_line = (
            f"📌 Kaynak: iddaa.com (Oranların eklendiği saat: {fetched_at} TSİ | "
            f"Oranlar değişiklik gösterebilir. +18 Sadece bilgilendirme amaçlıdır.)"
        )

    parts = [p for p in [caption, source_line] if p]
    if "304168" not in caption:
        parts.append(MANDATORY_DEALER_BLOCK)
    return "\n\n".join(parts)


def upload_reel(video_path: Path, caption: str) -> bool:
    base_dir = Path(__file__).resolve().parent
    load_env(base_dir / ".env")

    username = os.environ.get("IG_USERNAME", "").strip()
    password = os.environ.get("IG_PASSWORD", "").strip()

    if not username or not password or username == "kullanici_adin":
        print(
            f"[BİLGİ] .env dosyasında IG_USERNAME ve IG_PASSWORD henüz girilmemiş.\n"
            f"Lütfen {base_dir / '.env'} dosyasına Instagram kullanıcı adı ve şifrenizi yazın.\n"
            f"Hazır olan Reels videosu: {video_path}"
        )
        return False

    final_caption = format_caption(caption, base_dir)

    from instagrapi import Client

    session_file = base_dir / "ig_session.json"
    cl = Client()
    cl.delay_range = [2, 5]

    if session_file.exists():
        try:
            print("[1/3] Kayıtlı Instagram oturumu (ig_session.json) yükleniyor...")
            cl.load_settings(str(session_file))
            cl.login(username, password)
            cl.get_timeline_feed()
            print("[OK] Mevcut oturum ile güvenli giriş yapıldı.")
        except Exception:
            print("[BİLGİ] Oturum yenileniyor...")
            cl = Client()
            cl.login(username, password)
            cl.dump_settings(str(session_file))
    else:
        print(f"[1/3] @{username} hesabına ilk giriş yapılıyor ve oturum kaydediliyor...")
        cl.login(username, password)
        cl.dump_settings(str(session_file))
        print(f"[OK] Oturum kaydedildi: {session_file}")

    print(f"[2/3] Reels videosu Instagram'a yükleniyor: {video_path.name} ...")
    thumb_path = video_path.with_suffix(".png")
    media = cl.clip_upload(
        path=str(video_path),
        caption=final_caption,
        thumbnail=str(thumb_path) if thumb_path.exists() else None,
    )
    print(f"[3/3] BAŞARILI! Reels paylaşıldı. Media PK: {media.pk}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python upload_instagram.py <video_mp4_yolu> <aciklama_metni>")
        sys.exit(1)

    v_path = Path(sys.argv[1]).resolve()
    cap_text = sys.argv[2]
    if not v_path.exists():
        print(f"[HATA] Video dosyası bulunamadı: {v_path}")
        sys.exit(1)

    upload_reel(v_path, cap_text)
