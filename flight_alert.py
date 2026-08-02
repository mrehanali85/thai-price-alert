"""
Flight Price Alert: Karachi (KHI) -> Kuala Lumpur (KUL), Thai Airways (TG)
Checks flight prices across a date range and sends a Telegram message
whenever the cheapest price changes from the last check.

Uses SerpApi's Google Flights engine (free tier: 250 searches/month).

Runs via GitHub Actions on a schedule (see .github/workflows/price_check.yml).

Required environment variables (set as GitHub Actions Secrets):
  SERPAPI_API_KEY
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""

import os
import json
import requests
from datetime import date, timedelta

# ---- CONFIG ----------------------------------------------------------
ORIGIN = "KHI"
DESTINATION = "KUL"
START_DATE = date(2026, 8, 2)
END_DATE = date(2026, 8, 9)
ADULTS = 1
CHILDREN = 1  # age 3
CURRENCY = "PKR"
AIRLINE_CODE = "TG"  # Thai Airways only. Set to None to see all airlines.

SERPAPI_URL = "https://serpapi.com/search"
STATE_FILE = "state.json"
# -----------------------------------------------------------------------


def search_flights(departure_date):
    params = {
        "engine": "google_flights",
        "departure_id": ORIGIN,
        "arrival_id": DESTINATION,
        "outbound_date": departure_date.isoformat(),
        "type": "2",  # one-way
        "adults": ADULTS,
        "children": CHILDREN,
        "currency": CURRENCY,
        "hl": "en",
        "api_key": os.environ["SERPAPI_API_KEY"],
    }
    if AIRLINE_CODE:
        params["include_airlines"] = AIRLINE_CODE

    resp = requests.get(SERPAPI_URL, params=params)
    if resp.status_code != 200:
        print(f"  [{departure_date}] API error {resp.status_code}: {resp.text[:200]}")
        return None

    data = resp.json()
    flights = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    if not flights:
        return None

    prices = [f["price"] for f in flights if f.get("price")]
    return min(prices) if prices else None


def find_cheapest_across_range():
    best_price = None
    best_date = None
    day = START_DATE
    while day <= END_DATE:
        price = search_flights(day)
        print(f"  {day}: {price if price is not None else 'no offers found'}")
        if price is not None and (best_price is None or price < best_price):
            best_price = price
            best_date = day
        day += timedelta(days=1)
    return best_price, best_date


def load_last_price():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_price(price, dep_date):
    with open(STATE_FILE, "w") as f:
        json.dump({"price": price, "date": dep_date.isoformat()}, f)


def send_telegram(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": message})
    resp.raise_for_status()


def main():
    print(f"Checking prices {START_DATE} to {END_DATE} for {ORIGIN}->{DESTINATION} "
          f"({ADULTS} adult, {CHILDREN} child, airline={AIRLINE_CODE or 'any'})...")
    price, dep_date = find_cheapest_across_range()

    if price is None:
        print("No offers found for any date in range. Skipping alert.")
        return

    last = load_last_price()
    print(f"Cheapest found: {CURRENCY} {price} on {dep_date}")

    if last is None:
        send_telegram(
            f"✈️ Price tracking started for {ORIGIN}->{DESTINATION}\n"
            f"Cheapest so far: {CURRENCY} {price:.0f} on {dep_date}\n"
            f"(1 adult + 1 child, {START_DATE} to {END_DATE})"
        )
    elif abs(last["price"] - price) > 0.01:
        direction = "🔻 dropped" if price < last["price"] else "🔺 increased"
        send_telegram(
            f"{direction}: {ORIGIN}->{DESTINATION}\n"
            f"Old: {CURRENCY} {last['price']:.0f}\n"
            f"New: {CURRENCY} {price:.0f} on {dep_date}"
        )
    else:
        print("No price change since last check.")

    save_price(price, dep_date)


if __name__ == "__main__":
    main()
