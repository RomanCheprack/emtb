import time
import re
import json
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from openai import OpenAI
from dotenv import load_dotenv

# -------------------------------
# Setup
# -------------------------------
BASE_URL = "https://www.rosen-meents.co.il"

ROSEN_TARGET_URLS = [
    {"url": f"{BASE_URL}/אופני-הרים-חשמליים-E-MTB", "category": "electric", "sub_category": "electric_mtb"},
    {"url": f"{BASE_URL}/index.php?dir=site&page=catalog&op=category&cs=10001&range=0%2C48442&filter%5B10005%5D%5B%5D=12673&filter%5B10271%5D%5B%5D=19115&filter%5B10271%5D%5B%5D=15275&filter%5B10271%5D%5B%5D=14858", "category": "mtb", "sub_category": "hardtail"},
    {"url": f"{BASE_URL}/אופני-הרים-שיכוך-מלא", "category": "mtb", "sub_category": "full_suspension"},
    {"url": f"{BASE_URL}/index.php?dir=site&page=catalog&op=category&cs=10002&range=0%2C73990&filter%5B10038%5D%5B%5D=22064", "category": "gravel", "sub_category": "gravel"},
    {"url": f"{BASE_URL}/אופני-כביש", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/אופני-כביש-EROAD", "category": "electric", "sub_category": "electric_road"},
    {"url": f"{BASE_URL}/index.php?dir=site&page=catalog&op=category&cs=10002&range=0%2C68159&filter%5B10038%5D%5B%5D=26702", "category": "electric", "sub_category": "electric_gravel"},
    {"url": f"{BASE_URL}/אופני-עיר", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/אופניים-מתקפלים", "category": "city", "sub_category": "folding_bike"},
    {"url": f"{BASE_URL}/אופני-הרים-לילדים", "category": "kids", "sub_category": "kids"},
]


# Load .env from project root, then read API key
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')
client = OpenAI(api_key=CHATGPT_API_KEY) if CHATGPT_API_KEY else None

# Hebrew to English key mapping
HEBREW_TO_ENGLISH_KEYS = {
    "צבע": "color",
    "שלדה": "frame",
    "מידות": "sizes",
    "גימור / צבע": "finish_color",
    "בולם זעזועים קדמי": "fork",
    "בולם זעזועים אחורי": "rear_shock",
    "מערכת הינע": "drive_system",
    "הילוכים": "gears",
    "מעביר קדמי": "front_derailleur",
    "מעביר אחורי": "rear_derailleur",
    "מעבירי הילוכים (שיפטר)": "shifters",
    "קראנק": "crankset",
    "מעצורים": "brakes",
    "חישוקים": "rims",
    "צירי גלגל": "hubs",
    "סטם": "stem",
    "כידון": "handlebar",
    "מוט אוכף": "seatpost",
    "אוכף": "saddle",
    "דוושות (פדלים)": "pedals",
    "צמיגים": "tires",
    "סוללה": "battery",
    "מטען": "charger",
    "משקל": "weight",
    "טווח": "range",
    "מהירות": "speed",
    "כוח": "power"
}

scraped_data = []

# -------------------------------
# Helpers
# -------------------------------
def translate_hebrew_keys(specs_dict):
    translated_specs = {}
    for key, value in specs_dict.items():
        if key in HEBREW_TO_ENGLISH_KEYS:
            translated_specs[HEBREW_TO_ENGLISH_KEYS[key]] = value
        else:
            translated_specs[key] = value
    return translated_specs

def clean_model_name(model_name):
    """
    Clean model names by removing unwanted characters, Hebrew text, and extra spaces
    while preserving the actual model name.
    """
    if not model_name:
        return model_name
    
    # Create a copy to work with
    cleaned = model_name.strip()
    
    # Remove Hebrew characters and words that are not part of the model name
    hebrew_words_to_remove = [
        r'["ק]+',  # Hebrew quotes and other Hebrew characters
        r'נש',     # Hebrew word for "women's"
        r'תחרותי', # Hebrew word for "competitive"
        r'מרתון',  # Hebrew word for "marathon"
        r'שביל',   # Hebrew word for "trail"
        r'שיכוך מלא', # Hebrew phrase for "full suspension"
        r'ש["\\]?מ',    # Hebrew abbreviation (with different quote types)
        r'מ["\\]?מ',    # Hebrew abbreviation for millimeters
        r'שמ\s*',     # Hebrew abbreviation (without quotes)
    ]
    
    for pattern in hebrew_words_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Remove measurement patterns like "140150 מ\"מ" or "160170 מ\"מ"
    cleaned = re.sub(r'\d+\d+\s*מ["\\]?מ', '', cleaned)
    
    # Remove standalone measurement numbers like "140150" or "160170" at the beginning
    cleaned = re.sub(r'^\d{6}\s+', '', cleaned)
    
    # Remove "NEW" at the beginning (case insensitive)
    cleaned = re.sub(r'^NEW\s+', '', cleaned, flags=re.IGNORECASE)
    
    # Remove extra quotes and punctuation at the beginning
    cleaned = re.sub(r'^["\'\s]+', '', cleaned)
    cleaned = re.sub(r'["\'\s]+$', '', cleaned)
    
    # Remove extra spaces and clean up spacing
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove standalone numbers that appear to be measurements or codes
    # Keep numbers that are part of model names (like "475", "A70", "XC")
    # Remove standalone 4-digit numbers that might be codes (like "3000", "5000")
    cleaned = re.sub(r'\b\d{4}\b(?=\s*$)', '', cleaned)
    
    # Remove common unwanted patterns
    unwanted_patterns = [
        r'\be-MTB\b',  # Remove "e-MTB" suffix
        r'\bEMTB\b',   # Remove "EMTB" suffix
        r'\bXC\b(?=\s*$)',  # Remove "XC" at the end
        r'\bENDURO\b(?=\s*$)',  # Remove "ENDURO" at the end
    ]
    
    for pattern in unwanted_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up any remaining extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Remove trailing commas and periods
    cleaned = re.sub(r'[,\.]+$', '', cleaned)
    
    # Final cleanup - remove any remaining unwanted characters
    # Keep alphanumeric, spaces, hyphens, and dots
    cleaned = re.sub(r'[^\w\s\-\.]', '', cleaned)
    
    # Clean up multiple spaces again
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def clean_product_data(product_data):
    """
    Clean product data by removing unwanted keys and flattening nested objects
    
    Removes:
    - _raw_specs_text: Raw text from GPT parsing (for debugging only)
    - system_weight_limit: System weight limit information
    
    Flattens nested objects by joining values with commas:
    - hubs: front/rear hub information
    - tires/tyre: front/rear tire information  
    - shifters: front/rear shifter information
    - derailleur: derailleur information
    - light: front/rear light information
    - handlebar: handlebar specifications
    - stem: stem specifications
    - seatpost: seatpost specifications
    - saddle: saddle specifications
    - sizes: size information (flatten complex geometry objects)
    
    Removes geometry-related keys that contain detailed measurements
    
    Returns cleaned product data dictionary
    """
    # Keys to remove completely
    keys_to_remove = ["_raw_specs_text", "system_weight_limit", "frame_specifications"]
    
    # Geometry-related keys to remove (detailed measurements)
    geometry_keys_to_remove = [
        "seat_tube", "top_tube", "chain_stay_length", "head_tube_angle", 
        "seat_tube_angle", "bottom_bracket_drop", "head_tube", "fork_length",
        "reach", "stack", "wheel_base", "stand_over_height", "tyre_sizes",
        "size", "sizes", "rider_height_cm", "wheelbase_mm", "seat_angle",
        "stack_mm", "trail_mm", "rear_center_mm", "pad_reach_v_cockpit_mm",
        "reach_mm", "pad_stack_v_cockpit_mm", "head_angle", "bb_drop_mm",
        "pad_stack_flat_cockpit_mm", "stem_length_mm", "saddle_height_range",
        "seat_tube_mm", "stem_angle", "post_offset_mm", "crank_length_mm",
        "fork_rake_mm", "front_center_mm", "pad_reach_flat_cockpit_mm",
        "base_bar_drop_v_cockpit_mm", "base_bar_reach_v_cockpit_mm",
        "fork_length_mm", "base_bar_drop_flat_cockpit_mm", "base_bar_reach_flat_cockpit_mm",
        "מידות", "גודל", "גובה רוכב", "מרחק גלגלים", "זווית מושב",
        "גובה מושב", "מסלול", "מרכז אחורי", "הישג", "זווית ראש",
        "נפילת ברכיים", "אורך גזע", "טווח גובה אוכף", "אורך צינור מושב",
        "זווית גזע", "אופסט פוסט", "אורך קראנק", "מסלול מזלג",
        "מרכז קדמי", "נפילת בר", "הישג בר", "אורך מזלג", "additional_information",
        # Additional geometry keys found in the data
        "bar_rise", "bar_sweep", "bar_width", "bb_drop", "crank_length",
        "fork_rake", "front_center", "rear_center", "wheelbase", "trail",
        "stem_length", "seatpost_drop", "standover_height", "rider_height"
    ]
    
    # Clean the specs section if it exists
    if "specs" in product_data and isinstance(product_data["specs"], dict):
        cleaned_specs = {}
        for key, value in product_data["specs"].items():
            # Skip if key is in removal lists
            if key in keys_to_remove or key in geometry_keys_to_remove:
                continue
            
            # Skip if key contains geometry-related terms
            key_lower = key.lower()
            geometry_terms = ["mm", "angle", "reach", "stack", "drop", "length", "height", "range", "offset"]
            if any(term in key_lower for term in geometry_terms):
                continue
                
            cleaned_specs[key] = value
    
    # Flatten nested objects by joining values with commas
    keys_to_flatten = [
        "hubs", "tires", "tyre", "shifters", "derailleur", "light",
        "handlebar", "stem", "seatpost", "saddle"
    ]
    
    for key in keys_to_flatten:
        if key in cleaned_specs and isinstance(cleaned_specs[key], dict):
            # Join all values with commas
            values = []
            for sub_key, sub_value in cleaned_specs[key].items():
                if isinstance(sub_value, str):
                    values.append(f"{sub_key}: {sub_value}")
                else:
                    values.append(f"{sub_key}: {str(sub_value)}")
            cleaned_specs[key] = ", ".join(values)
    
    # Special handling for sizes - if it's a complex object with geometry, simplify it
    if "sizes" in cleaned_specs and isinstance(cleaned_specs["sizes"], dict):
        # Check if it's a complex geometry object (has nested objects with measurements)
        size_values = []
        for size_key, size_data in cleaned_specs["sizes"].items():
            if isinstance(size_data, dict):
                # This is a complex geometry object, just keep the size name
                size_values.append(size_key)
            else:
                # This is a simple size value
                size_values.append(f"{size_key}: {size_data}")
        cleaned_specs["sizes"] = ", ".join(size_values)
        
        # Update the specs in the product data
        product_data["specs"] = cleaned_specs
    
    return product_data


# Kids bike wheel sizes (inches)
KIDS_WHEEL_SIZE_PATTERN = re.compile(
    r'\b(12|14|16|18|20|24|26)\b|'
    r'(12|14|16|18|20|24|26)(?:x|\"| inch| אינץ)'
)

def extract_wheel_size_from_text(text):
    """Extract kids bike wheel sizes (12, 14, 16, 18, 20, 24, 26) from text. Returns list of ints."""
    if not text:
        return []
    matches = KIDS_WHEEL_SIZE_PATTERN.findall(str(text))
    result = []
    for m in matches:
        val = m if isinstance(m, str) else next((x for x in m if x), None)
        if val and int(val) not in result:
            result.append(int(val))
    return result

def extract_wheel_size_for_kids_bike(model, specs):
    """
    Extract wheel size for kids bikes. Returns int or None.
    - First try model name for single match
    - If multiple matches in model or no match, check specs (wheels, rims, front_tire, rear_tire, tires)
    """
    model_matches = extract_wheel_size_from_text(model or "")

    if len(model_matches) == 1:
        return model_matches[0]

    wheel_related_keys = ["wheels", "rims", "front_tire", "rear_tire", "tires"]
    for key in wheel_related_keys:
        val = specs.get(key) if specs else None
        if val:
            matches = extract_wheel_size_from_text(val)
            if matches:
                return matches[0]

    if model_matches:
        return model_matches[0]

    return None


# -------------------------------
# ChatGPT Description Rewriter
# -------------------------------
def rewrite_description_with_chatgpt(original_text, api_key):
    """Rewrite product description using ChatGPT API"""
    if not original_text:
        print("⚠️ Warning: No text provided for ChatGPT rewriting")
        return original_text
    
    if not api_key:
        print("⚠️ Warning: No API key provided for ChatGPT rewriting")
        return original_text
    
    try:
        print(f"🤖 Sending description to ChatGPT for rewriting... (API key: {api_key[:20]}...)")
        
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
        
        print("✅ Description successfully rewritten by ChatGPT")
        return rewritten_text
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling ChatGPT API: {e}")
        return original_text

# -------------------------------
# Old Extractors (fallbacks)
# -------------------------------
def extract_specs_p_br(soup):
    specs = {}
    paragraphs = soup.find_all("p")
    for p in paragraphs:
        parts = [line.strip() for line in p.decode_contents().split("<br>") if line.strip()]
        for part in parts:
            clean = BeautifulSoup(part, "html.parser").get_text().strip()
            if ":" in clean:
                key, value = clean.split(":", 1)
                specs[key.strip()] = value.strip()
            elif specs:
                last_key = list(specs.keys())[-1]
                specs[last_key] += " " + clean
    return specs

def extract_specs_table(soup):
    specs = {}
    spec_table = soup.find("table", class_="table")
    if spec_table:
        tbody = spec_table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    if key and val:
                        specs[key] = val
    return specs

# Known spec keys for Format 1 parsing (longest first for correct matching)
SPEC_KEYS_ORDERED = [
    "handlebar stem", "frame size", "derailleur (r)", "seat post", "seat clamp",
    "tyre front", "tyre rear", "light front", "light rear", "drive unit", "approx. weight",
    "frame", "color", "fork", "shock", "brakes", "rotors", "headset", "handlebar",
    "grip", "shifters", "saddle", "pedal", "chain", "chainwheel", "crank", "freewheel",
    "hubs", "rim", "axles", "spokes", "fender", "battery", "display", "weighed",
]

KEY_REMAP = {
    "derailleur (r)": "rear_derailleur",
    "shock": "rear_shock",
    "seat post": "seatpost",
    "seat clamp": "seat_clamp",
    "approx. weight": "weight",
    "drive unit": "drive_system",
    "color": "finish_color",
}

def _remap_key(key):
    """Normalize a spec key to snake_case standard."""
    k = key.strip()
    low = k.lower()
    if low in KEY_REMAP:
        return KEY_REMAP[low]
    if "derailleur" in low and ("r)" in low or low.startswith("rear")):
        return "rear_derailleur"
    return k


# ── Format 1: <p dir="ltr"> + <ul dir="ltr"> (Merida bikes) ──────────────
def _parse_format1_p_ul(container):
    """Parse <p>key value</p> optionally followed by <ul><li>...</li></ul>."""
    specs = {}
    elements = container.find_all(["p", "ul"], recursive=True)
    i = 0
    while i < len(elements):
        el = elements[i]
        if el.name == "p":
            text = el.get_text(separator=" ", strip=True).replace("\xa0", " ")
            if not text or len(text) < 3:
                i += 1
                continue
            key = None
            value = text
            for k in SPEC_KEYS_ORDERED:
                if text.lower().startswith(k.lower()):
                    key = k
                    value = text[len(k):].strip()
                    break
            if not key:
                parts = text.split(None, 1)
                if len(parts) >= 2:
                    key = parts[0]
                    value = parts[1]
                else:
                    i += 1
                    continue
            if i + 1 < len(elements) and elements[i + 1].name == "ul":
                li_items = [li.get_text(strip=True) for li in elements[i + 1].find_all("li")]
                if li_items:
                    value = (value + " | " + " | ".join(li_items)) if value else " | ".join(li_items)
                i += 1
            specs[_remap_key(key)] = value.strip()
        i += 1
    return specs


# ── Format 2: <table class="table ..."> (SCOR/BMC) ───────────────────────
def _parse_format2_table(table):
    """Parse a 2-column spec table: <td>key</td><td>value</td>."""
    specs = {}
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True)
            val = cells[1].get_text(strip=True)
            if key and val and val != "\xa0":
                specs[_remap_key(key)] = val
    return specs


# ── Format 3: <h4>Section</h4> <p><strong>Key:</strong><br/>Value</p> ────
def _parse_format3_strong_br(container):
    """Parse <strong>Key:</strong> or <strong>KEY</strong> followed by value text."""
    specs = {}
    skip_keys = {"spec", "specs", "specification", "specifications"}
    for p in container.find_all("p"):
        strong = p.find("strong")
        if not strong:
            continue
        key = strong.get_text(strip=True).rstrip(":").strip()
        if not key or key.lower() in skip_keys:
            continue
        full_text = p.get_text(separator="\n", strip=True)
        value = full_text.replace(strong.get_text(strip=True), "", 1).strip()
        value = value.lstrip(":").strip()
        if value and value != "\xa0":
            specs[_remap_key(key)] = value
    return specs


# ── Format 4: <ul><li><h3>KEY</h3>value<br/>• detail</li></ul> (BMC/SCOR) ──
def _parse_format4_li_h3(container):
    """Parse <li><h3>KEY</h3>value text</li> structure."""
    specs = {}
    skip_keys = {"spec", "specs", "specification", "specifications"}
    for li in container.find_all("li"):
        h3 = li.find("h3")
        if not h3:
            continue
        key = h3.get_text(strip=True)
        if not key or key.lower() in skip_keys:
            continue
        full_text = li.get_text(separator="\n", strip=True)
        value = full_text.replace(key, "", 1).strip()
        value = value.replace("•", "|").strip().strip("|").strip()
        if value:
            specs[_remap_key(key)] = value
    return specs


def _find_spec_tab_pane(soup):
    """Find the specific 'מפרט' (specs) tab pane inside the tab-content container.
    Returns the tab-pane div, or None if not found."""
    # Find tab nav links to get the href of the specs tab
    for link in soup.find_all("a", {"data-toggle": "tab"}):
        link_text = link.get_text(strip=True)
        if "מפרט" in link_text:
            href = link.get("href", "")
            if href.startswith("#"):
                tab_id = href[1:]
                pane = soup.find("div", id=tab_id)
                if pane:
                    return pane
    return None


def _detect_and_parse(container):
    """Detect which HTML format is used and parse accordingly. Returns dict."""
    if not container:
        return {}

    # Format 2: table
    table = container.find("table", class_=lambda c: c and "table" in c)
    if table:
        specs = _parse_format2_table(table)
        if specs:
            return specs

    # Format 4: <li><h3>KEY</h3>value</li> (BMC/SCOR)
    h3_in_li = container.find_all("h3")
    h3_with_li = [h for h in h3_in_li if h.parent and h.parent.name == "li"]
    if len(h3_with_li) >= 3:
        specs = _parse_format4_li_h3(container)
        if specs:
            return specs

    # Format 3: <strong>Key</strong> or <strong>Key:</strong>
    strongs = container.find_all("strong")
    spec_strongs = [s for s in strongs if len(s.get_text(strip=True)) >= 3]
    if len(spec_strongs) >= 3:
        specs = _parse_format3_strong_br(container)
        if specs:
            return specs

    # Format 1: <p> + <ul> (Merida-style)
    ps = container.find_all("p", attrs={"dir": "ltr"})
    if ps:
        specs = _parse_format1_p_ul(container)
        if specs:
            return specs

    # Format 1 without dir="ltr" (some pages)
    specs = _parse_format1_p_ul(container)
    if specs:
        return specs

    return {}


_JUNK_KEYS = {
    "_raw_specs_text", "system_weight_limit", "sizes", "size",
    "מידות", "גודל", "frame_specifications",
    "ניתן", "לרכישה", "המוצר", "זמין", "לא",
    "short_description", "short_description_en_gb",
    "astm_classification", "tubeless_information", "tire_clearance",
    "marketing_color", "model_name", "gender", "category",
    "number_of_gears",
}
_JUNK_VALUE_MARKERS = ["₪", "סניף", "מלאי", "לחץ כאן", "checkbox"]

# Normalize GPT output keys to match the canonical names used across all scrapers
_KEY_NORMALIZE = {
    # Fork
    "front_suspension": "fork",
    "front suspension": "fork",
    # Rear shock
    "rear_suspension": "rear shock",
    "shock": "rear_shock",
    "rear suspension": "rear_shock",
    # Motor
    "drive_unit": "motor",
    "drive unit": "motor",
    "drive_system": "motor",
    "drive system": "motor",
    # Battery
    "battery_pack": "battery",
    "battery pack": "battery",
    # Display / control
    "drive_unit_control": "display",
    "drive unit control": "display",
    # Brakes
    "front_brake": "brakes",
    "rear_brake": "brakes",
    "brake": "brakes",
    "brake_levers": "brakes",
    "brake levers": "brakes",
    "brake_levers_calipers": "brakes",
    "brake levers / calipers": "brakes",
    # Rotors
    "rotor": "rotors",
    "rotor_size": "rotors",
    "rotor_size_f_r": "rotors",
    "rotor size (f/r)": "rotors",
    # Grips
    "grip": "grips",
    "grips_tape": "grips",
    "grips / tape": "grips",
    "grips_bar_tape": "grips",
    # Tires
    "tire": "tires",
    "tyres": "tires",
    "tyre": "tires",
    "tyre_front": "front_tire",
    "tyre front": "front_tire",
    "tyre_rear": "rear_tire",
    "tyre rear": "rear_tire",
    # Cassette
    "freewheel": "cassette",
    "sprocket": "cassette",
    "cassette_size": "cassette",
    # Crankset
    "crank": "crankset",
    "cranks": "crankset",
    # Chainring
    "chainwheel": "chainring",
    "chainrings": "chainring",
    "chain_ring": "chainring",
    # Rims
    "rim": "rims",
    "wheels": "rims",
    "wheelset": "rims",
    # Hubs
    "hub": "hubs",
    "hub_front": "hubs",
    "hub_rear": "hubs",
    "front_hub": "hubs",
    "rear_hub": "hubs",
    "hubs_f_r": "hubs",
    "hubs_(f/r)": "hubs",
    "hubs (f/r)": "hubs",
    # Seatpost
    "seat_post": "seatpost",
    "seat post": "seatpost",
    # Pedals
    "pedal": "pedals",
    # Color
    "color": "finish_color",
    "colours": "finish_color",
    "colors": "finish_color",
    # Lights
    "front_light": "lights",
    "rear_light": "lights",
    "light_front": "lights",
    "light_rear": "lights",
    # Shifter
    "shifter": "shifters",
    # Front derailleur
    "front derailleur": "front_derailleur",
    # Rear derailleur
    "rear derailleur": "rear_derailleur",
    "derailleur": "rear_derailleur",
    # Seat clamp
    "seat clamp": "seat_clamp",
    # Frame size
    "frame size": "frame_size",
    # Weight
    "approx_weight": "weight",
    "approx. weight": "weight",
}


def _normalize_key(key):
    """Normalize a spec key to the canonical name."""
    k = key.strip()
    low = k.lower().replace(" ", "_")
    # Exact match (case-insensitive, underscore-normalized)
    for src, dst in _KEY_NORMALIZE.items():
        if low == src.lower().replace(" ", "_"):
            return dst
    # Partial matches for common patterns
    if "derailleur" in low and ("rear" in low or "(r)" in low):
        return "rear_derailleur"
    if "derailleur" in low and "front" in low:
        return "front_derailleur"
    return k


def _clean_specs(specs):
    """Normalize keys, remove junk, translate Hebrew. Returns clean dict."""
    translated = translate_hebrew_keys(specs)
    cleaned = {}
    for k, v in translated.items():
        if not isinstance(v, str):
            continue
        nk = _normalize_key(k)
        if nk.lower().replace(" ", "_") in _JUNK_KEYS:
            continue
        if any(m in v for m in _JUNK_VALUE_MARKERS):
            continue
        # Merge values when the same canonical key appears multiple times
        if nk in cleaned:
            cleaned[nk] = cleaned[nk] + " | " + v.strip()
        else:
            cleaned[nk] = v.strip()
    return cleaned


def _has_hebrew_keys(specs, threshold=0.5):
    """Check if more than threshold fraction of spec keys contain Hebrew."""
    if not specs:
        return False
    hebrew_count = sum(1 for k in specs.keys() if any('\u0590' <= c <= '\u05ff' for c in k))
    return hebrew_count / len(specs) > threshold


_GPT_SYSTEM = (
    "You extract bicycle specifications from HTML into a flat JSON object. "
    "Output ONLY spec key-value pairs as JSON. No nested objects."
)

_GPT_PROMPT = (
    "Extract all bicycle component specifications from this HTML.\n\n"
    "RULES:\n"
    "1. Output a flat JSON object with snake_case English keys.\n"
    "2. Each key = one component. Each value = a string describing that component.\n"
    "3. When a component (e.g. <p>frame ...</p>) is followed by sub-items "
    "(<ul><li>material: carbon</li><li>160mm travel</li></ul>), "
    "JOIN the main value and ALL sub-items with ' | '.\n"
    "   Example: \"frame\": \"eONE-SIXTY SL CF4 I | material: carbon | 160mm suspension travel\"\n"
    "4. Standard keys to use when applicable: frame, fork, rear_shock, brakes, rotors, "
    "headset, handlebar, stem, grip, rear_derailleur, front_derailleur, shifters, "
    "crankset, chain, cassette, seatpost, saddle, pedals, hubs, rims, "
    "tires, front_tire, rear_tire, spokes, axles, weight, "
    "motor, battery, display, charger, lights, fender, finish_color, frame_size.\n"
    "5. If keys are in Hebrew, translate them to English.\n"
    "6. Ignore: prices (₪), stock availability, store locations, geometry measurements "
    "(wheelbase, stack, reach, seat angle, head angle, rider height).\n"
    "7. Keep values exactly as they appear - don't invent or guess.\n\n"
    "HTML:\n"
)


def _gpt_extract_specs(html_content):
    """Use GPT to extract specs from arbitrary HTML."""
    if not html_content or not CHATGPT_API_KEY or not client:
        return {}
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _GPT_SYSTEM},
                {"role": "user", "content": _GPT_PROMPT + html_content[:8000]}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ GPT spec extraction failed: {e}")
        return {}


