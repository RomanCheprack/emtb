﻿document.addEventListener("DOMContentLoaded", () => {
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
        const dropdownButton = document.getElementById('firmDropdown');
        
        if (selectedFirms.length === 0) {
            dropdownButton.textContent = 'בחר מותגים';
        } else if (selectedFirms.length === 1) {
            dropdownButton.textContent = selectedFirms[0];
        } else {
            dropdownButton.textContent = `${selectedFirms.length} מותגים נבחרו`;
        }
    }

    function updateMotorBrandDropdownText() {
        const selectedMotorBrands = Array.from(document.querySelectorAll('.motor-brand-checkbox:checked')).map(cb => cb.value);
        const dropdownButton = document.getElementById('motorBrandDropdown');
        
        if (selectedMotorBrands.length === 0) {
            dropdownButton.textContent = 'בחר מותגי מנוע';
        } else if (selectedMotorBrands.length === 1) {
            dropdownButton.textContent = selectedMotorBrands[0].charAt(0).toUpperCase() + selectedMotorBrands[0].slice(1);
        } else {
            dropdownButton.textContent = `${selectedMotorBrands.length} מותגי מנוע נבחרו`;
        }
    }

    function applyFilters() {
        const query = searchInput.value.trim();
        const min_price = minPriceInput.value;
        const max_price = maxPriceInput.value;
        const min_battery = minBatteryInput.value;
        const max_battery = maxBatteryInput.value;

        const firms = Array.from(document.querySelectorAll('.firm-checkbox:checked')).map(cb => cb.value);
        const motorBrands = Array.from(document.querySelectorAll('.motor-brand-checkbox:checked')).map(cb => cb.value);

        const frameMaterial = document.querySelector('input[name="frame_material"]:checked')?.value;

        const params = new URLSearchParams();
        if (query) params.append("q", query);
        if (min_price) params.append("min_price", min_price);
        if (max_price) params.append("max_price", max_price);
        if (min_battery) params.append("min_battery", min_battery);
        if (max_battery) params.append("max_battery", max_battery);
        firms.forEach(f => params.append("firm", f));
        motorBrands.forEach(brand => params.append("motor_brand", brand));
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

                const bikesList = document.getElementById("bikes-list");
                const bikesCount = document.getElementById("bikes-count");
                bikesList.innerHTML = "";

                if (bikes.length === 0) {
                    bikesList.innerHTML = `<div class="col-12"><p>לא נמצאו תוצאות.</p></div>`;
                    bikesCount.textContent = `נמצאו 0 אופניים`;
                } else {
                    bikesCount.textContent = `נמצאו ${bikes.length} אופניים`;
                    bikes.forEach((bike) => {
                        bikesList.innerHTML += `
                    <div class="col-6 col-lg-2 mb-2 px-1">
                        <div class="card h-100 position-relative bike-card" data-bike='${JSON.stringify(bike)}'>
                            <img src="${bike["Image URL"]}" class="card-img-top" alt="${bike.Model}">
                            <div class="card-body">
                                <h4 class="card-firm">${bike.Firm}</h4>
                                <p class="card-title">${bike.Model}</p>
                                <h6 class="card-text-price">
                                   ${bike.Disc_price && bike.Disc_price !== "#N/A"
                                        ? `<span style="text-decoration: line-through; color: #888;">₪${bike.Price}</span>
                                        <span class="text-danger fw-bold ms-2">₪${bike.Disc_price}</span>`
                                   : `₪${bike.Price}`}

                                </h6>
                                <p class="card-text-year">${bike.Year}</p>
                                <div class="details-btn mb-2">
                                    <button type="button" class="btn btn-outline-dark details-btn" data-bike='${JSON.stringify(bike)}'>מפרט</button>
                                </div>
                                <div class="compare-btn-container">
                                    <button class="btn btn-compare compare-btn" data-bike-id="${bike.id}">
                                        <i class="fas fa-balance-scale me-1"></i>
                                        הוסף להשוואה
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                    });
                }

                attachCompareButtonListeners();
                 //attachDetailsButtonListeners(); // ✅ make sure this exists somewhere above!
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
                    ? `/remove_from_compare/${bikeId}`
                    : `/add_to_compare/${bikeId}`;

                fetch(url, { method: "POST" })
                    .then((res) => res.json())
                    .then((data) => {
                        if (data.success) updateCompareUI(data.compare_list || []);
                    });
            };
        });
    }

    function updateCompareUI(compareList) {
        document.querySelectorAll(".compare-btn").forEach((btn) => {
            const bikeId = btn.getAttribute("data-bike-id");
            const card = btn.closest(".card");
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

    // ---- 🚨 NEW: Show modal with bike details ----
    // Delegate click event for all current and future .details-btn buttons
    document.body.addEventListener('click', function (e) {
        if (e.target && e.target.classList.contains('details-btn')) {
            const bikeData = e.target.getAttribute('data-bike');
            if (bikeData) {
                const bike = JSON.parse(bikeData);
                showBikeDetailsModal(bike);
            }
        }
    });

    function showBikeDetailsModal(bike) {
        // Fields to exclude from the table (metadata fields, not specifications)
        const excludeFields = ["Firm", "Model", "Image URL", "Product URL", "slug", "id"];
        
        // Fields to show first (important specs)
        const priorityFields = [
            "Year", "Price", "Disc_price", "Frame", "Motor", "Battery", "Fork", "Rear Shox",
            "Stem", "Handelbar", "Brakes", "Front Brake", "Rear Brake", "Shifter", "Rear Der", "Cassette", "Chain",
            "Crank Set", "Front Wheel", "Rear Wheel", "Rims", "Front Axle", "Rear Axle", "Spokes", "Tubes", "Tires",
            "Front Tire", "Rear Tire", "Saddle", "Seat Post", "Clamp", "Charger", "Wheel Size", "Headset",
            "Brake Lever", "Screen", "Extras", "Pedals", "B.B", "מספר הילוכים:", "Weight", "Size", "Hub"
        ];

        let html = `
        <div class="row">
            <div class="col-md-5 text-center mb-3 mb-md-0">
                <img src="${bike['Image URL'] || ''}" alt="${bike['Model'] || ''}" class="img-fluid rounded" style="max-height:300px;">
            </div>
            <div class="col-md-7">
                <h4 class="fw-bold">${bike['Firm'] || '' }</h4>
                <h6>${bike['Model'] || ''}</h6>
                <div class="table-responsive">
                    <table class="table table-bordered table-sm align-middle">
                        <tbody>
    `;

        // First, show priority fields in order
        priorityFields.forEach(key => {
            if (bike[key] && String(bike[key]).trim() !== "" && !excludeFields.includes(key)) {
                let displayKey = key;
                let displayValue = bike[key];
                
                // Special handling for Disc_price
                if (key === "Disc_price") {
                    displayKey = "Discount";
                    displayValue = `<span style="color: red; font-weight: bold;">₪${bike[key]}</span>`;
                }
                // Special handling for Price - show in red if there's a discount
                else if (key === "Price" && bike["Disc_price"] && bike["Disc_price"].trim() !== "") {
                    displayValue = `<span style="text-decoration: line-through; color: #888;">₪${bike[key]}</span>`;
                }
                // Regular price formatting
                else if (key === "Price") {
                    displayValue = `₪${bike[key]}`;
                }
                
                html += `<tr><th style="width:40%;">${displayKey}</th><td>${displayValue}</td></tr>`;
            }
        });

        // Then show all remaining fields that have values
        Object.keys(bike).forEach(key => {
            if (
                !priorityFields.includes(key) && 
                !excludeFields.includes(key) &&
                bike[key] && 
                String(bike[key]).trim() !== ""
            ) {
                html += `<tr><th style="width:40%;">${key}</th><td>${bike[key]}</td></tr>`;
            }
        });

        html += `
                        </tbody>
                    </table>
                </div>
                <div class="mt-3">
                    ${bike['Product URL'] ? `<a href="${bike['Product URL']}" class="btn btn-info" target="_blank">לרכישה</a>` : ''}
                </div>
            </div>
        </div>
    `;

        document.getElementById('bike-details-content').innerHTML = html;
        const modal = new bootstrap.Modal(document.getElementById('bikeDetailsModal'));
        modal.show();
    }

    document.getElementById("apply-offcanvas-filters").addEventListener("click", () => {
        bootstrap.Offcanvas.getOrCreateInstance(document.getElementById("offcanvasFilters")).hide();
        applyFilters();
    });

    document.getElementById("reset-filters").addEventListener("click", () => {
        priceSlider.noUiSlider.set([0, 100000]);
        batterySlider.noUiSlider.set([200, 1000]);
        searchInput.value = "";
        sortDropdown.value = "none";

        // Reset year checkboxes
        document.querySelectorAll('input[name="year"]').forEach((cb) => {
            cb.checked = false;
        });

        // Reset frame material radios
        document.querySelectorAll('input[name="frame_material"]').forEach((cb) => {
            cb.checked = false;
        });

        // Reset firm checkboxes
        document.querySelectorAll('.firm-checkbox').forEach(cb => {
            cb.checked = false;
        });
        updateFirmDropdownText();

        // Reset motor brand checkboxes
        document.querySelectorAll('.motor-brand-checkbox').forEach(cb => {
            cb.checked = false;
        });
        updateMotorBrandDropdownText();

        fetch("/clear_compare", { method: "POST" }).then(() => {
            updateCompareUI([]);
            applyFilters();
        });
    });

    sortDropdown.addEventListener("change", applyFilters);
    searchInput.addEventListener("input", applyFilters);
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

    fetch("/api/compare_list")
        .then((res) => res.json())
        .then((data) => updateCompareUI(data.compare_list || []));

    applyFilters();  // initial load

    // Add event delegation for .bike-card clicks
    document.getElementById('bikes-list').addEventListener('click', function(e) {
        const card = e.target.closest('.bike-card');
        if (!card) return;
        // Prevent click if compare or details button is clicked
        if (e.target.closest('.compare-btn') || e.target.closest('.details-btn')) return;
        const bike = JSON.parse(card.getAttribute('data-bike'));
        showBikeDetailsModal(bike);
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
