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
import html
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
from typing import Any, Dict, List, Optional, Tuple, Union

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
from graph_motion_engine import render_graph_motion_mp4
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


DYNAMIC_BIO_STARS: List[Tuple[str, str, str]] = [
    ("Mauro Icardi", "Mauro_Icardi", "GALATASARAY'IN ARJANTİNLİ SÜPER GOLCÜSÜ"),
    ("Edin Džeko", "Edin_Džeko", "BOSNA ELMASINDAN GOL MAKİNESİ"),
    ("Fernando Muslera", "Fernando_Muslera", "SÜPER LİG TARİHİNİN EFSANE ELDİVENİ"),
    ("Ferdi Kadıoğlu", "Ferdi_Kadıoğlu", "MİLLİ TAKIMIN DİNAMOSU"),
    ("Orkun Kökçü", "Orkun_Kökçü", "AVRUPA SAHNESİNDEKİ TÜRK MAESTRO"),
    ("Barış Alper Yılmaz", "Barış_Alper_Yılmaz", "TÜRK FUTBOLUNUN FİZİK GÜCÜ YÜKSEK YILDIZI"),
    ("Kerem Aktürkoğlu", "Kerem_Aktürkoğlu", "ALT LİGLERDEN AVRUPA DEVLERİNE UZANAN HİKAYE"),
    ("Wesley Sneijder", "Wesley_Sneijder", "UZAK MESAFE FÜZELERİNİN HOLLANDALI USTASI"),
    ("Didier Drogba", "Didier_Drogba", "FİNALLERİN ADAMI VE AFRİKA EFSANESİ"),
    ("Roberto Carlos", "Roberto_Carlos", "FİZİK KURALLARINI YIKAN SOL BEK"),
    ("Ricardo Quaresma", "Ricardo_Quaresma", "TRİVELA SANATININ PORTEKİZLİ ÜSTADI"),
    ("Atiba Hutchinson", "Atiba_Hutchinson", "BEŞİKTAŞ'IN BİTMEYEN ENERJİSİ: AHTAPOT"),
    ("Metin Oktay", "Metin_Oktay", "AĞLARI DELEN TAÇSIZ KRAL"),
    ("Lefter Küçükandonyadis", "Lefter_Küçükandonyadis", "TÜRK FUTBOLUNUN ORDİNARYÜSÜ"),
    ("Rüştü Reçber", "Rüştü_Reçber", "2002 DÜNYA KUPASI KAHRAMANI"),
    ("Nihat Kahveci", "Nihat_Kahveci", "EURO 2008 DESTANININ UNUTULMAZ GOLCÜSÜ"),
    ("Arda Turan", "Arda_Turan", "LA LIGA ŞAMPİYONU TÜRK KAPTAN"),
    ("Burak Yılmaz", "Burak_Yılmaz", "LILLE İLE FRANSA'YI FETHEDEN KRAL"),
    ("Jude Bellingham", "Jude_Bellingham", "REAL MADRID'İN İNGİLİZ SÜPER YILDIZI"),
    ("Erling Haaland", "Erling_Haaland", "PREMIER LİG REKORLARINI PARAMPARÇA EDEN VİKİNG"),
    ("Vinícius Júnior", "Vinícius_Júnior", "ŞAMPİYONLAR LİGİ FİNALLERİNİN YILDIZI"),
    ("Mohamed Salah", "Mohamed_Salah", "ANFIELD'IN MISIR KRALI"),
    ("Kevin De Bruyne", "Kevin_De_Bruyne", "MODERN FUTBOLUN ASİST PROFESÖRÜ"),
    ("Luka Modrić", "Luka_Modrić", "YAŞLANMAYAN BALLON D'OR EFSANESİ"),
    ("Zlatan Ibrahimović", "Zlatan_Ibrahimović", "AKROBATİK GOLLERİN İSVEÇLİ İKONU"),
    ("Thierry Henry", "Thierry_Henry", "ARSENAL'İN YENİLMEZLER DÖNEMİ KRALI"),
    ("Andrés Iniesta", "Andrés_Iniesta", "DÜNYA KUPASI FİNALİNİN İSPANYOL SİHİRBAZI"),
    ("Gianluigi Buffon", "Gianluigi_Buffon", "FUTBOL TARİHİNİN ÖLÜMSÜZ İTALYAN KALECİSİ"),
    ("Diego Maradona", "Diego_Maradona", "FUTBOLUN ARJANTİNLİ DAHİSİ"),
    ("Pelé", "Pelé", "ÜÇ DÜNYA KUPASI KAZANAN TEK KRAL"),
]


