# Setup Guide: Flight Price Alerts (Karachi → Kuala Lumpur, Thai Airways)

This checks Thai Airways flight prices every 6 hours across your date range
(Aug 2–9, 2026) and messages you on Telegram whenever the cheapest price
changes. It runs for free using GitHub Actions + SerpApi's free tier.

**Why every 6 hours and not 15 min/1 hour?** SerpApi's free tier gives 250
searches/month. Checking 8 dates every 6 hours uses about 224 searches over
your 7-day travel window — safely inside the free quota. Checking more often
would blow past the free limit (checking hourly would need ~336+ searches for
this window). If you want faster checks, see the "Going faster" note at the
bottom.

## Step 1 — Get a Telegram bot + chat ID (5 min)

1. In Telegram, search for **@BotFather** and start a chat.
2. Send `/newbot`, follow the prompts, and pick a name.
3. BotFather gives you a **token** like `123456789:AAExampleTokenHere` — save it.
4. Send your new bot any message (e.g. "hi") so it can see your chat.
5. In your browser, visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   (replace `<YOUR_TOKEN>` with your token)
6. Find `"chat":{"id":123456789, ...}` in the response — that number is your
   **chat ID**. Save it.

## Step 2 — Get a free SerpApi key (5 min)

1. Go to https://serpapi.com/users/sign_up and create a free account
   (no credit card required).
2. Once logged in, go to https://serpapi.com/manage-api-key — you'll see
   your **API Key** right there. Copy and save it.
3. Free tier: 250 searches/month, capped at 50/hour. This script is
   designed to stay well within that for your travel window.

## Step 3 — Put this code on GitHub (5 min)

1. Create a free GitHub account if you don't have one: https://github.com
2. Create a new **private** repository, e.g. `thai-price-alert`.
3. Upload all the files from this folder (`flight_alert.py`,
   `requirements.txt`, `.github/workflows/price_check.yml`) into it,
   keeping the folder structure (the workflow file must stay inside
   `.github/workflows/`).

## Step 4 — Add your secrets to GitHub

In your repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add these four:

| Name | Value |
|---|---|
| `SERPAPI_API_KEY` | your SerpApi key |
| `TELEGRAM_BOT_TOKEN` | your Telegram bot token |
| `TELEGRAM_CHAT_ID` | your Telegram chat ID |

## Step 5 — Turn it on

- Go to the **Actions** tab in your repo → you should see "Flight Price Check".
- Click **Run workflow** to trigger it manually the first time and confirm
  you get a Telegram message.
- After that, it runs automatically every 6 hours (00:00, 06:00, 12:00,
  18:00 UTC).

## Notes

- The route, dates (Aug 2–9, 2026), passengers (1 adult + 1 child, age 3),
  and airline filter (Thai Airways, `TG`) are set at the top of
  `flight_alert.py` — edit there if anything changes. Set `AIRLINE_CODE = None`
  if you'd rather see the cheapest fare from any airline on this route.
- It checks every date in the range each run and tracks the single cheapest
  fare found; you'll be messaged only when that cheapest price changes.
- GitHub free tier gives ~2,000 Action minutes/month — this job takes well
  under a minute per run, so that's not a limiting factor.

## Going faster (optional)

If 6-hourly isn't fast enough once you're closer to booking:
- **Narrow the date range** to 2-3 dates you're actually likely to book —
  frees up quota for more frequent checks within the same 250/month limit.
- **Upgrade SerpApi** to a paid plan ($25/month for 1,000 searches) —
  removes the quota problem entirely and lets you go back to hourly or even
  15-minute checks. Just change the cron schedule in
  `.github/workflows/price_check.yml` accordingly.
