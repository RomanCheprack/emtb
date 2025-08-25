import json
import re

def test_extractions():
    # Load the existing rosen.json data
    with open('data/scraped_raw_data/rosen.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("Testing WH and fork length extraction on existing rosen.json data...")
    print("=" * 60)
    
    # Test first 10 products
    for i, product in enumerate(data[:10]):
        print(f"\n--- Product {i+1}: {product.get('model', 'Unknown')} ---")
        
        # Test WH extraction
        battery_value = product.get("battery", "")
        if battery_value:
            print(f"Battery: {battery_value}")
            wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
            if wh_match:
                wh_value = int(wh_match.group(1))
                print(f"🔋 Found Wh: {wh_value}Wh")
            else:
                fallback_match = re.search(r"\b(\d{3})\b", battery_value)
                if fallback_match:
                    print(f"🔋 Found 3-digit number: {fallback_match.group(1)}Wh")
                else:
                    print("❌ No WH found")
        else:
            print("❌ No battery field")
        
        # Test fork length extraction
        fork_text = product.get("fork", "")
        if fork_text:
            print(f"Fork: {fork_text}")
            
            # Try multiple patterns for fork travel
            patterns = [
                r'(?<!\d)(120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?',  # Original pattern
                r'(\d{3})\s*mm\s*(?:travel|suspension)',  # Pattern with "travel" or "suspension"
                r'(\d{3})\s*mm\s*[^0-9]*$',  # Pattern at end of string
                r'(\d{3})\s*mm',  # Simple mm pattern
            ]
            
            found = False
            for pattern in patterns:
                match = re.search(pattern, fork_text.lower())
                if match:
                    fork_length = int(match.group(1))
                    print(f"🔧 Found fork length: {fork_length}mm (pattern: {pattern})")
                    
                    # Determine sub-category
                    if fork_length == 120:
                        sub_category = "cross-country"
                    elif fork_length in [130, 140, 150]:
                        sub_category = "trail"
                    elif fork_length in [160, 170, 180]:
                        sub_category = "enduro"
                    else:
                        sub_category = "unknown"
                    print(f"🏷️ Sub-category: {sub_category}")
                    found = True
                    break
            
            if not found:
                print("❌ No fork length found with any pattern")
        else:
            print("❌ No fork field")

if __name__ == "__main__":
    test_extractions()
