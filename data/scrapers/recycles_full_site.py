# -*- coding: utf-8 -*-
import time
import re
import json
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc

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
    "מנוע": "motor",
    "צירי גלגלים": "hubs"
}

BASE_URL = "https://www.recycles.co.il/"

# ChatGPT API Configuration
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

scraped_data = []

RECYCLES_TARGET_URLS = [
    {"url": f"{BASE_URL}/אופני_הרים?סוג%20אופניים=261033&bsfilter-11634=261033", "category": "mtb", "sub_category": "full_suspension"},
    {"url": f"{BASE_URL}/אופני_הרים?סוג%20אופניים=261034&bsfilter-11634=261034", "category": "mtb", "sub_category": "hardtail"},
    {"url": f"{BASE_URL}/e_bike_mtb-אופני_הרים_חשמליים", "category": "electric", "sub_category": "electric_mtb"},
    {"url": f"{BASE_URL}/אופני_כביש?סוג%20אופניים=261375&bsfilter-11634=261375", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/אופני_כביש?סוג%20אופניים=261376&bsfilter-11634=261376", "category": "road", "sub_category": "timetrail"},
    {"url": f"{BASE_URL}/אופני_גראבל?סוג%20אופניים=261374&bsfilter-11634=261374", "category": "gravel", "sub_category": "gravel"},
    {"url": f"{BASE_URL}/אופני_גראבל?סוג%20אופניים=504381&bsfilter-11634=504381", "category": "electric", "sub_category": "electric_gravel"},
    {"url": f"{BASE_URL}/עירוני_חשמלי", "category": "electric", "sub_category": "electric_ city"},
    {"url": f"{BASE_URL}/אופני_עיר", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/אופני_ילדים", "category": "kids", "sub_category": "kids"},
    {"url": f"{BASE_URL}/כביש", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/טריאתלון_ונגש", "category": "road", "sub_category": "timetrail"},
    {"url": f"{BASE_URL}/גראבל", "category": "gravel", "sub_category": "gravel"},
    {"url": f"{BASE_URL}/מסלול", "category": "road", "sub_category": "track"},

]

def safe_to_int(text):
    try:
        return int(str(text).replace(',', '').replace('₪', '').replace("ליח'", '').strip())
    except (ValueError, AttributeError):
        return "צור קשר"

def rewrite_description_with_chatgpt(original_text, api_key):
    """Rewrite product description using ChatGPT API"""
    if not original_text:
        print("⚠️ Warning: No text provided for ChatGPT rewriting")
        return original_text
    
    if not api_key:
        print("⚠️ Warning: No API key provided for ChatGPT rewriting")
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

def recycles_bikes(driver, output_file):
    for entry in RECYCLES_TARGET_URLS:
        target_url = entry["url"]
        category_text = entry["category"]
        sub_category_text = entry.get("sub_category", None)
        
        print(f"\n🌐 Scraping: {target_url}")
        driver.get(target_url)
        time.sleep(3)

        # Parse the page source with BeautifulSoup and find product cards
        print("🔍 Searching for product cards...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("div", class_="brdr")
        print(f"✅ Found {len(cards)} products")

        for i, product in enumerate(cards, 1):
            print(f"Processing Product {i}/{len(cards)}")
            
            # Extract basic info from product card
            link_tag = product.find("a", href=True)
            if not link_tag:
                print("⚠️ No product link found, skipping...")
                continue
                
            product_url = BASE_URL + link_tag["href"]
            driver.get(product_url)
            time.sleep(2)
            product_soup = BeautifulSoup(driver.page_source, "html.parser")

            # Initialize price variables
            original_price = ""
            disc_price = ""
            
            # Extract title and firm/model info
            title_tag = product_soup.find("div", class_="title col-12 col-xl-10")
            firm = ""
            model = ""
            year_text = ""
            
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                
                # Extract year first, before cleaning the title
                year_text = ""
                for year in ["'22","'23", "'24", "'25", "'26"]:
                    if year in title_text:
                        year_text = f"20{year}".replace("'", "")
                        break
                
                if not year_text:
                    year_text = "לא צויין"
                
                # Extract firm name FIRST, before removing terms from title
                # Recycles carries Orbea, Factor and Niner bikes
                if "Orbea" in title_text or "ORBEA" in title_text:
                    firm = "Orbea"
                    model = title_text.replace("Orbea", "").replace("ORBEA", "").strip()
                elif "Factor" in title_text or "FACTOR" in title_text:
                    firm = "Factor"
                    model = title_text.replace("Factor", "").replace("FACTOR", "").strip()
                elif "Niner" in title_text or "NINER" in title_text:
                    firm = "Niner"
                    model = title_text.replace("Niner", "").replace("NINER", "").strip()
                else:
                    # Check URL as fallback for both brands
                    url_lower = product_url.lower()
                    title_lower = title_text.lower()
                    if "orbea" in url_lower or "orbea" in title_lower:
                        firm = "Orbea"
                    elif "factor" in url_lower or "factor" in title_lower:
                        firm = "Factor"
                    elif "niner" in url_lower or "niner" in title_lower:
                        firm = "Niner"
                    else:
                        # Additional fallback: check if it's an Orbea model by common patterns
                        # Check both URL and title for model patterns
                        combined_text = f"{url_lower} {title_lower}"
                        if any(pattern in combined_text for pattern in ["oiz", "ltd", "rise", "wild", "occam", "alma", "orca","ordu", "avant", "carpe"]):
                            firm = "Orbea"
                        elif any(pattern in combined_text for pattern in ["ostro", "one", "vam"]):
                            firm = "Factor"
                        elif any(pattern in combined_text for pattern in ["niner", "ninja"]):
                            firm = "Niner"
                        else:
                            firm = "Unknown"
                    
                    model = title_text
                
                # Remove category-specific terms from title (after firm extraction)
                terms_to_remove = [
                    "אופני הרים חשמליים",
                    "אופני הרים",
                    "אופני כביש",
                    "אופני גראבל",
                    "אופני טריאתלון",
                    "אופני מסלול",
                    "אופני עיר",
                    "אופני ילדים",
                    "אופני עיר חשמליים",
                    "אופני גראבל חשמליים",
                    "ORBEA",
                    "FACTOR",
                    "Factor",
                    "NINER",
                    "Niner",
                ]
                
                for term in terms_to_remove:
                    model = model.replace(term, "").strip()

                # Remove year from model name if it exists
                for year in ["'22","'23", "'24", "'25", "'26"]:
                    if year in model:
                        model = model.replace(year, "").strip()
                        break

            # Extract sale price (discounted price if discount exists, regular price if no discount)
            price_tag = product_soup.select_one(".saleprice")
            if price_tag:
                raw_price = price_tag.string.strip() if price_tag.string else price_tag.get_text(strip=True)
                sale_price = safe_to_int(raw_price)
            else:
                sale_price = ""

            # Extract original price (check if there's a discount)
            price_disc_tag = product_soup.find("span", class_="oldprice")
            
            # Check if there's actually a discount (oldprice element exists AND has content)
            if price_disc_tag and price_disc_tag.get_text(strip=True):
                # There's a discount - oldprice contains the original price
                raw_disc_price = price_disc_tag.string.strip() if price_disc_tag.string else price_disc_tag.get_text(strip=True)
                original_price = safe_to_int(raw_disc_price)
                disc_price = sale_price  # This is the discounted price
            else:
                # No discount - salePrice is the original price
                original_price = sale_price
                disc_price = ""  # No discount, so discounted price is empty

            # Extract main image
            img_tag = product_soup.find("img", attrs={"class": lambda x: x and "sp-image" in x})
            img_src = img_tag["data-default"] if img_tag and img_tag.has_attr("data-default") else ""
            img_url = BASE_URL + img_src if img_src else "N/A"

            # Create structured product data
            product_data = {
                "source": {
                    "importer": "Recycles",
                    "domain": BASE_URL,
                    "product_url": product_url
                },
                "firm": firm,
                "model": model,
                "year": year_text,
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

            # Extract gallery images from thumbnails
            gallery_images_urls = []
            thumbnails_div = product_soup.find("div", class_="sp-thumbnails sp-grab")
            if thumbnails_div:
                for img in thumbnails_div.find_all("img", class_="sp-thumbnail"):
                    src = img.get("src")
                    if src:
                        # If the src is a relative path, join with BASE_URL
                        if not src.startswith("http"):
                            src = urljoin(BASE_URL, src)
                        gallery_images_urls.append(src)
            product_data["images"]["gallery_images_urls"] = gallery_images_urls

            # Extract product description
            description_element = None
            description_text = ""
            
            # Try multiple selectors for description
            possible_selectors = [
                ("div", {"class": "product-description"}),
                ("div", {"class": "description"}),
                ("div", {"class": "product-details"}),
                ("div", {"class": "content"}),
                ("div", {"class": "tab-content"}),
                ("p", {"class": "description"}),
                ("section", {"class": "description"})
            ]
            
            for tag, attrs in possible_selectors:
                description_element = product_soup.find(tag, attrs)
                if description_element:
                    break
            
            original_description = ""
            rewritten_description = ""
            
            if description_element:
                original_description = description_element.get_text(strip=True)
                
                # Always try to rewrite with ChatGPT
                if original_description.strip():
                    rewritten_description = rewrite_description_with_chatgpt(original_description, CHATGPT_API_KEY)
                else:
                    print("⚠️ Warning: Empty description found")
                    rewritten_description = original_description
            else:
                print("⚠️ Warning: No product description found")
            
            # Add descriptions to product data
            product_data["rewritten_description"] = rewritten_description

            # Extract specs from <ul class="row list-unstyled">
            spec_list = product_soup.find("ul", class_="row list-unstyled")
            if spec_list:
                spec_items = spec_list.find_all("div", class_="spec col-12 col-lg-6")
                for item in spec_items:
                    key_span = item.find("span", class_="specTxt")
                    val_div = item.find("div", class_="specValue")
                    if key_span and val_div:
                        key = key_span.get_text(strip=True)
                        val = val_div.get_text(strip=True)
                        # Use existing HEBREW_TO_ENGLISH_KEYS dictionary to create structured specs
                        english_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)
                        product_data["specs"][english_key] = val
            else:
                print("⚠️ Warning: No specifications section found")

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
            fork_length = None
            
            if fork_text:  # Only try to extract if fork data exists
                # Look for travel-specific patterns (avoid hub widths like 15x110, 12x110)
                # Patterns: "150mm", "160mm travel", "travel: 150", "150 mm", etc.
                travel_patterns = [
                    r'(?:travel|טווח)[\s:]*(\d{2,3})\s*mm',  # "travel: 150mm" or "טווח: 150mm"
                    r'(\d{2,3})\s*mm\s*(?:travel|טווח)',      # "150mm travel"
                    r'(\d{2,3})\s*mm(?!\s*[x×])',             # "150mm" but not "15x110" or "12×110"
                ]
                
                for pattern in travel_patterns:
                    match = re.search(pattern, fork_text.lower())
                    if match:
                        potential_length = int(match.group(1))
                        # Validate it's a reasonable fork travel length (40-180mm)
                        if 40 <= potential_length <= 180:
                            fork_length = potential_length
                            break
                
                # If no travel pattern found, try to find standalone numbers but exclude hub widths
                if fork_length is None:
                    # Look for numbers that are NOT part of hub width patterns (like 15x110, 12x110)
                    # Exclude patterns like: \d+x\d+ (hub width), or numbers followed by Boost/Qr/etc
                    match = re.search(r'(?<![\dx])(40|50|60|70|80|90|100|120|130|140|150|160|170|180)(?![\dx]|boost|qr|thru)', fork_text.lower())
                    if match:
                        potential_length = int(match.group(1))
                        # Double check it's not a hub width by ensuring it's not near "x" or "×"
                        # Check 5 chars before and after
                        match_pos = match.start()
                        context = fork_text.lower()[max(0, match_pos-5):match_pos+10]
                        if 'x' not in context and '×' not in context:
                            fork_length = potential_length
            
            product_data["fork length"] = fork_length

            #----sub-category----
            if fork_length is not None:
                try:
                    if fork_length in [40, 50, 60, 70, 80, 90, 100, 110, 120]:
                        product_data["style"] = "cross-country"
                    elif fork_length in [130, 140, 150]:
                        product_data["style"] = "trail"
                    elif fork_length in [160, 170, 180]:
                        product_data["style"] = "enduro"
                    else:
                        product_data["style"] = "unknown"
                except ValueError:
                    product_data["style"] = "unknown"
            else:
                # Fallback: Check model name for known bike types
                model_lower = product_data.get("model", "").lower()
                url_lower = product_data.get("source", {}).get("product_url", "").lower()
                combined_text = f"{model_lower} {url_lower}"
                
                # Wild models are enduro bikes
                if "wild" in combined_text:
                    product_data["style"] = "enduro"
                # Rise models are typically trail/cross-country
                elif "rise" in combined_text:
                    product_data["style"] = "trail"
                # Oiz models are cross-country
                elif "oiz" in combined_text:
                    product_data["style"] = "cross-country"
                # Occam models are trail
                elif "occam" in combined_text:
                    product_data["style"] = "trail"
                else:
                    product_data["style"] = "unknown"
                
            scraped_data.append(product_data)
            
            # Save data incrementally (real-time updates)
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(scraped_data, f, ensure_ascii=False, indent=4)
                print(f"💾 Real-time save: {len(scraped_data)} products saved to JSON file")
            except Exception as e:
                print(f"⚠️ Error saving data: {e}")

        # Summary after each URL is processed
        print(f"✅ Completed {category_text}: {len([p for p in scraped_data if p.get('category') == category_text])} products")

    return scraped_data

# --- Setup Output Directory ---
if __name__ == '__main__':
    try:
        # Get project root (go up from data/scrapers/ to data/ to project root)
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "data" / "scraped_raw_data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = output_dir / "recycles_data.json"
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
        products = recycles_bikes(driver, output_file)
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