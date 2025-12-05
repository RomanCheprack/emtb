// Test Ride Modal Functionality

document.addEventListener('DOMContentLoaded', function() {
    // Get modal elements
    const modal = document.getElementById('testRideModal');
    const btn = document.getElementById('testRideBtn');
    const closeBtn = document.querySelector('.test-ride-modal-close');
    const cancelBtn = document.getElementById('cancelTestRide');
    const form = document.getElementById('testRideForm');

    // Open modal when button is clicked
    if (btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        });
    }

    // Close modal when X is clicked
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            closeModal();
        });
    }

    // Close modal when cancel button is clicked
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            closeModal();
        });
    }

    // Close modal when clicking outside of it
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    // Close modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.style.display === 'block') {
            closeModal();
        }
    });

    // Handle form submission
    if (form) {
        form.addEventListener('submit', function(e) {
            // Allow the form to submit naturally
            // After submission, close the modal and show success message
            setTimeout(function() {
                closeModal();
                form.reset();
                showSuccessMessage();
            }, 500);
        });
    }

    // Function to close modal
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
    }

    // Function to show success message
    function showSuccessMessage() {
        // Create success notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #28a745 0%, #218838 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            animation: slideInRight 0.4s ease;
            font-size: 16px;
            font-weight: 600;
        `;
        notification.textContent = 'הבקשה נשלחה בהצלחה! נחזור אליך בקרוב 🚴';
        
        document.body.appendChild(notification);

        // Remove notification after 4 seconds
        setTimeout(function() {
            notification.style.animation = 'slideOutRight 0.4s ease';
            setTimeout(function() {
                notification.remove();
            }, 400);
        }, 4000);
    }

    // Add animation styles dynamically
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
});

