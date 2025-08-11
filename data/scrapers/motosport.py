import time
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

# Hebrew to English key mappings
HEBREW_TO_ENGLISH_KEYS = {
    "שלדה": "frame",
    "בלמים": "brakes",
    "בולם קדמי": "fork",
    "בולם אחורי": "rear_shock",
    "בלם קדמי": "front_brake",
    "בלם אחורי": "rear_brake",
    "רוטורים": "rotors",
    "גלגלים": "wheels",
    "גלגל": "wheel",
    "מנוע": "motor",
    "סוללה": "battery",
    "כידון": "handlebar",
    "תצוגה": "display",
    "סטם": "stem",
    "הדסט": "headset",
    "גריפים": "grips",
    "מעביר אחורי": "rear_derailleur",
    "מעביר": "derailleur",
    "ידיות הילוכים": "shifters",
    "הילוכים": "gears",
    "ידיות": "levers",
    "קראנק": "crankset",
    "קסטה": "cassette",
    "שרשרת": "chain",
    "אוכף": "saddle",
    "מוט אוכף": "seatpost",
    "מוט": "post",
    "צמיגים": "tires",
    "צמיג": "tire",
    "מידות": "sizes",
    "מידה": "size"
}

def translate_hebrew_key(hebrew_key):
    """
    Translate a Hebrew key to its English equivalent.
    
    Args:
        hebrew_key (str): The Hebrew key to translate
        
    Returns:
        str: The English translation, or the original key if no translation found
    """
    return HEBREW_TO_ENGLISH_KEYS.get(hebrew_key, hebrew_key)

BASE_URL = "https://motosport-bicycle.co.il"

scraped_data = []

# --- KTM Scraper ---
KTM_TARGET_URLS = [
    {"url": f"{BASE_URL}/c/אופני-הרים-חשמלים-קלים", "firm": "Ktm"},
    {"url": f"{BASE_URL}/c/אופני-הרים-חשמליים?pageNum=1", "firm": "Ktm"},
    {"url": f"{BASE_URL}/c/אופני-הרים-חשמליים?pageNum=2", "firm": "Ktm"}

]

