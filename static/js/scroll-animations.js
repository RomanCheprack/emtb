// Scroll Animation Script for Vision Cards
document.addEventListener('DOMContentLoaded', function() {
    const observerOptions = {
        threshold: 0.3,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const card = entry.target;
                const animation = card.getAttribute('data-animation');
                
                // Remove existing animation classes
                card.classList.remove('slide-right', 'slide-left', 'slide-up');
                
                // Add the appropriate animation class
                if (animation) {
                    card.classList.add(animation);
                }
                
                // Stop observing after animation is triggered
                observer.unobserve(card);
            }
        });
    }, observerOptions);

    // Observe all vision cards
    const visionCards = document.querySelectorAll('.vision-card[data-animation]');
    visionCards.forEach(card => {
        observer.observe(card);
    });
});
