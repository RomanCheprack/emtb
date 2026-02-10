# -*- coding: utf-8 -*-
import time
import os
import re
import json
import logging
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ----------------- Logging -----------------
# Configure logging to output to stdout instead of stderr
# This prevents the orchestrator from prefixing log messages with "ERROR:"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ----------------- Constants -----------------
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
    "הד-סט / מיסבי היגוי": "headset",
    "תוספות:": "additionals",
    "צמיג קדמי": "front_tire",
    "צמיג אחורי": "rear_tire",
    "חישוקים": "rims",
    "נאבה קדמית": "front_hub",
    "נאבה אחורית": "rear_hub",
    "משקל:": "weight",
    "ידית נעילה": "lock_lever",
    "ציר מרכזי": "bottom_bracket",
    "מגבלת משקל:": "weight_limit",
    "מזלג": "fork",
    "סרט כידון": "handlebar_tape",
    "מעביר קדמי": "front_derailleur",
    "ידית נעילה:": "lock_lever",
    "גלגלים": "wheels",
}

CTC_TARGET_URLS = [
    {"url": "https://ctc.co.il/product-category/bikes/e-bikes/e-mtb/", "category": "electric", "sub_category": "electric_mtb"},
    {"url": "https://ctc.co.il/product-category/bikes/e-bikes/e-city", "category": "electric", "sub_category": "electric_city"},
    {"url": "https://ctc.co.il/product-category/bikes/e-bikes/אופני-כביש-חשמליים/", "category": "electric", "sub_category": "electric_road"},
    {"url": "https://ctc.co.il/product-category/bikes/mountain-bikes/full-suspension/", "category": "mtb", "sub_category": "full_suspension"},
    {"url": "https://ctc.co.il/product-category/bikes/mountain-bikes/hard-tail/", "category": "mtb", "sub_category": "hardtail"},
    {"url": "https://ctc.co.il/product-tag/aero/", "category": "road", "sub_category": "aero"},
    {"url": "https://ctc.co.il/product-tag/lightweight/", "category": "road", "sub_category": "lightweight"},
    {"url": "https://ctc.co.il/product-tag/endurance/", "category": "road", "sub_category": "endurance"},
    {"url": "https://ctc.co.il/product-tag/גראבל/", "category": "gravel", "sub_category": "gravel"},
    {"url": "https://ctc.co.il/product-category/bikes/city-bikes", "category": "city", "sub_category": "city"},
    {"url": "https://ctc.co.il/product-category/bikes/city-bikes/page/2", "category": "city", "sub_category": "city"},
    {"url": "https://ctc.co.il/product-category/bikes/kids-bikes/", "category": "kids", "sub_category": "kids"},
    {"url": "https://ctc.co.il/product-category/bikes/kids-bikes/page/2", "category": "kids", "sub_category": "kids"},
]

BASE_URL = "https://ctc.co.il"
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

scraped_data = []
# Use absolute path for cache file to avoid issues with working directory changes
project_root = Path(__file__).resolve().parents[2]
chatgpt_cache_file = project_root / "data" / "scrapers" / "chatgpt_cache.json"
if chatgpt_cache_file.exists():
    with open(chatgpt_cache_file, "r", encoding="utf-8") as f:
        chatgpt_cache = json.load(f)
else:
    chatgpt_cache = {}

# ----------------- Utilities -----------------
def is_driver_alive(driver):
    """Check if the Chrome driver is still alive and responsive"""
    try:
        driver.current_url
        return True
    except:
        return False

def recreate_driver():
    """Recreate a new Chrome driver instance"""
    try:
        logging.info("🔄 Recreating Chrome driver...")
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')  # Suppress Chrome logging
        driver = uc.Chrome(options=options, version_main=144)
        # Set explicit timeouts for better reliability
        # Use 60s page load timeout to avoid connection timeout issues (Selenium default is 120s)
        driver.set_page_load_timeout(60)  # 60 seconds for page load
        driver.implicitly_wait(10)  # 10 seconds for element finding
        logging.info("✅ Chrome driver recreated successfully!")
        return driver
    except Exception as e:
        logging.error(f"❌ Failed to recreate Chrome driver: {e}")
        return None