def scrape_ktm(driver):
    ktm_data = []
    for entry in KTM_TARGET_URLS:
        target_url = entry["url"]
        firm_text = entry["firm"]
        print(f"\n🌐 Scraping: {target_url}")
        driver.get(target_url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("div", class_="product-col col-xs-6 col-sm-6 col-md-4 col-lg-3")
        print(f"✅ Found {len(cards)} products.\n")
        for i, product_card in enumerate(cards):
            print(f"--- Processing Product {i+1} ---")
            model_text = None
            year_text = None
            price_text = None
            img_url = None
            product_url = None
            # Model
            model_tag = product_card.find('a', class_='cc-product-link-title')
            if model_tag:
                span_in_model_tag = model_tag.find('span')
                if span_in_model_tag:
                    model_text = span_in_model_tag.get_text(strip=True)
                    # Extract year
                    valid_years = set(str(y) for y in range(2022, 2028))
                    matches = re.findall(r'\b\d{4}\b', model_text)
                    year_text = next((year for year in matches if year in valid_years), None)
                    if year_text:
                        model_text = re.sub(r'\b' + re.escape(year_text) + r'\b', '', model_text).strip()
            # Price
            price_span = product_card.find('span', class_='cc-price')
            if price_span:
                price_text = price_span.get_text(strip=True)
                # Try to extract numeric price
                price_match = re.search(r'[\d,]+', price_text.replace('₪', '').replace(',', ''))
                if price_match:
                    try:
                        price_int = int(price_match.group().replace(',', ''))
                        price_text = price_int
                    except ValueError:
                        pass  # Keep original price_text if conversion fails
            else:
                price_text = "צור קשר"
            # Image
            img_tag = product_card.find('img', class_='image-rotator active')
            if img_tag:
                img_url = img_tag.get('src') or img_tag.get('data-original')
            # Product URL
            product_link_tag = product_card.find('a', class_='cc-product-link-title')
            if product_link_tag:
                relative_href = product_link_tag.get('href')
                product_url = urljoin(BASE_URL, relative_href)
                
            product_data = {
                "firm": firm_text,
                "model": model_text,
                "year": year_text,
                "original_price": price_text,
                "image_URL": img_url,
                "product_URL": product_url
            }
            # Scrape product page for specifications
            if product_url:
                try:
                    driver.get(product_url)
                    time.sleep(4)
                    product_soup = BeautifulSoup(driver.page_source, "html.parser")
                    spec_list_table = product_soup.find("table", class_="table")
                    if spec_list_table:
                        tbody = spec_list_table.find('tbody')
                        if tbody:
                            rows = tbody.find_all('tr')
                            key_translation = HEBREW_TO_ENGLISH_KEYS
                            for row in rows:
                                cells = row.find_all('td')
                                if len(cells) == 4:
                                    key1 = key_translation.get(cells[0].get_text(strip=True), cells[0].get_text(strip=True))
                                    val1 = cells[1].get_text(strip=True)
                                    key2 = key_translation.get(cells[2].get_text(strip=True), cells[2].get_text(strip=True))
                                    val2 = cells[3].get_text(strip=True)
                                    product_data[key1] = val1
                                    product_data[key2] = val2
                                elif len(cells) == 2:
                                    key = key_translation.get(cells[0].get_text(strip=True), cells[0].get_text(strip=True))
                                    val = cells[1].get_text(strip=True)
                                    product_data[key] = val
                except Exception as e:
                    print(f"⚠️ Error scraping product page ({product_url}): {e}")
            
            # Extract battery capacity (Wh)
            battery_value = product_data.get("battery", "")
            wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
            if wh_match:
                wh_value = int(wh_match.group(1))
                product_data["wh"] = wh_value
            else:
                # If no 'Wh' found, try to find a 3-digit number
                fallback_match = re.search(r"\b(\d{3})\b", battery_value)
                if fallback_match:
                    product_data["wh"] = int(fallback_match.group(1))
            
            # Extract fork length
            fork_text = product_data.get("fork", "")
            print(f"DEBUG: fork_text = '{fork_text}'")
            match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
            if match:
                fork_length = int(match.group(1))
                product_data["fork_length"] = fork_length
                
                # Determine sub-category based on fork length
                if fork_length == 120:
                    product_data["sub_category"] = "cross-country"
                elif fork_length in [130, 140, 150]:
                    product_data["sub_category"] = "trail"
                elif fork_length in [160, 170, 180]:
                    product_data["sub_category"] = "enduro"
                else:
                    product_data["sub_category"] = "unknown"
            else:
                print(f"⚠️ Could not extract fork length from: '{fork_text}'")
                product_data["fork_length"] = None
                product_data["sub_category"] = "unknown"
            
            ktm_data.append(product_data)
            print(product_data)
    return ktm_data

# --- BH Scraper ---
def scrape_bh(driver):
    bh_data = []
    target_url = f"{BASE_URL}/c/אופני-BH"
    print(f"\n🌐 Scraping: {target_url}")
    driver.get(target_url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("div", class_="product-col col-xs-6 col-sm-6 col-md-4 col-lg-3")
    print(f"✅ Found {len(cards)} products.\n")
    for i, product_card in enumerate(cards):
        print(f"--- Processing Product {i+1} ---")
        firm_text = "BH"
        model_text = None
        year_text = "2025"
        price_text = None
        img_url = None
        product_url = None
        # Model
        model_tag = product_card.find('a', class_='cc-product-link-title')
        if model_tag:
            span_in_model_tag = model_tag.find('span')
            if span_in_model_tag:
                model_text = span_in_model_tag.get_text(strip=True)
                # Remove "אופני" and "BH" from model name
                if model_text:
                    model_text = model_text.replace("אופני", "").replace("BH", "").strip()
        # Price
        price_span = product_card.find('span', class_='cc-price')
        if price_span:
            price_text = price_span.get_text(strip=True)
        # Image
        img_tag = product_card.find('img', class_='image-rotator active')
        if img_tag:
            img_url = img_tag.get('src') or img_tag.get('data-original')
        # Product URL
        product_link_tag = product_card.find('a', class_='cc-product-link-title')
        if product_link_tag:
            relative_href = product_link_tag.get('href')
            if relative_href:
                product_url = urljoin(BASE_URL, relative_href)
        
        # Try to convert price to integer
        if price_text and price_text != "צור קשר":
            price_match = re.search(r'[\d,]+', str(price_text).replace('₪', '').replace(',', ''))
            if price_match:
                try:
                    price_int = int(price_match.group().replace(',', ''))
                    price_text = price_int
                except ValueError:
                    pass  # Keep original price_text if conversion fails
        
        product_data = {
            "firm": firm_text,
            "model": model_text,
            "year": year_text,
            "original_price": price_text,
            "image_URL": img_url,
            "product_URL": product_url
        }
        # Scrape product page for specifications
        if product_url:
            try:
                driver.get(product_url)
                time.sleep(4)
                product_soup = BeautifulSoup(driver.page_source, "html.parser")
                spec_list_table = product_soup.find("table", class_="table")
                if spec_list_table:
                    tbody = spec_list_table.find('tbody')
                    if tbody:
                        rows = tbody.find_all('tr')
                        for table_row in rows:
                            cells = table_row.find_all('td')
                            if len(cells) >= 4:
                                key1 = HEBREW_TO_ENGLISH_KEYS.get(cells[0].get_text(strip=True), cells[0].get_text(strip=True))
                                value1 = cells[1].get_text(strip=True)
                                key2 = HEBREW_TO_ENGLISH_KEYS.get(cells[2].get_text(strip=True), cells[2].get_text(strip=True))
                                value2 = cells[3].get_text(strip=True)
                                if key1:
                                    product_data[key1] = value1
                                if key2:
                                    product_data[key2] = value2
                            elif len(cells) == 2:
                                key1 = HEBREW_TO_ENGLISH_KEYS.get(cells[0].get_text(strip=True), cells[0].get_text(strip=True))
                                value1 = cells[1].get_text(strip=True)
                                if key1:
                                    product_data[key1] = value1
            except Exception as e:
                print(f"⚠️ Error scraping product page ({product_url}): {e}")
        
        # Extract battery capacity (Wh)
        battery_value = product_data.get("battery", "")
        wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
        if wh_match:
            wh_value = int(wh_match.group(1))
            product_data["wh"] = wh_value
        else:
            # If no 'Wh' found, try to find a 3-digit number
            fallback_match = re.search(r"\b(\d{3})\b", battery_value)
            if fallback_match:
                product_data["wh"] = int(fallback_match.group(1))
        
        # Extract fork length
        fork_text = product_data.get("fork", "")
        print(f"DEBUG: fork_text = '{fork_text}'")
        match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
        if match:
            fork_length = int(match.group(1))
            product_data["fork_length"] = fork_length
            
            # Determine sub-category based on fork length
            if fork_length == 120:
                product_data["sub_category"] = "cross-country"
            elif fork_length in [130, 140, 150]:
                product_data["sub_category"] = "trail"
            elif fork_length in [160, 170, 180]:
                product_data["sub_category"] = "enduro"
            else:
                product_data["sub_category"] = "unknown"
        else:
            print(f"⚠️ Could not extract fork length from: '{fork_text}'")
            product_data["fork_length"] = None
            product_data["sub_category"] = "unknown"
        
        bh_data.append(product_data)
        print(product_data)
    return bh_data

# --- Whistle Scraper ---
def scrape_whistle(driver):
    whistle_data = []
    target_url = f"{BASE_URL}/c/אופני-Whistle"
    print(f"\n🌐 Scraping: {target_url}")
    driver.get(target_url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("div", class_="product-col col-xs-6 col-sm-6 col-md-4 col-lg-3")
    print(f"✅ Found {len(cards)} products.\n")
    for i, product_card in enumerate(cards):
        print(f"--- Processing Product {i+1} ---")
        firm_text = "Whistle"
        model_text = None
        year_text = "2025"
        price_text = None
        img_url = None
        product_url = None
        specifications = {}
        # Model
        model_tag = product_card.find('a', class_='cc-product-link-title')
        if model_tag:
            span_in_model_tag = model_tag.find('span')
            if span_in_model_tag:
                model_text = span_in_model_tag.get_text(strip=True)
        # Price
        price_span = product_card.find('span', class_='cc-price')
        if price_span:
            price_text = price_span.get_text(strip=True)
        # Image
        img_tag = product_card.find('img', class_='image-rotator active')
        if img_tag:
            img_url = img_tag.get('src') or img_tag.get('data-original')
        # Product URL
        product_link_tag = product_card.find('a', class_='cc-product-link-title')
        if product_link_tag:
            relative_href = product_link_tag.get('href')
            if relative_href:
                product_url = urljoin(BASE_URL, relative_href)

        # Try to convert price to integer
        if price_text and price_text != "צור קשר":
            price_match = re.search(r'[\d,]+', str(price_text).replace('₪', '').replace(',', ''))
            if price_match:
                try:
                    price_int = int(price_match.group().replace(',', ''))
                    price_text = price_int
                except ValueError:
                    pass  # Keep original price_text if conversion fails

        product_data = {
            "firm": firm_text,
            "model": model_text,
            "year": year_text,
            "original_price": price_text,

            "image_URL": img_url,
            "product_URL": product_url,
        }
        # Scrape product page for specifications
        if product_url:
            try:
                driver.get(product_url)
                time.sleep(4)
                product_soup = BeautifulSoup(driver.page_source, "html.parser")
                spec_list_table = product_soup.find("table", class_="table")
                if spec_list_table:
                    tbody = spec_list_table.find('tbody')
                    if tbody:
                        rows = tbody.find_all('tr')
                        for table_row in rows:
                            cells = table_row.find_all('td')
                            if len(cells) >= 4:
                                key1 = HEBREW_TO_ENGLISH_KEYS.get(cells[0].get_text(strip=True), cells[0].get_text(strip=True))
                                value1 = cells[1].get_text(strip=True)
                                key2 = HEBREW_TO_ENGLISH_KEYS.get(cells[2].get_text(strip=True), cells[2].get_text(strip=True))
                                value2 = cells[3].get_text(strip=True)
                                if key1:
                                    product_data[key1] = value1
                                if key2:
                                    product_data[key2] = value2
                            elif len(cells) == 2:
                                key1 = HEBREW_TO_ENGLISH_KEYS.get(cells[0].get_text(strip=True), cells[0].get_text(strip=True))
                                value1 = cells[1].get_text(strip=True)
                                if key1:
                                    product_data[key1] = value1
            except Exception as e:
                print(f"⚠️ Error scraping product page ({product_url}): {e}")
        
        # Extract battery capacity (Wh)
        battery_value = product_data.get("battery", "")
        wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
        if wh_match:
            wh_value = int(wh_match.group(1))
            product_data["wh"] = wh_value
        else:
            # If no 'Wh' found, try to find a 3-digit number
            fallback_match = re.search(r"\b(\d{3})\b", battery_value)
            if fallback_match:
                product_data["wh"] = int(fallback_match.group(1))
        
        # Extract fork length
        fork_text = product_data.get("fork", "")
        print(f"DEBUG: fork_text = '{fork_text}'")
        match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
        if match:
            fork_length = int(match.group(1))
            product_data["fork_length"] = fork_length
            
            # Determine sub-category based on fork length
            if fork_length == 120:
                product_data["sub_category"] = "cross-country"
            elif fork_length in [130, 140, 150]:
                product_data["sub_category"] = "trail"
            elif fork_length in [160, 170, 180]:
                product_data["sub_category"] = "enduro"
            else:
                product_data["sub_category"] = "unknown"
        else:
            print(f"⚠️ Could not extract fork length from: '{fork_text}'")
            product_data["fork_length"] = None
            product_data["sub_category"] = "unknown"
        
        whistle_data.append(product_data)
        print(product_data)

    return whistle_data

# --- Main ---
if __name__ == "__main__":
    driver = uc.Chrome()
    scraped_data.extend(scrape_ktm(driver))
    scraped_data.extend(scrape_bh(driver))
    scraped_data.extend(scrape_whistle(driver))
    driver.quit()
    import os
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
    output_file = os.path.join(output_dir, "motosport.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ All data saved to {output_file}") 