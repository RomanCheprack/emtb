// Vision Section JavaScript
class VisionSection {
    constructor() {
        this.init();
    }

    init() {
        this.setupStatCounters();
        this.setupCardInteractions();
    }

    setupStatCounters() {
        const statElements = document.querySelectorAll('.stat-number');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        statElements.forEach(element => {
            observer.observe(element);
        });
    }

    animateCounter(element) {
        const text = element.textContent;
        const suffix = text.replace(/\d/g, '');
        const endValue = parseInt(text.replace(/\D/g, ''));
        const duration = 2000; // 2 seconds
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = Math.floor(easeOutQuart * endValue);
            
            element.textContent = currentValue + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }





    setupCardInteractions() {
        const cards = document.querySelectorAll('.vision-card');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                this.animateCardHover(card, true);
            });

            card.addEventListener('mouseleave', () => {
                this.animateCardHover(card, false);
            });
        });
    }

    animateCardHover(card, isHovered) {
        const icon = card.querySelector('.vision-card-icon');
        const title = card.querySelector('.vision-card-title');
        const link = card.querySelector('.vision-card-link');

        if (isHovered) {
            // Animate icon
            if (icon) {
                icon.style.transform = 'scale(1.1) rotate(5deg)';
            }
            
            // Animate title color
            if (title) {
                title.style.color = '#dc2626';
            }
            
            // Animate link
            if (link) {
                link.style.transform = 'translateX(-10px)';
            }
        } else {
            // Reset animations
            if (icon) {
                icon.style.transform = 'scale(1) rotate(0deg)';
            }
            
            if (title) {
                title.style.color = '#1f2937';
            }
            
            if (link) {
                link.style.transform = 'translateX(0)';
            }
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new VisionSection();
});

// Smooth scroll for anchor links
document.addEventListener('DOMContentLoaded', () => {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});
