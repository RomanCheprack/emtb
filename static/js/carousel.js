// Carousel functionality for popular bikes section
let currentSlide = 0;
let totalSlides = 0;
let slidesPerView = 3; // Number of slides visible at once

// Initialize carousel when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCarousel();
    
    // Update slides per view based on screen size
    window.addEventListener('resize', function() {
        updateSlidesPerView();
        updateCarousel();
    });
    
    // Add keyboard navigation
    document.addEventListener('keydown', function(e) {
        const carouselContainer = document.querySelector('.carousel-container');
        if (carouselContainer && document.activeElement.closest('.carousel-container')) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                moveCarousel(-1);
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                moveCarousel(1);
            }
        }
    });
});

// Also initialize when window is fully loaded to ensure proper positioning
window.addEventListener('load', function() {
    setTimeout(() => {
        updateCarousel();
        
        // Also recalculate when images load
        const images = document.querySelectorAll('.carousel-item img');
        images.forEach(img => {
            if (img.complete) {
                updateCarousel();
            } else {
                img.addEventListener('load', updateCarousel);
            }
        });
    }, 200);
});

function initializeCarousel() {
    const track = document.querySelector('.carousel-track');
    const dots = document.querySelectorAll('.carousel-dot');
    
    if (!track || dots.length === 0) {
        console.warn('Carousel elements not found');
        return;
    }
    
    totalSlides = dots.length;
    currentSlide = 0; // Reset to first slide
    updateSlidesPerView();
    
    // Add click event listeners to dots
    dots.forEach((dot, index) => {
        dot.addEventListener('click', () => goToSlide(index));
    });
    
    // Wait a bit for styles to be applied before updating
    setTimeout(() => {
        updateCarousel();
        updateDots();
    }, 50);
}

function updateSlidesPerView() {
    if (window.innerWidth <= 768) {
        slidesPerView = 1;
    } else if (window.innerWidth <= 1024) {
        slidesPerView = 2;
    } else {
        slidesPerView = 3;
    }
    
    // Reset current slide if it's now beyond the maximum
    const maxSlide = Math.max(0, totalSlides - slidesPerView);
    if (currentSlide > maxSlide) {
        currentSlide = maxSlide;
    }
}

function moveCarousel(direction) {
    const maxSlide = Math.max(0, totalSlides - slidesPerView);
    
    if (direction === 1) {
        // Move right
        currentSlide = Math.min(currentSlide + 1, maxSlide);
    } else {
        // Move left
        currentSlide = Math.max(currentSlide - 1, 0);
    }
    
    updateCarousel();
    updateDots();
}

function goToSlide(slideIndex) {
    currentSlide = slideIndex;
    updateCarousel();
    updateDots();
}

function updateCarousel() {
    const track = document.querySelector('.carousel-track');
    if (!track) return;
    
    const container = document.querySelector('.carousel-container');
    const containerWidth = container.offsetWidth;
    
    // Get the actual carousel items to calculate their real width
    const items = track.querySelectorAll('.carousel-item');
    if (items.length === 0) return;
    
    // Get the computed width of the first item (including margins)
    const firstItem = items[0];
    const itemStyle = window.getComputedStyle(firstItem);
    const itemWidth = firstItem.offsetWidth;
    const itemMarginLeft = parseFloat(itemStyle.marginLeft);
    const itemMarginRight = parseFloat(itemStyle.marginRight);
    const totalItemWidth = itemWidth + itemMarginLeft + itemMarginRight;
    
    // Calculate translation based on actual item width
    const translateX = -(currentSlide * totalItemWidth);
    track.style.transform = `translateX(${translateX}px)`;
    
    // Debug logging
    console.log('Carousel Debug:', {
        currentSlide,
        itemWidth,
        itemMarginLeft,
        itemMarginRight,
        totalItemWidth,
        translateX,
        containerWidth
    });
    
    // Update button states
    updateButtonStates();
}

function updateButtonStates() {
    const prevButton = document.querySelector('.carousel-button-prev');
    const nextButton = document.querySelector('.carousel-button-next');
    
    if (prevButton) {
        prevButton.style.opacity = currentSlide === 0 ? '0.5' : '1';
        prevButton.style.pointerEvents = currentSlide === 0 ? 'none' : 'auto';
    }
    
    if (nextButton) {
        const maxSlide = Math.max(0, totalSlides - slidesPerView);
        nextButton.style.opacity = currentSlide >= maxSlide ? '0.5' : '1';
        nextButton.style.pointerEvents = currentSlide >= maxSlide ? 'none' : 'auto';
    }
}

function updateDots() {
    const dots = document.querySelectorAll('.carousel-dot');
    dots.forEach((dot, index) => {
        if (index === currentSlide) {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    });
}

// Auto-play functionality (optional)
let autoPlayInterval;

function startAutoPlay() {
    autoPlayInterval = setInterval(() => {
        const maxSlide = Math.max(0, totalSlides - slidesPerView);
        if (currentSlide >= maxSlide) {
            currentSlide = 0;
        } else {
            currentSlide++;
        }
        updateCarousel();
        updateDots();
    }, 5000); // Change slide every 5 seconds
}

function stopAutoPlay() {
    if (autoPlayInterval) {
        clearInterval(autoPlayInterval);
    }
}

// Pause auto-play on hover
document.addEventListener('DOMContentLoaded', function() {
    const carouselContainer = document.querySelector('.carousel-container');
    if (carouselContainer) {
        carouselContainer.addEventListener('mouseenter', stopAutoPlay);
        carouselContainer.addEventListener('mouseleave', startAutoPlay);
        
        // Start auto-play after a delay
        setTimeout(startAutoPlay, 2000);
        
        // Add touch/swipe support for mobile
        addTouchSupport(carouselContainer);
    }
});

// Touch/swipe support for mobile devices
function addTouchSupport(container) {
    let startX = 0;
    let endX = 0;
    let isDragging = false;
    
    container.addEventListener('touchstart', function(e) {
        startX = e.touches[0].clientX;
        isDragging = true;
        stopAutoPlay();
    });
    
    container.addEventListener('touchmove', function(e) {
        if (!isDragging) return;
        e.preventDefault();
    });
    
    container.addEventListener('touchend', function(e) {
        if (!isDragging) return;
        
        endX = e.changedTouches[0].clientX;
        const diffX = startX - endX;
        const threshold = 50; // Minimum swipe distance
        
        if (Math.abs(diffX) > threshold) {
            if (diffX > 0) {
                // Swipe left - go to next slide
                moveCarousel(1);
            } else {
                // Swipe right - go to previous slide
                moveCarousel(-1);
            }
        }
        
        isDragging = false;
        setTimeout(startAutoPlay, 1000);
    });
}
