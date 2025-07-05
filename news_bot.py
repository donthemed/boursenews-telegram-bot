import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import re
import time

# Try to import cloudscraper for medias24.com access
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

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
    
    # Generate date patterns for the last 24 hours only (today and yesterday)
    date_patterns = []
    for days_back in range(2):  # Today and yesterday only (last 24 hours)
        target_date = now - timedelta(days=days_back)
        day = str(target_date.day)
        month = french_months[target_date.strftime("%m")]
        year = str(target_date.year)
        
        # Add various date format patterns
        date_patterns.extend([
            f"{day} {month} {year}",
            f"{day} {month.capitalize()} {year}",
            f"Lundi {day} {month} {year}",
            f"Mardi {day} {month} {year}",
            f"Mercredi {day} {month} {year}",
            f"Jeudi {day} {month} {year}",
            f"Vendredi {day} {month} {year}",
            f"Samedi {day} {month} {year}",
            f"Dimanche {day} {month} {year}",
            f"Lundi {day} {month.capitalize()} {year}",
            f"Mardi {day} {month.capitalize()} {year}",
            f"Mercredi {day} {month.capitalize()} {year}",
            f"Jeudi {day} {month.capitalize()} {year}",
            f"Vendredi {day} {month.capitalize()} {year}",
            f"Samedi {day} {month.capitalize()} {year}",
            f"Dimanche {day} {month.capitalize()} {year}",
        ])

    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for pattern in date_patterns:
        if pattern not in seen:
            seen.add(pattern)
            unique_patterns.append(pattern)
    
    date_patterns = unique_patterns

    urls = [
        "https://boursenews.ma/articles/actualite",
        "https://boursenews.ma/articles/marches",
        "https://medias24.com/categorie/leboursier/actus/"
    ]
    
    # Improved headers to avoid being blocked, especially for medias24
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    all_articles = []
    print(f"🔍 Looking for STRICT Casablanca stock market & IPO articles from last 24 hours...")
    print(f"📅 Date patterns: {len(date_patterns)} patterns for last 24 hours")

    for base_url in urls:
        print(f"\n📊 Checking: {base_url}")
        
        # Use cloudscraper for medias24.com, regular requests for others
        if "medias24.com" in base_url:
            if not CLOUDSCRAPER_AVAILABLE:
                print(f"    ⚠️  CloudScraper not available for medias24.com - skipping")
                continue
            # Will use cloudscraper instead of headers
            use_cloudscraper = True
        else:
            use_cloudscraper = False
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        
        for page in range(1, 3):  # Check first 2 pages
            try:
                if "medias24.com" in base_url:
                    # Different pagination for medias24
                    url = base_url + (f"?page={page}" if page > 1 else "")
                else:
                    url = base_url + (f"/{page}" if page > 1 else "")
                
                # Use cloudscraper for medias24.com, regular requests for others
                if use_cloudscraper:
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url, timeout=30)
                    print(f"    🔧 Using CloudScraper for medias24.com")
                else:
                    response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 403 and not use_cloudscraper:
                    print(f"    ⚠️  Access blocked (403) - trying alternative approach...")
                    # Try with different user agent
                    headers['User-Agent'] = user_agents[1]
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 403:
                        print(f"    ❌ Still blocked - website has strong anti-bot protection")
                        break
                elif response.status_code != 200:
                    print(f"    ❌ HTTP {response.status_code}")
                    if use_cloudscraper:
                        print(f"    ⚠️  CloudScraper failed - medias24.com has additional protection")
                    break
                    
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Different selectors for different websites
                if "medias24.com" in base_url:
                    # Medias24 uses different HTML structure - try multiple selectors
                    h3_tags = []
                    
                    # Add a small delay to allow dynamic content loading
                    time.sleep(2)
                    
                    # Try various selectors for medias24
                    selectors = [
                        "article h3", "article h2", "div.article h3", "div.article h2",
                        ".post-title h3", ".post-title h2", ".entry-title", 
                        ".article-title", "h3", "h2", "h1"  # fallback
                    ]
                    
                    for selector in selectors:
                        elements = soup.select(selector)
                        if elements:
                            # Filter out loading messages
                            valid_elements = []
                            for element in elements:
                                text = element.get_text(strip=True)
                                if text and "chargement" not in text.lower() and len(text) > 10:
                                    valid_elements.append(element)
                            
                            if valid_elements:
                                h3_tags = valid_elements
                                print(f"    📍 Using selector: {selector} (found {len(valid_elements)} valid elements)")
                                break
                    
                    if not h3_tags:
                        print(f"    ⚠️  No valid content found - medias24.com may be loading dynamically")
                else:
                    h3_tags = soup.find_all("h3")
                
                page_articles_found = 0
                for h3 in h3_tags:
                    full_text = h3.get_text(strip=True)
                    a = h3.find("a")
                    if not a:
                        # Sometimes the link is in parent or sibling elements
                        parent = h3.find_parent("a")
                        if parent:
                            a = parent
                        else:
                            continue
                    
                    title = a.get_text(strip=True)
                    link = a.get("href", "")
                    
                    if not link:
                        continue
                    
                    # Fix link format for different websites
                    if link.startswith("http"):
                        full_link = link
                    elif "medias24.com" in base_url:
                        full_link = "https://medias24.com" + link
                    else:
                        full_link = "https://boursenews.ma" + link
                    
                    # Check if recent date (last 24 hours)
                    date_found = any(pattern in full_text for pattern in date_patterns)
                    
                    # STRICT check - only direct stock market relevance (works for both sites)
                    is_stock_related, match_reason = is_strict_stock_market_related(title, full_text)
                    
                    if date_found and is_stock_related:
                        importance = get_article_importance(title, full_text)
                        article_info = {
                            'title': title,
                            'link': full_link,
                            'full_text': full_text,
                            'importance': importance,
                            'match_reason': match_reason,
                            'section': base_url.split('/')[-1],
                            'source': 'Medias24' if 'medias24.com' in base_url else 'BourseNews'
                        }
                        all_articles.append(article_info)
                        page_articles_found += 1
                        print(f"      {importance['emoji']} Found: {title[:60]}...")
                        print(f"         📍 Reason: {match_reason}")
                        print(f"         🌐 Source: {article_info['source']}")
                
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
    """Create ORIGINAL Arabic summaries for stock market articles with duplicate detection"""
    if not articles:
        return "📭 لا توجد أخبار متعلقة ببورصة الدار البيضاء اليوم."
    
    # Group articles by company/topic to detect potential duplicates
    companies_mentioned = {}
    for i, article in enumerate(articles):
        title_lower = article['title'].lower()
        for company in LISTED_COMPANIES:
            if company in title_lower:
                if company not in companies_mentioned:
                    companies_mentioned[company] = []
                companies_mentioned[company].append((i, article))
    
    # Prepare articles for Gemini with source info and duplicate detection
    articles_text = []
    for i, article in enumerate(articles, 1):
        articles_text.append(f"{i}. {article['title']}\nالمصدر: {article['source']}\nالرابط: {article['link']}")
    
    # Add duplicate information to prompt
    duplicate_info = ""
    if companies_mentioned:
        duplicate_info = "\n\nتنبيه مهم: إذا وجدت مقالين أو أكثر يتحدثان عن نفس الشركة أو الموضوع، يرجى دمجهما في ملخص واحد شامل بدلاً من تكرار المعلومات."
    
    prompt = f"""أنت محلل مالي خبير في بورصة الدار البيضاء. إليك {len(articles)} مقال متعلق بالبورصة اليوم:

{chr(10).join(articles_text)}{duplicate_info}

التعليمات الصارمة:
1. اكتب ملخصاً أصلياً وفريداً لكل مقال باللغة العربية (ليس إعادة صياغة)
2. إذا كان هناك مقالان أو أكثر عن نفس الشركة أو الموضوع، ادمجهما في ملخص واحد شامل
3. ركز فقط على التأثير على البورصة والاستثمارات
4. جملتان قصيرتان كحد أقصى لكل ملخص (أو ثلاث جمل إذا كان مدموج)
5. استخدم معرفتك المالية لتحليل التأثير المحتمل
6. اذكر التأثير المحتمل على سعر السهم أو المؤشر
7. تجنب نسخ المحتوى - أنشئ تحليلاً أصلياً
8. رتب حسب الأهمية (الأكثر أهمية أولاً)
9. كن مختصراً ومفيداً
10. لا تضع روابط في الملخص - سيتم إضافتها تلقائياً

تنسيق الإجابة لكل ملخص:
[الرمز التعبيري] **عنوان قصير (50 حرف كحد أقصى)**
تحليل أصلي في جملتين كحد أقصى (أو ثلاث إذا كان مدموج).

ابدأ مباشرة بالملخصات، بدون مقدمة."""

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
            
        # Add RTL formatting and links to the generated content
        gemini_content = result["candidates"][0]["content"]["parts"][0]["text"]
        
        # Process the content and add sources at the end of each summary
        formatted_content = ""
        lines = gemini_content.split('\n')
        article_index = 0
        current_summary = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if (line.startswith('🚨') or line.startswith('📈') or line.startswith('📊')) and '**' in line:
                # This is a title line with emoji
                if current_summary and article_index > 0:
                    # Finish previous article
                    summary_text = ' '.join(current_summary)
                    if not summary_text.endswith('.'):
                        summary_text += '.'
                    # Use invisible character to prevent link preview compression
                    formatted_content += f"‏{summary_text} 📰 ‏[المصدر]({articles[min(article_index-1, len(articles)-1)]['link']})\n\n"
                    current_summary = []
                
                # Start new article
                formatted_content += f"‏{line}\n"
                article_index += 1
            elif line.startswith('**') and line.endswith('**'):
                # This is a title line without emoji
                if current_summary and article_index > 0:
                    # Finish previous article
                    summary_text = ' '.join(current_summary)
                    if not summary_text.endswith('.'):
                        summary_text += '.'
                    # Use invisible character to prevent link preview compression
                    formatted_content += f"‏{summary_text} 📰 ‏[المصدر]({articles[min(article_index-1, len(articles)-1)]['link']})\n\n"
                    current_summary = []
                
                # Start new article
                formatted_content += f"‏{line}\n"
                article_index += 1
            else:
                # This is content
                current_summary.append(line)
        
        # Don't forget the last article
        if current_summary and article_index > 0:
            summary_text = ' '.join(current_summary)
            if not summary_text.endswith('.'):
                summary_text += '.'
            # Use invisible character to prevent link preview compression
            formatted_content += f"‏{summary_text} 📰 ‏[المصدر]({articles[min(article_index-1, len(articles)-1)]['link']})\n\n"
        
        return formatted_content
        
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return format_articles_fallback(articles)

