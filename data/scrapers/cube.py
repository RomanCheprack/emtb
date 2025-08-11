import time
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

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
TARGET_URL = f"{BASE_URL}/product-category/אופניים/חשמליים/?swoof=1&really_curr_tax=25-product_cat"

scraped_data = []

#---price cleanning and covnerting to int---
def clean_and_convert(price_text):
    price_text = price_text.replace('₪', '').replace(',', '').strip()
    if price_text:
        return int(price_text)
    else:
        return "צור קשר"

def cube_bikes(driver):
    print(f"\n🌐 Scraping: {TARGET_URL}")
    driver.get(TARGET_URL)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("li", class_="jet-woo-builder-product")
    print(f"✅ Found {len(cards)} products.\n")

    for i, card in enumerate(cards):
        print(f"--- Processing Product {i+1} ---")

        firm_text = None # Cleaned up leading space
        model_text = None
        year_text = 2024 # You might want to extract this dynamically if available
        original_price = None
        discounted_price = None
        img_url = None
        product_url = None
        #specifications = {} 

        title_tag = card.find('h5', attrs={'class': 'jet-woo-builder-archive-product-title'})

        if title_tag is not None:
            a_tag = title_tag.find('a') if hasattr(title_tag, 'find') else None
            if a_tag is not None and hasattr(a_tag, 'get'):
                product_url = a_tag.get('href')
                full_text = a_tag.get_text(strip=True) if hasattr(a_tag, 'get_text') else ""

                # Split text into firm and model
                
                if "CUBE" in full_text:
                    firm_text = "Cube"
                    model_text = full_text.replace("CUBE", "").strip()
                else:
                    firm_text = "Cube"
                    model_text = full_text

                #print(firm_text)
                #print(model_text)

                # Extract original price
                price_tag = card.select_one('.ywcrbp_regular_price del bdi')
                if price_tag:
                    original_price = clean_and_convert(price_tag.get_text(strip=True))
                else:
                    original_price = "צור קשר"

                # Extract discounted price
                disc_price_tag = card.select_one('.ywcrbp_sale_price bdi')
                if disc_price_tag:
                    discounted_price = clean_and_convert(disc_price_tag.get_text(strip=True))
                else:
                    discounted_price = None

                thumbnail_div = card.find("div", class_="jet-woo-builder-archive-product-thumbnail")
                img_tag = thumbnail_div.find("img")
                img_url = img_tag.get("src") if img_tag else None

                #print("Image URL:", img_url)

                #print(f"product_url: {product_url}")

                products_data = {
                    "firm": firm_text,
                    "model": model_text,
                    "year": year_text,
                    "original_price": original_price,
                    "disc_price": discounted_price,
                    "image_url": img_url,
                    "product_url": product_url
                }

                if product_url:
                    try:
                        driver.get(product_url)
                        time.sleep(4)
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        sections = soup.find_all("section", class_="elementor-inner-section")


                        # Find all image tags inside the slick-track section
                        gallery_images_urls = []

                        gallery_images_urls = [img['src'] for img in soup.select('ol.flex-control-thumbs img')]
                        products_data["gallery_images_urls"] = gallery_images_urls

                        print(gallery_images_urls)

                        for section in sections:
                            key_span = section.find("span", class_="elementor-heading-title")
                            value_div = section.find("div", class_="elementor-widget-text-editor")

                            key = key_span.get_text(strip=True).rstrip(':') if key_span else None
                            value = value_div.get_text(strip=True) if value_div else None                    
                        
                            if key == 'מספר קטלוגי':
                                        continue
                                    
                            # Only skip if BOTH are None
                            if (key is None or key.strip() == "") and (value is None or value.strip() == ""):
                                continue
                            products_data[key.strip() if key else ""] = value.strip() if value else ""

                    except Exception as e:
                        print(f"⚠️ Error scraping product page ({product_url}): {e}")  


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
                print(match)
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
products = cube_bikes(driver)
driver.quit()

# Save to JSON
import os
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
output_file = os.path.join(output_dir, "cube.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print(f"\n✅ All data saved to {output_file}")