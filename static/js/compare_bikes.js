document.addEventListener('DOMContentLoaded', function () {
    runAiComparison();
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

            // --- Dynamic Table Header ---
            const headerRow = document.getElementById('comparison-header-row');
            headerRow.innerHTML = '<th>תכונה</th>'; // fixed column for features

            data.bikes?.forEach(bike => {
                headerRow.innerHTML += `
                    <th>
                        <strong>${bike.name}</strong>
                    </th>
                `;
            });

            // --- Dynamic Table Body ---
            const tableBody = document.getElementById('comparison-body-rows');
            tableBody.innerHTML = '';

            data.comparison_table?.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><strong>${row.feature}</strong></td>`;

                data.bikes.forEach(bike => {
                    const bikeName = bike.name;
                    const value = row.values?.[bikeName] || '—';
                    tr.innerHTML += `<td>${value}</td>`;
                });

                tableBody.appendChild(tr);
            });

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