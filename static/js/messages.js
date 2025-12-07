// Auto-dismiss messages after 3 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    
    alerts.forEach(function(alert) {
        // Set timeout to remove the alert after 3 seconds
        const timeoutId = setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 2000);
        
        // Clear the timeout if user manually closes the alert
        const closeButton = alert.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                clearTimeout(timeoutId);
            });
        }
    });
});
