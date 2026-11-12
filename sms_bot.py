"""
📱 SMS Bot v4 - Sıfır Ekstra Üyelik & Ultra Tasarruflu
─────────────────────────────────────────────────────
İçerikler:
  ☀️ Hava durumu (her sabah)
  💬 Motivasyon sözü (her sabah)
  📖 İngilizce kelime (akşamları dönüşümlü)
  🎮 Teknoloji haberi (akşamları dönüşümlü)
  ⚽ GS, FB, BJK ve Türkiye maç skorları (ESPN Açık API - Şifresiz/Keysiz)
     -> SADECE maç bitmişse ve bugün oynandıysa SMS gider!
"""

import os
import json
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import base64
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ── Ayarlar (GitHub Secrets'tan) ───────────────────────────────
TWILIO_SID   = os.environ.get("TWILIO_SID", "").strip()
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "").strip()
TWILIO_FROM  = os.environ.get("TWILIO_FROM", "").strip()
MY_PHONE     = os.environ.get("MY_PHONE", "").strip()
SEHIR        = os.environ.get("SEHIR", "Istanbul").strip()

# ── Telefon Numarası Format Temizleyici (E.164 Düzeltici) ───────
def format_phone(phone_str, default_tr=True):
    """
    Telefon numarasını Twilio'nun istediği E.164 formatına (+905321234567) çevirir.
    Boşluk, parantez veya eksik +90 hatalarını otomatik düzeltir.
    """
    if not phone_str:
        return ""
    p = phone_str.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").strip()
    if p.startswith("+"):
        return p
    if p.startswith("00"):
        return "+" + p[2:]
    if default_tr:
        if p.startswith("0") and len(p) == 11:  # 0532xxxxxxx
            return "+90" + p[1:]
        elif p.startswith("5") and len(p) == 10:  # 532xxxxxxx
            return "+90" + p
        elif p.startswith("90"):
            return "+" + p
    return "+" + p

# ── Karakter Dönüştürme (SMS tasarrufu ve ASCII temizliği) ─────
TR = str.maketrans("çÇğĞıİöÖşŞüÜâÂîÎûÛ", "cCgGiIoOsSuUaAiIuU")

def tr(t):
    if not t: return ""
    # Akıllı tırnak ve tire işaretlerini düzelt
    t = str(t).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    t = t.translate(TR)
    # Sadece standart ASCII karakterleri bırak (Twilio 400 ve segment patlamasını engeller)
    t = "".join(c for c in t if 32 <= ord(c) < 127)
    return t.replace("  ", " ").strip()

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_cache.json")

def cache_load():
    try:
        with open(CACHE_PATH) as f: return set(json.load(f))
    except: return set()

def cache_save(s):
    with open(CACHE_PATH, "w") as f: json.dump(list(s)[-300:], f)

def h(t):
    return hashlib.md5(t.encode()).hexdigest()[:10]

# ── RSS Okuyucu ────────────────────────────────────────────────
def rss_al(url, n=2):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            root = ET.parse(r).getroot()
        sonuc = []
        for item in root.iter("item"):
            t = item.findtext("title", "").strip()
            if t:
                sonuc.append(tr(t))
            if len(sonuc) >= n: break
        return sonuc
    except: return []

# ── Hava Durumu (Open-Meteo, Key istemez) ──────────────────────
KOORD = {
    "Istanbul":(41.01,28.98),"Ankara":(39.93,32.86),
    "Izmir":(38.42,27.13),"Antalya":(36.90,30.69),
    "Bursa":(40.19,29.06),"Adana":(37.00,35.32),
    "Trabzon":(41.00,39.72),"Konya":(37.87,32.48),
    "Gaziantep":(37.06,37.38),"Samsun":(41.29,36.33),
    "Diyarbakir":(37.91,40.22),"Kayseri":(38.73,35.49),
    "Eskisehir":(39.78,30.52),"Mersin":(36.80,34.63),
    "Erzurum":(39.90,41.27),
}
HKOD = {
    0:"Acik",1:"Az bulut",2:"Parcali",3:"Kapali",
    45:"Sis",48:"Sis",51:"Cise",53:"Cise",55:"Cise",
    61:"Yagmur",63:"Yagmur",65:"Saganak",71:"Kar",73:"Kar",
    75:"Kar+",80:"Saganak",81:"Saganak",82:"Saganak+",
    95:"Firtina",96:"Dolu",99:"Dolu",
}

def hava():
    lat, lon = KOORD.get(SEHIR, (41.01, 28.98))
    url = (f"https://api.open-meteo.com/v1/forecast?"
           f"latitude={lat}&longitude={lon}"
           f"&current=temperature_2m,weather_code"
           f"&daily=temperature_2m_max,temperature_2m_min"
           f"&timezone=Europe/Istanbul&forecast_days=2")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read())
        c = d["current"]; dy = d["daily"]
        t = int(c["temperature_2m"])
        durum = HKOD.get(c["weather_code"], "?")
        mn = int(dy["temperature_2m_min"][0])
        mx = int(dy["temperature_2m_max"][0])
        y_mn = int(dy["temperature_2m_min"][1])
        y_mx = int(dy["temperature_2m_max"][1])
        return f"{SEHIR} {t}C {durum} {mn}/{mx} Yarin:{y_mn}/{y_mx}"
    except: return None

