# -*- coding: utf-8 -*-
import time
import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
import requests

# ----------------------------
# CONFIGURATION
# ----------------------------
HEBREW_TO_ENGLISH_KEYS = {
    "שלדה": "frame",
    "מהלך בולמים": "travel",
    "בולם קדמי": "fork",
    "בולם אחורי": "rear_shock",
    "מערכת שליטה": "control_system",
    "מערכת הנעה": "motor",
    "בטריה": "battery",
    "מסך תצוגה": "display",
    "מטען": "charger",
    "מעביר אחורי": "rear_derailleur",
    "ידיות הילוכים": "shifters",
    "קראנק": "crankset",
    "מוביל שרשרת": "chain_guide",
    "שרשרת": "chain",
    "שרשראות": "chainring",
    "קסטה": "cassette",
    "ברקסים": "brakes",
    "דיסקים": "rotors",
    "כידון": "handlebar",
    "מוט אוכף": "seatpost",
    "אוכף": "saddle",
    "סטם": "stem",
    "צמיג קדמי": "front_tire",
    "צמיג אחורי": "rear_tire",
    "תאורה": "lighting",
    "נאבה קדמית": "front_hub",
    "נאבה אחורית": "rear_hub",
    "גלגלים": "wheels",
    "מיסבי היגוי": "headset",
    "מייסבי היגוי": "headset",
    "תוספות": "accessories",
    "אביזרים": "accessories",
    "חישוקים": "rims",
    "חשוקים": "rims",
    "שפיצים": "spokes",
    "משקל משוער": "weight",
    "מק\"ט": "catalog_number",
    "ציר מרכזי": "bottom_bracket",
    "מסייבי היגוי": "headset",
    "סט גלגלים": "wheels",
    "פדלים": "pedals",
    "משקל": "weight",
    "מעביר קדמי": "front_derailleur",
    "דיסקים": "rotors",
    "צמיגים": "tires",
    "אבזור": "accessories",
    "מזלג  קדמי": "fork",
    "מזלג קדמי": "fork",
    "ידיות ברקסים": "brake_levers",
}

BASE_URL = "https://www.cobra-bordo.co.il"
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

COBRA_TARGET_URLS = [
    {"url": f"{BASE_URL}/158456-אופני-הרים-חשמליים", "category": "electric", "sub_category": "electric_mtb", "firm": "Scott"},
    {"url": f"{BASE_URL}/153435-אופני-הרים-שיכוך-מלא-/245985", "category": "mtb", "sub_category": "full_suspension", "style": "cross-country"},
    {"url": f"{BASE_URL}/153435-אופני-הרים-שיכוך-מלא-/245986", "category": "mtb", "sub_category": "full_suspension", "style": "trail"},
    {"url": f"{BASE_URL}/153435-אופני-הרים-שיכוך-מלא-/245987", "category": "mtb", "sub_category": "full_suspension", "style": "all-mountain"},
    {"url": f"{BASE_URL}/153435-אופני-הרים-שיכוך-מלא-/245988", "category": "mtb", "sub_category": "full_suspension", "style": "enduro"},
    {"url": f"{BASE_URL}/153436-אופני-הרים-זנב-קשיח", "category": "mtb", "sub_category": "hardtail", "style": "cross-country"},
    {"url": f"{BASE_URL}/154360-אופני-כביש", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/179592-אופני-עיר-", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/155066-אופני-ילדים-ונוער", "category": "kids", "sub_category": "kids"},
    {"url": f"{BASE_URL}/167809-אופני-קיבוץ", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/217081-אופני-דחיפה-איזון-לילדים", "category": "kids", "sub_category": "push_bike"},
]

scraped_data = []

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------
def extract_price(price_str):
    match = re.search(r'\d+', price_str.replace(",", ""))
    return int(match.group()) if match else "צור קשר"

def is_driver_alive(driver):
    try:
        driver.current_url
        return True
    except:
        return False

def recreate_driver():
    try:
        print("🔄 Recreating Chrome driver...")
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        driver = uc.Chrome(options=options)
        print("✅ Chrome driver created successfully!")
        return driver
    except Exception as e:
        print(f"❌ Failed to recreate Chrome driver: {e}")
        return None

def rewrite_description_with_chatgpt(text, api_key):
    if not text or not api_key:
        return text
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים בחנויות אינטרנטיות. צור גרסה חדשה ומושכת."},
                {"role": "user", "content": text}
            ],
            "temperature": 0.6,
            "max_tokens": 500
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        res.raise_for_status()
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"⚠️ ChatGPT rewrite error: {e}")
        return text

