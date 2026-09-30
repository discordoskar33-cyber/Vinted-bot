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

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Vinted dziala!")

    def log_message(self, format, *args):
        return  # Wyciszenie logów serwera HTTP

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
        print(f"[!] Błąd Telegram: {e}", flush=True)

def get_vinted_session():
    """Inicjalizuje sesję curl_cffi i pobiera token access_token_web z ciasteczek Vinted."""
    s = cffi_requests.Session(impersonate="chrome124")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        # 1. Wejście na stronę główną
        s.get("https://www.vinted.pl/", headers=headers, timeout=15)
        cookies = s.cookies.get_dict()
        token = cookies.get("access_token_web")
        
        # 2. Jeśli tokena brakuje, odwiedzamy podstronę katalogu
        if not token:
            s.get("https://www.vinted.pl/catalog", headers=headers, timeout=15)
            cookies = s.cookies.get_dict()
            token = cookies.get("access_token_web")

        if token:
            print(f"[+] Sesja utworzona pomyślnie! Token: {token[:12]}...", flush=True)
            s.headers.update({
                "User-Agent": headers["User-Agent"],
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
                "Authorization": f"Bearer {token}",
                "Referer": "https://www.vinted.pl/catalog",
                "X-Requested-With": "XMLHttpRequest",
            })
            return s
        else:
            print(f"[!] Nie odnaleziono access_token_web w ciasteczkach ({len(cookies)} ciasteczek).", flush=True)
            return None
    except Exception as e:
        print(f"[!] Błąd podczas pobierania sesji: {e}", flush=True)
        return None

def main():
    threading.Thread(target=start_http_server, daemon=True).start()
    print("Bot uruchomiony! Rozpoczynam monitorowanie Vinted...", flush=True)
    
    session = None
    
    while True:
        if session is None:
            session = get_vinted_session()
            if session is None:
                print("[!] Oczekiwanie 15 sekund przed kolejną próbą utwożenia sesji...", flush=True)
                time.sleep(15)
                continue

        try:
            response = session.get(SEARCH_URL, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                print(f"[+] Sukces! Pobrano {len(items)} ofert.", flush=True)
                
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
                        
            elif response.status_code in (401, 403, 404):
                print(f"[!] Vinted odrzucił zapytanie (Status {response.status_code}). Resetowanie sesji...", flush=True)
                session = None
            else:
                print(f"[!] Nieoczekiwany status HTTP: {response.status_code}", flush=True)
                session = None

        except Exception as e:
            print(f"[!] Wyjątek podczas zapytania: {e}", flush=True)
            session = None

        time.sleep(25)

if __name__ == "__main__":
    main()



