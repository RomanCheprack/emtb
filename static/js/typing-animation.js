// Typing Animation Component - Magic UI inspired
class TypingAnimation {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            duration: 100, // Duration between each character
            delay: 0, // Delay before animation starts
            startOnView: false,
            onComplete: null, // Callback when animation completes
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
        
        // Make element visible and clear text immediately to prevent flash
        this.element.classList.add('animation-ready');
        this.element.textContent = '';
        
        let index = 0;
        
        const typeNextChar = () => {
            if (index < text.length) {
                this.element.textContent += text[index];
                index++;
                setTimeout(typeNextChar, this.options.duration);
            } else {
                // Animation complete, call callback if provided
                if (this.options.onComplete && typeof this.options.onComplete === 'function') {
                    this.options.onComplete();
                }
            }
        };
        
        // Start typing after delay
        setTimeout(typeNextChar, this.options.delay);
    }
}

// Initialize typing animations when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const heroH1 = document.querySelector('.hero-body h1[data-typing-animation]');
    const heroSpan = document.querySelector('.hero-body span[data-text-animate]');
    const heroButton = document.querySelector('.hero-body .cta-button-primary');
    
    // Immediately prepare the span to prevent flash of content
    if (heroSpan) {
        prepareSpanForAnimation(heroSpan);
    }
    
    // Initialize H1 typing animation
    if (heroH1) {
        const duration = parseInt(heroH1.getAttribute('data-typing-duration')) || 100;
        const delay = parseInt(heroH1.getAttribute('data-typing-delay')) || 0;
        const startOnView = heroH1.getAttribute('data-typing-start-on-view') === 'true';
        
        new TypingAnimation(heroH1, {
            duration,
            delay,
            startOnView,
            onComplete: () => {
                // When H1 typing completes, start span animation
                if (heroSpan) {
                    startSpanAnimation(heroSpan, () => {
                        // When span animation completes, show button
                        if (heroButton) {
                            heroButton.style.opacity = '1';
                            heroButton.style.transform = 'translateY(0)';
                            heroButton.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                        }
                    });
                }
            }
        });
    }
    
    // Handle other typing animations (if any)
    const otherTypingElements = document.querySelectorAll('[data-typing-animation]:not(.hero-body h1)');
    otherTypingElements.forEach(element => {
        const duration = parseInt(element.getAttribute('data-typing-duration')) || 100;
        const delay = parseInt(element.getAttribute('data-typing-delay')) || 0;
        const startOnView = element.getAttribute('data-typing-start-on-view') === 'true';
        
        new TypingAnimation(element, {
            duration,
            delay,
            startOnView
        });
    });
    
    // Show button after all animations complete (for non-hero animations)
    showButtonAfterAnimations();
});

// Function to prepare span for animation (hide content immediately)
function prepareSpanForAnimation(spanElement) {
    const animationType = spanElement.getAttribute('data-text-animate') || 'blurInUp';
    const by = spanElement.getAttribute('data-text-animate-by') || 'word';
    
    if (by === 'word' && animationType === 'blurInUp') {
        // Split text into words immediately to prevent flash of content
        const text = spanElement.textContent.trim();
        const words = text.split(/\s+/);
        const isRTL = spanElement.getAttribute('dir') === 'ltr';
        const duration = parseFloat(spanElement.getAttribute('data-text-animate-duration')) || 0.4;
        
        // Clear the element and prepare words (but keep hidden)
        spanElement.innerHTML = '';
        
        // Create word spans with initial hidden state
        words.forEach((word, index) => {
            const wordSpan = document.createElement('span');
            wordSpan.textContent = word;
            wordSpan.style.display = 'inline-block';
            wordSpan.style.opacity = '0';
            wordSpan.style.filter = 'blur(10px)';
            wordSpan.style.transform = 'translateY(20px)';
            wordSpan.style.transition = `opacity ${duration}s ease, transform ${duration}s ease, filter ${duration}s ease`;
            
            if (isRTL) {
                wordSpan.style.marginLeft = '0.2em';
            } else {
                wordSpan.style.marginRight = '0.2em';
            }
            
            spanElement.appendChild(wordSpan);
        });
        
        // Mark as prepared but don't show yet
        spanElement.setAttribute('data-animation-prepared', 'true');
    }
}

// Function to start span blurInUp animation
function startSpanAnimation(spanElement, onComplete) {
    const animationType = spanElement.getAttribute('data-text-animate') || 'blurInUp';
    const by = spanElement.getAttribute('data-text-animate-by') || 'word';
    const duration = parseFloat(spanElement.getAttribute('data-text-animate-duration')) || 0.4;
    const delay = parseFloat(spanElement.getAttribute('data-text-animate-delay')) || 0;
    
    // If not prepared yet, prepare it now
    if (!spanElement.hasAttribute('data-animation-prepared')) {
        prepareSpanForAnimation(spanElement);
    }
    
    if (by === 'word' && animationType === 'blurInUp') {
        const words = spanElement.querySelectorAll('span');
        
        // Now make the container visible and start animation
        spanElement.classList.add('animation-ready');
        
        // Use requestAnimationFrame to ensure the hidden state is applied before animation
        requestAnimationFrame(() => {
            // Animate each word with stagger
            words.forEach((wordSpan, index) => {
                const wordDelay = delay + (index * 0.08); // 80ms between words for faster sequence
                
                setTimeout(() => {
                    wordSpan.style.opacity = '1';
                    wordSpan.style.filter = 'blur(0)';
                    wordSpan.style.transform = 'translateY(0)';
                    
                    // Call onComplete when last word finishes animating
                    if (index === words.length - 1) {
                        setTimeout(() => {
                            if (onComplete && typeof onComplete === 'function') {
                                onComplete();
                            }
                        }, duration * 1000);
                    }
                }, wordDelay * 1000);
            });
        });
    }
}

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