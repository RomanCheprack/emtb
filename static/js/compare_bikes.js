document.addEventListener('DOMContentLoaded', function () {
    runAiComparison();
    
    // Auto-scroll to the right to show the keys column
    const compareContainer = document.querySelector('.compare-container');
    if (compareContainer) {
        // Wait a bit for the page to fully load, then scroll to the right
        setTimeout(() => {
            compareContainer.scrollLeft = compareContainer.scrollWidth;
        }, 100);
    }
    
    // WhatsApp floating share button logic
    var floatBtn = document.getElementById('whatsapp-share-float');
    if (floatBtn) {
        floatBtn.addEventListener('click', function() {
            if (typeof shareComparison === 'function') {
                shareComparison();
            }
        });
    }
    // Hide the button if there are no bikes to compare
    var bikesTable = document.querySelector('.compare-table');
    if (!bikesTable && floatBtn) {
        floatBtn.style.display = 'none';
    }
});

// Animated thinking dots and cycling text
let thinkingInterval;
const thinkingMessages = [
    "המומחה שלנו חושב עבורך",
    "בודק מפרטים...",
    "מנתח יתרונות וחסרונות...",
    "מחשב המלצה אישית..."
];
let thinkingIndex = 0;

function startThinkingAnimation() {
    const textElem = document.getElementById('ai-thinking-text');
    const dotsElem = document.getElementById('ai-dots');
    thinkingIndex = 0;
    let dotCount = 0;
    if (!textElem || !dotsElem) return;
    thinkingInterval = setInterval(() => {
        // Cycle message every 2.5 seconds
        if (dotCount % 5 === 0) {
            textElem.textContent = thinkingMessages[thinkingIndex % thinkingMessages.length];
            thinkingIndex++;
        }
        // Animate dots
        dotsElem.textContent = '.'.repeat(dotCount % 4);
        dotCount++;
    }, 500);
}

function stopThinkingAnimation() {
    clearInterval(thinkingInterval);
    const dotsElem = document.getElementById('ai-dots');
    if (dotsElem) dotsElem.textContent = '';
}

// Delegate remove button clicks
document.body.addEventListener('click', function (e) {
    if (e.target.classList.contains('remove-bike-btn')) {
        const bikeId = e.target.getAttribute('data-bike-id');
        fetch('/remove_from_compare', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ bike_id: bikeId })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // Reload the page to update the bike list
                    location.reload();
                }
            })
            .catch(err => {
                alert("שגיאה במחיקה: " + err.message);
            });
    }
});

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('show-more-btn')) {
        const btn = e.target;
        const cell = btn.closest('.collapsible-cell');
        const shortSpan = cell.querySelector('.cell-short');
        const fullSpan = cell.querySelector('.cell-full');
        if (btn.textContent.includes('הצג עוד')) {
            shortSpan.style.display = 'none';
            fullSpan.style.display = 'inline';
            btn.textContent = 'הצג פחות';
        } else {
            shortSpan.style.display = 'inline';
            fullSpan.style.display = 'none';
            btn.textContent = 'הצג עוד';
        }
    }
});

function runAiComparison() {
    const container = document.getElementById("ai-comparison-container");
    
    // Show loading message
    const loadingDiv = document.getElementById('ai-loading');
    if (loadingDiv) {
        loadingDiv.style.display = 'block';
        startThinkingAnimation();
    }

    fetch("/api/compare_ai_from_session")
        .then(res => res.json())
        .then(data => {
            // Hide loading message
            if (loadingDiv) {
                loadingDiv.style.display = 'none';
                stopThinkingAnimation();
            }

            if (data.error) {
                container.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }
            
            // Show the container only after successful API response
            container.style.display = "block";
            container.scrollIntoView({ behavior: "smooth" });
            
            // Handle new response format with comparison_id and share_url
            let comparisonData = data;
            
            // Check if this is the new format with nested data
            if (data.data) {
                comparisonData = data.data;
            } else if (data.comparison_data) {
                // Handle old format with comparison_data
                comparisonData = data.comparison_data;
            }
            
            // Show share button if we have comparison data
            const shareFloatBtn = document.getElementById('whatsapp-share-float');
            if (shareFloatBtn && data.comparison_id && data.share_url) {
                shareFloatBtn.style.display = 'flex';
                shareFloatBtn.setAttribute('data-comparison-id', data.comparison_id);
                shareFloatBtn.setAttribute('data-share-url', data.share_url);
            }

            // Update the UI with ChatGPT response
            const introElement = document.getElementById('ai-intro');
            const recommendationElement = document.getElementById('ai-recommendation');
            const expertTipElement = document.getElementById('ai-expert-tip');
            
            if (introElement) {
                introElement.textContent = comparisonData.intro || '';
            }
            if (recommendationElement) {
                recommendationElement.textContent = comparisonData.recommendation || '';
            }
            if (expertTipElement) {
                expertTipElement.textContent = comparisonData.expert_tip || '';
            }

            // --- AI Bike Analysis Cards ---
            const analysisContainer = document.getElementById('ai-bike-analysis');
            analysisContainer.innerHTML = '';

            comparisonData.bikes?.forEach(bike => {
                const card = document.createElement('div');
                card.className = 'card mb-3';
                card.innerHTML = `
                    <div class="card-header fw-bold d-flex justify-content-between align-items-center">
                        <span>${bike.name}</span>
                    </div>
                    <div class="card-body">
                        <p><strong>👍 יתרונות:</strong> ${bike.pros?.join(', ')}</p>
                        <p><strong>👎 חסרונות:</strong> ${bike.cons?.join(', ')}</p>
                        <p><strong>🚵‍♂️ מתאים ל:</strong> ${bike.best_for}</p>
                    </div>
                `;
                analysisContainer.appendChild(card);
            });

            // Note: WhatsApp share button is already handled above
        })
        .catch(err => {
            if (loadingDiv) {
                loadingDiv.style.display = 'none';
                stopThinkingAnimation();
            }
            container.innerHTML = `<div class="alert alert-danger">שגיאה: ${err.message}</div>`;
        });
}

// Function to share comparison
function shareComparison() {
    const floatBtn = document.getElementById('whatsapp-share-float');
    const shareUrl = floatBtn.getAttribute('data-share-url');
    const comparisonId = floatBtn.getAttribute('data-comparison-id');
    
    if (!shareUrl) {
        alert('אין השוואה זמינה לשיתוף');
        return;
    }
    
    // Check if Web Share API is available (mobile devices)
    if (navigator.share) {
        navigator.share({
            title: 'השוואת אופניים - המלצת מומחה',
            text: 'בדוק את ההשוואה המקצועית בין אופני הרים חשמליים',
            url: shareUrl
        }).then(() => {
            // Shared successfully
        }).catch((error) => {
            // Fallback to copy URL
            copyShareUrl(shareUrl);
        });
    } else {
        // Fallback for desktop browsers
        copyShareUrl(shareUrl);
    }
}

// Function to copy share URL to clipboard (for compare_bikes page)
function copyShareUrl(url) {
    navigator.clipboard.writeText(url).then(function() {
        // Show success message
        const button = event.target.closest('button');
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
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = url;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        // Show success message
        alert('הקישור הועתק ללוח!');
    });
}