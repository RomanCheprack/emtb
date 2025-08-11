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

document.addEventListener("DOMContentLoaded", () => {
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

    const sortDropdown = document.getElementById("sort-price");

    // Cache DOM elements for better performance
    const bikesList = document.getElementById("bikes-list");
    const bikesCount = document.getElementById("bikes-count");
    const firmDropdown = document.getElementById('firmDropdown');
    const motorBrandDropdown = document.getElementById('motorBrandDropdown');

    // Debounce function for search input
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

    noUiSlider.create(priceSlider, {
        start: [0, 100000],
        connect: true,
        step: 100,
        range: { min: 0, max: 100000 },
        format: {
            to: (val) => Math.round(val),
            from: (val) => Number(val),
        },
    });

    priceSlider.noUiSlider.on("update", (values) => {
        minPriceInput.value = values[0];
        maxPriceInput.value = values[1];
        minPriceValue.textContent = values[0];
        maxPriceValue.textContent = values[1];
    });

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
            noResultsDiv.className = 'col-12';
            noResultsDiv.innerHTML = '<p>לא נמצאו תוצאות.</p>';
            fragment.appendChild(noResultsDiv);
        } else {
            bikes.forEach((bike) => {
                const bikeDiv = document.createElement('div');
                bikeDiv.className = 'col-6 col-lg-2 mb-2 px-1';
                bikeDiv.innerHTML = `
                    <div class="card h-100 position-relative bike-card" data-bike='${JSON.stringify(bike)}'>
                        <img src="${bike["image_url"]}" class="card-img-top" alt="${bike.model}">
                        <div class="card-body">
                            <h2 class="card-firm">${bike.firm}</h2>
                            <p class="card-title">${bike.model}</p>
                            <p class="card-text-price">
                               ${bike.disc_price && bike.disc_price !== "#N/A"
                                    ? `${formatNumberWithCommas(bike.price) === 'צור קשר' 
                                        ? `<span style="text-decoration: line-through; color: #888;">${formatNumberWithCommas(bike.price)}</span>`
                                        : `<span style="text-decoration: line-through; color: #888;">₪ ${formatNumberWithCommas(bike.price)}</span>`
                                    }
                                    <br>
                                    ${formatNumberWithCommas(bike.disc_price) === 'צור קשר'
                                        ? `<span class="text-danger fw-bold ms-2">${formatNumberWithCommas(bike.disc_price)}</span>`
                                        : `<span class="text-danger fw-bold ms-2">₪ ${formatNumberWithCommas(bike.disc_price)}</span>`
                                    }`
                                   : `${formatNumberWithCommas(bike.price) === 'צור קשר'
                                        ? formatNumberWithCommas(bike.price)
                                        : `₪ ${formatNumberWithCommas(bike.price)}`
                                    }`}
                            </p>
                            <p class="card-text-year">${bike.year}</p>
                            <div class="details-btn mb-2">
                                <button type="button" class="btn btn-outline-info details-btn" data-bike='${JSON.stringify(bike)}'>מפרט</button>
                            </div>
                            <div class="compare-btn-container">
                                <button class="btn btn-compare compare-btn" data-bike-id="${bike.id}">
                                    <i class="fas fa-balance-scale me-1"></i>
                                    הוסף להשוואה
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

    function applyFilters() {
        const query = searchInput.value.trim();
        const min_price = minPriceInput.value;
        const max_price = maxPriceInput.value;
        const min_battery = minBatteryInput.value;
        const max_battery = maxBatteryInput.value;

        const firms = Array.from(document.querySelectorAll('.firm-checkbox:checked')).map(cb => cb.value);
        const motorBrands = Array.from(document.querySelectorAll('.motor-brand-checkbox:checked')).map(cb => cb.value);
        const subCategories = Array.from(document.querySelectorAll('.sub-category-checkbox:checked')).map(cb => cb.value);

        const frameMaterial = document.querySelector('input[name="frame_material"]:checked')?.value;

        const params = new URLSearchParams();
        if (query) params.append("q", query);
        if (min_price) params.append("min_price", min_price);
        if (max_price) params.append("max_price", max_price);
        if (min_battery) params.append("min_battery", min_battery);
        if (max_battery) params.append("max_battery", max_battery);
        firms.forEach(f => params.append("firm", f));
        motorBrands.forEach(brand => params.append("motor_brand", brand));
        subCategories.forEach(cat => params.append("sub_category", cat));
        if (frameMaterial) params.append("frame_material", frameMaterial);

        const years = Array.from(document.querySelectorAll('input[name="year"]:checked')).map(cb => cb.value);
        years.forEach(y => params.append("year", y));

        fetch(`/api/filter_bikes?${params.toString()}`)
            .then((res) => {
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                return res.json();
            })
            .then((bikes) => {
                const sortOrder = sortDropdown.value;
                if (sortOrder === "asc") {
                    bikes.sort((a, b) =>
                        parseInt(a.Price?.replace(/[^\d]/g, '')) - parseInt(b.Price?.replace(/[^\d]/g, ''))
                    );
                } else if (sortOrder === "desc") {
                    bikes.sort((a, b) =>
                        parseInt(b.Price?.replace(/[^\d]/g, '')) - parseInt(a.Price?.replace(/[^\d]/g, ''))
                    );
                }

                // Clear and update bikes list efficiently
                bikesList.innerHTML = "";
                const bikesFragment = generateBikesHTML(bikes);
                bikesList.appendChild(bikesFragment);

                // Update count
                bikesCount.textContent = `נמצאו ${bikes.length} אופניים`;

                attachCompareButtonListeners();
                // Restore compare UI state after regenerating HTML
                fetch("/api/compare_list")
                    .then((res) => res.json())
                    .then((data) => updateCompareUI(data.compare_list || []));
            })
            .catch((err) => {
                console.error("❌ Error in fetch or JSON:", err);
            });
    }

    function attachCompareButtonListeners() {
        document.querySelectorAll(".compare-btn").forEach((btn) => {
            btn.onclick = () => {
                const bikeId = btn.getAttribute("data-bike-id");
                const isSelected = btn.classList.contains("selected");
                
                const url = isSelected
                    ? `/remove_from_compare`
                    : `/add_to_compare`;

                console.log(`Sending ${isSelected ? 'remove' : 'add'} request for bike ID: ${bikeId}`);
                console.log(`Full URL: ${url}`);
                fetch(url, { 
                    method: "POST",
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ bike_id: bikeId })
                })
                    .then((res) => {
                        console.log(`Response status: ${res.status}`);
                        console.log(`Response headers:`, res.headers);
                        
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
                        console.log("Response data:", data);
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

    function updateCompareUI(compareList) {
        console.log("Updating compare UI with list:", compareList);
        document.querySelectorAll(".compare-btn").forEach((btn) => {
            const bikeId = btn.getAttribute("data-bike-id");
            const card = btn.closest(".card");
            
            console.log(`Checking bike ${bikeId} - in list: ${compareList.includes(bikeId)}`);
            
            if (compareList.includes(bikeId)) {
                btn.classList.add("selected");
                btn.innerHTML = '<i class="fas fa-check me-1"></i>הסר השוואה';
                card.classList.add("compare-selected");
            } else {
                btn.classList.remove("selected");
                btn.innerHTML = '<i class="fas fa-balance-scale me-1"></i>הוסף להשוואה';
                card.classList.remove("compare-selected");
            }
        });

        const compareBtn = document.getElementById("go-to-compare");
        const compareCount = document.getElementById("compare-count");
        if (compareList.length > 0) {
            compareBtn.style.display = "inline-block";
            compareCount.textContent = `${compareList.length}`;
        } else {
            compareBtn.style.display = "none";
        }
    }

    function showBikeDetailsModal(bike) {
        console.log('Showing bike details modal for:', bike);
        
        // Validate bike object
        if (!bike || typeof bike !== 'object') {
            console.error('Invalid bike object:', bike);
            alert('שגיאה: נתוני האופניים לא תקינים');
            return;
        }
        
        // Field translations and organization
        const fieldTranslations = {
            'firm': 'מותג',
            'model': 'דגם',
            'year': 'שנה',
            'price': 'מחיר',
            'disc_price': 'מחיר מבצע',
            'motor': 'מנוע',
            'battery': 'סוללה',
            'wh': 'קיבולת סוללה',
            'fork': 'בולם קדמי',
            'rear_shock': 'בולם אחורי',
            'frame': 'שלדה',
            'tires': 'גלגלים',
            'brakes': 'בלמים',
            'weight': 'משקל',
            'wheel_size': 'גודל גלגלים',
            'sub_category': 'סוג אופניים',
            'size': 'גודל',
            'gear_count': 'מספר הילוכים',
            'front_brake': 'בלם קדמי',
            'rear_brake': 'בלם אחורי',
            'front_tire': 'צמיג קדמי',
            'rear_tire': 'צמיג אחורי',
            'saddle': 'אוכף',
            'pedals': 'דוושות',
            'charger': 'מטען',
            'screen': 'מסך',
            'extras': 'תוספות'
        };
        
        // Define the order of fields to display
        const fieldOrder = [
            'firm',
            'model', 
            'year',
            'price',
            'disc_price',
            'motor',
            'battery',
            'wh',
            'frame',
            'fork',
            'rear_shock',
            'weight',
            'wheel_size',
            'sub_category',
            'size',
            'gear_count',
            'front_brake',
            'rear_brake',
            'front_tire',
            'rear_tire',
            'saddle',
            'pedals',
            'charger',
            'screen',
            'extras'
        ];
        
        let html = `
            <div class="row">
                <div class="col-md-4">
                    <img src="${bike['image_url'] || ''}" class="img-fluid" alt="${bike.model || 'Bike'}">
                </div>
                <div class="col-md-8">
                    <table class="table table-striped">
                        <tbody>
        `;

        // Display fields in the specified order
        fieldOrder.forEach((key) => {
            if (
                bike[key] &&
                bike[key] !== "#N/A" &&
                bike[key] !== "N/A" &&
                String(bike[key]).trim() !== ""
            ) {
                let value = bike[key];
                // Format price fields with commas and shekel symbol
                if (key === 'price' || key === 'disc_price') {
                    const formattedValue = formatNumberWithCommas(bike[key]);
                    if (formattedValue === 'צור קשר') {
                        value = formattedValue;
                    } else {
                        value = `₪ ${formattedValue}`;
                    }
                }
                
                // Translate the field name
                const translatedKey = fieldTranslations[key] || key;
                html += `<tr><th style="width:40%; text-align: right;">${translatedKey}</th><td style="text-align: left;">${value}</td></tr>`;
            }
        });

        html += `
                        </tbody>
                    </table>
                </div>
                <div class="mt-3">
                    ${bike['product_url'] ? `<a href="${bike['product_url']}" class="btn btn-info" target="_blank">לרכישה</a>` : ''}
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
            
            const modal = new bootstrap.Modal(modalElement);
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

    // Optimized reset filters function
    document.getElementById("reset-filters").addEventListener("click", () => {
        // Show loading state
        const resetBtn = document.getElementById("reset-filters");
        const originalText = resetBtn.textContent;
        resetBtn.textContent = "מאפס...";
        resetBtn.disabled = true;

        // Reset sliders
        priceSlider.noUiSlider.set([0, 100000]);
        batterySlider.noUiSlider.set([200, 1000]);
        
        // Reset inputs
        searchInput.value = "";
        sortDropdown.value = "none";

        // Batch DOM operations for better performance
        const allCheckboxes = [
            ...document.querySelectorAll('input[name="year"]'),
            ...document.querySelectorAll('input[name="frame_material"]'),
            ...document.querySelectorAll('.firm-checkbox'),
            ...document.querySelectorAll('.motor-brand-checkbox'),
            ...document.querySelectorAll('.sub-category-checkbox')
        ];
        
        allCheckboxes.forEach(cb => {
            cb.checked = false;
        });

        // Update dropdown texts
        updateFirmDropdownText();
        updateMotorBrandDropdownText();

        // Clear compare and apply filters in parallel
        Promise.all([
            fetch("/clear_compare", { method: "POST" }),
            fetch(`/api/filter_bikes`)
        ])
        .then(([clearRes, filterRes]) => {
            return Promise.all([
                clearRes.json(),
                filterRes.json()
            ]);
        })
        .then(([clearData, bikes]) => {
            // Update compare UI
            updateCompareUI([]);
            
            // Update bikes list
            const sortOrder = sortDropdown.value;
            if (sortOrder === "asc") {
                bikes.sort((a, b) =>
                    parseInt(a.Price?.replace(/[^\d]/g, '')) - parseInt(b.Price?.replace(/[^\d]/g, ''))
                );
            } else if (sortOrder === "desc") {
                bikes.sort((a, b) =>
                    parseInt(b.Price?.replace(/[^\d]/g, '')) - parseInt(a.Price?.replace(/[^\d]/g, ''))
                );
            }

            bikesList.innerHTML = "";
            const bikesFragment = generateBikesHTML(bikes);
            bikesList.appendChild(bikesFragment);
            bikesCount.textContent = `נמצאו ${bikes.length} אופניים`;

            attachCompareButtonListeners();
        })
        .catch((err) => {
            console.error("Error in reset:", err);
        })
        .finally(() => {
            // Restore button state
            resetBtn.textContent = originalText;
            resetBtn.disabled = false;
        });
    });

    sortDropdown.addEventListener("change", applyFilters);
    
    // Debounced search input
    const debouncedApplyFilters = debounce(applyFilters, 300);
    searchInput.addEventListener("input", debouncedApplyFilters);
    
    document.querySelectorAll('input[name="year"], input[name="firm"]').forEach((cb) =>
        cb.addEventListener("change", applyFilters)
    );

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

    // Add listeners for sub-category checkboxes
    document.querySelectorAll('.sub-category-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', applyFilters);
    });

    fetch("/api/compare_list")
        .then((res) => res.json())
        .then((data) => updateCompareUI(data.compare_list || []));

    // Debug: Check initial bike data structure
    console.log('Initial bikes count:', document.querySelectorAll('.bike-card').length);
    document.querySelectorAll('.bike-card').forEach((card, index) => {
        const bikeData = card.getAttribute('data-bike');
        console.log(`Bike ${index + 1} data:`, bikeData);
        try {
            const bike = JSON.parse(bikeData);
            console.log(`Bike ${index + 1} parsed successfully:`, bike);
        } catch (error) {
            console.error(`Bike ${index + 1} JSON parse error:`, error);
        }
    });
    
    applyFilters();  // initial load

    // Add event delegation for .bike-card clicks and details buttons
    document.getElementById('bikes-list').addEventListener('click', function(e) {
        const card = e.target.closest('.bike-card');
        if (!card) return;
        
        // Handle details button clicks
        if (e.target.closest('.details-btn')) {
            try {
                const bikeData = card.getAttribute('data-bike');
                console.log('Details button clicked, bike data:', bikeData);
                const bike = JSON.parse(bikeData);
                showBikeDetailsModal(bike);
            } catch (error) {
                console.error('Error parsing bike data for details button:', error);
                console.error('Raw bike data:', card.getAttribute('data-bike'));
                alert('שגיאה בטעינת פרטי האופניים. אנא נסה שוב.');
            }
            return;
        }
        
        // Prevent click if compare button is clicked
        if (e.target.closest('.compare-btn')) return;
        
        // Handle card clicks (excluding buttons)
        try {
            const bikeData = card.getAttribute('data-bike');
            console.log('Card clicked, bike data:', bikeData);
            const bike = JSON.parse(bikeData);
            showBikeDetailsModal(bike);
        } catch (error) {
            console.error('Error parsing bike data for card click:', error);
            console.error('Raw bike data:', card.getAttribute('data-bike'));
            alert('שגיאה בטעינת פרטי האופניים. אנא נסה שוב.');
        }
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
});
