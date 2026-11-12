"""
📱 SMS Bot v3 - Kişiselleştirilmiş & Tasarruflu
─────────────────────────────────────────────
İçerikler:
  ☀️ Hava durumu (her sabah)
  💬 Motivasyon sözü (her sabah)
  📖 İngilizce kelime (her akşam)
  🎮 Teknoloji haberi (her akşam, gün dönüşümlü)
  ⚽ GS/FB/BJK/Türkiye maç skoru (SADECE maç varsa!)

Günde max 2 SMS = 100 SMS ile 50 gün
Maç olmayan gün = 1 SMS = daha da tasarruf!
"""

import os
import json
import hashlib
import urllib.request
import urllib.parse
import base64
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ── Ayarlar ────────────────────────────────────────────────────
TWILIO_SID   = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")
TWILIO_FROM  = os.environ.get("TWILIO_FROM", "")
MY_PHONE     = os.environ.get("MY_PHONE", "")
SEHIR        = os.environ.get("SEHIR", "Istanbul")

# API-Football (RapidAPI) - ucretsiz, 50 istek/gun
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")

# Takip edilen takimlar (API-Football team ID'leri)
TAKIMLAR = {
    "Galatasaray": 645,
    "Fenerbahce": 611,
    "Besiktas": 549,
    "Turkey": 1,  # Milli takim (fixture'da country olarak)
}

# ── Yardimcilar ────────────────────────────────────────────────
TR = str.maketrans("çÇğĞıİöÖşŞüÜâÂîÎûÛ", "cCgGiIoOsSuUaAiIuU")

def tr(t):
    return t.translate(TR).replace("\n"," ").replace("  "," ").strip()

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_cache.json")

def cache_load():
    try:
        with open(CACHE_PATH) as f: return set(json.load(f))
    except: return set()

def cache_save(s):
    with open(CACHE_PATH,"w") as f: json.dump(list(s)[-300:], f)

def h(t):
    return hashlib.md5(t.encode()).hexdigest()[:10]

# ── RSS ────────────────────────────────────────────────────────
def rss_al(url, n=2):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Bot/3"})
        with urllib.request.urlopen(req, timeout=12) as r:
            root = ET.parse(r).getroot()
        sonuc = []
        for item in root.iter("item"):
            t = item.findtext("title","").strip()
            if t:
                sonuc.append(tr(t))
            if len(sonuc) >= n: break
        return sonuc
    except: return []

# ── Hava Durumu ────────────────────────────────────────────────
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
    lat,lon = KOORD.get(SEHIR,(41.01,28.98))
    url = (f"https://api.open-meteo.com/v1/forecast?"
           f"latitude={lat}&longitude={lon}"
           f"&current=temperature_2m,weather_code"
           f"&daily=temperature_2m_max,temperature_2m_min"
           f"&timezone=Europe/Istanbul&forecast_days=2")
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Bot/3"})
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read())
        c = d["current"]; dy = d["daily"]
        t = int(c["temperature_2m"])
        durum = HKOD.get(c["weather_code"],"?")
        mn = int(dy["temperature_2m_min"][0])
        mx = int(dy["temperature_2m_max"][0])
        y_mn = int(dy["temperature_2m_min"][1])
        y_mx = int(dy["temperature_2m_max"][1])
        return f"{SEHIR} {t}C {durum} {mn}/{mx} Yarin:{y_mn}/{y_mx}"
    except: return None

# ── Motivasyon Sozu ────────────────────────────────────────────
def soz():
    items = rss_al("http://www.quotationspage.com/data/qotd.rss", 1)
    if items:
        s = items[0]
        return s[:65] + "..." if len(s) > 65 else s
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
        "Yapamiyorum diyen yapmak istemiyordur",
        "Bugunku kucuk adim yarinin buyuk zaferi",
    ])

# ── Ingilizce Kelime ───────────────────────────────────────────
def ingilizce():
    items = rss_al("https://www.merriam-webster.com/wotd/feed", 1)
    if items:
        w = items[0]
        return w[:55] + "..." if len(w) > 55 else w
    return None

# ── Teknoloji ──────────────────────────────────────────────────
def teknoloji():
    items = rss_al("https://www.log.com.tr/feed/", 2)
    if items:
        t = items[0]
        return t[:65] + "..." if len(t) > 65 else t
    return None

# ── MAC SKORLARI (API-Football) ───────────────────────────────
# GS=645, FB=611, BJK=549 | Turkiye milli=1
# Sadece bugun bitmis mac varsa SMS gelir, yoksa gelmez!

