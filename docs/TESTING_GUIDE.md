# Testing Guide for Backward Compatibility Removal

## 📋 Overview

This guide explains how to test the migration from old format to new format using the feature flag system.

---

## 🚩 Feature Flag Control

### What is USE_NEW_BIKE_FORMAT?

A configuration variable that switches between:
- **`false`** (default) = Old flat format (backward compatibility)
- **`true`** = New normalized format (target)

### Method 1: Environment Variable (Quick Testing)

**Windows PowerShell** (Your Current Shell):

```powershell
# Set flag to TRUE (new format)
$env:USE_NEW_BIKE_FORMAT="true"
python app.py

# Set flag to FALSE (old format)  
$env:USE_NEW_BIKE_FORMAT="false"
python app.py

# Check current value
echo $env:USE_NEW_BIKE_FORMAT

# Remove variable (defaults to false)
Remove-Item Env:\USE_NEW_BIKE_FORMAT
```

**Windows CMD**:
```cmd
set USE_NEW_BIKE_FORMAT=true
python app.py
```

**Linux/Mac**:
```bash
export USE_NEW_BIKE_FORMAT=true
python app.py
```

### Method 2: .env File (Persistent - Recommended)

Create or edit `.env` file in project root:

```bash
# .env
USE_NEW_BIKE_FORMAT=false   # Start with old format (safe)
```

The app already loads `.env` via `python-dotenv` package.

**To switch formats**:
1. Edit `.env` file
2. Change `USE_NEW_BIKE_FORMAT=true` or `=false`
3. Restart the app

### Method 3: Config File (For Testing Only)

**Temporary hardcode in `app/config.py`**:
```python
# For testing only - don't commit this!
USE_NEW_BIKE_FORMAT = True  # or False
```

---

## 🧪 Testing Workflow

### Phase-by-Phase Testing

#### Phase 1: Backend Testing (After implementing serialization)

**Test 1: New Serialization Function**
```powershell
# Run in project directory
cd C:\Users\roman\Code\emtb_site

# Activate virtual environment
.\env\Scripts\activate

# Run Python shell
python

# Test the new serialization
>>> from app.models import Bike
>>> from app.extensions import db
>>> from app import create_app
>>> app = create_app()
>>> with app.app_context():
...     bike = Bike.query.first()
...     from app.services.bike_service import serialize_bike
...     result = serialize_bike(bike)
...     import json
...     print(json.dumps(result, indent=2, ensure_ascii=False))
```

**Expected Output**: Should see nested structure with `brand`, `listing`, `specs`, `images`

**Test 2: Feature Flag Switching**
```python
>>> from app.config import Config
>>> print(Config.USE_NEW_BIKE_FORMAT)  # Should be False by default
>>> 
>>> # Test the wrapper
>>> from app.services.bike_service import get_bike_serializer
>>> serializer = get_bike_serializer()
>>> print(serializer.__name__)  # Should show which function is active
```

---

#### Phase 2-3: Frontend & Template Testing

**Start the development server:**
```powershell
# With OLD format (safe - default)
$env:USE_NEW_BIKE_FORMAT="false"
python app.py
```

**Test Checklist** (do this with BOTH flag settings):

1. **Homepage** (`http://localhost:5000/`)
   - [ ] Page loads without errors
   - [ ] Top bikes display correctly
   - [ ] No console errors (F12 → Console)

2. **Bikes Page** (`http://localhost:5000/bikes`)
   - [ ] All bikes display
   - [ ] Prices show correctly
   - [ ] Search works
   - [ ] Category filtering works
   - [ ] Price slider works
   - [ ] Battery slider works
   - [ ] Brand dropdown works
   - [ ] Motor brand dropdown works
   - [ ] Click "פרטים" (Details) button → modal opens
   - [ ] All specs display in modal
   - [ ] Gallery images work in modal
   - [ ] No console errors

3. **Comparison Page** (`http://localhost:5000/compare_bikes`)
   - [ ] Add bikes to comparison (from bikes page)
   - [ ] Comparison page loads
   - [ ] All bike details display
   - [ ] AI comparison runs
   - [ ] Share button works
   - [ ] Remove bikes works
   - [ ] No console errors

4. **Shared Comparison** 
   - [ ] Create a comparison
   - [ ] Copy share link
   - [ ] Open in incognito/private window
   - [ ] Shared comparison displays correctly

---

### Manual Test Script

Create `tests/test_feature_flag.py`:

