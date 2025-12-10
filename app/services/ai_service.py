import os
import json
import asyncio
import threading
import re
from typing import Any, Dict, List, Optional

try:
    import aiohttp  # type: ignore
except Exception:
    aiohttp = None
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("WARNING: OPENAI_API_KEY not set in environment variables!")
client = OpenAI(api_key=api_key) if api_key else None

def _extract_all_bike_fields(bike: Dict[str, Any]) -> Dict[str, Any]:
    """Extract all fields from a bike, handling both flat and nested formats."""
    fields = {}
    
    # Handle nested format (with specs dict)
    if 'specs' in bike and isinstance(bike['specs'], dict):
        # Add all specs
        fields.update(bike['specs'])
        # Add top-level fields
        for key in ['firm', 'brand', 'model', 'year', 'category', 'sub_category', 'style', 
                    'description', 'rewritten_description', 'slug', 'main_image_url']:
            if key in bike:
                fields[key] = bike[key]
    else:
        # Flat format - use all fields except internal/metadata ones
        exclude_fields = {'id', 'internal_id', 'uuid', 'slug', 'main_image_url', 'image_url', 
                         'product_url', 'gallery_images_urls', 'images', 'prices', 'source',
                         'created_at', 'updated_at'}
        for key, value in bike.items():
            if key not in exclude_fields and value not in [None, '', 'N/A', '#N/A']:
                fields[key] = value
    
    # Handle prices if available
    if 'prices' in bike and isinstance(bike['prices'], list) and bike['prices']:
        # Get the most recent or first price
        price_data = bike['prices'][0] if isinstance(bike['prices'][0], dict) else {}
        if 'price' in price_data:
            fields['price'] = price_data['price']
        if 'disc_price' in price_data:
            fields['disc_price'] = price_data['disc_price']
    elif 'price' in bike:
        fields['price'] = bike['price']
    if 'disc_price' in bike:
        fields['disc_price'] = bike['disc_price']
    
    return fields


def _get_all_comparable_fields(bikes: List[Dict[str, Any]]) -> List[str]:
    """Get all fields that should be included in comparison (hybrid approach).
    
    Returns: list of field names to include
    - Always includes core fields
    - Includes other fields if present in at least one bike
    """
    core_fields = ['firm', 'brand', 'model', 'year', 'price', 'disc_price']
    
    # Collect all fields from all bikes
    all_fields_set = set(core_fields)
    for bike in bikes:
        bike_fields = _extract_all_bike_fields(bike)
        all_fields_set.update(bike_fields.keys())
    
    # Exclude metadata/internal fields
    exclude_fields = {'id', 'internal_id', 'uuid', 'slug', 'main_image_url', 'image_url', 
                     'product_url', 'gallery_images_urls', 'images', 'prices', 'source',
                     'created_at', 'updated_at'}
    all_fields_set -= exclude_fields
    
    # Sort: core fields first, then others alphabetically
    core_present = [f for f in core_fields if f in all_fields_set]
    other_fields = sorted([f for f in all_fields_set if f not in core_fields])
    
    return core_present + other_fields


