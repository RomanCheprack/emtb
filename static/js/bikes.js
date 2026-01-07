// Function to format numbers with commas
function formatNumberWithCommas(value) {
    if (value === null || value === undefined || value === '') {
        return '';
    }
    
    // Convert to string first to check if it's a text value
    const valueStr = String(value).trim();
    
    // If it's the Hebrew text "צור קשר", return it as-is
    if (valueStr === "צור קשר") {
        return valueStr;
    }
    
    try {
        // Convert to integer and format with commas
        return parseInt(parseFloat(value)).toLocaleString();
    } catch (error) {
        // If conversion fails, return the original value
        return valueStr;
    }
}

/**
 * Adapter to normalize bike data format.
 * During migration, can handle both old flat format and new nested format.
 * This allows the frontend to work with both formats during the transition.
 */
function adaptBikeData(bike) {
    // Check if already in new format (has 'brand' instead of 'firm')
    if (bike.brand !== undefined && bike.listing !== undefined) {
        // New format - already normalized, but ensure required properties exist
        return {
            ...bike,
            listing: bike.listing || { product_url: null, price: null, original_price: null },
            specs: bike.specs || {},
            images: bike.images || []
        };
    }
    
    // Old format - convert to new format structure for internal use
    const specs = {};
    
    // Core fields that are NOT specs (these belong at the root level)
    const coreFields = new Set([
        'id', 'firm', 'model', 'year', 'image_url', 'sub_category', 'category',
        'style', 'product_url', 'price', 'disc_price', 'gallery_images_urls',
        'fork_length' // fork_length is at root level in bikes table
    ]);
    
    // Automatically capture ALL other fields as specs
    for (const [key, value] of Object.entries(bike)) {
        if (!coreFields.has(key) && value !== null && value !== undefined && value !== '') {
            specs[key] = value;
        }
    }
    
    return {
        id: bike.id,
        brand: bike.firm,
        model: bike.model,
        year: bike.year,
        image_url: bike.image_url,
        sub_category: bike.sub_category,
        listing: {
            product_url: bike.product_url,
            price: bike.disc_price || bike.price,
            original_price: bike.price
        },
        specs: specs,
        images: bike.gallery_images_urls ? JSON.parse(bike.gallery_images_urls) : []
    };
}