```python
#!/usr/bin/env python3
"""
Test script to verify feature flag switching
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.models import Bike
from app.extensions import db
from app.services.bike_service import serialize_bike, convert_new_bike_to_old_format, get_bike_serializer
import json

def test_feature_flag():
    """Test that feature flag correctly switches serializers"""
    
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing Feature Flag System\n")
        print("=" * 60)
        
        # Check current flag value
        from app.config import Config
        flag_value = getattr(Config, 'USE_NEW_BIKE_FORMAT', False)
        print(f"📍 Feature Flag Value: {flag_value}")
        print(f"📍 Flag Type: {'NEW FORMAT' if flag_value else 'OLD FORMAT'}")
        print("=" * 60)
        
        # Get a test bike
        bike = Bike.query.first()
        if not bike:
            print("❌ No bikes found in database")
            return
        
        print(f"\n🚲 Test Bike: {bike.brand.name if bike.brand else 'Unknown'} {bike.model}")
        print("=" * 60)
        
        # Test both serializers
        print("\n1️⃣ Testing OLD format (convert_new_bike_to_old_format):")
        print("-" * 60)
        old_format = convert_new_bike_to_old_format(bike)
        print(f"   - Type: {type(old_format)}")
        print(f"   - Keys (first 10): {list(old_format.keys())[:10]}")
        print(f"   - Has 'firm' key: {'firm' in old_format}")
        print(f"   - Has 'brand' key: {'brand' in old_format}")
        print(f"   - Has 'specs' key: {'specs' in old_format}")
        print(f"   - Motor access: bike['motor'] = {old_format.get('motor', 'N/A')}")
        
        print("\n2️⃣ Testing NEW format (serialize_bike):")
        print("-" * 60)
        new_format = serialize_bike(bike)
        print(f"   - Type: {type(new_format)}")
        print(f"   - Keys: {list(new_format.keys())}")
        print(f"   - Has 'firm' key: {'firm' in new_format}")
        print(f"   - Has 'brand' key: {'brand' in new_format}")
        print(f"   - Has 'listing' key: {'listing' in new_format}")
        print(f"   - Has 'specs' key: {'specs' in new_format}")
        print(f"   - Motor access: bike.specs['motor'] = {new_format.get('specs', {}).get('motor', 'N/A')}")
        
        print("\n3️⃣ Testing get_bike_serializer() wrapper:")
        print("-" * 60)
        serializer = get_bike_serializer()
        print(f"   - Active serializer: {serializer.__name__}")
        print(f"   - Expected: {'serialize_bike' if flag_value else 'convert_new_bike_to_old_format'}")
        
        result = serializer(bike)
        print(f"   - Result type: {type(result)}")
        print(f"   - Has 'brand' key: {'brand' in result}")
        print(f"   - Has 'firm' key: {'firm' in result}")
        
        # Verify correct serializer is used
        if flag_value:  # Should use NEW format
            if 'brand' in result and 'specs' in result:
                print("   ✅ Correctly using NEW format")
            else:
                print("   ❌ Flag is TRUE but using OLD format!")
        else:  # Should use OLD format
            if 'firm' in result and 'motor' in result:
                print("   ✅ Correctly using OLD format")
            else:
                print("   ❌ Flag is FALSE but using NEW format!")
        
        print("\n" + "=" * 60)
        print("🎯 Test Complete")
        print("=" * 60)
        
        # Show sample output
        print("\n📄 Sample Output (first 500 chars):")
        print("-" * 60)
        sample = json.dumps(result, ensure_ascii=False, indent=2)[:500]
        print(sample + "...")

if __name__ == "__main__":
    test_feature_flag()
```

**Run the test:**
```powershell
# Test with OLD format
$env:USE_NEW_BIKE_FORMAT="false"
python tests/test_feature_flag.py

# Test with NEW format
$env:USE_NEW_BIKE_FORMAT="true"
python tests/test_feature_flag.py
```

---

### Browser Testing Checklist

**Open Developer Console** (F12) → Console tab

#### Test with Flag = FALSE (Old Format)
```powershell
$env:USE_NEW_BIKE_FORMAT="false"
python app.py
```

Go to `http://localhost:5000/bikes`:

1. Open Console (F12)
2. Type: `fetch('/api/bike/SOME-UUID').then(r => r.json()).then(console.log)`
3. Check response structure:
   - ✅ Should have `firm` key
   - ✅ Should have flat spec fields (`motor`, `battery`, etc.)
   - ❌ Should NOT have `brand`, `listing`, `specs` keys