def _get_category_based_system_message(category: Optional[str], sub_category: Optional[str]) -> str:
    """Get category-adaptive system message for AI comparison."""
    base_message = "אתה כתב מגזין מומחה לאופניים. תן סקירה בעברית תקינה, קלילה וקולחת, בסגנון מגזין כמו Bikepanel. שים דגש על חווית רכיבה, יתרונות, חסרונות והמלצה ברורה."
    
    category_lower = (category or '').lower()
    sub_category_lower = (sub_category or '').lower()
    
    # Electric bikes emphasis
    if 'electric' in category_lower or 'electric' in sub_category_lower:
        emphasis = "הדגש במיוחד על: כוח מנוע, קיבולת סוללה, טווח נסיעה, מערכת עזרה, משקל, שלדה, בולמים, וכל המפרט הטכני הרלוונטי."
    
    # Mountain bikes emphasis
    elif 'mtb' in category_lower or 'mountain' in category_lower:
        emphasis = "הדגש במיוחד על: בולמים (מזלג ובולם אחורי), חומר שלדה, גיאומטריה, משקל, צמיגים, מערכת הילוכים, וכל המפרט הטכני הרלוונטי."
    
    # Kids bikes emphasis
    elif 'kids' in category_lower or 'ילדים' in sub_category_lower:
        emphasis = "הדגש במיוחד על: בטיחות, גודל מותאם, משקל, יציבות, גלגלי עזר, וכל המפרט הטכני הרלוונטי."
    
    # City bikes emphasis
    elif 'city' in category_lower or 'עיר' in sub_category_lower:
        emphasis = "הדגש במיוחד על: נוחות רכיבה, אבזור (תאורה, פעמון, מתלה), משקל, גלגלים, מחיר, וכל המפרט הטכני הרלוונטי."
    
    # Road bikes emphasis
    elif 'road' in category_lower or 'כביש' in sub_category_lower:
        emphasis = "הדגש במיוחד על: משקל, אווירודינמיקה, חומר שלדה, מערכת הילוכים, צמיגים, וכל המפרט הטכני הרלוונטי."
    
    # Gravel bikes emphasis
    elif 'gravel' in category_lower:
        emphasis = "הדגש במיוחד על: גיאומטריה, בולמים, חומר שלדה, צמיגים, מערכת הילוכים, משקל, וכל המפרט הטכני הרלוונטי."
    
    else:
        emphasis = "הדגש על כל המפרט הטכני הרלוונטי, יתרונות, חסרונות, והתאמה לשימוש."
    
    return f"{base_message} {emphasis}"


def create_ai_prompt(bikes_to_compare):
    """Create a dynamic prompt with all available bike specs (hybrid approach)."""
    if not bikes_to_compare:
        return ""
    
    # Get all fields to include
    fields_to_include = _get_all_comparable_fields(bikes_to_compare)
    
    # Hebrew field name mapping
    field_names_he = {
        'firm': 'חברה',
        'brand': 'חברה',
        'model': 'דגם',
        'year': 'שנה',
        'category': 'קטגוריה',
        'sub_category': 'תת-קטגוריה',
        'style': 'סגנון',
        'price': 'מחיר',
        'disc_price': 'מחיר מבצע',
        'motor': 'מנוע',
        'battery': 'סוללה',
        'wh': 'קיבולת סוללה (Wh)',
        'frame': 'שלדה',
        'frame_material': 'חומר שלדה',
        'fork': 'מזלג',
        'fork_length': 'מהלך מזלג (mm)',
        'rear_shock': 'בולם אחורי',
        'brakes': 'בלמים',
        'front_brake': 'בלם קדמי',
        'rear_brake': 'בלם אחורי',
        'weight': 'משקל',
        'wheel_size': 'גודל גלגלים',
        'tires': 'צמיגים',
        'front_tire': 'צמיג קדמי',
        'rear_tire': 'צמיג אחורי',
        'gear_count': 'מספר הילוכים',
        'shifter': 'שיפטר',
        'rear_derailleur': 'מעביר אחורי',
        'cassette': 'קסטה',
        'chain': 'שרשרת',
        'crank_set': 'קראנק',
        'saddle': 'אוכף',
        'seat_post': 'מוט אוכף',
        'handlebar': 'כידון',
        'stem': 'סטם',
        'pedals': 'דוושות',
        'description': 'תיאור',
        'rewritten_description': 'תיאור מפורט',
    }
    
    prompt = []
    for i, bike in enumerate(bikes_to_compare, 1):
        bike_fields = _extract_all_bike_fields(bike)
        specs_lines = []
        
        for field in fields_to_include:
            if field in bike_fields:
                value = bike_fields[field]
                # Skip empty values
                if value in [None, '', 'N/A', '#N/A']:
                    continue
                
                # Get Hebrew name or use field name
                field_name_he = field_names_he.get(field, field.replace('_', ' '))
                specs_lines.append(f"{field_name_he}: {value}")
        
        specs = "\n".join(specs_lines) if specs_lines else "אין מפרט זמין"
        prompt.append(f"אופניים {i}:\n{specs}")
    
    return "\n\n".join(prompt)

