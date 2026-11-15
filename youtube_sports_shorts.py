"""
%100 Saf Spor Medyası YouTube Shorts Üretim Motoru (youtube_sports_shorts.py)
- Sıfır bahis / iddaa / oran / bayi kodu: Tamamen spor haberciliği, futbol genel kültürü,
  futbolcu biyografisi, son dakika gelişmeleri, maç önü istatistikleri ve maç sonu analizi.
- 6 Kategori (--mode):
  1) headlines  (08:00) -> Günün Spor Manşetleri (Canlı Google News TR Futbol RSS)
  2) biography  (10:45) -> Futbolcu Biyografisi & Kariyer Hikayesi (Gerçek Wikipedia Portresi)
  3) breaking   (13:30) -> Son Dakika Futbol & Transfer Gündemi (Canlı RSS)
  4) trivia     (16:15) -> Futbol Genel Kültürü & İlginç Bilgiler ("Biliyor Muydunuz?")
  5) pre_match  (19:00) -> Maç Önü İstatistikleri & Form Karşılaştırması (Mackolik Resmi Arma + Son 5 Maç)
  6) post_match (22:00) -> Günün Maç Sonu Analizi & Skor Özeti (Mackolik Canlı Skor & Goller)
"""

import argparse
import asyncio
import datetime
import io
import math
import os
import random
import re
import subprocess
import sys
import textwrap
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from auto_manset_reels import (
    ASSETS_DIR,
    BASE_DIR,
    FPS,
    HEADERS,
    HEIGHT,
    LIVEDATA_URL,
    OUTPUT_DIR,
    TURKISH_GIANTS,
    WIDTH,
    fetch_team_crest,
    fetch_team_last_5_matches,
    is_basketball_or_other_sport,
    is_excluded_football_category,
    load_impact_font,
    tr_upper,
)
from motion_reels import ease_out_back, ease_out_cubic, generate_tts, get_audio_duration, load_font
from upload_youtube import upload_short

WIKI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FutbolShortsBot/1.0; +https://github.com/turgayolcu/instagram-futbol-reels)"
}

# Modern Spor Medyası Renk Paleti (Lacivert / Koyu Gece / Kırmızı / Altın Sarısı / Turkuaz)
BG_DARK_TOP = (8, 14, 28)
BG_DARK_BOT = (4, 8, 16)
CARD_NAVY = (14, 24, 46)
CARD_BORDER_GOLD = (245, 195, 45)
ACCENT_RED = (225, 32, 52)
ACCENT_GOLD = (250, 204, 21)
ACCENT_CYAN = (56, 189, 248)
TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (180, 195, 218)

SUBSCRIBE_VOICEOVER = "Güncel futbol haberleri ve analizler için kanala abone olup videoyu beğenmeyi unutmayın!"

