
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('sort-price').addEventListener('change', function () {
        document.getElementById('filter-form').dispatchEvent(new Event('submit'));
    });

    function parsePrice(price) {
        if (!price) return 0;
        return parseInt(String(price).replace(/[^\d]/g, ''), 10) || 0;
    }
    function sortBikesByPrice(bikes, order) {
        if (order === 'asc') {
            return bikes.sort((a, b) => parsePrice(a.Price) - parsePrice(b.Price));
        } else if (order === 'desc') {
            return bikes.sort((a, b) => parsePrice(b.Price) - parsePrice(a.Price));
        }
        return bikes;
    }
    function updateCompareUI(compareList) {
        document.querySelectorAll('.compare-btn').forEach(btn => {
            const bikeId = btn.getAttribute('data-bike-id');
            const card = btn.closest('.card');
            if (compareList.includes(bikeId)) {
                btn.classList.add('selected');
                btn.textContent = 'הסר השוואה';
                card.classList.add('compare-selected');
            } else {
                btn.classList.remove('selected');
                btn.textContent = 'השווה';
                card.classList.remove('compare-selected');
            }
        });
        // Show or hide the compare button
        const compareBtn = document.getElementById('go-to-compare');
        const compareCount = document.getElementById('compare-count');
        if (compareBtn) {
            if (compareList.length > 0) {
                compareBtn.style.display = 'inline-block';
                if (compareCount) {
                    compareCount.textContent = `(${compareList.length})`;
                }
            } else {
                compareBtn.style.display = 'none';
            }
        }
    }

    function attachCompareButtonListeners() {
        document.querySelectorAll('.compare-btn').forEach(btn => {
            btn.onclick = function () {
                const bikeId = btn.getAttribute('data-bike-id');
                const isSelected = btn.classList.contains('selected');
                const url = isSelected ? `/remove_from_compare/${bikeId}` : `/add_to_compare/${bikeId}`;
                fetch(url, { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            // Get the latest compare list and update the UI
                            fetch('/api/compare_list')
                                .then(res => res.json())
                                .then(compareData => {
                                    const compareList = compareData.compare_list || [];
                                    updateCompareUI(compareList);
                                    attachCompareButtonListeners(); // re-attach after UI update
                                });
                        } else if (data.error) {
                            alert(data.error);
                        }
                    });
            };
        });
    }

    // --- Price Slider Setup ---
    var priceSlider = document.getElementById('price-slider');
    var minPriceInput = document.getElementById('min_price');
    var maxPriceInput = document.getElementById('max_price');
    var minPriceValue = document.getElementById('min_price_value');
    var maxPriceValue = document.getElementById('max_price_value');

    noUiSlider.create(priceSlider, {
        start: [0, 100000],
        connect: true,
        step: 100,
        range: {
            'min': 0,
            'max': 100000
        },
        format: {
            to: function (value) { return Math.round(value); },
            from: function (value) { return Number(value); }
        }
    });

    priceSlider.noUiSlider.on('update', function (values, handle) {
        minPriceInput.value = values[0];
        maxPriceInput.value = values[1];
        minPriceValue.textContent = values[0];
        maxPriceValue.textContent = values[1];
    });

    // --- Battery Slider Setup ---
    var batterySlider = document.getElementById('battery-slider');
    var minBatteryInput = document.getElementById('min_battery');
    var maxBatteryInput = document.getElementById('max_battery');
    var minBatteryValue = document.getElementById('min_battery_value');
    var maxBatteryValue = document.getElementById('max_battery_value');

    noUiSlider.create(batterySlider, {
        start: [200, 1000],
        connect: true,
        step: 10,
        range: {
            'min': 200,
            'max': 1000
        },
        format: {
            to: function (value) { return Math.round(value); },
            from: function (value) { return Number(value); }
        }
    });

    batterySlider.noUiSlider.on('update', function (values, handle) {
        minBatteryInput.value = values[0];
        maxBatteryInput.value = values[1];
        minBatteryValue.textContent = values[0];
        maxBatteryValue.textContent = values[1];
    });

    // --- AJAX Filter Form Submission ---
    document.getElementById('filter-form').addEventListener('submit', function (e) {
        e.preventDefault();
        const min_price = minPriceInput.value;
        const max_price = maxPriceInput.value;
        const min_battery = minBatteryInput.value;
        const max_battery = maxBatteryInput.value;
        // Collect selected years (checkboxes)
        const yearCheckboxes = document.querySelectorAll('input[name="year"]:checked');
        const years = Array.from(yearCheckboxes).map(cb => cb.value);

        // Collect selected firms (checkboxes)
        const firmCheckboxes = document.querySelectorAll('input[name="firm"]:checked');
        const firms = Array.from(firmCheckboxes).map(cb => cb.value);

        // Build query params
        const params = new URLSearchParams();
        if (min_price) params.append('min_price', min_price);
        if (max_price) params.append('max_price', max_price);
        if (min_battery) params.append('min_battery', min_battery);
        if (max_battery) params.append('max_battery', max_battery);
        years.forEach(y => params.append('year', y));
        firms.forEach(f => params.append('firm', f));

        fetch('/api/filter_bikes?' + params.toString())
            .then(response => response.json())
            .then(data => {
                const sortOrder = document.getElementById('sort-price').value;
                const sortedBikes = sortBikesByPrice(data, sortOrder);

                const bikesList = document.getElementById('bikes-list');
                const bikesCount = document.getElementById('bikes-count');
                bikesCount.textContent = `נמצאו ${sortedBikes.length} אופניים`;
                bikesList.innerHTML = '';
                if (sortedBikes.length === 0) {
                    bikesList.innerHTML = '<div class="col-12"><p>לא נמצאו תוצאות.</p></div>';
                } else {
                    sortedBikes.forEach(bike => {
                        bikesList.innerHTML += `
                            <div class="col-6 mb-4 px-1">
                                <div class="card h-100 position-relative">
                                    <div class="position-absolute top-0 end-0 p-2">
                                        <button class="btn btn-sm btn-outline-warning compare-btn" data-bike-id="${bike['id']}">השווה</button>
                                    </div>
                                    <img src="${bike['Image URL']}" class="card-img-top" alt="${bike['Model']}">
                                    <div class="card-body">
                                        <h4 class="card-firm">${bike['Firm']}</h4>
                                        <p class="card-title">${bike['Model']}</p>
                                        <h6 class="card-text-price">מחיר: ${bike['Price']}</h6>
                                        <p class="card-text-year">שנה: ${bike['Year']}</p>
                                        <div class="details-btn">
                                            <button type="button"
                                                class="btn btn-primary details-btn"
                                                data-bike='${JSON.stringify(bike)}'>
                                                לפרטים
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            `;
                        attachCompareButtonListeners();
                    });
                }
            });
    });
    attachCompareButtonListeners();

    document.getElementById('apply-offcanvas-filters').addEventListener('click', function () {
        // Optionally, close the offcanvas
        var offcanvas = bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('offcanvasFilters'));
        offcanvas.hide();

        // Trigger the filter form submit (or call your AJAX filter function directly)
        document.getElementById('filter-form').dispatchEvent(new Event('submit'));
    });

    // --- Optional: Reset Button Logic ---
    const resetBtn = document.getElementById('reset-filters');
    if (resetBtn) {
        resetBtn.addEventListener('click', function () {
            priceSlider.noUiSlider.set([0, 100000]);
            batterySlider.noUiSlider.set([200, 1000]);
            // Uncheck all year checkboxes
            document.querySelectorAll('input[name="year"]').forEach(cb => cb.checked = false);
            document.querySelectorAll('input[name="firm"]').forEach(cb => cb.checked = false);
            document.getElementById('filter-form').dispatchEvent(new Event('submit'));
            // Clear compare list in session
            fetch('/clear_compare', { method: 'POST' })
                .then(res => res.json())
                .then(() => {
                    // Optionally update UI immediately
                    updateCompareUI([]);
                    // Now trigger the filter form submit
                    document.getElementById('filter-form').dispatchEvent(new Event('submit'));
                });
        });
    }


    // Fetch current compare list on page load
    let compareList = [];
    fetch('/api/compare_list')
        .then(res => res.json())
        .then(data => {
            compareList = data.compare_list || [];
            updateCompareUI(compareList);
        });

    // Handle compare button click
    document.querySelectorAll('.compare-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const bikeId = btn.getAttribute('data-bike-id');
            const isSelected = btn.classList.contains('selected');
            const url = isSelected ? `/remove_from_compare/${bikeId}` : `/add_to_compare/${bikeId}`;
            fetch(url, { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        compareList = data.compare_list;
                        updateCompareUI(compareList);
                    } else if (data.error) {
                        alert(data.error);
                    }
                });
        });
    });
});


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
    const fieldOrder = [
        "Firm", "Model", "Year", "Price", "Frame", "Motor", "Battery", "Fork", "Rear Shox",
        "Stem", "Handelbar", "Front Brake", "Rear Brake", "Shifter", "Rear Der", "Cassette", "Chain",
        "Crank Set", "Front Wheel", "Rear Wheel", "Rims", "Front Axle", "Rear Axle", "Spokes", "Tubes",
        "Front Tire", "Rear Tire", "Saddle", "Seat Post", "Clamp", "Charger", "Wheel Size", "Headset",
        "Brake Lever", "Screen", "Extras", "Pedals", "B.B", "מספר הילוכים:"
    ];

    let html = `
        <div class="row">
            <div class="col-md-5 text-center mb-3 mb-md-0">
                <img src="${bike['Image URL']}" alt="${bike['Model']}" class="img-fluid rounded" style="max-height:300px;">
            </div>
            <div class="col-md-7">
                <h4>${bike['Firm'] || ''}</h4>
                <h6>${bike['Model'] || ''}</h6>
                <div class="table-responsive">
                    <table class="table table-bordered table-sm align-middle">
                        <tbody>
    `;

    // Preferred order
    fieldOrder.forEach(key => {
        if (
            key !== "Firm" && key !== "Model" && key !== "Image URL" && key !== "Product URL" && key !== "slug" &&
            bike[key] && String(bike[key]).trim() !== ""
        ) {
            html += `<tr><th style="width:40%;">${key}</th><td>${bike[key]}</td></tr>`;
        }
    });

    // Any remaining fields
    Object.keys(bike).forEach(key => {
        if (
            !fieldOrder.includes(key) &&
            key !== "Firm" && key !== "Model" && key !== "Image URL" && key !== "Product URL" && key !== "slug" &&
            bike[key] && String(bike[key]).trim() !== ""
        ) {
            html += `<tr><th style="width:40%;">${key}</th><td>${bike[key]}</td></tr>`;
        }
    });

    html += `
                        </tbody>
                    </table>
                </div>
                <div class="mt-3">
                    <a href="${bike['Product URL']}" class="btn btn-info" target="_blank">לרכישה</a>
                </div>
            </div>
        </div>
    `;
    document.getElementById('bike-details-content').innerHTML = html;
    var modal = new bootstrap.Modal(document.getElementById('bikeDetailsModal'));
    modal.show();
}