def wait_for_element(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    except:
        return None

def scroll_to_bottom(driver, pause=0.5, max_scrolls=20):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def safe_to_int(text):
    try:
        return int(text)
    except (ValueError, TypeError):
        return None

def extract_price(bdi_tag):
    if not bdi_tag:
        return None
    text = bdi_tag.get_text(strip=True).replace("₪", "").replace(",", "")
    return safe_to_int(text)

def get_best_img_url(img_tag):
    for attr in ['data-brsrcset', 'srcset']:
        srcset = img_tag.get(attr)
        if srcset:
            high_res = srcset.split(',')[-1].strip().split(' ')[0]
            if high_res and not high_res.startswith("data:image/"):
                return high_res
    return img_tag.get('src')

def rewrite_description_with_chatgpt(original_text):
    if not original_text or not CHATGPT_API_KEY:
        return original_text
    if original_text in chatgpt_cache:
        return chatgpt_cache[original_text]
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {CHATGPT_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים..."},
                {"role": "user", "content": f"להלן תיאור האופניים:\n\n{original_text}\n\nאנא כתוב גרסה שיווקית חדשה, מקורית, מעניינת, באורך של 100-300 מילים."}
            ],
            "temperature": 0.6,
            "max_tokens": 500
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        rewritten = result['choices'][0]['message']['content'].strip()
        chatgpt_cache[original_text] = rewritten
        with open(chatgpt_cache_file, "w", encoding="utf-8") as f:
            json.dump(chatgpt_cache, f, ensure_ascii=False, indent=4)
        return rewritten
    except Exception as e:
        logging.warning(f"ChatGPT rewriting failed: {e}")
        return original_text

def clean_model_data(raw_model):
    cleaned = re.sub(r"^אופני(?:ים)?(?: הרים)? חשמליים[-]?\s*", "", raw_model).strip()
    year = None
    year_match = re.search(r"(20\d{2}|(\d{2})-(\d{2}))", cleaned)
    if year_match:
        if year_match.group(2) and year_match.group(3):
            year = 2000 + int(year_match.group(3))
        else:
            year = int(year_match.group(1))
    cleaned = re.sub(r"(20\d{2}|\d{2}-\d{2})", "", cleaned).strip()
    words = cleaned.split()
    firm, model = "", ""
    for i, word in enumerate(words):
        if re.search(r'[a-zA-Z]', word):
            firm = word
            model = " ".join(words[i+1:])
            break
    return firm, model, year

# ----------------- Scraper -----------------
def ctc_bikes(driver, output_file):
    fork_to_style = {40: "cross-country", 60: "cross-country", 80: "cross-country", 100: "cross-country", 110: "cross-country",
                     120: "cross-country", 130: "trail", 140: "trail", 150: "trail", 160: "enduro",
                     170: "enduro", 180: "enduro"}
    for i, entry in enumerate(CTC_TARGET_URLS):
        target_url = entry["url"]
        category_text = entry["category"]
        sub_category_text = entry.get("sub_category", None)
        logging.info(f"Scraping URL #{i+1}: {target_url}")
        
        # Check driver health before starting
        if not is_driver_alive(driver):
            logging.warning(f"Driver is not alive before loading {target_url}, recreating...")
            new_driver = recreate_driver()
            if new_driver is None:
                logging.error("Failed to recreate driver, skipping URL")
                continue
            # Clean up old driver
            try:
                driver.quit()
            except:
                pass
            driver = new_driver
        
        try:
            driver.get(target_url)
        except TimeoutException as e:
            logging.warning(f"Page load timeout for URL {target_url}: {e}")
            # Try to stop the page load
            try:
                driver.execute_script("window.stop();")
            except:
                pass
            # Check if driver died during page load
            if not is_driver_alive(driver):
                logging.warning("Driver died during page load timeout, recreating...")
                new_driver = recreate_driver()
                if new_driver is None:
                    logging.error("Failed to recreate driver, skipping URL")
                    continue
                try:
                    driver.quit()
                except:
                    pass
                driver = new_driver
            continue
        except Exception as e:
            logging.warning(f"Error loading URL {target_url}: {e}")
            # Check if driver died during page load
            if not is_driver_alive(driver):
                logging.warning("Driver died during page load, recreating...")
                new_driver = recreate_driver()
                if new_driver is None:
                    logging.error("Failed to recreate driver, skipping URL")
                    continue
                try:
                    driver.quit()
                except:
                    pass
                driver = new_driver
            continue
        
        try:
            scroll_to_bottom(driver, pause=0.5)
        except Exception as e:
            logging.warning(f"Error scrolling page {target_url}: {e}")
            if not is_driver_alive(driver):
                logging.warning("Driver died during scroll, recreating...")
                new_driver = recreate_driver()
                if new_driver is None:
                    logging.error("Failed to recreate driver, skipping URL")
                    continue
                try:
                    driver.quit()
                except:
                    pass
                driver = new_driver
                continue
        
        # Add timeout and retry for getting page source
        max_retries = 3
        soup = None
        for retry in range(max_retries):
            try:
                # Check driver health before accessing page_source
                if not is_driver_alive(driver):
                    logging.warning(f"Driver not alive before getting page source (retry {retry + 1}/{max_retries}), recreating...")
                    new_driver = recreate_driver()
                    if new_driver is None:
                        logging.error("Failed to recreate driver")
                        break
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = new_driver
                    # Reload the page with new driver
                    try:
                        driver.get(target_url)
                        scroll_to_bottom(driver, pause=0.5)
                    except Exception as e2:
                        logging.warning(f"Error reloading page after driver recreation: {e2}")
                        break
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                break
            except Exception as e:
                if retry < max_retries - 1:
                    logging.warning(f"Retry {retry + 1}/{max_retries} getting page source for {target_url}: {e}")
                    # Check if driver is still alive
                    if not is_driver_alive(driver):
                        logging.warning("Driver died, will recreate on next retry")
                    time.sleep(2)
                else:
                    logging.error(f"Failed to get page source after {max_retries} retries: {e}")
                    # Try to recreate driver one last time
                    if not is_driver_alive(driver):
                        logging.warning("Attempting final driver recreation...")
                        new_driver = recreate_driver()
                        if new_driver:
                            try:
                                driver.quit()
                            except:
                                pass
                            driver = new_driver
                    continue
        if soup is None:
            continue
        all_cards = soup.find_all("li", class_="product-warp-item")
        cards = [c for c in all_cards if "product-category" not in c.get("class", [])]
        logging.info(f"Found {len(cards)} product links.")

        for j, card in enumerate(cards):
            model_tag = card.find('a', class_="name")
            if not model_tag: continue
            raw_model_text = model_tag.get_text(strip=True)
            if "ארכיון" in raw_model_text: continue

            # Prices
            original_price, discounted_price = None, None
            price_span = card.find("span", class_="price")
            if price_span:
                # Skip archived products (ארכיון means "archive")
                if "ארכיון" in price_span.get_text():
                    continue
                original_price = extract_price(price_span.find("bdi"))
            if not original_price:
                price_wrap = card.find("div", class_="price-wrap")
                if price_wrap:
                    original_price = extract_price(price_wrap.find("del bdi"))
                    discounted_price = extract_price(price_wrap.find("ins bdi"))
                    if not original_price and not discounted_price:
                        original_price = extract_price(price_wrap.select_one("bdi"))
            if not original_price:
                original_price = extract_price(card.find("bdi"))

            # Images
            main_img_div = card.find('div', class_='main-img')
            main_img_url = get_best_img_url(main_img_div.find('img')) if main_img_div else None
            back_img_div = card.find('div', class_=['back-img', 'back'])
            back_img_url = get_best_img_url(back_img_div.find('img')) if back_img_div else None

            a_tag = card.find("a", class_="product-img")
            product_url = a_tag["href"] if a_tag else None
            firm, model, year = clean_model_data(raw_model_text)

            product_data = {
                "source": {"importer": "CTC", "domain": BASE_URL, "product_url": product_url},
                "firm": firm, "model": model, "year": year,
                "category": category_text, "sub_category": sub_category_text,
                "original_price": original_price, "disc_price": discounted_price,
                "images": {"image_url": main_img_url, "gallery_images_urls": []},
                "specs": {}
            }

            if product_url:
                try:
                    # Check driver health before loading product page
                    if not is_driver_alive(driver):
                        logging.warning(f"Driver not alive before loading product {product_url}, recreating...")
                        new_driver = recreate_driver()
                        if new_driver is None:
                            logging.error("Failed to recreate driver, skipping product page")
                            product_soup = None
                        else:
                            try:
                                driver.quit()
                            except:
                                pass
                            driver = new_driver
                    
                    product_soup = None
                    if is_driver_alive(driver):
                        try:
                            driver.get(product_url)
                        except TimeoutException as e:
                            logging.warning(f"Page load timeout for product URL {product_url}: {e}")
                            # Try to stop the page load
                            try:
                                driver.execute_script("window.stop();")
                            except:
                                pass
                            if not is_driver_alive(driver):
                                logging.warning("Driver died during product page load timeout, recreating...")
                                new_driver = recreate_driver()
                                if new_driver is None:
                                    logging.error("Failed to recreate driver, skipping product page")
                                else:
                                    try:
                                        driver.quit()
                                    except:
                                        pass
                                    driver = new_driver
                        except Exception as e:
                            logging.warning(f"Error loading product URL {product_url}: {e}")
                            if not is_driver_alive(driver):
                                logging.warning("Driver died during product page load, recreating...")
                                new_driver = recreate_driver()
                                if new_driver is None:
                                    logging.error("Failed to recreate driver, skipping product page")
                                else:
                                    try:
                                        driver.quit()
                                    except:
                                        pass
                                    driver = new_driver
                        
                        if is_driver_alive(driver):
                            try:
                                scroll_to_bottom(driver, pause=0.5)
                            except Exception as e:
                                logging.warning(f"Error scrolling product page {product_url}: {e}")
                                if not is_driver_alive(driver):
                                    logging.warning("Driver died during scroll, recreating...")
                                    new_driver = recreate_driver()
                                    if new_driver is None:
                                        logging.error("Failed to recreate driver, skipping product page")
                                    else:
                                        try:
                                            driver.quit()
                                        except:
                                            pass
                                        driver = new_driver
                            
                            # Add timeout and retry for getting page source
                            if is_driver_alive(driver):
                                max_retries = 3
                                for retry in range(max_retries):
                                    try:
                                        # Check driver health before accessing page_source
                                        if not is_driver_alive(driver):
                                            logging.warning(f"Driver not alive before getting product page source (retry {retry + 1}/{max_retries}), recreating...")
                                            new_driver = recreate_driver()
                                            if new_driver is None:
                                                logging.error("Failed to recreate driver")
                                                break
                                            try:
                                                driver.quit()
                                            except:
                                                pass
                                            driver = new_driver
                                            # Reload the page with new driver
                                            try:
                                                driver.get(product_url)
                                                scroll_to_bottom(driver, pause=0.5)
                                            except Exception as e2:
                                                logging.warning(f"Error reloading product page after driver recreation: {e2}")
                                                break
                                        
                                        product_soup = BeautifulSoup(driver.page_source, "html.parser")
                                        break
                                    except Exception as e:
                                        if retry < max_retries - 1:
                                            logging.warning(f"Retry {retry + 1}/{max_retries} getting page source for {product_url}: {e}")
                                            # Check if driver is still alive
                                            if not is_driver_alive(driver):
                                                logging.warning("Driver died, will recreate on next retry")
                                            time.sleep(2)
                                        else:
                                            logging.error(f"Failed to get page source after {max_retries} retries: {e}")
                                            # Try to recreate driver one last time
                                            if not is_driver_alive(driver):
                                                logging.warning("Attempting final driver recreation...")
                                                new_driver = recreate_driver()
                                                if new_driver:
                                                    try:
                                                        driver.quit()
                                                    except:
                                                        pass
                                                    driver = new_driver
                                            product_soup = None
                    
                    if product_soup is None:
                        logging.warning(f"Skipping product page details for {product_url} due to page source error")
                        # Continue to append product_data at the end with basic info only
                    else:
                        desc_el = product_soup.find("div", class_="woocommerce-product-details__short-description")
                        original_description = desc_el.get_text(strip=True) if desc_el else ""
                        rewritten_description = rewrite_description_with_chatgpt(original_description)
                        product_data["rewritten_description"] = rewritten_description

                        # Gallery images
                        gallery_images_urls = []
                        for thumb_div in product_soup.select('.nasa-wrap-item-thumb'):
                            img_tag = thumb_div.find('img')
                            if img_tag:
                                url_candidate = get_best_img_url(img_tag)
                                if url_candidate and not url_candidate.startswith("data:image/"):
                                    gallery_images_urls.append(url_candidate)
                        product_data["images"]["gallery_images_urls"] = list(set(gallery_images_urls))

                        # Specs
                        spec_table = product_soup.find("table", class_="spec-table")
                        skip_keys = ['גלגל שיניים מקסימלי', 'רוחב צמיג מקסימלי', 'אורך בולם מקסימלי']
                        if spec_table:
                            for tr in spec_table.find_all("tr"):
                                th, td = tr.find("th"), tr.find("td")
                                if th and td:
                                    key, val = th.get_text(strip=True), td.get_text(strip=True)
                                    if key in skip_keys: continue
                                    english_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)
                                    product_data["specs"][english_key] = val
                except Exception as e:
                    logging.warning(f"Error scraping product page ({product_url}): {e}")

            # Extract battery Wh
            battery_value = product_data.get("specs", {}).get("battery", "")
            wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
            if wh_match:
                product_data["wh"] = int(wh_match.group(1))
            else:
                fallback_match = re.search(r"\b(\d{3})\b", battery_value)
                if fallback_match:
                    product_data["wh"] = int(fallback_match.group(1))

            # Extract fork length
            fork_text = product_data.get("specs", {}).get("fork", "")
            fork_lengths = [int(x) for x in re.findall(r'(?<!\d)(40|60|80|100|120|130|140|150|160|170|180)(?!\d)', fork_text)]
            fork_lengths = [fl for fl in fork_lengths if fl != 110]  # remove common hub
            fork_length = max(fork_lengths) if fork_lengths else None
            product_data["fork length"] = fork_length
            product_data["style"] = fork_to_style.get(fork_length, "unknown")

            scraped_data.append(product_data)

            # Save progress
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(scraped_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logging.warning(f"Could not save progress: {e}")

    return scraped_data, driver

# ----------------- Setup Output -----------------
if __name__ == '__main__':
    try:
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "data" / "scraped_raw_data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = output_dir / "ctc_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        logging.info(f"Output file ready: {output_file}")
    except Exception as e:
        logging.error(f"Error setting up output directory: {e}")
        exit(1)

    # ----------------- Run Scraper -----------------
    products = []
    driver = None
    try:
        logging.info("Starting Chrome driver...")
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')  # Suppress Chrome logging
        driver = uc.Chrome(options=options, version_main=144)
        # Set explicit timeouts for better reliability
        # Use 60s page load timeout to avoid connection timeout issues (Selenium default is 120s)
        driver.set_page_load_timeout(60)  # 60 seconds for page load
        driver.implicitly_wait(10)  # 10 seconds for element finding
        logging.info("Chrome driver started successfully!")
        products, driver = ctc_bikes(driver, output_file)
    except Exception as e:
        logging.error(f"Error during scraping: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                logging.info("Chrome driver closed")
            except:
                pass

    logging.info(f"Scraping completed! Total products: {len(products)}. Data saved to {output_file}")
