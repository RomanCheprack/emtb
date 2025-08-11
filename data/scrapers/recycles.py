import time
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

BASE_URL = "https://www.recycles.co.il/"
TARGET_URL = BASE_URL + "e_bike_mtb-אופני_הרים_חשמליים"

HEBREW_TO_ENGLISH_KEYS = {
    "שלדה": "frame",
    "מזלג": "fork",
    "כידון": "handlebar",
    "אוכף": "saddle",
    "מוט אוכף": "seatpost",
    "בולם אחורי": "rear shock",
    "מוט כידון": "stem",
    "ידיות הילוכים": "shifters",
    "מעביר אחורי": "rear derailleur",
    "בלמים": "brakes",
    "קסטה": "cassette",
    "גלגל הינע": "crankset",
    "חישוקים": "rims",
    "צמיגים": "tires",
    "סוללה": "battery",
    "לוח תצוגה": "display",
     "מטען": "charger",
    "מנוע": "motor"
}

scraped_data = []

def safe_to_int(text):
    try:
        return int(str(text).replace(',', '').replace('₪', '').replace("ליח'", '').strip())
    except (ValueError, AttributeError):
        return "צור קשר"

def recycles_bikes(driver):
    driver.get(TARGET_URL)
    time.sleep(5)

    # Parse the page source with BeautifulSoup and find product cards
    print("🔍 Searching for product cards...")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("div", class_="brdr")
    print(f"✅ Found {len(cards)} products.\n")

    for product in cards:
        # Click on the product link (if needed)
        link_tag = product.find("a", href=True)
        if link_tag:
            product_url = BASE_URL + link_tag["href"]
            print(f"Navigating to: {product_url}")
            driver.get(product_url)
            time.sleep(2)
            product_soup = BeautifulSoup(driver.page_source, "html.parser")
        else:
            continue

        # Initialize price variables
        original_price = ""
        disc_price = ""
        
        # Extract title
        title_tag = product_soup.find("div", class_="title col-12 col-xl-10")
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            
            # Remove "אופני הרים חשמליים"
            title_text = title_text.replace("אופני הרים חשמליים", "").strip()
            title_text = title_text.replace("ORBEA", "").strip()
            # Extract firm name
            firm = ""
            if "Orbea" or "ORBEA"  in title_text:
                firm = "Orbea"
                model = title_text.replace("Orbea", "").strip()
                #print(firm_text)

            # Extract year and modify format
            year_text = ""  # Initialize year_text
            for year in ["'23", "'24", "'25", "'26"]:
                if year in title_text:
                    year_text = f"20{year}".replace("'", "")
                    model = title_text.replace(year, "").strip()
                    break

        # Extract sale price (discounted price if discount exists, regular price if no discount)
        price_tag = product_soup.select_one(".saleprice")
        #print(price_tag)
        if price_tag:
            raw_price = price_tag.string.strip() if price_tag.string else price_tag.get_text(strip=True)
            sale_price = safe_to_int(raw_price)
            print(f"DEBUG: Sale price extracted: {sale_price}")
        else:
            sale_price = ""
            print("DEBUG: No sale price found")


        # Extract original price (check if there's a discount)
        price_disc_tag = product_soup.find("span", class_="oldprice")
        
        # Check if there's actually a discount (oldprice element exists AND has content)
        if price_disc_tag and price_disc_tag.get_text(strip=True):
            # There's a discount - oldprice contains the original price
            raw_disc_price = price_disc_tag.string.strip() if price_disc_tag.string else price_disc_tag.get_text(strip=True)
            original_price = safe_to_int(raw_disc_price)
            disc_price = sale_price  # This is the discounted price
            print(f"DEBUG: Discount found - Original: {original_price}, Discounted: {disc_price}")
        else:
            # No discount - salePrice is the original price
            original_price = sale_price
            disc_price = ""  # No discount, so discounted price is empty
            print(f"DEBUG: No discount - Original: {original_price}, Discounted: {disc_price}")


        #extract image
        product_soup = BeautifulSoup(driver.page_source, "html.parser")

        img_tag = product_soup.find("img", attrs={"class": lambda x: x and "sp-image" in x})
        time.sleep(10)
        img_src = img_tag["data-default"] if img_tag and img_tag.has_attr("data-default") else ""
        img_url = BASE_URL + img_src if img_src else "N/A"
        

        print(firm)
        print(model)
        print(year_text)  # Fixed: use year_text instead of year
        print(original_price)
        print(disc_price)
        print(img_url)
        print(product_url)


        products_data = {
            "firm": firm,
            "model": model,
            "year": year_text,
            "original_price": original_price,
            "disc_price": disc_price,
            "image_URL": img_url,
            "product_URL": product_url
        }
        # Extract specs from <ul class="row list-unstyled">
        spec_list = product_soup.find("ul", class_="row list-unstyled")
        if spec_list:
            spec_items = spec_list.find_all("div", class_="spec col-12 col-lg-6")
            for item in spec_items:
                key_span = item.find("span", class_="specTxt")
                val_div = item.find("div", class_="specValue")  # <-- FIXED
                if key_span and val_div:
                    key = key_span.get_text(strip=True)
                    val = val_div.get_text(strip=True)
                    products_data[key] = val

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
        if fork_text:  # Only try to extract if fork data exists
            match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
            if match:
                fork_length = match.group(1)
                translated_row["fork length"] = int(fork_length)
            else:
                print(f"⚠️ Could not extract fork length from: '{fork_text}'")
                translated_row["fork length"] = None
        else:
            print(f"⚠️ No fork information available for {translated_row.get('model', 'Unknown')}")
            translated_row["fork length"] = None


        #----sub-category----
        fork_length_str = translated_row.get("fork length")

        if fork_length_str is not None:
            try:
                fork_length = int(fork_length_str)
                if fork_length == 120:
                    translated_row["sub-category"] = "cross-country"
                elif fork_length in [130, 140, 150]:
                    translated_row["sub-category"] = "trail"
                elif fork_length in [160, 170, 180]:
                    translated_row["sub-category"] = "enduro"
                else:
                    print(f"⚠️ Unexpected fork length value: {fork_length}")
                    translated_row["sub-category"] = "unknown"
            except ValueError as e:
                print(f"⚠️ Invalid fork length '{fork_length_str}': {e}")
                translated_row["sub-category"] = "unknown"
        else:
            translated_row["sub-category"] = "unknown"
            
        scraped_data.append(translated_row)

    return scraped_data

driver = uc.Chrome()
products = recycles_bikes(driver)
driver.quit()

# Save to JSON
import os
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
output_file = os.path.join(output_dir, "recycles.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print(f"\n✅ All data saved to {output_file}")

