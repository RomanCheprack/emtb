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

HEBREW_TO_ENGLISH_KEYS = {
    "שלדה": "frame",
    "מידה": "size",
    "בולם קדמי": "fork",
    "בולם אחורי": "rear_shock",
    "ברקסים": "brakes",
    "מעביר אחורי": "rear_derailleur",
    "ידית הילוכים": "shifters",
    "קסטה": "cassette",
    "קרנק": "crankset",
    "שרשרת": "chain",
    "סט גלגלים": "wheelset",
    "צמיגים": "tires",
    "סטם": "stem",
    "כידון": "handlebar",
    "מוט כיסא": "seatpost",
    "חבק אוכף": "seat_clamp",
    "כיסא": "saddle",
    "משקל": "weight",
    "צבע": "color",
    "מספר קטלוגי": "sku",
    "סוג מנוע": "motor",
    "סוללה": "battery",
    "מסך": "display",
    "שלט מצבי מנוע": "control_system"
}

BASE_URL = "https://rudy-extreme.co.il/"

# ChatGPT API Configuration
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

# Cache for rewritten descriptions
description_cache_file = Path("cube_description_cache.json")
if description_cache_file.exists():
    with open(description_cache_file, "r", encoding="utf-8") as f:
        description_cache = json.load(f)
else:
    description_cache = {}

# --- Utility Functions ---
def clean_and_convert(price_text):
    price_text = price_text.replace('₪', '').replace(',', '').strip()
    if price_text:
        try:
            return int(price_text)
        except:
            return "צור קשר"
    return "צור קשר"

def rewrite_description_with_chatgpt(original_text, api_key):
    """Rewrite product description using ChatGPT API with caching."""
    if not original_text or not api_key:
        return original_text

    if original_text in description_cache:
        return description_cache[original_text]

    try:
        print("🤖 Sending description to ChatGPT for rewriting...")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים בחנויות אינטרנטיות. המטרה שלך היא לקחת תיאור אופניים קיים וליצור גרסה חדשה, מושכת ומקצועית, כך שהקורא לא יזהה את המקור. יש להתמקד בחוויית רכיבה, נוחות, בטיחות, עיצוב ויתרונות שימושיים לעיר, לטיולים או לרכיבה יומיומית."
                },
                {
                    "role": "user",
                    "content": f"להלן תיאור האופניים: \n\n{original_text}\n\nאנא כתוב גרסה שיווקית חדשה, מושכת, שמתאימה לפרסום בחנות אינטרנטית, עם דגש על חוויית רכיבה, יתרונות המוצר, עיצוב ונוחות, תוך שמירה על מהות האופניים. הרחב ותאר את האופניים בצורה שתגרום לקוראים לרצות לרכוש אותם, כולל קריאה לפעולה בסוף."
                }
            ],
            "temperature": 0.6,
            "max_tokens": 500
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        rewritten_text = response.json()['choices'][0]['message']['content'].strip()
        description_cache[original_text] = rewritten_text
        with open(description_cache_file, "w", encoding="utf-8") as f:
            json.dump(description_cache, f, ensure_ascii=False, indent=4)
        return rewritten_text
    except Exception as e:
        print(f"⚠️ Error rewriting description: {e}")
        return original_text

