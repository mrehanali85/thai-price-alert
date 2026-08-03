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
DATES = [
    date(2026, 8, 4),
    date(2026, 8, 6),
    date(2026, 8, 7),
    date(2026, 8, 8),
    date(2026, 8, 9),
]
ADULTS = 1
CHILDREN = 1  # age 3
CURRENCY = "PKR"
AIRLINE_CODE = None  # None = all airlines. Set to e.g. "TG" to filter to one airline only.

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
    offers = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    if not offers:
        return None

    # find the cheapest offer, and pull the airline name from its first leg
    cheapest = min(
        (o for o in offers if o.get("price")),
        key=lambda o: o["price"],
        default=None,
    )
    if cheapest is None:
        return None

    legs = cheapest.get("flights") or []
    airline = legs[0]["airline"] if legs and legs[0].get("airline") else "Unknown"
    if len(legs) > 1:
        airline += " (connecting)"

    total_minutes = cheapest.get("total_duration")  # in minutes
    if total_minutes:
        duration = f"{total_minutes // 60}h {total_minutes % 60}m"
    else:
        duration = "Unknown"

    return {"price": cheapest["price"], "airline": airline, "duration": duration}


def find_cheapest_across_range():
    best = None
    best_date = None
    for day in DATES:
        result = search_flights(day)
        print(f"  {day}: {result if result is not None else 'no offers found'}")
        if result is not None and (best is None or result["price"] < best["price"]):
            best = result
            best_date = day
    return best, best_date


def load_last_price():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_price(price, airline, duration, dep_date):
    with open(STATE_FILE, "w") as f:
        json.dump(
            {"price": price, "airline": airline, "duration": duration, "date": dep_date.isoformat()},
            f,
        )


def send_telegram(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": message})
    resp.raise_for_status()


def main():
    print(f"Checking prices on {DATES} for {ORIGIN}->{DESTINATION} "
          f"({ADULTS} adult, {CHILDREN} child, airline={AIRLINE_CODE or 'any'})...")
    result, dep_date = find_cheapest_across_range()

    if result is None:
        print("No offers found for any date in range. Skipping alert.")
        return

    price = result["price"]
    airline = result["airline"]
    duration = result["duration"]
    last = load_last_price()
    print(f"Cheapest found: {CURRENCY} {price} on {dep_date} ({airline}, {duration})")

    if last is None:
        send_telegram(
            f"✈️ Price tracking started for {ORIGIN}->{DESTINATION}\n"
            f"Cheapest so far: {CURRENCY} {price:.0f} on {dep_date}\n"
            f"Airline: {airline}\n"
            f"Duration: {duration}\n"
            f"(1 adult + 1 child)"
        )
    elif abs(last["price"] - price) > 0.01:
        direction = "🔻 dropped" if price < last["price"] else "🔺 increased"
        send_telegram(
            f"{direction}: {ORIGIN}->{DESTINATION}\n"
            f"Old: {CURRENCY} {last['price']:.0f} ({last.get('airline', 'unknown')})\n"
            f"New: {CURRENCY} {price:.0f} ({airline}, {duration}) on {dep_date}"
        )
    else:
        print("No price change since last check.")

    save_price(price, airline, duration, dep_date)


if __name__ == "__main__":
    main()
