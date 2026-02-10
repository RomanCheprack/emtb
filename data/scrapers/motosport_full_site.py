import os
import re
import json
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import time

BASE_URL = "https://motosport-bicycle.co.il"

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
    "מידה": "size",
    "FRAME": "frame",
    "FORK": "fork",
    "SHOCK": "rear_shock",
    "R. DERAILL.": "rear_derailleur",
    "SHIFTLEV.": "shifters",
    "CRANKSET": "crankset",
    "SPROCKET": "cassette",
    "CHAIN": "chain",
    "BRAKE": "brakes",
    "ROTOR": "rotors",
    "WHEEL F": "front_wheel",
    "WHEEL R": "rear_wheel",
    "TIRE F": "front_tire",
    "TIRE R": "rear_tire",
    "GRIP": "grips",
    "BAR": "handlebar",
    "STEM": "stem",
    "HEADSET": "headset",
    "SADDLE": "saddle",
    "SEATPOST": "seatpost",
    "WEIGHT": "weight",
    "PERMISSIBLE TOTAL WEIGHT": "max_weight"
}

def translate_key(key):
    return HEBREW_TO_ENGLISH_KEYS.get(key, key)

def extract_specifications(soup):
    specs = {}
    # Try new table structure first
    table_container = soup.find("div", class_="table-responsive table-dark")
    if table_container:
        for table in table_container.find_all("table"):
            tbody = table.find('tbody')
            if not tbody:
                continue
            for row in tbody.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    specs[translate_key(th.get_text(strip=True))] = td.get_text(strip=True)
        return specs
    # Fallback to old table structure
    table = soup.find("table", class_="table")
    if table:
        tbody = table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) == 4:
                    specs[translate_key(cells[0].get_text(strip=True))] = cells[1].get_text(strip=True)
                    specs[translate_key(cells[2].get_text(strip=True))] = cells[3].get_text(strip=True)
                elif len(cells) == 2:
                    specs[translate_key(cells[0].get_text(strip=True))] = cells[1].get_text(strip=True)
    return specs

def save_json(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    if len(data) > 0:
        print(f"💾 Saved {len(data)} products to {file_path}")

def parse_price(price_text):
    if not price_text or price_text == "צור קשר":
        return price_text
    match = re.search(r'[\d,]+', price_text.replace('₪','').replace(',',''))
    return int(match.group().replace(',','')) if match else price_text

def extract_fork_and_style(fork_text):
    fork_text = fork_text.lower() if fork_text else ""
    match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)', fork_text)
    fork_length = int(match.group(1)) if match else None
    style = "unknown"
    if fork_length:
        if fork_length == 120:
            style = "cross-country"
        elif fork_length in [130,140,150]:
            style = "trail"
        elif fork_length in [160,170,180]:
            style = "enduro"
    return fork_length, style

