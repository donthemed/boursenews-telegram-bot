import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

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
    
    # Create date patterns to match
    date_patterns = [
        f"{day} {month} {year}",  # "20 juin 2025"
        f"{day} {month.capitalize()} {year}",  # "20 Juin 2025"
        f"Vendredi {day} {month} {year}",  # "Vendredi 20 juin 2025"
        f"Vendredi {day} {month.capitalize()} {year}",  # "Vendredi 20 Juin 2025"
    ]

    urls = [
        "https://boursenews.ma/articles/actualite",
        "https://boursenews.ma/articles/marches"
    ]
    
    articles = []
    print(f"🔍 Looking for articles with dates: {date_patterns}")

    for base_url in urls:
        print(f"\n📊 Checking: {base_url}")
        
        # Check multiple pages
        for page in range(1, 6):  # Check first 5 pages
            try:
                url = base_url + (f"/{page}" if page > 1 else "")
                print(f"  Checking page {page}...")
                
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    print(f"    HTTP {response.status_code}")
                    break
                    
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Updated selector: Look for H3 tags directly instead of list_item divs
                h3_tags = soup.find_all("h3")
                print(f"    Found {len(h3_tags)} H3 tags")
                
                page_articles_found = 0
                for h3 in h3_tags:
                    # Get the full text which contains title and date
                    full_text = h3.get_text(strip=True)
                    
                    # Look for links within the H3
                    a = h3.find("a")
                    if not a:
                        continue
                    
                    title = a.get_text(strip=True)
                    link = a["href"]
                    full_link = link if link.startswith("http") else "https://boursenews.ma" + link
                    
                    # Check if any of our date patterns match
                    date_found = False
                    for pattern in date_patterns:
                        if pattern in full_text:
                            date_found = True
                            break
                    
                    if date_found:
                        article_entry = f"- {title}\n{full_link}"
                        if article_entry not in articles:  # Avoid duplicates
                            articles.append(article_entry)
                            page_articles_found += 1
                            print(f"      ✅ Found: {title[:60]}...")
                
                print(f"    Page {page}: Found {page_articles_found} new articles")
                
                # If no articles found on this page, likely no more pages
                if page_articles_found == 0 and page > 1:
                    print(f"    No matching articles on page {page}, stopping pagination")
                    break

            except Exception as e:
                print(f"    Page {page}: Error - {e}")
                break

    print(f"\n🎯 Total articles found: {len(articles)}")
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
        else:
            print("✅ Message sent to Telegram successfully!")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

if __name__ == "__main__":
    try:
        raw = get_today_articles()
        print(f"\n📰 Articles found: {raw[:300]}..." if len(raw) > 300 else f"\n📰 Articles found: {raw}")
        
        if raw != "📭 Aucun article pertinent pour aujourd'hui.":
            print("\n🤖 Generating summary with Gemini...")
            summary = summarize_with_gemini(raw)
            print(f"✅ Summary generated!")
            print(f"📝 Summary: {summary[:200]}..." if len(summary) > 200 else f"📝 Summary: {summary}")
            
            send_to_telegram(summary)
            print("✅ Process completed successfully!")
        else:
            send_to_telegram(raw)
            print("📭 No articles message sent to Telegram!")
            
    except Exception as e:
        error_message = f"❌ Erreur dans le bot: {str(e)}"
        print(error_message)
        send_to_telegram(error_message) 