def fetch_recent_channel_titles(max_results: int = 35) -> List[str]:
    """
    Saatlik yayın akışında aynı haber, futbolcu, bilgi veya maçın tekrar yüklenmemesi için
    kanaldaki son videoların başlıklarını çeker (sadece 1 API birimi harcar).
    """
    try:
        from googleapiclient.discovery import build
        from upload_youtube import load_youtube_credentials

        creds = load_youtube_credentials(BASE_DIR)
        yt = build("youtube", "v3", credentials=creds)
        ch = yt.channels().list(part="contentDetails", mine=True).execute().get("items", [])
        if not ch:
            return []
        upl = ch[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = yt.playlistItems().list(part="snippet", playlistId=upl, maxResults=max_results).execute()
        return [it["snippet"]["title"].lower() for it in pl.get("items", []) if it.get("snippet", {}).get("title")]
    except Exception:
        return []


def _build_dynamic_wiki_bio(name: str, wiki_slug: str, subtitle: str) -> Optional[Dict[str, str]]:
    """
    Türkçe Wikipedia özetinden gerçek kariyer cümlelerini çekerek saatlik sınırsız biyografi üretir.
    """
    try:
        enc = urllib.parse.quote(wiki_slug)
        r = requests.get(f"https://tr.wikipedia.org/api/rest_v1/page/summary/{enc}", headers=WIKI_HEADERS, timeout=8)
        if r.status_code != 200:
            return None
        extract = _clean_news_text(r.json().get("extract", ""))
        sents = [s.strip() for s in re.split(r"(?<!\d)(?<=[.!?])\s+", extract) if len(s.strip()) >= 35]
        if len(sents) < 2:
            return None
        while len(sents) < 3:
            sents.append(f"{name}, kariyeri boyunca kazandığı başarılar ve unutulmaz performanslarıyla futbol tarihine damga vurdu.")
        vo_body = _trim_to_sentence(" ".join([_prepare_spoken_news_sentence(s) for s in sents[:3]]), 380)
        return {
            "name": name,
            "wiki_tr": wiki_slug,
            "wiki_en": wiki_slug,
            "subtitle": subtitle,
            "fact1": _trim_to_sentence(sents[0], 175),
            "fact2": _trim_to_sentence(sents[1], 175),
            "fact3": _trim_to_sentence(sents[2], 175),
            "vo": f"Futbolcu portresinde bu saatte: {name}! {vo_body} Siz {name} hakkında ne düşünüyorsunuz? Yorumlara yazın!",
        }
    except Exception:
        return None


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


NEWS_BANNED_KW = [
    "iddaa", "bahis", "kupon", "misli", "nesine", "bilyoner", "tuttur", "oley.com",
    "voleybol", "basketbol", "euroleague", "nba", "tenis", "formula 1", "grand prix", "hentbol",
    "medicana", "madeş", "opet", "beko", "mct", "daikin", "eczacıbaşı", "vakıfbank",
    "anadolu efes", "sultanlar", "efeler", "filede", "parkede", "potada", "set ",
    "pistons", "lakers", "celtics", "pelicans", "miami heat", "warriors", "rockets",
    "kadın futbol", "arsavev", "fomget", "alg spor", "u19", "u17",
]

FOOTBALL_POSITIVE_KW = [
    "futbol", "süper lig", "şampiyonlar ligi", "avrupa ligi", "konferans ligi", "uluslar ligi",
    "milli takım", "ay-yıldızlı", "ayyıldızlı", "galatasaray", "fenerbahçe", "beşiktaş", "trabzonspor",
    "başakşehir", "samsunspor", "göztepe", "eyüpspor", "konyaspor", "antalyaspor", "alanyaspor",
    "real madrid", "barcelona", "liverpool", "arsenal", "manchester", "juventus", "inter", "milan",
    "bayern", "dortmund", "psg", "portekiz", "ispanya", "fransa", "ingiltere", "almanya", "italya",
    "brezilya", "arjantin", "hollanda", "belçika", "hırvatistan", "danimarka",
    "transfer", "bonservis", "teknik direktör", "forvet", "golcü", "kaleci", "penaltı",
    "deplasman", "stadyum", "stadı", "hakem", "kırmızı kart", "ofsayt", "gol ", "golü", "golleri",
]


def _clean_news_text(raw: str) -> str:
    txt = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    txt = re.sub(r"\s+", " ", txt).strip()
    junk_patterns = [
        r"Devamı için tıklayınız\.?",
        r"Haberin devamı için tıklayınız\.?",
        r"İşte detaylar\.{0,3}",
        r"İşte o flaş gerçek\.{0,3}",
        r"İşte tüm senaryolar\.{0,3}",
        r"CANLI İZLE!?",
        r"Şifresiz mi\??",
        r"\|\s*Son dakika[^.]*$",
    ]
    for pat in junk_patterns:
        txt = re.sub(pat, "", txt, flags=re.IGNORECASE).strip()
    return re.sub(r"\s+", " ", txt).strip(" -|•:")


def _clean_headline_title(raw_title: str) -> str:
    t = _clean_news_text(raw_title)
    # "X maçı ne zaman, saat kaçta, hangi kanalda?" gibi SEO kuyruklarını temizle
    t = re.sub(r"\s*[-–|]?\s*(ne zaman|saat kaçta|hangi kanalda).*$", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"^(FENERBAHÇE|GALATASARAY|BEŞİKTAŞ|TRABZONSPOR)\s+HABERİ\s*[:|]\s*", "", t, flags=re.IGNORECASE).strip()
    return t


def _prepare_spoken_news_sentence(text: str) -> str:
    s = text.strip()
    s = re.sub(r"\(p\)", " penaltıdan ", s, flags=re.IGNORECASE)
    s = re.sub(r"\(2\)", " iki golle ", s)
    s = re.sub(r"\(3\)", " üç golle ", s)
    s = re.sub(r"\bTSİ\b", "Türkiye saatiyle", s)
    s = re.sub(r"(\d+)\+(\d+)\.\s*dakika", r"\1 artı \2. dakika", s)
    s = re.sub(r"!{2,}", "!", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _scrape_article_details_and_photo(url: str, rss_desc: str, rss_img_url: str) -> Tuple[List[str], Optional[Image.Image]]:
    body_paragraphs: List[str] = []
    og_img_url = rss_img_url

    if url:
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=7)
            if r.status_code == 200:
                html_txt = r.text
                og_m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html_txt, re.I)
                if not og_m:
                    og_m = re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html_txt, re.I)
                if og_m:
                    cand = html.unescape(og_m.group(1).strip())
                    if "im.haberturk.com" in cand and "/jpg/1200x628" in cand:
                        cand = cand.replace("/jpg/1200x628", "/jpg/640x640")
                    if cand.startswith("http") and "logo" not in cand.lower():
                        og_img_url = cand

                raw_ps = re.findall(r"<p[^>]*>(.*?)</p>", html_txt, flags=re.S | re.I)
                skip_p_kw = [
                    "çerez", "cookie", "gizlilik", "copyright", "tüm hakları", "abone ol",
                    "bülten", "reklam", "whatsapp", "instagram", "uygulamamızı", "kvkk",
                    "misli", "iddaa", "nesine", "bilyoner", "bahis", "canlı anlatım",
                ]
                for rp in raw_ps:
                    cp = _clean_news_text(rp)
                    if len(cp) < 50 or len(cp) > 380:
                        continue
                    if any(sk in cp.lower() for sk in skip_p_kw):
                        continue
                    # Tam cümle kontrolü (sonu noktalama ile bitmeli)
                    if cp[-1] not in ".!?\"'”":
                        continue
                    # Yabancı takım 11 listelerini ("Fransa: X, Y, Z...") seslendirmede atla; Türkiye 11'ini doğal cümleye çevir
                    if cp.count(",") >= 6 and ":" in cp[:28]:
                        team_lbl, roster = cp.split(":", 1)
                        if "türkiye" in team_lbl.lower() or "milli" in team_lbl.lower():
                            cp = f"Ay-yıldızlı ekibimizin muhtemel on birinde {roster.strip().rstrip('.')} yer alıyor."
                        else:
                            continue
                    if any(cp[:38].lower() in existing.lower() or existing[:38].lower() in cp.lower() for existing in body_paragraphs):
                        continue
                    body_paragraphs.append(cp)
                    if len(body_paragraphs) >= 4:
                        break
        except Exception:
            pass

    if not body_paragraphs and rss_desc and len(rss_desc) >= 55 and rss_desc[-1] in ".!?":
        body_paragraphs.append(rss_desc)

    photo_img: Optional[Image.Image] = None
    if og_img_url and og_img_url.startswith("http"):
        try:
            ir = requests.get(og_img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=7)
            if ir.status_code == 200 and len(ir.content) > 8000:
                im = Image.open(io.BytesIO(ir.content)).convert("RGB")
                if im.size[0] >= 360 and im.size[1] >= 200:
                    photo_img = im
        except Exception:
            photo_img = None

    return body_paragraphs, photo_img