# -------------------------------
# Main spec extractor
# -------------------------------
def _get_spec_html(soup):
    """Find the best HTML container for specs. Returns (html_string, source_label)."""
    # Priority 1: Specific "מפרט" tab pane
    spec_pane = _find_spec_tab_pane(soup)
    if spec_pane:
        html = spec_pane.decode_contents().strip()
        if len(html) > 50:
            return html, "מפרט tab"

    # Priority 2: Tab-content (skip geometry panes)
    tab_content = soup.find("div", class_="tab-content tab-content-product-item")
    if tab_content:
        geometry_words = {"rider height", "wheelbase", "seat angle", "head angle",
                          "top tube", "stack mm", "reach mm", "seat tube"}
        for pane in tab_content.find_all("div", class_="tab-pane"):
            pane_text = pane.get_text().lower()
            if any(g in pane_text for g in geometry_words):
                continue
            html = pane.decode_contents().strip()
            if len(html) > 100:
                return html, "tab-pane"

    # Priority 3: Product description area
    desc_div = (
        soup.find("div", class_="product-item-content text-toggle")
        or soup.find("div", class_="product-item-content")
        or soup.find("div", class_=lambda c: c and isinstance(c, list)
                     and "product-item-content" in c)
    )
    if desc_div:
        html = desc_div.decode_contents().strip()
        if len(html) > 50:
            return html, "description"

    return "", ""