#### Test with Flag = TRUE (New Format)
```powershell
$env:USE_NEW_BIKE_FORMAT="true"  
python app.py
```

Go to `http://localhost:5000/bikes`:

1. Open Console (F12)
2. Same fetch command
3. Check response structure:
   - ✅ Should have `brand` key
   - ✅ Should have `listing` object
   - ✅ Should have `specs` object
   - ✅ Should have `images` array
   - ❌ Should NOT have `firm`, flat `motor` keys

---

## 🔍 Debugging Tips

### Check Current Flag Value

**In Python:**
```python
from app.config import Config
print(f"Feature flag: {Config.USE_NEW_BIKE_FORMAT}")
```

**In Browser Console:**
```javascript
// Fetch a bike and inspect structure
fetch('/api/bike/BIKE-UUID-HERE')
  .then(r => r.json())
  .then(bike => {
    console.log('Has brand?', 'brand' in bike);
    console.log('Has firm?', 'firm' in bike);
    console.log('Has specs?', 'specs' in bike);
    console.log('Structure:', Object.keys(bike));
  });
```

### Common Issues

**Issue**: Flag doesn't seem to work
- **Solution**: Make sure to restart Flask app after changing env variable
- **Check**: Print `Config.USE_NEW_BIKE_FORMAT` in your route to verify

**Issue**: Page shows old format even with flag=true
- **Solution**: Clear browser cache (Ctrl+Shift+Delete)
- **Solution**: Clear Flask cache: `cache.clear()`
- **Check**: Inspect API response in Network tab

**Issue**: Console errors about undefined properties
- **Solution**: This is expected during migration - the adapter should handle it
- **Check**: Verify adapter function is being used

---

## 📊 Testing Progression

### Week 1: Development Testing
- [ ] Test with flag OFF (baseline - should work perfectly)
- [ ] Implement Phase 1 (backend)
- [ ] Test new serialization in Python shell
- [ ] Test feature flag switching

### Week 2: Integration Testing  
- [ ] Implement Phase 2-4 (frontend + templates + routes)
- [ ] Test with flag OFF (should still work)
- [ ] Test with flag ON (new format)
- [ ] Fix any issues found

### Week 3: UAT (User Acceptance Testing)
- [ ] Deploy to staging with flag OFF
- [ ] Test all functionality
- [ ] Enable flag on staging
- [ ] Full regression testing
- [ ] Performance comparison

### Week 4: Production
- [ ] Deploy to production with flag OFF
- [ ] Monitor for 24 hours
- [ ] Enable flag on production
- [ ] Monitor closely
- [ ] Rollback plan ready

---

## 🚨 Rollback Procedures

### Quick Rollback (If Issues Found)

**Option 1: Flip the Flag**
```powershell
# Just turn off the new format
$env:USE_NEW_BIKE_FORMAT="false"

# Or in .env file
USE_NEW_BIKE_FORMAT=false

# Restart app
python app.py
```

**Option 2: Git Revert**
```bash
# If code has issues
git revert HEAD
git push

# Or checkout previous working commit
git checkout <commit-hash>
```

---

## 📈 Success Metrics

After enabling new format, verify:

- [ ] ✅ No JavaScript console errors
- [ ] ✅ All pages load in < 3 seconds
- [ ] ✅ All filters work correctly
- [ ] ✅ Bike details modal works
- [ ] ✅ Comparison works
- [ ] ✅ AI comparison works
- [ ] ✅ Shared links work
- [ ] ✅ No 500 errors in server logs
- [ ] ✅ Database queries are efficient
- [ ] ✅ Hebrew text displays correctly (RTL)
- [ ] ✅ Brand colors maintained

---

## 🔗 Quick Reference

**Start app with old format (safe)**:
```powershell
$env:USE_NEW_BIKE_FORMAT="false"
python app.py
```

**Start app with new format (testing)**:
```powershell
$env:USE_NEW_BIKE_FORMAT="true"
python app.py
```

**Check what's running**:
```python
python -c "from app.config import Config; print(f'Flag: {Config.USE_NEW_BIKE_FORMAT}')"
```

**Run feature flag test**:
```powershell
python tests/test_feature_flag.py
```

**Clear cache**:
```python
python -c "from app import create_app; app = create_app(); app.extensions['cache'].clear(); print('Cache cleared')"
```

