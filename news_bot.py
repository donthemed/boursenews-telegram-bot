# news_bot.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

french_months = {
    "01": "janvier", "02": "février", "03": "mars", "04": "avril",
    "05": "mai", "06": "juin", "07": "juillet", "08": "août",
    "09": "septembre", "10": "octobre", "11": "novembre", "12": "décembre"
}

def get_today_articles():
    now = datetime.now()
    day = str(now.day)
    month = french_months[now.strftime("%m")]
    year = str(now.year)
    today_str = f"{day} {month} {year}"

    urls = [
        "https://boursenews.ma/articles/actualite",
        "https://boursenews.ma/articles/marches"
    ]
    
    articles = []

    for base_url in urls:
        for page in range(1, 6):  # check first 5 pages
            url = base_url + (f"/{page}" if page > 1 else "")
            html = requests.get(url).text
            soup = BeautifulSoup(html, "html.parser")

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

                if all(part.lower() in date.lower() for part in [day, month]):
                    articles.append(f"- {title}\n{full_link}")

    return "\n\n".join(articles) if articles else "📭 Aucun article pertinent pour aujourd'hui."

def summarize_with_gemini(prompt, api_key=GEMINI_API_KEY):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": f"Voici des nouvelles économiques marocaines du jour :\n\n{prompt}\n\nFais un résumé clair et utile pour un investisseur."}
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
    summary = summarize_with_gemini(raw)
    send_to_telegram(summary)
