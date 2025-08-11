import time
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
from bs4.element import Tag
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

HEBREW_TO_ENGLISH_KEYS = {
    "שלדה": "frame",
    "בולם קדמי": "fork",
    "בולם אחורי": "rear_shock",
    "אורך בולם מקסימלי": "max_fork_length",
    "גלגל קדמי": "front_wheel",
    "גלגל אחורי": "rear_wheel",
    "צמיגים": "tires",
    "סרט חישוק": "rim_tape",
    "רוחב צמיג מקסימלי": "max_tire_width",
    "ידיות הילוכים": "shifters",
    "מעביר אחורי": "rear_derailleur",
    "קראנק": "crankset",
    "גלגל שיניים מקסימלי": "max_chainring_size",
    "קסטה": "cassette",
    "שרשרת": "chain",
    "אוכף": "saddle",
    "מוט אוכף": "seatpost",
    "כידון": "handlebar",
    "גריפים": "grips",
    "מעצורים": "brakes",
    "רוטרים": "rotors",
    "סוללה": "battery",
    "מנוע": "motor",
    "מערכת שליטה": "display",
    "מטען": "charger",
    "משקל": "weight",
    "פדלים": "pedals",
    "סטם / עמוד כידון": "stem",
    "משקל": "weight",
    "הד-סט / מיסבי היגוי": "headset",
     "תוספות:": "additionals",
     "צמיג קדמי": "front_tire",
     "צמיג אחורי": "rear_tire",
     "חישוקים": "rims",
     "נאבה קדמית": "front_hub",
     "נאבה אחורית": "rear_hub",
     "משקל:": "weight",
     "משקל": "weight"

}



# ----- Setup -----
BASE_URL = "https://ctc.co.il"
TARGET_URL = f"{BASE_URL}/product-category/bikes/e-bikes/e-mtb/"

scraped_data = []

#---trigger lazy loading for image appear---
def scroll_to_bottom(driver, pause=1.0):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


#--- check price is int or not----
def safe_to_int(text):
    try:
        return int(text)
    except (ValueError, TypeError):
        return ("צור קשר")


def clean_model_data(raw_model):
    # Step 1: Remove Hebrew prefix like "אופניים חשמליים", "אופני הרים חשמליים"
    hebrew_prefix_pattern = r"^אופני(?:ים)?(?: הרים)? חשמליים[-]?\s*"
    cleaned = re.sub(hebrew_prefix_pattern, "", raw_model).strip()

    # Step 2: Extract all 4-digit years (2022–2026)
    years = re.findall(r"\b(2022|2023|2024|2025|2026)\b", cleaned)
    year = int(max(years)) if years else None

    # Step 3: Remove all years and year ranges like "2022-23"
    cleaned = re.sub(r"\b(2022|2023|2024|2025|2026)\b(?:\s*[-–]\s*\b(2022|2023|2024|2025|2026)\b)?", "", cleaned).strip()

    # Step 4: Split to words, and find first English word (the brand)
    words = cleaned.split()
    firm = ""
    model = ""
    for i, word in enumerate(words):
        if re.search(r'[a-zA-Z]', word):  # first English word is likely the brand
            firm = word
            model = " ".join(words[i+1:])
            break

    return firm, model, year


