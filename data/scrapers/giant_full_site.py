# -*- coding: utf-8 -*-
import time
import re
import json
import os
import logging
import sys
import threading
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -----------------------
# Config & constants
# -----------------------
# Configure logging to output to stdout instead of stderr
# This prevents the orchestrator from prefixing log messages with "ERROR:"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("giant-scraper")

BASE_URL = "https://giant-bike.co.il"
CHATGPT_API_KEY = os.getenv("SCRAPER_OPENAI_API_KEY", "")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "scraped_raw_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "giant_data.json"

SAVE_BATCH = 5
PAGE_LOAD_TIMEOUT = 18
PAGE_LOAD_RETRIES = 2
ELEMENT_WAIT_TIMEOUT = 10
CHATGPT_TIMEOUT = 10
CHATGPT_RETRIES = 2

GIANT_TARGET_URLS = [
    {"url": f"{BASE_URL}/חנות/אופניים/חשמלי-הרים/", "category": "electric", "sub_category": "electric_mtb"},
    {"url": f"{BASE_URL}/חנות/אופניים/אופני-כביש/?filter_category-shop=נגד-השעון", "category": "road", "sub_category": "time_trial"},
    {"url": f"{BASE_URL}/חנות/אופניים/אופני-כביש/?filter_category-shop=כביש-דיסק", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/חנות/אופניים/אופני-שטח/?filter_category-shop=שיכוך-מלא", "category": "mtb", "sub_category": "full_suspension"},
    {"url": f"{BASE_URL}/חנות/אופניים/אופני-שטח/?filter_category-shop=זנב-קשיח", "category": "mtb", "sub_category": "hardtail"},
    {"url": f"{BASE_URL}/חנות/אופניים/אופני-עיר/", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/חנות/אופניים/גראבל/", "category": "gravel", "sub_category": "gravel"},
    {"url": f"{BASE_URL}/חנות/אופניים/אופני-ילדים/", "category": "kids", "sub_category": "kids"},
]

HEBREW_TO_ENGLISH_KEYS = {
    "שלדה": "frame", "מידה": "size", "בולם קדמי": "fork", "בולם אחורי": "rear_shock",
    "ברקסים": "brakes", "מעביר אחורי": "rear_derailleur", "ידית הילוכים": "shifters",
    "קסטה": "cassette", "קרנק": "crankset", "שרשרת": "chain", "סט גלגלים": "wheelset",
    "צמיגים": "tires", "סטם": "stem", "כידון": "handlebar", "מוט כיסא": "seatpost",
    "חבק אוכף": "seat_clamp", "כיסא": "saddle", "משקל": "weight", "צבע": "color",
    "מספר קטלוגי": "sku", "סוג מנוע": "motor", "סוללה": "battery", "מסך": "display",
    "שלט מצבי מנוע": "control_system"
}

FORK_STYLE_MAP = {
    "cross-country": [40, 50, 60, 70, 80, 90, 100, 110, 120],
    "trail": [130, 140, 150],
    "enduro": [160, 170, 180]
}

# -----------------------
# Utility
# -----------------------
def save_json_file(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed saving JSON: {e}")

def safe_to_int(text):
    try:
        if text is None:
            return "צור קשר"
        t = str(text).replace(",", "").replace("₪", "").strip()
        return int(t) if t else "צור קשר"
    except:
        return "צור קשר"

# -----------------------
# ChatGPT rewrite
# -----------------------
def rewrite_description_with_chatgpt(original_text):
    if not original_text or not CHATGPT_API_KEY:
        return original_text or ""
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים בחנויות אינטרנטיות."},
            {"role": "user", "content": f"כתוב גרסה שיווקית:\n{original_text}"}
        ],
        "temperature": 0.6,
        "max_tokens": 500
    }
    for attempt in range(1, CHATGPT_RETRIES + 1):
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {CHATGPT_API_KEY}"},
                json=payload,
                timeout=CHATGPT_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"ChatGPT attempt {attempt} failed: {e}")
            time.sleep(attempt)
    return original_text

# -----------------------
# Selenium helpers
# -----------------------
def wait_for_element(driver, by, selector, timeout=ELEMENT_WAIT_TIMEOUT):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
    except:
        return None

def is_driver_alive(driver):
    try:
        _ = driver.current_url
        return True
    except:
        return False

def recreate_driver(options=None):
    opts = options or uc.ChromeOptions()
    return uc.Chrome(options=opts)

def safe_get(driver, url, timeout=PAGE_LOAD_TIMEOUT, retries=PAGE_LOAD_RETRIES):
    for attempt in range(1, retries + 1):
        finished = {"ok": False}
        def _load():
            try:
                driver.get(url)
                finished["ok"] = True
            except: pass
        thread = threading.Thread(target=_load)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            try: driver.execute_script("window.stop();")
            except: pass
        if finished["ok"]:
            return True
        time.sleep(1)
    return False

# -----------------------
# Robust fork extraction
# -----------------------
def extract_fork(specs):
    fork_keys = [k for k in specs if "fork" in k.lower() or "בולם" in k]
    fork_text = specs[fork_keys[0]] if fork_keys else ""
    if not fork_text:
        return None, None
    fork_len = None
    fork_text_clean = fork_text.lower().replace('"', '').replace("מ\"מ", "mm")
    # First: look for number + mm
    m = re.findall(r'(\d{2,3})\s*mm', fork_text_clean)
    if m:
        lengths = [int(x) for x in m if int(x) in sum(FORK_STYLE_MAP.values(), [])]
        if lengths:
            fork_len = max(lengths)
    # Fallback: any reasonable 2-3 digit number
    if not fork_len:
        m2 = re.findall(r'\b(\d{2,3})\b', fork_text_clean)
        if m2:
            lengths = [int(x) for x in m2 if int(x) in sum(FORK_STYLE_MAP.values(), [])]
            if lengths:
                fork_len = max(lengths)
    style = next((s for s, v in FORK_STYLE_MAP.items() if fork_len in v), None) if fork_len else None
    return fork_len, style

