import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from curl_cffi import requests as cffi_requests

TELEGRAM_TOKEN = "7913644987:AAGf3SGA8ixaxw2rsjinQ0j-aZ7cGpOl7u8"
CHAT_ID = "7361590854"
SEARCH_URL = "https://www.vinted.pl/api/v2/catalog/items?search_text=nike&price_to=40&currency=PLN&order=newest_first&page=1&per_page=10"

seen_ids = set()
session = None
bearer_token = None

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Vinted dziala!")

def start_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

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
        requests.post(telegram_api, data=payload, timeout=10)
    except Exception as e:
        print(f"Błąd Telegram: {e}", flush=True)

def create_fresh_session():
    global bearer_token
    s = cffi_requests.Session(impersonate="chrome124")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
    }
    try:
        resp = s.get("https://www.vinted.pl/", headers=headers, timeout=12)
        bearer_token = s.cookies.get("access_token_web") or s.cookies.get("_vinted_fr_session")
        print(f"[+] Nowa sesja! Status HTTP: {resp.status_code}, Token: {'OK' if bearer_token else 'Brak'}", flush=True)
    except Exception as e:
        print(f"[!] Błąd pobierania sesji: {e}", flush=True)
        bearer_token = None
    return s

def check_vinted():
    global session, bearer_token
    if session is None or not bearer_token:
        session = create_fresh_session()
        time.sleep(2)
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
        "Referer": "https://www.vinted.pl/catalog",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    
    try:
        response = session.get(SEARCH_URL, headers=headers, timeout=10)
    except Exception as e:
        print(f"Błąd połączenia z API: {e}", flush=True)
        session = None
        bearer_token = None
        return
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        print(f"[+] Pobrano {len(items)} ofert z Vinted", flush=True)
        for item in reversed(items):
            item_id = item["id"]
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                title = item.get("title", "Brak tytułu")
                price = item.get("price", {}).get("amount", "??")
                item_url = item.get("url")
                photos = item.get("photos", [])
                photo_url = photos[0].get("url") if photos else None
                
                print(f"[+] Nowa oferta: {title} - {price} zł", flush=True)
                send_telegram_notification(title, price, item_url, photo_url)
    else:
        print(f"Błąd Vinted: Status {response.status_code} -> Resetuję sesję...", flush=True)
        session = None
        bearer_token = None

if __name__ == "__main__":
    threading.Thread(target=start_http_server, daemon=True).start()
    print("Bot uruchomiony! Szukam okazji...", flush=True)
    while True:
        try:
            check_vinted()
        except Exception as e:
            print(f"Wyjątek pętli: {e}", flush=True)
            session = None
            bearer_token = None
        time.sleep(30)