def ctc_bikes(driver):
    driver.get(TARGET_URL)
    # Wait for at least one gallery image to appear
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".nasa-content-page-products"))
    )
    scroll_to_bottom(driver, pause=1.5)
    time.sleep(4)  # Let lazy-loaded content settle


    # ----- Get all product links -----
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("li", class_="product-warp-item")
    print(f"🔗 Found {len(cards)} product links.")


    for i, card in enumerate(cards):
        print(f"--- Processing Product {i+1} ---") 
    
        model_tag = card.find('a', class_="name")
        if model_tag:
          raw_model_text = model_tag.get_text(strip=True)
        
        # ---- Price ----
        price_wrap = card.find("div", class_="price-wrap")

        original_price = None
        discounted_price = None

        if price_wrap:
            # Try to find original price in <del>
            del_tag = price_wrap.find("del")
            if del_tag:
                bdi = del_tag.find("bdi")
                if bdi:
                    price_text = bdi.get_text(strip=True).replace("₪", "").replace(",", "")
                    original_price = safe_to_int(price_text)

            # Try to find discounted price in <ins>
            ins_tag = price_wrap.find("ins")
            if ins_tag:
                bdi = ins_tag.find("bdi")
                if bdi:
                    price_text = bdi.get_text(strip=True).replace("₪", "").replace(",", "")
                    discounted_price = safe_to_int(price_text)

            # Fallback: find any <bdi> if neither del nor ins found
            if not original_price and not discounted_price:
                bdi = price_wrap.select_one("bdi")
                if bdi:
                    price_text = bdi.get_text(strip=True).replace("₪", "").replace(",", "")
                    original_price = safe_to_int(price_text)

         # ---- Image ----
        def get_best_img_url(img_tag):
            # Try to get the highest resolution from srcset or data-brsrcset
            for attr in ['data-brsrcset', 'srcset']:
                srcset = img_tag.get(attr)
                if srcset:
                    high_res = srcset.split(',')[-1].strip().split(' ')[0]
                    return high_res
            # Fallback to src
            return img_tag.get('src')

        main_img_url = None
        back_img_url = None

        main_img_div = card.find('div', class_=['main-img'])
        if main_img_div:
            main_img = main_img_div.find('img')
            if main_img:
                main_img_url = get_best_img_url(main_img)

        back_img_div = card.find('div', class_=['back-img', 'back'])
        if back_img_div:
            back_img = back_img_div.find('img')
            if back_img:
                back_img_url = get_best_img_url(back_img)

        print("Main image:", main_img_url)
        print("Back image:", back_img_url)

        # Use main_img_url as the main image, but you can also store back_img_url if needed
        img_url = main_img_url

        #-----Product URL-------
        product_url = card.find("a", class_="product-img").get("href")
     
        firm, model, year = clean_model_data(raw_model_text)

        products_data = {
            "firm": firm,
            "model": model,
            "year": year,
            "original_price": original_price,
            "disc_price": discounted_price,
            "image_url": img_url,
            "product_url": product_url
        }

        # 🔍 Look for the specifications table

        if product_url:
            try:
                driver.get(product_url)
                scroll_to_bottom(driver, pause=1.5)
                time.sleep(3)
                product_soup = BeautifulSoup(driver.page_source, "html.parser")

            
                spec_table = product_soup.find("table", class_="spec-table")

                #-----  Gallery images ---
      
                gallery_images_urls = []

                # Get all thumbnail wrappers
                for thumb_div in product_soup.select('.nasa-wrap-item-thumb'):
                    #print(product_soup.select('.nasa-wrap-item-thumb'))
                    img_tag = thumb_div.find('img')
                    img_url = None

                    if img_tag:
                        # Check srcset or data-brsrcset for the highest resolution
                        if img_tag.has_attr('data-brsrcset'):
                            srcset_items = img_tag['data-brsrcset'].split(',')
                            high_res = srcset_items[-1].strip().split(' ')[0]
                            img_url = high_res
                        elif img_tag.has_attr('srcset'):
                            srcset_items = img_tag['srcset'].split(',')
                            high_res = srcset_items[-1].strip().split(' ')[0]
                            img_url = high_res
                        elif thumb_div.has_attr('data-thumb_org'):
                            img_url = thumb_div['data-thumb_org']
                        elif img_tag.has_attr('src'):
                            img_url = img_tag['src']
                    
                    if img_url and not img_url.startswith("data:image/"):
                        gallery_images_urls.append(img_url)


                # Remove duplicates just in case
                gallery_images_urls = list(set(gallery_images_urls))
                products_data["gallery_images_urls"] = gallery_images_urls
                
                time.sleep(4)
       
                for tr in spec_table.find_all("tr"):
                    th = tr.find("th")
                    td = tr.find("td")
                    if th and td:
                        key = th.get_text(strip=True)
                        val = td.get_text(strip=True)

                        if key == 'גלגל שיניים מקסימלי':
                            continue

                        if key == 'רוחב צמיג מקסימלי':
                            continue

                        if key == 'אורך בולם מקסימלי':
                            continue

                        products_data[key] = val
                        '''
                        print(f"✅ Specs scraped from product page.")
                        print("🔧 Product specs found:")
                        print(f"{key} | {val}")
                        '''
            except Exception as e:
                print(f"⚠️ Error scraping product page ({product_url}): {e}")

        translated_row = {}
        for key, value in products_data.items():
            translated_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)  # default to original key if no translation
            translated_row[translated_key] = value

        battery_value = translated_row.get("battery", "")
        wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)

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
        #print(f"DEBUG: fork_text = '{fork_text}'")
        match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
        #print(match)
        if match:
            fork_length = match.group(1)
            translated_row["fork length"] = int(fork_length)
        else:
            raise ValueError(f"❌ Could not extract fork length from: '{fork_text}'")

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

        scraped_data.append(translated_row)

    return scraped_data

driver = uc.Chrome()
products = ctc_bikes(driver)
driver.quit()

 # Save to JSON
import os
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
output_file = os.path.join(output_dir, "ctc.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=4)       

print(f"\n✅ All data saved to {output_file}")