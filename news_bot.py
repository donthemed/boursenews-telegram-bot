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

# STRICT keywords - only for direct Casablanca stock market relevance
STRICT_STOCK_KEYWORDS = [
    "bourse de casablanca", "masi", "madex", "cotation", "introduction en bourse", 
    "ipo", "dividende", "résultat financier", "chiffre d'affaires", "capitalisation boursière",
    "volume d'échange", "séance boursière", "cours de bourse", "action", "titre",
    "société cotée", "indice boursier", "carnet d'ordres", "suspension", "reprise"
]

# Listed companies on Casablanca Stock Exchange (major ones)
LISTED_COMPANIES = [
    "attijariwafa bank", "attijariwafa", "bank of africa", "boa", "bmce bank", "bmce",
    "cih bank", "cih", "maroc telecom", "iam", "ocp group", "ocp", "managem",
    "addoha", "lafargeholcim", "cosumar", "lesieur cristal", "bmci", "crédit du maroc",
    "delta holding", "douja prom", "snep", "alliances", "aradei capital", "jet contractors",
    "vicenne", "nexans maroc", "salafin", "wafa assurance", "atlanta", "rebab company",
    "res dar saada", "marsa maroc", "sodep", "auto hall", "colorado", "disway",
    "ennakl", "fenie brossette", "high tech payment systems", "involys", "label vie",
    "microdata", "risma", "sonasid", "taqa morocco", "timar", "unimer"
]

# High importance: IPOs, major corporate actions, index movements
HIGH_IMPORTANCE_KEYWORDS = [
    "introduction en bourse", "ipo", "masi", "madex", "dividende exceptionnel",
    "résultat annuel", "acquisition", "fusion", "scission", "augmentation de capital",
    "rachat d'actions", "opa", "opv", "suspension de cotation"
]

def get_today_articles():
    now = datetime.now()
    day = str(now.day)
    month = french_months[now.strftime("%m")]
    year = str(now.year)
    
    date_patterns = [
        f"{day} {month} {year}",
        f"{day} {month.capitalize()} {year}",
        f"Vendredi {day} {month} {year}",
        f"Vendredi {day} {month.capitalize()} {year}",
    ]

    urls = [
        "https://boursenews.ma/articles/actualite",
        "https://boursenews.ma/articles/marches"
    ]
    
    all_articles = []
    print(f"🔍 Looking for STRICT Casablanca stock market & IPO articles...")

    for base_url in urls:
        print(f"\n📊 Checking: {base_url}")
        
        for page in range(1, 3):  # Check first 2 pages
            try:
                url = base_url + (f"/{page}" if page > 1 else "")
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    break
                    
                soup = BeautifulSoup(response.text, "html.parser")
                h3_tags = soup.find_all("h3")
                
                page_articles_found = 0
                for h3 in h3_tags:
                    full_text = h3.get_text(strip=True)
                    a = h3.find("a")
                    if not a:
                        continue
                    
                    title = a.get_text(strip=True)
                    link = a["href"]
                    full_link = link if link.startswith("http") else "https://boursenews.ma" + link
                    
                    # Check if today's date
                    date_found = any(pattern in full_text for pattern in date_patterns)
                    
                    # STRICT check - only direct stock market relevance
                    is_stock_related, match_reason = is_strict_stock_market_related(title, full_text)
                    
                    if date_found and is_stock_related:
                        importance = get_article_importance(title, full_text)
                        article_info = {
                            'title': title,
                            'link': full_link,
                            'full_text': full_text,
                            'importance': importance,
                            'match_reason': match_reason,
                            'section': base_url.split('/')[-1]
                        }
                        all_articles.append(article_info)
                        page_articles_found += 1
                        print(f"      {importance['emoji']} Found: {title[:60]}...")
                        print(f"         📍 Reason: {match_reason}")
                
                print(f"    Page {page}: Found {page_articles_found} strict stock market articles")
                
                if page_articles_found == 0 and page > 1:
                    break

            except Exception as e:
                print(f"    Page {page}: Error - {e}")
                break

    # Sort by importance (most important first)
    all_articles.sort(key=lambda x: x['importance']['level'], reverse=True)
    
    print(f"\n🎯 Total STRICT stock market articles found: {len(all_articles)}")
    return all_articles

def is_strict_stock_market_related(title, content):
    """STRICT check - only direct Casablanca stock market and IPO relevance"""
    text_to_check = (title + " " + content).lower()
    
    # Exclude general economic/international news
    exclude_keywords = [
        "inflation", "pib", "croissance économique", "banque centrale", "politique monétaire",
        "bourses européennes", "bourse américaine", "wall street", "euro stoxx", "s&p",
        "onee", "oncf", "adm", "onda", "ram", "banque mondiale", "fmi"
    ]
    
    for exclude in exclude_keywords:
        if exclude in text_to_check:
            return False, f"Excluded: {exclude}"
    
    # Check for strict stock market keywords
    for keyword in STRICT_STOCK_KEYWORDS:
        if keyword in text_to_check:
            return True, f"Stock keyword: {keyword}"
    
    # Check for listed companies (strict matching)
    for company in LISTED_COMPANIES:
        if company in text_to_check:
            return True, f"Listed company: {company}"
    
    return False, "No direct stock market relevance"

