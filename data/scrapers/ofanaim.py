import time
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
import requests
from PIL import Image
import pytesseract
import io
import base64
import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ----- Hebrew to English Key Mapping -----
# This dictionary maps Hebrew keys found in the scraped data to their English equivalents
# Add new mappings here as you encounter more Hebrew keys
HEBREW_TO_ENGLISH_KEYS = {
    "סוג אופניים": "bike_type",        # Bike type
    "חומר שלדה": "frame_material",     # Frame material
    "גודל גלגלים": "wheel_size",       # Wheel size
    "חברה": "company"                  # Company/Brand
}

# ----- Setup -----
BASE_URL = "https://www.ofanaim.co.il/"
TARGET_URL = BASE_URL + "product-category/emtb/"

scraped_data = []

def translate_hebrew_keys(data_dict):
    """
    Translate Hebrew keys to English keys in a dictionary
    """
    translated_dict = {}
    for key, value in data_dict.items():
        if key in HEBREW_TO_ENGLISH_KEYS:
            translated_key = HEBREW_TO_ENGLISH_KEYS[key]
            translated_dict[translated_key] = value
            print(f"🔄 Translated Hebrew key '{key}' to '{translated_key}'")
        else:
            translated_dict[key] = value
    return translated_dict

def should_skip_image(image_url):
    """
    Check if an image should be skipped (sizing tables, geometry charts, etc.)
    """
    # Convert to lowercase for easier matching
    url_lower = image_url.lower()
    
    # Skip sizing table images
    if any(keyword in url_lower for keyword in [
        'gep-',  # Geometry/sizing tables
        'geo-',  # Geometry
        'sizing', 
        'size-',
        'geometry',
        'chart',
        'table'
    ]):
        return True
    
    # Skip images with specific dimensions that indicate charts/tables
    if any(pattern in url_lower for pattern in [
        '300x147',  # Common sizing table dimensions
        '300x144',  # Another common sizing table dimension
        'chart',
        'table'
    ]):
        return True
    
    return False

def extract_specs_from_image_with_chatgpt(image_url):
    """
    Extract specifications from an image using ChatGPT API and return structured JSON data
    """
    try:
        # Check if OpenAI API key is set
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️ OPENAI_API_KEY not found in environment variables or .env file")
            return {}
        
        # Download the image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Convert image to base64
        image_base64 = base64.b64encode(response.content).decode('utf-8')
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Prepare the prompt for ChatGPT
        prompt = """
        Analyze this image which contains technical specifications for an electric mountain bike (eMTB).
        Extract all the specification data and return it as a JSON object.
        
        IMPORTANT: If this image appears to be a sizing table, geometry chart, or measurement diagram, 
        return an empty JSON object {} as these are not the specifications we need.
        
        The image should contain specifications like:
        - Frame material, size, geometry
        - Motor brand, power, torque
        - Battery capacity, voltage
        - Fork brand, travel, type
        - Shock brand, travel
        - Drivetrain components (derailleur, cassette, chainring)
        - Brake system
        - Wheel size, tire specifications
        - Weight, dimensions
        - And other technical details
        
        DO NOT extract:
        - Sizing tables with measurements for different frame sizes
        - Geometry charts with angles and measurements
        - Measurement diagrams
        - Tables that show S/M/L/XL dimensions
        
        Please extract all visible specifications and return them as a clean JSON object where:
        - Keys are lowercase English specification names
        - Values are the corresponding specification values
        - Skip any empty or unclear values
        - If you see Hebrew text, translate the keys to English but keep values as they appear
        
        Return ONLY the JSON object, no additional text or explanations.
        """
        
        # Call ChatGPT API with the image
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        # Extract the response content
        content = response.choices[0].message.content.strip()
        
        # Try to parse the JSON response
        try:
            # Remove any markdown formatting if present
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            specs_data = json.loads(content)
            print(f"✅ Successfully extracted {len(specs_data)} specifications from image")
            return specs_data
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse JSON response: {e}")
            print(f"Raw response: {content[:200]}...")
            return {}
            
    except Exception as e:
        print(f"⚠️ Error processing image with ChatGPT API ({image_url}): {e}")
        return {}

