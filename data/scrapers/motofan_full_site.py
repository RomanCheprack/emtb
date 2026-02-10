# -*- coding: utf-8 -*-
import time
import os
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
import requests

BASE_URL = "https://www.moto-ofan.co.il"

# ChatGPT API Configuration
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

scraped_data = []


MOTOFAN_TARGET_URLS = [
    {"url": f"{BASE_URL}/353679-אופני-שטח-חשמליים", "category": "electric", "sub_category": "electric_mtb"},
    {"url": f"{BASE_URL}/353678-אופני-ילדים", "category": "kids", "sub_category": "kids"},
    {"url": f"{BASE_URL}/357667-אופני-עיר", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/353675-אופני-שטח", "category": "mtb", "sub_category": None},  # Will be determined by firm name
]

def safe_to_int(text):
    """Extracts the first number from a string and converts it to int, or returns 'Not listed'."""
    match = re.search(r'\d+', text.replace(",", ""))
    if match:
        return int(match.group())
    else:
        return "צור קשר"

def is_driver_alive(driver):
    """Check if the WebDriver is still functional"""
    try:
        driver.current_url
        return True
    except:
        return False

def recreate_driver():
    """Create a new WebDriver instance"""
    try:
        print("🔄 Recreating Chrome driver...")
        # Add some options to make Chrome more stable
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        driver = uc.Chrome(options=options, version_main=144)
        print("✅ New Chrome driver created successfully!")
        return driver
    except Exception as e:
        print(f"❌ Failed to recreate Chrome driver: {e}")
        return None

def rewrite_description_with_chatgpt(original_text, api_key):
    """Rewrite product description using ChatGPT API"""
    if not original_text or not api_key:
        print("⚠️ Warning: No text or API key provided for ChatGPT rewriting")
        return original_text
    
    try:
        # Prepare the API request
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים בחנויות אינטרנטיות. המטרה שלך היא לקחת תיאור אופניים קיים וליצור גרסה חדשה, מושכת ומקצועית, כך שהקורא לא יזהה את המקור. יש להתמקד בחוויית רכיבה, נוחות, בטיחות, עיצוב ויתרונות שימושיים לעיר, לטיולים או לרכיבה יומיומית. אפשר להוסיף הרחבות, פרטים ושפה שיווקית, אך אין לשנות את מהות האופניים."
                },
                {
                    "role": "user",
                    "content": f"להלן תיאור האופניים: \n\n{original_text}\n\nאנא כתוב גרסה שיווקית חדשה, מושכת, שמתאימה לפרסום בחנות אינטרנטית, עם דגש על חוויית רכיבה, יתרונות המוצר, עיצוב ונוחות, תוך שמירה על מהות האופניים. הרחב ותאר את האופניים בצורה שתגרום לקוראים לרצות לרכוש אותם אך לא בצורה מוגזמת, לוחצת וגסה ודוחפת, כולל קריאה לפעולה בסוף."
                }
            ],
            "temperature": 0.6,
            "max_tokens": 500
        }
        
        # Make the API request
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        # Extract the rewritten text
        result = response.json()
        rewritten_text = result['choices'][0]['message']['content'].strip()
        
        return rewritten_text
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling ChatGPT API: {e}")
        return original_text
    except KeyError as e:
        print(f"❌ Error parsing ChatGPT response: {e}")
        return original_text
    except Exception as e:
        print(f"❌ Unexpected error in ChatGPT rewriting: {e}")
        return original_text