def fetch_rich_football_news(limit: int = 5, prefer_breaking: bool = False) -> List[Dict[str, Any]]:
    """
    Habertürk Spor, A Spor Futbol, TRT Haber Spor, Sabah Spor ve Cumhuriyet Spor RSS + makale gövdesinden
    GERÇEK haber metni, skor/oyuncu/puan detayları ve basın fotoğrafı içeren zengin futbol haberlerini çeker.
    Sadece başlık olan veya detayı boş olan haberleri kesinlikle eler.
    """
    feeds = [
        ("Habertürk Spor", "https://www.haberturk.com/rss/spor.xml", False),
        ("A Spor", "https://www.aspor.com.tr/rss/futbol.xml", True),
        ("TRT Spor", "https://www.trthaber.com/spor_articles.rss", False),
        ("Sabah Spor", "https://www.sabah.com.tr/rss/spor.xml", False),
        ("Cumhuriyet Spor", "https://www.cumhuriyet.com.tr/rss/spor.xml", False),
    ]
    if prefer_breaking:
        feeds = [feeds[1], feeds[0], feeds[3], feeds[2], feeds[4]]

    candidates: List[Dict[str, str]] = []
    seen_titles = set()

    for source_name, feed_url, is_pure_football in feeds:
        try:
            r = requests.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=7)
            if r.status_code != 200 or b"<item" not in r.content:
                continue
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:14]:
                raw_title = (item.findtext("title") or "").strip()
                raw_desc = (item.findtext("description") or "").strip()
                link = (item.findtext("link") or "").strip()
                if not raw_title or not link:
                    continue

                img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_desc, re.I)
                rss_img = img_m.group(1).strip() if img_m else ""

                headline = _clean_headline_title(raw_title)
                clean_desc = _clean_news_text(raw_desc)
                combined_low = f"{headline} {clean_desc}".lower()

                if len(headline) < 16:
                    continue
                if any(b in combined_low for b in NEWS_BANNED_KW):
                    continue
                if not is_pure_football and not any(fk in combined_low for fk in FOOTBALL_POSITIVE_KW):
                    continue

                # Sadece "ne zaman saat kaçta" rehberi olan boş SEO haberlerini ele
                if any(seo in raw_title.lower() for seo in ["neden yok?", "sakat mı?", "şifresiz mi"]):
                    continue

                norm_key = re.sub(r"[^a-zçğıöşü0-9]", "", headline.lower())[:26]
                if norm_key in seen_titles:
                    continue
                seen_titles.add(norm_key)

                candidates.append({
                    "headline": headline,
                    "rss_desc": clean_desc,
                    "rss_img": rss_img,
                    "link": link,
                    "source": source_name,
                })
        except Exception:
            continue

    rich_items: List[Dict[str, Any]] = []
    used_topics = set()

    for cand in candidates:
        # Aynı maç veya aynı konu hakkında iki ayrı haber seçilmesini önle
        words = [w for w in re.findall(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]{4,}", cand["headline"].lower()) if w not in ("milli", "takım", "maçı", "haberi", "sonra", "önce", "karşı", "üzerine")]
        topic_overlap = sum(1 for w in words[:4] if w in used_topics)
        if topic_overlap >= 2 and len(rich_items) >= 1:
            continue

        paras, photo = _scrape_article_details_and_photo(cand["link"], cand["rss_desc"], cand["rss_img"])
        # Gerçek detay kontrolü: En az 75 karakterlik somut haber detayı şart!
        detail_paras = [p for p in paras if len(p) >= 50 and p.lower()[:30] != cand["headline"].lower()[:30]]
        if not detail_paras:
            continue

        # Konuşma metni için en doyurucu 2 paragrafı birleştir
        spoken_parts: List[str] = []
        char_len = 0
        for p in detail_paras:
            sp = _prepare_spoken_news_sentence(p)
            if char_len + len(sp) <= 360 or not spoken_parts:
                spoken_parts.append(sp)
                char_len += len(sp)
            if len(spoken_parts) >= 2 and char_len >= 190:
                break

        spoken_detail = " ".join(spoken_parts).strip()
        spoken_detail = _trim_to_sentence(spoken_detail, 350)

        if len(spoken_detail) < 65:
            continue

        for w in words[:4]:
            used_topics.add(w)

        rich_items.append({
            "headline": cand["headline"],
            "source": cand["source"],
            "paragraphs": detail_paras[:3],
            "spoken_detail": spoken_detail,
            "photo": photo,
        })
        if len(rich_items) >= limit:
            break

    return rich_items


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


def _trim_to_sentence(text: str, max_chars: int) -> str:
    txt = text.strip()
    if len(txt) <= max_chars:
        return txt
    cut = txt[:max_chars]
    # Rakamdan sonraki sıra noktasını (4., 90+4., 1.) cümle sonu sanma!
    ends = [m.end() for m in re.finditer(r"(?<!\d)[.!?](?=\s|$)", cut)]
    if ends and ends[-1] >= int(max_chars * 0.45):
        return cut[: ends[-1]].strip()
    last_sp = cut.rfind(" ")
    return (cut[:last_sp] if last_sp > 40 else cut).rstrip(" ,;:-") + "..."


def _render_detailed_story_poster(
    story: Dict[str, Any],
    masthead_title: str,
    badge_text: str,
    out_path: Path,
    accent: Tuple[int, int, int] = ACCENT_RED,
) -> Path:
    photo = (
        story.get("photo")
        or detect_subject_photo(story["headline"])
        or detect_subject_photo(story.get("spoken_detail", ""))
        or fetch_wiki_image("UEFA_Champions_League", lang="en")
    )
    img = build_broadcast_background(photo, accent=accent)
    if photo is not None:
        paste_hero_photo_card(img, photo, (48, 175, WIDTH - 48, 765), border_col=ACCENT_GOLD)
    draw = ImageDraw.Draw(img)
    draw_top_masthead(draw, masthead_title, accent=accent)

    # Manşet Başlık Kartı (kompakt yükseklik)
    draw.rounded_rectangle([48, 790, WIDTH - 48, 1068], radius=24, fill=CARD_NAVY, outline=ACCENT_GOLD, width=3)
    f_badge = load_font(22, True)
    btb = draw.textbbox((0, 0), badge_text, font=f_badge)
    bw = btb[2] - btb[0] + 38
    draw.rounded_rectangle([74, 812, 74 + bw, 858], radius=10, fill=accent)
    draw.text((93, 821), badge_text, font=f_badge, fill=TEXT_WHITE)

    hl_txt = _trim_to_sentence(tr_upper(story["headline"]), 96)
    f_hl = load_impact_font(48 if len(hl_txt) <= 64 else 41)
    draw_wrapped_text(
        draw,
        hl_txt,
        76,
        878,
        WIDTH - 152,
        f_hl,
        fill=ACCENT_GOLD,
        line_spacing=8,
    )

    # Haberin Gerçek İçerik / Detay Kartı (geniş alan: 2 tam paragraf sığar)
    draw.rounded_rectangle([48, 1092, WIDTH - 48, 1815], radius=24, fill=(11, 20, 38), outline=(56, 189, 248), width=2)
    draw.rounded_rectangle([74, 1116, 360, 1162], radius=8, fill=(22, 48, 88))
    draw.text((92, 1125), "HABERİN DETAYLARI", font=load_font(21, True), fill=ACCENT_CYAN)

    paras = story.get("paragraphs") or [story.get("spoken_detail", "")]
    cur_y = 1184
    for p_idx, para in enumerate(paras[:2]):
        clean_p = _trim_to_sentence(para, 290 if p_idx == 0 else 250)
        if cur_y > 1715:
            break
        draw.ellipse([74, cur_y + 10, 90, cur_y + 26], fill=ACCENT_GOLD)
        cur_y = draw_wrapped_text(
            draw,
            clean_p,
            106,
            cur_y,
            WIDTH - 182,
            load_font(28, True),
            fill=TEXT_WHITE,
            line_spacing=8,
        )
        cur_y += 24

    img.save(out_path, quality=95)
    return out_path


def _story_to_motion_spec(
    story: Dict[str, Any],
    masthead: str,
    badge: str,
    vo_text: str,
    accent: Tuple[int, int, int] = ACCENT_RED,
) -> Dict[str, Any]:
    photo = (
        story.get("photo")
        or detect_subject_photo(story["headline"])
        or detect_subject_photo(story.get("spoken_detail", ""))
        or fetch_wiki_image("UEFA_Champions_League", lang="en")
    )
    raw_paras = story.get("paragraphs") or [story.get("spoken_detail", "")]
    bullets: List[str] = []
    for p in raw_paras[:3]:
        bullets.append(_trim_to_sentence(p, 195))
    if len(bullets) == 1 and len(raw_paras[0]) > 150:
        sents = [s.strip() for s in re.split(r"(?<!\d)(?<=[.!?])\s+", raw_paras[0]) if len(s.strip()) >= 35]
        if len(sents) >= 2:
            bullets = [_trim_to_sentence(s, 185) for s in sents[:3]]
    return {
        "kind": "story",
        "masthead": masthead,
        "badge": badge,
        "headline": story["headline"],
        "bullets": bullets[:3],
        "photo": photo,
        "accent": accent,
        "ticker": story["headline"],
        "vo": vo_text,
    }


def build_headlines_short() -> Tuple[List[Dict[str, Any]], str]:
    """Sabah/Öğle/Akşam Spor Bülteni (Graph-Motion: her manşet kendi hareketli kartları ve tam detaylarıyla)"""
    recent_titles = fetch_recent_channel_titles()
    all_stories = fetch_rich_football_news(limit=8, prefer_breaking=False)
    stories = [
        s for s in all_stories
        if not any(s["headline"].lower()[:22] in rt for rt in recent_titles)
    ] or all_stories
    if not stories:
        stories = [
            {
                "headline": "A Milli Futbol Takımımız Uluslar Ligi'nde sahaya çıkıyor",
                "source": "Spor Gündemi",
                "paragraphs": [
                    "Ay-yıldızlı ekibimiz UEFA Uluslar A Ligi mücadelesinde kritik deplasman sınavına hazırlanıyor.",
                    "Teknik heyet son taktik antrenmanın ardından maç kadrosunu ve oyun planını şekillendirdi.",
                ],
                "spoken_detail": "Ay-yıldızlı ekibimiz UEFA Uluslar A Ligi mücadelesinde kritik deplasman sınavına çıkarken teknik heyet ilk on bir tercihini netleştirdi.",
                "photo": None,
            }
        ]

    selected = stories[:2] if sum(len(s["spoken_detail"]) for s in stories[:3]) > 780 else stories[:3]
    specs: List[Dict[str, Any]] = []
    intros = [
        "Günün spor bülteninde ilk haberimiz:",
        "Gündemdeki ikinci önemli gelişme:",
        "Ve bültenimizin son haberi:",
    ]

    for idx, st in enumerate(selected):
        badge = f"GÜNÜN MANŞETİ {idx + 1}/{len(selected)}"
        concise_detail = _trim_to_sentence(st["spoken_detail"], 340 if len(selected) == 2 else 245)
        clean_hl = st["headline"].rstrip("!")
        seg_vo = f"{intros[idx]} {clean_hl}! {concise_detail}"
        specs.append(_story_to_motion_spec(st, "GÜNÜN SPOR BÜLTENİ", badge, seg_vo, accent=ACCENT_RED))

    lead = selected[0]
    clean_lead_hl = lead["headline"].rstrip("!")
    bullet_block = "\n\n".join(
        [f"🔹 {s['headline']}\n   ↳ {_trim_to_sentence(s['spoken_detail'], 220)}" for s in selected]
    )
    caption = (
        f"📰 GÜNÜN SPOR BÜLTENİ: {clean_lead_hl}! ⚽🔥\n\n"
        f"{bullet_block}\n\n"
        f"💬 Günün gelişmeleri hakkında siz ne düşünüyorsunuz? Yorumlarda buluşalım!"
    )
    return specs, caption


def build_biography_short(target_date: datetime.date) -> Tuple[List[Dict[str, Any]], str]:
    """Saatlik Tekrarsız Futbolcu Biyografisi (Graph-Motion Timeline)"""
    recent_titles = fetch_recent_channel_titles()
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    hour_now = datetime.datetime.now(tz_tr).hour
    start_idx = (target_date.toordinal() * 7 + hour_now) % len(BIOGRAPHIES)

    bio = None
    for offset in range(len(BIOGRAPHIES)):
        cand = BIOGRAPHIES[(start_idx + offset) % len(BIOGRAPHIES)]
        if not any(cand["name"].lower() in rt for rt in recent_titles):
            bio = cand
            break

    if bio is None:
        dyn_start = (target_date.toordinal() * 11 + hour_now) % len(DYNAMIC_BIO_STARS)
        for offset in range(len(DYNAMIC_BIO_STARS)):
            nm, slug, sub = DYNAMIC_BIO_STARS[(dyn_start + offset) % len(DYNAMIC_BIO_STARS)]
            if any(nm.lower() in rt for rt in recent_titles):
                continue
            dyn_bio = _build_dynamic_wiki_bio(nm, slug, sub)
            if dyn_bio is not None:
                bio = dyn_bio
                break

    if bio is None:
        bio = BIOGRAPHIES[start_idx]
    photo = fetch_wiki_image(bio["wiki_tr"], lang="tr") or fetch_wiki_image(bio["wiki_en"], lang="en")

    spec = {
        "kind": "story",
        "masthead": "FUTBOLCU BİYOGRAFİSİ",
        "badge": bio["subtitle"],
        "headline": f"{bio['name']} KARİYER HİKAYESİ",
        "bullets": [bio["fact1"], bio["fact2"], bio["fact3"]],
        "photo": photo,
        "accent": (210, 145, 12),
        "ticker": f"{bio['name']}  •  {bio['subtitle']}",
        "vo": bio["vo"],
    }
    caption = (
        f"⭐ EFSANE PORTRE: {bio['name']} Hikayesi! ⚽👑\n\n"
        f"📌 {bio['subtitle']}\n"
        f"🔹 {bio['fact1']}\n"
        f"🔹 {bio['fact2']}\n"
        f"🔹 {bio['fact3']}\n\n"
        f"💬 Sıradaki videoda hangi futbolcunun hikayesini görmek istersiniz? Yorumlara yazın!"
    )
    return [spec], caption


def build_breaking_short() -> Tuple[List[Dict[str, Any]], str]:
    """Son Dakika Futbol & Transfer Gelişmesi (Graph-Motion, kanal geçmişine göre tekrarsız)"""
    recent_titles = fetch_recent_channel_titles()
    all_stories = fetch_rich_football_news(limit=8, prefer_breaking=True)
    stories = [
        s for s in all_stories
        if not any(s["headline"].lower()[:22] in rt for rt in recent_titles)
    ] or all_stories
    if not stories:
        return build_headlines_short()

    picked = stories[:2] if len(stories) >= 2 else stories[:1]
    specs: List[Dict[str, Any]] = []
    for idx, st in enumerate(picked):
        badge = f"SICAK GELİŞME #{idx + 1}"
        full_detail = " ".join([_prepare_spoken_news_sentence(p) for p in st.get("paragraphs", [])[:2]]).strip()
        full_detail = _trim_to_sentence(full_detail or st["spoken_detail"], 320 if len(picked) == 1 else 250)
        lead_phrase = "Futbol gündeminden sıcak gelişme!" if idx == 0 else "Gündemin bir diğer önemli gelişmesinde ise:"
        clean_hl = st["headline"].rstrip("!")
        seg_vo = f"{lead_phrase} {clean_hl}! {full_detail}"
        if idx == len(picked) - 1:
            seg_vo += " Siz bu gelişmeyi nasıl değerlendiriyorsunuz? Yorumlara yazın!"
        specs.append(_story_to_motion_spec(st, "SON DAKİKA FUTBOL", badge, seg_vo, accent=ACCENT_RED))

    main_st = picked[0]
    details_txt = "\n\n".join([f"📌 {s['headline']}\n🔹 {_trim_to_sentence(s['spoken_detail'], 220)}" for s in picked])
    caption = (
        f"🚨 SON DAKİKA: {main_st['headline']}! ⚽🔥\n\n"
        f"{details_txt}\n\n"
        f"💬 Siz bu gelişme hakkında ne düşünüyorsunuz? Yorumlara yazın!"
    )
    return specs, caption


def build_trivia_short(target_date: datetime.date) -> Tuple[List[Dict[str, Any]], str]:
    """Futbol Genel Kültürü & İlginç Bilgiler (Graph-Motion Timeline)"""
    recent_titles = fetch_recent_channel_titles()
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    hour_now = datetime.datetime.now(tz_tr).hour
    start_idx = (target_date.toordinal() * 5 + hour_now) % len(TRIVIA_ITEMS)
    trv = TRIVIA_ITEMS[start_idx]
    for offset in range(len(TRIVIA_ITEMS)):
        cand = TRIVIA_ITEMS[(start_idx + offset) % len(TRIVIA_ITEMS)]
        if not any(cand["headline"].lower()[:20] in rt for rt in recent_titles):
            trv = cand
            break
    photo = fetch_wiki_image(trv["wiki_en"], lang="en")

    spec = {
        "kind": "story",
        "masthead": "BİLİYOR MUYDUNUZ?",
        "badge": trv.get("badge", "FUTBOL KÜLTÜRÜ"),
        "headline": trv["headline"],
        "bullets": [trv["body1"], trv["body2"], trv["body3"]],
        "photo": photo,
        "accent": (14, 136, 198),
        "ticker": f"FUTBOL GENEL KÜLTÜRÜ  •  {trv['headline']}",
        "vo": trv["vo"],
    }
    caption = (
        f"🧠 FUTBOL GENEL KÜLTÜRÜ: {trv['headline']} ⚽😲\n\n"
        f"🔹 {trv['body1']}\n"
        f"🔹 {trv['body2']}\n"
        f"🔹 {trv['body3']}\n\n"
        f"💬 Bu ilginç bilgiyi daha önce duymuş muydunuz? Yorumlara yazın!"
    )
    return [spec], caption


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


def build_pre_match_short(target_date: datetime.date) -> Tuple[List[Dict[str, Any]], str]:
    """Maç Önü İstatistikleri & Canlı Büyüyen Graph-Motion Karşılaştırma Barları"""
    recent_titles = fetch_recent_channel_titles(max_results=18)
    matches = _fetch_mackolik_day_matches(target_date)
    upcoming = [m for m in matches if m["status"] in ("", "0", "Başlamadı")] or matches
    if not upcoming:
        return build_headlines_short()

    fresh_upcoming = [
        x for x in upcoming
        if not any(x["home"].lower() in rt and x["away"].lower() in rt for rt in recent_titles)
    ]
    m = fresh_upcoming[0] if fresh_upcoming else upcoming[0]
    h_last5 = fetch_team_last_5_matches(m["home_id"], m["home"], target_date)
    a_last5 = fetch_team_last_5_matches(m["away_id"], m["away"], target_date)

    def calc_stats(l5: List[Dict[str, Any]], tid: int) -> Tuple[List[str], int, int, int, int]:
        forms = [x["result"] for x in l5[:5]]
        w = sum(1 for x in l5 if x["result"] == "G")
        d = sum(1 for x in l5 if x["result"] == "B")
        pts = w * 3 + d
        gf = sum(x["home_goals"] if x["home_id"] == tid else x["away_goals"] for x in l5)
        ga = sum(x["away_goals"] if x["home_id"] == tid else x["home_goals"] for x in l5)
        return forms, w, pts, gf, ga

    h_forms, h_w, h_pts, h_gf, h_ga = calc_stats(h_last5, m["home_id"])
    a_forms, a_w, a_pts, a_gf, a_ga = calc_stats(a_last5, m["away_id"])

    h_crest = fetch_team_crest(m["home_id"], target_size=195)
    a_crest = fetch_team_crest(m["away_id"], target_size=195)

    bars = [
        {"label": "SON 5 MAÇ TOPLANAN PUAN", "home_val": h_pts, "away_val": a_pts, "suffix": " Puan"},
        {"label": "SON 5 MAÇ GALİBİYET SAYISI", "home_val": h_w, "away_val": a_w, "suffix": " Galibiyet"},
        {"label": "SON 5 MAÇ ATILAN GOL", "home_val": h_gf, "away_val": a_gf, "suffix": " Gol"},
        {"label": "SAVUNMA DİRENCİ (YENİLEN GOL)", "home_val": h_ga, "away_val": a_ga, "suffix": " Gol"},
    ]

    vo = (
        f"Maç önü grafik analiz ekranında günün kritik randevusu! "
        f"{m['country']} heyecanında saat {m['time']}'de {m['home']} ile {m['away']} karşı karşıya geliyor! "
        f"Ev sahibi {m['home']} son beş maçında {h_w} galibiyetle {h_pts} puan toplarken rakip ağlara {h_gf} gol gönderdi. "
        f"Konuk ekip {m['away']} ise son beş maçında {a_w} galibiyet, {a_pts} puan ve {a_gf} gol kaydetti! "
        f"Sizce bu mücadeleden hangi takım galip ayrılır? Skor tahminlerinizi yorumlara yazın!"
    )
    spec = {
        "kind": "stats",
        "masthead": "MAÇ ÖNÜ GRAFİK ANALİZ",
        "accent": (210, 145, 12),
        "sub_header": f"{tr_upper(m['country'])}  •  {tr_upper(m['league_sub'])}  •  SAAT {m['time']}",
        "home_name": m["home"],
        "away_name": m["away"],
        "home_crest": h_crest,
        "away_crest": a_crest,
        "center_badge": "VS",
        "home_forms": h_forms,
        "away_forms": a_forms,
        "bars": bars,
        "ticker": f"{m['home']} - {m['away']} MAÇ ÖNÜ FORM VE GOL GRAFİĞİ",
        "vo": vo,
    }
    caption = (
        f"📊 MAÇ ÖNÜ GRAFİK ANALİZ: {m['home']} - {m['away']}! ⚽🔥\n\n"
        f"🏆 {m['country']} - {m['league_sub']} | Saat: {m['time']}\n"
        f"🔹 {m['home']} Son 5 Maç: {h_pts} Puan, {h_w} Galibiyet, {h_gf} Gol\n"
        f"🔹 {m['away']} Son 5 Maç: {a_pts} Puan, {a_w} Galibiyet, {a_gf} Gol\n\n"
        f"💬 Sizce bu karşılaşma kaç kaç biter? Yorumlara tahmininizi yazın!"
    )
    return [spec], caption


def build_post_match_short(target_date: datetime.date) -> Tuple[List[Dict[str, Any]], str]:
    """Günün Maç Sonu Analizi & Kinetik Skor Grafiği"""
    recent_titles = fetch_recent_channel_titles(max_results=18)
    matches = _fetch_mackolik_day_matches(target_date)
    finished = [m for m in matches if m["status"] in ("MS", "Uz.", "Pen.", "Bitti")]
    if not finished:
        yesterday = target_date - datetime.timedelta(days=1)
        finished = [m for m in _fetch_mackolik_day_matches(yesterday) if m["status"] in ("MS", "Uz.", "Pen.", "Bitti")]
    if not finished:
        return build_headlines_short()

    fresh_fin = [
        x for x in finished
        if not any(x["home"].lower() in rt and x["away"].lower() in rt for rt in recent_titles)
    ]
    top = fresh_fin[0] if fresh_fin else finished[0]
    others_raw = [x for x in finished if x["match_id"] != top["match_id"]][:4]

    if top["hg"] > top["ag"]:
        verdict = f"{top['home']} sahadan {top['score']}'lık net galibiyetle ayrıldı!"
    elif top["ag"] > top["hg"]:
        verdict = f"{top['away']} deplasmanda {top['score']} kazanarak kritik bir zafer elde etti!"
    else:
        verdict = f"Büyük çekişmeye sahne olan mücadele {top['score']} eşitlikle sona erdi!"

    other_items = []
    for om in others_raw:
        other_items.append({
            "home": om["home"],
            "away": om["away"],
            "hg": om["hg"],
            "ag": om["ag"],
            "score": om["score"],
            "home_crest": fetch_team_crest(om["home_id"], target_size=80),
            "away_crest": fetch_team_crest(om["away_id"], target_size=80),
        })

    other_spoken = ", ".join([f"{x['home']} {x['hg']}, {x['away']} {x['ag']}" for x in others_raw[:3]])
    vo = (
        f"Maç sonu grafik analiz ekranında günün sonuçları! "
        f"Günün öne çıkan mücadelesinde {verdict} "
        + (f"Tamamlanan diğer karşılaşmalarda ise {other_spoken} skorları kaydedildi. " if other_spoken else "")
        + "Maçın yıldızı sizce kimdi? Yorumlarda değerlendirelim!"
    )
    spec = {
        "kind": "stats",
        "masthead": "MAÇ SONU SKOR GRAFİĞİ",
        "accent": ACCENT_RED,
        "sub_header": f"MAÇ SONUCU  •  {tr_upper(top['country'])}",
        "home_name": top["home"],
        "away_name": top["away"],
        "home_crest": fetch_team_crest(top["home_id"], target_size=195),
        "away_crest": fetch_team_crest(top["away_id"], target_size=195),
        "center_badge": top["score"],
        "verdict": verdict,
        "other_matches": other_items,
        "ticker": f"MAÇ SONUCU: {top['home']} {top['score']} {top['away']}",
        "vo": vo,
    }
    other_lines = "\n".join([f"⚽ {x['home']} {x['score']} {x['away']}" for x in others_raw])
    caption = (
        f"🏁 MAÇ SONU ANALİZİ: {top['home']} {top['score']} {top['away']}! ⚽🔥\n\n"
        f"📌 {verdict}\n"
        + (f"\n📊 Günün Diğer Sonuçları:\n{other_lines}\n" if other_lines else "")
        + "\n💬 Karşılaşmanın performansını nasıl buldunuz? Yorumlara yazın!"
    )
    return [spec], caption


def render_subscribe_outro_frame(frame: Image.Image, draw: ImageDraw.ImageDraw, elapsed: float, dur: float) -> None:
    """
    Son 2.8 saniyede bahis/bayi ekranı yerine şık 'KANALA ABONE OL & BİLDİRİMLERİ AÇ' kartı çizer.
    """
    prog = ease_out_back(min(1.0, elapsed / 0.45))
    cx, cy = WIDTH // 2, HEIGHT // 2
    cw = max(40, int(900 * prog))
    ch = max(40, int(680 * prog))
    x1, y1, x2, y2 = cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2

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
    outro_bg = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK_BOT)
    outro_bg_draw = ImageDraw.Draw(outro_bg)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 * (1 - ratio) + 4 * ratio)
        g = int(18 * (1 - ratio) + 8 * ratio)
        b = int(38 * (1 - ratio) + 18 * ratio)
        outro_bg_draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
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
            frame = outro_bg.copy()
            draw = ImageDraw.Draw(frame)
            render_subscribe_outro_frame(frame, draw, t - main_dur, outro_dur)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    stderr_bytes = proc.stderr.read() if proc.stderr else b""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası:\n{stderr_bytes.decode('utf-8', errors='ignore')}")
    return out_mp4