document.addEventListener("DOMContentLoaded", () => {
    // ========== LOAD ALL BIKES DATA FOR CLIENT-SIDE FILTERING ==========
    let allBikes = []; // All bikes for current category
    let filteredBikes = []; // Currently displayed bikes after filtering
    
    // Load bikes from inline JSON
    const bikesDataElement = document.getElementById('bikes-data');
    if (bikesDataElement) {
        try {
            allBikes = JSON.parse(bikesDataElement.textContent);
            filteredBikes = [...allBikes]; // Start with all bikes
            console.log(`Loaded ${allBikes.length} bikes for client-side filtering`);
            
            // Success!
            if (allBikes.length > 0) {
                console.log(`✅ Client-side filtering ready with ${allBikes.length} bikes`);
            }
        } catch (e) {
            console.error('Failed to parse bikes data:', e);
            allBikes = [];
            filteredBikes = [];
        }
    }
    
    // ========== DOM ELEMENTS ==========
    const priceSlider = document.getElementById("price-slider");
    const batterySlider = document.getElementById("battery-slider");
    const searchInput = document.getElementById("search-input");

    const minPriceInput = document.getElementById("min_price");
    const maxPriceInput = document.getElementById("max_price");
    const minPriceValue = document.getElementById("min_price_value");
    const maxPriceValue = document.getElementById("max_price_value");

    const minBatteryInput = document.getElementById("min_battery");
    const maxBatteryInput = document.getElementById("max_battery");
    const minBatteryValue = document.getElementById("min_battery_value");
    const maxBatteryValue = document.getElementById("max_battery_value");

    const minForkInput = document.getElementById("min_fork");
    const maxForkInput = document.getElementById("max_fork");
    const minForkValue = document.getElementById("min_fork_value");
    const maxForkValue = document.getElementById("max_fork_value");

    const sortDropdown = document.getElementById("sort-price");

    // Cache DOM elements for better performance
    const bikesList = document.getElementById("bikes-list");
    const bikesCount = document.getElementById("bikes-count");
    const firmDropdown = document.getElementById('firmDropdown');
    const motorBrandDropdown = document.getElementById('motorBrandDropdown');

    // Debounce function for search input (less aggressive since filtering is instant)
    let searchTimeout;
    function debounce(func, wait) {
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(searchTimeout);
                func(...args);
            };
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(later, wait);
        };
    }

    // Get category first to determine price range and other settings
    const categoryInput = document.getElementById('selected-category');
    const selectedCategory = categoryInput ? categoryInput.value : null;
    
    // Set price range based on category
    let maxPrice = 80000; // Default max price
    let defaultMaxPrice = 100000; // Default slider end position
    
    switch(selectedCategory) {
        case 'kids':
            maxPrice = 10000;
            defaultMaxPrice = 10000;
            break;
        case 'city':
            maxPrice = 20000;
            defaultMaxPrice = 20000;
            break;
        case 'electric':
            maxPrice = 80000;
            defaultMaxPrice = 80000;
            break;
        case 'road':
            maxPrice = 60000;
            defaultMaxPrice = 60000;
            break;
        case 'mtb':
            maxPrice = 70000;
            defaultMaxPrice = 70000;
            break;
        default:
            maxPrice = 80000;
            defaultMaxPrice = 80000;
    }
    
    noUiSlider.create(priceSlider, {
        start: [0, defaultMaxPrice],
        connect: true,
        step: 1000,
        range: { min: 0, max: maxPrice },
        format: {
            to: (val) => Math.round(val),
            from: (val) => Number(val),
        },
    });

    priceSlider.noUiSlider.on("update", (values) => {
        minPriceInput.value = values[0];
        maxPriceInput.value = values[1];
        // Swap display values for RTL: left handle (visually) updates left display, right handle (visually) updates right display
        minPriceValue.textContent = values[1];
        maxPriceValue.textContent = values[0];
    });
    
    // Only create battery slider if category is electric
    if (selectedCategory === 'electric') {
        noUiSlider.create(batterySlider, {
            start: [200, 1000],
            connect: true,
            step: 10,
            range: { min: 200, max: 1000 },
            format: {
                to: (val) => Math.round(val),
                from: (val) => Number(val),
            },
        });

        batterySlider.noUiSlider.on("update", (values) => {
            minBatteryInput.value = values[0];
            maxBatteryInput.value = values[1];
            minBatteryValue.textContent = values[0];
            maxBatteryValue.textContent = values[1];
        });
    } else {
        // Hide battery slider container if not electric category
        const batterySliderContainer = batterySlider.closest('.slider-padding-wh');
        if (batterySliderContainer) {
            batterySliderContainer.style.display = 'none';
        }
    }

    // Firms and sub-categories are now filtered server-side
    // No need for client-side filtering anymore

    // Hide motor dropdown if category is not electric
    if (selectedCategory !== 'electric') {
        const motorDropdownContainer = document.getElementById('motorBrandDropdown')?.closest('.mb-3');
        if (motorDropdownContainer) {
            motorDropdownContainer.style.display = 'none';
        }
    }

    // Initialize and manage fork length slider
    const forkSlider = document.getElementById("fork-slider");
    const forkSliderContainer = document.getElementById("fork-slider-container");
    
    // Hide fork slider for road, city, kids, and gravel categories
    // Only show for MTB and electric categories
    if (selectedCategory === 'road' || selectedCategory === 'city' || selectedCategory === 'kids' || selectedCategory === 'gravel') {
        if (forkSliderContainer) {
            forkSliderContainer.style.display = 'none';
        }
    } else {
        // Create fork slider for non-road categories
        if (forkSlider) {
            noUiSlider.create(forkSlider, {
                start: [80, 170],
                connect: true,
                step: 5,
                range: { min: 80, max: 170 },
                format: {
                    to: (val) => Math.round(val),
                    from: (val) => Number(val),
                },
            });

            forkSlider.noUiSlider.on("update", (values) => {
                minForkInput.value = values[0];
                maxForkInput.value = values[1];
                // Swap display values for RTL: left handle (visually) updates left display, right handle (visually) updates right display
                minForkValue.textContent = values[1];
                maxForkValue.textContent = values[0];
            });
        }
    }

    function updateFirmDropdownText() {
        const selectedFirms = Array.from(document.querySelectorAll('.firm-checkbox:checked')).map(cb => cb.value);
        
        if (selectedFirms.length === 0) {
            firmDropdown.textContent = 'בחר מותגים';
        } else if (selectedFirms.length === 1) {
            firmDropdown.textContent = selectedFirms[0];
        } else {
            firmDropdown.textContent = `${selectedFirms.length} מותגים נבחרו`;
        }
    }

    function updateMotorBrandDropdownText() {
        const selectedMotorBrands = Array.from(document.querySelectorAll('.motor-brand-checkbox:checked')).map(cb => cb.value);
        
        if (selectedMotorBrands.length === 0) {
            motorBrandDropdown.textContent = 'בחר מותגי מנוע';
        } else if (selectedMotorBrands.length === 1) {
            motorBrandDropdown.textContent = selectedMotorBrands[0].charAt(0).toUpperCase() + selectedMotorBrands[0].slice(1);
        } else {
            motorBrandDropdown.textContent = `${selectedMotorBrands.length} מותגי מנוע נבחרו`;
        }
    }

    // Optimized HTML generation using DocumentFragment
    function generateBikesHTML(bikes) {
        const fragment = document.createDocumentFragment();
        
        if (bikes.length === 0) {
            const noResultsDiv = document.createElement('div');
            noResultsDiv.className = 'bike-row-item';
            noResultsDiv.innerHTML = '<p style="text-align: center; padding: 20px;">לא נמצאו תוצאות.</p>';
            fragment.appendChild(noResultsDiv);
        } else {
            bikes.forEach((bike) => {
                // Adapt bike data to work with both old and new formats
                const adaptedBike = adaptBikeData(bike);
                
                // Check if there's a discount
                const hasDiscount = adaptedBike.listing.price && adaptedBike.listing.original_price && 
                                   adaptedBike.listing.price !== adaptedBike.listing.original_price && 
                                   adaptedBike.listing.price !== "#N/A";
                
                // Generate price HTML
                let priceHTML = '';
                if (hasDiscount) {
                    const originalPrice = formatNumberWithCommas(adaptedBike.listing.original_price);
                    const discountPrice = formatNumberWithCommas(adaptedBike.listing.price);
                    priceHTML = `
                        <div class="bike-price-wrapper">
                            ${originalPrice === 'צור קשר' 
                                ? `<span class="bike-price-original">${originalPrice}</span>`
                                : `<span class="bike-price-original">₪ ${originalPrice}</span>`
                            }
                            <br>
                            ${discountPrice === 'צור קשר'
                                ? `<span class="bike-price-discount">${discountPrice}</span>`
                                : `<span class="bike-price-discount">₪ ${discountPrice}</span>`
                            }
                        </div>
                    `;
                } else {
                    const currentPrice = formatNumberWithCommas(adaptedBike.listing.price);
                    priceHTML = `
                        <div class="bike-price-wrapper">
                            ${currentPrice === 'צור קשר'
                                ? `<span class="bike-price-current">${currentPrice}</span>`
                                : `<span class="bike-price-current">₪ ${currentPrice}</span>`
                            }
                        </div>
                    `;
                }
                
                const bikeDiv = document.createElement('div');
                bikeDiv.className = 'bike-row-item position-relative bike-card';
                bikeDiv.setAttribute('data-bike-id', adaptedBike.id);
                bikeDiv.innerHTML = `
                    <button class="bike-menu-dots" aria-label="תפריט אפשרויות">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <circle cx="12" cy="5" r="2"/>
                            <circle cx="12" cy="12" r="2"/>
                            <circle cx="12" cy="19" r="2"/>
                        </svg>
                    </button>
                    <div class="bike-header-info">
                        ${adaptedBike.year ? `<span class="bike-year-header">${adaptedBike.year}</span> | ` : ''}<span class="bike-model">${adaptedBike.model}</span> | <a href="#" class="bike-brand-link" data-brand="${(adaptedBike.brand || '').replace(/"/g, '&quot;')}">${adaptedBike.brand}</a>
                    </div>
                    <div class="bike-row-content">
                        <div class="bike-image-container">
                            <img src="${adaptedBike.image_url}" class="bike-row-image" alt="${adaptedBike.model}" loading="lazy" referrerpolicy="no-referrer">
                            <a href="#" class="bike-compare-link" data-bike-id="${adaptedBike.id}">
                               הוסף להשוואה
                            </a>
                        </div>
                        <div class="bike-price-container">
                            ${priceHTML}
                            <button class="btn btn-outline-primary purchase-btn" data-bike-id="${adaptedBike.id}" data-product-url="${adaptedBike.listing.product_url || ''}">
                                <i class="fas fa-shopping-cart me-1"></i>
                                רכישה
                            </button>
                        </div>
                        <div class="bike-actions-container">
                            <div class="bike-actions-top" style="flex-direction: column;">
                                <button type="button" class="btn btn-outline-secondary details-btn" data-bike-id="${adaptedBike.id}">
                                    <i class="fas fa-info-circle me-1"></i>
                                    מפרט
                                </button>
                                <button type="button"
                                        class="btn btn-outline-primary availability-btn"
                                        data-bike-id="${adaptedBike.id}"
                                        data-bike-model="${adaptedBike.brand} ${adaptedBike.model}${adaptedBike.year ? ' ' + adaptedBike.year : ''}"
                                        data-bs-toggle="modal"
                                        data-bs-target="#availabilityModal"
                                        style="margin-top: 4px;">
                                    בדוק זמינות
                                </button>
                                <button type="button"
                                        class="btn btn-outline-primary find-store-btn"
                                        data-bike-id="${adaptedBike.id}"
                                        data-bike-model="${adaptedBike.brand} ${adaptedBike.model}${adaptedBike.year ? ' ' + adaptedBike.year : ''}"
                                        data-bs-toggle="modal"
                                        data-bs-target="#findStoreModal"
                                        style="margin-top: 4px;">
                                    מצא חנות
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                fragment.appendChild(bikeDiv);
            });
        }
        
        return fragment;
    }

    // ========== HELPER FUNCTIONS ==========
    // Helper function to determine frame material (matches server-side logic)
    function getBikeFrameMaterial(bike) {
        // Check frame_material field first
        const frameMaterialField = (bike.frame_material || '').trim();
        if (frameMaterialField) {
            const frameMaterialLower = frameMaterialField.toLowerCase();
            if (frameMaterialLower.includes('carbon')) {
                return 'carbon';
            } else if (frameMaterialLower.includes('aluminium') || frameMaterialLower.includes('aluminum')) {
                return 'aluminium';
            }
        }
        
        // Check frame description and model
        const frameVal = (bike.frame || '').trim();
        const modelVal = (bike.model || '').trim();
        
        // If both are empty, frame material is unknown
        if (!frameVal && !modelVal) {
            return null;
        }
        
        // Search for material indicators
        const combined = `${frameVal} ${modelVal}`.toLowerCase();
        
        if (combined.includes('carbon')) {
            return 'carbon';
        } else if (combined.includes('aluminium') || combined.includes('aluminum')) {
            return 'aluminium';
        }
        
        // If we have frame/model info but no material indicator, return null (unknown)
        return null;
    }

    // ========== CLIENT-SIDE FILTERING (INSTANT!) ==========
    function applyFilters() {
        const startTime = performance.now();
        
        // Get all filter values
        const query = searchInput.value.trim().toLowerCase();
        const min_price = parseInt(minPriceInput.value) || 0;
        const max_price = parseInt(maxPriceInput.value) || defaultMaxPrice;
        const min_battery = parseInt(minBatteryInput.value) || 0;
        const max_battery = parseInt(maxBatteryInput.value) || 1000;
        const min_fork = minForkInput ? parseInt(minForkInput.value) || 0 : 0;
        const max_fork = maxForkInput ? parseInt(maxForkInput.value) || 1000 : 1000;

        const selectedFirms = Array.from(document.querySelectorAll('.firm-checkbox:checked')).map(cb => cb.value);
        const selectedMotorBrands = Array.from(document.querySelectorAll('.motor-brand-checkbox:checked')).map(cb => cb.value);
        const selectedStyles = Array.from(document.querySelectorAll('.style-checkbox:checked')).map(cb => cb.value);
        const selectedYears = Array.from(document.querySelectorAll('input[name="year"]:checked')).map(cb => parseInt(cb.value));
        
        const frameMaterialRadio = document.querySelector('input[name="frame_material"]:checked');
        const frameMaterial = frameMaterialRadio ? frameMaterialRadio.value : undefined;
        const hasDiscount = document.querySelector('input[name="has_discount"]:checked')?.value;
        
        // Filter bikes in memory - FAST!
        // Ensure we're starting with the full allBikes array
        if (allBikes.length === 0) {
            console.warn('allBikes is empty!');
        }
        
        // Debug: Track which filters are excluding bikes
        const filterStats = {
            total: allBikes.length,
            excludedBy: {}
        };
        
        filteredBikes = allBikes.filter((bike) => {
            
            // Search filter (model or firm)
            if (query) {
                const modelMatch = bike.model?.toLowerCase().includes(query);
                const firmMatch = bike.firm?.toLowerCase().includes(query);
                if (!modelMatch && !firmMatch) {
                    filterStats.excludedBy.search = (filterStats.excludedBy.search || 0) + 1;
                    return false;
                }
            }
            
            // Price filter
            // Only filter if user has actually changed the price range from default
            // If max_price equals defaultMaxPrice, don't filter by max (show all bikes regardless of price)
            const price = bike.disc_price || bike.price;
            if (price && price !== "צור קשר") {
                // Parse price correctly - handle decimals (27990.00 should be 27990, not 2799000)
                const priceNum = Math.round(parseFloat(String(price))) || 0;
                // Filter by min_price if user has increased it from 0
                if (priceNum < min_price) {
                    filterStats.excludedBy.price = (filterStats.excludedBy.price || 0) + 1;
                    return false;
                }
                // Only filter by max_price if user has reduced it from default (max_price < defaultMaxPrice)
                if (max_price < defaultMaxPrice && priceNum > max_price) {
                    filterStats.excludedBy.price = (filterStats.excludedBy.price || 0) + 1;
                    return false;
                }
            }
            
            // Year filter
            if (selectedYears.length > 0) {
                // Include bikes with null/undefined/empty year OR bikes matching selected years
                if (bike.year != null && bike.year !== undefined && bike.year !== '') {
                    // Convert bike.year to number for comparison
                    const bikeYear = parseInt(bike.year);
                    if (!selectedYears.includes(bikeYear)) {
                        return false;
                    }
                }
                // If bike.year is null/undefined/empty, include it (don't return false)
            }
            
            // Firm/Brand filter
            if (selectedFirms.length > 0) {
                if (!bike.firm || !selectedFirms.includes(bike.firm)) {
                    return false;
                }
            }
            
            // Style filter
            if (selectedStyles.length > 0 && bike.style && !selectedStyles.includes(bike.style)) {
                return false;
            }
            
            // Battery filter (for electric bikes only)
            // Only apply if category is electric AND bike has battery data
            // Bikes without battery data should be included
            if (selectedCategory === 'electric' && bike.wh) {
                const wh = parseInt(bike.wh) || 0;
                if (wh < min_battery || wh > max_battery) {
                    filterStats.excludedBy.battery = (filterStats.excludedBy.battery || 0) + 1;
                    return false;
                }
            }
            
            // Fork length filter (only for MTB and electric categories)
            // Don't apply for road, city, kids, or gravel categories
            // Only apply if category is MTB or electric AND bike has fork_length data
            // Bikes without fork_length data should be included
            const shouldApplyForkFilter = (selectedCategory === 'mtb' || selectedCategory === 'electric') && bike.fork_length;
            if (shouldApplyForkFilter) {
                const forkMatch = String(bike.fork_length).match(/\d+/);
                const forkNum = forkMatch ? parseInt(forkMatch[0]) : 0;
                if (forkNum && (forkNum < min_fork || forkNum > max_fork)) {
                    filterStats.excludedBy.fork = (filterStats.excludedBy.fork || 0) + 1;
                    return false;
                }
            }
            
            // Frame material filter
            // Empty string or undefined means "All" - show all bikes
            // Only apply filter if a specific material is selected
            const shouldApplyFrameFilter = frameMaterial !== undefined && 
                                         frameMaterial !== null && 
                                         frameMaterial !== '' && 
                                         String(frameMaterial).trim() !== '';
            
            if (shouldApplyFrameFilter) {
                const bikeFrameMaterial = getBikeFrameMaterial(bike);
                
                // Include bikes with null/unknown frame material OR bikes matching selected material
                if (bikeFrameMaterial !== null && bikeFrameMaterial !== frameMaterial) {
                    return false;
                }
                // If bikeFrameMaterial is null (unknown), include it (don't return false)
            }
            // If frameMaterial is empty/undefined/null, skip filter (show all bikes)
            
            // Motor brand filter
            if (selectedMotorBrands.length > 0) {
                const bikeMotor = bike.motor_brand || bike.motor || '';
                const motorMatch = selectedMotorBrands.some(brand => 
                    bikeMotor.toLowerCase().includes(brand.toLowerCase())
                );
                if (!motorMatch) return false;
            }
            
            // Discount filter
            if (hasDiscount === "true" && !bike.disc_price) {
                return false;
            }
            
            return true;
        });
        
        // Sort if needed
        const sortOrder = sortDropdown.value;
        if (sortOrder === "asc" || sortOrder === "desc") {
            filteredBikes.sort((a, b) => {
                const aPrice = a.disc_price || a.price;
                const bPrice = b.disc_price || b.price;
                
                // Parse price correctly - handle decimals
                const aNum = aPrice && aPrice !== "צור קשר" ? Math.round(parseFloat(String(aPrice))) : 0;
                const bNum = bPrice && bPrice !== "צור קשר" ? Math.round(parseFloat(String(bPrice))) : 0;
                
                return sortOrder === "asc" ? aNum - bNum : bNum - aNum;
            });
        }
        
        // Render filtered bikes
        bikesList.innerHTML = "";
        const bikesFragment = generateBikesHTML(filteredBikes);
        bikesList.appendChild(bikesFragment);
        bikesCount.textContent = `נמצאו ${filteredBikes.length} אופניים`;
        
        // Debug: Log filter statistics when bikes are missing
        if (filteredBikes.length !== allBikes.length) {
            console.warn(`⚠️ Filtering issue: allBikes=${allBikes.length}, filteredBikes=${filteredBikes.length}`);
            console.warn('Excluded by:', filterStats.excludedBy);
            console.warn('Filter values:', {
                query,
                min_price, max_price,
                min_battery, max_battery,
                min_fork, max_fork,
                selectedYears,
                selectedFirms,
                selectedStyles,
                selectedMotorBrands,
                frameMaterial,
                hasDiscount
            });
        }

        // Re-attach event listeners
        attachCompareButtonListeners();
        attachPurchaseButtonListeners();
        
        // Restore compare UI state
        fetch("/api/compare_list")
            .then((res) => res.json())
            .then((data) => updateCompareUI(data.compare_list || []))
            .catch(err => console.error('Error fetching compare list:', err));
        
        const endTime = performance.now();
        console.log(`⚡ Filtering completed in ${(endTime - startTime).toFixed(2)}ms - showing ${filteredBikes.length} bikes`);
    }

    function attachCompareButtonListeners() {
        document.querySelectorAll(".bike-compare-link").forEach((link) => {
            link.onclick = (e) => {
                e.preventDefault();
                const bikeId = link.getAttribute("data-bike-id");
                const isSelected = link.classList.contains("selected");
                
                const url = isSelected
                    ? `/remove_from_compare`
                    : `/add_to_compare`;

                // Get CSRF token from meta tag (optional since routes are exempt)
                const csrfMeta = document.querySelector('meta[name="csrf-token"]');
                const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : null;
                
                const headers = {
                    'Content-Type': 'application/json'
                };
                // Only add CSRF token if available (routes are exempt anyway)
                if (csrfToken) {
                    headers['X-CSRFToken'] = csrfToken;
                }
                
                fetch(url, { 
                    method: "POST",
                    headers: headers,
                    body: JSON.stringify({ bike_id: bikeId })
                })
                    .then((res) => {
                        // Check if response is JSON
                        const contentType = res.headers.get('content-type');
                        if (!contentType || !contentType.includes('application/json')) {
                            // If not JSON, get the text to see what we're getting
                            return res.text().then(text => {
                                console.error("Server returned non-JSON response:", text.substring(0, 500));
                                throw new Error(`Server returned ${res.status}: ${text.substring(0, 100)}`);
                            });
                        }
                        
                        return res.json();
                    })
                    .then((data) => {
                        if (data.success) {
                            updateCompareUI(data.compare_list || []);
                        } else {
                            console.error("Compare operation failed:", data.error);
                            alert("שגיאה: " + (data.error || "לא ניתן להוסיף אופניים להשוואה"));
                        }
                    })
                    .catch((err) => {
                        console.error("Error in compare operation:", err);
                        alert("שגיאה בחיבור לשרת: " + err.message);
                    });
            };
        });
    }

    function attachPurchaseButtonListeners() {
        document.querySelectorAll(".purchase-btn").forEach((btn) => {
            btn.onclick = () => {
                const productUrl = btn.getAttribute("data-product-url");
                
                if (productUrl && productUrl.trim() !== '') {
                    // Open the product URL in a new tab
                    window.open(productUrl, '_blank');
                } else {
                    // Show a message if no product URL is available
                    alert('לא ניתן לרכוש כרגע - אין קישור למוצר זמין');
                }
            };
        });
    }

    function updateCompareUI(compareList) {
        document.querySelectorAll(".bike-compare-link").forEach((link) => {
            const bikeId = String(link.getAttribute("data-bike-id")); // Ensure string
            const card = link.closest(".bike-card") || link.closest(".card");
            
            // Convert all items in compareList to strings for comparison
            const compareListStrings = compareList.map(id => String(id));
            
            if (compareListStrings.includes(bikeId)) {
                link.classList.add("selected");
                if (card) card.classList.add("compare-selected");
            } else {
                link.classList.remove("selected");
                if (card) card.classList.remove("compare-selected");
            }
        });

        const compareBtn = document.getElementById("go-to-compare");
        const compareCount = document.getElementById("compare-count");
        if (compareList.length > 0) {
            compareBtn.style.display = "inline-block";
            compareCount.textContent = `${compareList.length}`;
            
            // Store current page URL in session before navigating to comparison
            if (compareBtn && !compareBtn.hasAttribute('data-listener-attached')) {
                compareBtn.addEventListener('click', function(e) {
                    // Store the current page URL (with query params) for return navigation
                    const currentUrl = window.location.pathname + window.location.search;
                    
                    // Send to server to store in session
                    fetch('/api/store_compare_referrer', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ referrer: currentUrl })
                    }).catch(err => {
                        console.log('Could not store referrer:', err);
                        // Continue navigation even if storing fails
                    });
                });
                compareBtn.setAttribute('data-listener-attached', 'true');
            }
        } else {
            compareBtn.style.display = "none";
        }
    }

    function fetchBikeDetailsAndShowModal(bikeId) {
    // Show loading state
    const modalElement = document.getElementById('bikeDetailsModal');
    const modalBody = document.getElementById('bike-details-content');
    
    // Clear any existing modal instance and backdrop
    const existingModal = bootstrap.Modal.getInstance(modalElement);
    if (existingModal) {
        existingModal.dispose();
    }
    
    // Remove any existing backdrop
    const existingBackdrop = document.querySelector('.modal-backdrop');
    if (existingBackdrop) {
        existingBackdrop.remove();
    }
    
    // Remove modal-open class from body
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">טוען...</span></div><p class="mt-2">טוען פרטי האופניים...</p></div>';
    
    // Create new modal instance and show
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    // Fetch bike details from API
    fetch(`/api/bike/${encodeURIComponent(bikeId)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(bike => {
            showBikeDetailsModal(bike);
        })
        .catch(error => {
            console.error('Error fetching bike details:', error);
            modalBody.innerHTML = '<div class="alert alert-danger">שגיאה בטעינת פרטי האופניים. אנא נסה שוב.</div>';
        });
}

/**
 * Format field names for display when no Hebrew translation exists
 * Converts snake_case or camelCase to readable format
 */
function formatFieldName(fieldName) {
    if (!fieldName) return '';
    
    // Convert to string and handle common patterns
    let formatted = String(fieldName)
        .replace(/_/g, ' ')  // Replace underscores with spaces
        .replace(/([a-z])([A-Z])/g, '$1 $2')  // Add space between camelCase
        .trim();
    
    // Capitalize first letter of each word
    formatted = formatted.split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
    
    return formatted;
}

function showBikeDetailsModal(bike) {
        // Validate bike object
        if (!bike || typeof bike !== 'object') {
            console.error('Invalid bike object:', bike);
            alert('שגיאה: נתוני האופניים לא תקינים');
            return;
        }
        
        // Adapt bike data to work with both old and new formats
        const adaptedBike = adaptBikeData(bike);
        
        // Field translations and organization (includes common raw spec keys)
        const fieldTranslations = {
            'brand': 'מותג',
            'model': 'דגם',
            'year': 'שנה',
            'bike_type': 'סוג אופניים',
            'bike_series': 'סדרה',
            'price': 'מחיר',
            'disc_price': 'מחיר מבצע',
            'motor': 'מנוע',
            'battery': 'סוללה',
            'wh': '(WH) סוללה',
            'fork': 'בולם קדמי',
            'rear_shock': 'בולם אחורי',
            'shock': 'בולם',
            'frame': 'שלדה',
            'tires': 'צמיגים',
            'brakes': 'בלמים',
            'weight': 'משקל',
            'wheel_size': 'גודל גלגלים',
            'sub_category': 'סוג אופניים',
            'size': 'מידה',
            'sizes': 'מידות',
            'sku': 'מק"ט',
            'gear_count': 'מספר הילוכים',
            'number_of_gears': 'מספר הילוכים',
            'front_brake': 'ברקס קידמי',
            'rear_brake': 'ברקס אחורי',
            'front_tire': 'צמיג קדמי',
            'rear_tire': 'צמיג אחורי',
            'saddle': 'אוכף',
            'pedals': 'דוושות',
            'charger': 'מטען',
            'screen': 'מסך',
            'extras': 'תוספות',
            'additionals': 'תוספות',
            'rear_der': 'מעביר אחורי',
            'shifter': 'שיפטר',
            'shifters': 'שיפטרים',
            'crank_set': 'קראנק',
            'crankset': 'קראנק',
            'crank': 'קראנק',
            'chain': 'שרשרת',
            'chainring': 'גלגל שיניים',
            'chainset': 'קראנק',
            'chainstay': 'זרוע אחורית',
            'cassette': 'קסטה',
            'rotors': 'רוטורים',
            'rotor': 'רוטור',
            'handlebar': 'כידון',
            'handelbar': 'כידון',
            'bar': 'כידון',
            'seat_post': 'מוט אוכף',
            'seatpost': 'מוט אוכף',
            'seatpost_clamp': 'מהדק מוט אוכף',
            'stem': 'סטם',
            'lights': 'תאורה',
            'lighting': 'תאורה',
            'wheels': 'גלגלים',
            'wheelset': 'סט גלגלים',
            'wheelbase': 'בסיס גלגלים',
            'rims': 'חישוקים',
            'spokes': 'חישורים',
            'front_hub': 'ציר קדמי',
            'rear_hub': 'ציר אחורי',
            'hub': 'רכזת',
            'hubs': 'רכזות',
            'headset': 'הד סט',
            'head tube': 'צינור היגוי',
            'remote': 'שלט',
            'fork_length': 'אורך בולמים',
            'chain_guide': 'מדריך שרשרת',
            'chainguide': 'מדריך שרשרת',
            'tubes': 'פנימיות',
            'front_wheel': 'גלגל קדמי',
            'rear_wheel': 'גלגל אחורי',
            'rear_derailleur': 'מעביר אחורי',
            'rear derailleur': 'מעביר אחורי',
            'front_derailleur': 'מעביר קדמי',
            'front derailleur': 'מעביר קדמי',
            'derailleur': 'מעביר',
            'mech': 'מעביר',
            'bb': 'בראקט תחתון',
            'bottom_bracket': 'בראקט תחתון',
            'battery_capacity': 'קיבולת סוללה',
            'front_wheel_size': 'גודל גלגל קדמי',
            'rear_wheel_size': 'גודל גלגל אחורי',
            'battery_watts_per_hour': 'סוללה (WH)',
            'rear_wheel_maxtravel': 'מהלך מקסימלי אחורי',
            'brake_lever': 'ידית בלם',
            'brake_levers': 'ידיות בלם',
            'brake levers': 'ידיות בלם',
            'clamp': 'מהדק',
            'seat_clamp': 'מהדק אוכף',
            'front_axle': 'ציר קדמי',
            'rear_axle': 'ציר אחורי',
            'axle': 'ציר',
            'category': 'קטגוריה',
            'style': 'סגנון',
            'suspension': 'מתלה',
            'groupset': 'קבוצת העברה',
            'drivetrain': 'מערכת הינע',
            'display': 'תצוגה',
            'controller': 'בקר',
            'control_system': 'מערכת בקרה',
            'accessories': 'אביזרים',
            'grips': 'גריפים',
            'grip': 'גריפ',
            'seat': 'אוכף',
            'tire': 'צמיג',
            'tyres': 'צמיגים',
            'valve': 'ונטיל',
            'speed': 'מהירות',
            'speeds': 'הילוכים',
            'gears': 'הילוכים',
            'color': 'צבע',
            'colours': 'צבעים',
            'colors': 'צבעים',
            'material': 'חומר',
            'travel': 'מהלך',
            'trail': 'טרייל',
            'seat angle': 'זווית אוכף',
            'bottom bracket drop': 'ירידת בראקט',
            'front guide': 'מדריך קדמי',
            'diameter': 'קוטר',
            'width': 'רוחב',
            'length': 'אורך',
            'height': 'גובה',
            'angle': 'זווית',
            'reach': 'ריץ\'',
            'stack': 'סטאק',
            'range': 'טווח',
            'torque': 'מומנט',
            'power': 'עוצמה',
            'voltage': 'מתח',
            'amperage': 'עוצמת זרם',
            'charge_time': 'זמן טעינה',
            'charging_time': 'זמן טעינה',
            'rim_tape': 'סרט חישוק',
            'handlebar_tape': 'סרט כידון',
            'additionals': 'תוספות'
        };
        
        // Define the order of fields to display
        const fieldOrder = [
            'brand',
            'model',
            'sub_category', 
            'year',
            'price',
            'disc_price',
            'motor',
            'battery',
            'wh',
            'frame',
            'fork',
            'fork_length',
            'rear_shock',
            'remote',
            'weight',
            'rear_derailleur',
            'shifter',
            'crank_set',
            'chain_guide',
            'chain',
            'cassette',
            'brakes',
            'rotors',
            'handlebar',
            'seat_post',
            'saddle',
            'stem',
            'front_tire',
            'rear_tire',
            'front_hub',
            'rear_hub',
            'rims',
            'spokes',
            'headset',
            'lights',
            'wheels',
            'front_wheel',
            'rear_wheel',
            'tubes',
            'charger',
            'screen',
            'extras'
        ];
        
        // Get gallery images from adapted bike (already an array)
        // Handle both array format and ensure it's always an array
        let galleryImages = [];
        if (Array.isArray(adaptedBike.images)) {
            galleryImages = adaptedBike.images;
        } else if (adaptedBike.images && typeof adaptedBike.images === 'string') {
            try {
                galleryImages = JSON.parse(adaptedBike.images);
            } catch (e) {
                console.warn('Failed to parse gallery images:', e);
                galleryImages = [];
            }
        }
        
        // Gallery images ready
        
        let html = `
            <div class="row">
                <div class="col-md-4">
                    <div class="main-image-container">
                        <img src="${adaptedBike.image_url || ''}" class="img-fluid main-bike-image" alt="${(adaptedBike.model || 'Bike').replace(/"/g, '&quot;')}" id="main-bike-image" onclick="openImageZoom(${JSON.stringify(adaptedBike.image_url || '')}, ${JSON.stringify(adaptedBike.model || 'Bike')})" loading="lazy" referrerpolicy="no-referrer">
                        <div class="zoom-overlay">
                            <i class="fas fa-search-plus"></i>
                        </div>
                    </div>
                    ${galleryImages.length > 1 ? `
                    <div class="gallery-carousel mt-3">
                        <div class="gallery-scroll">
                            ${galleryImages.map((imgUrl, index) => `
                                <div class="gallery-thumbnail ${index === 0 ? 'active' : ''}" onclick="changeMainImage(${JSON.stringify(imgUrl)}, this)">
                                    <img src="${imgUrl}" alt="${(adaptedBike.model || 'Bike').replace(/"/g, '&quot;')} - תמונה ${index + 1}" class="img-fluid" loading="lazy">
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                </div>
                <div class="col-md-8">
                    <table class="table table-striped" dir="rtl">
                        <tbody>
        `;

                // Display fields in the specified order
        const displayedFields = new Set(); // Track which fields we've already displayed
        
        fieldOrder.forEach((key) => {
            // Get value from appropriate location in adapted bike
            let value;
            if (key === 'brand' || key === 'model' || key === 'year' || key === 'sub_category') {
                // Basic fields at root level
                value = adaptedBike[key];
            } else if (key === 'price') {
                // Price from listing
                value = adaptedBike.listing?.original_price;
            } else if (key === 'disc_price') {
                // Discounted price from listing
                value = adaptedBike.listing?.price;
            } else {
                // Everything else is in specs
                value = adaptedBike.specs?.[key];
            }
            
            // Check if there's a discount
            const hasDiscount = adaptedBike.listing && 
                               adaptedBike.listing.price !== adaptedBike.listing.original_price && 
                               adaptedBike.listing.price !== null && 
                               adaptedBike.listing.price !== undefined &&
                               adaptedBike.listing.price !== '';
            
            // Skip disc_price row if there's no discount
            if (key === 'disc_price' && !hasDiscount) {
                return;
            }
            
            // Skip if value is undefined or null
            if (value === undefined || value === null) {
                return;
            }
            
            displayedFields.add(key); // Mark this field as displayed
            
            // Format price fields with commas and shekel symbol
            if (key === 'price' || key === 'disc_price') {
                const formattedValue = formatNumberWithCommas(value);
                if (formattedValue === 'צור קשר') {
                    value = formattedValue;
                } else {
                    value = `₪ ${formattedValue}`;
                }
            }
            
            // Translate the field name, or format it nicely if no translation exists
            const translatedKey = fieldTranslations[key] || formatFieldName(key);
            
            // Check if value is long and needs collapsible functionality
            const isLongValue = value && value.length > 100;
            
            // Apply styling based on field type and discount status
            let cellStyle = 'text-align: left;';
            if (key === 'price' && hasDiscount) {
                // Original price with strikethrough when there's a discount - right aligned
                cellStyle = 'text-align: right; text-decoration: line-through; color: #888;';
            } else if (key === 'disc_price') {
                // Discounted price in red - right aligned
                cellStyle = 'text-align: right; color: #d32f2f; font-weight: bold;';
            }
            
            if (isLongValue) {
                const shortValue = value.substring(0, 100) + '...';
                html += `<tr><th style="width:40%; text-align: right;">${translatedKey}</th><td style="${cellStyle}">
                    <span class="cell-short">${shortValue}</span>
                    <span class="cell-full" style="display: none;">${value}</span>
                    <button class="show-more-btn" onclick="toggleValue(this)">הצג עוד</button>
                </td></tr>`;
            } else {
                html += `<tr><th style="width:40%; text-align: right;">${translatedKey}</th><td style="${cellStyle}">${value}</td></tr>`;
            }
        });
        
        // Display any remaining specs that weren't in fieldOrder
        if (adaptedBike.specs && typeof adaptedBike.specs === 'object') {
            Object.keys(adaptedBike.specs).forEach((key) => {
                // Skip if already displayed
                if (displayedFields.has(key)) {
                    return;
                }
                
                const value = adaptedBike.specs?.[key];
                
                // Skip if value is undefined, null, or empty
                if (value === undefined || value === null || value === '') {
                    return;
                }
                
                // Translate the field name if translation exists, otherwise format it nicely
                const translatedKey = fieldTranslations[key] || formatFieldName(key);
                
                // Check if value is long and needs collapsible functionality
                const isLongValue = value && value.length > 100;
                
                if (isLongValue) {
                    const shortValue = value.substring(0, 100) + '...';
                    html += `<tr><th style="width:40%; text-align: right;">${translatedKey}</th><td style="text-align: left;">
                        <span class="cell-short">${shortValue}</span>
                        <span class="cell-full" style="display: none;">${value}</span>
                        <button class="show-more-btn" onclick="toggleValue(this)">הצג עוד</button>
                    </td></tr>`;
                } else {
                    html += `<tr><th style="width:40%; text-align: right;">${translatedKey}</th><td style="text-align: left;">${value}</td></tr>`;
                }
            });
        }

        html += `
                        </tbody>
                    </table>
                </div>
                <div class="mt-3">
                    ${adaptedBike.listing?.product_url ? `<a href="${adaptedBike.listing.product_url}" class="btn btn-info" target="_blank">לרכישה</a>` : ''}
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" style="margin-right: 10px;">סגור</button>
                </div>
            </div>
        </div>
    `;

        try {
            document.getElementById('bike-details-content').innerHTML = html;
            
            // Check if Bootstrap is available
            if (typeof bootstrap === 'undefined') {
                console.error('Bootstrap is not loaded');
                alert('שגיאה: Bootstrap לא נטען כראוי');
                return;
            }
            
            const modalElement = document.getElementById('bikeDetailsModal');
            if (!modalElement) {
                console.error('Modal element not found');
                alert('שגיאה: אלמנט החלון לא נמצא');
                return;
            }
            
            // Get existing modal instance or create new one
            let modal = bootstrap.Modal.getInstance(modalElement);
            if (!modal) {
                modal = new bootstrap.Modal(modalElement);
            }
            
            // Add event listener to properly clean up when modal is hidden
            modalElement.addEventListener('hidden.bs.modal', function () {
                // Remove backdrop
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) {
                    backdrop.remove();
                }
                
                // Clean up body classes and styles
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
            }, { once: true });
            
            modal.show();
        } catch (error) {
            console.error('Error showing bike details modal:', error);
            alert('שגיאה בפתיחת חלון הפרטים. אנא נסה שוב.');
        }
    }

    document.getElementById("apply-offcanvas-filters").addEventListener("click", () => {
        bootstrap.Offcanvas.getOrCreateInstance(document.getElementById("offcanvasFilters")).hide();
        applyFilters();
    });

    // ========== INSTANT RESET BUTTON ==========
    document.getElementById("reset-filters").addEventListener("click", () => {
        // Reset sliders - use the category-specific max price
        priceSlider.noUiSlider.set([0, defaultMaxPrice]);
        if (batterySlider && batterySlider.noUiSlider) {
            batterySlider.noUiSlider.set([200, 1000]);
        }
        if (forkSlider && forkSlider.noUiSlider) {
            forkSlider.noUiSlider.set([80, 170]);
        }
        
        // Reset inputs
        searchInput.value = "";
        sortDropdown.value = "none";

        // Reset all checkboxes
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        // Reset radio buttons
        document.querySelectorAll('input[type="radio"]:checked').forEach(radio => {
            radio.checked = false;
        });

        // Update dropdown texts
        updateFirmDropdownText();
        updateMotorBrandDropdownText();

        // Clear compare list asynchronously (don't wait for it)
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        fetch("/clear_compare", { 
            method: "POST",
            headers: { 'X-CSRFToken': csrfToken }
        }).then(res => res.json())
          .then(() => updateCompareUI([]))
          .catch(err => console.error('Error clearing compare:', err));
        
        // Show all bikes INSTANTLY (no API call needed!)
        filteredBikes = [...allBikes];
        bikesList.innerHTML = "";
        const bikesFragment = generateBikesHTML(filteredBikes);
        bikesList.appendChild(bikesFragment);
        bikesCount.textContent = `נמצאו ${filteredBikes.length} אופניים`;

        attachCompareButtonListeners();
        attachPurchaseButtonListeners();
        
        console.log('Reset completed instantly!');
    });

    sortDropdown.addEventListener("change", applyFilters);
    
    // Debounced search input
    const debouncedApplyFilters = debounce(() => {
        applyFilters();
    }, 300);
    
    if (searchInput) {
        searchInput.addEventListener("input", debouncedApplyFilters);
    }
    
    document.querySelectorAll('input[name="year"], input[name="firm"]').forEach((cb) => {
        cb.addEventListener("change", applyFilters);
    });

    // Add listeners for firm checkboxes
    document.querySelectorAll('.firm-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateFirmDropdownText();
            applyFilters();
        });
    });

    // Add listeners for motor brand checkboxes
    document.querySelectorAll('.motor-brand-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateMotorBrandDropdownText();
            applyFilters();
        });
    });


    // Add listeners for style checkboxes
    document.querySelectorAll('.style-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', applyFilters);
    });

    // Frame material filter - handle radio button changes
    // The "All" option (value="") will show all bikes
    // Also allow unchecking by clicking a checked radio (except "All")
    
    // Set "All" as default selection on page load
    const allFrameMaterialOption = document.getElementById('frame-material-all');
    if (allFrameMaterialOption && !document.querySelector('input[name="frame_material"]:checked')) {
        allFrameMaterialOption.checked = true;
    }
    
    document.querySelectorAll('input[name="frame_material"]').forEach(radio => {
        let wasCheckedBefore = false;
        
        // Track state before click
        radio.addEventListener('mousedown', function() {
            wasCheckedBefore = this.checked;
        });
        
        // Handle clicks - if clicking a checked radio (except "All"), uncheck it
        radio.addEventListener('click', function(e) {
            // If clicking a checked radio that's not "All", uncheck it and select "All"
            if (wasCheckedBefore && this.value !== '') {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                
                // Select the "All" option instead
                const allOption = document.getElementById('frame-material-all');
                if (allOption) {
                    // Uncheck the current radio first
                    this.checked = false;
                    // Check "All" option
                    allOption.checked = true;
                    // Trigger change event to ensure filters apply
                    allOption.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    // Fallback: uncheck all if "All" option doesn't exist
                    document.querySelectorAll('input[name="frame_material"]').forEach(r => {
                        r.checked = false;
                    });
                    // Apply filters
                    applyFilters();
                }
            }
        });
        
        // Handle normal selection changes
        radio.addEventListener('change', function() {
            applyFilters();
        });
    });

    // Add listener for discount checkbox
    document.querySelectorAll('input[name="has_discount"]').forEach(checkbox => {
        checkbox.addEventListener('change', applyFilters);
    });

    fetch("/api/compare_list")
        .then((res) => res.json())
        .then((data) => updateCompareUI(data.compare_list || []));

    // Attach initial button listeners
    attachCompareButtonListeners();
    attachPurchaseButtonListeners();

    
    // Only load bikes via AJAX if they're not already rendered server-side
    const initialBikesCount = document.querySelectorAll('.bike-card').length;
    if (initialBikesCount === 0) {
        applyFilters();  // initial load
    } else {
        // Bikes are pre-rendered server-side, set up initial state for infinite scroll
        currentOffset = initialBikesCount;
        
        // Still need to set up compare UI for pre-rendered bikes
        fetch("/api/compare_list")
            .then((res) => res.json())
            .then((data) => updateCompareUI(data.compare_list || []));
    }

    // Add global modal cleanup event listener
    document.addEventListener('hidden.bs.modal', function (event) {
        if (event.target.id === 'bikeDetailsModal') {
            // Remove backdrop
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
            
            // Clean up body classes and styles
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }
    });

    // Add event delegation for .bike-card clicks and details buttons
    document.getElementById('bikes-list').addEventListener('click', function(e) {
        const card = e.target.closest('.bike-card');
        if (!card) return;
        
        // Handle three dots menu clicks
        if (e.target.closest('.bike-menu-dots')) {
            e.preventDefault();
            e.stopPropagation();
            const menuButton = e.target.closest('.bike-menu-dots');
            const card = menuButton.closest('.bike-card');
            const bikeId = card.getAttribute('data-bike-id');
            
            // Check if menu is already open
            let existingBackdrop = document.querySelector('.bike-menu-backdrop');
            let existingDropdown = document.querySelector('.bike-menu-dropdown');
            
            if (existingBackdrop || existingDropdown) {
                // Close existing menu
                if (existingBackdrop) existingBackdrop.remove();
                if (existingDropdown) existingDropdown.remove();
                document.body.style.overflow = '';
                return;
            }
            
            // Create backdrop overlay
            const backdrop = document.createElement('div');
            backdrop.className = 'bike-menu-backdrop';
            document.body.appendChild(backdrop);
            document.body.style.overflow = 'hidden';
            
            // Get bike details for sharing
            const bikeBrand = card.querySelector('.bike-brand-link')?.textContent?.trim() || '';
            const bikeModel = card.querySelector('.bike-model')?.textContent?.trim() || '';
            const bikeYear = card.querySelector('.bike-year-header')?.textContent?.trim() || '';
            const bikeName = `${bikeBrand} ${bikeModel}${bikeYear ? ' ' + bikeYear : ''}`.trim();
            
            // Create product page URL
            const productUrl = `${window.location.origin}/bike/${bikeId}`;
            const shareText = `הסתכל על האופניים האלה: ${bikeName}\n${productUrl}`;
            const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
            
            // Create dropdown menu
            const dropdown = document.createElement('div');
            dropdown.className = 'bike-menu-dropdown';
            dropdown.innerHTML = `
                <a href="${whatsappUrl}" target="_blank" class="bike-menu-item" onclick="event.stopPropagation();">
                    <i class="fab fa-whatsapp me-2"></i>
                    שתף ב-WhatsApp
                </a>
                <a href="#" class="bike-menu-item" data-bike-id="${bikeId}">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    דווח על בעיה
                </a>
            `;
            document.body.appendChild(dropdown);
            
            // Position dropdown near the menu button
            const buttonRect = menuButton.getBoundingClientRect();
            dropdown.style.top = (buttonRect.bottom + 5) + 'px';
            dropdown.style.left = buttonRect.left + 'px';
            
            // Handle WhatsApp share click
            const shareButton = dropdown.querySelector('.bike-menu-item[href*="wa.me"]');
            if (shareButton) {
                shareButton.addEventListener('click', function(e) {
                    e.stopPropagation();
                    // Close menu after a short delay to allow WhatsApp to open
                    setTimeout(closeMenu, 100);
                });
            }
            
            // Handle report problem click
            const reportButton = dropdown.querySelector('.bike-menu-item[data-bike-id]');
            if (reportButton) {
                reportButton.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const bikeId = this.getAttribute('data-bike-id');
                    // TODO: Implement report problem functionality
                    alert('דווח על בעיה - Bike ID: ' + bikeId);
                    closeMenu();
                });
            }
            
            // Close function
            function closeMenu() {
                backdrop.remove();
                dropdown.remove();
                document.body.style.overflow = '';
            }
            
            // Close when clicking backdrop
            backdrop.addEventListener('click', closeMenu);
            
            // Close on escape key
            const escapeHandler = function(event) {
                if (event.key === 'Escape') {
                    closeMenu();
                    document.removeEventListener('keydown', escapeHandler);
                }
            };
            document.addEventListener('keydown', escapeHandler);
            
            return;
        }
        
        // Handle brand link clicks - filter by brand
        if (e.target.closest('.bike-brand-link')) {
            e.preventDefault();
            e.stopPropagation();
            const brandLink = e.target.closest('.bike-brand-link');
            // Get brand name from data attribute first, fallback to text content
            const brandName = brandLink.getAttribute('data-brand') || brandLink.textContent.trim();
            
            // Find the corresponding firm checkbox
            const firmCheckboxes = document.querySelectorAll('.firm-checkbox');
            let foundCheckbox = null;
            
            firmCheckboxes.forEach(checkbox => {
                if (checkbox.value === brandName || checkbox.value.trim() === brandName.trim()) {
                    foundCheckbox = checkbox;
                }
            });
            
            if (foundCheckbox) {
                // Uncheck all other firm checkboxes first (single brand selection)
                firmCheckboxes.forEach(cb => {
                    if (cb !== foundCheckbox) {
                        cb.checked = false;
                    }
                });
                
                // Check the selected brand checkbox
                foundCheckbox.checked = true;
                
                // Update dropdown button text to show selected brand
                if (typeof updateFirmDropdownText === 'function') {
                    updateFirmDropdownText();
                }
                
                // Apply filters
                applyFilters();
                
                // Scroll to top of bikes list to show filtered results
                const bikesList = document.getElementById('bikes-list');
                if (bikesList) {
                    bikesList.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            } else {
                console.warn('Brand checkbox not found for:', brandName);
                // Try to apply filter anyway with the brand name directly
                // This handles cases where the brand might not be in the filter list
            }
            
            return;
        }
        
        // Handle details button clicks - open modal (keep existing behavior)
        if (e.target.closest('.details-btn')) {
            const bikeId = card.getAttribute('data-bike-id');
            fetchBikeDetailsAndShowModal(bikeId);
            return;
        }
        
        // Prevent click if compare link, purchase button, details button, or availability button is clicked
        if (e.target.closest('.bike-compare-link') || e.target.closest('.purchase-btn') || e.target.closest('.details-btn') || e.target.closest('.availability-btn') || e.target.closest('.find-store-btn')) return;
        
        // Handle card clicks (excluding buttons) - redirect to detail page
        const bikeId = card.getAttribute('data-bike-id');
        window.location.href = `/bike/${bikeId}`;
    });

    // Sticky compare button functionality
    window.addEventListener('scroll', function() {
        const compareBtn = document.getElementById('go-to-compare');
        if (compareBtn && compareBtn.style.display !== 'none') {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            if (scrollTop > 100) { // Show after scrolling 100px
                compareBtn.style.position = 'fixed';
                compareBtn.style.top = '10px'; // Stick to very top
                compareBtn.style.right = '20px';
                compareBtn.style.zIndex = '1050';
                compareBtn.style.padding = '8px 16px';
                compareBtn.style.borderRadius = '5px';
                compareBtn.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
            } else {
                compareBtn.style.position = 'static';
                compareBtn.style.top = '';
                compareBtn.style.right = '';
                compareBtn.style.zIndex = '';
                compareBtn.style.padding = '';
                compareBtn.style.borderRadius = '';
                compareBtn.style.boxShadow = '';
            }
        }
    });

    // ========== RETURN TO CATEGORIES BUTTON - STICK TO TOP WHEN SCROLLING ==========
    const returnBtn = document.querySelector('.return-to-categories-btn');
    if (returnBtn) {
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            if (scrollTop > 150) { // After scrolling 150px, stick to top
                returnBtn.style.setProperty('top', '5px', 'important');
            } else {
                // Return to original position when near top
                returnBtn.style.setProperty('top', '105px', 'important');
            }
        });
    }

    // ========== BACK TO TOP BUTTON ==========
    // (Infinite scroll removed - all bikes load at once for instant filtering)
    const backToTopBtn = document.getElementById('back-to-top');
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Back to top button visibility
        if (scrollTop > 300) { // Show after scrolling 300px
            backToTopBtn.classList.add('show');
        } else {
            backToTopBtn.classList.remove('show');
        }
    });
    
    // Smooth scroll to top when button is clicked
    backToTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // ========== AVAILABILITY CHECK MODAL ==========
    // Handle availability modal show event to populate bike model
    const availabilityModal = document.getElementById('availabilityModal');
    if (availabilityModal) {
        availabilityModal.addEventListener('show.bs.modal', function(event) {
            // Get the button that triggered the modal
            const button = event.relatedTarget;
            if (button && button.classList.contains('availability-btn')) {
                const bikeModel = button.getAttribute('data-bike-model');
                const bikeId = button.getAttribute('data-bike-id');
                
                // Populate the bike model and ID in the form
                const modelInput = document.getElementById('availability-bike-model');
                const modelDisplay = document.getElementById('availability-bike-display');
                const bikeIdInput = document.getElementById('availability-bike-id');
                if (modelInput) modelInput.value = bikeModel || '';
                if (modelDisplay) modelDisplay.value = bikeModel || '';
                if (bikeIdInput) bikeIdInput.value = bikeId || '';
            }
        });
    }

    // Handle form submission
    const availabilityForm = document.getElementById('availabilityForm');
    if (availabilityForm) {
        availabilityForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Check if agreement checkbox is checked
            const agreementCheckbox = document.getElementById('availability-agreement');
            if (!agreementCheckbox.checked) {
                alert('אנא אשר/י את הסכמתך למדיניות הפרטיות ותנאי השימוש');
                agreementCheckbox.focus();
                return;
            }
            
            const formData = new FormData(availabilityForm);
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || formData.get('csrf_token');
            
            // Show loading state
            const submitBtn = availabilityForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'שולח...';
            
            // Submit via fetch
            fetch(availabilityForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => {
                if (response.ok) {
                    return response.text();
                }
                throw new Error('Network response was not ok');
            })
            .then(data => {
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('availabilityModal'));
                modal.hide();
                
                // Show success message (you can customize this)
                alert('הבקשה נשלחה בהצלחה! נחזור אליך בהקדם.');
                
                // Reset form
                availabilityForm.reset();
            })
            .catch(error => {
                console.error('Error:', error);
                alert('אירעה שגיאה בשליחת הבקשה. אנא נסה שוב.');
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            });
        });
    }

    // ========== FIND STORE MODAL ==========
    // Israeli cities from data.gov.il API
    const api_url = "https://data.gov.il/api/3/action/datastore_search";
    const cities_resource_id = "5c78e9fa-c2e2-4771-93ff-7f400a12f7ba";
    const city_name_key = "שם_ישוב";
    
    // Cache for cities list
    let citiesCache = null;
    let citiesLoading = false;

    /**
     * Get data from gov data API
     */
    const getCitiesData = (limit = "32000") => {
        return fetch(`${api_url}?resource_id=${cities_resource_id}&limit=${limit}`)
            .then(response => response.json())
            .catch(error => {
                console.error('Error fetching cities:', error);
                throw error;
            });
    };

    /**
     * Parse records from data into array of city names
     */
    const parseCitiesResponse = (records = []) => {
        const cities = records
            .map(record => record[city_name_key]?.trim())
            .filter(city => city) // Remove empty values
            .sort(); // Sort alphabetically
        
        // Remove duplicates
        return [...new Set(cities)];
    };

    /**
     * Parse records from data into 'option' elements for datalist
     */
    const parseCitiesForDatalist = (records = []) => {
        const cities = records
            .map(record => record[city_name_key]?.trim())
            .filter(city => city) // Remove empty values
            .sort(); // Sort alphabetically
        
        // Remove duplicates
        const uniqueCities = [...new Set(cities)];
        
        // Return HTML string of options
        return uniqueCities
            .map(city => `<option value="${city.replace(/"/g, '&quot;')}">`)
            .join('\n') || '';
    };

    /**
     * Populate cities datalist from API (for autocomplete input)
     */
    const populateCitiesDatalist = () => {
        const datalist = document.getElementById('find-store-cities-data');
        if (!datalist) {
            console.log('Cities datalist element not found');
            return;
        }

        // If already populated, don't do it again
        if (citiesCache && datalist.children.length > 1) {
            return;
        }

        // If cache exists, use it
        if (citiesCache) {
            const optionsHtml = citiesCache
                .map(city => `<option value="${city.replace(/"/g, '&quot;')}">`)
                .join('\n');
            datalist.innerHTML = optionsHtml;
            return;
        }

        // If already loading, wait
        if (citiesLoading) {
            return;
        }

        // Show loading state
        citiesLoading = true;
        datalist.innerHTML = '<option value="">טוען רשימת ערים...</option>';

        // Fetch cities from API
        getCitiesData()
            .then(response => {
                const records = response?.result?.records || [];
                citiesCache = parseCitiesResponse(records);
                
                // Populate datalist with cities from cache
                const optionsHtml = citiesCache
                    .map(city => `<option value="${city.replace(/"/g, '&quot;')}">`)
                    .join('\n');
                datalist.innerHTML = optionsHtml;
            })
            .catch(error => {
                console.error('Error populating cities:', error);
                datalist.innerHTML = '<option value="">שגיאה בטעינת הערים</option>';
            })
            .finally(() => {
                citiesLoading = false;
            });
    };

    // Handle find store modal show event
    const findStoreModal = document.getElementById('findStoreModal');
    if (findStoreModal) {

        findStoreModal.addEventListener('show.bs.modal', function(event) {
            // Get the button that triggered the modal
            const button = event.relatedTarget;
            if (button && button.classList.contains('find-store-btn')) {
                const bikeModel = button.getAttribute('data-bike-model');
                const bikeId = button.getAttribute('data-bike-id');
                
                // Populate the bike model and ID in the form
                const modelInput = document.getElementById('find-store-bike-model');
                const modelDisplay = document.getElementById('find-store-bike-display');
                const bikeIdInput = document.getElementById('find-store-bike-id');
                
                // Set bike model values
                if (modelInput) {
                    modelInput.value = bikeModel || '';
                }
                if (modelDisplay) {
                    modelDisplay.value = bikeModel || '';
                }
                if (bikeIdInput) {
                    bikeIdInput.value = bikeId || '';
                }
                
                // Populate cities datalist (will use cache if available)
                populateCitiesDatalist();
                
                // Initialize custom autocomplete dropdown after cities are loaded
                setTimeout(() => {
                    initCityAutocomplete();
                }, 100);
                
                // Reset form and hide success message (but preserve bike model)
                const form = document.getElementById('findStoreForm');
                const successMessage = document.getElementById('find-store-success-message');
                const modalBody = document.querySelector('#findStoreModal .modal-body');
                const descriptiveParagraph = modalBody ? modalBody.querySelector('p') : null;
                
                if (form) {
                    // Store bike model values before reset
                    const savedBikeModel = modelInput ? modelInput.value : '';
                    const savedBikeDisplay = modelDisplay ? modelDisplay.value : '';
                    const savedBikeId = bikeIdInput ? bikeIdInput.value : '';
                    
                    form.reset();
                    form.style.display = 'block';
                    
                    // Restore bike model values after reset
                    if (modelInput) modelInput.value = savedBikeModel;
                    if (modelDisplay) modelDisplay.value = savedBikeDisplay;
                    if (bikeIdInput) bikeIdInput.value = savedBikeId;
                }
                if (descriptiveParagraph) {
                    descriptiveParagraph.style.display = 'block';
                }
                if (successMessage) successMessage.style.display = 'none';
            }
        });
    }

    /**
     * Initialize custom city autocomplete dropdown (mobile-friendly)
     */
    let currentHighlightedIndex = -1;
    let filteredCities = [];
    
    const initCityAutocomplete = () => {
        const cityInput = document.getElementById('find-store-city');
        const cityDropdown = document.getElementById('find-store-city-dropdown');
        
        if (!cityInput || !cityDropdown) return;
        
        // Clear any existing event listeners by cloning
        const newInput = cityInput.cloneNode(true);
        cityInput.parentNode.replaceChild(newInput, cityInput);
        
        // Handle input changes
        newInput.addEventListener('input', function(e) {
            const query = e.target.value.trim().toLowerCase();
            currentHighlightedIndex = -1;
            
            if (!citiesCache || citiesCache.length === 0) {
                cityDropdown.style.display = 'none';
                return;
            }
            
            if (query.length === 0) {
                cityDropdown.style.display = 'none';
                return;
            }
            
            // Filter cities
            filteredCities = citiesCache.filter(city => 
                city.toLowerCase().includes(query)
            );
            
            // Show dropdown with filtered results
            if (filteredCities.length > 0) {
                renderCityDropdown(filteredCities, query);
                cityDropdown.style.display = 'block';
            } else {
                cityDropdown.innerHTML = '<div class="city-option no-results">לא נמצאו ערים</div>';
                cityDropdown.style.display = 'block';
            }
        });
        
        // Handle focus
        newInput.addEventListener('focus', function(e) {
            const query = e.target.value.trim().toLowerCase();
            if (query.length > 0 && filteredCities.length > 0) {
                cityDropdown.style.display = 'block';
            }
        });
        
        // Handle keyboard navigation
        newInput.addEventListener('keydown', function(e) {
            if (!cityDropdown.style.display || cityDropdown.style.display === 'none') {
                return;
            }
            
            const options = cityDropdown.querySelectorAll('.city-option:not(.no-results)');
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                currentHighlightedIndex = Math.min(currentHighlightedIndex + 1, options.length - 1);
                updateHighlight(options);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                currentHighlightedIndex = Math.max(currentHighlightedIndex - 1, -1);
                updateHighlight(options);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (currentHighlightedIndex >= 0 && options[currentHighlightedIndex]) {
                    const cityName = options[currentHighlightedIndex].getAttribute('data-city');
                    selectCity(cityName);
                }
            } else if (e.key === 'Escape') {
                cityDropdown.style.display = 'none';
            }
        });
        
        // Hide dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!newInput.contains(e.target) && !cityDropdown.contains(e.target)) {
                cityDropdown.style.display = 'none';
            }
        });
    };
    
    /**
     * Render city dropdown options
     */
    const renderCityDropdown = (cities, query) => {
        const cityDropdown = document.getElementById('find-store-city-dropdown');
        if (!cityDropdown) return;
        
        // Limit to 10 results for better performance
        const limitedCities = cities.slice(0, 10);
        
        const html = limitedCities.map((city, idx) => {
            // Highlight matching text
            const index = city.toLowerCase().indexOf(query);
            const cityHtml = index >= 0 
                ? `${city.substring(0, index)}<strong>${city.substring(index, index + query.length)}</strong>${city.substring(index + query.length)}`
                : city;
            return `<div class="city-option" data-city="${city.replace(/"/g, '&quot;')}">${cityHtml}</div>`;
        }).join('');
        
        cityDropdown.innerHTML = html;
        
        // Add click handlers
        cityDropdown.querySelectorAll('.city-option').forEach(option => {
            option.addEventListener('click', function() {
                const cityName = this.getAttribute('data-city');
                selectCity(cityName);
            });
        });
    };
    
    /**
     * Update highlighted option
     */
    const updateHighlight = (options) => {
        options.forEach((opt, idx) => {
            opt.classList.toggle('highlighted', idx === currentHighlightedIndex);
        });
        
        // Scroll into view
        if (currentHighlightedIndex >= 0 && options[currentHighlightedIndex]) {
            options[currentHighlightedIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    };
    
    /**
     * Select a city
     */
    const selectCity = (city) => {
        const cityInput = document.getElementById('find-store-city');
        const cityDropdown = document.getElementById('find-store-city-dropdown');
        
        if (cityInput) {
            cityInput.value = city;
            cityInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
        if (cityDropdown) {
            cityDropdown.style.display = 'none';
        }
        
        currentHighlightedIndex = -1;
    };

    // Handle find store form submission
    const findStoreForm = document.getElementById('findStoreForm');
    if (findStoreForm) {
        findStoreForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(findStoreForm);
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || formData.get('csrf_token');
            
            // Show loading state
            const submitBtn = findStoreForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'שולח...';
            
            // Submit via fetch
            fetch(findStoreForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => {
                if (response.ok) {
                    return response.text();
                }
                throw new Error('Network response was not ok');
            })
            .then(data => {
                // Hide form and descriptive paragraph, show success message
                findStoreForm.style.display = 'none';
                const modalBody = findStoreForm.closest('.modal-body');
                const descriptiveParagraph = modalBody ? modalBody.querySelector('p') : null;
                if (descriptiveParagraph) {
                    descriptiveParagraph.style.display = 'none';
                }
                
                const successMessage = document.getElementById('find-store-success-message');
                if (successMessage) {
                    // Ensure only the intended text is shown
                    successMessage.textContent = 'תודה! החנות תיצור קשר בהקדם.';
                    successMessage.style.display = 'block';
                }
                
                // Close modal after 2 seconds
                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('findStoreModal'));
                    modal.hide();
                    
                    // Reset form and show it again for next time
                    findStoreForm.reset();
                    findStoreForm.style.display = 'block';
                    if (descriptiveParagraph) {
                        descriptiveParagraph.style.display = 'block';
                    }
                    if (successMessage) successMessage.style.display = 'none';
                }, 2000);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('אירעה שגיאה בשליחת הבקשה. אנא נסה שוב.');
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            });
        });
    }
});