# ── Motivasyon Sözü ────────────────────────────────────────────
def soz():
    items = rss_al("http://www.quotationspage.com/data/qotd.rss", 1)
    if items:
        s = items[0]
        return s[:60] + "..." if len(s) > 60 else s
    import random
    return random.choice([
        "Basarinin sirri baslamaktir -Mark Twain",
        "Hayat cesaret isteyenlere guler",
        "Buyuk isler kucuk adimlarla baslar",
        "Her usta bir zamanlar ogrenciydi",
        "Bilgi gucdur -Francis Bacon",
        "Hayal et, inan, basla",
        "Dusmeyen kalkmaz",
        "En karanlik gece bile sabahla biter",
        "Bugunku kucuk adim yarinin buyuk zaferi",
    ])

# ── İngilizce Kelime ───────────────────────────────────────────
def ingilizce():
    items = rss_al("https://www.merriam-webster.com/wotd/feed", 1)
    if items:
        w = items[0]
        return w[:50] + "..." if len(w) > 50 else w
    return None

# ── Teknoloji Haberi ───────────────────────────────────────────
def teknoloji():
    items = rss_al("https://www.log.com.tr/feed/", 2)
    if items:
        t = items[0]
        return t[:60] + "..." if len(t) > 60 else t
    return None

# ── ESPN AÇIK API: MAÇ SKORLARI ────────────────────────────────
LIGLER = [
    "tur.1",             # Trendyol Süper Lig
    "uefa.champions",    # Şampiyonlar Ligi
    "uefa.europa",       # UEFA Avrupa Ligi
    "uefa.europa.conf",  # Konferans Ligi
    "uefa.nations",      # Uluslar Ligi
    "fifa.friendly",     # Hazırlık Maçları
    "fifa.worldq.uefa",  # Dünya Kupası Elemeleri
    "uefa.euroq",        # Avrupa Şampiyonası Elemeleri
]

HEDEF_TAKIMLAR = {
    "galatasaray": "GS",
    "fenerbahce": "FB",
    "besiktas": "BJK",
    "turkey": "TR",
    "turkiye": "TR"
}

def kisalt_isim(isim):
    t_low = tr(isim).lower()
    for anahtar, kisa in HEDEF_TAKIMLAR.items():
        if anahtar in t_low:
            return kisa
    return tr(isim)[:6].strip()

def mac_skorlari():
    """Bugün oynanıp BİTMİŞ GS/FB/BJK/Türkiye maç sonuçlarını çeker."""
    tz = timezone(timedelta(hours=3))
    bugun_str = datetime.now(tz).strftime("%Y%m%d")
    skorlar = []

    for lig in LIGLER:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lig}/scoreboard?dates={bugun_str}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            
            for event in data.get("events", []):
                status_info = event.get("status", {}).get("type", {})
                is_completed = status_info.get("completed", False)
                state = status_info.get("state", "")

                if not (is_completed or state == "post"):
                    continue

                comps = event.get("competitions", [])
                if not comps: continue
                competitors = comps[0].get("competitors", [])
                if len(competitors) < 2: continue

                t1_name = competitors[0].get("team", {}).get("displayName", "")
                t2_name = competitors[1].get("team", {}).get("displayName", "")
                t1_score = competitors[0].get("score", "0")
                t2_score = competitors[1].get("score", "0")

                t1_low = tr(t1_name).lower()
                t2_low = tr(t2_name).lower()

                ilgili = any(k in t1_low or k in t2_low for k in HEDEF_TAKIMLAR.keys())
                if ilgili:
                    kisa1 = kisalt_isim(t1_name)
                    kisa2 = kisalt_isim(t2_name)
                    mac_sonuc = f"{kisa1} {t1_score}-{t2_score} {kisa2}"
                    if mac_sonuc not in skorlar:
                        skorlar.append(mac_sonuc)
        except Exception:
            continue

    return skorlar

