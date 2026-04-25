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

HEBREW_TO_ENGLISH_KEYS = {
    "הערות מוצר": "product_notes",
    "שילדה": "frame",
    "מזלג קדמי": "fork",
    "בולם אחורי": "rear_shock",
    "מנוע": "motor",
    "בטריה": "battery",
    "ידיות הילוכים": "shifters",
    "מעביר אחורי": "rear_derailleur",
    "קראנק": "crankset",
    "ציר מרכזי": "bottom_bracket",
    "קסטה": "cassette",
    "שרשרת": "chain",
    "מעצורים": "brakes",
    "גלגלים": "wheels",
    "צמיגים": "tires",
    "אוכף": "saddle",
    "מוט אוכף": "seatpost",
    "כידון": "handlebar",
    "מוט כידון": "stem",
    "מיסבי היגוי": "headset",
    "פדלים": "pedals",
    "מעביר קדמי": "front_derailleur",
    "מעביר אחורי": "rear_derailleur",
}

# ----- Setup -----
BASE_URL = "https://pedalim.co.il"
CHATGPT_API_KEY = os.getenv('SCRAPER_OPENAI_API_KEY', '')

scraped_data = []

PEDALIM_TARGET_URLS = [
    {"url": f"{BASE_URL}/אופניים-חשמליים", "category": "electric", "sub_category": "electric_mtb"},
    {"url": f"{BASE_URL}/אופניים-היברידיים-חשמליים", "category": "electric", "sub_category": "electric_city"},
    {"url": f"{BASE_URL}/אופני-הרים?סוג%20אופניים=307444&bsfilter-13166=307444", "category": "mtb", "sub_category": "hardtail"},
    {"url": f"{BASE_URL}/אופני-הרים?סוג%20אופניים=306187&bsfilter-13166=306187", "category": "mtb", "sub_category": "full_suspension"},
    {"url": f"{BASE_URL}/אופני-הרים?סוג%20אופניים=310291&bsfilter-13166=310291", "category": "mtb", "sub_category": "tandem"},
    {"url": f"{BASE_URL}/אופני-גראבל", "category": "gravel", "sub_category": "gravel"},
    {"url": f"{BASE_URL}/אופני-כביש", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/אופני-כביש?bscrp=2", "category": "road", "sub_category": "road"},
    {"url": f"{BASE_URL}/אופני-עיר", "category": "city", "sub_category": "city"},
    {"url": f"{BASE_URL}/אופני-ילדים", "category": "kids", "sub_category": "kids"},
    {"url": f"{BASE_URL}/אופני_נשים", "category": "city", "sub_category": "woman"},
]

def safe_to_int(text):
    try:
        return int(str(text).replace(',', '').replace('₪', '').strip())
    except (ValueError, AttributeError):
        return "צור קשר"

# ---------- Variant extraction (size + color) ----------
# Pedalim product pages embed all per-variant data as JS arrays in the page
# source (IdArrAss, sizeArr, colorArr, arrCode, stockArr, prodImage1..12).
# Each index across these arrays describes a single (size x color) variant.
def _js_string_array(html, var_name):
    """Extract a JS array of quoted strings, returning a Python list[str]."""
    pattern = rf"var\s+{re.escape(var_name)}\s*=\s*\[(.*?)\]\s*;"
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        return None
    items = re.findall(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'', m.group(1))
    return [a or b for a, b in items]

def _js_int_array(html, var_name):
    pattern = rf"var\s+{re.escape(var_name)}\s*=\s*\[([^\]]*)\]\s*;"
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        return None
    out = []
    for x in m.group(1).split(','):
        x = x.strip().strip("'\"")
        if not x:
            continue
        try:
            out.append(int(x))
        except ValueError:
            out.append(None)
    return out

def _js_string(html, var_name):
    pattern = rf"var\s+{re.escape(var_name)}\s*=\s*'((?:[^'\\]|\\.)*)'\s*;"
    m = re.search(pattern, html, re.DOTALL)
    return m.group(1) if m else None

def extract_pedalim_variants_live(driver, timeout=12):
    """Read live per-variant data from the page's `ListObj` JS variable.

    Pedalim product pages declare an initial ``stockArr = [0,0,0,0,...]`` that
    is almost always stale. The real stock is fetched after page load via
    ``bsGetStockAndPriceJson(arrCode, true)`` and each variant's live stock +
    sale price is then written into ``ListObj[<variant_id>]`` inside the page's
    ``$(document).ready`` handler. This helper polls the browser until
    ``ListObj`` has been populated for every id in ``IdArrAss`` and converts it
    to the same shape as :func:`extract_pedalim_variants`.

    Returns ``None`` if the page has no variants or the AJAX never populated
    ``ListObj`` within ``timeout`` seconds; callers should fall back to
    :func:`extract_pedalim_variants` in that case.
    """
    script = r"""
        try {
            var idArr = window.IdArrAss;
            var obj = window.ListObj;
            if (!idArr || !idArr.length || !obj) return null;
            var out = [];
            for (var i = 0; i < idArr.length; i++) {
                var id = idArr[i];
                var v = obj[id];
                if (!v) return null; // not populated yet — keep polling
                out.push({
                    variant_id: String(id),
                    size: v.size || null,
                    color: v.color || null,
                    sku: v.code || null,
                    stock: (typeof v.stock === 'number') ? v.stock : (v.stock != null ? parseInt(v.stock, 10) : null),
                    saleprice: v.saleprice != null ? v.saleprice : null,
                    img1: v.img1 || null,
                    img3: v.img3 || null,
                    img4: v.img4 || null,
                    img5: v.img5 || null,
                    img6: v.img6 || null,
                    img7: v.img7 || null,
                    img8: v.img8 || null,
                    img9: v.img9 || null,
                    img10: v.img10 || null,
                    img11: v.img11 || null,
                    img12: v.img12 || null
                });
            }
            return out;
        } catch (e) { return null; }
    """
    deadline = time.time() + timeout
    raw = None
    while time.time() < deadline:
        try:
            raw = driver.execute_script(script)
        except Exception:
            raw = None
        if raw:
            break
        time.sleep(0.25)
    if not raw:
        return None

    out = []
    for entry in raw:
        gallery = []
        for key in (
            "img1", "img3", "img4", "img5", "img6", "img7",
            "img8", "img9", "img10", "img11", "img12",
        ):
            path = (entry.get(key) or "").strip()
            if not path:
                continue
            full = path if path.startswith("http") else urljoin(BASE_URL + "/", path)
            if full not in gallery:
                gallery.append(full)
        stock_val = entry.get("stock")
        if isinstance(stock_val, bool):  # JS truthiness guard
            stock_val = int(stock_val)
        elif stock_val is not None and not isinstance(stock_val, int):
            try:
                stock_val = int(stock_val)
            except (TypeError, ValueError):
                stock_val = None
        out.append({
            "variant_id": entry.get("variant_id"),
            "size": (entry.get("size") or "").strip() or None,
            "color": (entry.get("color") or "").strip() or None,
            "sku": (entry.get("sku") or "").strip() or None,
            "stock": stock_val,
            "image_url": gallery[0] if gallery else None,
            "gallery_images_urls": gallery,
        })
    return out


def extract_pedalim_variants(html):
    """Extract size/color variants from a Pedalim product page.

    Returns a list of dicts, one per variant:
        {
            "variant_id": str,
            "size": str | None,
            "color": str | None,
            "sku": str | None,
            "stock": int | None,
            "image_url": str | None,           # primary image for this variant
            "gallery_images_urls": list[str],  # all images for this variant
        }
    Returns [] when the page has no variant data (e.g. single-SKU product).

    Note: the ``stock`` values come from the page's inlined ``stockArr`` which
    is frequently stale (often all zeros). Prefer
    :func:`extract_pedalim_variants_live` when a live Chrome driver is
    available.
    """
    ids = _js_int_array(html, "IdArrAss") or []
    if not ids:
        return []
    sizes = _js_string_array(html, "sizeArr") or []
    colors = _js_string_array(html, "colorArr") or []
    arr_code = _js_string(html, "arrCode") or ""
    skus = arr_code.split(";") if arr_code else []
    stocks = _js_int_array(html, "stockArr") or []

    image_arrays = []
    for i in [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
        arr = _js_string_array(html, f"prodImage{i}")
        if arr:
            image_arrays.append(arr)

    variants = []
    for idx, vid in enumerate(ids):
        gallery = []
        for arr in image_arrays:
            if idx < len(arr):
                p = (arr[idx] or "").strip()
                if not p:
                    continue
                full = p if p.startswith("http") else urljoin(BASE_URL + "/", p)
                if full not in gallery:
                    gallery.append(full)
        variants.append({
            "variant_id": str(vid),
            "size": sizes[idx].strip() if idx < len(sizes) and sizes[idx] else None,
            "color": colors[idx].strip() if idx < len(colors) and colors[idx] else None,
            "sku": skus[idx].strip() if idx < len(skus) and skus[idx].strip() else None,
            "stock": stocks[idx] if idx < len(stocks) else None,
            "image_url": gallery[0] if gallery else None,
            "gallery_images_urls": gallery,
        })
    return variants


# ---------- DOM-based variant extraction ----------
# Pedalim product pages also expose size/color pickers as buttons:
#   <div id="size"><button value="<idx>" onclick="setImage(<imgId>);setColor2(<colorId>)">XS</button> ...</div>
#   <div id="color"><button id="s<colorId>" onclick="setImage(<colorId>);selectedProduct(<colorId>)"
#                           class="stock_in|stock_out [active]" mystock="<N>">label</button> ...</div>
# This gives us ordered Hebrew labels, the "default" selection, stock per color,
# and the primary image for each color (via setImage argument).
_ONCLICK_SETIMAGE_RE = re.compile(r"setImage\(\s*(\d+)\s*\)")
_ONCLICK_SETCOLOR2_RE = re.compile(r"setColor2\(\s*(\d+)\s*\)")


def _resolve_image_url(img_id, soup):
    """Best-effort resolve an image id (from setImage(<id>)) to a URL.

    Pedalim's setImage() uses the prodImage* arrays as the actual image source.
    Most of the time we can recover the URL from the gallery thumbnails on the
    page (they share the same file naming). If we cannot resolve it, return
    None and let the JS-array merge fill it in.
    """
    if not img_id or not soup:
        return None
    # Look for an img tag whose URL contains the id as a number token.
    pattern = re.compile(rf"(?<!\d){re.escape(str(img_id))}(?!\d)")
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
        if src and pattern.search(src):
            src = src.strip()
            return src if src.startswith("http") else urljoin(BASE_URL, src)
    return None


def extract_pedalim_variants_dom(page_soup):
    """Parse size/color button groups from the Pedalim product page DOM.

    Returns:
        {
            "colors": [
                {"color_id": str, "label": str, "image_id": str|None,
                 "image_url": str|None, "total_stock": int, "in_stock": bool,
                 "is_default": bool, "position": int}
            ],
            "sizes": [
                {"label": str, "value": str|None, "image_id": str|None,
                 "color_id": str|None, "is_default": bool, "position": int}
            ],
        }
    Returns {"colors": [], "sizes": []} when neither picker exists.
    """
    result = {"colors": [], "sizes": []}
    if page_soup is None:
        return result

    color_div = page_soup.find("div", id="color")
    if color_div:
        for pos, btn in enumerate(color_div.find_all("button")):
            btn_id = (btn.get("id") or "").strip()
            color_id = btn_id[1:] if btn_id.startswith("s") else btn_id or None
            label = btn.get_text(strip=True)
            onclick = btn.get("onclick") or ""
            img_match = _ONCLICK_SETIMAGE_RE.search(onclick)
            image_id = img_match.group(1) if img_match else color_id
            classes = btn.get("class") or []
            class_str = " ".join(classes)
            try:
                total_stock = int((btn.get("mystock") or "0").strip() or 0)
            except ValueError:
                total_stock = 0
            in_stock = "stock_in" in class_str or total_stock > 0
            if "stock_out" in class_str:
                in_stock = False
            result["colors"].append({
                "color_id": str(color_id) if color_id else None,
                "label": label or None,
                "image_id": str(image_id) if image_id else None,
                "image_url": _resolve_image_url(image_id, page_soup),
                "total_stock": total_stock,
                "in_stock": bool(in_stock),
                "is_default": "active" in classes,
                "position": pos,
            })

    size_div = page_soup.find("div", id="size")
    if size_div:
        for pos, btn in enumerate(size_div.find_all("button")):
            label = btn.get_text(strip=True)
            onclick = btn.get("onclick") or ""
            img_match = _ONCLICK_SETIMAGE_RE.search(onclick)
            color2_match = _ONCLICK_SETCOLOR2_RE.search(onclick)
            classes = btn.get("class") or []
            result["sizes"].append({
                "label": label or None,
                "value": (btn.get("value") or "").strip() or None,
                "image_id": img_match.group(1) if img_match else None,
                "color_id": color2_match.group(1) if color2_match else None,
                "is_default": "active" in classes,
                "position": pos,
            })

    return result


# ---------- Merge JS-array variants with DOM buttons ----------
def merge_variants(js_variants, dom):
    """Merge the flat JS-array per-(size,color) list with DOM color/size buttons.

    Produces the normalized shape consumed by the rest of the pipeline:
        {
            "sizes": [label, ...],                # ordered by DOM, fallback to JS
            "colors": [
                {
                    "color_id": str,
                    "label": str,
                    "image_url": str|None,
                    "gallery_images_urls": [str, ...],
                    "total_stock": int,
                    "in_stock": bool,
                    "is_default": bool,
                    "position": int,
                    "sizes": {
                        size_label: {"sku": str|None, "stock": int|None, "in_stock": bool}
                    }
                }
            ],
        }
    Returns None when neither source yields any data.
    """
    dom = dom or {"colors": [], "sizes": []}
    js_variants = js_variants or []

    # ---- Ordered size labels ----
    size_labels_ordered = []
    for s in dom.get("sizes", []):
        lbl = (s.get("label") or "").strip()
        if lbl and lbl not in size_labels_ordered:
            size_labels_ordered.append(lbl)
    if not size_labels_ordered:
        for v in js_variants:
            lbl = (v.get("size") or "").strip()
            if lbl and lbl not in size_labels_ordered:
                size_labels_ordered.append(lbl)

    # ---- Group JS variants by color label for later lookup ----
    js_by_color_label = {}
    for v in js_variants:
        color_lbl = (v.get("color") or "").strip()
        if not color_lbl:
            continue
        js_by_color_label.setdefault(color_lbl, []).append(v)

    colors_out = []

    # Prefer DOM colors as the canonical list (Hebrew labels, order, stock flags).
    dom_colors = dom.get("colors", [])
    if dom_colors:
        for dc in dom_colors:
            label = dc.get("label")
            color_id = dc.get("color_id")
            js_rows = js_by_color_label.get(label, []) if label else []
            # Build per-size lookup for this color.
            sizes_map = {}
            gallery = []
            primary_image = dc.get("image_url")
            for size_lbl in size_labels_ordered:
                # Find the JS variant matching (size, color).
                match = next(
                    (v for v in js_rows if (v.get("size") or "").strip() == size_lbl),
                    None,
                )
                if match:
                    stock = match.get("stock")
                    sizes_map[size_lbl] = {
                        "sku": match.get("sku"),
                        "stock": stock,
                        "in_stock": bool(stock) if stock is not None else dc.get("in_stock", False),
                    }
                    for img in match.get("gallery_images_urls") or []:
                        if img and img not in gallery:
                            gallery.append(img)
                    if not primary_image and match.get("image_url"):
                        primary_image = match.get("image_url")
                else:
                    sizes_map[size_lbl] = {
                        "sku": None,
                        "stock": None,
                        "in_stock": False,
                    }
            # If the color has no per-size data (e.g., bike without sizes), and
            # there is exactly one JS row for this color, use it for primary image.
            if not sizes_map and js_rows:
                row = js_rows[0]
                if not primary_image:
                    primary_image = row.get("image_url")
                for img in row.get("gallery_images_urls") or []:
                    if img and img not in gallery:
                        gallery.append(img)
            # When we have per-size data, derive the color-level stock totals
            # from the merged sizes_map. The DOM button's ``mystock`` attribute
            # reflects only the *currently selected* variant (Pedalim reuses
            # the #color div to echo the active size on single-color bikes),
            # so using it as the color total would mark in-stock sizes as OOS.
            if sizes_map:
                size_stocks = [
                    s.get("stock") for s in sizes_map.values()
                    if isinstance(s.get("stock"), int)
                ]
                if size_stocks:
                    color_total_stock = sum(size_stocks)
                    color_in_stock = color_total_stock > 0
                else:
                    color_total_stock = dc.get("total_stock", 0)
                    color_in_stock = any(
                        s.get("in_stock") for s in sizes_map.values()
                    ) or dc.get("in_stock", False)
            else:
                color_total_stock = dc.get("total_stock", 0)
                color_in_stock = dc.get("in_stock", False)
            colors_out.append({
                "color_id": color_id,
                "label": label,
                "image_url": primary_image,
                "gallery_images_urls": gallery,
                "total_stock": color_total_stock,
                "in_stock": color_in_stock,
                "is_default": dc.get("is_default", False),
                "position": dc.get("position", len(colors_out)),
                "sizes": sizes_map,
            })
    elif js_variants:
        # DOM has no colors; synthesize from JS-array grouping.
        ordered_color_labels = []
        for v in js_variants:
            lbl = (v.get("color") or "").strip()
            if lbl and lbl not in ordered_color_labels:
                ordered_color_labels.append(lbl)
        for pos, label in enumerate(ordered_color_labels):
            rows = js_by_color_label.get(label, [])
            sizes_map = {}
            gallery = []
            primary_image = None
            total_stock = 0
            for size_lbl in size_labels_ordered or [None]:
                match = None
                if size_lbl is None:
                    match = rows[0] if rows else None
                else:
                    match = next(
                        (v for v in rows if (v.get("size") or "").strip() == size_lbl),
                        None,
                    )
                if match:
                    stock = match.get("stock")
                    if size_lbl is not None:
                        sizes_map[size_lbl] = {
                            "sku": match.get("sku"),
                            "stock": stock,
                            "in_stock": bool(stock) if stock is not None else False,
                        }
                    if isinstance(stock, int):
                        total_stock += stock
                    if not primary_image and match.get("image_url"):
                        primary_image = match.get("image_url")
                    for img in match.get("gallery_images_urls") or []:
                        if img and img not in gallery:
                            gallery.append(img)
            # Use the first JS row's variant_id as color_id fallback.
            first_row = rows[0] if rows else {}
            colors_out.append({
                "color_id": str(first_row.get("variant_id")) if first_row.get("variant_id") else None,
                "label": label,
                "image_url": primary_image,
                "gallery_images_urls": gallery,
                "total_stock": total_stock,
                "in_stock": total_stock > 0,
                "is_default": pos == 0,
                "position": pos,
                "sizes": sizes_map,
            })
    else:
        return None

    if not colors_out and not size_labels_ordered:
        return None

    # Ensure at least one default color is flagged.
    if colors_out and not any(c.get("is_default") for c in colors_out):
        for c in colors_out:
            if c.get("in_stock"):
                c["is_default"] = True
                break
        else:
            colors_out[0]["is_default"] = True

    return {
        "sizes": size_labels_ordered,
        "colors": colors_out,
    }

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

def rewrite_description_with_chatgpt(original_text, api_key):
    """Rewrite product description using ChatGPT API"""
    if not original_text or not api_key:
        return original_text
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "אתה מומחה לכתיבת תוכן שיווקי לאופניים בחנויות אינטרנטיות..."},
                {"role": "user", "content": f"להלן תיאור האופניים: \n\n{original_text}\n\nכתוב גרסה שיווקית חדשה."}
            ],
            "temperature": 0.6,
            "max_tokens": 500
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except:
        return original_text