def format_articles_fallback(articles):
    """Fallback formatting if Gemini fails - in Arabic with RTL"""
    if not articles:
        return "📭 لا توجد أخبار متعلقة ببورصة الدار البيضاء اليوم."
    
    formatted = f"‏📈 *بورصة الدار البيضاء - {len(articles)} أخبار اليوم*\n\n"
    
    for article in articles:
        title = article['title'][:70] + ('...' if len(article['title']) > 70 else '')
        formatted += f"‏{article['importance']['emoji']} **{title}**\n"
        formatted += f"‏شركة مدرجة في البورصة مع تأثير محتمل على الأسعار. 📰 [المصدر]({article['link']})\n\n"
    
    return formatted

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",  # Enable markdown for formatting
        "disable_web_page_preview": True,  # Disable link previews to prevent compression
        "disable_notification": False  # Keep notifications enabled
    }
    
    try:
        response = requests.post(url, data=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Message sent to Telegram successfully!")
            return True
        else:
            print(f"❌ Telegram API error: {response.status_code}")
            print("Response:", response.text)
            
            # If markdown fails, try with HTML parse mode
            if "parse_mode" in str(response.text).lower():
                print("🔄 Retrying with HTML parse mode...")
                payload["parse_mode"] = "HTML"
                # Convert markdown to HTML for links
                html_text = text.replace("[المصدر]", "<a href='#'>المصدر</a>")
                html_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html_text)
                payload["text"] = html_text
                
                response = requests.post(url, data=payload, timeout=15)
                if response.status_code == 200:
                    print("✅ Message sent with HTML formatting!")
                    return True
            
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
            
            # Add header only (no footer) with RTL formatting
            today = datetime.now().strftime("%d %B %Y")
            final_message = f"‏🏛️ **بورصة الدار البيضاء** - {today}\n\n{summary}"
            
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
        error_message = f"‏❌ خطأ في البوت: {str(e)}"
        print(error_message)
        send_to_telegram(error_message) 
