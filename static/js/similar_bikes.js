// Similar bikes carousel functionality
// This file handles fetching and displaying similar bikes in a Splide carousel

document.addEventListener('DOMContentLoaded', function() {
    // Get bike_id from the page (from the similar-bikes-section data attribute)
    const bikeIdElement = document.getElementById('similar-bikes-section');
    if (!bikeIdElement) {
        console.warn('Similar bikes section not found, cannot load similar bikes');
        return;
    }
    
    const bikeId = bikeIdElement.getAttribute('data-bike-id');
    if (!bikeId) {
        console.warn('Bike ID not found, cannot load similar bikes');
        return;
    }
    
    // Fetch similar bikes
    console.log('Fetching similar bikes for bike_id:', bikeId);
    fetch(`/similar_bikes/${bikeId}`)
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                return response.json().then(err => {
                    console.error('API error:', err);
                    throw new Error(err.error || 'Failed to fetch similar bikes');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Similar bikes data:', data);
            const similarBikes = data.similar_bikes || [];
            console.log('Number of similar bikes:', similarBikes.length);
            if (similarBikes.length === 0) {
                // Hide the carousel section if no similar bikes
                console.log('No similar bikes found, hiding section');
                const carouselSection = document.getElementById('similar-bikes-section');
                if (carouselSection) {
                    carouselSection.style.display = 'none';
                }
                return;
            }
            
            // Render the carousel with similar bikes
            renderSimilarBikesCarousel(similarBikes);
        })
        .catch(error => {
            console.error('Error loading similar bikes:', error);
            // Don't hide the section on error - show error message instead
            const carouselContainer = document.getElementById('similar-bikes-carousel');
            if (carouselContainer) {
                carouselContainer.innerHTML = '<p>שגיאה בטעינת אופניים דומים. אנא נסה שוב מאוחר יותר.</p>';
            }
        });
});

function renderSimilarBikesCarousel(bikes) {
    const carouselContainer = document.getElementById('similar-bikes-carousel');
    if (!carouselContainer) {
        console.error('Carousel container not found');
        return;
    }
    
    // Build HTML for the carousel
    let carouselHTML = `
        <div class="splide" id="similar-bikes-splide">
            <div class="splide__track">
                <ul class="splide__list">
    `;
    
    bikes.forEach(bike => {
        const bikeId = bike.id || bike.uuid || '';
        const imageUrl = bike.image_url || '/static/images/placeholder.png';
        const brand = bike.firm || bike.brand || '';
        const model = bike.model || '';
        const year = bike.year || '';
        const price = bike.price || '';
        const discPrice = bike.disc_price || '';
        const productUrl = bike.product_url || '#';
        
        // Format price display
        let priceHTML = '';
        if (discPrice && discPrice !== 'None' && discPrice !== '') {
            const formattedDiscPrice = formatPrice(discPrice);
            const formattedOriginalPrice = formatPrice(price);
            priceHTML = `
                <p class="price-discounted">₪${formattedDiscPrice}</p>
                ${price && price !== 'None' && price !== '' ? `<p class="price-original">₪${formattedOriginalPrice}</p>` : ''}
            `;
        } else if (price && price !== 'None' && price !== '') {
            const formattedPrice = formatPrice(price);
            if (formattedPrice === 'צור קשר') {
                priceHTML = `<p class="price">${formattedPrice}</p>`;
            } else {
                priceHTML = `<p class="price">₪${formattedPrice}</p>`;
            }
        } else {
            priceHTML = '<p class="price">צור קשר</p>';
        }
        
        carouselHTML += `
            <li class="splide__slide">
                <div class="bike-card-splide">
                    <div class="card-img-container">
                        <a href="/bikes/bike/${bikeId}">
                            <img src="${imageUrl}" class="card-img-top" alt="${brand} ${model}" loading="lazy" referrerpolicy="no-referrer">
                        </a>
                    </div>
                    <div class="w3-container bike-card" style="display: flex; flex-direction: column; align-items: center;">
                        <h5 class="card-firm"><b>${brand}</b></h5>
                        <p class="model-text">${model}${year ? ' ' + year : ''}</p>
                        <div class="price-container">
                            ${priceHTML}
                        </div>
                        <div class="bike-card-buttons">
                            <a href="/bikes/bike/${bikeId}" class="btn btn-primary mb-3">פרטים</a>
                        </div>
                    </div>
                </div>
            </li>
        `;
    });
    
    carouselHTML += `
                </ul>
            </div>
        </div>
    `;
    
    carouselContainer.innerHTML = carouselHTML;
    
    // Initialize Splide carousel
    // Configuration matches user's specification:
    // type: 'loop', drag: 'free', focus: 'center', perPage: 3, autoScroll: { speed: 1 }
    const splideElement = document.querySelector('#similar-bikes-splide');
    if (!splideElement) {
        console.error('Splide element #similar-bikes-splide not found');
        return;
    }
    
    if (typeof Splide === 'undefined') {
        console.error('Splide library not found. Make sure Splide is loaded before this script.');
        return;
    }
    
    const splideConfig = {
        type: 'loop',
        drag: 'free',
        focus: 'center',
        perPage: 3,
        gap: '20px',
        padding: { left: '40px', right: '40px' },
        breakpoints: {
            1024: {
                perPage: 2,
            },
            768: {
                perPage: 1,
            },
        },
        direction: 'rtl', // RTL for Hebrew
    };
    
    // Add AutoScroll if available
    // Note: AutoScroll extension needs to be loaded separately
    // For ES modules: import { AutoScroll } from '@splidejs/splide-extension-auto-scroll';
    // For CDN: Load the extension script before this file, then it will be available
    try {
        if (typeof window !== 'undefined' && window.AutoScroll) {
            splideConfig.autoScroll = {
                speed: 1,
            };
            const splide = new Splide('#similar-bikes-splide', splideConfig);
            splide.mount({ AutoScroll: window.AutoScroll });
            console.log('Splide carousel initialized with AutoScroll');
        } else {
            // Initialize without AutoScroll (carousel will still work)
            const splide = new Splide('#similar-bikes-splide', splideConfig);
            splide.mount();
            console.log('Splide carousel initialized without AutoScroll');
        }
    } catch (error) {
        console.error('Error initializing Splide carousel:', error);
    }
}

function formatPrice(price) {
    if (!price || price === 'None' || price === '') {
        return 'צור קשר';
    }
    
    // Check if it's already the Hebrew text
    if (price === 'צור קשר') {
        return price;
    }
    
    try {
        // Remove non-digit characters except decimal point
        const cleanPrice = price.toString().replace(/[^\d.]/g, '');
        const numPrice = parseFloat(cleanPrice);
        if (isNaN(numPrice)) {
            return 'צור קשר';
        }
        // Format with commas
        return numPrice.toLocaleString('he-IL');
    } catch (e) {
        return 'צור קשר';
    }
}