# --- Main Scraper ---
CUBE_TARGET_URLS = [
    {"url": f"{BASE_URL}/product-category/אופניים/חשמליים/", "category": "electric", "sub_category": "electric_mtb"},
    {"url": f"{BASE_URL}/product-category/אופניים/שיכוך-מלא/", "category": "mtb", "sub_category": "full_suspension"},
    {"url": f"{BASE_URL}/product-category/אופניים/זנב-קשיח/", "category": "mtb", "sub_category": "hardtail"},
    {"url": f"{BASE_URL}/product-category/אופניים/אופני-כביש/", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/product-category/אופניים/ילדים/", "category": "kids", "sub_category": "kids"}
]

scraped_data = []

def cube_bikes(driver, output_file):
    for entry in CUBE_TARGET_URLS:
        target_url = entry["url"]
        category_text = entry["category"]
        sub_category_text = entry.get("sub_category")
        
        print(f"\n🌐 Scraping: {target_url}")
        driver.get(target_url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("li", class_="jet-woo-builder-product")
        print(f"✅ Found {len(cards)} products.")

        for i, card in enumerate(cards):
            print(f"\n--- Processing Product {i+1} ---")
            title_tag = card.find('h5', class_='jet-woo-builder-archive-product-title')
            if not title_tag: continue
            a_tag = title_tag.find('a')
            if not a_tag: continue

            product_url = a_tag.get('href')
            full_text = a_tag.get_text(strip=True)
            firm_text = "Cube"
            model_text = full_text.replace("CUBE", "").strip() if "CUBE" in full_text else full_text

            # Price
            original_price = card.select_one('.ywcrbp_regular_price del bdi')
            discounted_price = card.select_one('.ywcrbp_sale_price bdi')
            original_price = clean_and_convert(original_price.get_text(strip=True)) if original_price else "צור קשר"
            discounted_price = clean_and_convert(discounted_price.get_text(strip=True)) if discounted_price else None

            # Thumbnail
            img_tag = card.select_one("div.jet-woo-builder-archive-product-thumbnail img")
            img_url = img_tag.get("src") if img_tag else None

            product_data = {
                "source": {"importer": "Cube", "domain": BASE_URL, "product_url": product_url},
                "firm": firm_text,
                "model": model_text,
                "year": 2024,
                "category": category_text,
                "sub_category": sub_category_text,
                "original_price": original_price,
                "disc_price": discounted_price,
                "images": {"image_url": img_url, "gallery_images_urls": []},
                "specs": {}
            }

            # --- Product Page Scraping ---
            if product_url:
                try:
                    driver.get(product_url)
                    time.sleep(3)
                    soup = BeautifulSoup(driver.page_source, "html.parser")

                    # Description - try multiple selectors
                    description_element = None
                    possible_selectors = [
                        ("div", {"class": "woocommerce-product-details__short-description"}),
                        ("div", {"class": "product-description"}),
                        ("div", {"class": "description"}),
                        ("div", {"itemprop": "description"}),
                        ("div", {"class": "product-summary"}),
                        ("div", {"class": "content"}),
                        ("div", {"class": "product-info"}),
                        ("div", {"class": "product-details"}),
                        ("div", {"class": "tab-content"}),
                        ("p", {"class": "description"}),
                        ("section", {"class": "description"})
                    ]
                    
                    for tag, attrs in possible_selectors:
                        description_element = soup.find(tag, attrs)
                        if description_element:
                            print(f"🔍 Found description using selector: {tag} with {attrs}")
                            break
                    
                    original_description = ""
                    rewritten_description = ""
                    
                    if description_element:
                        original_description = description_element.get_text(strip=True)
                        print(f"📝 Original description: {original_description[:100]}...")
                        
                        # Only rewrite if we have actual content and API key
                        if original_description.strip():
                            if CHATGPT_API_KEY:
                                rewritten_description = rewrite_description_with_chatgpt(original_description, CHATGPT_API_KEY)
                                print(f"✨ Rewritten description: {rewritten_description[:100]}...")
                            else:
                                print("⚠️ Warning: No ChatGPT API key provided, using original description")
                                rewritten_description = original_description
                        else:
                            print("⚠️ Warning: Empty description found")
                            rewritten_description = original_description
                    else:
                        print("⚠️ Warning: No product description found")
                    
                    product_data["rewritten_description"] = rewritten_description

                    # Gallery Images
                    gallery_el = soup.find('div', class_='woocommerce-product-gallery__wrapper')
                    gallery_images = [img['src'] for img in gallery_el.find_all('img') if img.get('src')] if gallery_el else []
                    product_data["images"]["gallery_images_urls"] = gallery_images

                    # Specs Extraction
                    specs = {}
                    sections = soup.select("section.elementor-inner-section")
                    for section in sections:
                        key_el = section.select_one("span.elementor-heading-title")
                        val_el = section.select_one("div.elementor-widget-text-editor")
                        key_text = key_el.get_text(strip=True).rstrip(":") if key_el else None
                        val_text = val_el.get_text(strip=True) if val_el else None
                        if not key_text and not val_text:
                            continue
                        english_key = HEBREW_TO_ENGLISH_KEYS.get(key_text, key_text) if key_text else None
                        if english_key:
                            specs[english_key] = val_text or ""
                    product_data["specs"] = specs

                    # --- Battery Wh ---
                    battery_value = specs.get("battery", "")
                    wh_match = re.search(r"(\d+)\s*Wh", battery_value)
                    if wh_match:
                        product_data["wh"] = int(wh_match.group(1))
                    else:
                        fallback = re.search(r"\b(\d{3})\b", battery_value)
                        if fallback:
                            product_data["wh"] = int(fallback.group(1))

                    # --- Fork Length ---
                    fork_text = specs.get("fork", "")
                    fork_match = re.findall(r'(\d{2,3})\s*(?:mm|travel|טיול)?', fork_text)
                    fork_lengths = [int(f) for f in fork_match if int(f) != 110]
                    if fork_lengths:
                        fork_length = max(fork_lengths)
                        product_data["fork length"] = fork_length
                        if fork_length in [40, 60, 80, 100, 120]:
                            product_data["style"] = "cross-country"
                        elif fork_length in [130, 140, 150]:
                            product_data["style"] = "trail"
                        elif fork_length in [160, 170, 180]:
                            product_data["style"] = "enduro"
                        else:
                            product_data["style"] = "unknown"
                    else:
                        product_data["fork length"] = None
                        product_data["style"] = "unknown"

                except Exception as e:
                    print(f"⚠️ Error scraping product page ({product_url}): {e}")

            # --- Append and Save ---
            scraped_data.append(product_data)
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(scraped_data, f, ensure_ascii=False, indent=4)
                print(f"💾 Saved {len(scraped_data)} products so far.")
            except Exception as e:
                print(f"⚠️ Could not save progress: {e}")

    return scraped_data

# --- Setup Output File ---
project_root = Path(__file__).resolve().parents[2]
output_dir = project_root / "data" / "scraped_raw_data"
os.makedirs(output_dir, exist_ok=True)
output_file = output_dir / "cube_data.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump([], f, ensure_ascii=False, indent=4)

# --- Run the Scraper ---
products = []
driver = None
try:
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless=new')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    driver = uc.Chrome(options=options)
    products = cube_bikes(driver, output_file)
finally:
    if driver:
        driver.quit()

print(f"\n✅ Scraping completed! Total products: {len(products)}")