def save_json(data, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"💾 Saved {len(data)} products to {path}")
    except Exception as e:
        print(f"⚠️ Failed to save JSON: {e}")

def parse_specifications(spec_soup):
    specs = {}
    if not spec_soup:
        return specs
    all_lis = spec_soup.find_all("li")
    for li in all_lis:
        key_tag = li.find("b")
        val_tag = li.find("span")
        if key_tag and val_tag:
            key = key_tag.get_text(strip=True)
            val = val_tag.get_text(strip=True)
            if key == 'מק"ט':
                continue
            specs[HEBREW_TO_ENGLISH_KEYS.get(key, key)] = val
    return specs

def extract_fork_length(fork_text):
    match = re.search(r'(?<!\d)(40|60|80|100|120|130|140|150|160|170|180)(?!\d)', fork_text)
    return int(match.group(1)) if match else None

def determine_style_from_fork(fork_length):
    if fork_length in [40, 60, 80, 100, 120]:
        return "cross-country"
    elif fork_length in [130, 140, 150]:
        return "trail"
    elif fork_length in [160, 170, 180]:
        return "enduro"
    return None

# ----------------------------
# SCRAPER FUNCTION
# ----------------------------
def scrape_cobra(driver, output_file):
    for entry in COBRA_TARGET_URLS:
        url = entry["url"]
        category = entry["category"]
        sub_category = entry.get("sub_category")
        firm = entry.get("firm")
        print(f"\n🌐 Scraping {url}")

        if not is_driver_alive(driver):
            driver = recreate_driver()
            if not driver:
                print("❌ Cannot continue, driver dead")
                break

        for attempt in range(3):
            try:
                driver.get(url)
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                break
            except:
                print(f"🔄 Retry {attempt+1} for {url}")
                time.sleep(2)
        else:
            print(f"❌ Failed to load {url}")
            continue

        cards = soup.find_all("div", class_="layout_list_item")[5:]  # skip first 5
        print(f"✅ Found {len(cards)} products")

        for card in cards:
            model_tag = card.find("h3", class_="title")
            if not model_tag:
                continue
            model_text = model_tag.get_text(strip=True)
            year_match = re.search(r'\b(2023|2024|2025|2026)\b', model_text)
            year = int(year_match.group(1)) if year_match else None
            cleaned_model = re.sub(r"(קיבוץ|קוברה|הילוכי|שימנו|7|אופני|סקוט|חשמליים|–|-)", "", model_text)
            cleaned_model = re.sub(r'\b(2023|2024|2025|2026)\b', '', cleaned_model).strip()
            model_text = cleaned_model

            # Detect firm
            for f in ["SCOTT", "COBRA", "FAST"]:
                if f in model_text.upper():
                    firm = f.capitalize()
                    model_text = model_text.replace(f, "").strip()

            # Price extraction
            origin_price_tag = card.find('p', class_="origin_price")
            price_tag = card.find('span', class_='price')
            original_price = discounted_price = None
            if origin_price_tag:
                for span in origin_price_tag.find_all("span", style=lambda v: v and "display: none" in v):
                    span.decompose()
                original_price = extract_price(origin_price_tag.get_text(strip=True))
                if price_tag:
                    for span in price_tag.find_all("span", style=lambda v: v and "display: none" in v):
                        span.decompose()
                    discounted_price = extract_price(price_tag.get_text(strip=True))
            elif price_tag:
                for span in price_tag.find_all("span", style=lambda v: v and "display: none" in v):
                    span.decompose()
                original_price = extract_price(price_tag.get_text(strip=True))

            # Image & URL
            img_tag = card.find('img', class_="img-responsive")
            img_url = img_tag['src'] if img_tag else None
            link_tag = card.select_one("a")
            product_url = urljoin(BASE_URL, link_tag['href'].strip()) if link_tag else None

            # Product data skeleton
            product_data = {
                "source": {"importer": "Cobra-Bordo", "domain": BASE_URL, "product_url": product_url},
                "firm": firm, "model": model_text, "year": year,
                "category": category, "sub_category": sub_category,
                "original_price": original_price, "disc_price": discounted_price,
                "images": {"image_url": img_url, "gallery_images_urls": []},
            }

            # Visit product page
            if product_url:
                try:
                    driver.get(product_url)
                    time.sleep(3)
                    prod_soup = BeautifulSoup(driver.page_source, "html.parser")

                    # Description rewrite
                    desc_elem = prod_soup.find("div", id="item_current_sub_title")
                    original_desc = desc_elem.get_text(strip=True) if desc_elem else ""
                    rewritten_desc = rewrite_description_with_chatgpt(original_desc, CHATGPT_API_KEY) if CHATGPT_API_KEY else original_desc
                    product_data["rewritten_description"] = rewritten_desc

                    # Gallery images
                    ul = prod_soup.find('ul', class_='lightSlider lsGrab lSSlide')
                    if ul:
                        gallery = [img['src'] for img in ul.find_all('img') if img.get('src')]
                        product_data["images"]["gallery_images_urls"] = gallery

                    # Specs
                    spec_soup = prod_soup.find("div", class_="specifications row")
                    specs = parse_specifications(spec_soup)
                    if specs:
                        product_data["specs"] = specs
                        # Battery Wh
                        battery_value = specs.get("battery", "")
                        wh_match = re.search(r"(\d+)\s*Wh", battery_value)
                        if wh_match:
                            product_data["wh"] = int(wh_match.group(1))
                        else:
                            fallback = re.search(r"\b(\d{3})\b", battery_value)
                            if fallback:
                                product_data["wh"] = int(fallback.group(1))

                        # Fork length & style
                        fork_len = extract_fork_length(specs.get("fork", ""))
                        product_data["fork length"] = fork_len
                        style_from_fork = determine_style_from_fork(fork_len)
                        if style_from_fork:
                            product_data["style"] = style_from_fork

                except Exception as e:
                    print(f"⚠️ Error scraping {product_url}: {e}")

            scraped_data.append(product_data)
            save_json(scraped_data, output_file)

        print(f"✅ Completed {category}: {len([p for p in scraped_data if p.get('category')==category])} products")

    return scraped_data, driver

# ----------------------------
# SETUP OUTPUT FILE
# ----------------------------
if __name__ == '__main__':
    try:
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "data" / "scraped_raw_data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = output_dir / "cobra_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        print(f"📁 Output file ready: {output_file}")
    except Exception as e:
        print(f"❌ Error setting up output directory: {e}")
        exit(1)

    # ----------------------------
    # RUN SCRAPER
    # ----------------------------
    products = []
    driver = None
    try:
        print("🚀 Starting Chrome driver...")
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless=new')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        driver = uc.Chrome(options=options)
        print("✅ Chrome driver started")
        products, driver = scrape_cobra(driver, output_file)
    except Exception as e:
        print(f"❌ Chrome driver init error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                print("🔒 Chrome driver closed")
            except:
                pass

    print(f"\n✅ Scraping completed: {len(products)} products")
    save_json(products, output_file)