def render_multi_scene_short_mp4(scenes: List[Tuple[Path, str]], out_mp4: Path) -> Path:
    """
    Birden fazla haber sahnesini (her biri kendi basın fotoğrafı, detaylı bilgi kartı ve spiker sesiyle)
    birebir saniye senkronlu olarak birleştirir, yumuşak geçiş ekler ve 'Abone Ol' kartıyla bitirir.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    vo_sub_path = OUTPUT_DIR / "vo_subscribe_outro.mp3"
    if not vo_sub_path.exists() or vo_sub_path.stat().st_size < 1000:
        asyncio.run(generate_tts(SUBSCRIBE_VOICEOVER, vo_sub_path))
    outro_dur = max(2.8, get_audio_duration(vo_sub_path) + 0.35)

    seg_records: List[Tuple[Image.Image, Path, float]] = []
    for idx, (p_path, seg_vo) in enumerate(scenes):
        seg_mp3 = OUTPUT_DIR / f"vo_{out_mp4.stem}_seg_{idx}.mp3"
        asyncio.run(generate_tts(seg_vo, seg_mp3))
        dur = max(4.0, get_audio_duration(seg_mp3) + 0.35)
        p_img = Image.open(p_path).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        seg_records.append((p_img, seg_mp3, dur))

    # 3 sahneli bülten 57.5 saniyeyi aşarsa ve 3 sahne varsa, süreyi hızlandırmadan önce kontrol et;
    # ensure_shorts_duration hafif tempo ayarıyla <57.5 sn garantisi verir.
    main_dur = sum(x[2] for x in seg_records)
    total_dur = main_dur + outro_dur
    total_frames = int(math.ceil(total_dur * FPS))

    outro_bg = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK_BOT)
    outro_bg_draw = ImageDraw.Draw(outro_bg)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(10 * (1 - ratio) + 4 * ratio)
        g = int(18 * (1 - ratio) + 8 * ratio)
        b = int(38 * (1 - ratio) + 18 * ratio)
        outro_bg_draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Her sahnenin sesini kendi başlangıç milisaniyesine yerleştir
    input_args: List[str] = []
    filter_parts: List[str] = [
        f"aevalsrc='0.11*sin(2*PI*65*t)*exp(-3.2*mod(t,0.5))+0.04*sin(2*PI*196*t)*exp(-5.5*mod(t,0.25))'"
        f":s=44100:d={total_dur:.2f}[bgm]"
    ]
    mix_labels = ["[bgm]"]
    elapsed_cursor = 0.0

    for idx, (_, seg_mp3, seg_dur) in enumerate(seg_records):
        input_args.extend(["-i", str(seg_mp3)])
        in_idx = idx + 1
        delay_ms = int(round(elapsed_cursor * 1000))
        lbl = f"[vo{idx}]"
        if delay_ms > 0:
            filter_parts.append(f"[{in_idx}:a]aresample=44100,volume=1.95,adelay={delay_ms}|{delay_ms}{lbl}")
        else:
            filter_parts.append(f"[{in_idx}:a]aresample=44100,volume=1.95{lbl}")
        mix_labels.append(lbl)
        elapsed_cursor += seg_dur

    input_args.extend(["-i", str(vo_sub_path)])
    sub_in_idx = len(seg_records) + 1
    sub_delay_ms = int(round(main_dur * 1000))
    filter_parts.append(f"[{sub_in_idx}:a]aresample=44100,volume=1.95,adelay={sub_delay_ms}|{sub_delay_ms}[vosub]")
    mix_labels.append("[vosub]")

    filter_parts.append(
        f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=first:dropout_transition=0,"
        f"alimiter=limit=0.95[aout]"
    )
    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-t", f"{total_dur:.2f}",
        str(out_mp4),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    # Sahne zaman aralıklarını hazırla
    bounds: List[Tuple[float, float, Image.Image]] = []
    cur_t = 0.0
    for p_img, _, seg_dur in seg_records:
        bounds.append((cur_t, cur_t + seg_dur, p_img))
        cur_t += seg_dur

    for f_idx in range(total_frames):
        t = f_idx / FPS
        if t < main_dur:
            active_idx = len(bounds) - 1
            for b_i, (st_t, en_t, _) in enumerate(bounds):
                if st_t <= t < en_t:
                    active_idx = b_i
                    break
            st_t, en_t, base_img = bounds[active_idx]
            local_t = t - st_t
            seg_len = max(0.2, en_t - st_t)

            zoom = 1.0 + 0.026 * math.sin((local_t / seg_len) * math.pi)
            zw, zh = int(WIDTH * zoom), int(HEIGHT * zoom)
            resized = base_img.resize((zw, zh), Image.Resampling.BILINEAR)
            ox, oy = (zw - WIDTH) // 2, (zh - HEIGHT) // 2
            frame = resized.crop((ox, oy, ox + WIDTH, oy + HEIGHT))

            # Sahne geçişinde 0.22 sn yumuşak crossfade
            if active_idx > 0 and local_t < 0.22:
                prev_img = bounds[active_idx - 1][2]
                alpha = local_t / 0.22
                frame = Image.blend(prev_img, frame, alpha)

            draw = ImageDraw.Draw(frame)
            bar_w = int((WIDTH - 96) * min(1.0, t / max(0.1, total_dur)))
            if bar_w > 4:
                draw.rounded_rectangle([48, HEIGHT - 84, 48 + bar_w, HEIGHT - 77], radius=3, fill=ACCENT_GOLD)
        else:
            frame = outro_bg.copy()
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

    specs: List[Dict[str, Any]]
    if args.mode == "headlines":
        specs, cap = build_headlines_short()
    elif args.mode == "biography":
        specs, cap = build_biography_short(target_date)
    elif args.mode == "breaking":
        specs, cap = build_breaking_short()
    elif args.mode == "trivia":
        specs, cap = build_trivia_short(target_date)
    elif args.mode == "pre_match":
        specs, cap = build_pre_match_short(target_date)
    else:
        specs, cap = build_post_match_short(target_date)

    out_video = OUTPUT_DIR / f"yt_short_{args.mode}.mp4"
    print(f"[1/2] '{args.mode}' kategorisinde ({len(specs)} sahneli Graph-Motion) Spor Shorts üretiliyor...")
    render_graph_motion_mp4(specs, out_video)
    print(f"[OK] Graph-Motion video hazır: {out_video}")

    if args.upload:
        upload_short(out_video, cap)


if __name__ == "__main__":
    main()
