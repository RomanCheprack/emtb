document.addEventListener('DOMContentLoaded', function() {
    // Load current preferences
    const consent = window.RidealCookieConsent.getConsent();
    
    if (consent) {
        document.getElementById('analyticsCookies').checked = consent.analytics !== false; // Default to true if not explicitly false
        document.getElementById('preferenceCookies').checked = consent.preferences !== false; // Default to true if not explicitly false
    } else {
        // If no consent exists, default to checked (consent given)
        document.getElementById('analyticsCookies').checked = true;
        document.getElementById('preferenceCookies').checked = true;
    }
    
    // Save preferences
    document.getElementById('savePreferences').addEventListener('click', function() {
        const newConsent = {
            essential: true,
            analytics: document.getElementById('analyticsCookies').checked,
            preferences: document.getElementById('preferenceCookies').checked,
            timestamp: new Date().toISOString()
        };
        
        // Save to localStorage
        localStorage.setItem('rideal_cookie_consent', JSON.stringify(newConsent));
        
        // Also save as cookie
        const cookieValue = JSON.stringify(newConsent);
        const expiryDate = new Date();
        expiryDate.setFullYear(expiryDate.getFullYear() + 1);
        
        document.cookie = `rideal_cookie_consent=${encodeURIComponent(cookieValue)}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
        
        // Apply the consent
        if (window.RidealCookieConsent) {
            // Reload page to apply new settings
            location.reload();
        }
        
        alert('ההגדרות נשמרו בהצלחה!');
    });
    
    // Reset preferences
    document.getElementById('resetPreferences').addEventListener('click', function() {
        if (confirm('האם אתה בטוח שברצונך לאפס את כל הגדרות העוגיות?')) {
            localStorage.removeItem('rideal_cookie_consent');
            document.cookie = 'rideal_cookie_consent=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            location.reload();
        }
    });
});