def get_article_importance(title, content):
    """Determine article importance and assign emoji"""
    text_to_check = (title + " " + content).lower()
    
    # High importance: IPOs, major corporate actions, index movements
    for keyword in HIGH_IMPORTANCE_KEYWORDS:
        if keyword in text_to_check:
            return {'level': 3, 'emoji': '🚨', 'label': 'Très Important', 'matched': keyword}
    
    # Medium importance: Company financial results, strategic moves
    medium_keywords = ["résultat", "chiffre d'affaires", "bénéfice", "stratégie", "partenariat", "investissement"]
    for keyword in medium_keywords:
        if keyword in text_to_check:
            return {'level': 2, 'emoji': '📈', 'label': 'Important', 'matched': keyword}
    
    # Normal importance: General company news
    return {'level': 1, 'emoji': '📊', 'label': 'Standard', 'matched': 'général'}

def summarize_articles_with_gemini(articles, api_key=GEMINI_API_KEY):
    """Create ORIGINAL Arabic summaries for stock market articles"""
    if not articles:
        return "📭 لا توجد أخبار متعلقة ببورصة الدار البيضاء اليوم."
    
    # Prepare articles for Gemini
    articles_text = []
    for i, article in enumerate(articles, 1):
        articles_text.append(f"{i}. {article['title']}\nالرابط: {article['link']}")
    
    prompt = f"""أنت محلل مالي خبير في بورصة الدار البيضاء. إليك {len(articles)} مقال متعلق بالبورصة اليوم:

{chr(10).join(articles_text)}

التعليمات الصارمة:
1. اكتب ملخصاً أصلياً وفريداً لكل مقال باللغة العربية (ليس إعادة صياغة)
2. ركز فقط على التأثير على البورصة والاستثمارات
3. جملتان قصيرتان كحد أقصى لكل مقال
4. استخدم معرفتك المالية لتحليل التأثير المحتمل
5. اذكر التأثير المحتمل على سعر السهم أو المؤشر
6. تجنب نسخ المحتوى - أنشئ تحليلاً أصلياً
7. رتب حسب الأهمية (الأكثر أهمية أولاً)
8. كن مختصراً ومفيداً

تنسيق الإجابة لكل مقال:
[الرمز التعبيري] **عنوان قصير (50 حرف كحد أقصى)**
تحليل أصلي في جملتين كحد أقصى.
📰 [المصدر](الرابط)

ابدأ مباشرة بالمقالات، بدون مقدمة."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            print("❌ Gemini API error:", response.text)
            return format_articles_fallback(articles)
        
        result = response.json()
        
        if "candidates" not in result or not result["candidates"]:
            print("❌ No candidates in Gemini response")
            return format_articles_fallback(articles)
            
        return result["candidates"][0]["content"]["parts"][0]["text"]
        
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return format_articles_fallback(articles)

def format_articles_fallback(articles):
    """Fallback formatting if Gemini fails - in Arabic"""
    if not articles:
        return "📭 لا توجد أخبار متعلقة ببورصة الدار البيضاء اليوم."
    
    formatted = f"📈 *بورصة الدار البيضاء - {len(articles)} أخبار اليوم*\n\n"
    
    for article in articles:
        formatted += f"{article['importance']['emoji']} **{article['title'][:70]}{'...' if len(article['title']) > 70 else ''}**\n"
        formatted += f"شركة مدرجة في البورصة مع تأثير محتمل على الأسعار.\n"
        formatted += f"📰 [المصدر]({article['link']})\n\n"
    
    return formatted

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",  # Enable markdown for formatting
        "disable_web_page_preview": False  # Show link previews
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Message sent to Telegram successfully!")
            return True
        else:
            print(f"❌ Telegram API error: {response.status_code}")
            print("Response:", response.text)
            return False
    except Exception as e:
        print(f"❌ Error sending to Telegram: {e}")
        return False

if __name__ == "__main__":
    try:
        print("🎯 STRICT CASABLANCA STOCK MARKET & IPO NEWS BOT")
        print("=" * 60)
        
        # Get today's STRICT stock market articles
        articles = get_today_articles()
        
        if not articles:
            message = "📭 لا توجد أخبار متعلقة ببورصة الدار البيضاء اليوم."
            send_to_telegram(message)
            print("📭 No strict stock market articles found for today")
        else:
            print(f"\n📈 Processing {len(articles)} strict stock market articles...")
            
            # Create enhanced Arabic summary with Gemini
            summary = summarize_articles_with_gemini(articles)
            
            # Add header only (no footer)
            today = datetime.now().strftime("%d %B %Y")
            final_message = f"🏛️ **بورصة الدار البيضاء** - {today}\n\n{summary}"
            
            # Send to Telegram
            success = send_to_telegram(final_message)
            
            if success:
                print("✅ Arabic stock market summary sent successfully!")
                print(f"📊 Summary included {len(articles)} articles")
                
                # Show importance breakdown
                high_imp = sum(1 for a in articles if a['importance']['level'] == 3)
                med_imp = sum(1 for a in articles if a['importance']['level'] == 2)
                low_imp = sum(1 for a in articles if a['importance']['level'] == 1)
                
                print(f"🚨 Très Important: {high_imp}")
                print(f"📈 Important: {med_imp}")
                print(f"📊 Standard: {low_imp}")
            else:
                print("❌ Failed to send message")
            
    except Exception as e:
        error_message = f"❌ خطأ في البوت: {str(e)}"
        print(error_message)
        send_to_telegram(error_message) 