def pedalim_bikes(driver, output_file):
    for entry in PEDALIM_TARGET_URLS:
        target_url = entry["url"]
        category_text = entry["category"]
        sub_category_text = entry.get("sub_category", None)
        print(f"\n🌐 Scraping: {target_url}")
        driver.get(target_url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("div", class_="col-xs-6 col-sm-4 col-md-4 col-lg-4")
        print(f"✅ Found {len(cards)} products.\n")
        for i, product in enumerate(cards):
            print(f"--- Processing Product {i+1} ---")
            # ---- Basic Info ----
            firm_tag = product.find("div", class_="description")
            firm_text = firm_tag.find("span").get_text(strip=True) if firm_tag else "N/A"
            model_tag = product.find("div", class_="description")
            model_text = firm_tag.find("h2").get_text(strip=True) if model_tag else "N/A"
            model_text = re.sub(r"^[\u0590-\u05FF\s]+(?=[A-Za-z])", "", model_text).strip()
            if firm_text and model_text:
                model_text = re.sub(re.escape(firm_text), "", model_text, flags=re.IGNORECASE).strip()
            year_tag = product.find(class_="newOnSite")
            year_text = "לא צויין"
            if year_tag:
                match = re.search(r"\b(20\d{2})\b", year_tag.get_text(strip=True))
                year_text = match.group(1) if match else "לא צויין"
            # ---- Price ----
            oldprice_tag = product.find("span", class_="oldprice")
            saleprice_tag = product.select_one("span.saleprice")
            regular_price_tag = product.find("span", class_="price")
            original_price = disc_price = ""
            if oldprice_tag and saleprice_tag:
                original_price = safe_to_int(oldprice_tag.get_text(strip=True))
                disc_price = safe_to_int(saleprice_tag.get_text(strip=True))
            elif regular_price_tag:
                original_price = safe_to_int(regular_price_tag.get_text(strip=True))
            elif saleprice_tag:
                original_price = safe_to_int(saleprice_tag.get_text(strip=True))
            else:
                original_price = "צור קשר"
            # ---- Image ----
            img_tag = product.find("img")
            img_src = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
            img_url = urljoin(BASE_URL, img_src) if img_src else "N/A"
            # ---- Link ----
            link_tag = product.find("a", href=True)
            product_url = urljoin(BASE_URL, link_tag["href"]) if link_tag else "N/A"
            product_data = {
                "source": {"importer": "Pedalim", "domain": BASE_URL, "product_url": product_url},
                "firm": firm_text,
                "model": model_text,
                "year": year_text,
                "category": category_text,
                "sub_category": sub_category_text,
                "original_price": original_price,
                "disc_price": disc_price,
                "images": {"image_url": img_url, "gallery_images_urls": []},
                "specs": {}
            }
            # ---- Product Page ----
            if product_url != "N/A":
                try:
                    driver.get(product_url)
                    time.sleep(4)
                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    # Description
                    desc_element = page_soup.find("ul", class_="desc_bullet")
                    if desc_element:
                        description_text = " ".join([li.get_text(strip=True) for li in desc_element.find_all("li")])
                    else:
                        description_text = ""
                    rewritten_description = rewrite_description_with_chatgpt(description_text, CHATGPT_API_KEY) if description_text else ""
                    product_data["rewritten_description"] = rewritten_description
                    # Gallery images
                    gallery_images_urls = []
                    thumbs_div = page_soup.find("div", class_="sp-thumbnails sp-grab")
                    if thumbs_div:
                        for img in thumbs_div.find_all("img", class_="sp-thumbnail"):
                            # Try multiple src attributes (lazy loading often uses data-src)
                            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                            if src:
                                src = src.strip()  # Remove any whitespace
                                if src and not src.startswith("http"):
                                    src = urljoin(BASE_URL, src)
                                # Only add non-empty URLs
                                if src and src not in gallery_images_urls:
                                    gallery_images_urls.append(src)
                    # Also try alternative selectors if no images found
                    if not gallery_images_urls:
                        # Try finding images in other common gallery structures
                        gallery_imgs = page_soup.find_all("img", class_="sp-thumbnail")
                        for img in gallery_imgs:
                            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                            if src:
                                src = src.strip()
                                if src and not src.startswith("http"):
                                    src = urljoin(BASE_URL, src)
                                if src and src not in gallery_images_urls:
                                    gallery_images_urls.append(src)
                    product_data["images"]["gallery_images_urls"] = gallery_images_urls
                    # ---- Variants (size + color combinations) ----
                    # Each variant carries its own image set so the frontend
                    # can swap the displayed image when the user picks a
                    # specific size/color, mirroring pedalim.co.il behavior.
                    try:
                        # Prefer live JS state: Pedalim fetches real stock via
                        # AJAX (bsGetStockAndPriceJson) after page load and
                        # stashes it in ListObj. The inline stockArr in the
                        # page source is almost always stale (often all zeros).
                        js_variants = extract_pedalim_variants_live(driver)
                        if not js_variants:
                            js_variants = extract_pedalim_variants(driver.page_source)
                        dom_variants = extract_pedalim_variants_dom(page_soup)
                        merged = merge_variants(js_variants, dom_variants)
                        if merged and (merged.get("colors") or merged.get("sizes")):
                            product_data["variants"] = merged
                    except Exception as e:
                        print(f"  ⚠️ Failed to extract variants: {e}")
                    # ---- Specs ----
                    # Try multiple selectors for specs list
                    spec_list = None
                    specs_found = False
                    possible_selectors = [
                        ("ul", {"class": "list-unstyled"}),
                        ("ul", {"class": "list-unstyled properties-product"}),
                        ("ul", {"class": "properties-product"}),
                        ("div", {"class": "properties-product"}),
                        ("div", {"id": "specifications"}),
                        ("div", {"class": "product-specs"}),
                    ]
                    
                    for tag_name, attrs in possible_selectors:
                        spec_list = page_soup.find(tag_name, attrs)
                        if spec_list:
                            break
                    
                    if spec_list:
                        for li in spec_list.find_all("li"):
                            # Remove images from text extraction
                            for img in li.find_all("img"): img.decompose()
                            
                            # Try multiple methods to extract key and value
                            key = None
                            val = None
                            
                            # Method 1: Look for span with class "attributeList" (original method)
                            val_tag = li.find("span", class_="attributeList")
                            if val_tag:
                                val = val_tag.get_text(strip=True)
                                full_text = li.get_text(strip=True)
                                key = full_text.replace(val, "").strip()
                            else:
                                # Method 2: Look for spans with title/value classes
                                key_tag = li.find("span", class_="titleKey") or li.find("span", class_="title")
                                val_tag = li.find("span", class_="valueKey") or li.find("span", class_="value")
                                
                                if key_tag and val_tag:
                                    key = key_tag.get_text(strip=True)
                                    val = val_tag.get_text(strip=True)
                                else:
                                    # Method 3: Look for any spans - first is key, second is value
                                    spans = li.find_all("span")
                                    if len(spans) >= 2:
                                        key = spans[0].get_text(strip=True)
                                        val = spans[1].get_text(strip=True)
                                    elif len(spans) == 1:
                                        # Single span might be the value, key is rest of text
                                        val = spans[0].get_text(strip=True)
                                        full_text = li.get_text(strip=True)
                                        key = full_text.replace(val, "").strip()
                                    else:
                                        # Method 4: Look for bold/strong tags as keys
                                        bold_tag = li.find("b") or li.find("strong")
                                        if bold_tag:
                                            key = bold_tag.get_text(strip=True)
                                            full_text = li.get_text(strip=True)
                                            val = full_text.replace(key, "").strip()
                                        else:
                                            # Method 5: Split by colon or dash if present
                                            full_text = li.get_text(strip=True)
                                            if ":" in full_text:
                                                parts = full_text.split(":", 1)
                                                key = parts[0].strip()
                                                val = parts[1].strip()
                                            elif "-" in full_text and len(full_text.split("-", 1)) == 2:
                                                parts = full_text.split("-", 1)
                                                key = parts[0].strip()
                                                val = parts[1].strip()
                            
                            if key and val and key != "הערות מוצר":
                                english_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)
                                product_data["specs"][english_key] = val
                                specs_found = True
                    
                    # If still no specs found, try looking for any ul with li elements containing specs
                    if not product_data["specs"]:
                        all_uls = page_soup.find_all("ul")
                        for ul in all_uls:
                            lis = ul.find_all("li")
                            if len(lis) > 3:  # Likely a specs list if it has multiple items
                                for li in lis:
                                    for img in li.find_all("img"): img.decompose()
                                    full_text = li.get_text(strip=True)
                                    if ":" in full_text:
                                        parts = full_text.split(":", 1)
                                        key = parts[0].strip()
                                        val = parts[1].strip()
                                        if key and val and key != "הערות מוצר" and len(key) < 50:  # Reasonable key length
                                            english_key = HEBREW_TO_ENGLISH_KEYS.get(key, key)
                                            product_data["specs"][english_key] = val
                                            specs_found = True
                                if product_data["specs"]:
                                    break
                    
                    # Debug output if no specs found
                    if not specs_found and not product_data["specs"]:
                        print(f"  ⚠️ No specs found for {product_data.get('firm', 'N/A')} {product_data.get('model', 'N/A')}")
                except Exception as e:
                    print(f"⚠️ Error scraping product page ({product_url}): {e}")
            # ---- Battery Wh ----
            battery_value = product_data.get("specs", {}).get("battery", "")
            wh_match = re.search(r"(\d+)\s*Wh", battery_value, re.IGNORECASE)
            if wh_match:
                product_data["wh"] = int(wh_match.group(1))
            else:
                fallback_match = re.search(r"\b(\d{3})\b", battery_value)
                if fallback_match:
                    product_data["wh"] = int(fallback_match.group(1))
            # ---- Fork length & style ----
            fork_text = product_data.get("specs", {}).get("fork", "")
            match = re.search(r'(?<!\d)(40|50|60|70|80|90|100|110|120|130|140|150|160|170|180)(?!\d)\s*(?:mm)?', fork_text.lower())
            fork_length = int(match.group(1)) if match else None
            product_data["fork length"] = fork_length
            if fork_length:
                if fork_length in [40, 50, 60, 70, 80, 90, 100, 110, 120]: product_data["style"] = "cross-country"
                elif fork_length in [130, 140, 150]: product_data["style"] = "trail"
                elif fork_length in [160, 170, 180]: product_data["style"] = "enduro"
            # Kids bike wheel size (only when category is kids)
            if category_text == "kids":
                wheel_size = extract_wheel_size_for_kids_bike(
                    product_data.get("model"),
                    product_data.get("specs"),
                )
                if wheel_size is not None:
                    product_data["wheel_size"] = wheel_size
            scraped_data.append(product_data)
            # ---- Save progress ----
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(scraped_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"⚠️ Could not save progress: {e}")
        print(f"✅ Completed {category_text}: {len([p for p in scraped_data if p.get('category') == category_text])} products")
    return scraped_data

# --- Setup Output File ---
if __name__ == '__main__':
    try:
        project_root = Path(__file__).resolve().parents[2]
        output_dir = project_root / "data" / "scraped_raw_data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = output_dir / "pedalim_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Error setting up output directory: {e}")
        exit(1)

    # --- Run Scraper ---
    products = []
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless=new')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        driver = uc.Chrome(options=options, version_main=146)
        products = pedalim_bikes(driver, output_file)
    except Exception as e:
        print(f"❌ Chrome driver error: {e}")
    finally:
        if driver: driver.quit()

    print(f"\n✅ Scraping completed! Total products: {len(products)}. Saved to {output_file}")
