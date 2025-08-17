// Typing Animation Component - Magic UI inspired
class TypingAnimation {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            duration: 100, // Duration between each character
            delay: 0, // Delay before animation starts
            startOnView: false,
            ...options
        };
        
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
                if (entry.isIntersecting) {
                    this.animate();
                }
            });
        }, { threshold: 0.1 });
        
        observer.observe(this.element);
    }
    
    animate() {
        const text = this.element.textContent;
        this.element.textContent = '';
        
        let index = 0;
        
        const typeNextChar = () => {
            if (index < text.length) {
                this.element.textContent += text[index];
                index++;
                setTimeout(typeNextChar, this.options.duration);
            }
        };
        
        // Start typing after delay
        setTimeout(typeNextChar, this.options.delay);
    }
}

// Initialize typing animations when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const typingElements = document.querySelectorAll('[data-typing-animation]');
    
    typingElements.forEach(element => {
        const duration = parseInt(element.getAttribute('data-typing-duration')) || 100;
        const delay = parseInt(element.getAttribute('data-typing-delay')) || 0;
        const startOnView = element.getAttribute('data-typing-start-on-view') === 'true';
        
        new TypingAnimation(element, {
            duration,
            delay,
            startOnView
        });
    });
    
    // Show button after all animations complete
    showButtonAfterAnimations();
});

// Function to show button after all text animations are complete
function showButtonAfterAnimations() {
    const compareButton = document.getElementById('compare-button');
    if (!compareButton) return;
    
    // Calculate total animation time
    const typingDuration = 200; // ms per character
    const typingDelay = 250; // ms delay
    const typingText = "Rideal";
    const typingTotalTime = typingDelay + (typingText.length * typingDuration);
    
    const textAnimateDelay = 600; // ms delay
    const textAnimateDuration = 700; // ms duration
    const textAnimateStagger = 200; // ms between words
    const hebrewWords = "רכישת אופניים חכמה".split(' ').length;
    const textAnimateTotalTime = textAnimateDelay + textAnimateDuration + (hebrewWords * textAnimateStagger);
    
    // Use the longer of the two animations plus some buffer
    const totalAnimationTime = Math.max(typingTotalTime, textAnimateTotalTime) + 400; // 300ms buffer
    
    // Show button after animations complete
    setTimeout(() => {
        compareButton.style.opacity = '1';
    }, totalAnimationTime);
}
