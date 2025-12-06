// notifications.js - Handles all notification functionality
document.addEventListener('DOMContentLoaded', function() {
    initNotificationSystem();
});

function initNotificationSystem() {
    // Mark a single notification as read, then navigate
    document.addEventListener('click', function(e) {
        const notifItem = e.target.closest('.notification-item');
        if (!notifItem) return;

        const notifId = notifItem.dataset.notificationId;
        const targetUrl = notifItem.getAttribute('href') || '#';

        if (!notifId) {
            // No persistent notification ID (system/info item) – just follow the link
            return;
        }

        // Prevent default navigation so we can persist the read state first
        e.preventDefault();

        markNotificationAsRead(notifId, function(remaining) {
            // Update UI state
            notifItem.classList.remove('unread');
            const dot = notifItem.querySelector('.notification-badge-dot');
            if (dot) {
                dot.remove();
            }
            setBadgeCount(remaining);
            showEmptyStateIfNeeded();

            // Finally navigate to the target page
            window.location.href = targetUrl;
        }, function() {
            // On error, still navigate so UX is not blocked
            window.location.href = targetUrl;
        });
    });

    // Mark all notifications as read
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            markAllNotificationsAsRead(function() {
                // Clear unread styling from all items
                document.querySelectorAll('.notification-item.unread').forEach(item => {
                    item.classList.remove('unread');
                    const dot = item.querySelector('.notification-badge-dot');
                    if (dot) {
                        dot.remove();
                    }
                });

                setBadgeCount(0);
                showEmptyStateIfNeeded();
            });
        });
    }
}

function markNotificationAsRead(notificationId, callback, onError) {
    fetch(`/notifications/mark-read/?id=${encodeURIComponent(notificationId)}`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok && typeof callback === 'function') {
            // Prefer server-provided remaining unread count if available
            const remaining = typeof data.remaining === 'number'
                ? data.remaining
                : Math.max(0, getCurrentBadgeCount() - 1);
            callback(remaining);
        } else {
            console.error('Error marking notification as read:', data.error || 'Unknown error');
            if (typeof onError === 'function') {
                onError();
            }
        }
    })
    .catch(error => {
        console.error('Error marking notification as read:', error);
        if (typeof onError === 'function') {
            onError();
        }
    });
}

function markAllNotificationsAsRead(callback) {
    fetch('/notifications/mark-all-read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok && typeof callback === 'function') {
            callback();
        } else if (!data.ok) {
            console.error('Error marking all notifications as read:', data.error);
        }
    })
    .catch(error => console.error('Error marking all notifications as read:', error));
}

function setBadgeCount(count) {
    count = Math.max(0, parseInt(count || 0, 10) || 0);

    const mainBadge = document.getElementById('notif-badge-main');
    const inlineBadge = document.getElementById('notif-badge-inline');
    const footerCount = document.getElementById('notif-unread-count');

    if (mainBadge) {
        if (count > 0) {
            mainBadge.textContent = count;
            mainBadge.style.display = '';
        } else {
            mainBadge.remove();
        }
    }

    if (inlineBadge) {
        if (count > 0) {
            inlineBadge.textContent = count;
            inlineBadge.style.display = '';
        } else {
            inlineBadge.style.display = 'none';
        }
    }

    if (footerCount) {
        if (count > 0) {
            footerCount.textContent = count;
            footerCount.parentElement.style.display = '';
        } else {
            footerCount.textContent = '0';
            footerCount.parentElement.style.display = 'none';
        }
    }
}

function getCurrentBadgeCount() {
    const mainBadge = document.getElementById('notif-badge-main');
    const inlineBadge = document.getElementById('notif-badge-inline');

    let current = 0;
    if (mainBadge && mainBadge.textContent) {
        current = parseInt(mainBadge.textContent, 10) || 0;
    } else if (inlineBadge && inlineBadge.textContent) {
        current = parseInt(inlineBadge.textContent, 10) || 0;
    }
    return current;
}

function showEmptyStateIfNeeded() {
    const notificationList = document.querySelector('.notification-list');
    if (!notificationList) return;

    const hasUnreadItems = document.querySelectorAll('.notification-item.unread').length > 0;
    const hasEmptyState = document.querySelector('.notification-empty');

    if (!hasUnreadItems && !hasEmptyState) {
        showEmptyState();
    }
}

function showEmptyState() {
    const notificationList = document.querySelector('.notification-list');
    if (!notificationList) return;

    // Remove any existing empty states
    document.querySelectorAll('.notification-empty').forEach(el => el.remove());

    // Add new empty state
    const emptyState = document.createElement('div');
    emptyState.className = 'notification-empty';
    emptyState.innerHTML = `
        <i class="fas fa-bell-slash"></i>
        <p>No new notifications</p>
    `;
    notificationList.appendChild(emptyState);
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