def extract_battery_wh(battery_text):
    if not battery_text:
        return None
    match = re.search(r'(\d+)\s*Wh', battery_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    fallback = re.search(r'\b(\d{3})\b', battery_text)
    return int(fallback.group(1)) if fallback else None

def scrape_brand(driver, brand_name, target_urls, output_file):
    print(f"\n🌐 Scraping {brand_name}...")
    brand_data = []
    for entry in target_urls:
        print(f"  📍 Processing URL: {entry['url']}")
        driver.get(entry["url"])
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("div", class_="product-col col-xs-6 col-sm-6 col-md-4 col-lg-3")
        print(f"  ✅ Found {len(cards)} products")
        for idx, card in enumerate(cards, 1):
            print(f"  Processing Product {idx}/{len(cards)}")
            # Basic product info
            model_tag = card.find('a', class_='cc-product-link-title')
            model = model_tag.get_text(strip=True) if model_tag else None
            price_span = card.find('span', class_='cc-price')
            price = parse_price(price_span.get_text(strip=True) if price_span else None)
            img_tag = card.find('img', class_='image-rotator active')
            img_url = img_tag.get('src') or img_tag.get('data-original') if img_tag else None
            product_url = urljoin(BASE_URL, model_tag.get('href')) if model_tag else None

            product_data = {
                "source": {"importer":"Motosport","domain":BASE_URL,"product_url":product_url},
                "firm": brand_name,
                "model": model,
                "year": None,
                "category": entry.get("category","unknown"),
                "sub_category": entry.get("sub_category","unknown"),
                "original_price": price,
                "disc_price": None,
                "images":{"image_url":img_url,"gallery_images_urls":[]},
                "specs":{}
            }

            if product_url:
                try:
                    driver.get(product_url)
                    time.sleep(2)
                    product_soup = BeautifulSoup(driver.page_source, "html.parser")
                    # Specs
                    product_data["specs"] = extract_specifications(product_soup)
                    # Gallery
                    gallery = product_soup.find("div", class_="product-gallery") or product_soup.find("div", class_="gallery")
                    if gallery:
                        product_data["images"]["gallery_images_urls"] = [img.get('src') or img.get('data-original') 
                                                                         for img in gallery.find_all("img") 
                                                                         if img.get('src') and not img.get('src').startswith("data:image/")]
                    # Fork and style
                    fork_text = product_data["specs"].get("fork","")
                    product_data["fork length"], product_data["style"] = extract_fork_and_style(fork_text)
                    # Battery
                    battery_text = product_data["specs"].get("battery","")
                    product_data["wh"] = extract_battery_wh(battery_text)
                except Exception as e:
                    print(f"  ⚠️ Error scraping product page ({product_url}): {e}")
            
            brand_data.append(product_data)
    
    print(f"  ✅ Completed {brand_name}: {len(brand_data)} products")
    # Don't save here - will save all accumulated data at the end
    return brand_data

# --- Setup output file ---
if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "data" / "scraped_raw_data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = output_dir / "motosport_data.json"
    print(f"📁 Output file: {output_file}")

    # Create empty JSON file to start with
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)
    print("📄 Created empty JSON file - ready for data!")

    # --- Run scraper ---
    driver = None
    scraped_products = []
    try:
        print("🚀 Starting Chrome driver...")
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--headless=new")
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        driver = uc.Chrome(options=options, version_main=144)
        print("✅ Chrome driver started successfully!")

        KTM_URLS = [
            {"url": f"{BASE_URL}/c/אופני-הרים-חשמלים-קלים", "category":"electric","sub_category":"electric_mtb"},
            {"url": f"{BASE_URL}/c/אופני-הרים", "category":"mtb","sub_category":"full_suspension"}
        ]
        BH_URLS = [{"url": f"{BASE_URL}/c/אופני-BH","category":"electric","sub_category":"electric_mtb"}]
        WHISTLE_URLS = [{"url": f"{BASE_URL}/c/אופני-Whistle","category":"electric","sub_category":"electric_mtb"}]

        scraped_products.extend(scrape_brand(driver, "KTM", KTM_URLS, output_file))
        scraped_products.extend(scrape_brand(driver, "BH", BH_URLS, output_file))
        scraped_products.extend(scrape_brand(driver, "Whistle", WHISTLE_URLS, output_file))

    except Exception as e:
        print(f"❌ Error initializing Chrome driver: {e}")
        print("💡 Make sure Chrome browser is installed and accessible")
        scraped_products = []
    finally:
        if driver:
            try:
                driver.quit()
                print("🔒 Chrome driver closed")
            except:
                pass

    # Final summary
    print(f"\n✅ Scraping completed!")
    print(f"📊 Total products scraped: {len(scraped_products)}")

    # Save all accumulated products to the output file
    try:
        save_json(scraped_products, output_file)
        print(f"💾 Final data saved to: {output_file}")
    except Exception as e:
        print(f"⚠️ Warning: Could not save final JSON file: {e}")
