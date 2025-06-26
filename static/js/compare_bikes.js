document.addEventListener('DOMContentLoaded', function () {
    runAiComparison();
});
    // Delegate remove button clicks
    document.body.addEventListener('click', function (e) {
        if (e.target.classList.contains('remove-bike-btn')) {
            const bikeId = e.target.getAttribute('data-bike-id');
            fetch(`/remove_from_compare/${bikeId}`, { method: 'POST' })
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



function runAiComparison() {
    const container = document.getElementById("ai-comparison-container");
    container.style.display = "block";
    container.scrollIntoView({ behavior: "smooth" });

    fetch("/api/compare_ai_from_session")
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                container.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }

            document.getElementById('ai-intro').textContent = data.intro || '';
            document.getElementById('ai-recommendation').textContent = data.recommendation || '';
            document.getElementById('ai-expert-tip').textContent = data.expert_tip || '';

            // --- AI Bike Analysis Cards ---
            const analysisContainer = document.getElementById('ai-bike-analysis');
            analysisContainer.innerHTML = '';

            data.bikes?.forEach(bike => {
                const card = document.createElement('div');
                card.className = 'card mb-3';
                card.innerHTML = `
                    <div class="card-header fw-bold">${bike.name}</div>
                    <div class="card-body">
                        <p><strong>👍 יתרונות:</strong> ${bike.pros?.join(', ')}</p>
                        <p><strong>👎 חסרונות:</strong> ${bike.cons?.join(', ')}</p>
                        <p><strong>🚵‍♂️ מתאים ל:</strong> ${bike.best_for}</p>
                    </div>
                `;
                analysisContainer.appendChild(card);
            });
        })
        .catch(err => {
            container.innerHTML = `<div class="alert alert-danger">שגיאה: ${err.message}</div>`;
        });
}