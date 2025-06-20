# news_bot.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_today_articles():
    url = "https://boursenews.ma/articles/actualite"
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    today_str = datetime.now().strftime("%d %B %Y")
    today_str = today_str[0:1] + today_str[1:]

    articles = []

    for card in soup.find_all("div", class_="item-content"):
        h3 = card.find("h3")
        a = h3.find("a") if h3 else None
        span = card.find("span")

        if not (a and span):
            continue

        title = a.get_text(strip=True)
        link = a["href"]
        full_link = link if link.startswith("http") else "https://boursenews.ma" + link
        date = span.get_text(strip=True).split("-")[0].strip()

        if today_str in date:
            articles.append(f"- {title}\n{full_link}")

    return "\n\n".join(articles) if articles else "Pas d'articles pertinents aujourd'hui."


def summarize_with_gemini(text):
    import requests
    import os
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GEMINI_API_KEY}"
    }
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Résume les actualités suivantes en 3 lignes max en français:\n\n{text}"
            }]
        }]
    }
    r = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        headers=headers,
        json=payload
    )

    print("FULL GEMINI RESPONSE:", r.status_code, r.text)

    response = r.json()
    return response["candidates"][0]["content"]["parts"][0]["text"]


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=payload)


if __name__ == "__main__":
    raw = get_today_articles()
    summary = summarize_with_gemini(raw)
    send_to_telegram(summary)
