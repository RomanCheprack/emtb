import time
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

BASE_URL = "https://www.moto-ofan.co.il/"
TARGET_URL = BASE_URL + "353679-אופני-שטח-חשמליים"

scraped_data = []

def safe_to_int(text):
    """Extracts the first number from a string and converts it to int, or returns 'Not listed'."""
    match = re.search(r'\d+', text.replace(",", ""))
    if match:
        return int(match.group())
    else:
        return "צור קשר"


def motofan_bikes(driver):
    driver.get(TARGET_URL)
    time.sleep(5)

    # Parse the page source with BeautifulSoup and find product cards
    print("🔍 Searching for product cards...")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("div", class_="layout_list_item")
    print(f"✅ Found {len(cards)} products.\n")

    for idx, card in enumerate(cards):
        print(f"--- Processing Product {idx+1} ---")

        firm = None
        model = None
        year = None
        original_price = None
        disc_price = None
        img_url = None
        product_url = None

        # Common bike brands that might appear in the title
        common_brands = [
            "MOUSTACHE", "PIVOT"
        ]

        # Remove common Hebrew bike type terms
        terms_to_remove = [
            "אופני שטח חשמליים",
            "אופני הרים חשמליים", 
            "מוסטש",
            "גיים",
            "טרייל",
            "קיט",
            "E- BIKE"
        ]
                
        # Extract product title
        title_text = card.find('h3', class_='title')
        if title_text:
            raw_title_text = title_text.get_text(strip=True)
            print(f"Raw title: {raw_title_text}")
        else:
            print("⚠️ Title text not found")
            raw_title_text = ""
        
        # Extract firm name (look for English brand names)    
        firm = ""
        dirty_model = raw_title_text
        for brand in common_brands:
            if brand in raw_title_text.upper():
                firm = brand.title()  # Capitalize first letter of each word
                # Remove the brand name from the model
                dirty_model = re.sub(rf'\b{brand}\b', '', raw_title_text, flags=re.IGNORECASE).strip()
                print(f"Model after brand removal: {dirty_model}")
                break
                
        # Clean up the model name (remove extra spaces and common terms)
        cleaned_model = re.sub(r'\s+', ' ', dirty_model).strip()
        
        for term in terms_to_remove:
            cleaned_model = cleaned_model.replace(term, "").strip()
        
        model = cleaned_model
        print(f"Final model: {model}")

        # Extract year from the end of the title
        year_match = re.search(r'(202[0-9]|202[0-9])', model)
        year = int(year_match.group(1)) if year_match else None
                
        # Remove year from model name if found
        if year:
            model = model.replace(str(year), "").strip()

        # Extract price
        price_tag = card.find('p', class_='price')
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            # Remove the Hebrew text "מחיר" and any extra whitespace
            clean_price_text = re.sub(r'מחיר\s*', '', price_text).strip()
            original_price = safe_to_int(clean_price_text)
            print(f"Price extracted: {original_price}")
        else:
            print("⚠️ Price element (price) not found")
            original_price = "צור קשר"
        
        # Extract image
        img_tag = card.find('img', class_='img-responsive')
        if img_tag:
            img_url = img_tag.get('src')
            print(f"Image URL: {img_url}")
        else:
            print("  Warning: Image tag not found.")  

        # Extract product link - look for the specific structure in the wrap div
        wrap_div = card.find('div', class_='wrap')
        if wrap_div:
            # Find the first anchor tag that contains the product link (not the brand link)
            product_link_tag = wrap_div.find('a', href=True)
            if product_link_tag:
                raw_href = product_link_tag.get('href', '')
                clean_href = raw_href.strip()  # removes spaces, tabs, and newlines
                product_url = urljoin(BASE_URL, clean_href)
                print(f"Product URL: {product_url}")
            else:
                product_url = None
                print("⚠️ Product link not found in wrap div")
        else:
            # Fallback: try to find any anchor tag in the card
            product_link_tag = card.find('a', href=True)
            if product_link_tag:
                raw_href = product_link_tag.get('href', '')
                clean_href = raw_href.strip()
                product_url = urljoin(BASE_URL, clean_href)
                print(f"Product URL (fallback): {product_url}")
            else:
                product_url = None
                print("⚠️ Product link not found")

        # Create product data dictionary
        product_data = {
            "firm": firm,
            "model": model,
            "year": year,
            "original_price": original_price,
            "disc_price": disc_price,
            "image_URL": img_url,
            "product_URL": product_url
        }

                        # Visit product page and extract specs
        if product_url:
            try:
                driver.get(product_url)
                time.sleep(4)
                prod_soup = BeautifulSoup(driver.page_source, "html.parser")

                #images Gallery
                ul = prod_soup.find('ul', class_='lSPager lSGallery')
                #print(ul)
                # Extract all image srcs from <li> elements inside this <ul>
                gallery_images_urls = [img['src'] for img in ul.find_all('img') if img.get('src')]
                product_data["gallery_images_urls"] = gallery_images_urls

                # Extract specifications from the product page
                spec_list = prod_soup.find_all('li')
                for spec_item in spec_list:
                    bold_tag = spec_item.find('b')
                    if bold_tag:
                        spec_name = bold_tag.get_text(strip=True).lower()
                        span_tag = spec_item.find('span', class_='he_false')
                        if span_tag:
                            spec_value = span_tag.get_text(strip=True)
                            product_data[spec_name] = spec_value
                            print(f"Spec: {spec_name} = {spec_value}")

            except Exception as e:
                print(f"⚠️ Error scraping product page ({product_url}): {e}")

        battery_value = product_data.get("battery", "")
        wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)

        #extract Wh from battery value
        if wh_match:
            wh_value = int(wh_match.group(1))  # Convert to int if needed
            product_data["wh"] = wh_value
        else:
        # If no 'Wh' found, try to find a 3-digit number
            fallback_match = re.search(r"\b(\d{3})\b", battery_value)
            if fallback_match:
                product_data["wh"] = int(fallback_match.group(1))

        #---fork length----
        fork_text = product_data.get("fork", "")
        print(f"DEBUG: fork_text = '{fork_text}'")
        match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
        if match:
            fork_length = match.group(1)
            product_data["fork length"] = int(fork_length)
        else:
            raise ValueError(f"❌ Could not extract fork length from: '{fork_text}'")


        #----sub-category----
        fork_length_str = product_data.get("fork length")

        if fork_length_str:
            try:
                fork_length = int(fork_length_str)
                if fork_length == 120:
                    product_data["sub-category"] = "cross-country"
                elif fork_length in [130, 140, 150]:
                    product_data["sub-category"] = "trail"
                elif fork_length in [160, 170, 180]:
                    product_data["sub-category"] = "enduro"
                else:
                    raise ValueError(f"Unexpected fork length value: {fork_length}")
            except ValueError as e:
                raise ValueError(f"Invalid fork length '{fork_length_str}': {e}")

        scraped_data.append(product_data)

    return scraped_data


driver = uc.Chrome()
products = motofan_bikes(driver)
driver.quit()

# Save to JSON
import os
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
output_file = os.path.join(output_dir, "motofan.json")

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print(f"\n✅ All data saved to {output_file}")
print(f"📊 Total products scraped: {len(products)}")