import time
import requests
from curl_cffi import requests as cffi_requests

TELEGRAM_TOKEN = "7913644987:AAGf3SGA8ixaxw2rsjinQ0j-aZ7cGp0l7u8"
CHAT_ID = "7361590854"

SEARCH_URL = "https://www.vinted.pl/api/v2/catalog/items?page=1&per_page=10&price_to=40&search_text=nike&order=newest_first"

seen_ids = set()

def send_telegram_notification(title, price, url, photo_url):
    msg = (
        f"🔥 <b>NOWA OKAZJA NA VINTED!</b>\n\n"
        f"📌 <b>Przedmiot:</b> {title}\n"
        f"💰 <b>Cena:</b> {price} zł\n\n"
        f"🔗 <a href='{url}'>KUP TERAZ NA VINTED</a>"
    )
    telegram_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "caption": msg,
        "parse_mode": "HTML",
        "photo": photo_url if photo_url else "https://via.placeholder.com/300"
    }
    try:
        requests.post(telegram_api, data=payload)
    except Exception as e:
        print(f"Błąd Telegram: {e}")

def check_vinted():
    session = cffi_requests.Session(impersonate="chrome120")
    session.get("https://www.vinted.pl")
    response = session.get(SEARCH_URL)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        for item in reversed(items):
            item_id = item["id"]
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                title = item.get("title", "Brak tytułu")
                price = item.get("price", {}).get("amount", "??")
                item_url = item.get("url")
                photos = item.get("photos", [])
                photo_url = photos[0].get("url") if photos else None
                
                print(f"[+] Nowa oferta: {title} - {price} zł")
                send_telegram_notification(title, price, item_url, photo_url)
    else:
        print(f"Błąd pobierania danych z Vinted: Status {response.status_code}")

print("Bot uruchomiony! Szukam okazji...")
while True:
    try:
        check_vinted()
    except Exception as e:
        print(f"Błąd: {e}")
    time.sleep(20)