# Yıl boyunca tekrar etmeyen Futbolcu Biyografi Kütüphanesi
BIOGRAPHIES: List[Dict[str, str]] = [
    {
        "name": "Arda Güler",
        "wiki_tr": "Arda_Güler",
        "wiki_en": "Arda_Güler",
        "subtitle": "TÜRK FUTBOLUNUN ALTIN ÇOCUĞU",
        "stats": "Mevki: On Numara / Sağ Kanat  •  Kulüp: Real Madrid  •  Milli Takım: Türkiye",
        "fact1": "Gençlerbirliği altyapısında keşfedildi, 16 yaşında Fenerbahçe A takımında asist yaparak tarihe geçti.",
        "fact2": "2023 yazında dünya devi Real Madrid'e imza atarak Şampiyonlar Ligi kupası kazanan ilk Türk futbolcu oldu.",
        "fact3": "EURO 2024'te Gürcistan'a attığı muhteşem uzaktan golle turnuva tarihinin ilk maçında gol atan en genç yıldızı unvanını aldı.",
        "vo": (
            "Futbolcu portresinde bugün: Türk futbolunun altın çocuğu Arda Güler! "
            "Gençlerbirliği altyapısında yetişip henüz on altı yaşında Fenerbahçe formasıyla sahneye çıkan Arda, "
            "kısa sürede Avrupa devlerini peşine taktı ve Real Madrid'e transfer oldu. "
            "İlk sezonunda Şampiyonlar Ligi şampiyonluğu yaşayan genç yıldız, "
            "Avrupa Şampiyonası'nda Gürcistan ağlarına gönderdiği jeneriklik golle adını futbol tarihine altın harflerle yazdırdı! "
            "Peki sizce Arda Güler kariyerinde Ballon d'Or kazanabilir mi? Yorumlara yazın!"
        ),
    },
    {
        "name": "Kenan Yıldız",
        "wiki_tr": "Kenan_Yıldız",
        "wiki_en": "Kenan_Yıldız",
        "subtitle": "JUVENTUS'UN 10 NUMARALI TÜRK YILDIZI",
        "stats": "Mevki: Sol Kanat / Forvet Arkası  •  Kulüp: Juventus  •  Forma: 10",
        "fact1": "Bayern Münih altyapısında 10 yıl eğitim aldıktan sonra İtalyan devi Juventus'a transfer oldu.",
        "fact2": "İdolü Alessandro Del Piero'nun efsanevi 10 numaralı Juventus formasını sırtına geçirdi.",
        "fact3": "Şampiyonlar Ligi'nin yeni formatındaki ilk golü atarak Juventus tarihinin en genç golcüsü rekorunu kırdı.",
        "vo": (
            "Futbolcu biyografisinde bugün: Juventus'un on numaralı Türk yıldızı Kenan Yıldız! "
            "Almanya'da Bayern Münih altyapısında yetişen Kenan, genç yaşta İtalyan devi Juventus'un yolunu tuttu. "
            "Kulüp efsanesi Del Piero'nun mirası olan on numaralı formayı devralan milli yıldızımız, "
            "Şampiyonlar Ligi'nde Juventus formasıyla gol atan en genç futbolcu olarak kulüp rekorunu kırdı! "
            "Kenan Yıldız'ın performansını nasıl buluyorsunuz? Yorumlarda buluşalım!"
        ),
    },
    {
        "name": "Alex de Souza",
        "wiki_tr": "Alex_de_Souza",
        "wiki_en": "Alex_(footballer,_born_1977)",
        "subtitle": "KADIKÖY'ÜN HEYKELİ DİKİLEN EFSANESİ",
        "stats": "Mevki: On Numara  •  Fenerbahçe: 344 Maç, 171 Gol, 146 Asist",
        "fact1": "2004 yılında Fenerbahçe'ye imza attı ve 8 sezonda 3 Süper Lig şampiyonluğu yaşadı.",
        "fact2": "Süper Lig tarihinde gol kralı olan ilk yabancı orta saha oyuncularından biri olarak rekorlar kırdı.",
        "fact3": "Yoğurtçu Parkı'na taraftarlar tarafından heykeli dikilerek Türk futbol tarihinin unutulmazları arasına girdi.",
        "vo": (
            "Efsaneler kuşağında bugün: Doktor lakaplı Alex de Souza! "
            "İki bin dört yılında Brezilya'dan Fenerbahçe'ye gelen Alex, sekiz sezonda çıktığı üç yüz kırk dört maçta "
            "yüz yetmiş bir gol ve yüz kırk altı asist üreterek inanılmaz bir istatistiğe imza attı. "
            "Oyun zekası, frikikleri ve centilmenliğiyle taraflı tarafsız herkesin saygısını kazanan efsanenin "
            "Kadıköy'e heykeli dikildi! Sizin unutamadığınız Alex golü hangisi? Yorumlara yazın!"
        ),
    },
    {
        "name": "Gheorghe Hagi",
        "wiki_tr": "Gheorghe_Hagi",
        "wiki_en": "Gheorghe_Hagi",
        "subtitle": "KARPATLARIN MARADONASI",
        "stats": "Mevki: On Numara  •  Başarı: UEFA Kupası & Süper Kupa (2000)",
        "fact1": "Hem Real Madrid hem Barcelona forması giydikten sonra 1996'da Galatasaray'a transfer oldu.",
        "fact2": "Üst üste 4 Süper Lig şampiyonluğu ve 2000 UEFA Kupası zaferinin başmimarı oldu.",
        "fact3": "Monaco ve Athletic Bilbao'ya attığı efsanevi sol ayak golleri hala hafızalardaki yerini koruyor.",
        "vo": (
            "Futbol efsanelerinde bugün: Karpatların Maradonası Gheorghe Hagi! "
            "Real Madrid ve Barcelona gibi iki devde oynadıktan sonra otuz bir yaşında Galatasaray'a imza atan Hagi, "
            "bitti denilen yaşta Türk futbol tarihini değiştirdi! "
            "Dört lig şampiyonluğunun yanı sıra iki bin yılındaki UEFA Kupası ve Süper Kupa zaferleriyle "
            "unutulmaz bir destan yazdı! Hagi deyince aklınıza gelen ilk an hangisi? Yorumlara bekliyoruz!"
        ),
    },
    {
        "name": "Sergen Yalçın",
        "wiki_tr": "Sergen_Yalçın",
        "wiki_en": "Sergen_Yalçın",
        "subtitle": "TÜRK FUTBOLUNUN SAF YETENEĞİ",
        "stats": "Mevki: On Numara  •  Özellik: Hem Futbolcu Hem Hoca Şampiyonluğu",
        "fact1": "Beşiktaş özkaynak düzeninden çıkıp dört büyüklerin tamamında forma giyen ilk futbolculardan oldu.",
        "fact2": "Chelsea deplasmanında attığı iki golle Beşiktaş'a unutulmaz Londra zaferini getirdi.",
        "fact3": "Hem 100. yılda futbolcu olarak hem 2021'de teknik direktör olarak Beşiktaş'ı şampiyon yaptı.",
        "vo": (
            "Futbolcu hikayelerinde bugün: Türk futbolunun gördüğü en saf yeteneklerden Sergen Yalçın! "
            "Beşiktaş altyapısından yetişen ve sol ayağıyla adeta topa hükmeden Sergen, "
            "Şampiyonlar Ligi'nde Chelsea'ye deplasmanda attığı iki golle Avrupa'yı salladı. "
            "Yüzüncü yılda futbolcu olarak yaşadığı şampiyonluğu, yıllar sonra teknik direktör koltuğunda "
            "çifte kupayla tekrarlayarak adını kulüp tarihine kazıdı!"
        ),
    },
    {
        "name": "Cristiano Ronaldo",
        "wiki_tr": "Cristiano_Ronaldo",
        "wiki_en": "Cristiano_Ronaldo",
        "subtitle": "FUTBOL TARİHİNİN GOL MAKİNESİ",
        "stats": "Ödül: 5 Ballon d'Or  •  5 Şampiyonlar Ligi  •  900+ Resmi Kariyer Golü",
        "fact1": "Madeira adasında mütevazı bir mahalleden çıkıp Sporting altyapısında keşfedildi.",
        "fact2": "Manchester United, Real Madrid ve Juventus formalarıyla kırılmadık gol rekoru bırakmadı.",
        "fact3": "Resmi maçlarda 900 gol barajını aşan futbol tarihindeki ilk oyuncu unvanını elinde tutuyor.",
        "vo": (
            "Futbolcu biyografisinde bugün: Çalışkanlığın ve azmin sembolü Cristiano Ronaldo! "
            "Portekiz'in küçük Madeira adasından çıkıp dünya futbolunun zirvesine tırmanan Ronaldo, "
            "beş Ballon d'Or ve beş Şampiyonlar Ligi kupası kazandı. "
            "Kariyerinde dokuz yüz resmi gol barajını aşan tarihteki ilk futbolcu olan Portekizli efsane, "
            "ilerleyen yaşına rağmen rekorları altüst etmeye devam ediyor!"
        ),
    },
    {
        "name": "Lionel Messi",
        "wiki_tr": "Lionel_Messi",
        "wiki_en": "Lionel_Messi",
        "subtitle": "8 BALLON D'OR VE DÜNYA KUPASI EFSANESİ",
        "stats": "Ödül: 8 Ballon d'Or  •  2022 Dünya Kupası  •  4 Şampiyonlar Ligi",
        "fact1": "Çocuk yaşta büyüme hormonu tedavisi şartıyla peçeteye atılan imzayla Barcelona'ya katıldı.",
        "fact2": "2012 takvim yılında tek başına 91 gol atarak kırılması imkansız bir dünya rekoruna ulaştı.",
        "fact3": "2022 Katar Dünya Kupası'nda Arjantin'i şampiyonluğa taşıyarak koleksiyonundaki son eksik kupayı tamamladı.",
        "vo": (
            "Futbol efsanelerinde bugün: Sekiz Ballon d'Or sahibi Lionel Messi! "
            "Rosario sokaklarından Barcelona'nın La Masia akademisine bir restoran peçetesine atılan imzayla uzanan hikayesinde, "
            "bir takvim yılında doksan bir gol atarak dünya rekoru kırdı. "
            "İki bin yirmi iki Dünya Kupası'nda Arjantin ile zafere ulaşan Messi, "
            "futbol tarihinin en çok kupa kazanan oyuncusu konumunda!"
        ),
    },
    {
        "name": "Hakan Çalhanoğlu",
        "wiki_tr": "Hakan_Çalhanoğlu",
        "wiki_en": "Hakan_Çalhanoğlu",
        "subtitle": "MİLLİ TAKIM KAPTANI VE SERIE A'NIN BEYNİ",
        "stats": "Mevki: Derin Oyun Kurucu  •  Kulüp: Inter  •  Milli Takım Kaptanı",
        "fact1": "Almanya'da başladığı kariyerinde 41 metreden Borussia Dortmund'a attığı frikik golüyle dünyayı hayran bıraktı.",
        "fact2": "Inter'de 6 numara pozisyonuna evrilerek Avrupa'nın en iyi oyun kurucularından birine dönüştü.",
        "fact3": "Yıllar sonra Ballon d'Or aday listesine giren ilk Türk futbolcu olarak göğsümüzü kabarttı.",
        "vo": (
            "Futbolcu portresinde bugün: A Milli Takımımızın kaptanı Hakan Çalhanoğlu! "
            "Kariyerinin başında mesafe tanımaksızın attığı olağanüstü frikik golleriyle ünlenen Hakan, "
            "İtalya'da Inter formasıyla derin oyun kurucu rolünde adeta yeniden doğdu. "
            "Serie A şampiyonluğu ve Şampiyonlar Ligi finalinin ardından Ballon d'Or aday listesine seçilerek "
            "Avrupa'nın en seçkin orta sahaları arasındaki yerini perçinledi!"
        ),
    },
    {
        "name": "Victor Osimhen",
        "wiki_tr": "Victor_Osimhen",
        "wiki_en": "Victor_Osimhen",
        "subtitle": "MASKELİ SÜPER FORVET",
        "stats": "Mevki: Santrfor  •  Başarı: Serie A Gol Kralı & Afrika Yılın Futbolcusu",
        "fact1": "Nijerya'nın Lagos sokaklarında su satarak ailesine destek olduğu zorlu bir çocukluktan zirveye çıktı.",
        "fact2": "Napoli'yi 33 yıl sonra İtalya Serie A şampiyonluğuna taşıyarak gol kralı oldu.",
        "fact3": "Sürpriz Galatasaray transferiyle Süper Lig tarihinin en yüksek piyasa değerli yıldızı olarak büyük yankı uyandırdı.",
        "vo": (
            "Futbolcu hikayelerinde bugün: Maskeli gol makinesi Victor Osimhen! "
            "Lagos sokaklarında zorluklar içinde büyüyen Nijeryalı yıldız, U on yedi Dünya Kupası'nda kırdığı gol rekoruyla Avrupa'ya adım attı. "
            "Napoli'yi otuz üç yıl aradan sonra İtalya şampiyonu yapan ve ikonik yüz maskesiyle tanınan Osimhen, "
            "patlayıcı hızı ve hava hakimiyetiyle dünya futbolunun en korkulan santrforlarından biri!"
        ),
    },
    {
        "name": "Ronaldinho",
        "wiki_tr": "Ronaldinho",
        "wiki_en": "Ronaldinho",
        "subtitle": "FUTBOLU GÜLÜMSETEREK OYNAYAN SİHİRBAZ",
        "stats": "Ödül: Ballon d'Or (2005)  •  Dünya Kupası (2002)  •  Şampiyonlar Ligi (2006)",
        "fact1": "2002 Dünya Kupası'nda İngiltere kalecisi Seaman'ı 35 metreden avlayarak dünyaya adını ezberletti.",
        "fact2": "Santiago Bernabéu deplasmanında Real Madrid taraftarlarının ayakta alkışladığı nadir Barcelona oyuncularından oldu.",
        "fact3": "Yüzünden hiç düşmeyen gülümsemesi ve bilek hareketleriyle bir nesle futbolu sevdirdi.",
        "vo": (
            "Efsaneler kuşağında bugün: Futbolun gülen yüzü Ronaldinho! "
            "Porto Alegre sokaklarından Dünya Kupası ve Şampiyonlar Ligi zirvesine uzanan kariyerinde, "
            "top ayağına geldiğinde zamanı durduran çalımlarıyla milyonları ekran başına kilitledi. "
            "Ezeli rakip Real Madrid taraftarlarına bile Bernabeu'da kendini ayakta alkışlatan Brezilyalı sihirbaz, "
            "futbol tarihinin en estetik efsanesi olarak anılıyor!"
        ),
    },
    {
        "name": "Zinedine Zidane",
        "wiki_tr": "Zinedine_Zidane",
        "wiki_en": "Zinedine_Zidane",
        "subtitle": "ZARAFETİN VE FİNALLERİN USTASI",
        "stats": "Ödül: Ballon d'Or (1998)  •  TD Rekoru: Üst Üste 3 Şampiyonlar Ligi",
        "fact1": "1998 Dünya Kupası finalinde Brezilya'ya iki kafa golü atarak Fransa'ya tarihinin ilk kupasını getirdi.",
        "fact2": "2002 Şampiyonlar Ligi finalinde Leverkusen'e attığı sol ayak vole golü turnuva tarihinin en ikonik golü seçildi.",
        "fact3": "Teknik direktör olarak Real Madrid'i üst üste 3 kez Şampiyonlar Ligi şampiyonu yapan ilk isim oldu.",
        "vo": (
            "Futbol efsanelerinde bugün: Orta sahanın maestrosu Zinedine Zidane! "
            "Marsilya göçmeni bir ailenin çocuğu olarak başladığı yolculukta hem Dünya Kupası hem Avrupa Şampiyonası'nı kaldırdı. "
            "Şampiyonlar Ligi finalindeki unutulmaz vole golünün ardından, teknik direktör koltuğunda da "
            "üst üste üç Şampiyonlar Ligi kazanarak erişilmesi güç bir rekora imza attı!"
        ),
    },
    {
        "name": "Kylian Mbappé",
        "wiki_tr": "Kylian_Mbappé",
        "wiki_en": "Kylian_Mbappé",
        "subtitle": "DÜNYA KUPASI FİNALLERİNİN REKORTMENİ",
        "stats": "Başarı: 2018 Dünya Kupası  •  2022 Finalinde Hat-Trick  •  Real Madrid",
        "fact1": "Henüz 19 yaşındayken Pelé'den sonra Dünya Kupası finalinde gol atan en genç futbolcu oldu.",
        "fact2": "2022 Dünya Kupası finalinde hat-trick yaparak 1966'dan beri bunu başaran ilk oyuncu unvanını aldı.",
        "fact3": "PSG tarihinin en golcü oyuncusu olduktan sonra çocukluk hayali Real Madrid'e transfer oldu.",
        "vo": (
            "Futbolcu biyografisinde bugün: Rüzgarın oğlu Kylian Mbappe! "
            "Henüz on dokuz yaşında Fransa ile Dünya Kupası kaldırarak Pele'nin rekorlarına ortak olan Mbappe, "
            "iki bin yirmi iki Dünya Kupası finalinde yaptığı hat-trick ile tarihe geçti. "
            "Paris Saint Germain tarihinin en golcü ismi olduktan sonra çocukluk hayali Real Madrid formasını sırtına geçirdi!"
        ),
    },
]

