# Brand/Firm Standardization Plan

## Goal
Standardize on **brand** throughout the app. "firm" is legacy (Hebrew "חברה" = company).

## Current State
- **Database:** `Brand` model, `bikes.brand_id` → correct
- **JSON/scrapers:** Use `firm` (source data - keep for migration)
- **Bike.to_dict flat:** Outputs `firm` only
- **Bike.to_dict nested:** Outputs `brand` only
- **Templates:** Use `firms`, `bike['firm']`
- **bikes.js:** adaptBikeData converts `firm` → `brand` for display

## Steps (in order) ✅ COMPLETED

### Step 1: Bike model – add brand to flat format ✅
- In `_to_dict_flat()`, add `'brand': self.brand.name` 
- Keep `'firm'` as alias (same value) for backward compat
- Result: Both keys in output, no breaking changes

### Step 2: bike_service – add brand-named functions ✅
- Add `get_all_brands()` = `get_all_firms()` 
- Add `get_brands_by_category()` = `get_firms_by_category()`
- Keep old functions as aliases (call new ones)
- Update routes to use new names internally

### Step 3: Templates – use brands variable, bike.brand with fallback ✅
- Pass `brands` to templates (same data as firms)
- Use `bike['brand'] or bike['firm']` for display
- Rename firmDropdown → brandDropdown, firm-checkbox → brand-checkbox (optional, can defer)

### Step 4: bikes.js – use brand consistently ✅
- In adaptBikeData: use `brand: bike.brand || bike.firm`
- In filters: use `bike.brand || bike.firm`
- Simplify – no conversion needed when both exist

### Step 5: API routes – support brands param ✅
- filter_bikes: accept `brands` param, map to firms for DB query
- compare.py: always_show use "brand"
- ai_service: use bike.get("brand", bike.get("firm", ""))

### Step 6: Final cleanup ✅
- Remove firm from Bike model flat output
- Remove get_all_firms, get_firms_by_category
- Remove firm fallbacks from templates (use bike['brand'] only)
- Remove firm from bikes.js, similar_bikes.js, ai_service
- filter_bikes API: brands param only (firm removed)

## Files to modify (by step)

| Step | Files |
|------|-------|
| 1 | app/models/models.py |
| 2 | app/services/bike_service.py, app/routes/bikes.py, app/routes/main.py |
| 3 | templates/bikes.html, templates/home.html, templates/compare_bikes.html, templates/shared_comparison.html |
| 4 | static/js/bikes.js |
| 5 | app/routes/bikes.py (filter_bikes), app/routes/compare.py, app/services/ai_service.py |
| 6 | All above (remove firm) |
