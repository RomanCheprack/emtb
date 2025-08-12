// Text Animate - Fade In by Line Animation
class TextAnimate {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            animation: 'fadeIn',
            by: 'line',
            delay: 300,
            startOnView: true,
            once: true,
            ...options
        };
        
        this.hasAnimated = false;
        this.init();
    }
    
    init() {
        if (this.options.startOnView) {
            this.observeElement();
        } else {
            this.animate();
        }
    }
    
    observeElement() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !this.hasAnimated) {
                    this.animate();
                    this.hasAnimated = true;
                    if (this.options.once) {
                        observer.unobserve(this.element);
                    }
                }
            });
        }, { 
            threshold: 0.3,
            rootMargin: '-50px'
        });
        
        observer.observe(this.element);
    }
    
    animate() {
        if (this.options.by === 'line') {
            this.splitIntoLines();
        }
    }
    
    splitIntoLines() {
        const text = this.element.innerHTML;
        const lines = text.split('<br>');
        
        // Clear the element
        this.element.innerHTML = '';
        
        // Add the fade-in-by-line class
        this.element.classList.add('fade-in-by-line');
        
        // Create line elements
        lines.forEach((line, index) => {
            if (line.trim()) {
                const lineElement = document.createElement('div');
                lineElement.className = 'line';
                lineElement.innerHTML = line.trim();
                this.element.appendChild(lineElement);
            }
        });
    }
}

// Initialize text animation when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Hero section sequential animation
    const heroH1 = document.querySelector('.hero-body h1');
    const heroSpan = document.querySelector('.hero-body span');
    const heroButton = document.querySelector('.hero-body .cta-button-primary');
    
    // Animate H1 first
    if (heroH1) {
        setTimeout(() => {
            heroH1.style.opacity = '1';
            heroH1.style.transform = 'translateY(0)';
        }, 500);
    }
    
    // Animate span second
    if (heroSpan) {
        setTimeout(() => {
            heroSpan.style.opacity = '1';
            heroSpan.style.transform = 'translateY(0)';
        }, 1500);
    }
    
    // Animate button last
    if (heroButton) {
        setTimeout(() => {
            heroButton.style.opacity = '1';
            heroButton.style.transform = 'translateY(0)';
        }, 2500);
    }
    
    // Vision description animation
    const visionDescription = document.querySelector('.vision-description');
    if (visionDescription) {
        new TextAnimate(visionDescription, {
            animation: 'fadeIn',
            by: 'line',
            startOnView: true,
            once: true
        });
    }
    
    // Vision title animation
    const visionTitle = document.querySelector('.vision-title');
    if (visionTitle) {
        new TextAnimate(visionTitle, {
            animation: 'fadeIn',
            by: 'line',
            startOnView: true,
            once: true
        });
    }
});