def motofan_bikes(driver, output_file):
    for entry in MOTOFAN_TARGET_URLS:
        target_url = entry["url"]
        category_text = entry["category"]
        sub_category_text = entry.get("sub_category", None)
        
        print(f"\n🌐 Scraping: {target_url}")
        
        # Check if driver is still alive before each page
        if not is_driver_alive(driver):
            print("⚠️ WebDriver is not responding, recreating...")
            driver = recreate_driver()
            if not driver:
                print("❌ Cannot continue without a working WebDriver")
                break
        
        # Retry logic for page loading
        max_retries = 3
        for attempt in range(max_retries):
            try:
                driver.get(target_url)
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                break  # Success, exit retry loop
            except Exception as e:
                print(f"❌ Error loading page {target_url} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("🔄 Retrying...")
                    time.sleep(3)  # Wait before retry
                    # Try to recreate driver if it seems broken
                    if not is_driver_alive(driver):
                        driver = recreate_driver()
                        if not driver:
                            break
                else:
                    print(f"❌ Failed to load {target_url} after {max_retries} attempts, skipping...")
                    continue
        
        # Parse the page source with BeautifulSoup and find product cards
        print("🔍 Searching for product cards...")
        cards = soup.find_all("div", class_="layout_list_item")
        print(f"✅ Found {len(cards)} products.\n")

        for idx, card in enumerate(cards):
            print(f"Processing Product {idx+1}/{len(cards)}")

            firm = None
            model = None
            year = None
            original_price = None
            disc_price = None
            img_url = None
            product_url = None

            # Common bike brands that might appear in the title
            common_brands = [
                "MOUSTACHE", "PIVOT", "REID", "IBIS", "RUDERBERNA", "RUDER BERNA"
            ]

            # Remove common Hebrew bike type terms and redundant words
            terms_to_remove = [
                # Hebrew bike type terms
                "אופני שטח חשמליים",
                "אופני הרים חשמליים", 
                "אופני שטח",
                "אופני הרים גברים",
                "אופני הרים ילדים",
                "אופני עיר ילדים",
                "אופני עיר",
                "אופני סינגל ספיד",
                "תלת אופן",
                
                # Brand names and variations
                "מוסטש",
                "MOUSTACHE",
                "Moustache",
                
                # Model type terms
                "גיים",
                "GAME",
                "Game",
                "טרייל", 
                "TRAIL",
                "Trail",
                "קיט",
                "KIT",
                "Kit",
                
                # Electric bike terms
                "E- BIKE",
                "E-BIKE",
                "E-Bike",
                "E BIKE",
                "Electric",
                "ELECTRIC",
                
                # Common redundant words
                "Ride",
                "RIDE",
                "Pro",
                "PRO",
                "SL",
                "SLX",
                "XT",
                "X0",
                "Eagle",
                "EAGLE",
                "Transmission",
                "TRANSMISSION",
                "Disc",
                "DISC",
                "Black",
                "BLACK",
                "Pink",
                "PINK",
                "Classic",
                "CLASSIC",
                "LADY",
                "Lady",
                "WOMAN",
                "Woman",
                "Puristico",
                "PURISTICO",
                "Harrier",
                "HARRIER",
                "Eightper",
                "EIGHTPER",
                "Viper",
                "VIPER",
                "Scout",
                "SCOUT",
                "Loko",
                "LOKO",
                "כסוף",
                "כחול",
                "ללא הילוכים",
                "עם הילוכים ומעצורי דיסק הידראולי",
                "במגוון צבעים",
                "לגברים",
                "נשים",
                "גברים",
                "ילדים",
                "ליידי",
                "קלאסיק",
                "דיסק",
                "הידראולי",
                "רודרברנה",
                "טראנזיט",
                "הרייר",
                "לוקו",
                "סקאוט",
                "וייפר",
                "אייטפר",
                "פוריסטיקו",
                
                # Size indicators that should be removed from model names
                "20\"",
                "24\"",
                "29\"",
                "26\"",
                "27.5\"",
                
                # Common prefixes/suffixes
                "-",
                "–",
                "—",
                "  ",  # Double spaces
                "   ", # Triple spaces
                
                # Numbers that are likely not part of model names
                "2.0",
                "3.0",
                "4.0",
                "5.0",
                "6.0",
                "7.0",
                "8.0",
                "9.0",
                "10.0",
                
                # Common bike component terms that shouldn't be in model names
                "Shimano",
                "SHIMANO",
                "SRAM",
                "Bosch",
                "BOSCH",
                "Magura",
                "MAGURA",
                "Marzocchi",
                "MARZOCCHI",
                "Fox",
                "FOX",
                "RockShox",
                "ROCKSHOX",
                "Suntour",
                "SUNTOUR"
            ]
            
            # Extract product title
            title_text = card.find('h3', class_='title')
            if title_text:
                raw_title_text = title_text.get_text(strip=True)
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
                    break
                    
            # Clean up the model name (remove extra spaces and common terms)
            cleaned_model = re.sub(r'\s+', ' ', dirty_model).strip()
            
            for term in terms_to_remove:
                cleaned_model = cleaned_model.replace(term, "").strip()
            
            model = cleaned_model

            # Extract year from the end of the title
            year_match = re.search(r'(202[0-9]|202[0-9])', model)
            year = int(year_match.group(1)) if year_match else None
                    
            # Remove year from model name if found
            if year:
                model = model.replace(str(year), "").strip()
            
            # If model is empty after cleaning, try to extract from URL or title
            if not model or len(model.strip()) == 0:
                # Try to extract from product URL if available (will be set later)
                # For now, check title for special cases
                if "תלת אופן" in raw_title_text or "תלת-אופן" in raw_title_text:
                    # Tricycle - extract wheel size
                    wheel_match = re.search(r'(\d+)[""]', raw_title_text)
                    if wheel_match:
                        model = f"Tricycle {wheel_match.group(1)}\""
                    else:
                        model = "Tricycle"
                elif "סינגל ספיד" in raw_title_text or "single speed" in raw_title_text.lower():
                    # Single speed bike
                    if "PURISTICO" in raw_title_text.upper() or "פוריסטיקו" in raw_title_text:
                        model = "PURISTICO"
                    elif "EIGHTPER" in raw_title_text.upper() or "אייטפר" in raw_title_text:
                        model = "EIGHTPER"
                    else:
                        model = "Single Speed"
                else:
                    # Last resort: use a portion of the title
                    model = raw_title_text[:50].strip() if raw_title_text else "Unknown Model"

            # Extract price
            price_tag = card.find('p', class_='price')
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                # Remove the Hebrew text "מחיר" and any extra whitespace
                clean_price_text = re.sub(r'מחיר\s*', '', price_text).strip()
                original_price = safe_to_int(clean_price_text)
            else:
                print("⚠️ Price element (price) not found")
                original_price = "צור קשר"
            
            # Extract image
            img_tag = card.find('img', class_='img-responsive')
            if img_tag:
                img_url = img_tag.get('src')
            else:
                print("⚠️ Warning: Image tag not found")  

            # Extract product link - look for the specific structure in the wrap div
            wrap_div = card.find('div', class_='wrap')
            if wrap_div:
                # Find the first anchor tag that contains the product link (not the brand link)
                product_link_tag = wrap_div.find('a', href=True)
                if product_link_tag:
                    raw_href = product_link_tag.get('href', '')
                    clean_href = raw_href.strip()  # removes spaces, tabs, and newlines
                    product_url = urljoin(BASE_URL, clean_href)
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
                else:
                    product_url = None
                    print("⚠️ Product link not found")

            # Create product data dictionary
            product_data = {
                "source": {
                    "importer": "Moto-Fan",
                    "domain": BASE_URL,
                    "product_url": product_url
                },
                "firm": firm,
                "model": model,
                "year": year,
                "category": category_text,
                "sub_category": sub_category_text,
                "original_price": original_price,
                "disc_price": disc_price,
                "images": {
                    "image_url": img_url,
                    "gallery_images_urls": []
                },
                "specs": {}
            }

            # Visit product page and extract specs
            if product_url:
                try:
                    driver.get(product_url)
                    time.sleep(4)
                    prod_soup = BeautifulSoup(driver.page_source, "html.parser")

                    # Extract and rewrite product description
                    # Look for the span element with data-font-size="14" that contains the description
                    description_element = prod_soup.find("div", {"id": "item_current_sub_title"}).find("span")
                    original_description = ""
                    rewritten_description = ""
                    
                    if description_element:
                        # Extract only the text content, removing HTML tags
                        original_description = description_element.get_text(strip=True)
                        
                        # Rewrite with ChatGPT if API key is available
                        if CHATGPT_API_KEY:
                            rewritten_description = rewrite_description_with_chatgpt(original_description, CHATGPT_API_KEY)
                        else:
                            print("⚠️ Warning: No ChatGPT API key provided, using original description")
                            rewritten_description = original_description
                    else:
                        print("⚠️ Warning: No product description found")
                    
                    # Add descriptions to product data
                    product_data["rewritten_description"] = rewritten_description

                    #images Gallery
                    ul = prod_soup.find('ul', class_='lightSlider lsGrab lSSlide')
                    # Extract all image srcs from <li> elements inside this <ul>
                    if ul:
                        gallery_images_urls = [img['src'] for img in ul.find_all('img') if img.get('src')]
                        product_data["images"]["gallery_images_urls"] = gallery_images_urls
                    else:
                        product_data["images"]["gallery_images_urls"] = []

                    # Extract specifications from the product page
                    spec_list = prod_soup.find_all('li')
                    for spec_item in spec_list:
                        bold_tag = spec_item.find('b')
                        if bold_tag:
                            spec_name = bold_tag.get_text(strip=True).lower()
                            span_tag = spec_item.find('span', class_='he_false')
                            if span_tag:
                                spec_value = span_tag.get_text(strip=True)
                                product_data["specs"][spec_name] = spec_value

                except Exception as e:
                    print(f"⚠️ Error scraping product page ({product_url}): {e}")

            # Extract battery capacity (Wh) from specs
            battery_value = product_data.get("specs", {}).get("battery", "")
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
            fork_text = product_data.get("specs", {}).get("fork", "")
            match = re.search(r'(?<!\d)(40|50|60|70|80|90|100|110|120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
            if match:
                fork_length = match.group(1)
                product_data["fork length"] = int(fork_length)
            else:
                print(f"⚠️ Warning: Could not extract fork length from: '{fork_text}' - skipping sub-category assignment")
                product_data["fork length"] = None


            #----sub-category----
            # For the specific MTB URL (אופני-שטח-353675), determine style and sub_category based on firm name or fork length
            if "353675-אופני-שטח" in target_url:
                # Set sub_category based on firm name (at firm level as requested)
                firm_sub_category_map = {
                    "REID": "hardtail_mtb",
                    "Reid": "hardtail_mtb",
                    "PIVOT": "trail",
                    "Pivot": "trail",
                    "IBIS": "trail",
                    "Ibis": "trail",
                }
                
                if firm and firm.upper() in [k.upper() for k in firm_sub_category_map.keys()]:
                    # Use firm-based sub_category
                    product_data["sub_category"] = firm_sub_category_map.get(firm, firm_sub_category_map.get(firm.upper(), "hardtail_mtb"))
                elif firm == "REID":
                    product_data["style"] = "hardtail_mtb"
                    product_data["sub_category"] = "hardtail_mtb"
                else:
                    # Use fork length logic for non-REID bikes from MTB URL
                    fork_length_str = product_data.get("fork length")
                    if fork_length_str is not None:
                        try:
                            fork_length = int(fork_length_str)
                            if fork_length in [40,50,60,70,80,90,100,110,120]:
                                product_data["style"] = "cross-country"
                                product_data["sub_category"] = "hardtail_mtb"
                            elif fork_length in [130, 140, 150]:
                                product_data["style"] = "trail"
                                product_data["sub_category"] = "trail"
                            elif fork_length in [160, 170, 180]:
                                product_data["style"] = "enduro"
                                product_data["sub_category"] = "enduro"
                            else:
                                print(f"⚠️ Warning: Unexpected fork length value: {fork_length} - defaulting to full_suspension_mtb")
                                product_data["style"] = "full_suspension_mtb"
                                product_data["sub_category"] = "full_suspension"
                        except ValueError as e:
                            print(f"⚠️ Warning: Invalid fork length '{fork_length_str}': {e} - defaulting to full_suspension_mtb")
                            product_data["style"] = "full_suspension_mtb"
                            product_data["sub_category"] = "full_suspension"
                    else:
                        # No fork length - use firm-based or default
                        if firm and firm.upper() in ["PIVOT", "IBIS"]:
                            product_data["sub_category"] = "trail"
                        else:
                            print("⚠️ Warning: No fork length available - defaulting to hardtail_mtb")
                            product_data["sub_category"] = "hardtail_mtb"
            else:
                # For other URLs, use fork length logic for style (but sub_category comes from URL)
                fork_length_str = product_data.get("fork length")
                if fork_length_str is not None:
                    try:
                        fork_length = int(fork_length_str)
                        if fork_length in [40,50,60,70,80,90,100,110,120]:
                            product_data["style"] = "cross-country"
                        elif fork_length in [130, 140, 150]:
                            product_data["style"] = "trail"
                        elif fork_length in [160, 170, 180]:
                            product_data["style"] = "enduro"
                        else:
                            print(f"⚠️ Warning: Unexpected fork length value: {fork_length} - using sub_category from URL")
                    except ValueError as e:
                        print(f"⚠️ Warning: Invalid fork length '{fork_length_str}': {e} - using sub_category from URL")
                else:
                    print("⚠️ Warning: No fork length available - using sub_category from URL")

            scraped_data.append(product_data)
            
            # Save progress after each product is processed (real-time updates)
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(scraped_data, f, ensure_ascii=False, indent=4)
                print(f"💾 Real-time save: {len(scraped_data)} products saved to JSON file")
            except Exception as e:
                print(f"⚠️ Warning: Could not save progress: {e}")

        # Summary after each URL is processed
        print(f"✅ Completed {category_text}: {len([p for p in scraped_data if p.get('category') == category_text])} products")

    return scraped_data, driver


# --- Setup Output File ---
if __name__ == '__main__':
    try:
        # Get project root (go up from data/scrapers/ to data/ to project root)
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "data" / "scraped_raw_data"
        os.makedirs(output_dir, exist_ok=True)  # Create directory if it doesn't exist
        output_file = output_dir / "motofan_data.json"
        print(f"📁 Output file: {output_file}")
        
        # Create empty JSON file to start with
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        print("📄 Created empty JSON file - ready for data!")
        
    except Exception as e:
        print(f"❌ Error setting up output directory: {e}")
        exit(1)

    # --- Run the Scraper ---
    products = []
    driver = None
    try:
        print("🚀 Starting Chrome driver...")
        # Add stable Chrome options
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        driver = uc.Chrome(options=options, version_main=144)
        print("✅ Chrome driver started successfully!")
        products, driver = motofan_bikes(driver, output_file)
    except Exception as e:
        print(f"❌ Error initializing Chrome driver: {e}")
        print("💡 Make sure Chrome browser is installed and accessible")
        products = []
    finally:
        if driver:
            try:
                driver.quit()
                print("🔒 Chrome driver closed")
            except:
                pass

    # Final summary
    print(f"\n✅ Scraping completed!")
    print(f"📊 Total products scraped: {len(products)}")
    print(f"💾 Final data saved to: {output_file}")

    # Ensure final data is saved even if scraping failed
    if len(products) == 0:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            print("📄 Updated JSON file with empty results")
        except Exception as e:
            print(f"⚠️ Warning: Could not update final JSON file: {e}")