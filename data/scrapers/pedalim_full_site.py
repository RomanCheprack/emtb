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
    "הערות מוצר": "product_notes",
    "שילדה": "frame",
    "מזלג קדמי": "fork",
    "בולם אחורי": "rear_shock",
    "מנוע": "motor",
    "בטריה": "battery",
    "ידיות הילוכים": "shifters",
    "מעביר אחורי": "rear_derailleur",
    "קראנק": "crankset",
    "ציר מרכזי": "bottom_bracket",
    "קסטה": "cassette",
    "שרשרת": "chain",
    "מעצורים": "brakes",
    "גלגלים": "wheels",
    "צמיגים": "tires",
    "אוכף": "saddle",
    "מוט אוכף": "seatpost",
    "כידון": "handlebar",
    "מוט כידון": "stem",
    "מיסבי היגוי": "headset",
    "פדלים": "pedals",
    "מעביר קדמי": "front_derailleur",
    "מעביר אחורי": "rear_derailleur",
}

# ----- Setup -----
BASE_URL = "https://pedalim.co.il"
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

scraped_data = []

PEDALIM_TARGET_URLS = [
    {"url": f"{BASE_URL}/אופניים-חשמליים", "category": "electric", "sub_category": "electric_mtb"},
    {"url": f"{BASE_URL}/אופני-הרים?סוג%20אופניים=307444&bsfilter-13166=307444", "category": "mtb", "sub_category": "hardtail"},
    {"url": f"{BASE_URL}/אופני-הרים?סוג%20אופניים=306187&bsfilter-13166=306187", "category": "mtb", "sub_category": "full_suspension"},
    {"url": f"{BASE_URL}/אופני-הרים?סוג%20אופניים=310291&bsfilter-13166=310291", "category": "mtb", "sub_category": "tandem"},
    {"url": f"{BASE_URL}/אופני-כביש?סוג%20אופניים=339667,339773&bsfilter-13166=339667,339773", "category": "gravel", "sub_category": "gravel"},
    {"url": f"{BASE_URL}/אופני-כביש?סוג%20אופניים=306189,307446&bsfilter-13166=306189,307446", "category": "road", "sub_category": "road"}
]

def safe_to_int(text):
    try:
        return int(str(text).replace(',', '').replace('₪', '').strip())
    except (ValueError, AttributeError):
        return "צור קשר"

def rewrite_description_with_chatgpt(original_text, api_key):
    """Rewrite product description using ChatGPT API"""
    if not original_text or not api_key:
        return original_text
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים בחנויות אינטרנטיות..."},
                {"role": "user", "content": f"להלן תיאור האופניים: \n\n{original_text}\n\nכתוב גרסה שיווקית חדשה."}
            ],
            "temperature": 0.6,
            "max_tokens": 500
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except:
        return original_text