def extract_text_from_image(image_url):
    """
    Extract text from an image using OCR (fallback method)
    """
    try:
        # Download the image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        # Open image with PIL
        image = Image.open(io.BytesIO(response.content))

        try:
            # Extract text using pytesseract
            # Configure for Hebrew text
            text = pytesseract.image_to_string(image, lang='heb+eng', config='--psm 6')
            return text.strip()
        except ImportError:
            print("⚠️ pytesseract not installed. Install it with: pip install pytesseract")
            print("⚠️ Also install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
            return ""
        except Exception as e:
            print(f"⚠️ OCR error for image {image_url}: {e}")
            return ""

    except Exception as e:
        print(f"⚠️ Error downloading image {image_url}: {e}")
        return ""

def extract_specs_from_image_or_text(spec_element):
    """
    Extract specifications from either text or image
    Returns either a string (for text) or a dictionary (for image specs from ChatGPT)
    """
    # First try to get text directly
    text_content = spec_element.get_text(strip=True)

    # If no text content, look for images
    if not text_content:
        img_tags = spec_element.find_all('img')
        for img in img_tags:
            img_src = img.get('src')
            if img_src:
                # Handle relative URLs
                if img_src.startswith('/'):
                    img_src = BASE_URL + img_src
                elif not img_src.startswith('http'):
                    img_src = urljoin(BASE_URL, img_src)

                # Skip sizing table images and geometry charts
                if should_skip_image(img_src):
                    print(f"⏭️ Skipping sizing/geometry image: {img_src}")
                    continue

                print(f"🔍 Found image specification: {img_src}")
                # Extract specifications using ChatGPT API
                extracted_specs = extract_specs_from_image_with_chatgpt(img_src)
                if extracted_specs:
                    print(f"✅ Extracted specifications from image using ChatGPT API")
                    # Return the specifications as a dictionary that can be merged
                    return extracted_specs
                else:
                    print(f"❌ Failed to extract specifications from image: {img_src}")

    return text_content

def handle_spec_extraction_result(result, products_data):
    """
    Handle the result from extract_specs_from_image_or_text
    If it's a dictionary, merge it into products_data
    If it's a string, return it as is
    """
    if isinstance(result, dict):
        # Merge the extracted specifications into products_data
        for key, value in result.items():
            if key and value and len(str(value)) > 1:
                products_data[key] = value
                print(f"📋 Extracted from ChatGPT API: {key} = {value}")
        return None  # Return None since we've already merged the data
    else:
        # Return the string value as is
        return result

def safe_to_int(text):
    try:
        return int(str(text).replace(',', '').replace('₪', '').strip())
    except (ValueError, AttributeError):
        return "צור קשר"

def ofanaim_bikes(driver):
    print(f"\n🌐 Scraping: {TARGET_URL}")
    driver.get(TARGET_URL)
    time.sleep(5)  # wait for page to load

    print("🔍 Searching for product cards...")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.find_all("li", class_="product-style-default")
    print(f"✅ Found {len(cards)} products.\n")

    for idx, card in enumerate(cards, start=1):
        print(f"\n➡️ Scraping product {idx}/{len(cards)}...")

        title_tag = card.select_one('h3.woocommerce-loop-product__title a')
        model = title_tag.get_text(strip=True) if title_tag else ""

        # Firm (from category links, assuming the first one is the brand)
        firm_tag = card.select_one('.posted-in a')
        firm = firm_tag.get_text(strip=True).replace("אופני", "").strip() if firm_tag else ""

        # Remove firm name from model if it appears at the beginning
        if firm and model.lower().startswith(firm.lower()):
            model = model[len(firm):].strip()

        # Year from model string
        year_match = re.search(r'(2024|2025|2026)', model)
        year = year_match.group(1) if year_match else ""

        # Remove year from model name if found
        if year:
            model = model.replace(year, "").strip()

        # Prices
        price_container = card.select_one('span.price')

        # Check if there's a discount (look for <del> and <ins> tags)
        del_tag = price_container.select_one('del .woocommerce-Price-amount') if price_container else None
        ins_tag = price_container.select_one('ins .woocommerce-Price-amount') if price_container else None

        if del_tag and ins_tag:
            # There's a discount - extract both prices
            original_price_raw = del_tag.get_text(strip=True).replace("₪", "").replace(",", "").replace("\xa0", "")
            disc_price_raw = ins_tag.get_text(strip=True).replace("₪", "").replace(",", "").replace("\xa0", "")

            # Convert to integers (remove decimal part)
            original_price = int(float(original_price_raw)) if original_price_raw else ""
            disc_price = int(float(disc_price_raw)) if disc_price_raw else ""
        else:
            # No discount - get the regular price
            price_tag = price_container.select_one('.woocommerce-Price-amount') if price_container else None
            original_price_raw = price_tag.get_text(strip=True).replace("₪", "").replace(",", "").replace("\xa0", "") if price_tag else ""
            original_price = int(float(original_price_raw)) if original_price_raw else ""
            disc_price = ""  # No discount, so discounted price is empty

        # Product URL
        product_link_tag = card.select_one('a.woocommerce-LoopProduct-link')
        product_url = product_link_tag['href'] if product_link_tag else ""

        # Image URL (use main image)
        image_tag = card.select_one('.product-image.image-main img')
        img_url = image_tag['src'] if image_tag and 'src' in image_tag.attrs else ""

        print(firm)
        print(model)
        print(year)
        print(original_price)
        print(disc_price)
        print(img_url)
        print(product_url)


        products_data =  {
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

                # Images Gallery
                gallery_images_urls = []

                # Try first structure: slick-track div
                images_gallery = prod_soup.find('div', class_='slick-track')
                if images_gallery:
                    # Extract all image srcs from img elements inside the slick-track
                    img_elements = images_gallery.find_all('img')
                    gallery_images_urls = [img['src'] for img in img_elements if img.get('src')]

                # If no images found, try second structure: flex-control-nav ol
                if not gallery_images_urls:
                    images_gallery = prod_soup.find('ol', class_='flex-control-nav')
                    if images_gallery:
                        # Extract all image srcs from img elements inside the ol
                        img_elements = images_gallery.find_all('img')
                        gallery_images_urls = [img['src'] for img in img_elements if img.get('src')]

                products_data["gallery_images_urls"] = gallery_images_urls

                # Extract specifications from the new structure
                spec_rows = prod_soup.find_all('div', class_='Specifications__Row-sc-ki43hb-5')

                for spec_row in spec_rows:
                    # Find the title cell (key) and value cell
                    cells = spec_row.find_all('div', class_='Specifications__Cell-sc-ki43hb-6')

                    if len(cells) >= 2:
                        # First cell contains the title/key
                        key_result = extract_specs_from_image_or_text(cells[0])
                        key = handle_spec_extraction_result(key_result, products_data)
                        if key is None:  # If it was a dict, skip this iteration
                            continue
                        key = key.lower()
                        
                        # Second cell contains the value
                        value_result = extract_specs_from_image_or_text(cells[1])
                        value = handle_spec_extraction_result(value_result, products_data)
                        if value is None:  # If it was a dict, skip this iteration
                            continue

                        # Check if the value cell contains multiple specifications (separated by <br> tags)
                        if '<br>' in str(cells[1]):
                            # Split by <br> tags and process each specification
                            value_text = str(cells[1])
                            # Remove HTML tags and split by line breaks
                            value_text = value_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                            # Use BeautifulSoup to get clean text
                            clean_text = BeautifulSoup(value_text, 'html.parser').get_text()
                            
                            # Split by newlines and process each line
                            lines = clean_text.split('\n')
                            current_key = None
                            
                            for line in lines:
                                line = line.strip()
                                if line:
                                    # If this line doesn't contain a colon, it might be a key
                                    if ':' not in line and len(line) < 50:  # Likely a key
                                        current_key = line.lower()
                                    elif current_key and ':' in line:  # This is a key-value pair
                                        parts = line.split(':', 1)
                                        if len(parts) == 2:
                                            spec_key = parts[0].strip().lower()
                                            spec_value = parts[1].strip()
                                            if spec_value and len(spec_value) > 1:
                                                products_data[spec_key] = spec_value
                                                print(f"📋 Extracted multi-spec: {spec_key} = {spec_value}")
                                    elif current_key and line:  # This is a value for the current key
                                        if line not in products_data and len(line) > 1:
                                            products_data[current_key] = line
                                            print(f"📋 Extracted multi-spec: {current_key} = {line}")
                        else:
                            # Single specification (original logic)
                            if key == 'type brakemount':
                                continue
                            if key == 'min. brake rotor size (mm)':
                                continue
                            if key == 'rear Wheel MaxTravel':
                                continue
                            if key == 'number of gears':
                                continue
                            if key == 'Tyre size ETRTO':
                                continue
                            if key == 'Frame Description':
                                continue

                            # Add to products_data
                            if value and len(value) > 1:
                                products_data[key] = value
                                print(f"📋 Extracted spec: {key} = {value}")

                                # Extract specifications from tables (alternative structure)
                spec_tables = prod_soup.find_all('table', class_='spectable')
                
                for table in spec_tables:
                    # Find all rows in the table
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        # Find all cells in the row
                        cells = row.find_all('td')
                        
                        # Handle 3-column structure: icon, category, value
                        if len(cells) >= 3:
                            category_cell = cells[1]  # Second cell is specCategory
                            value_cell = cells[2]     # Third cell is specValue
                            
                            if category_cell and value_cell:
                                key_result = extract_specs_from_image_or_text(category_cell)
                                key = handle_spec_extraction_result(key_result, products_data)
                                if key is None:  # If it was a dict, skip this iteration
                                    continue
                                key = key.lower()
                                
                                value_result = extract_specs_from_image_or_text(value_cell)
                                value = handle_spec_extraction_result(value_result, products_data)
                                if value is None:  # If it was a dict, skip this iteration
                                    continue
                                
                                # Add to products_data
                                products_data[key] = value
                                print(f"📋 Extracted table spec: {key} = {value}")
                        
                        # Handle 2-column structure as fallback
                        elif len(cells) >= 2:
                            category_cell = row.find('td', class_='specCategory')
                            value_cell = row.find('td', class_='specValue')
                            
                            if category_cell and value_cell:
                                key_result = extract_specs_from_image_or_text(category_cell)
                                key = handle_spec_extraction_result(key_result, products_data)
                                if key is None:  # If it was a dict, skip this iteration
                                    continue
                                key = key.lower()
                                
                                value_result = extract_specs_from_image_or_text(value_cell)
                                value = handle_spec_extraction_result(value_result, products_data)
                                if value is None:  # If it was a dict, skip this iteration
                                    continue
                                
                                # Add to products_data
                                products_data[key] = value
                                print(f"📋 Extracted table spec: {key} = {value}")

                # Extract specifications from other table structures
                # Look for tables without specific classes
                all_tables = prod_soup.find_all('table')
                for table in all_tables:
                    if table not in spec_tables:  # Skip already processed tables
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                # First cell as key, second as value
                                key_result = extract_specs_from_image_or_text(cells[0])
                                key = handle_spec_extraction_result(key_result, products_data)
                                if key is None:  # If it was a dict, skip this iteration
                                    continue
                                key = key.lower()
                                
                                value_result = extract_specs_from_image_or_text(cells[1])
                                value = handle_spec_extraction_result(value_result, products_data)
                                if value is None:  # If it was a dict, skip this iteration
                                    continue

                                # Skip empty keys/values
                                if key and value and key not in products_data:
                                    products_data[key] = value
                                    print(f"📋 Extracted general table spec: {key} = {value}")

                # Extract specifications from div-based structures (alternative)
                spec_divs = prod_soup.find_all('div', class_='specification')
                for spec_div in spec_divs:
                    key_elem = spec_div.find(['h3', 'h4', 'strong', 'b'])
                    value_elem = spec_div.find(['p', 'span', 'div'])

                    if key_elem and value_elem:
                        key_result = extract_specs_from_image_or_text(key_elem)
                        key = handle_spec_extraction_result(key_result, products_data)
                        if key is None:  # If it was a dict, skip this iteration
                            continue
                        key = key.lower()
                        
                        value_result = extract_specs_from_image_or_text(value_elem)
                        value = handle_spec_extraction_result(value_result, products_data)
                        if value is None:  # If it was a dict, skip this iteration
                            continue

                        if key and value and key not in products_data:
                            products_data[key] = value
                            print(f"📋 Extracted div spec: {key} = {value}")
                
                # Extract specifications from figure images (specification screenshots)
                print("🔍 Looking for specification images in figures...")
                
                # Look for figure elements that might contain specification images
                figures = prod_soup.find_all('figure')
                for figure in figures:
                    # Check if the figure caption indicates it's a specification image
                    caption = figure.find('figcaption')
                    caption_text = caption.get_text().lower() if caption else ""
                    
                    # Look for specification-related keywords in caption
                    spec_keywords = ['screenshot', 'spec', 'specification', 'tech', 'technical', 'details', 'info', 'data']
                    is_spec_figure = any(keyword in caption_text for keyword in spec_keywords)
                    
                    # Also check if the figure is large enough to potentially contain specifications
                    img = figure.find('img')
                    if img:
                        img_width = img.get('width', 0)
                        img_height = img.get('height', 0)
                        try:
                            width = int(img_width)
                            height = int(img_height)
                            if width > 400 and height > 400:  # Large images might contain specs
                                is_spec_figure = True
                        except ValueError:
                            pass
                    
                    if is_spec_figure and img:
                        img_src = img.get('src', '')
                        if img_src:
                            # Handle relative URLs
                            if img_src.startswith('/'):
                                img_src = BASE_URL + img_src
                            elif not img_src.startswith('http'):
                                img_src = urljoin(BASE_URL, img_src)
                            
                            print(f"🔍 Found specification figure image: {img_src}")
                            print(f"   Caption: {caption_text}")
                            
                            # Extract specifications from the image using ChatGPT API
                            extracted_specs = extract_specs_from_image_with_chatgpt(img_src)
                            if extracted_specs:
                                print(f"✅ Extracted specifications from spec image using ChatGPT API")
                                # Merge the extracted specifications into products_data
                                for key, value in extracted_specs.items():
                                    if key and value and len(str(value)) > 1 and key not in products_data:
                                        products_data[key] = value
                                        print(f"📋 Extracted from spec image: {key} = {value}")
                            else:
                                print(f"❌ Failed to extract specifications from specification image: {img_src}")
                
                # Also look for any large images that might contain specifications
                print("🔍 Looking for other potential specification images...")
                all_images = prod_soup.find_all('img')
                for img in all_images:
                    img_src = img.get('src', '')
                    img_alt = img.get('alt', '').lower()
                    
                    # Check if this is a large image that might contain specifications
                    img_width = img.get('width', 0)
                    img_height = img.get('height', 0)
                    
                    try:
                        width = int(img_width)
                        height = int(img_height)
                        is_large_image = width > 500 and height > 500
                    except ValueError:
                        is_large_image = False
                    
                    # Check if image filename suggests it might contain specifications
                    filename_keywords = ['spec', 'tech', 'details', 'info', 'data', 'aa1', 'aa2']
                    filename = img_src.lower().split('/')[-1] if img_src else ""
                    has_spec_filename = any(keyword in filename for keyword in filename_keywords)
                    
                    if (is_large_image or has_spec_filename) and img_src:
                        # Handle relative URLs
                        if img_src.startswith('/'):
                            img_src = BASE_URL + img_src
                        elif not img_src.startswith('http'):
                            img_src = urljoin(BASE_URL, img_src)
                        
                        print(f"🔍 Found potential spec image: {img_src}")
                        
                        # Extract specifications from the image using ChatGPT API
                        extracted_specs = extract_specs_from_image_with_chatgpt(img_src)
                        if extracted_specs:
                            print(f"✅ Extracted specifications from large image using ChatGPT API")
                            # Merge the extracted specifications into products_data
                            for key, value in extracted_specs.items():
                                if key and value and len(str(value)) > 1 and key not in products_data:
                                    products_data[key] = value
                                    print(f"📋 Extracted from large image: {key} = {value}")
                
                # Extract specifications from images in anchor tags within paragraphs
                print("🔍 Looking for specification images in anchor tags...")
                
                # Look for p tags that contain anchor tags with images
                p_tags_with_images = prod_soup.find_all('p')
                for p_tag in p_tags_with_images:
                    # Find all anchor tags with images inside this p tag
                    anchor_tags = p_tag.find_all('a')
                    
                    for anchor in anchor_tags:
                        img_tag = anchor.find('img')
                        if img_tag:
                            img_src = img_tag.get('src', '')
                            img_width = img_tag.get('width', 0)
                            img_height = img_tag.get('height', 0)
                            
                            # Check if this image is large enough to contain specifications
                            try:
                                width = int(img_width)
                                height = int(img_height)
                                is_large_enough = width > 400 and height > 200  # Lower threshold for these images
                            except ValueError:
                                is_large_enough = False
                            
                            # Also check if the image filename suggests it contains specifications
                            filename = img_src.lower().split('/')[-1] if img_src else ""
                            spec_filename_keywords = ['spec', 'tech', 'details', 'info', 'data', 'aa1', 'aa2', 'b1', '1.jpg', '2.jpg', '3.jpg', '4.jpg', '5.jpg']
                            has_spec_filename = any(keyword in filename for keyword in spec_filename_keywords)
                            
                            if (is_large_enough or has_spec_filename) and img_src:
                                # Handle relative URLs
                                if img_src.startswith('/'):
                                    img_src = BASE_URL + img_src
                                elif not img_src.startswith('http'):
                                    img_src = urljoin(BASE_URL, img_src)
                                
                                print(f"🔍 Found specification image in anchor tag: {img_src}")
                                print(f"   Dimensions: {img_width}x{img_height}")
                                
                                # Extract specifications from the image using ChatGPT API
                                extracted_specs = extract_specs_from_image_with_chatgpt(img_src)
                                if extracted_specs:
                                    print(f"✅ Extracted specifications from anchor image using ChatGPT API")
                                    # Merge the extracted specifications into products_data
                                    for key, value in extracted_specs.items():
                                        if key and value and len(str(value)) > 1 and key not in products_data:
                                            products_data[key] = value
                                            print(f"📋 Extracted from anchor image: {key} = {value}")
                                else:
                                    print(f"❌ Failed to extract specifications from anchor image: {img_src}")
                
                # Extract specifications from sectionx div structure
                print("🔍 Looking for specifications in sectionx divs...")
                
                # Look for div elements with class "sectionx"
                sectionx_divs = prod_soup.find_all('div', class_='sectionx')
                for sectionx in sectionx_divs:
                    # Find all p tags in this sectionx div
                    p_tags = sectionx.find_all('p')
                    
                    if len(p_tags) >= 2:
                        # First p tag should contain the strong tag (key)
                        first_p = p_tags[0]
                        strong_tag = first_p.find('strong')
                        
                        # Second p tag should contain the value
                        second_p = p_tags[1]
                        
                        if strong_tag and second_p:
                            key = strong_tag.get_text(strip=True).lower()
                            value = second_p.get_text(strip=True)
                            
                            # Skip if the value is the same as the key or empty
                            if value != key and len(value) > 1:
                                # Skip if this key already exists (avoid duplicates)
                                if key not in products_data:
                                    products_data[key] = value
                                    print(f"📋 Extracted from sectionx: {key} = {value}")
                
                # Also look for any div with strong tags that might contain specifications
                print("🔍 Looking for other strong tag specifications...")
                all_strong_tags = prod_soup.find_all('strong')
                for strong_tag in all_strong_tags:
                    # Get the key from the strong tag
                    key = strong_tag.get_text(strip=True).lower()
                    
                    # Look for the value in the next sibling or parent's next sibling
                    value = ""
                    
                    # Try to find value in the next sibling p tag
                    next_sibling = strong_tag.find_next_sibling('p')
                    if next_sibling:
                        value = next_sibling.get_text(strip=True)
                    
                    # If no next sibling, try to find it in the parent's next sibling
                    if not value and strong_tag.parent:
                        parent_next = strong_tag.parent.find_next_sibling()
                        if parent_next:
                            p_tag = parent_next.find('p')
                            if p_tag:
                                value = p_tag.get_text(strip=True)
                    
                    # If we found a value and it's not the same as the key
                    if value and value != key and len(value) > 1:
                        # Skip if this key already exists
                        if key not in products_data:
                            products_data[key] = value
                            print(f"📋 Extracted from strong tag: {key} = {value}")

                # Extract specifications from the new div structure with Specifications__Row-sc-ki43hb-5
                print("🔍 Looking for specifications in new div structure...")
                
                # Look for div elements with the new class structure
                new_spec_rows = prod_soup.find_all('div', class_='Specifications__Row-sc-ki43hb-5')
                
                for spec_row in new_spec_rows:
                    # Find all cells in this row
                    cells = spec_row.find_all('div', class_='Specifications__Cell-sc-ki43hb-6')
                    
                    if len(cells) >= 2:
                        # First cell contains the title/key
                        title_cell = cells[0]
                        value_cell = cells[1]
                        
                        key = title_cell.get_text(strip=True).lower()
                        value = value_cell.get_text(strip=True)
                        
                        # Check if the value cell contains multiple specifications (separated by <br> tags)
                        if '<br>' in str(value_cell):
                            # Split by <br> tags and process each specification
                            value_text = str(value_cell)
                            # Remove HTML tags and split by line breaks
                            value_text = value_text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                            # Use BeautifulSoup to get clean text
                            clean_text = BeautifulSoup(value_text, 'html.parser').get_text()
                            
                            # Split by newlines and process each line
                            lines = clean_text.split('\n')
                            current_key = None
                            
                            for line in lines:
                                line = line.strip()
                                if line:
                                    # If this line doesn't contain a colon and is short, it might be a key
                                    if ':' not in line and len(line) < 50:  # Likely a key
                                        current_key = line.lower()
                                    elif current_key and ':' in line:  # This is a key-value pair
                                        parts = line.split(':', 1)
                                        if len(parts) == 2:
                                            spec_key = parts[0].strip().lower()
                                            spec_value = parts[1].strip()
                                            if spec_value and len(spec_value) > 1:
                                                products_data[spec_key] = spec_value
                                                print(f"📋 Extracted new div multi-spec: {spec_key} = {spec_value}")
                                    elif current_key and line:  # This is a value for the current key
                                        if line not in products_data and len(line) > 1:
                                            products_data[current_key] = line
                                            print(f"📋 Extracted new div multi-spec: {current_key} = {line}")
                        else:
                            # Single specification
                            if value and len(value) > 1 and key not in products_data:
                                products_data[key] = value
                                print(f"📋 Extracted new div spec: {key} = {value}")

            except Exception as e:
                print(f"⚠️ Error scraping product page ({product_url}): {e}")

        # Translate Hebrew keys to English keys
        products_data = translate_hebrew_keys(products_data)
        
        # Validate the scraped data to detect malformed entries
        # Check for extremely long keys that indicate concatenated data
        malformed_entry = False
        for key, value in products_data.items():
            if len(key) > 100:  # If any key is longer than 100 characters, it's likely malformed
                print(f"⚠️ Detected malformed entry with long key: {key[:50]}...")
                malformed_entry = True
                break
        
        if malformed_entry:
            print(f"❌ Skipping malformed entry for product: {products_data.get('model', 'Unknown')}")
            continue  # Skip this entry and continue with the next product

        
        # Check if fork information is available (required for sub-category classification)
        if not products_data.get("fork"):
            print(f"⚠️ Warning: No fork information found for {products_data.get('model', 'Unknown')}")

        # Extract Wh from battery value - try multiple sources
        battery_value = products_data.get("battery", "")
        wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)

        # Extract Wh from battery value
        if wh_match:
            wh_value = int(wh_match.group(1))  # Convert to int if needed
            products_data["wh"] = wh_value
            print(f"🔋 Found Wh in battery field: {wh_value}Wh")
        else:
            # If no 'Wh' found in battery, try to find a 3-digit number in battery field
            fallback_match = re.search(r"\b(\d{3})\b", battery_value)
            if fallback_match:
                products_data["wh"] = int(fallback_match.group(1))
                print(f"🔋 Found 3-digit number in battery field: {fallback_match.group(1)}Wh")
            else:
                # If not found in battery, search in motor field
                motor_value = products_data.get("motor", "")
                motor_wh_match = re.search(r"(\d+)\s*Wh", motor_value, re.IGNORECASE)
                if motor_wh_match:
                    wh_value = int(motor_wh_match.group(1))
                    products_data["wh"] = wh_value
                    print(f"🔋 Found Wh in motor field: {wh_value}Wh")
                else:
                    # If not found in motor, search for "battery watts per hour" in any field
                    battery_watts_found = False
                    for key, value in products_data.items():
                        if isinstance(value, str) and "battery watts per hour" in value.lower():
                            watts_match = re.search(r"(\d+)", value)
                            if watts_match:
                                wh_value = int(watts_match.group(1))
                                products_data["wh"] = wh_value
                                print(f"🔋 Found battery watts per hour in {key} field: {wh_value}Wh")
                                battery_watts_found = True
                                break
                    
                    if not battery_watts_found:
                        print(f"⚠️ Could not find Wh information for {products_data.get('model', 'Unknown')}")
                        products_data["wh"] = None

        #---fork length----
        fork_text = products_data.get("fork", "") or products_data.get("front fork", "")
        print(f"DEBUG: fork_text = '{fork_text}'")
        
        if fork_text:  # Only try to extract if fork data exists
            match = re.search(r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
            if match:
                fork_length = match.group(1)
                products_data["fork length"] = int(fork_length)
            else:
                print(f"⚠️ Could not extract fork length from: '{fork_text}'")
                products_data["fork length"] = None
        else:
            print(f"⚠️ No fork information available for {products_data.get('model', 'Unknown')}")
            products_data["fork length"] = None

        #----sub-category----
        fork_length_str = products_data.get("fork length")

        if fork_length_str is not None:
            try:
                fork_length = int(fork_length_str)
                if fork_length == 120:
                    products_data["sub-category"] = "cross-country"
                elif fork_length in [130, 140, 150]:
                    products_data["sub-category"] = "trail"
                elif fork_length in [160, 170, 180]:
                    products_data["sub-category"] = "enduro"
                else:
                    print(f"⚠️ Unexpected fork length value: {fork_length}")
                    products_data["sub-category"] = "unknown"
            except ValueError as e:
                print(f"⚠️ Invalid fork length '{fork_length_str}': {e}")
                products_data["sub-category"] = "unknown"
        else:
            products_data["sub-category"] = "unknown"

        scraped_data.append(products_data)

    return scraped_data


if __name__ == "__main__":
    # Only run the scraper if this file is executed directly
    driver = uc.Chrome()
    products = ofanaim_bikes(driver)
    driver.quit()

    # Save to JSON
    import os
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scraped_raw_data')
    output_file = os.path.join(output_dir, "ofanaim.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

    print(f"\n✅ All data saved to {output_file}")