async def _search_with_openai_web(bike_query: str) -> Optional[Dict[str, Any]]:
    """Use OpenAI Responses web_search tool for a single query.

    Returns a dict with 'query' and 'answer' text if successful, else None.
    """
    if not client:
        return None
    try:
        # Python 3.8 compatible: use run_in_executor instead of to_thread
        import concurrent.futures
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: client.responses.create(
                model="gpt-4o-mini",
                input=(
                    f"בצע חיפוש אינטרנט קצר ומדויק על הדגם הבא: {bike_query}. "
                    "החזר סיכום קצר בעברית עם 3-5 נקודות עיקריות ומקורות."),
                tools=[{"type": "web_search"}],
            )
        )
        text = getattr(resp, "output_text", None)
        if text:
            return {"query": bike_query, "answer": text}
        return None
    except Exception as e:
        print(f"Error in OpenAI web search for {bike_query}: {e}")
        return None


async def _search_with_ddg(session: "aiohttp.ClientSession", bike_query: str) -> Optional[Dict[str, Any]]:
    """DuckDuckGo Instant Answer API as a lightweight fallback."""
    try:
        params = {"q": bike_query, "format": "json", "no_html": 1, "t": "emtb_site"}
        async with session.get("https://api.duckduckgo.com/", params=params, timeout=aiohttp.ClientTimeout(total=12)) as r:
            if r.status != 200:
                return None
            data = await r.json(content_type=None)
            abstract = data.get("AbstractText") or data.get("Heading") or ""
            related = []
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict):
                    txt = topic.get("Text")
                    if txt:
                        related.append(txt)
            combined = (abstract + "\n" + "\n".join(related)).strip()
            if combined:
                return {"query": bike_query, "answer": combined}
            return None
    except Exception:
        return None


