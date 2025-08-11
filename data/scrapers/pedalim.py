import time
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

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
    "פדלים": "pedals"
}

# ----- Setup -----
BASE_URL = "https://pedalim.co.il"
TARGET_URL = f"{BASE_URL}/אופניים-חשמליים"  # Category may vary

scraped_data = []

def safe_to_int(text):
    try:
        return int(str(text).replace(',', '').replace('₪', '').strip())
    except (ValueError, AttributeError):
        return "צור קשר"

def pedalim_bikes(driver):
    driver.get(TARGET_URL)
    time.sleep(5)

    # ----- Get all product links -----
    soup = BeautifulSoup(driver.page_source, "html.parser")
    products_grid = soup.select_one("div.products.row")

    cards = soup.find_all("div", class_="col-xs-6 col-sm-4 col-md-4 col-lg-4")


    for product in cards:

        # ---- Basic Info from product card ----
        firm_tag = product.find("div", class_="description")
        firm_text = firm_tag.find("span").get_text(strip=True) if firm_tag else "N/A"

        model_tag = product.find("div", class_="description")
        model_text = firm_tag.find("h2").get_text(strip=True) if model_tag else "N/A"
        model_text = re.sub(r"^[\u0590-\u05FF\s]+(?=[A-Za-z])", "", model_text).strip()

        # Remove brand name from model_text if present
        if firm_text and model_text:
            model_text = re.sub(re.escape(firm_text), "", model_text, flags=re.IGNORECASE).strip()


        year_tag = product.find(class_="newOnSite")
        if year_tag:
            year_text_raw = year_tag.get_text(strip=True)
            match = re.search(r"\b(20\d{2})\b", year_text_raw)
            year_text = match.group(1) if match else "לא צויין"
        else:
            year_text = "לא צויין"


        disc_price_tag = product.select_one("span.saleprice")
        if disc_price_tag:
            disc_price = safe_to_int(disc_price_tag.string.strip() if disc_price_tag.string else disc_price_tag.get_text(strip=True))
        else:
            disc_price = "צור קשר"

        # Extract old price (discounted price)
        original_price_tag = product.find("span", class_="oldprice")
        if original_price_tag:
            original_price = safe_to_int(original_price_tag.string.strip() if original_price_tag.string else original_price_tag.get_text(strip=True))
        else:
            original_price = ""

        # --- Image ---

        img_tag = product.find("img")
        img_src = img_tag["data-src"] if img_tag and img_tag.has_attr("data-src") else (img_tag["src"] if img_tag and img_tag.has_attr("src") else "")
        img_url = urljoin(BASE_URL, img_src) if img_src else "N/A"

        # --- Product Link ---
        link_tag = product.find("a", href=True)
        if link_tag:
            product_url = urljoin(BASE_URL, link_tag["href"])
        else:
            product_url = "N/A"

        products_data = {
            "firm": firm_text,
            "model": model_text,
            "year": year_text,
            "original_price": original_price,
            "disc_price": disc_price,
            "image_URL": img_url,
            "product_URL": product_url
        }
        
        # ---- Scrape Specs from Product Page ----
        if product_url:
            try:
                driver.get(product_url)
                time.sleep(4)  # wait for product page to load
                product_soup = BeautifulSoup(driver.page_source, "html.parser")
                spec_list = product_soup.find("ul", class_="list-unstyled")
                time.sleep(4)  

                # Extract gallery images from thumbnails
                gallery_images_urls = []
                thumbnails_div = product_soup.find("div", class_="sp-thumbnails sp-grab")
                if thumbnails_div:
                    for img in thumbnails_div.find_all("img", class_="sp-thumbnail"):
                        src = img.get("src")
                        if src:
                            # If the src is a relative path, join with BASE_URL
                            if not src.startswith("http"):
                                src = urljoin(BASE_URL, src)
                            gallery_images_urls.append(src)
                products_data["gallery_images_urls"] = gallery_images_urls

                if spec_list:
                    items = spec_list.find_all("li")
                    for item in items:
                        # Remove embedded image
                        img = item.find("img")
                        if img:
                            img.decompose()

                        # Extract value
                        val_tag = item.find("span", class_="attributeList")
                        val = val_tag.get_text(strip=True) if val_tag else ""

                        # Extract key (everything except val)
                        full_text = item.get_text(strip=True)
                        key = full_text.replace(val, "").strip() if val in full_text else full_text

                        if key == 'הערות מוצר':
                            continue

                        if key and val:
                            products_data[key] = val
                        #print("🔧 Product specs found:")
                    #print(f"{key} | {val}")
            except Exception as e:
                print(f"⚠️ Error scraping product page: {e}")
        else:
            print("⚠️ No product URL found.")

        translated_row = {}
        for key, value in products_data.items():
            translated_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)  # default to original key if no translation
            translated_row[translated_key] = value

        battery_value = translated_row.get("battery", "")
        wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)

        #extract Wh from battery value
        if wh_match:
            wh_value = int(wh_match.group(1))  # Convert to int if needed
            translated_row["wh"] = wh_value
        else:
        # If no 'Wh' found, try to find a 3-digit number
            fallback_match = re.search(r"\b(\d{3})\b", battery_value)
            if fallback_match:
                translated_row["wh"] = int(fallback_match.group(1))

        #---fork length----
        fork_text = translated_row.get("fork", "")
        print(f"DEBUG: fork_text = '{fork_text}'")
        match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
        if match:
            fork_length = match.group(1)
            translated_row["fork length"] = int(fork_length)
        else:
            print(f"⚠️ Could not extract fork length from: '{fork_text}'")
            translated_row["fork length"] = None


        #----sub-category----
        fork_length_str = translated_row.get("fork length")

        if fork_length_str:
            try:
                fork_length = int(fork_length_str)
                if fork_length == 120:
                    translated_row["sub-category"] = "cross-country"
                elif fork_length in [130, 140, 150]:
                    translated_row["sub-category"] = "trail"
                elif fork_length in [160, 170, 180]:
                    translated_row["sub-category"] = "enduro"
                else:
                    raise ValueError(f"Unexpected fork length value: {fork_length}")
            except ValueError as e:
                raise ValueError(f"Invalid fork length '{fork_length_str}': {e}")
        else:
            translated_row["sub-category"] = None

        scraped_data.append(translated_row)

    return scraped_data
        
driver = uc.Chrome()
products = pedalim_bikes(driver)
driver.quit()

# 💾 Save progress to Json
import os
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
output_file = os.path.join(output_dir, "pedalim.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"📁 JSON file updated: '{output_file}'")