# Futbol Genel Kültürü & İlginç Bilgiler Kütüphanesi
TRIVIA_ITEMS: List[Dict[str, str]] = [
    {
        "headline": "BİR MAÇTA 3 SARI KART GÖREN FUTBOLCU!",
        "wiki_en": "Josip_Šimunić",
        "badge": "DÜNYA KUPASI TARİHİ",
        "body1": "2006 Dünya Kupası'ndaki Hırvatistan - Avustralya maçında hakem Graham Poll inanılmaz bir kural hatasına imza attı.",
        "body2": "Hırvat savunmacı Josip Šimunić 61. ve 90. dakikalarda iki sarı kart görmesine rağmen hakem kırmızı kart çıkarmayı unuttu!",
        "body3": "Šimunić ancak 90+3. dakikada gördüğü ÜÇÜNCÜ sarı karttan sonra oyundan atıldı ve bu olay hakem Poll'ün Dünya Kupası kariyerini bitirdi.",
        "vo": (
            "Futbol genel kültüründe bugün: Bir Dünya Kupası maçında tam üç sarı kart gören futbolcuyu biliyor muydunuz? "
            "İki bin altı Dünya Kupası'nda oynanan Hırvatistan Avustralya karşılaşmasında İngiliz hakem Graham Poll, "
            "Hırvat stoper Josip Şimuniç'e altmış birinci ve doksanıncı dakikalarda iki sarı kart gösterdi ancak kırmızı kart çıkarmayı unuttu! "
            "Oyunda kalmaya devam eden Şimuniç, uzatmalarda üçüncü sarı kartını görünce nihayet kırmızı kartla oyun dışı kaldı!"
        ),
    },
    {
        "headline": "KALECİ OLARAK 131 GOL ATAN EFSANE!",
        "wiki_en": "Rogério_Ceni",
        "badge": "KIRILAMAZ REKOR",
        "body1": "Brezilyalı efsane kaleci Rogério Ceni, tüm kariyerini São Paulo kulübünde geçirerek 1200'den fazla maça çıktı.",
        "body2": "Takımının frikik ve penaltı ustası olan Ceni, kariyeri boyunca rakip ağlara tam 131 resmi gol gönderdi!",
        "body3": "Bu gollerin 61 tanesini doğrudan serbest vuruştan atarak çoğu forvetin bile ulaşamadığı bir Guinness rekoru kırdı.",
        "vo": (
            "Biliyor muydunuz? Futbol tarihinde yüz otuz bir gol atan bir kaleci var! "
            "Brezilya'nın Sao Paulo kulübüyle özdeşleşen efsane eldiven Rojeryo Seni, "
            "kalesini korumakla yetinmeyip takımının tüm frikik ve penaltılarını kullandı. "
            "Altmış biri doğrudan frikikten olmak üzere toplam yüz otuz bir resmi gol atan Seni, "
            "futbol tarihinin açık ara en golcü kalecisi rekorunu elinde tutuyor!"
        ),
    },
    {
        "headline": "SARI VE KIRMIZI KART TRAFİK IŞIĞINDAN DOĞDU!",
        "wiki_en": "Ken_Aston",
        "badge": "FUTBOLUN İCATLARI",
        "body1": "1966 Dünya Kupası'na kadar futbolda kart yoktu; hakemler cezayı sözlü söylüyor ancak dil farkı yüzünden kaos çıkıyordu.",
        "body2": "İngiltere - Arjantin maçındaki kargaşadan sonra hakem komitesi başkanı Ken Aston, Londra'da kırmızı ışıkta dururken ilham aldı!",
        "body3": "Sarı 'dikkat et', kırmızı 'dur ve çık' anlamına gelen kart sistemi ilk kez 1970 Meksika Dünya Kupası'nda uygulandı.",
        "vo": (
            "Futbolda sarı ve kırmızı kartların bir trafik ışığında icat edildiğini biliyor muydunuz? "
            "Bin dokuz yüz altmış altı Dünya Kupası'na kadar futbolda kart kullanılmıyor ve farklı dilleri konuşan oyuncular hakemi anlamıyordu. "
            "İngiliz hakem Ken Aston, Londra'da arabasıyla trafik ışığında beklerken sarı ve kırmızı renklerin evrensel bir dil olduğunu fark etti "
            "ve bin dokuz yüz yetmiş Dünya Kupası'yla birlikte kart sistemi futbolun değişmez kuralı oldu!"
        ),
    },
    {
        "headline": "ÇALINAN DÜNYA KUPASINI BULAN KÖPEK: PICKLES!",
        "wiki_en": "Pickles_(dog)",
        "badge": "İNANILMAZ OLAY",
        "body1": "1966 İngiltere Dünya Kupası başlamadan sadece 4 ay önce Londra'da sergilenen altın Jules Rimet kupası çalındı!",
        "body2": "Tüm İngiliz polisi seferber olsa da kupayı bulamadı; ta ki 7 gün sonra Pickles adlı bir köpek parkta yürüyüşe çıkana kadar.",
        "body3": "Çalıların arasında gazeteye sarılı altın kupayı koklayarak bulan Pickles milli kahraman ilan edildi ve şampiyonluk yemeğine davet edildi!",
        "vo": (
            "Çalınan Dünya Kupası'nı bir sokak yürüyüşünde bir köpeğin bulduğunu biliyor muydunuz? "
            "Bin dokuz yüz altmış altı Dünya Kupası'ndan dört ay önce Londra'da sergilenen altın kupa gizemli şekilde çalındı. "
            "Scotland Yard dedektifleri kupayı her yerde ararken, yedi gün sonra Pickles adındaki sevimli bir köpek "
            "bahçedeki çalıların altında gazeteye sarılı kupayı koklayarak buldu ve İngiltere'de milli kahraman ilan edildi!"
        ),
    },
    {
        "headline": "ŞAMPİYONLAR LİGİ MARŞININ ARKASINDAKİ SIR!",
        "wiki_en": "UEFA_Champions_League_anthem",
        "badge": "DEVLER LİGİ KÜLTÜRÜ",
        "body1": "Tüyleri diken diken eden Şampiyonlar Ligi müziği 1992 yılında İngiliz besteci Tony Britten tarafından uyarlandı.",
        "body2": "Eser aslında 1727 yılında ünlü besteci Handel'in İngiltere Kralı II. George'un taç giyme töreni için yazdığı marşa dayanıyor!",
        "body3": "Sözleri İngilizce, Fransızca ve Almanca olmak üzere üç dilde yazılan marşın nakaratında 'En iyiler, şampiyonlar!' deniyor.",
        "vo": (
            "Her futbolseverin tüylerini diken diken eden Şampiyonlar Ligi müziğinin neredeyse üç yüz yıllık bir kraliyet marşı olduğunu biliyor muydunuz? "
            "Bin dokuz yüz doksan ikide besteci Tony Britten tarafından uyarlanan bu efsanevi eser, "
            "aslında bin yedi yüz yirmi yedide İngiltere kralının taç giyme töreni için bestelenmişti! "
            "Sözleri ise UEFA'nın üç resmi dili olan İngilizce, Fransızca ve Almanca olarak seslendiriliyor!"
        ),
    },
    {
        "headline": "BALLON D'OR KAZANAN TEK KALECİ: LEV YAŞİN!",
        "wiki_en": "Lev_Yashin",
        "badge": "KARA ÖRÜMCEK",
        "body1": "1956'dan bu yana verilen Ballon d'Or ödülünü futbol tarihinde kazanabilen yalnızca TEK BİR kaleci vardır: Lev Yaşin!",
        "body2": "Baştan aşağı siyah forma giydiği için 'Kara Örümcek' lakabını alan Yaşin, kariyerinde 150'den fazla penaltı kurtardı.",
        "body3": "1963 yılında altın topu kazanan efsanenin anısına bugün yılın en iyi kalecisine 'Yaşin Ödülü' verilmektedir.",
        "vo": (
            "Futbol tarihinde Ballon d'Or ödülünü kazanabilen tek kalecinin kim olduğunu biliyor muydunuz? "
            "Tamamen siyah forması ve insanüstü refleksleriyle Kara Örümcek lakabını alan efsane eldiven Lev Yaşin, "
            "kariyeri boyunca yüz elliden fazla penaltı kurtardı ve bin dokuz yüz altmış üç yılında Ballon d'Or kazanarak "
            "bugüne kadar hiçbir kalecinin tekrarlayamadığı bir tarihe imza attı!"
        ),
    },
    {
        "headline": "149 - 0 BİTEN FUTBOL TARİHİNİN EN FARKLI MAÇI!",
        "wiki_en": "AS_Adema_149–0_SO_l'Emyrne",
        "badge": "GUINNESS REKORU",
        "body1": "2002 yılında Madagaskar Ligi'nde oynanan AS Adema - SO l'Emyrne maçı Guinness Rekorlar Kitabı'na geçti.",
        "body2": "Bir önceki maçtaki hakem kararlarını protesto eden konuk takım oyuncuları, santradan itibaren kendi kalelerine gol atmaya başladı!",
        "body3": "Rakip takım topa bile dokunmadan maç 149-0 sona erdi ve ortalama her 36 saniyede bir gol kaydedildi.",
        "vo": (
            "Futbol tarihinin en farklı resmi maçının yüz kırk dokuz sıfır bittiğini biliyor muydunuz? "
            "İki bin iki yılında Madagaskar liginde oynanan karşılaşmada, hakem kararlarını protesto eden konuk ekip oyuncuları "
            "başlama vuruşundan itibaren topu sürekli kendi ağlarına gönderdi! "
            "Ortalama her otuz altı saniyede bir golün olduğu mücadele yüz kırk dokuz sıfırlık skorla dünya rekorlar kitabına girdi!"
        ),
    },
    {
        "headline": "NUMARASIZ FORMADAN 1-11 KURALINA GEÇİŞ!",
        "wiki_en": "Squad_number_(association_football)",
        "badge": "FUTBOL TARİHİ",
        "body1": "Futbolun ilk 60 yılında formaların arkasında numara yoktu; ilk numaralı formalar 1928'de Arsenal ve Chelsea maçlarında denendi.",
        "body2": "Uzun yıllar ilk 11 oyuncuları sahadaki dizilişe göre 1'den 11'e kadar numara giymek zorundaydı; bu yüzden oyun kuruculara '10 numara' dendi!",
        "body3": "Sabit oyuncu numarası ve sırtta isim yazılması ise ancak 1993 yılında Premier Lig ve Dünya Kupası ile kalıcı hale geldi.",
        "vo": (
            "Futbolda oyun kuruculara neden on numara, golcülere neden dokuz numara dendiğini hiç düşündünüz mü? "
            "Yıllar boyunca takımlar sahaya birden on bire kadar diziliş sırasına göre numaralandırılmış formalarla çıkıyordu "
            "ve forvet arkası pozisyonu her zaman on numaraya denk geliyordu! "
            "Futbolcuların arkasında kendi isimlerinin ve sabit numaralarının yazması ise ancak doksanlı yıllarda kalıcı hale geldi!"
        ),
    },
]