// Function to toggle collapsible values in bike details modal
function toggleValue(button) {
    const cell = button.parentElement;
    const shortSpan = cell.querySelector('.cell-short');
    const fullSpan = cell.querySelector('.cell-full');
    
    if (fullSpan.style.display === 'none') {
        // Show full value
        shortSpan.style.display = 'none';
        fullSpan.style.display = 'inline';
        button.textContent = 'הצג פחות';
    } else {
        // Show short value
        shortSpan.style.display = 'inline';
        fullSpan.style.display = 'none';
        button.textContent = 'הצג עוד';
    }
}

// Function to change main image in gallery
function changeMainImage(imageUrl, thumbnailElement) {
    // Update main image
    const mainImage = document.getElementById('main-bike-image');
    if (mainImage) {
        mainImage.src = imageUrl;
        mainImage.referrerPolicy = "no-referrer";
        // Update the onclick handler for the new image
        mainImage.onclick = () => openImageZoom(imageUrl, mainImage.alt);
    }
    
    // Update active thumbnail
    const allThumbnails = document.querySelectorAll('.gallery-thumbnail');
    allThumbnails.forEach(thumb => thumb.classList.remove('active'));
    thumbnailElement.classList.add('active');
}

// Function to open image zoom modal
function openImageZoom(imageUrl, imageAlt) {
    // Create zoom modal if it doesn't exist
    let zoomModal = document.getElementById('imageZoomModal');
    if (!zoomModal) {
        zoomModal = document.createElement('div');
        zoomModal.id = 'imageZoomModal';
        zoomModal.className = 'image-zoom-modal';
        zoomModal.innerHTML = `
            <div class="zoom-modal-content">
                <div class="zoom-modal-header">
                    <button type="button" class="zoom-close-btn" onclick="closeImageZoom()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="zoom-modal-body">
                    <img src="" alt="" class="zoomed-image" id="zoomedImage" referrerpolicy="no-referrer">
                </div>
                <div class="zoom-controls">
                    <button class="zoom-btn" onclick="zoomIn()">
                        <i class="fas fa-search-plus"></i>
                    </button>
                    <button class="zoom-btn" onclick="zoomOut()">
                        <i class="fas fa-search-minus"></i>
                    </button>
                    <button class="zoom-btn" onclick="resetZoom()">
                        <i class="fas fa-expand-arrows-alt"></i>
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(zoomModal);
    }
    
    // Set the image
    const zoomedImage = document.getElementById('zoomedImage');
    zoomedImage.src = imageUrl;
    zoomedImage.alt = imageAlt;
    zoomedImage.referrerPolicy = "no-referrer";
    
    // Reset zoom and pan
    resetZoom();
    
    // Set up drag handlers
    setupDragHandlers();
    
    // Show modal
    zoomModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// Function to close image zoom modal
function closeImageZoom() {
    const zoomModal = document.getElementById('imageZoomModal');
    if (zoomModal) {
        // Clean up drag handlers
        cleanupDragHandlers();
        
        zoomModal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// Zoom and pan variables
let currentZoom = 1;
let currentPanX = 0;
let currentPanY = 0;
const zoomStep = 0.3;
const maxZoom = 5;
const minZoom = 0.5;

// Drag variables
let isDragging = false;
let startX = 0;
let startY = 0;
let lastX = 0;
let lastY = 0;

function zoomIn() {
    if (currentZoom < maxZoom) {
        currentZoom += zoomStep;
        applyTransform();
    }
}

function zoomOut() {
    if (currentZoom > minZoom) {
        currentZoom -= zoomStep;
        applyTransform();
    }
}

function resetZoom() {
    currentZoom = 1;
    currentPanX = 0;
    currentPanY = 0;
    applyTransform();
}

function applyTransform() {
    const zoomedImage = document.getElementById('zoomedImage');
    if (zoomedImage) {
        zoomedImage.style.transform = `translate(${currentPanX}px, ${currentPanY}px) scale(${currentZoom})`;
    }
}

// Mouse event handlers for dragging
function setupDragHandlers() {
    const zoomedImage = document.getElementById('zoomedImage');
    if (!zoomedImage) return;

    // Mouse events
    zoomedImage.addEventListener('mousedown', startDrag);
    document.addEventListener('mousemove', drag);
    document.addEventListener('mouseup', endDrag);

    // Touch events for mobile
    zoomedImage.addEventListener('touchstart', startDragTouch);
    document.addEventListener('touchmove', dragTouch);
    document.addEventListener('touchend', endDrag);

    // Prevent context menu on right click
    zoomedImage.addEventListener('contextmenu', (e) => e.preventDefault());
}

function startDrag(e) {
    if (currentZoom > 1) {
        isDragging = true;
        startX = e.clientX - currentPanX;
        startY = e.clientY - currentPanY;
        lastX = e.clientX;
        lastY = e.clientY;
        
        // Add dragging class for visual feedback
        const zoomedImage = document.getElementById('zoomedImage');
        if (zoomedImage) {
            zoomedImage.classList.add('dragging');
        }
        
        e.preventDefault();
    }
}

function startDragTouch(e) {
    if (currentZoom > 1 && e.touches.length === 1) {
        isDragging = true;
        const touch = e.touches[0];
        startX = touch.clientX - currentPanX;
        startY = touch.clientY - currentPanY;
        lastX = touch.clientX;
        lastY = touch.clientY;
        
        // Add dragging class for visual feedback
        const zoomedImage = document.getElementById('zoomedImage');
        if (zoomedImage) {
            zoomedImage.classList.add('dragging');
        }
        
        e.preventDefault();
    }
}

function drag(e) {
    if (isDragging && currentZoom > 1) {
        const deltaX = e.clientX - lastX;
        const deltaY = e.clientY - lastY;
        
        currentPanX += deltaX;
        currentPanY += deltaY;
        
        lastX = e.clientX;
        lastY = e.clientY;
        
        applyTransform();
        e.preventDefault();
    }
}

function dragTouch(e) {
    if (isDragging && currentZoom > 1 && e.touches.length === 1) {
        const touch = e.touches[0];
        const deltaX = touch.clientX - lastX;
        const deltaY = touch.clientY - lastY;
        
        currentPanX += deltaX;
        currentPanY += deltaY;
        
        lastX = touch.clientX;
        lastY = touch.clientY;
        
        applyTransform();
        e.preventDefault();
    }
}

function endDrag() {
    isDragging = false;
    
    // Remove dragging class
    const zoomedImage = document.getElementById('zoomedImage');
    if (zoomedImage) {
        zoomedImage.classList.remove('dragging');
    }
}

// Clean up event listeners when modal closes
function cleanupDragHandlers() {
    const zoomedImage = document.getElementById('zoomedImage');
    if (zoomedImage) {
        zoomedImage.removeEventListener('mousedown', startDrag);
        zoomedImage.removeEventListener('touchstart', startDragTouch);
    }
    document.removeEventListener('mousemove', drag);
    document.removeEventListener('mouseup', endDrag);
    document.removeEventListener('touchmove', dragTouch);
    document.removeEventListener('touchend', endDrag);
}

// ========== FILTER HELP TOOLTIPS ==========
(function initFilterTooltips() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTooltips);
    } else {
        initTooltips();
    }
    
    function initTooltips() {
        // Create backdrop for mobile tooltips if it doesn't exist
        let tooltipBackdrop = document.getElementById('tooltip-backdrop');
        if (!tooltipBackdrop) {
            tooltipBackdrop = document.createElement('div');
            tooltipBackdrop.id = 'tooltip-backdrop';
            tooltipBackdrop.className = 'tooltip-backdrop';
            document.body.appendChild(tooltipBackdrop);
        }
        
        // Get all help icons
        const helpIcons = document.querySelectorAll('.filter-help-icon');
        let activeTooltip = null;
        
        // Check if we're on a large screen
        function isLargeScreen() {
            return window.matchMedia('(min-width: 992px)').matches;
        }
        
        // Function to show tooltip
        function showTooltip(icon, tooltipId) {
            // Hide any currently active tooltip
            if (activeTooltip) {
                hideTooltip(activeTooltip);
            }
            
            const tooltip = document.getElementById(`tooltip-${tooltipId}`);
            if (!tooltip) return;
            
            activeTooltip = tooltipId;
            
            if (isLargeScreen()) {
                // Large screen: show on hover (CSS handles most of it, but we handle click too)
                tooltip.classList.add('show');
            } else {
                // Medium/small screen: show modal-style tooltip with backdrop
                // Move tooltip to body level to avoid offcanvas dimming effects
                if (tooltip.parentElement !== document.body) {
                    const originalParent = tooltip.parentElement;
                    tooltip.setAttribute('data-original-parent', originalParent ? 'true' : 'false');
                    document.body.appendChild(tooltip);
                }
                tooltipBackdrop.classList.add('show');
                tooltip.classList.add('show');
            }
        }
        
        // Function to hide tooltip
        function hideTooltip(tooltipId) {
            const tooltip = document.getElementById(`tooltip-${tooltipId}`);
            if (tooltip) {
                tooltip.classList.remove('show');
                // Return tooltip to original position after a brief delay
                setTimeout(() => {
                    if (!tooltip.classList.contains('show')) {
                        // Find the original parent by checking the HTML structure
                        // We'll keep it simple - just move it back if needed
                        const offcanvasBody = document.querySelector('#offcanvasFilters .offcanvas-body');
                        if (offcanvasBody && tooltip.parentElement === document.body) {
                            // Try to find where it should go based on filter ID
                            let targetContainer = null;
                            if (tooltipId === 'price') {
                                targetContainer = document.querySelector('.prices-label');
                            } else if (tooltipId === 'battery') {
                                targetContainer = document.querySelector('.wh-label');
                            } else if (tooltipId === 'fork') {
                                targetContainer = document.querySelector('.fork-label');
                            } else if (tooltipId === 'brand') {
                                targetContainer = document.querySelector('#offcanvasFilters .mb-3:has(label:contains("מותג"))');
                            } else if (tooltipId === 'frame-material') {
                                targetContainer = document.querySelector('#offcanvasFilters .mb-3:has(label:contains("חומר שלדה"))');
                            }
                            
                            if (targetContainer) {
                                targetContainer.appendChild(tooltip);
                            } else {
                                // Default: put it back in offcanvas body
                                offcanvasBody.appendChild(tooltip);
                            }
                        }
                    }
                }, 300);
            }
            if (tooltipBackdrop) {
                tooltipBackdrop.classList.remove('show');
            }
            activeTooltip = null;
        }
        
        // Handle clicks on help icons (for all screen sizes)
        helpIcons.forEach(icon => {
            const filterType = icon.getAttribute('data-filter');
            
            // Click handler for medium/small screens and toggle on large screens
            icon.addEventListener('click', (e) => {
                e.stopPropagation();
                
                if (activeTooltip === filterType) {
                    // Already showing this tooltip, hide it
                    hideTooltip(filterType);
                } else {
                    // Show this tooltip
                    showTooltip(icon, filterType);
                }
            });
        });
        
        // Handle close button clicks
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('tooltip-close')) {
                e.stopPropagation();
                if (activeTooltip) {
                    hideTooltip(activeTooltip);
                }
            }
        });
        
        // Hide tooltip when clicking on backdrop (mobile/tablet)
        tooltipBackdrop.addEventListener('click', () => {
            if (activeTooltip) {
                hideTooltip(activeTooltip);
            }
        });
        
        // Hide tooltip when clicking outside (mobile/tablet)
        document.addEventListener('click', (e) => {
            if (!isLargeScreen() && activeTooltip) {
                const tooltip = document.getElementById(`tooltip-${activeTooltip}`);
                const icon = document.querySelector(`[data-filter="${activeTooltip}"]`);
                
                if (tooltip && icon && 
                    !tooltip.contains(e.target) && 
                    !icon.contains(e.target) &&
                    !e.target.classList.contains('tooltip-close')) {
                    hideTooltip(activeTooltip);
                }
            }
        });
        
        // Hide tooltip on window resize if switching from small to large
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                if (isLargeScreen() && activeTooltip) {
                    // On large screens, tooltips work better with hover
                    // But we keep click functionality too
                }
            }, 250);
        });
        
        // Close tooltip on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && activeTooltip) {
                hideTooltip(activeTooltip);
            }
        });
    }
})();
