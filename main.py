import requests
import time
import html
import datetime
import pytz
from deep_translator import GoogleTranslator
from apscheduler.schedulers.background import BackgroundScheduler
import statistics
from flask import Flask
import threading
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 ربات فعاله و بیداره!"

def start_flask():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=start_flask).start()
# --- اطلاعات ربات و API ---
TELEGRAM_BOT_TOKEN = '7725601905:AAG2JKoGXCkd--AuFNTihFquO0e1HyyYSkk'
TELEGRAM_CHANNEL_ID = '@Crypto_Zone360'
MARKETAUX_API_KEY = 'QR7tIkmOgsz46kyPGGilkFAHkqCTdGPV11LAivmC'

# --- کلمات کلیدی برای اخبار ---
KEYWORDS = ["Bitcoin", "Ethereum", "SEC", "ETF", "Ripple", "Binance", "Solana", "bullish", "bearish", "crypto", "cryptocurrency", "regulation", "altcoin", "blockchain"]

# --- ارزهای مهم برای گزارش ---
COINS = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'solana': 'SOL',
    'toncoin': 'TON',
    'ripple': 'XRP',
    'binancecoin': 'BNB'
}

# --- ارسال پیام به تلگرام ---
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHANNEL_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print("❗️Telegram error:", response.text)

# --- ترجمه ---
def translate(text):
    try:
        return GoogleTranslator(source='en', target='fa').translate(text)
    except Exception as e:
        print("❗️ Translation error:", e)
        return "ترجمه ناموفق بود."

# --- گرفتن اخبار ---
def fetch_news():
    url = f"https://api.marketaux.com/v1/news/all?categories=crypto&language=en&api_token={MARKETAUX_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print("❗️ Failed to fetch news:", response.text)
        return []

# --- بررسی اینکه آیا خبر مهم است؟ ---
def is_important(title):
    return any(keyword.lower() in title.lower() for keyword in KEYWORDS)

# --- اجرای ربات اخبار ---
posted_titles = set()

def run_news_bot():
    try:
        news_list = fetch_news()
        print(f"📥 {len(news_list)} خبر دریافت شد")

        for news in news_list:
            title = html.unescape(news["title"])
            summary = news.get("description", "")
            url = news.get("url", "")
            print("🔎 بررسی عنوان:", title)

            if title not in posted_titles and is_important(title):
                print("📌 خبر مهم تشخیص داده شد:", title)
                translated_title = translate(title)
                translated_summary = translate(summary) if summary else ""
                message = f"📢 {translated_title}\n\n📝 {translated_summary}\n\n🔗 <a href='{url}'>مطالعه کامل خبر</a>\n\n👥 @Crypto_Zone360\nبه ما بپیوندید 🦈"
                send_to_telegram(message)
                posted_titles.add(title)
                time.sleep(5)
    except Exception as e:
        print("❗️ General news error:", e)
        send_to_telegram("❗️ ربات اخبار با خطا مواجه شد و دوباره تلاش می‌کند.")

# --- دریافت داده بازار از CoinGecko ---
def fetch_market_data():
    ids = ','.join(COINS.keys())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("❗️خطا در دریافت داده بازار:", response.text)
        return {}

# --- دریافت قیمت‌های گذشته برای تحلیل تکنیکال ---
def fetch_historical_prices(coin_id, days=30):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
    response = requests.get(url)
    if response.status_code == 200:
        prices = response.json().get("prices", [])
        return [p[1] for p in prices]
    else:
        print(f"❗️خطا در دریافت داده تاریخی {coin_id}:", response.text)
        return []

# --- محاسبه تحلیل تکنیکال ساده ---
def get_technical_analysis(prices):
    if len(prices) < 14:
        return "اطلاعات کافی برای تحلیل نیست."

    ma7 = round(statistics.mean(prices[-7:]), 2)
    ma30 = round(statistics.mean(prices[-30:]), 2)

    # RSI ساده (بر پایه اختلافات قیمت)
    deltas = [j - i for i, j in zip(prices[:-1], prices[1:])]
    gains = sum(d for d in deltas if d > 0)
    losses = -sum(d for d in deltas if d < 0)
    rs = gains / losses if losses != 0 else 100
    rsi = round(100 - (100 / (1 + rs)), 1)

    rsi_note = "اشباع فروش 📉" if rsi < 30 else "اشباع خرید 📈" if rsi > 70 else "نرمال"
    trend = "روند صعودی 🔼" if ma7 > ma30 else "روند نزولی 🔽"

    analysis = f"MA7: {ma7}, MA30: {ma30}, RSI: {rsi} ({rsi_note}), {trend}"
    disclaimer = "🔸 تحلیل ارائه‌شده صرفاً جنبه اطلاع‌رسانی دارد و نباید به‌عنوان توصیه مالی در نظر گرفته شود."

    return f"{analysis}\n{disclaimer}"

# --- ساخت پیام گزارش بازار ---
def build_market_message(data, title):
    date_str = datetime.datetime.now(pytz.timezone("Asia/Tehran")).strftime("%Y/%m/%d")
    lines = [f"📊 {title} - {date_str}\n"]
    lines.append("<pre>ارز     قیمت ($)    تغییر ۲۴ساعت  حجم معاملات")
    lines.append("----------------------------------------------")
    for coin_id, symbol in COINS.items():
        if coin_id in data:
            price = round(data[coin_id]['usd'])
            change = round(data[coin_id]['usd_24h_change'], 1)
            volume = round(data[coin_id]['usd_24hr_vol'] / 1_000_000)
            line = f"{symbol:<7}${price:<10}{change:+}%         ${volume}M"
            lines.append(line)
    lines.append("</pre>\n")

    # اضافه کردن تحلیل تکنیکال
    lines.append("📈 تحلیل تکنیکال:")
    for coin_id, symbol in COINS.items():
        prices = fetch_historical_prices(coin_id)
        analysis = get_technical_analysis(prices)
        lines.append(f"{symbol}: {analysis}")

    lines.append("\n📡 @Crypto_Zone360")
    lines.append("برای دریافت روزانه اخبار و تحلیل‌ها، به ما بپیوندید 🦈")
    return '\n'.join(lines)

# --- ارسال گزارش روزانه ---
def daily_market_report():
    data = fetch_market_data()
    if data:
        msg = build_market_message(data, "گزارش روزانه بازار کریپتو")
        send_to_telegram(msg)

# --- برنامه‌ریز زمان‌بندی (برای گزارش‌ها) ---
scheduler = BackgroundScheduler(timezone="Asia/Tehran")
scheduler.add_job(daily_market_report, 'cron', hour=21, minute=0)  # هر شب ساعت ۹
scheduler.start()

# --- اجرای مداوم (اخبار هر ۱۰ دقیقه) ---
print("✅ ربات ترکیبی با تحلیل تکنیکال فعال است...")

while True:
    run_news_bot()
    time.sleep(600)  # هر 10 دقیقه بررسی اخبار











































































































