def fetch_wiki_image(wiki_title: str, lang: str = "tr") -> Optional[Image.Image]:
    """
    Wikipedia REST API'den ilgili kişi/konunun yüksek çözünürlüklü gerçek fotoğrafını çeker.
    """
    if not wiki_title:
        return None
    for lg in ([lang, "en"] if lang != "en" else ["en", "tr"]):
        try:
            enc = urllib.parse.quote(wiki_title.replace(" ", "_"))
            url = f"https://{lg}.wikipedia.org/api/rest_v1/page/summary/{enc}"
            r = requests.get(url, headers=WIKI_HEADERS, timeout=8)
            if r.status_code != 200:
                continue
            data = r.json()
            candidates = [
                data.get("originalimage", {}).get("source"),
                data.get("thumbnail", {}).get("source"),
            ]
            for img_url in candidates:
                if not img_url or img_url.lower().endswith(".svg"):
                    continue
                ir = requests.get(img_url, headers=WIKI_HEADERS, timeout=10)
                if ir.status_code == 200 and len(ir.content) > 1500:
                    return Image.open(io.BytesIO(ir.content)).convert("RGB")
        except Exception:
            continue
    fallback = ASSETS_DIR / "kadikoy_stadium.jpg"
    if fallback.exists():
        try:
            return Image.open(fallback).convert("RGB")
        except Exception:
            pass
    return None


def fetch_google_football_rss(query: str = '"Süper Lig" OR "Milli Takım" OR "Şampiyonlar Ligi" OR futbol when:1d') -> List[Dict[str, str]]:
    """
    Google News Türkiye üzerinden en güncel futbol haber başlıklarını çeker (bahis/basketbol/voleybol kelimelerini filtreler).
    """
    encoded_q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=tr&gl=TR&ceid=TR:tr"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        root = ET.fromstring(r.content)
        items = []
        banned_kw = [
            "iddaa", "bahis", "kupon", "oran", "voleybol", "basketbol", "euroleague", "nba", "tenis",
            "medicana", "madeş", "opet", "beko", "mct", "daikin", "eczacıbaşı", "vakıfbank",
            "anadolu efes", "sultanlar", "efeler", "filede", "parkede", "potada", "set ",
            "kadın futbol", "arsavev", "fomget", "alg spor", "u19", "u17",
        ]
        seen_prefixes = set()
        for item in root.findall(".//item"):
            raw_title = (item.findtext("title") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            if not raw_title:
                continue
            # Kaynak adını ayır ("Başlık - Fanatik" -> title="Başlık", source="Fanatik")
            if " - " in raw_title:
                headline, source = raw_title.rsplit(" - ", 1)
            else:
                headline, source = raw_title, "Spor Gündemi"
            headline = headline.strip()
            if any(b in headline.lower() for b in banned_kw):
                continue
            if len(headline) < 18:
                continue
            prefix = headline.lower()[:28]
            if prefix in seen_prefixes:
                continue
            seen_prefixes.add(prefix)
            items.append({
                "headline": headline,
                "source": source.strip(),
                "pub_date": pub_date,
            })
        return items
    except Exception as e:
        print(f"[UYARI] RSS çekilemedi: {e}")
        return []


def detect_subject_photo(text: str) -> Optional[Image.Image]:
    """
    Haber metninde geçen futbolcu veya kulübü tespit edip gerçek Wikipedia/arma görselini getirir.
    """
    keyword_to_wiki = [
        ("Arda Güler", "Arda_Güler"),
        ("Kenan Yıldız", "Kenan_Yıldız"),
        ("Hakan Çalhanoğlu", "Hakan_Çalhanoğlu"),
        ("Osimhen", "Victor_Osimhen"),
        ("Icardi", "Mauro_Icardi"),
        ("Mourinho", "José_Mourinho"),
        ("Okan Buruk", "Okan_Buruk"),
        ("Immobile", "Ciro_Immobile"),
        ("Rafa Silva", "Rafa_Silva"),
        ("Dzeko", "Edin_Džeko"),
        ("Tadic", "Dušan_Tadić"),
        ("En-Nesyri", "Youssef_En-Nesyri"),
        ("Muslera", "Fernando_Muslera"),
        ("Barış Alper", "Barış_Alper_Yılmaz"),
        ("Kerem Aktürkoğlu", "Kerem_Aktürkoğlu"),
        ("Ferdi Kadıoğlu", "Ferdi_Kadıoğlu"),
        ("Montella", "Vincenzo_Montella"),
        ("Ronaldo", "Cristiano_Ronaldo"),
        ("Messi", "Lionel_Messi"),
        ("Mbappe", "Kylian_Mbappé"),
        ("Mbappé", "Kylian_Mbappé"),
        ("Haaland", "Erling_Haaland"),
        ("Ancelotti", "Carlo_Ancelotti"),
        ("Guardiola", "Pep_Guardiola"),
        ("Salah", "Mohamed_Salah"),
        ("Galatasaray", "RAMS_Park"),
        ("Fenerbahçe", "Fenerbahçe_Şükrü_Saracoğlu_Stadyumu"),
        ("Beşiktaş", "Beşiktaş_Park"),
        ("Trabzonspor", "Şenol_Güneş_Spor_Kompleksi"),
        ("Milli Takım", "Türkiye_millî_futbol_takımı"),
    ]
    t_low = text.lower()
    for kw, wiki_key in keyword_to_wiki:
        if kw.lower() in t_low:
            img = fetch_wiki_image(wiki_key, lang="tr")
            if img is not None:
                return img
    return None


def build_broadcast_background(hero_photo: Optional[Image.Image] = None, accent: Tuple[int, int, int] = ACCENT_RED) -> Image.Image:
    """
    Modern Spor TV dikey 9:16 arka planı oluşturur (üstte stadyum/fotoğraf atmosferi + koyu lacivert yayın gradyanı).
    """
    bg = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK_BOT)
    draw = ImageDraw.Draw(bg)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG_DARK_TOP[0] * (1 - ratio) + BG_DARK_BOT[0] * ratio)
        g = int(BG_DARK_TOP[1] * (1 - ratio) + BG_DARK_BOT[1] * ratio)
        b = int(BG_DARK_TOP[2] * (1 - ratio) + BG_DARK_BOT[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    if hero_photo is not None:
        # Arka plana hafif bulanık atmosferik yansıma ekle
        blurred = hero_photo.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(radius=32))
        bg = Image.blend(bg, blurred, 0.22)

    # Üst Yayın Bandı (Header)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 0, WIDTH, 145], fill=(6, 12, 24, 235))
    od.rectangle([0, 142, WIDTH, 148], fill=(accent[0], accent[1], accent[2], 255))
    # Alt Yayın Bandı (Footer)
    od.rectangle([0, HEIGHT - 76, WIDTH, HEIGHT], fill=(6, 12, 24, 240))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    return bg


def draw_top_masthead(draw: ImageDraw.ImageDraw, category_label: str, accent: Tuple[int, int, int] = ACCENT_RED) -> None:
    # Sol: Kategori Etiketi
    f_cat = load_font(26, True)
    ctb = draw.textbbox((0, 0), category_label, font=f_cat)
    cw = ctb[2] - ctb[0] + 44
    draw.rounded_rectangle([48, 44, 48 + cw, 102], radius=12, fill=accent)
    draw.text((70, 56), category_label, font=f_cat, fill=TEXT_WHITE)

    # Sağ: Tarih & Spor Ekranı
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    now_str = datetime.datetime.now(tz_tr).strftime("%d.%m.%Y")
    f_date = load_font(25, True)
    right_txt = f"FUTBOL GÜNDEMİ  •  {now_str}"
    rtb = draw.textbbox((0, 0), right_txt, font=f_date)
    draw.text((WIDTH - 48 - (rtb[2] - rtb[0]), 57), right_txt, font=f_date, fill=ACCENT_GOLD)

    # Alt Footer Yazısı
    f_foot = load_font(23, True)
    ftxt = "GÜNCEL FUTBOL HABERLERİ & ANALİZ  •  ABONE OLMAYI UNUTMAYIN"
    ftb = draw.textbbox((0, 0), ftxt, font=f_foot)
    draw.text(((WIDTH - (ftb[2] - ftb[0])) // 2, HEIGHT - 52), ftxt, font=f_foot, fill=TEXT_MUTED)


def paste_hero_photo_card(base_img: Image.Image, photo: Image.Image, box: Tuple[int, int, int, int], border_col: Tuple[int, int, int] = ACCENT_GOLD) -> None:
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    pw, ph = photo.size
    # Yüz/portre üst kısmı kesilmesin diye dikeyde üst-%15 odaklı crop (center-top crop)
    scale = max(bw / max(1, pw), bh / max(1, ph))
    nw, nh = int(pw * scale), int(ph * scale)
    resized = photo.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = (nw - bw) // 2
    oy = max(0, int((nh - bh) * 0.16))
    cropped = resized.crop((ox, oy, ox + bw, oy + bh))
    cropped = ImageEnhance.Contrast(cropped).enhance(1.08)

    # Yuvarlatılmış maske
    mask = Image.new("L", (bw, bh), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, bw, bh], radius=26, fill=255)
    base_img.paste(cropped, (x1, y1), mask)

    d = ImageDraw.Draw(base_img)
    d.rounded_rectangle([x1, y1, x2, y2], radius=26, outline=border_col, width=4)


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int] = TEXT_WHITE,
    line_spacing: int = 10,
    center: bool = False,
) -> int:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        tb = draw.textbbox((0, 0), test, font=font)
        if tb[2] - tb[0] <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    cur_y = y
    for ln in lines:
        tb = draw.textbbox((0, 0), ln, font=font)
        lw = tb[2] - tb[0]
        lh = tb[3] - tb[1]
        dx = x + (max_width - lw) // 2 if center else x
        draw.text((dx, cur_y), ln, font=font, fill=fill)
        cur_y += lh + line_spacing
    return cur_y


