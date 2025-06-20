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
            try:
                url = base_url + (f"/{page}" if page > 1 else "")
                html = requests.get(url, timeout=10).text
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
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue

    return "\n\n".join(articles) if articles else "📭 Aucun article pertinent pour aujourd'hui."

def summarize_with_gemini(prompt, api_key=GEMINI_API_KEY):
    # Updated to use the correct model name
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
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

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            print("FULL GEMINI RESPONSE:", response.text)
            raise Exception(f"GEMINI API error: {response.status_code}")
        
        result = response.json()
        
        # Check if the response has the expected structure
        if "candidates" not in result or not result["candidates"]:
            print("Unexpected response structure:", result)
            raise Exception("No candidates in response")
            
        return result["candidates"][0]["content"]["parts"][0]["text"]
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        raise Exception(f"Network error: {e}")
    except KeyError as e:
        print(f"Response parsing error: {e}")
        print("Full response:", response.text if 'response' in locals() else 'No response')
        raise Exception(f"Response parsing error: {e}")

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"Telegram API error: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

if __name__ == "__main__":
    try:
        raw = get_today_articles()
        print(f"Found articles: {raw[:200]}...")
        
        if raw != "📭 Aucun article pertinent pour aujourd'hui.":
            summary = summarize_with_gemini(raw)
            send_to_telegram(summary)
            print("Summary sent to Telegram successfully!")
        else:
            send_to_telegram(raw)
            print("No articles found message sent to Telegram!")
            
    except Exception as e:
        error_message = f"❌ Erreur dans le bot: {str(e)}"
        print(error_message)
        send_to_telegram(error_message) 
