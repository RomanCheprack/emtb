import time
import re
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

BASE_URL = "https://giant-bike.co.il"
TARGET_URL = f"{BASE_URL}/חנות/אופניים/חשמלי-הרים/"

scraped_data = []

def extract_number(price_str):
    return re.sub(r'[^\d,]', '', price_str)

def safe_to_int(text):
    try:
        return int(text.replace(',', '').replace('₪', '').strip())
    except (ValueError, AttributeError):
        return "צור קשר"

def giant_bikes(driver):
    print(f"\n🌐 Scraping: {TARGET_URL}")
    driver.get(TARGET_URL)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("div", class_="product-grid-item")
    print(f"✅ Found {len(cards)} products.\n")


    for i, card in enumerate(cards):
        print(f"--- Processing Product {i+1} ---")

        firm_text = "Giant" # Cleaned up leading space
        model_text = None
        year_text = None # You might want to extract this dynamically if available
        price_text = None
        disc_price_text = None
        img_url = None
        product_url = None
        specifications = {} 

        model_text = card.find('h3', class_='product-title').a.text
        #model_text = model_tag.get_text(strip=True)
        #print(model_text)

        price_tag = card.find("span", class_="price")

        if price_tag:
            price_tag = price_tag.find('span', class_='woocommerce-Price-amount')
            price_text = safe_to_int(price_tag.text if price_tag else None)
            print(price_text)
        else: 
            price_text = "צור קשר"
            print("price not found or not exist")

        disc_price_tag = card.find('ins')
        if disc_price_tag:
            disc_price_tag = disc_price_tag.find('span', class_='woocommerce-Price-amount')
            disc_price_text = safe_to_int(disc_price_tag.text if disc_price_tag else None)
            print(disc_price_text)
        else:
            disc_price_text = ""
            print("discount price not found or not exist")


        product_div = card.find('div', class_='product-element-top')

        # Extract the first <a> (that wraps the <img>)
        a_tag = product_div.find('a')
        product_url = a_tag['href'] if a_tag else None
        #print(product_url)
        # Extract the <img> tag inside that <a>
        img_tag = a_tag.find('img') if a_tag else None
        img_url = img_tag['src'] if img_tag else None
        #print(img_url)
        
        products_data = {
            "firm": firm_text,
            "model": model_text,
            "year": year_text,
            "original_price": price_text,
            "disc_price": disc_price_text,
            "image_url": img_url,
            "product_url": product_url
        }

        if product_url:
            try:
                driver.get(product_url)
                time.sleep(4)
                product_soup = BeautifulSoup(driver.page_source, "html.parser")

                #-----  Gallery images ---

                owl_stage = product_soup.find("div", class_="owl-stage")

                # Extract all img src attributes inside it
                image_urls = [img["src"] for img in owl_stage.find_all("img")]
                print(image_urls)
                products_data["gallery_images_urls"] = image_urls

                tables = product_soup.find_all('table', class_='specifications')

                if tables:
                    for table in tables:
                        rows = table.find_all('tr')
                        #print(rows)
                        for row in rows:
                            key_tag = row.find('th')
                            #print(key_tag)
                            value_tag = row.find('td')
                            #print(value_tag)
                            
                            key = key_tag.get_text(strip=True)
                            #print(key)
                            # Prefer inner .value if exists, else just get the td text
                            value_divs = value_tag.find_all('div', class_='value')
                            if value_divs:
                                # join all inner .value divs, to avoid nesting issues
                                value = " ".join(div.get_text(strip=True) for div in value_divs)
                                #print(value)
                            else:
                                value = value_tag.get_text(strip=True)

                            products_data[key] = value

            except Exception as e:
                print(f"⚠️ Error scraping product page ({product_url}): {e}")   

        for key, value in list(products_data.items()):
            if key.strip().lower() == "battery":
                wh_match = re.search(r"(\d+)\s*Wh", value, re.IGNORECASE)
                if wh_match:
                    battery_wh = int(wh_match.group(1))
                    products_data["wh"] = battery_wh
                    print("Battery capacity:", battery_wh)
                else:
                    # If no 'Wh' found, try to find a 3-digit number
                    fallback_match = re.search(r"\b(\d{3})\b", value)
                    if fallback_match:
                        battery_wh = int(fallback_match.group(1))
                        products_data["wh"] = battery_wh
                        print("Battery fallback capacity:", battery_wh)

        products_data = {key.lower(): value for key, value in products_data.items()}

        #---fork length----
        fork_text = products_data.get("fork", "")
        print(f"DEBUG: fork_text = '{fork_text}'")
        match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
        print(match)
        if match:
            fork_length = match.group(1)
            products_data["fork length"] = int(fork_length)
        else:
            print(f"⚠️ Could not extract fork length from: '{fork_text}'")
            products_data["fork length"] = None  # or "unknown"

        #----sub-category----
        fork_length_str = products_data.get("fork length")

        if fork_length_str:
            try:
                fork_length = int(fork_length_str)
                if fork_length == 120:
                    products_data["sub-category"] = "cross-country"
                elif fork_length in [130, 140, 150]:
                    products_data["sub-category"] = "trail"
                elif fork_length in [160, 170, 180]:
                    products_data["sub-category"] = "enduro"
                else:
                    print(f"Unexpected fork length value: {fork_length}")
            except ValueError as e:
                print(f"Invalid fork length '{fork_length_str}': {e}")

        scraped_data.append(products_data)

    return scraped_data                        

driver = uc.Chrome()
products = giant_bikes(driver)
driver.quit()



# Save to JSON

output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
output_file = os.path.join(output_dir, "giant.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print(f"\n✅ All data saved to {output_file}")