# -----------------------
# Main scraping
# -----------------------
def giant_bikes(driver):
    scraped = []
    product_counter = 0
    save_json_file(OUTPUT_FILE, [])

    for entry in GIANT_TARGET_URLS:
        target_url = entry["url"]
        cat = entry["category"]
        sub = entry["sub_category"]

        logger.info(f"Scraping {target_url}")
        if not safe_get(driver, target_url):
            logger.error(f"Could not load {target_url}")
            continue

        wait_for_element(driver, By.CSS_SELECTOR, ".product-grid-item", timeout=8)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("div", class_="product-grid-item")

        for card in cards:
            product_counter += 1
            title_tag = card.find("h3", class_="product-title")
            model = title_tag.a.get_text(strip=True) if title_tag and title_tag.a else None

            price_span = card.find("span", class_="price")
            price = safe_to_int(price_span.find("span", class_="woocommerce-Price-amount").get_text()) if price_span else "צור קשר"
            disc_tag = card.find("ins")
            disc_price = safe_to_int(disc_tag.find("span", class_="woocommerce-Price-amount").get_text()) if disc_tag else None

            div_top = card.find("div", class_="product-element-top")
            a_tag = div_top.find("a") if div_top else None
            product_url = urljoin(BASE_URL, a_tag["href"]) if a_tag else None
            img_tag = a_tag.find("img") if a_tag else None
            img_url = img_tag["src"] if img_tag else None

            product = {
                "source": {"importer": "Giant", "domain": BASE_URL, "product_url": product_url},
                "firm": "Giant",
                "model": model,
                "year": None,
                "category": cat,
                "sub_category": sub,
                "original_price": price,
                "disc_price": disc_price,
                "images": {"image_url": img_url, "gallery_images_urls": []},
                "specs": {},
                "fork length": None,
                "style": None,
            }

            if product_url:
                if not is_driver_alive(driver):
                    driver.quit()
                    driver = recreate_driver()

                if safe_get(driver, product_url):
                    wait_for_element(driver, By.CSS_SELECTOR, ".woocommerce-product-details__short-description", timeout=6)
                    psoup = BeautifulSoup(driver.page_source, "html.parser")

                    # Description
                    desc_el = psoup.find("div", class_="woocommerce-product-details__short-description")
                    original_desc = desc_el.get_text(strip=True) if desc_el else ""
                    product["rewritten_description"] = rewrite_description_with_chatgpt(original_desc)

                    # Gallery
                    gallery = []
                    stage = psoup.find("div", class_="owl-stage") or psoup.find("div", class_="woocommerce-product-gallery__wrapper")
                    if stage:
                        for img in stage.find_all("img"):
                            src = img.get("data-src") or img.get("src")
                            if src and not src.startswith("data:"):
                                gallery.append(src)
                    product["images"]["gallery_images_urls"] = list(dict.fromkeys(gallery))

                    # Specs
                    specs = {}
                    for table in psoup.find_all("table", class_="specifications"):
                        for row in table.find_all("tr"):
                            th = row.find("th"); td = row.find("td")
                            if not th or not td: continue
                            key = th.get_text(strip=True).rstrip(":")
                            val = " ".join(d.get_text(strip=True) for d in td.find_all("div", class_="value")) or td.get_text(strip=True)
                            specs[HEBREW_TO_ENGLISH_KEYS.get(key,key)] = val
                    for sec in psoup.select("section.elementor-inner-section"):
                        h = sec.select_one("span.elementor-heading-title")
                        c = sec.select_one("div.elementor-widget-text-editor")
                        if h and c:
                            k = HEBREW_TO_ENGLISH_KEYS.get(h.get_text(strip=True).rstrip(":"), h.get_text(strip=True).rstrip(":"))
                            if k not in specs: specs[k] = c.get_text(strip=True)
                    product["specs"] = specs

                    # Battery Wh
                    batt = specs.get("battery","")
                    m = re.search(r"(\d{2,4})\s*Wh", batt)
                    if m: product["wh"] = int(m.group(1))
                    else:
                        m = re.search(r"\b(\d{3})\b", batt)
                        if m: product["wh"] = int(m.group(1))

                    # Fork length & style
                    fork_len, style = extract_fork(specs)
                    product["fork length"] = fork_len
                    product["style"] = style

            # Fallback if fork not found
            if product.get("fork length") is None:
                fork_len, style = extract_fork(product.get("specs", {}))
                product["fork length"] = fork_len
                product["style"] = style

            # normalize lowercase
            product = {k.lower(): v for k,v in product.items()}
            if isinstance(product.get("specs"), dict):
                product["specs"] = {k.lower():v for k,v in product["specs"].items()}

            scraped.append(product)

            if len(scraped) % SAVE_BATCH == 0:
                save_json_file(OUTPUT_FILE, scraped)
                logger.info("Auto-saved batch.")

    save_json_file(OUTPUT_FILE, scraped)
    logger.info(f"Finished. Total {len(scraped)} items saved.")
    return scraped

# -----------------------
# Runner
# -----------------------
def main():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = uc.Chrome(options=options)
    try:
        giant_bikes(driver)
    finally:
        driver.quit()

if __name__=="__main__":
    main()
