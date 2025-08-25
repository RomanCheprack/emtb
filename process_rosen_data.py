import json
import re

def process_rosen_data():
    # Load the existing rosen.json data
    with open('data/scraped_raw_data/rosen.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Processing {len(data)} products from rosen.json...")
    
    for i, product in enumerate(data):
        print(f"\n--- Processing Product {i+1}: {product.get('model', 'Unknown')} ---")
        
        # Extract WH from battery field
        battery_value = product.get("battery", "")
        if battery_value:
            wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
            if wh_match:
                wh_value = int(wh_match.group(1))
                product["wh"] = wh_value
                print(f"🔋 Found Wh: {wh_value}Wh")
            else:
                # If no 'Wh' found, try to find a 3-digit number in battery field
                fallback_match = re.search(r"\b(\d{3})\b", battery_value)
                if fallback_match:
                    product["wh"] = int(fallback_match.group(1))
                    print(f"🔋 Found 3-digit number: {fallback_match.group(1)}Wh")
        
        # Extract fork length from fork field
        fork_text = product.get("fork", "")
        if fork_text:
            # Try multiple patterns for fork travel
            patterns = [
                r'(\d{3})\s*mm\s*(?:travel|suspension)',  # Pattern with "travel" or "suspension"
                r'(\d{3})\s*mm\s*[^0-9]*$',  # Pattern at end of string
                r'(\d{3})\s*mm',  # Simple mm pattern
                r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?',  # Original pattern
            ]
            
            found = False
            for pattern in patterns:
                match = re.search(pattern, fork_text.lower())
                if match:
                    fork_length = int(match.group(1))
                    product["fork length"] = fork_length
                    print(f"🔧 Found fork length: {fork_length}mm")
                    
                    # Determine sub-category based on fork length
                    if fork_length == 120:
                        product["sub-category"] = "cross-country"
                    elif fork_length in [130, 140, 150]:
                        product["sub-category"] = "trail"
                    elif fork_length in [160, 170, 180]:
                        product["sub-category"] = "enduro"
                    else:
                        product["sub-category"] = "unknown"
                    print(f"🏷️ Sub-category: {product['sub-category']}")
                    found = True
                    break
            
            if not found:
                print(f"⚠️ No fork length found in: {fork_text}")
                product["fork length"] = None
                product["sub-category"] = "unknown"
    
    # Save the updated data back to the file
    with open('data/scraped_raw_data/rosen.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"\n✅ Updated rosen.json with WH and fork length data")
    
    # Print summary
    wh_count = sum(1 for p in data if p.get('wh'))
    fork_length_count = sum(1 for p in data if p.get('fork length'))
    sub_category_count = sum(1 for p in data if p.get('sub-category') and p.get('sub-category') != 'unknown')
    
    print(f"📊 Summary:")
    print(f"   - Products with WH: {wh_count}/{len(data)}")
    print(f"   - Products with fork length: {fork_length_count}/{len(data)}")
    print(f"   - Products with sub-category: {sub_category_count}/{len(data)}")

if __name__ == "__main__":
    process_rosen_data()
