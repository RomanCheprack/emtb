/**
 * Record a purchase outbound click (server-side). Only call when product_url is non-empty.
 * Used from bikes listing (bikes.js) and bike detail page.
 */
(function () {
    function recordPurchaseClick(bikeId, productUrl) {
        if (!bikeId || !productUrl || !String(productUrl).trim()) {
            return;
        }
        var payload = JSON.stringify({
            bike_id: String(bikeId),
            product_url: String(productUrl).trim(),
        });
        fetch("/api/purchase_click", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: payload,
            keepalive: true,
        }).catch(function () {});
    }

    window.recordPurchaseClick = recordPurchaseClick;

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("a.purchase-track").forEach(function (el) {
            el.addEventListener("click", function () {
                var bid = el.getAttribute("data-bike-id");
                var pid = el.getAttribute("data-product-url");
                recordPurchaseClick(bid, pid);
            });
        });
    });
})();