def pedalim_bikes(driver, output_file):
    for entry in PEDALIM_TARGET_URLS:
        target_url = entry["url"]
        category_text = entry["category"]
        sub_category_text = entry.get("sub_category", None)
        print(f"\n🌐 Scraping: {target_url}")
        driver.get(target_url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("div", class_="col-xs-6 col-sm-4 col-md-4 col-lg-4")
        print(f"✅ Found {len(cards)} products.\n")
        for i, product in enumerate(cards):
            print(f"--- Processing Product {i+1} ---")
            # ---- Basic Info ----
            firm_tag = product.find("div", class_="description")
            firm_text = firm_tag.find("span").get_text(strip=True) if firm_tag else "N/A"
            model_tag = product.find("div", class_="description")
            model_text = firm_tag.find("h2").get_text(strip=True) if model_tag else "N/A"
            model_text = re.sub(r"^[\u0590-\u05FF\s]+(?=[A-Za-z])", "", model_text).strip()
            if firm_text and model_text:
                model_text = re.sub(re.escape(firm_text), "", model_text, flags=re.IGNORECASE).strip()
            year_tag = product.find(class_="newOnSite")
            year_text = "לא צויין"
            if year_tag:
                match = re.search(r"\b(20\d{2})\b", year_tag.get_text(strip=True))
                year_text = match.group(1) if match else "לא צויין"
            # ---- Price ----
            oldprice_tag = product.find("span", class_="oldprice")
            saleprice_tag = product.select_one("span.saleprice")
            regular_price_tag = product.find("span", class_="price")
            original_price = disc_price = ""
            if oldprice_tag and saleprice_tag:
                original_price = safe_to_int(oldprice_tag.get_text(strip=True))
                disc_price = safe_to_int(saleprice_tag.get_text(strip=True))
            elif regular_price_tag:
                original_price = safe_to_int(regular_price_tag.get_text(strip=True))
            elif saleprice_tag:
                original_price = safe_to_int(saleprice_tag.get_text(strip=True))
            else:
                original_price = "צור קשר"
            # ---- Image ----
            img_tag = product.find("img")
            img_src = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
            img_url = urljoin(BASE_URL, img_src) if img_src else "N/A"
            # ---- Link ----
            link_tag = product.find("a", href=True)
            product_url = urljoin(BASE_URL, link_tag["href"]) if link_tag else "N/A"
            product_data = {
                "source": {"importer": "Pedalim", "domain": BASE_URL, "product_url": product_url},
                "firm": firm_text,
                "model": model_text,
                "year": year_text,
                "category": category_text,
                "sub_category": sub_category_text,
                "original_price": original_price,
                "disc_price": disc_price,
                "images": {"image_url": img_url, "gallery_images_urls": []},
                "specs": {}
            }
            # ---- Product Page ----
            if product_url != "N/A":
                try:
                    driver.get(product_url)
                    time.sleep(4)
                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    # Description
                    desc_element = page_soup.find("ul", class_="desc_bullet")
                    if desc_element:
                        description_text = " ".join([li.get_text(strip=True) for li in desc_element.find_all("li")])
                    else:
                        description_text = ""
                    rewritten_description = rewrite_description_with_chatgpt(description_text, CHATGPT_API_KEY) if description_text else ""
                    product_data["rewritten_description"] = rewritten_description
                    # Gallery images
                    gallery_images_urls = []
                    thumbs_div = page_soup.find("div", class_="sp-thumbnails sp-grab")
                    if thumbs_div:
                        for img in thumbs_div.find_all("img", class_="sp-thumbnail"):
                            # Try multiple src attributes (lazy loading often uses data-src)
                            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                            if src:
                                src = src.strip()  # Remove any whitespace
                                if src and not src.startswith("http"):
                                    src = urljoin(BASE_URL, src)
                                # Only add non-empty URLs
                                if src and src not in gallery_images_urls:
                                    gallery_images_urls.append(src)
                    # Also try alternative selectors if no images found
                    if not gallery_images_urls:
                        # Try finding images in other common gallery structures
                        gallery_imgs = page_soup.find_all("img", class_="sp-thumbnail")
                        for img in gallery_imgs:
                            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                            if src:
                                src = src.strip()
                                if src and not src.startswith("http"):
                                    src = urljoin(BASE_URL, src)
                                if src and src not in gallery_images_urls:
                                    gallery_images_urls.append(src)
                    product_data["images"]["gallery_images_urls"] = gallery_images_urls
                    # ---- Specs ----
                    # Try multiple selectors for specs list
                    spec_list = None
                    specs_found = False
                    possible_selectors = [
                        ("ul", {"class": "list-unstyled"}),
                        ("ul", {"class": "list-unstyled properties-product"}),
                        ("ul", {"class": "properties-product"}),
                        ("div", {"class": "properties-product"}),
                        ("div", {"id": "specifications"}),
                        ("div", {"class": "product-specs"}),
                    ]
                    
                    for tag_name, attrs in possible_selectors:
                        spec_list = page_soup.find(tag_name, attrs)
                        if spec_list:
                            break
                    
                    if spec_list:
                        for li in spec_list.find_all("li"):
                            # Remove images from text extraction
                            for img in li.find_all("img"): img.decompose()
                            
                            # Try multiple methods to extract key and value
                            key = None
                            val = None
                            
                            # Method 1: Look for span with class "attributeList" (original method)
                            val_tag = li.find("span", class_="attributeList")
                            if val_tag:
                                val = val_tag.get_text(strip=True)
                                full_text = li.get_text(strip=True)
                                key = full_text.replace(val, "").strip()
                            else:
                                # Method 2: Look for spans with title/value classes
                                key_tag = li.find("span", class_="titleKey") or li.find("span", class_="title")
                                val_tag = li.find("span", class_="valueKey") or li.find("span", class_="value")
                                
                                if key_tag and val_tag:
                                    key = key_tag.get_text(strip=True)
                                    val = val_tag.get_text(strip=True)
                                else:
                                    # Method 3: Look for any spans - first is key, second is value
                                    spans = li.find_all("span")
                                    if len(spans) >= 2:
                                        key = spans[0].get_text(strip=True)
                                        val = spans[1].get_text(strip=True)
                                    elif len(spans) == 1:
                                        # Single span might be the value, key is rest of text
                                        val = spans[0].get_text(strip=True)
                                        full_text = li.get_text(strip=True)
                                        key = full_text.replace(val, "").strip()
                                    else:
                                        # Method 4: Look for bold/strong tags as keys
                                        bold_tag = li.find("b") or li.find("strong")
                                        if bold_tag:
                                            key = bold_tag.get_text(strip=True)
                                            full_text = li.get_text(strip=True)
                                            val = full_text.replace(key, "").strip()
                                        else:
                                            # Method 5: Split by colon or dash if present
                                            full_text = li.get_text(strip=True)
                                            if ":" in full_text:
                                                parts = full_text.split(":", 1)
                                                key = parts[0].strip()
                                                val = parts[1].strip()
                                            elif "-" in full_text and len(full_text.split("-", 1)) == 2:
                                                parts = full_text.split("-", 1)
                                                key = parts[0].strip()
                                                val = parts[1].strip()
                            
                            if key and val and key != "הערות מוצר":
                                english_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)
                                product_data["specs"][english_key] = val
                                specs_found = True
                    
                    # If still no specs found, try looking for any ul with li elements containing specs
                    if not product_data["specs"]:
                        all_uls = page_soup.find_all("ul")
                        for ul in all_uls:
                            lis = ul.find_all("li")
                            if len(lis) > 3:  # Likely a specs list if it has multiple items
                                for li in lis:
                                    for img in li.find_all("img"): img.decompose()
                                    full_text = li.get_text(strip=True)
                                    if ":" in full_text:
                                        parts = full_text.split(":", 1)
                                        key = parts[0].strip()
                                        val = parts[1].strip()
                                        if key and val and key != "הערות מוצר" and len(key) < 50:  # Reasonable key length
                                            english_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)
                                            product_data["specs"][english_key] = val
                                            specs_found = True
                                if product_data["specs"]:
                                    break
                    
                    # Debug output if no specs found
                    if not specs_found and not product_data["specs"]:
                        print(f"  ⚠️ No specs found for {product_data.get('firm', 'N/A')} {product_data.get('model', 'N/A')}")
                except Exception as e:
                    print(f"⚠️ Error scraping product page ({product_url}): {e}")
            # ---- Battery Wh ----
            battery_value = product_data.get("specs", {}).get("battery", "")
            wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
            if wh_match:
                product_data["wh"] = int(wh_match.group(1))
            else:
                fallback_match = re.search(r"\b(\d{3})\b", battery_value)
                if fallback_match:
                    product_data["wh"] = int(fallback_match.group(1))
            # ---- Fork length & style ----
            fork_text = product_data.get("specs", {}).get("fork", "")
            match = re.search(r'(?<!\d)(40|50|60|70|80|90|100|110|120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
            fork_length = int(match.group(1)) if match else None
            product_data["fork length"] = fork_length
            if fork_length:
                if fork_length in [40, 50, 60, 70, 80, 90, 100, 110, 120]: product_data["style"] = "cross-country"
                elif fork_length in [130, 140, 150]: product_data["style"] = "trail"
                elif fork_length in [160, 170, 180]: product_data["style"] = "enduro"
            scraped_data.append(product_data)
            # ---- Save progress ----
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(scraped_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"⚠️ Could not save progress: {e}")
        print(f"✅ Completed {category_text}: {len([p for p in scraped_data if p.get('category') == category_text])} products")
    return scraped_data

# --- Setup Output File ---
if __name__ == '__main__':
    try:
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "data" / "scraped_raw_data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = output_dir / "pedalim_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Error setting up output directory: {e}")
        exit(1)

    # --- Run Scraper ---
    products = []
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless=new')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        driver = uc.Chrome(options=options)
        products = pedalim_bikes(driver, output_file)
    except Exception as e:
        print(f"❌ Chrome driver error: {e}")
    finally:
        if driver: driver.quit()

    print(f"\n✅ Scraping completed! Total products: {len(products)}. Saved to {output_file}")