def mac_skorlari():
    """Bugün oynanan GS/FB/BJK/Türkiye maçlarının sonuçlarını döndürür."""
    if not RAPIDAPI_KEY:
        print("  [!] RAPIDAPI_KEY yok, mac skoru atlanıyor")
        return []

    tz = timezone(timedelta(hours=3))
    bugun = datetime.now(tz).strftime("%Y-%m-%d")
    skorlar = []

    team_ids = [645, 611, 549]  # GS, FB, BJK

    for team_id in team_ids:
        url = (f"https://api-football-v1.p.rapidapi.com/v3/fixtures?"
               f"date={bugun}&team={team_id}&status=FT-AET-PEN")
        try:
            req = urllib.request.Request(url)
            req.add_header("x-rapidapi-host", "api-football-v1.p.rapidapi.com")
            req.add_header("x-rapidapi-key", RAPIDAPI_KEY)
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.loads(r.read())

            for mac in data.get("response", []):
                ev = mac["teams"]["home"]["name"]
                dep = mac["teams"]["away"]["name"]
                ev_g = mac["goals"]["home"]
                dep_g = mac["goals"]["away"]

                # Takım adlarını kısalt
                ev_k = kisalt(ev)
                dep_k = kisalt(dep)

                skorlar.append(f"{ev_k} {ev_g}-{dep_g} {dep_k}")
        except Exception as e:
            print(f"  [!] Mac API hatasi (team {team_id}): {e}")

    # Turkiye milli takim
    url_tr = (f"https://api-football-v1.p.rapidapi.com/v3/fixtures?"
              f"date={bugun}&team=1&status=FT-AET-PEN")
    try:
        req = urllib.request.Request(url_tr)
        req.add_header("x-rapidapi-host", "api-football-v1.p.rapidapi.com")
        req.add_header("x-rapidapi-key", RAPIDAPI_KEY)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        for mac in data.get("response", []):
            ev = mac["teams"]["home"]["name"]
            dep = mac["teams"]["away"]["name"]
            ev_g = mac["goals"]["home"]
            dep_g = mac["goals"]["away"]
            ev_k = kisalt(ev)
            dep_k = kisalt(dep)
            skorlar.append(f"{ev_k} {ev_g}-{dep_g} {dep_k}")
    except Exception as e:
        print(f"  [!] Milli takim API hatasi: {e}")

    # Tekrar eden maçları kaldır
    return list(dict.fromkeys(skorlar))

def kisalt(takim):
    """Takım adlarını kısaltır."""
    kisaltmalar = {
        "Galatasaray": "GS",
        "Fenerbahce": "FB", "Fenerbahçe": "FB",
        "Besiktas": "BJK", "Beşiktaş": "BJK",
        "Turkey": "TR", "Türkiye": "TR", "Turkiye": "TR",
    }
    for uzun, kisa in kisaltmalar.items():
        if uzun.lower() in takim.lower():
            return kisa
    # Bilinmeyen takım: ilk 3 harf
    return tr(takim)[:8]

