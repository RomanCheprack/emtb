// Splide carousel initialization for popular bikes section
document.addEventListener('DOMContentLoaded', function() {
    const splideElement = document.querySelector('#popular-bikes-splide');
    
    if (splideElement) {
        var splide = new Splide('#popular-bikes-splide', {
            type: 'loop',
            perPage: 3,
            perMove: 1,
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
            // RTL support for Hebrew
            direction: 'rtl',
        });
        
        splide.mount();
    }
});
