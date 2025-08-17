// Cookie Consent Management
class CookieConsent {
    constructor() {
        this.cookieName = 'rideal_cookie_consent';
        this.modal = document.getElementById('cookieConsentModal');
        this.analyticsCheckbox = document.getElementById('analyticsCookies');
        this.preferenceCheckbox = document.getElementById('preferenceCookies');
        
        this.init();
    }
    
    init() {
        // Check if user has already made a choice
        const consent = this.getConsent();
        
        if (!consent) {
            // Show modal on first visit
            this.showModal();
        } else {
            // Apply saved preferences
            this.applyConsent(consent);
        }
        
        // Add event listeners
        this.addEventListeners();
    }
    
    showModal() {
        if (this.modal) {
            this.modal.style.display = 'flex';
            // Prevent body scroll when modal is open
            document.body.style.overflow = 'hidden';
        }
    }
    
    hideModal() {
        if (this.modal) {
            this.modal.style.display = 'none';
            // Restore body scroll
            document.body.style.overflow = 'auto';
        }
    }
    
    addEventListeners() {
        // Accept all cookies
        const acceptAllBtn = document.getElementById('acceptAll');
        if (acceptAllBtn) {
            acceptAllBtn.addEventListener('click', () => {
                this.analyticsCheckbox.checked = true;
                this.preferenceCheckbox.checked = true;
                this.saveConsent({
                    essential: true,
                    analytics: true,
                    preferences: true,
                    timestamp: new Date().toISOString()
                });
                this.hideModal();
            });
        }
        
        // Accept selected cookies (now the default action)
        const acceptSelectedBtn = document.getElementById('acceptSelected');
        if (acceptSelectedBtn) {
            acceptSelectedBtn.addEventListener('click', () => {
                this.saveConsent({
                    essential: true,
                    analytics: this.analyticsCheckbox.checked,
                    preferences: this.preferenceCheckbox.checked,
                    timestamp: new Date().toISOString()
                });
                this.hideModal();
            });
        }
        
        // Decline all cookies
        const declineAllBtn = document.getElementById('declineAll');
        if (declineAllBtn) {
            declineAllBtn.addEventListener('click', () => {
                this.analyticsCheckbox.checked = false;
                this.preferenceCheckbox.checked = false;
                this.saveConsent({
                    essential: true,
                    analytics: false,
                    preferences: false,
                    timestamp: new Date().toISOString()
                });
                this.hideModal();
            });
        }
    }
    
    saveConsent(consent) {
        // Save to localStorage
        localStorage.setItem(this.cookieName, JSON.stringify(consent));
        
        // Also save as a cookie for server-side access
        const cookieValue = JSON.stringify(consent);
        const expiryDate = new Date();
        expiryDate.setFullYear(expiryDate.getFullYear() + 1); // 1 year expiry
        
        document.cookie = `${this.cookieName}=${encodeURIComponent(cookieValue)}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
        
        // Apply the consent immediately
        this.applyConsent(consent);
    }
    
    getConsent() {
        // Try localStorage first
        const localConsent = localStorage.getItem(this.cookieName);
        if (localConsent) {
            try {
                return JSON.parse(localConsent);
            } catch (e) {
                console.warn('Invalid consent data in localStorage');
            }
        }
        
        // Try cookies as fallback
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === this.cookieName) {
                try {
                    return JSON.parse(decodeURIComponent(value));
                } catch (e) {
                    console.warn('Invalid consent data in cookie');
                }
            }
        }
        
        return null;
    }
    
    applyConsent(consent) {
        if (!consent) return;
        
        // Apply analytics consent
        if (consent.analytics) {
            this.enableAnalytics();
        } else {
            this.disableAnalytics();
        }
        
        // Apply preferences consent
        if (consent.preferences) {
            this.enablePreferences();
        } else {
            this.disablePreferences();
        }
    }
    
    enableAnalytics() {
        // Enable Google Analytics
        if (typeof gtag !== 'undefined') {
            gtag('consent', 'update', {
                'analytics_storage': 'granted'
            });
        }
        
        // Enable Microsoft Clarity
        if (typeof clarity !== 'undefined') {
            // Clarity is already loaded, just ensure it's tracking
            console.log('Analytics enabled');
        }
    }
    
    disableAnalytics() {
        // Disable Google Analytics
        if (typeof gtag !== 'undefined') {
            gtag('consent', 'update', {
                'analytics_storage': 'denied'
            });
        }
        
        // Disable Microsoft Clarity
        if (typeof clarity !== 'undefined') {
            // Note: Clarity doesn't have a built-in disable method
            // We'll rely on the consent check
            console.log('Analytics disabled');
        }
    }
    
    enablePreferences() {
        // Enable preference storage
        console.log('Preferences enabled');
    }
    
    disablePreferences() {
        // Disable preference storage
        console.log('Preferences disabled');
    }
    
    // Method to update consent (for future use)
    updateConsent(newConsent) {
        this.saveConsent(newConsent);
    }
    
    // Method to reset consent (for testing)
    resetConsent() {
        localStorage.removeItem(this.cookieName);
        document.cookie = `${this.cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
        location.reload();
    }
}

// Initialize cookie consent when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new CookieConsent();
});

// Add a global function to access cookie consent from other scripts
window.RidealCookieConsent = {
    getConsent: function() {
        const consent = localStorage.getItem('rideal_cookie_consent');
        return consent ? JSON.parse(consent) : null;
    },
    
    hasAnalyticsConsent: function() {
        const consent = this.getConsent();
        return consent && consent.analytics;
    },
    
    hasPreferencesConsent: function() {
        const consent = this.getConsent();
        return consent && consent.preferences;
    }
};
