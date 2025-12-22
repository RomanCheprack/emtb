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
    
    // WhatsApp floating share button logic - use event delegation for dynamic content
    document.addEventListener('click', function(e) {
        const floatBtn = document.getElementById('whatsapp-share-float');
        if (floatBtn && floatBtn.style.display !== 'none') {
            // Check if click is on the button or its children
            if (e.target.closest('#whatsapp-share-float') === floatBtn || 
                e.target === floatBtn || 
                floatBtn.contains(e.target)) {
                e.preventDefault();
                e.stopPropagation();
                console.log('WhatsApp button clicked');
                if (typeof shareComparison === 'function') {
                    shareComparison();
                } else {
                    console.error('shareComparison function not found');
                }
            }
        }
    });
    // Hide the button if there are no bikes to compare
    var bikesTable = document.querySelector('.compare-table');
    var floatBtn = document.getElementById('whatsapp-share-float');
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
    
    // Check if there are at least 2 bikes in the comparison table
    const bikeHeaders = document.querySelectorAll('.specs-th');
    if (!bikeHeaders || bikeHeaders.length < 2) {
        console.log("Not enough bikes to compare (need at least 2)");
        return;
    }
    
    // Show loading message
    const loadingDiv = document.getElementById('ai-loading');
    if (loadingDiv) {
        loadingDiv.style.display = 'block';
        startThinkingAnimation();
    }

    fetch("/api/compare_ai_from_session")
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                // Extract error message from response if available
                const errorMsg = data.error || `HTTP error! status: ${res.status}`;
                throw new Error(errorMsg);
            }
            return data;
        })
        .then(data => {
            // Hide loading message
            if (loadingDiv) {
                loadingDiv.style.display = 'none';
                stopThinkingAnimation();
            }

            if (data.error) {
                console.error("AI comparison error:", data.error, data.details);
                const errorMsg = data.details ? `${data.error}<br><small>${data.details}</small>` : data.error;
                container.innerHTML = `<div class="alert alert-danger">${errorMsg}</div>`;
                container.style.display = "block";
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
                console.log('WhatsApp button shown with URL:', data.share_url);
                
                // Add direct click handler as backup
                shareFloatBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Direct click handler triggered');
                    shareComparison();
                }, { once: false });
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
            console.error("Error fetching AI comparison:", err);
            if (loadingDiv) {
                loadingDiv.style.display = 'none';
                stopThinkingAnimation();
            }
            container.innerHTML = `<div class="alert alert-danger">שגיאה: ${err.message}<br><small>נסה לרענן את הדף או לנסות שוב מאוחר יותר</small></div>`;
            container.style.display = "block";
        });
}

// Function to share comparison via WhatsApp
function shareComparison() {
    const floatBtn = document.getElementById('whatsapp-share-float');
    const shareUrl = floatBtn.getAttribute('data-share-url');
    
    if (!shareUrl) {
        alert('אין השוואה זמינה לשיתוף');
        return;
    }
    
    // Open WhatsApp with the comparison URL (same as shared_comparison.html)
    const whatsappUrl = "https://wa.me/?text=" + encodeURIComponent(shareUrl);
    window.open(whatsappUrl, "_blank", "noopener,noreferrer");
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