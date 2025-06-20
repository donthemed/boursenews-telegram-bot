# news_bot.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_today_articles():
    base_url = "https://boursenews.ma/articles/marches"
    today_str = datetime.now().strftime("%d %B %Y")
    today_str = today_str[0:1] + today_str[1:]

    all_articles = []
    page = 1

    while True:
        url = f"{base_url}?page={page}"
        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="item-content")

        if not cards:
            break  # No more content

        found_today = False
        for card in cards:
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
                found_today = True
                all_articles.append(f"- {title}\n{full_link}")

        if not found_today:
            break  # Stop when today's articles are no longer found
        page += 1

    return "\n\n".join(all_articles) if all_articles else "Pas d'articles pertinents aujourd'hui."



def summarize_with_gemini(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": "Résume en français les nouvelles suivantes pour un investisseur marocain:\n\n" + prompt}
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        print("FULL GEMINI RESPONSE:", response.text)
        raise Exception(f"GEMINI API error: {response.status_code}")

    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=payload)


if __name__ == "__main__":
    raw = get_today_articles()
    if "Pas d'articles pertinents" in raw:
        send_to_telegram("📭 Aucun article pertinent pour aujourd'hui.")
    else:
        summary = summarize_with_gemini(raw, GEMINI_API_KEY)
        send_to_telegram("📰 *Résumé des nouvelles boursières du jour:*\n\n" + summary)
