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
    // Hero section animations are handled by typing-animation.js
    // This file only handles vision section animations
    
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