async def _gather_bikes_research(bikes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run per-bike research concurrently. Try OpenAI web_search first, then DDG fallback."""
    queries: List[str] = []
    for bike in bikes:
        firm = bike.get("firm", "")
        model = bike.get("model", "")
        year = bike.get("year", "")
        q = " ".join([str(x) for x in [firm, model, year] if x])
        queries.append(q.strip() or "אופניים חשמליים דגם לא ידוע")

    # First try OpenAI web search concurrently (in threadpool since SDK is sync)
    async def _openai_task(q: str) -> Optional[Dict[str, Any]]:
        return await _search_with_openai_web(q)

    openai_results = await asyncio.gather(*[_openai_task(q) for q in queries])

    # For any missing results, fill via DDG concurrently
    results: List[Optional[Dict[str, Any]]] = list(openai_results)
    http_session: Optional["aiohttp.ClientSession"] = None
    if aiohttp is None:
        # aiohttp not available
        ddg_results = [None for _ in results]
    else:
        http_session = aiohttp.ClientSession(headers={"User-Agent": "emtb_site/1.0"})
    if http_session is not None:
        async with http_session as http_session_ctx:
            ddg_tasks = []
            for idx, res in enumerate(results):
                if res is None:
                    ddg_tasks.append(_search_with_ddg(http_session_ctx, queries[idx]))
                else:
                    ddg_tasks.append(asyncio.sleep(0, result=None))
            ddg_results = await asyncio.gather(*ddg_tasks)
    else:
        ddg_results = [None for _ in results]
    for idx, res in enumerate(results):
        if res is None and ddg_results[idx] is not None:
            results[idx] = ddg_results[idx]

    # Build final list aligned with bikes - include all bike data for research context
    final: List[Dict[str, Any]] = []
    for idx, bike in enumerate(bikes):
        # Extract all fields from bike for research context
        bike_fields = _extract_all_bike_fields(bike)
        final.append({
            "bike": bike_fields,  # Include all fields, not just hardcoded ones
            "research": results[idx] or {"query": None, "answer": ""}
        })
    return final


def _build_comparison_prompt(bikes: List[Dict[str, Any]], research: List[Dict[str, Any]]) -> str:
    """Compose dynamic Hebrew prompt combining all available specs and web research."""
    # Get all fields to include (hybrid approach)
    fields_to_include = _get_all_comparable_fields(bikes)
    
    # Hebrew field name mapping
    field_names_he = {
        'firm': 'חברה',
        'brand': 'חברה',
        'model': 'דגם',
        'year': 'שנה',
        'category': 'קטגוריה',
        'sub_category': 'תת-קטגוריה',
        'style': 'סגנון',
        'price': 'מחיר',
        'disc_price': 'מחיר מבצע',
        'motor': 'מנוע',
        'battery': 'סוללה',
        'wh': 'קיבולת סוללה (Wh)',
        'frame': 'שלדה',
        'frame_material': 'חומר שלדה',
        'fork': 'מזלג',
        'fork_length': 'מהלך מזלג (mm)',
        'rear_shock': 'בולם אחורי',
        'brakes': 'בלמים',
        'front_brake': 'בלם קדמי',
        'rear_brake': 'בלם אחורי',
        'weight': 'משקל',
        'wheel_size': 'גודל גלגלים',
        'tires': 'צמיגים',
        'front_tire': 'צמיג קדמי',
        'rear_tire': 'צמיג אחורי',
        'gear_count': 'מספר הילוכים',
        'shifter': 'שיפטר',
        'rear_derailleur': 'מעביר אחורי',
        'cassette': 'קסטה',
        'chain': 'שרשרת',
        'crank_set': 'קראנק',
        'saddle': 'אוכף',
        'seat_post': 'מוט אוכף',
        'handlebar': 'כידון',
        'stem': 'סטם',
        'pedals': 'דוושות',
        'description': 'תיאור',
        'rewritten_description': 'תיאור מפורט',
    }
    
    lines: List[str] = []
    for i, (bike, item) in enumerate(zip(bikes, research), 1):
        bike_fields = _extract_all_bike_fields(bike)
        r = item["research"]
        
        # Build specs dynamically
        specs_lines = []
        for field in fields_to_include:
            if field in bike_fields:
                value = bike_fields[field]
                # Skip empty values
                if value in [None, '', 'N/A', '#N/A']:
                    continue
                
                # Get Hebrew name or use field name
                field_name_he = field_names_he.get(field, field.replace('_', ' '))
                specs_lines.append(f"{field_name_he}: {value}")
        
        specs = "\n".join(specs_lines) if specs_lines else "אין מפרט זמין"
        web = f"תוצאות חיפוש מקוצרות: {r.get('answer','').strip()}" if r.get('answer') else "אין תוצאות חיפוש."
        lines.append(f"אופניים {i}:\n{specs}\n\n{web}")
    
    return "\n\n".join(lines)


def _fix_json_syntax(json_str: str) -> str:
    """Fix common JSON syntax errors like trailing commas, missing commas, etc."""
    if not json_str or not json_str.strip():
        return json_str
    
    # Remove leading/trailing whitespace
    json_str = json_str.strip()
    
    # Remove markdown code blocks if present (handle both ```json and ```)
    if json_str.startswith('```'):
        # Remove ```json or ``` at start (multiline)
        json_str = re.sub(r'^```(?:json)?\s*\n?', '', json_str, flags=re.MULTILINE)
        # Remove ``` at end (multiline)
        json_str = re.sub(r'\n?\s*```$', '', json_str, flags=re.MULTILINE)
        json_str = json_str.strip()
    
    # Find the JSON object boundaries using brace matching
    start = json_str.find('{')
    if start == -1:
        return json_str
    
    # Use brace matching to find the complete JSON object
    brace_count = 0
    bracket_count = 0
    in_string = False
    escape_next = False
    end = start
    
    for i in range(start, len(json_str)):
        char = json_str[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
        elif char == '[':
            bracket_count += 1
        elif char == ']':
            bracket_count -= 1
    
    # If we found a complete JSON object, use it
    if end > start and brace_count == 0:
        json_content = json_str[start:end+1]
    else:
        # Fallback: try to find last } and hope it's complete
        end = json_str.rfind('}')
        if end == -1 or end <= start:
            return json_str
        json_content = json_str[start:end+1]
    
    # Fix trailing commas before closing braces/brackets
    json_content = re.sub(r',\s*}', '}', json_content)
    json_content = re.sub(r',\s*]', ']', json_content)
    
    # Fix missing commas between object properties
    json_content = re.sub(r'}\s*{', '},{', json_content)
    
    return json_content


def _parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON with multiple fallback strategies."""
    if not text or not text.strip():
        print("Warning: Empty text for JSON parsing")
        return None
    
    # Strategy 1: Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Direct JSON parse failed: {e}")
    
    # Strategy 2: Remove markdown and try again
    try:
        cleaned = text.strip()
        # Remove markdown code blocks
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'\n?\s*```$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"Markdown-cleaned JSON parse failed: {e}")
    
    # Strategy 3: Extract JSON from text (find first { to last })
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Extracted JSON parse failed: {e}")
    
    # Strategy 4: Fix common syntax errors and try again
    try:
        fixed_json = _fix_json_syntax(text)
        if fixed_json and fixed_json.strip():
            return json.loads(fixed_json)
    except json.JSONDecodeError as e:
        print(f"Fixed JSON parse failed: {e}")
        print(f"Error at position {e.pos if hasattr(e, 'pos') else 'unknown'}")
        if fixed_json:
            # Show context around the error
            error_pos = e.pos if hasattr(e, 'pos') else len(fixed_json)
            start_context = max(0, error_pos - 100)
            end_context = min(len(fixed_json), error_pos + 100)
            print(f"Context around error: ...{fixed_json[start_context:end_context]}...")
    
    # Strategy 5: Try to extract and fix the JSON portion with brace matching
    try:
        start = text.find('{')
        if start != -1:
            # Use brace matching to find the end (respecting strings)
            brace_count = 0
            bracket_count = 0
            in_string = False
            escape_next = False
            end = start
            
            for i in range(start, len(text)):
                char = text[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if in_string:
                    continue
                
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
            
            if end > start:
                json_str = text[start:end+1]
                fixed_json = _fix_json_syntax(json_str)
                if fixed_json:
                    return json.loads(fixed_json)
    except json.JSONDecodeError as e:
        print(f"Extract and fix JSON parse failed: {e}")
        if 'fixed_json' in locals():
            error_pos = e.pos if hasattr(e, 'pos') else len(fixed_json)
            start_context = max(0, error_pos - 100)
            end_context = min(len(fixed_json), error_pos + 100)
            print(f"Context around error: ...{fixed_json[start_context:end_context]}...")
    
    # Strategy 6: Try to parse partial JSON and reconstruct if possible
    # This is a last resort - try to extract what we can
    try:
        # Find the JSON structure and try to complete it
        start = text.find('{')
        if start != -1:
            # Try to find where the JSON might be incomplete
            # Look for patterns like incomplete arrays or objects
            partial_json = text[start:]
            
            # Try to close incomplete structures
            # Count open braces and brackets
            open_braces = partial_json.count('{') - partial_json.count('}')
            open_brackets = partial_json.count('[') - partial_json.count(']')
            
            # If we have open structures, try to close them
            if open_braces > 0 or open_brackets > 0:
                # Find the last complete structure
                # This is complex, so we'll just try to close everything
                fixed = partial_json
                # Close arrays first
                for _ in range(open_brackets):
                    # Find last incomplete array
                    last_open = fixed.rfind('[')
                    if last_open != -1:
                        # Check if it's already closed after this
                        after_open = fixed[last_open:].count(']')
                        if after_open == 0:
                            # Try to close it before the end
                            # Find a good place to insert ]
                            # For now, just append
                            fixed = fixed.rstrip().rstrip(',') + ']'
                
                # Close objects
                for _ in range(open_braces):
                    fixed = fixed.rstrip().rstrip(',') + '}'
                
                fixed_json = _fix_json_syntax(fixed)
                if fixed_json:
                    return json.loads(fixed_json)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Partial JSON reconstruction failed: {e}")
    
    # Log the actual response for debugging
    print(f"Original text (first 1000 chars): {text[:1000]}")
    print(f"Original text (last 500 chars): {text[-500:] if len(text) > 500 else text}")
    return None


def _run_coroutine_blocking(coro: Any) -> Any:
    """Run an async coroutine from sync code safely across environments.

    Handles cases where an event loop is already running by delegating to a new thread.
    """
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        # If there's already a running loop (e.g., in some servers/notebooks)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            result_container: Dict[str, Any] = {}
            error_container: Dict[str, BaseException] = {}

            def _runner() -> None:
                try:
                    local_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(local_loop)
                    result = local_loop.run_until_complete(coro)
                    result_container["result"] = result
                except BaseException as exc:  # capture to raise after join
                    error_container["exc"] = exc
                finally:
                    try:
                        local_loop.close()
                    except Exception:
                        pass

            thread = threading.Thread(target=_runner, daemon=True)
            thread.start()
            thread.join()
            if "exc" in error_container:
                raise error_container["exc"]
            return result_container.get("result")
        # No running loop: create one and run
        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


def generate_comparison_with_ai_from_bikes(bikes_to_compare: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Public entry: run async research per bike, then call Responses API for structured JSON output.

    Returns dict with intro, recommendation, bikes[], expert_tip. On error returns {"error": ...}.
    """
    if not client:
        return {"error": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."}
    
    try:
        research: List[Dict[str, Any]] = _run_coroutine_blocking(_gather_bikes_research(bikes_to_compare))
    except Exception as e:
        print(f"Error in async research: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Async research error: {str(e)}"}

    prompt = _build_comparison_prompt(bikes_to_compare, research)
    
    # Get category for adaptive system message
    category = bikes_to_compare[0].get('category') if bikes_to_compare else None
    sub_category = bikes_to_compare[0].get('sub_category') if bikes_to_compare else None
    system_message = _get_category_based_system_message(category, sub_category)

    # Use Chat Completions API directly for better JSON support
    # (Responses API doesn't support response_format and is less reliable for JSON)
    print(f"Using Chat Completions API with prompt length: {len(prompt)}")
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{system_message} "
                        "החזר JSON בלבד במבנה: { 'intro': str, 'recommendation': str, 'bikes': [ { 'name': str, 'pros': [str], 'cons': [str], 'best_for': str } ], 'expert_tip': str }."),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=2000,  # Increased for longer responses
            response_format={"type": "json_object"},  # Force JSON format
        )
        content = completion.choices[0].message.content.strip()
        print(f"Chat Completions response length: {len(content)}")
        print(f"Chat Completions response preview: {content[:500]}")
        
        # Try safe parsing
        parsed = _parse_json_safely(content)
        if parsed:
            print("Successfully parsed JSON from Chat Completions")
            return parsed
        
        print("Could not parse JSON from response")
        print(f"Full response: {content}")
        return {"error": "Could not parse JSON from response"}
    except Exception as e:
        print(f"Chat Completions API error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"OpenAI API error: {str(e)}"}