def extract_product_specifications(driver, product_url):
    if not product_url:
        return {}

    try:
        print(f"🔍 Extracting specs from: {product_url}")
        driver.get(product_url)
        time.sleep(3)

        # Click the specs tab ("מפרט") to make its content visible/loaded
        try:
            specs_tab = driver.find_element(By.XPATH, "//a[contains(text(), 'מפרט')]")
            specs_tab.click()
            time.sleep(2)
        except Exception:
            pass

        soup = BeautifulSoup(driver.page_source, "html.parser")

        if "404" in driver.title:
            print("⚠️ Page not found (404)")
            return {}

        spec_html, source = _get_spec_html(soup)
        if not spec_html:
            print("⚠️ No spec container found")
            return {}

        # PRIMARY: GPT extraction (handles all formats reliably)
        gpt_specs = _gpt_extract_specs(spec_html)
        if gpt_specs:
            cleaned = _clean_specs(gpt_specs)
            print(f"✅ GPT extracted {len(cleaned)} specs from {source}")
            return cleaned

        # FALLBACK: Direct parsing (when GPT unavailable)
        container = BeautifulSoup(spec_html, "html.parser")
        specs = _detect_and_parse(container)
        if specs:
            cleaned = _clean_specs(specs)
            print(f"✅ Direct parsed {len(cleaned)} specs from {source}")
            return cleaned

        print("⚠️ No specs extracted")
        return {}

    except Exception as e:
        print(f"❌ Error extracting specifications: {e}")
        return {}