def build_headlines_short() -> Tuple[Path, str, str]:
    """1) Sabah 08:00 - Günün Spor Manşetleri"""
    items = fetch_google_football_rss()
    if len(items) < 3:
        items = [
            {"headline": "Süper Lig devlerinde kritik hafta mesaisi başladı", "source": "Spor Gündemi"},
            {"headline": "Avrupa kupalarında temsilcilerimizin maç programı netleşti", "source": "Futbol Ekranı"},
            {"headline": "A Milli Futbol Takımımızda aday kadro heyecanı yaşanıyor", "source": "Milli Gündem"},
        ]

    lead = items[0]
    sub1 = items[1]
    sub2 = items[2]

    photo = detect_subject_photo(lead["headline"]) or detect_subject_photo(sub1["headline"])
    if photo is None:
        photo = fetch_wiki_image("UEFA_Champions_League", lang="en")

    img = build_broadcast_background(photo, accent=ACCENT_RED)
    if photo is not None:
        paste_hero_photo_card(img, photo, (48, 180, WIDTH - 48, 790), border_col=ACCENT_GOLD)
    draw = ImageDraw.Draw(img)
    draw_top_masthead(draw, "GÜNÜN SPOR MANŞETLERİ", accent=ACCENT_RED)

    # Ana Manşet Kartı
    draw.rounded_rectangle([48, 820, WIDTH - 48, 1185], radius=24, fill=CARD_NAVY, outline=ACCENT_GOLD, width=3)
    draw.rounded_rectangle([74, 844, 330, 892], radius=10, fill=ACCENT_RED)
    draw.text((92, 852), "GÜNÜN 1 NUMARASI", font=load_font(22, True), fill=TEXT_WHITE)
    draw_wrapped_text(
        draw,
        tr_upper(lead["headline"]),
        76,
        914,
        WIDTH - 152,
        load_impact_font(52),
        fill=ACCENT_GOLD,
        line_spacing=10,
    )

    # Alt 2 Manşet Kartı
    for idx, sub in enumerate([sub1, sub2]):
        sy1 = 1215 + idx * 285
        sy2 = sy1 + 260
        draw.rounded_rectangle([48, sy1, WIDTH - 48, sy2], radius=22, fill=(12, 22, 42), outline=(45, 75, 120), width=2)
        draw.rounded_rectangle([74, sy1 + 22, 265, sy1 + 66], radius=8, fill=(28, 52, 95))
        draw.text((90, sy1 + 30), f"MANŞET #{idx + 2}", font=load_font(21, True), fill=ACCENT_CYAN)
        draw_wrapped_text(
            draw,
            sub["headline"],
            76,
            sy1 + 84,
            WIDTH - 152,
            load_font(33, True),
            fill=TEXT_WHITE,
            line_spacing=8,
        )

    poster_path = ASSETS_DIR / "yt_headlines_poster.jpg"
    img.save(poster_path, quality=95)

    vo = (
        f"Günün öne çıkan spor manşetleriyle karşınızdayız! "
        f"Günün ilk manşetinde: {lead['headline']}. "
        f"Gündemin ikinci önemli gelişmesi: {sub1['headline']}. "
        f"Ve üçüncü başlığımızda: {sub2['headline']}. "
        f"Günün tüm sıcak gelişmeleri için takipte kalın!"
    )
    caption = (
        f"📰 GÜNÜN SPOR MANŞETLERİ: {lead['headline']}! ⚽🔥\n\n"
        f"🔹 {lead['headline']}\n"
        f"🔹 {sub1['headline']}\n"
        f"🔹 {sub2['headline']}\n\n"
        f"💬 Gündemdeki gelişmeler hakkında ne düşünüyorsunuz? Yorumlarda buluşalım!"
    )
    return poster_path, vo, caption