# ── SMS Gönderici ──────────────────────────────────────────────
def sms_gonder(mesaj):
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, MY_PHONE]):
        print("[!] Twilio ayarlari eksik!")
        print(f"    TWILIO_SID: {'VAR' if TWILIO_SID else 'YOK'}")
        print(f"    TWILIO_TOKEN: {'VAR' if TWILIO_TOKEN else 'YOK'}")
        print(f"    TWILIO_FROM: {'VAR' if TWILIO_FROM else 'YOK'}")
        print(f"    MY_PHONE: {'VAR' if MY_PHONE else 'YOK'}")
        return False

    # Numara formatlarını garantiye al
    to_phone = format_phone(MY_PHONE, default_tr=True)
    from_phone = format_phone(TWILIO_FROM, default_tr=False)

    # 160 karaktere sığdır
    temiz_mesaj = tr(mesaj)
    if len(temiz_mesaj) > 155:
        temiz_mesaj = temiz_mesaj[:152] + "..."

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    params = urllib.parse.urlencode({
        "To": to_phone,
        "From": from_phone,
        "Body": temiz_mesaj,
    }).encode("utf-8")

    cred = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
    req = urllib.request.Request(url, data=params, method="POST")
    req.add_header("Authorization", f"Basic {cred}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
            print(f"  [OK] SMS basariyla iletildi -> SID: {res.get('sid','?')}")
            return True
    except urllib.error.HTTPError as e:
        hata_metni = e.read().decode("utf-8", errors="ignore")
        print(f"  [HATA] Twilio HTTP {e.code}: {hata_metni}")
        try:
            hata_json = json.loads(hata_metni)
            print(f"  [!] Hata Mesaji: {hata_json.get('message')}")
            print(f"  [!] Hata Kodu: {hata_json.get('code')}")
        except:
            pass
        return False
    except Exception as e:
        print(f"  [HATA] Beklenmeyen hata: {e}")
        return False

# ══════════════════════════════════════════════════════════════
#  ÇALIŞMA DÖNGÜSÜ
# ══════════════════════════════════════════════════════════════
def main():
    tz = timezone(timedelta(hours=3))
    now = datetime.now(tz)
    tarih = now.strftime("%Y%m%d")
    gun = now.weekday()
    gun_adi = ["Pzt","Sal","Car","Per","Cum","Cmt","Paz"][gun]

    print(f"\n{'='*50}")
    print(f"  SMS Bot v4.1 | {now.strftime('%d.%m.%Y %H:%M')} {gun_adi}")
    print(f"{'='*50}")

    cache = cache_load()
    utc_saat = datetime.now(timezone.utc).hour
    sms_sayisi = 0

    # ── 1) SABAH (UTC 04 = TR 07:00) -> Hava Durumu + Motivasyon ──
    if utc_saat in [3, 4, 5]:
        print("\n[SABAH] Hava + Soz")
        parcalar = []
        h_txt = hava()
        if h_txt: parcalar.append(h_txt)
        s_txt = soz()
        if s_txt:
            kalan = 155 - len("|".join(parcalar)) - 2 if parcalar else 155
            if len(s_txt) > kalan: s_txt = s_txt[:kalan-3] + "..."
            parcalar.append(f">{s_txt}")

        if parcalar:
            mesaj = "|".join(parcalar)
            key = h(f"sabah_{tarih}")
            if key not in cache:
                print(f"  Gonderiliyor ({len(mesaj)} kr): {mesaj}")
                if sms_gonder(mesaj):
                    cache.add(key)
                    sms_sayisi += 1
            else:
                print("  Bugun sabah SMS'i zaten gitti.")

    # ── 2) AKŞAM (UTC 17 = TR 20:00) -> İngilizce/Teknoloji + MAÇ ──
    elif utc_saat in [16, 17, 18]:
        print(f"\n[AKSAM] Bonus ({gun_adi})")
        parcalar = []
        if gun % 2 == 0:
            ing = ingilizce()
            if ing: parcalar.append(f"ENG:{ing}")
        else:
            tek = teknoloji()
            if tek: parcalar.append(f"TEK:{tek}")

        s_txt = soz()
        if s_txt:
            kalan = 155 - len("|".join(parcalar)) - 2 if parcalar else 155
            if len(s_txt) + 2 <= kalan:
                parcalar.append(f">{s_txt}")

        if parcalar:
            mesaj = "|".join(parcalar)
            key = h(f"aksam_{tarih}")
            if key not in cache:
                print(f"  Gonderiliyor ({len(mesaj)} kr): {mesaj}")
                if sms_gonder(mesaj):
                    cache.add(key)
                    sms_sayisi += 1
            else:
                print("  Bugun aksam SMS'i zaten gitti.")

        # ── MAÇ SKORU KONTROLÜ (SADECE BİTEN MAÇ VARSA!) ──
        print("\n[MAC KONTROL] GS / FB / BJK / Turkiye kontrol ediliyor...")
        skorlar = mac_skorlari()
        if skorlar:
            mesaj = "SKOR|" + "|".join(skorlar)
            key = h(f"mac_{tarih}_{'-'.join(skorlar)}")
            if key not in cache:
                print(f"  Biten mac bulundu: {mesaj}")
                if sms_gonder(mesaj):
                    cache.add(key)
                    sms_sayisi += 1
            else:
                print("  Bu mac skoru daha once gonderildi.")
        else:
            print("  Bugun bitmis GS/FB/BJK/TR maci yok. SMS tasarrufu saglandi!")

    # ── 3) TEST ÇALIŞTIRMASI (Manuel tetikleme için) ──
    else:
        print("\n[MANUEL TEST]")
        parcalar = []
        h_txt = hava()
        if h_txt: parcalar.append(h_txt)
        s_txt = soz()
        if s_txt: parcalar.append(f">{s_txt}")
        mesaj = "|".join(parcalar)
        key = h(f"test_{tarih}_{utc_saat}")
        if key not in cache:
            if sms_gonder(mesaj):
                cache.add(key)
                sms_sayisi += 1

    cache_save(cache)
    print(f"\nTamamlandi. Toplam {sms_sayisi} SMS gonderildi.\n{'='*50}")

if __name__ == "__main__":
    main()