# -------------------------------
# Phase 1: Scrape product cards
# -------------------------------
def rosen_bikes(driver, output_file):
    """Scrape bikes from Rosen Meents"""
    scraped_data = []
    
    for i, entry in enumerate(ROSEN_TARGET_URLS):
        target_url = entry["url"]
        category_text = entry["category"]
        sub_category_text = entry.get("sub_category", None)
        
        print(f"\n🚀 Processing URL {i+1}/{len(ROSEN_TARGET_URLS)}: {category_text} - {sub_category_text}")
        print(f"🌐 Scraping: {target_url}")
        driver.get(target_url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Look for product cards - Rosen Meents uses wrap-product-box-2023 class
        cards = soup.find_all("div", class_="wrap-product-box-2023")
        print(f"✅ Found {len(cards)} products using wrap-product-box-2023 selector")
    
        # Debug: Print first few product card titles to verify we're getting different products
        for i, card in enumerate(cards[:3]):  # Only first 3 for debugging
            title_tag = card.find("div", class_="product-box-top__title")
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                print(f"🔍 DEBUG: Card {i+1} title: '{title_text}'")
            else:
                print(f"🔍 DEBUG: Card {i+1} - No title found")
        
        for i, product_card in enumerate(cards):
            print(f"--- Processing Product {i+1}/{len(cards)} ---")
            print(f"🔍 DEBUG: Starting product {i+1} processing...")
        
            # Extract basic info from product card - initialize fresh variables for each product
            firm_text = None
            model_text = None
            year_text = None
            original_price = None
            discounted_price = None
            img_url = None
            product_url = None
        
            # Extract model name from product-box-top__title
            model_tag = product_card.find("div", class_="product-box-top__title")
            if model_tag:
                model_text = model_tag.get_text(strip=True)
                if model_text:
                    # Extract firm name from model name (case-insensitive)
                    firm_names = ["FRITZI","Bolt","Colnago", "Mongoose", "Gt", "Rocky Mountain", "BMC", "Merida", "Look", "Pinarello", "Vision", "Rainbow","SCHWINN"]
                    for firm in firm_names:
                        if firm.lower() in model_text.lower():
                            firm_text = firm
                            model_text = re.sub(re.escape(firm), "", model_text, flags=re.IGNORECASE).strip()
                            break
                    
                    # If no firm found but "scor" is in the model name, set firm to BMC
                    if not firm_text and "scor" in model_text.lower():
                        firm_text = "BMC"
                    
                    # Remove Hebrew words and other specified terms
                    words_to_remove = [
                        "אופני הרים חשמליים",
                        "אופני",
                        "New",
                        "קרבון מלא",
                        "אנדורו", 
                        "הרים לילדים",
                        "גברים",
                        "מאלומיניום",
                        "הרים",
                        "זנב קשיח",
                        "לנערים",
                        "אלומיניום",
                        "מתקפלים",
                        "אופני כביש",
                        "אופני עיר",
                        "אופני דחיפה",
                        "אופני קיבוץ",
                        "אופני דחיפה",
                        "ז",
                        "פעלולים מקצועיים",
                        "פעלולים",
                        "פריסטייל",
                        "כביש",
                        "תחרותים",
                        "אופני",
                        "נג\"ש",
                        "אירו",
                        "קרבון",
                        "/",
                        "29",
                        "27.5",
                        "לנשים",
                        'ז"ק',
                        "עיר",
                        "חשמלים",
                        "וכושר",
                        "ים",
                        "ונוער",
                        "מקצועייים",
                        "תחרויות",
                        "בסטייל",
                        "רטרו",
                        "פיסי",
                        
                        


                    ]
                    
                    for word in words_to_remove:
                        model_text = model_text.replace(word, "").strip()
                    
                    # Extract year from model name
                    valid_years = set(str(y) for y in range(2020, 2028))
                    matches = re.findall(r'\b\d{4}\b', model_text)
                    year_text = next((year for year in matches if year in valid_years), None)
                    if year_text:
                        model_text = re.sub(r'\b' + re.escape(year_text) + r'\b', '', model_text).strip()
                    
                    # Clean the model name using the cleanup function
                    model_text = clean_model_name(model_text)
            
            # Extract original price from product-item-price__price-changer
            original_price_tag = product_card.find("span", class_="product-item-price__price-changer")
            if original_price_tag:
                original_price_text = original_price_tag.get_text(strip=True)
                if original_price_text:
                    price_match = re.search(r'[\d,]+', original_price_text.replace('₪', '').replace(',', ''))
                    if price_match:
                        try:
                            original_price = int(price_match.group().replace(',', ''))
                        except ValueError:
                            pass
            
            # Extract discounted price from product-box_price-extra-change (club price)
            discounted_price_tag = product_card.find("span", class_="product-box_price-extra-change")
            if discounted_price_tag:
                discounted_price_text = discounted_price_tag.get_text(strip=True)
                if discounted_price_text:
                    price_match = re.search(r'[\d,]+', discounted_price_text.replace('₪', '').replace(',', ''))
                    if price_match:
                        try:
                            discounted_price = int(price_match.group().replace(',', ''))
                        except ValueError:
                            pass
            
            # Extract image URL from product-box-top__image-item
            img_tag = product_card.find("img", class_="product-box-top__image-item")
            if img_tag:
                img_url = img_tag.get('data-src') or img_tag.get('src')
                if img_url:
                    if '?' in img_url:
                        img_url = img_url.split('?')[0]
                    if not img_url.startswith('http'):
                        img_url = urljoin(BASE_URL, img_url)
                    
                    # Check if this is a placeholder image and skip it
                    if img_url and ('anim.gif' in img_url or 'placeholder' in img_url.lower()):
                        print(f"⚠️ Skipping placeholder image: {img_url}")
                        img_url = None
            
            # Extract product URL from the main link
            link_tag = product_card.find('a', class_="product-box-2023")
            if link_tag:
                relative_href = link_tag.get('href')
                if relative_href:
                    product_url = urljoin(BASE_URL, relative_href)
            
            # Check if this is a bike (exclude accessories and courses)
            exclude_words = [
                "סוללת",
                "תפס",
                "כבל",
                "קורס",
                "סוללה מגדילת טווח",
                "לרוכבי",
            ]
            
            is_bike = True
            if model_text:
                for word in exclude_words:
                    if word in model_text:
                        is_bike = False
                        print(f"⚠️ Skipped (not a bike): {model_text} - contains '{word}'")
                        break
            
                # Debug output
                print(f"🔍 DEBUG: Product {i+1} - Model: '{model_text}', Firm: '{firm_text}', Price: {original_price}, URL: {product_url}")
                
                # Only process if it's a bike and we have at least a model or image
                if is_bike and (model_text or img_url):
                    print(f"✅ Processing bike: {model_text} - Original: {original_price}, Discounted: {discounted_price}")
                    
                    # Create product data with correct structure
                    product_data = {
                        "source": {
                            "importer": "Rosen Meents",
                            "domain": "https://www.rosen-meents.co.il",
                            "product_url": product_url
                        },
                        "firm": firm_text,
                        "model": model_text,
                        "year": year_text,
                        "category": category_text,
                        "sub_category": sub_category_text,
                        "original_price": original_price,
                        "disc_price": discounted_price if discounted_price else "",
                        "images": {
                            "image_url": img_url,
                            "gallery_images_urls": []
                        },
                        "specs": {}
                    }
                    
                    # Extract specs and gallery images if we have a product URL
                    if product_url:
                        # Process all products (don't skip any based on size information)
                        print(f"🚴 Processing product: {model_text}")
                        
                        # Extract specs using the original function that was working
                        specs = extract_product_specifications(driver, product_url)
                        product_data["specs"] = specs
                        
                        # Helper: case-insensitive spec lookup across multiple key names
                        def _spec_find(keys_to_try):
                            """Search specs for any matching key (case-insensitive). Returns value or ''."""
                            spec_dict = product_data.get("specs", {})
                            for try_key in keys_to_try:
                                for k, v in spec_dict.items():
                                    if k.lower().replace("_", " ") == try_key.lower().replace("_", " "):
                                        return str(v)
                            return ""

                        # Extract WH (Watt Hours) from battery specs - only for electric bikes
                        if category_text == "electric":
                            battery_text = _spec_find([
                                "battery", "battery_pack", "battery pack",
                                "סוללה", "charger",
                            ])
                            # Also search ALL spec values for Wh mention
                            if not re.search(r"\d+\s*Wh", battery_text, re.IGNORECASE):
                                for v in product_data.get("specs", {}).values():
                                    if re.search(r"\d+\s*Wh", str(v), re.IGNORECASE):
                                        battery_text = str(v)
                                        break

                            wh_match = re.search(r"(\d+)\s*Wh", battery_text, re.IGNORECASE)
                            if wh_match:
                                product_data["wh"] = int(wh_match.group(1))
                                print(f"🔋 Found Wh: {wh_match.group(1)}Wh")
                            else:
                                fallback_match = re.search(r"\b(\d{3})\b", battery_text)
                                if fallback_match:
                                    product_data["wh"] = int(fallback_match.group(1))
                                    print(f"🔋 Fallback Wh: {fallback_match.group(1)}Wh")
                                else:
                                    product_data["wh"] = None
                        else:
                            print(f"🚴 Non-electric bike - skipping WH extraction")

                        # Extract fork length (travel in mm)
                        fork_text = _spec_find([
                            "fork", "front_suspension", "front suspension",
                            "בולם זעזועים קדמי", "בולם קדמי",
                        ])
                        if fork_text:
                            match = re.search(r"(\d+)\s*mm\s*(?:travel|suspension|מהלך)?", fork_text, re.IGNORECASE)
                            if match:
                                product_data["fork length"] = int(match.group(1))
                                print(f"🔧 Fork length: {match.group(1)}mm")
                            else:
                                product_data["fork length"] = None
                        else:
                            product_data["fork length"] = None
                        
                        # Determine bike style based on fork length
                        fork_length_str = product_data.get("fork length")
                        if fork_length_str is not None:
                            try:
                                fork_length = int(fork_length_str)
                                if fork_length in [40, 50, 60, 70, 80, 90, 100, 110, 120]:
                                    product_data["bike_style"] = "cross-country"  # Cross Country
                                    print(f"🏔️ Bike style determined: XC (fork: {fork_length}mm)")
                                elif fork_length in [130, 140, 150]:
                                    product_data["bike_style"] = "trail"  # Trail
                                    print(f"🌲 Bike style determined: Trail (fork: {fork_length}mm)")
                                elif fork_length in [160, 170, 180]:
                                    product_data["bike_style"] = "enduro"  # Enduro
                                    print(f"🚵 Bike style determined: Enduro (fork: {fork_length}mm)")
                                else:
                                    print(f"⚠️ Unexpected fork length value: {fork_length}")
                                    product_data["bike_style"] = None
                            except ValueError as e:
                                print(f"⚠️ Invalid fork length '{fork_length_str}': {e}")
                                product_data["bike_style"] = None
                        else:
                            print("⚠️ No fork length available - cannot determine bike style")
                            product_data["bike_style"] = None
                        
                        # Extract and rewrite product description
                        description_element = None
                        original_description = ""
                        rewritten_description = ""
                        
                        # Look for description in product-item-content text-toggle element
                        # Get the product page to extract description
                        if product_url:
                            driver.get(product_url)
                            time.sleep(2)
                            product_soup = BeautifulSoup(driver.page_source, "html.parser")
                            description_element = product_soup.find("div", class_="product-item-content text-toggle")
                            if description_element:
                                original_description = description_element.get_text(strip=True)
                                print(f"📝 Original description: {original_description[:100]}...")
                                
                                # Rewrite description with ChatGPT if we have content
                                if original_description.strip():
                                    rewritten_description = rewrite_description_with_chatgpt(original_description, CHATGPT_API_KEY)
                                    print(f"✨ Rewritten description: {rewritten_description[:100]}...")
                                else:
                                    print("⚠️ Warning: Empty description found")
                                    rewritten_description = original_description
                            else:
                                print("⚠️ Warning: No product description found")
                                rewritten_description = ""
                        else:
                            print("⚠️ Warning: No product URL - cannot extract description")
                            rewritten_description = ""
                        
                        # Add descriptions to product data
                        product_data["rewritten_description"] = rewritten_description
                        
                        # Extract gallery images using the original function
                        gallery_images_urls = extract_gallery_images(driver, product_url)
                        product_data["images"]["gallery_images_urls"] = gallery_images_urls
                    
                        # If no valid main image, use first gallery image
                        if (not product_data["images"]["image_url"] or 
                            'anim.gif' in product_data["images"]["image_url"] or 
                            'placeholder' in product_data["images"]["image_url"].lower()) and gallery_images_urls:
                            best_gallery_image = None
                            for gallery_img in gallery_images_urls:
                                if '/source/' in gallery_img:
                                    best_gallery_image = gallery_img
                                    break
                                elif '/thumb/' in gallery_img:
                                    best_gallery_image = gallery_img
                            
                            if not best_gallery_image and gallery_images_urls:
                                best_gallery_image = gallery_images_urls[0]
                            
                            if best_gallery_image:
                                product_data["images"]["image_url"] = best_gallery_image
                                print(f"🖼️ Using gallery image as main image: {best_gallery_image}")

                        # Kids bike wheel size (only when category is kids)
                        if category_text == "kids":
                            wheel_size = extract_wheel_size_for_kids_bike(
                                product_data.get("model"),
                                product_data.get("specs"),
                            )
                            if wheel_size is not None:
                                product_data["wheel_size"] = wheel_size
                    
                    # Add the product data directly (specs are already cleaned in extract_product_specifications)
                    scraped_data.append(product_data)
                    
                    # Save data incrementally (real-time saving)
                    try:
                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
                        print(f"💾 Real-time save: {len(scraped_data)} products saved to JSON file")
                    except Exception as e:
                        print(f"⚠️ Warning: Could not save progress: {e}")
                elif not is_bike:
                    pass  # Already printed skip message above
                else:
                    print(f"⚠️ Skipped: No model or image found for product {i+1}")
            
            print(f"🔍 DEBUG: Finished processing {len(cards)} products from this URL")
            
            # Summary after each URL is processed
            print(f"✅ Completed {category_text}: {len([p for p in scraped_data if p.get('category') == category_text])} products")
    
    return scraped_data

# -------------------------------
# Gallery Images Extractor
# -------------------------------
def extract_gallery_images(driver, product_url):
    """Extract gallery images from the slick-track element on product page"""
    if not product_url:
        return []
    
    try:
        print(f"🖼️ Extracting gallery images from: {product_url}")
        driver.get(product_url)
        time.sleep(4)  # Increased wait time for JavaScript to load
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        gallery_images_urls = []
        
        # Method 1: Look for slick-track element with new structure
        slick_track = soup.find("div", class_="slick-track")
        if slick_track:
            print("✅ Found slick-track element")
            
            # Find all product-item-slider-wrap elements (new structure)
            slider_wraps = slick_track.find_all("div", class_="product-item-slider-wrap")
            print(f"Found {len(slider_wraps)} slider wraps")
            
            for wrap in slider_wraps:
                # Find the product-item-slider__image div
                image_div = wrap.find("div", class_="product-item-slider__image")
                if image_div:
                    # Look for <a> tag with href attribute
                    link_tag = image_div.find("a", href=True)
                    if link_tag:
                        img_url = link_tag.get("href")
                        if img_url:
                            # Convert relative URL to absolute URL
                            if not img_url.startswith('http'):
                                img_url = urljoin(BASE_URL, img_url)
                            
                            # Filter out non-product images
                            if ("files/catalog/item" in img_url and 
                                "menu" not in img_url.lower() and 
                                "banner" not in img_url.lower() and
                                "hermidabanner" not in img_url.lower() and
                                "anim.gif" not in img_url and
                                "placeholder" not in img_url.lower() and
                                img_url not in gallery_images_urls):
                                gallery_images_urls.append(img_url)
                                print(f"🖼️ Found gallery image: {img_url}")
        else:
            print("⚠️ No slick-track element found")
        
        # Method 2: Fallback - look for any img tags in gallery containers
        if not gallery_images_urls:
            print("🔍 Trying fallback method: searching for img tags in gallery containers")
            gallery_containers = soup.find_all(["div", "ul"], class_=lambda x: x and any(word in x.lower() for word in ["gallery", "slider", "thumb", "image"]))
            for container in gallery_containers:
                img_tags = container.find_all("img")
                for img in img_tags:
                    src = img.get("src") or img.get("data-src")
                    if src and ("files/catalog" in src or ".png" in src or ".jpg" in src):
                        if not src.startswith('http'):
                            src = urljoin(BASE_URL, src)
                        # Filter out menu images and only include product-specific images
                        if ("files/catalog/item" in src and 
                            "menu" not in src.lower() and 
                            "banner" not in src.lower() and
                            "hermidabanner" not in src.lower() and
                            "anim.gif" not in src and
                            "placeholder" not in src.lower() and
                            src not in gallery_images_urls):
                            gallery_images_urls.append(src)
                            print(f"🖼️ Found fallback gallery image: {src}")
        
        print(f"✅ Extracted {len(gallery_images_urls)} gallery images")
        
        # Prioritize larger/higher quality images by sorting them
        # Look for images with 'source' in the URL (usually larger) first
        sorted_gallery_images = []
        
        # First add source images (usually highest quality)
        for img_url in gallery_images_urls:
            if '/source/' in img_url:
                sorted_gallery_images.append(img_url)
        
        # Then add other images
        for img_url in gallery_images_urls:
            if '/source/' not in img_url:
                sorted_gallery_images.append(img_url)
        
        # Debug: Print the first few lines of the HTML to see the structure
        if not gallery_images_urls:
            print("🔍 Debug: First 500 characters of HTML:")
            print(driver.page_source[:500])
        
        return sorted_gallery_images
        
    except Exception as e:
        print(f"❌ Error extracting gallery images: {e}")
        return []

def extract_product_specifications_from_soup(soup, product_url):
    """Extract product specifications from a BeautifulSoup object (reuses main logic)."""
    if not soup:
        return {}
    try:
        print(f"🔍 Extracting specs from soup for: {product_url}")
        spec_html, source = _get_spec_html(soup)
        if not spec_html:
            print("⚠️ No spec container found")
            return {}

        gpt_specs = _gpt_extract_specs(spec_html)
        if gpt_specs:
            return _clean_specs(gpt_specs)

        container = BeautifulSoup(spec_html, "html.parser")
        specs = _detect_and_parse(container)
        if specs:
            return _clean_specs(specs)

        print("⚠️ No specs extracted")
        return {}
    except Exception as e:
        print(f"❌ Error extracting specifications: {e}")
        return {}

def extract_gallery_images_from_soup(soup, product_url):
    """Extract gallery images from a BeautifulSoup object"""
    if not soup:
        return []
    
    try:
        print(f"🖼️ Extracting gallery images from soup for: {product_url}")
        
        gallery_images_urls = []
        
        # Method 1: Look for slick-track element with new structure
        slick_track = soup.find("div", class_="slick-track")
        if slick_track:
            print("✅ Found slick-track element")
            
            # Find all product-item-slider-wrap elements (new structure)
            slider_wraps = slick_track.find_all("div", class_="product-item-slider-wrap")
            print(f"Found {len(slider_wraps)} slider wraps")
            
            for wrap in slider_wraps:
                # Find the product-item-slider__image div
                image_div = wrap.find("div", class_="product-item-slider__image")
                if image_div:
                    # Look for <a> tag with href attribute
                    link_tag = image_div.find("a", href=True)
                    if link_tag:
                        img_url = link_tag.get("href")
                        if img_url:
                            # Convert relative URL to absolute URL
                            if not img_url.startswith('http'):
                                img_url = urljoin(BASE_URL, img_url)
                            
                            # Filter out non-product images
                            if ("files/catalog/item" in img_url and 
                                "menu" not in img_url.lower() and 
                                "banner" not in img_url.lower() and
                                "hermidabanner" not in img_url.lower() and
                                "anim.gif" not in img_url and
                                "placeholder" not in img_url.lower() and
                                img_url not in gallery_images_urls):
                                gallery_images_urls.append(img_url)
                                print(f"🖼️ Found gallery image: {img_url}")
        else:
            print("⚠️ No slick-track element found")
        
        # Method 2: Fallback - look for any img tags in gallery containers
        if not gallery_images_urls:
            print("🔍 Trying fallback method: searching for img tags in gallery containers")
            gallery_containers = soup.find_all(["div", "ul"], class_=lambda x: x and any(word in x.lower() for word in ["gallery", "slider", "thumb", "image"]))
            for container in gallery_containers:
                img_tags = container.find_all("img")
                for img in img_tags:
                    src = img.get("src") or img.get("data-src")
                    if src and ("files/catalog" in src or ".png" in src or ".jpg" in src):
                        if not src.startswith('http'):
                            src = urljoin(BASE_URL, src)
                        # Filter out menu images and only include product-specific images
                        if ("files/catalog/item" in src and 
                            "menu" not in src.lower() and 
                            "banner" not in src.lower() and
                            "hermidabanner" not in src.lower() and
                            "anim.gif" not in src and
                            "placeholder" not in src.lower() and
                            src not in gallery_images_urls):
                            gallery_images_urls.append(src)
                            print(f"🖼️ Found fallback gallery image: {src}")
        
        print(f"✅ Extracted {len(gallery_images_urls)} gallery images")
        
        # Prioritize larger/higher quality images by sorting them
        # Look for images with 'source' in the URL (usually larger) first
        sorted_gallery_images = []
        
        # First add source images (usually highest quality)
        for img_url in gallery_images_urls:
            if '/source/' in img_url:
                sorted_gallery_images.append(img_url)
        
        # Then add other images
        for img_url in gallery_images_urls:
            if '/source/' not in img_url:
                sorted_gallery_images.append(img_url)
        
        return sorted_gallery_images
        
    except Exception as e:
        print(f"❌ Error extracting gallery images: {e}")
        return []

# -------------------------------
# Main
# -------------------------------
if __name__ == '__main__':
    # --- Setup Output Directory ---
    try:
        # Get project root (go up from data/scrapers/ to data/ to project root)
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "data" / "scraped_raw_data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = output_dir / "rosen_data.json"
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
        options.add_argument('--headless=new')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        driver = uc.Chrome(options=options, version_main=146)
        print("✅ Chrome driver started successfully!")
        products = rosen_bikes(driver, output_file)
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
