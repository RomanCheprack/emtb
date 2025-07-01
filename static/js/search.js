document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');

    if (!searchInput) return;

    searchInput.addEventListener('input', function () {
        const query = searchInput.value.trim();

        fetch(`/api/search_bikes?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(bikes => {
                const bikesList = document.getElementById('bikes-list');
                const bikesCount = document.getElementById('bikes-count');
                bikesList.innerHTML = '';

                if (bikes.length === 0) {
                    bikesList.innerHTML = '<div class="col-12"><p>לא נמצאו תוצאות.</p></div>';
                    bikesCount.textContent = `נמצאו 0 אופניים`;
                    return;
                }

                bikesCount.textContent = `נמצאו ${bikes.length} אופניים`;

                bikes.forEach(bike => {
                    bikesList.innerHTML += `
                        <div class="col-6 col-lg-2 mb-2 px-1">
                          <div class="card h-100 position-relative">
                            <div class="position-absolute top-0 end-0 p-2">
                              <button class="btn btn-outline-warning compare-btn" data-bike-id="${bike['id']}">השווה</button>
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
                });
            });
    });
});