# ── SMS Gonder ─────────────────────────────────────────────────
def sms_gonder(mesaj):
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, MY_PHONE]):
        print(f"[!] Twilio eksik!"); return False

    if len(mesaj) > 155:
        mesaj = mesaj[:152] + "..."

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    params = urllib.parse.urlencode({
        "To": MY_PHONE, "From": TWILIO_FROM, "Body": mesaj,
    }).encode()
    cred = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
    req = urllib.request.Request(url, data=params, method="POST")
    req.add_header("Authorization", f"Basic {cred}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
            print(f"  [OK] SMS -> {res.get('sid','?')}")
            return True
    except Exception as e:
        print(f"  [HATA] {e}"); return False

# ══════════════════════════════════════════════════════════════
#  PROGRAM: Gunluk 2 SMS (mac varsa 3)
#
#  SABAH 07:00 → Hava + Soz                    (1 SMS, her gun)
#  AKSAM 21:00 → Ingilizce/Teknoloji donus      (1 SMS, her gun)
#  AKSAM 22:00 → Mac skoru SADECE mac varsa!     (0 veya 1 SMS)
#
#  Mac olmayan gun  = 2 SMS  → 100/2 = 50 gun
#  Mac olan gun     = 3 SMS  → biraz daha az
#  Ortalama ~2.3 SMS/gun     → ~43 gun
# ══════════════════════════════════════════════════════════════

def main():
    tz = timezone(timedelta(hours=3))
    now = datetime.now(tz)
    tarih = now.strftime("%Y%m%d")
    saat = now.hour
    gun = now.weekday()
    gun_adi = ["Pzt","Sal","Car","Per","Cum","Cmt","Paz"][gun]

    print(f"\n{'='*50}")
    print(f"  SMS Bot v3 | {now.strftime('%d.%m.%Y %H:%M')} {gun_adi}")
    print(f"{'='*50}")

    cache = cache_load()
    sms_sayisi = 0

    utc_saat = now.utcnow().hour

    # ── SABAH (UTC 04 = TR 07) ─────────────────────────────────
    if utc_saat in [3, 4, 5]:
        print("\n[SABAH] Hava + Soz")
        parcalar = []

        h_txt = hava()
        if h_txt:
            parcalar.append(h_txt)

        s_txt = soz()
        if s_txt:
            # Kalan alana sığdır
            kalan = 155 - len("|".join(parcalar)) - 2 if parcalar else 155
            if len(s_txt) > kalan:
                s_txt = s_txt[:kalan-3] + "..."
            parcalar.append(f">{s_txt}")

        if parcalar:
            mesaj = "|".join(parcalar)
            key = h(f"sabah_{tarih}")
            if key not in cache:
                print(f"  [{len(mesaj)} kr] {mesaj}")
                if sms_gonder(mesaj):
                    cache.add(key)
                    sms_sayisi += 1
            else:
                print("  Bugun zaten gonderildi")

    # ── AKSAM (UTC 16-17 = TR 19-20) ──────────────────────────
    elif utc_saat in [16, 17]:
        # 1) Ingilizce / Teknoloji (donusumlu)
        print(f"\n[AKSAM] Bonus ({gun_adi})")
        parcalar = []

        if gun % 2 == 0:  # Cift gunler: Ingilizce
            ing = ingilizce()
            if ing:
                parcalar.append(f"ENG:{ing}")
        else:  # Tek gunler: Teknoloji
            tek = teknoloji()
            if tek:
                parcalar.append(f"TEK:{tek}")

        # Kalan alana soz ekle
        if parcalar:
            kalan = 155 - len("|".join(parcalar)) - 2
            s_txt = soz()
            if s_txt and len(s_txt) + 2 <= kalan:
                if len(s_txt) > kalan - 2:
                    s_txt = s_txt[:kalan-5] + "..."
                parcalar.append(f">{s_txt}")

        if parcalar:
            mesaj = "|".join(parcalar)
            key = h(f"aksam_{tarih}")
            if key not in cache:
                print(f"  [{len(mesaj)} kr] {mesaj}")
                if sms_gonder(mesaj):
                    cache.add(key)
                    sms_sayisi += 1
            else:
                print("  Bugun zaten gonderildi")

        # 2) Mac skorlari (SADECE mac varsa SMS gider!)
        print(f"\n[MAC] GS/FB/BJK/TR skor kontrolu")
        skorlar = mac_skorlari()

        if skorlar:
            mesaj = "SKOR|" + "|".join(skorlar)
            if len(mesaj) > 155:
                mesaj = mesaj[:152] + "..."
            key = h(f"mac_{tarih}")
            if key not in cache:
                print(f"  [{len(mesaj)} kr] {mesaj}")
                if sms_gonder(mesaj):
                    cache.add(key)
                    sms_sayisi += 1
            else:
                print("  Mac skoru zaten gonderildi")
        else:
            print("  Bugun GS/FB/BJK/TR maci yok, SMS gonderilmiyor")

    # ── TEST (manuel workflow_dispatch) ────────────────────────
    else:
        print(f"\n[TEST] Saat {saat}")
        mesaj = sabah_test(tarih)
        if mesaj:
            key = h(f"test_{tarih}_{saat}")
            if key not in cache:
                if sms_gonder(mesaj):
                    cache.add(key)
                    sms_sayisi += 1

    cache_save(cache)

    # İstatistik
    toplam = len(cache)
    kalan = max(0, 100 - toplam)
    print(f"\n  Bugun gonderilen: {sms_sayisi}")
    print(f"  Toplam gonderilen: {toplam}")
    print(f"  Kalan SMS: ~{kalan}")
    print(f"  Tahmini gun: ~{kalan // 2}")
    print(f"{'='*50}\n")


def sabah_test(tarih):
    """Test modu icin sabah SMS'i"""
    parcalar = []
    h_txt = hava()
    if h_txt: parcalar.append(h_txt)
    s_txt = soz()
    if s_txt: parcalar.append(f">{s_txt}")
    return "|".join(parcalar) if parcalar else None


if __name__ == "__main__":
    main()