def build_biography_short(target_date: datetime.date) -> Tuple[Path, str, str]:
    """2) 10:45 - Futbolcu Biyografisi"""
    day_idx = (target_date.toordinal() + 3) % len(BIOGRAPHIES)
    bio = BIOGRAPHIES[day_idx]
    photo = fetch_wiki_image(bio["wiki_tr"], lang="tr") or fetch_wiki_image(bio["wiki_en"], lang="en")

    img = build_broadcast_background(photo, accent=ACCENT_GOLD)
    if photo is not None:
        paste_hero_photo_card(img, photo, (48, 175, WIDTH - 48, 880), border_col=ACCENT_GOLD)
    draw = ImageDraw.Draw(img)
    draw_top_masthead(draw, "FUTBOLCU BİYOGRAFİSİ", accent=(195, 135, 10))

    # İsim & Unvan Bandı
    draw.rounded_rectangle([48, 902, WIDTH - 48, 1092], radius=22, fill=CARD_NAVY, outline=ACCENT_GOLD, width=3)
    f_name = load_impact_font(76)
    ntb = draw.textbbox((0, 0), tr_upper(bio["name"]), font=f_name)
    draw.text(((WIDTH - (ntb[2] - ntb[0])) // 2, 916), tr_upper(bio["name"]), font=f_name, fill=TEXT_WHITE)

    f_sub = load_font(27, True)
    stb = draw.textbbox((0, 0), bio["subtitle"], font=f_sub)
    draw.text(((WIDTH - (stb[2] - stb[0])) // 2, 1012), bio["subtitle"], font=f_sub, fill=ACCENT_GOLD)

    # 3 Kariyer Notu Kartı
    facts = [bio["fact1"], bio["fact2"], bio["fact3"]]
    for idx, fc in enumerate(facts):
        fy1 = 1116 + idx * 222
        fy2 = fy1 + 202
        draw.rounded_rectangle([48, fy1, WIDTH - 48, fy2], radius=20, fill=(11, 20, 38), outline=(50, 82, 132), width=2)
        draw.ellipse([70, fy1 + 26, 114, fy1 + 70], fill=ACCENT_GOLD)
        draw.text((84, fy1 + 30), str(idx + 1), font=load_font(26, True), fill=(10, 16, 28))
        draw_wrapped_text(draw, fc, 134, fy1 + 26, WIDTH - 204, load_font(28, True), fill=TEXT_WHITE, line_spacing=7)

    poster_path = ASSETS_DIR / "yt_biography_poster.jpg"
    img.save(poster_path, quality=95)

    caption = (
        f"⭐ EFSANE PORTRE: {bio['name']} Hikayesi! ⚽👑\n\n"
        f"📌 {bio['subtitle']}\n"
        f"🔹 {bio['fact1']}\n"
        f"🔹 {bio['fact2']}\n"
        f"🔹 {bio['fact3']}\n\n"
        f"💬 Sıradaki videoda hangi futbolcunun hikayesini görmek istersiniz? Yorumlara yazın!"
    )
    return poster_path, bio["vo"], caption


def build_breaking_short() -> Tuple[Path, str, str]:
    """3) 13:30 - Son Dakika Futbol & Transfer Gelişmesi"""
    items = fetch_google_football_rss('transfer OR "son dakika" OR Galatasaray OR Fenerbahçe OR Beşiktaş OR "Süper Lig" when:12h')
    if not items:
        items = fetch_google_football_rss()
    story = items[min(3, len(items) - 1)] if items else {
        "headline": "Avrupa ve Süper Lig'de transfer gündemi hareketlendi!",
        "source": "Futbol Ekranı",
    }
    extra = items[min(4, len(items) - 1)] if len(items) > 4 else None

    photo = detect_subject_photo(story["headline"]) or fetch_wiki_image("Association_football", lang="en")
    img = build_broadcast_background(photo, accent=ACCENT_RED)
    if photo is not None:
        paste_hero_photo_card(img, photo, (48, 180, WIDTH - 48, 860), border_col=ACCENT_RED)
    draw = ImageDraw.Draw(img)
    draw_top_masthead(draw, "SON DAKİKA GELİŞMESİ", accent=ACCENT_RED)

    # Kırmızı SON DAKİKA Kuşağı
    draw.rounded_rectangle([48, 890, WIDTH - 48, 1005], radius=18, fill=ACCENT_RED)
    sd_txt = "SICAK GELİŞME  •  FUTBOL GÜNDEMİ"
    f_sd = load_impact_font(54)
    sdtb = draw.textbbox((0, 0), sd_txt, font=f_sd)
    draw.text(((WIDTH - (sdtb[2] - sdtb[0])) // 2, 916), sd_txt, font=f_sd, fill=TEXT_WHITE)

    # Ana Son Dakika Kartı
    draw.rounded_rectangle([48, 1030, WIDTH - 48, 1500], radius=24, fill=CARD_NAVY, outline=ACCENT_GOLD, width=3)
    draw_wrapped_text(
        draw,
        tr_upper(story["headline"]),
        80,
        1075,
        WIDTH - 160,
        load_impact_font(62),
        fill=TEXT_WHITE,
        line_spacing=14,
        center=True,
    )
    src_txt = f"Kaynak: {story['source']}"
    f_src = load_font(26, True)
    stb = draw.textbbox((0, 0), src_txt, font=f_src)
    draw.text(((WIDTH - (stb[2] - stb[0])) // 2, 1430), src_txt, font=f_src, fill=ACCENT_GOLD)

    if extra and extra["headline"] != story["headline"]:
        draw.rounded_rectangle([48, 1530, WIDTH - 48, 1795], radius=20, fill=(11, 20, 38), outline=(56, 189, 248), width=2)
        draw.text((76, 1554), "GÜNDEMDEN DİĞER NOT:", font=load_font(24, True), fill=ACCENT_CYAN)
        draw_wrapped_text(draw, extra["headline"], 76, 1600, WIDTH - 152, load_font(32, True), fill=TEXT_WHITE, line_spacing=8)

    poster_path = ASSETS_DIR / "yt_breaking_poster.jpg"
    img.save(poster_path, quality=95)

    vo = (
        f"Futbol gündeminden sıcak gelişme! {story['headline']}! "
        + (f"Öte yandan gündemdeki bir diğer gelişmede ise {extra['headline']}. " if extra else "")
        + "Siz bu gelişmeyi nasıl değerlendiriyorsunuz? Görüşlerinizi yorumlara bekliyoruz!"
    )
    caption = (
        f"🚨 SON DAKİKA: {story['headline']}! ⚽🔥\n\n"
        f"📰 Futbol gündemindeki en sıcak gelişmeler anbean ekranınızda!\n\n"
        f"💬 Siz bu gelişme hakkında ne düşünüyorsunuz? Yorumlara yazın!"
    )
    return poster_path, vo, caption


def build_trivia_short(target_date: datetime.date) -> Tuple[Path, str, str]:
    """4) 16:15 - Futbol Genel Kültürü & İlginç Bilgiler"""
    t_idx = (target_date.toordinal() + 5) % len(TRIVIA_ITEMS)
    trv = TRIVIA_ITEMS[t_idx]
    photo = fetch_wiki_image(trv["wiki_en"], lang="en")

    img = build_broadcast_background(photo, accent=ACCENT_CYAN)
    if photo is not None:
        paste_hero_photo_card(img, photo, (48, 180, WIDTH - 48, 825), border_col=ACCENT_CYAN)
    draw = ImageDraw.Draw(img)
    draw_top_masthead(draw, "BİLİYOR MUYDUNUZ?", accent=(14, 116, 175))

    # Manşet Bandı
    draw.rounded_rectangle([48, 852, WIDTH - 48, 1085], radius=22, fill=CARD_NAVY, outline=ACCENT_GOLD, width=3)
    draw_wrapped_text(
        draw,
        trv["headline"],
        76,
        882,
        WIDTH - 152,
        load_impact_font(56),
        fill=ACCENT_GOLD,
        line_spacing=10,
        center=True,
    )

    # 3 Hikaye Paragrafı
    for idx, btxt in enumerate([trv["body1"], trv["body2"], trv["body3"]]):
        by1 = 1112 + idx * 226
        by2 = by1 + 206
        draw.rounded_rectangle([48, by1, WIDTH - 48, by2], radius=20, fill=(11, 20, 38), outline=(56, 189, 248), width=2)
        draw_wrapped_text(draw, btxt, 76, by1 + 28, WIDTH - 152, load_font(29, True), fill=TEXT_WHITE, line_spacing=8)

    poster_path = ASSETS_DIR / "yt_trivia_poster.jpg"
    img.save(poster_path, quality=95)

    caption = (
        f"🧠 FUTBOL GENEL KÜLTÜRÜ: {trv['headline']} ⚽😲\n\n"
        f"🔹 {trv['body1']}\n"
        f"🔹 {trv['body2']}\n"
        f"🔹 {trv['body3']}\n\n"
        f"💬 Bu ilginç bilgiyi daha önce duymuş muydunuz? Yorumlara yazın!"
    )
    return poster_path, trv["vo"], caption


def _fetch_mackolik_day_matches(target_date: datetime.date) -> List[Dict[str, Any]]:
    date_str = target_date.strftime("%d/%m/%Y")
    r = requests.get(LIVEDATA_URL.format(date=date_str), headers=HEADERS, timeout=12).json()
    out: List[Dict[str, Any]] = []
    for m in r.get("m", []):
        if not isinstance(m, list) or len(m) < 37:
            continue
        lg = m[36] if isinstance(m[36], list) and len(m[36]) > 3 else [0, "Futbol", 0, ""]
        c_name = str(lg[1]).strip()
        l_name = str(lg[3]).strip()
        l_code = str(lg[9]).strip() if len(lg) > 9 else ""
        h_id = int(m[1]) if str(m[1]).isdigit() else 0
        h_name = str(m[2]).strip()
        a_id = int(m[3]) if str(m[3]).isdigit() else 0
        a_name = str(m[4]).strip()
        status = str(m[6]).strip()
        kickoff = str(m[16]).strip()

        if is_basketball_or_other_sport(c_name, l_name, l_code, h_name, a_name):
            continue
        if is_excluded_football_category(c_name, l_name, l_code, h_name, a_name):
            continue

        hg = int(m[12]) if str(m[12]).isdigit() else 0
        ag = int(m[13]) if str(m[13]).isdigit() else 0

        prio = 10
        up_c = tr_upper(c_name)
        up_l = tr_upper(l_name)
        if h_name == "Türkiye" or a_name == "Türkiye":
            prio += 2000
        if h_id in (1, 2, 3, 4) or a_id in (1, 2, 3, 4):
            prio += 1500
        if "TÜRKİYE" in up_c and "SÜPER" in up_l:
            prio += 950
        if any(k in up_c or k in up_l for k in ["ŞAMPİYONLAR", "AVRUPA LİGİ", "KONFERANS", "ULUSLAR LİGİ", "DÜNYA KUPASI", "AVRUPA ŞAMPİYONASI"]):
            prio += 850
        elif any(k in up_c for k in ["İNGİLTERE", "İSPANYA", "İTALYA", "ALMANYA", "FRANSA"]) and any(
            t in up_l for t in ["PREMIER", "LALIGA", "SERIE A", "BUNDESLIGA", "LIGUE 1"]
        ):
            prio += 750
        if any(low_kw in up_l for low_kw in ["2.LİG", "3.LİG", "2. LİG", "3. LİG", "AMATÖR", "REZERV"]):
            prio -= 300

        out.append({
            "match_id": m[0],
            "home_id": h_id,
            "home": h_name,
            "away_id": a_id,
            "away": a_name,
            "status": status,
            "time": kickoff,
            "country": c_name,
            "league_sub": l_name,
            "hg": hg,
            "ag": ag,
            "score": f"{hg} - {ag}",
            "priority": prio,
        })
    out.sort(key=lambda x: (-x["priority"], x["time"]))
    return out


def build_pre_match_short(target_date: datetime.date) -> Tuple[Path, str, str]:
    """5) 19:00 - Maç Önü İstatistikleri & Form Karşılaştırması (Sıfır İddaa/Oran!)"""
    matches = _fetch_mackolik_day_matches(target_date)
    upcoming = [m for m in matches if m["status"] in ("", "0", "Başlamadı")] or matches
    if not upcoming:
        return build_headlines_short()

    m = upcoming[0]
    h_last5 = fetch_team_last_5_matches(m["home_id"], m["home"], target_date)
    a_last5 = fetch_team_last_5_matches(m["away_id"], m["away"], target_date)

    img = build_broadcast_background(None, accent=ACCENT_GOLD)
    draw = ImageDraw.Draw(img)
    draw_top_masthead(draw, "MAÇ ÖNÜ İSTATİSTİK", accent=(195, 135, 10))

    # Lig ve Saat Başlığı
    lg_txt = f"{tr_upper(m['country'])}  •  {tr_upper(m['league_sub'])}  •  SAAT {m['time']}"
    f_lg = load_font(27, True)
    ltb = draw.textbbox((0, 0), lg_txt, font=f_lg)
    draw.text(((WIDTH - (ltb[2] - ltb[0])) // 2, 178), lg_txt, font=f_lg, fill=ACCENT_CYAN)

    # İki Takım Arması + VS Sahnesi
    draw.rounded_rectangle([48, 232, WIDTH - 48, 690], radius=26, fill=CARD_NAVY, outline=ACCENT_GOLD, width=3)
    h_crest = fetch_team_crest(m["home_id"], target_size=220)
    a_crest = fetch_team_crest(m["away_id"], target_size=220)
    img.paste(h_crest, (235 - 110, 415 - 110), h_crest)
    img.paste(a_crest, (845 - 110, 415 - 110), a_crest)
    draw = ImageDraw.Draw(img)

    draw.ellipse([460, 335, 620, 495], fill=ACCENT_RED, outline=ACCENT_GOLD, width=5)
    f_vs = load_impact_font(76)
    vtb = draw.textbbox((0, 0), "VS", font=f_vs)
    draw.text((540 - (vtb[2] - vtb[0]) // 2, 368), "VS", font=f_vs, fill=TEXT_WHITE)

    f_tn = load_font(32, True)
    for cx, nm in [(235, tr_upper(m["home"])[:15]), (845, tr_upper(m["away"])[:15])]:
        ntb = draw.textbbox((0, 0), nm, font=f_tn)
        draw.text((cx - (ntb[2] - ntb[0]) // 2, 565), nm, font=f_tn, fill=TEXT_WHITE)

    # Karşılaştırmalı Son 5 Maç Form ve Gol İstatistikleri
    def calc_stats(l5: List[Dict[str, Any]], tid: int) -> Tuple[str, int, int, int]:
        form_str = " - ".join([x["result"] for x in l5[:5]]) if l5 else "Veri Yok"
        w = sum(1 for x in l5 if x["result"] == "G")
        gf = sum(x["home_goals"] if x["home_id"] == tid else x["away_goals"] for x in l5)
        ga = sum(x["away_goals"] if x["home_id"] == tid else x["home_goals"] for x in l5)
        return form_str, w, gf, ga

    h_form, h_w, h_gf, h_ga = calc_stats(h_last5, m["home_id"])
    a_form, a_w, a_gf, a_ga = calc_stats(a_last5, m["away_id"])

    rows = [
        ("SON 5 MAÇ FORMU", h_form, a_form),
        ("SON 5 MAÇ GALİBİYET", f"{h_w} Galibiyet", f"{a_w} Galibiyet"),
        ("SON 5 MAÇ ATILAN GOL", f"{h_gf} Gol", f"{a_gf} Gol"),
        ("SON 5 MAÇ YENİLEN GOL", f"{h_ga} Gol", f"{a_ga} Gol"),
    ]
    for idx, (label, hv, av) in enumerate(rows):
        ry1 = 725 + idx * 245
        ry2 = ry1 + 218
        draw.rounded_rectangle([48, ry1, WIDTH - 48, ry2], radius=22, fill=(11, 20, 38), outline=(50, 82, 132), width=2)
        f_rlbl = load_font(25, True)
        rtb = draw.textbbox((0, 0), label, font=f_rlbl)
        draw.text(((WIDTH - (rtb[2] - rtb[0])) // 2, ry1 + 24), label, font=f_rlbl, fill=ACCENT_GOLD)

        f_rval = load_impact_font(50)
        htb = draw.textbbox((0, 0), hv, font=f_rval)
        atb = draw.textbbox((0, 0), av, font=f_rval)
        draw.text((260 - (htb[2] - htb[0]) // 2, ry1 + 98), hv, font=f_rval, fill=TEXT_WHITE)
        draw.text((820 - (atb[2] - atb[0]) // 2, ry1 + 98), av, font=f_rval, fill=ACCENT_CYAN)
        draw.line([(540, ry1 + 82), (540, ry2 - 24)], fill=(45, 70, 110), width=2)

    poster_path = ASSETS_DIR / "yt_prematch_poster.jpg"
    img.save(poster_path, quality=95)

    vo = (
        f"Maç önü istatistik ekranında günün dev randevusu! "
        f"{m['country']} heyecanında saat {m['time']}'de {m['home']} ile {m['away']} karşı karşıya geliyor! "
        f"Ev sahibi {m['home']} son beş maçında {h_w} galibiyet alırken rakip ağlara {h_gf} gol gönderdi. "
        f"Konuk ekip {m['away']} ise son beş maçında {a_w} galibiyet ve {a_gf} gol kaydetti! "
        f"Sizce bu kritik mücadeleden hangi takım galip ayrılır? Skor tahminlerinizi yorumlara bekliyoruz!"
    )
    caption = (
        f"📊 MAÇ ÖNÜ ANALİZ: {m['home']} - {m['away']} İstatistikleri! ⚽🔥\n\n"
        f"🏆 {m['country']} - {m['league_sub']} | Saat: {m['time']}\n"
        f"🔹 {m['home']} Son 5 Maç: {h_w} Galibiyet, {h_gf} Gol\n"
        f"🔹 {m['away']} Son 5 Maç: {a_w} Galibiyet, {a_gf} Gol\n\n"
        f"💬 Sizce bu karşılaşma kaç kaç biter? Yorumlara tahmininizi yazın!"
    )
    return poster_path, vo, caption


def build_post_match_short(target_date: datetime.date) -> Tuple[Path, str, str]:
    """6) 22:00 - Günün Maç Sonu Analizi & Skor Özeti"""
    matches = _fetch_mackolik_day_matches(target_date)
    finished = [m for m in matches if m["status"] in ("MS", "Uz.", "Pen.", "Bitti")]
    if not finished:
        yesterday = target_date - datetime.timedelta(days=1)
        finished = [m for m in _fetch_mackolik_day_matches(yesterday) if m["status"] in ("MS", "Uz.", "Pen.", "Bitti")]
    if not finished:
        return build_headlines_short()

    top = finished[0]
    others = finished[1:5]

    img = build_broadcast_background(None, accent=ACCENT_RED)
    draw = ImageDraw.Draw(img)
    draw_top_masthead(draw, "MAÇ SONU ANALİZİ", accent=ACCENT_RED)

    # Ana Biten Maç Skor Tabelası
    draw.rounded_rectangle([48, 178, WIDTH - 48, 760], radius=28, fill=CARD_NAVY, outline=ACCENT_GOLD, width=3)
    lg_txt = f"MAÇ SONUCU  •  {tr_upper(top['country'])}"
    f_lg = load_font(27, True)
    ltb = draw.textbbox((0, 0), lg_txt, font=f_lg)
    draw.text(((WIDTH - (ltb[2] - ltb[0])) // 2, 204), lg_txt, font=f_lg, fill=ACCENT_GOLD)

    h_crest = fetch_team_crest(top["home_id"], target_size=210)
    a_crest = fetch_team_crest(top["away_id"], target_size=210)
    img.paste(h_crest, (215 - 105, 430 - 105), h_crest)
    img.paste(a_crest, (865 - 105, 430 - 105), a_crest)
    draw = ImageDraw.Draw(img)

    # Dev Skor Kutusu
    draw.rounded_rectangle([380, 355, 700, 505], radius=22, fill=(6, 12, 24), outline=ACCENT_GOLD, width=4)
    f_sc = load_impact_font(96)
    sctb = draw.textbbox((0, 0), top["score"], font=f_sc)
    draw.text((540 - (sctb[2] - sctb[0]) // 2, 372), top["score"], font=f_sc, fill=ACCENT_GOLD)

    f_tn = load_font(32, True)
    for cx, nm in [(215, tr_upper(top["home"])[:14]), (865, tr_upper(top["away"])[:14])]:
        ntb = draw.textbbox((0, 0), nm, font=f_tn)
        draw.text((cx - (ntb[2] - ntb[0]) // 2, 575), nm, font=f_tn, fill=TEXT_WHITE)

    # Maç Özeti Yorum Satırı
    if top["hg"] > top["ag"]:
        verdict = f"{top['home']} sahadan {top['score']}'lık net galibiyetle ayrıldı!"
    elif top["ag"] > top["hg"]:
        verdict = f"{top['away']} deplasmanda {top['score']} kazanarak kritik bir zafer elde etti!"
    else:
        verdict = f"Büyük çekişmeye sahne olan mücadele {top['score']} eşitlikle sona erdi!"

    vtb = draw.textbbox((0, 0), verdict, font=load_font(27, True))
    draw.text(((WIDTH - (vtb[2] - vtb[0])) // 2, 682), verdict, font=load_font(27, True), fill=ACCENT_CYAN)

    # Günün Diğer Tamamlanan Maçları
    draw.text((56, 795), "GÜNÜN DİĞER TAMAMLANAN KARŞILAŞMALARI", font=load_font(26, True), fill=ACCENT_GOLD)
    for idx, om in enumerate(others):
        oy1 = 850 + idx * 215
        oy2 = oy1 + 190
        draw.rounded_rectangle([48, oy1, WIDTH - 48, oy2], radius=20, fill=(11, 20, 38), outline=(45, 75, 120), width=2)
        hc = fetch_team_crest(om["home_id"], target_size=82)
        ac = fetch_team_crest(om["away_id"], target_size=82)
        img.paste(hc, (78, oy1 + 54), hc)
        img.paste(ac, (WIDTH - 160, oy1 + 54), ac)
        draw = ImageDraw.Draw(img)

        draw.text((180, oy1 + 74), om["home"][:14], font=load_font(30, True), fill=TEXT_WHITE)
        atb = draw.textbbox((0, 0), om["away"][:14], font=load_font(30, True))
        draw.text((WIDTH - 180 - (atb[2] - atb[0]), oy1 + 74), om["away"][:14], font=load_font(30, True), fill=TEXT_WHITE)

        draw.rounded_rectangle([460, oy1 + 48, 620, oy2 - 48], radius=14, fill=CARD_NAVY, outline=ACCENT_GOLD, width=2)
        ostb = draw.textbbox((0, 0), om["score"], font=load_impact_font(48))
        draw.text((540 - (ostb[2] - ostb[0]) // 2, oy1 + 64), om["score"], font=load_impact_font(48), fill=ACCENT_GOLD)

    poster_path = ASSETS_DIR / "yt_postmatch_poster.jpg"
    img.save(poster_path, quality=95)

    other_spoken = ", ".join([f"{x['home']} {x['hg']}, {x['away']} {x['ag']}" for x in others[:3]])
    vo = (
        f"Maç sonu analiz ekranında günün sonuçları! "
        f"Günün öne çıkan mücadelesinde {verdict} "
        + (f"Günün diğer karşılaşmalarında ise {other_spoken} skorları kaydedildi. " if other_spoken else "")
        + "Maçın yıldızı sizce kimdi? Yorumlarda değerlendirelim!"
    )
    other_lines = "\n".join([f"⚽ {x['home']} {x['score']} {x['away']}" for x in others])
    caption = (
        f"🏁 MAÇ SONU ANALİZİ: {top['home']} {top['score']} {top['away']}! ⚽🔥\n\n"
        f"📌 {verdict}\n"
        + (f"\n📊 Günün Diğer Sonuçları:\n{other_lines}\n" if other_lines else "")
        + "\n💬 Karşılaşmanın performansını nasıl buldunuz? Yorumlara yazın!"
    )
    return poster_path, vo, caption


def render_subscribe_outro_frame(frame: Image.Image, draw: ImageDraw.ImageDraw, elapsed: float, dur: float) -> None:
    """
    Son 2.8 saniyede bahis/bayi ekranı yerine şık 'KANALA ABONE OL & BİLDİRİMLERİ AÇ' kartı çizer.
    """
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 * (1 - ratio) + 4 * ratio)
        g = int(18 * (1 - ratio) + 8 * ratio)
        b = int(38 * (1 - ratio) + 18 * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    prog = ease_out_back(min(1.0, elapsed / 0.45))
    cx, cy = WIDTH // 2, HEIGHT // 2
    cw = int(900 * prog)
    ch = int(680 * prog)
    x1, y1, x2, y2 = cx - cw // 2, cy - ch // 2

    draw.rounded_rectangle([x1, y1, x2, y2], radius=36, fill=CARD_NAVY, outline=ACCENT_GOLD, width=5)

    if prog > 0.65:
        # Kırmızı YouTube Abone Ol Butonu
        pulse = int(8 * math.sin(elapsed * 8.0))
        bx1, by1, bx2, by2 = cx - 290 - pulse, cy - 40 - pulse // 2, cx + 290 + pulse, cy + 95 + pulse // 2
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=28, fill=ACCENT_RED, outline=TEXT_WHITE, width=3)

        f_sub = load_impact_font(68)
        stb = draw.textbbox((0, 0), "ABONE OL", font=f_sub)
        draw.text((cx - (stb[2] - stb[0]) // 2, (by1 + by2) // 2 - 42), "ABONE OL", font=f_sub, fill=TEXT_WHITE)

        t1 = "FUTBOL GÜNDEMİNİ KAÇIRMA!"
        f_t1 = load_impact_font(62)
        tb1 = draw.textbbox((0, 0), t1, font=f_t1)
        draw.text((cx - (tb1[2] - tb1[0]) // 2, y1 + 95), t1, font=f_t1, fill=ACCENT_GOLD)

        t2 = "Her gün yeni spor haberleri, hikayeler ve analizler!"
        f_t2 = load_font(31, True)
        tb2 = draw.textbbox((0, 0), t2, font=f_t2)
        draw.text((cx - (tb2[2] - tb2[0]) // 2, by2 + 70), t2, font=f_t2, fill=TEXT_WHITE)

        t3 = "Videoyu beğenip yorum yapmayı unutmayın"
        f_t3 = load_font(27, True)
        tb3 = draw.textbbox((0, 0), t3, font=f_t3)
        draw.text((cx - (tb3[2] - tb3[0]) // 2, by2 + 135), t3, font=f_t3, fill=ACCENT_CYAN)


def render_sports_short_mp4(poster_path: Path, vo_script: str, out_mp4: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    vo_main_path = OUTPUT_DIR / f"vo_{out_mp4.stem}.mp3"
    vo_sub_path = OUTPUT_DIR / "vo_subscribe_outro.mp3"

    asyncio.run(generate_tts(vo_script, vo_main_path))
    if not vo_sub_path.exists() or vo_sub_path.stat().st_size < 1000:
        asyncio.run(generate_tts(SUBSCRIBE_VOICEOVER, vo_sub_path))

    main_dur = max(9.0, get_audio_duration(vo_main_path) + 0.6)
    outro_dur = max(2.8, get_audio_duration(vo_sub_path) + 0.4)
    total_dur = min(57.5, main_dur + outro_dur)
    if main_dur + outro_dur > 57.5:
        main_dur = 57.5 - outro_dur

    total_frames = int(math.ceil(total_dur * FPS))
    poster_base = Image.open(poster_path).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    sub_delay_ms = int(main_dur * 1000)

    filter_complex = (
        f"aevalsrc='0.11*sin(2*PI*65*t)*exp(-3.2*mod(t,0.5))+0.04*sin(2*PI*196*t)*exp(-5.5*mod(t,0.25))'"
        f":s=44100:d={total_dur:.2f}[bgm];"
        f"[1:a]aresample=44100,volume=1.95[vo_main];"
        f"[2:a]aresample=44100,volume=1.95,adelay={sub_delay_ms}|{sub_delay_ms}[vo_sub];"
        f"[bgm][vo_main][vo_sub]amix=inputs=3:duration=first:dropout_transition=0,"
        f"alimiter=limit=0.95[aout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        "-i", str(vo_main_path),
        "-i", str(vo_sub_path),
        "-filter_complex", filter_complex,
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-t", f"{total_dur:.2f}",
        str(out_mp4),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    for f_idx in range(total_frames):
        t = f_idx / FPS
        if t < main_dur:
            zoom = 1.0 + 0.028 * math.sin((t / main_dur) * math.pi)
            zw, zh = int(WIDTH * zoom), int(HEIGHT * zoom)
            resized = poster_base.resize((zw, zh), Image.Resampling.BILINEAR)
            ox, oy = (zw - WIDTH) // 2, (zh - HEIGHT) // 2
            frame = resized.crop((ox, oy, ox + WIDTH, oy + HEIGHT))
            draw = ImageDraw.Draw(frame)
            bar_w = int((WIDTH - 96) * min(1.0, t / max(0.1, total_dur)))
            if bar_w > 4:
                draw.rounded_rectangle([48, HEIGHT - 84, 48 + bar_w, HEIGHT - 77], radius=3, fill=ACCENT_GOLD)
        else:
            frame = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK_BOT)
            draw = ImageDraw.Draw(frame)
            render_subscribe_outro_frame(frame, draw, t - main_dur, outro_dur)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    stderr_bytes = proc.stderr.read() if proc.stderr else b""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası:\n{stderr_bytes.decode('utf-8', errors='ignore')}")
    return out_mp4


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["headlines", "biography", "breaking", "trivia", "pre_match", "post_match"],
        required=True,
    )
    parser.add_argument("--date", default="", help="GG/AA/YYYY formatında tarih (boşsa bugün TSİ)")
    parser.add_argument("--upload", action="store_true", help="Üretilen videoyu YouTube Shorts olarak yükle")
    args = parser.parse_args()

    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    target_date = (
        datetime.datetime.strptime(args.date, "%d/%m/%Y").date()
        if args.date
        else datetime.datetime.now(tz_tr).date()
    )

    if args.mode == "headlines":
        poster, vo, cap = build_headlines_short()
    elif args.mode == "biography":
        poster, vo, cap = build_biography_short(target_date)
    elif args.mode == "breaking":
        poster, vo, cap = build_breaking_short()
    elif args.mode == "trivia":
        poster, vo, cap = build_trivia_short(target_date)
    elif args.mode == "pre_match":
        poster, vo, cap = build_pre_match_short(target_date)
    else:
        poster, vo, cap = build_post_match_short(target_date)

    out_video = OUTPUT_DIR / f"yt_short_{args.mode}.mp4"
    print(f"[1/2] '{args.mode}' kategorisinde Spor Shorts videosu üretiliyor...")
    render_sports_short_mp4(poster, vo, out_video)
    print(f"[OK] Video hazır: {out_video}")

    if args.upload:
        upload_short(out_video, cap)


if __name__ == "__main__":
    main()
