// Shared Comparison Page JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // Initialize any shared comparison page functionality
    console.log('Shared comparison page loaded');
});

// Function to copy share URL to clipboard
function copyShareUrl() {
    const shareUrl = document.getElementById('shareUrl');
    if (!shareUrl) return;
    
    shareUrl.select();
    shareUrl.setSelectionRange(0, 99999); // For mobile devices
    
    navigator.clipboard.writeText(shareUrl.value).then(function() {
        // Show success message
        const button = event.target.closest('button');
        if (!button) return;
        
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> הועתק!';
        button.classList.remove('btn-primary');
        button.classList.add('btn-success');
        
        setTimeout(function() {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
            button.classList.add('btn-primary');
        }, 2000);
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
        // Fallback for older browsers
        document.execCommand('copy');
        
        // Show success message even for fallback
        const button = event.target.closest('button');
        if (button) {
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check"></i> הועתק!';
            button.classList.remove('btn-primary');
            button.classList.add('btn-success');
            
            setTimeout(function() {
                button.innerHTML = originalText;
                button.classList.remove('btn-success');
                button.classList.add('btn-primary');
            }, 2000);
        }
    });
}

// Function to share on social media
function shareOnSocial(platform) {
    const shareUrl = document.getElementById('shareUrl').value;
    const title = document.title;
    const description = document.querySelector('meta[name="description"]')?.content || '';
    
    let shareLink = '';
    
    switch(platform) {
        case 'facebook':
            shareLink = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
            break;
        case 'twitter':
            shareLink = `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(title)}`;
            break;
        case 'whatsapp':
            shareLink = `https://wa.me/?text=${encodeURIComponent(title + ' ' + shareUrl)}`;
            break;
        case 'telegram':
            shareLink = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(title)}`;
            break;
        default:
            return;
    }
    
    // Open in new window
    window.open(shareLink, '_blank', 'width=600,height=400');
}

// Function to print the comparison
function printComparison() {
    window.print();
}

// Function to download as PDF (placeholder for future implementation)
function downloadAsPDF() {
    alert('פונקציונליות הורדת PDF תתווסף בקרוב');
}

// Add smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading animation for images
document.querySelectorAll('img').forEach(img => {
    img.addEventListener('load', function() {
        this.classList.add('loaded');
    });
    
    img.addEventListener('error', function() {
        this.style.display = 'none';
        console.log('Image failed to load:', this.src);
    });
});

// Add tooltip functionality for bike specs
document.querySelectorAll('[data-toggle="tooltip"]').forEach(element => {
    element.addEventListener('mouseenter', function() {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = this.getAttribute('title');
        tooltip.style.cssText = `
            position: absolute;
            background: #333;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 1000;
            pointer-events: none;
        `;
        
        document.body.appendChild(tooltip);
        
        const rect = this.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
        
        this._tooltip = tooltip;
    });
    
    element.addEventListener('mouseleave', function() {
        if (this._tooltip) {
            document.body.removeChild(this._tooltip);
            this._tooltip = null;
        }
    });
}); 