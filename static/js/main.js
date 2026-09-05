// AWAS - Adlay Water Augmentation System
// Modern JavaScript for enhanced UX

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initScrollAnimations();
    initNavbarScroll();
    initSmoothScrolling();
    initFormEnhancements();
    initTooltips();
    initLoadingStates();
    initModalEnhancements();
});

// Scroll-triggered animations
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fadeInUp');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements for animation
    document.querySelectorAll('.feature-card, .benefit-item, .stat-item').forEach(el => {
        observer.observe(el);
    });
}

// Navbar scroll effects
function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    let lastScrollTop = 0;

    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Add shadow on scroll
        if (scrollTop > 10) {
            navbar.classList.add('shadow-lg');
        } else {
            navbar.classList.remove('shadow-lg');
        }

        // Hide/show navbar on scroll (optional)
        if (scrollTop > lastScrollTop && scrollTop > 100) {
            navbar.style.transform = 'translateY(-100%)';
        } else {
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop;
    });
}

// Smooth scrolling for anchor links
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Form enhancements
function initFormEnhancements() {
    // Add floating labels effect
    document.querySelectorAll('.form-control').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
    });

    // Form validation feedback
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
            }
        });
    });
}

// Initialize Bootstrap tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Loading states for buttons
function initLoadingStates() {
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function() {
            if (this.type === 'submit' || this.classList.contains('btn-primary')) {
                this.classList.add('loading');
                setTimeout(() => {
                    this.classList.remove('loading');
                }, 2000);
            }
        });
    });
}

// Utility functions
const Utils = {
    // Debounce function for performance
    debounce: function(func, wait, immediate) {
        let timeout;
        return function executedFunction() {
            const context = this;
            const args = arguments;
            const later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    },

    // Throttle function for scroll events
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Check if element is in viewport
    isInViewport: function(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
};

// Performance optimizations
window.addEventListener('scroll', Utils.throttle(function() {
    // Throttled scroll events
}, 16)); // ~60fps

// Add custom CSS classes dynamically
document.addEventListener('DOMContentLoaded', function() {
    // Add animation classes to elements
    const animatedElements = document.querySelectorAll('.feature-card, .benefit-item');
    animatedElements.forEach((el, index) => {
        el.style.animationDelay = `${index * 0.1}s`;
    });
});

// Modal enhancements
function initModalEnhancements() {
    // Password toggle functionality
    function setupPasswordToggle(toggleId, passwordId, iconId) {
        const toggleBtn = document.getElementById(toggleId);
        const passwordField = document.getElementById(passwordId);
        const icon = document.getElementById(iconId);
        
        if (toggleBtn && passwordField && icon) {
            toggleBtn.addEventListener('click', function() {
                const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
                passwordField.setAttribute('type', type);
                icon.classList.toggle('fa-eye');
                icon.classList.toggle('fa-eye-slash');
            });
        }
    }
    
    // Setup password toggles for all modals
    setupPasswordToggle('togglePassword', 'login-password', 'togglePasswordIcon');
    setupPasswordToggle('togglePassword1', 'signup-password1', 'togglePassword1Icon');
    setupPasswordToggle('togglePassword2', 'signup-password2', 'togglePassword2Icon');
    
    // Enhanced form validation for modals
    const modalForms = document.querySelectorAll('#loginForm, #signupForm, #membershipForm');
    modalForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Auto-focus first input when modal opens
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            const firstInput = modal.querySelector('input:not([type="hidden"]):not([type="checkbox"])');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
        });
        
        // Clear form validation when modal is hidden
        modal.addEventListener('hidden.bs.modal', function() {
            const form = modal.querySelector('form');
            if (form) {
                form.classList.remove('was-validated');
                form.reset();
            }
        });
    });
    
    // AJAX form submission for modals
    const ajaxForms = document.querySelectorAll('#loginForm, #signupForm, #membershipForm');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            // Show loading state
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
            submitBtn.disabled = true;
            
            // Prepare form data
            const formData = new FormData(form);
            formData.append('X-Requested-With', 'XMLHttpRequest');
            
            // Submit form via AJAX
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    showModalAlert(form, 'success', data.message || 'Success!');
                    
                    // Redirect after a short delay
                    setTimeout(() => {
                        window.location.href = data.redirect || '/';
                    }, 1500);
                } else {
                    // Show error messages
                    showFormErrors(form, data.errors);
                    showModalAlert(form, 'danger', 'Please correct the errors below.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showModalAlert(form, 'danger', 'An error occurred. Please try again.');
            })
            .finally(() => {
                // Reset button state
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            });
        });
    });
}

// Helper function to show modal alerts
function showModalAlert(form, type, message) {
    // Remove existing alerts
    const existingAlert = form.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    // Create new alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert alert at the top of the form
    form.insertBefore(alert, form.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Helper function to show form errors
function showFormErrors(form, errors) {
    // Clear existing error states
    form.querySelectorAll('.is-invalid').forEach(el => {
        el.classList.remove('is-invalid');
    });
    form.querySelectorAll('.invalid-feedback').forEach(el => {
        el.remove();
    });
    
    // Add error states and messages
    Object.keys(errors).forEach(fieldName => {
        const field = form.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.classList.add('is-invalid');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback d-block';
            errorDiv.textContent = errors[fieldName][0];
            
            field.parentNode.appendChild(errorDiv);
        }
    });
}

// Console branding
console.log('%cAWAS - Adlay Water Augmentation System', 'color: #0d6efd; font-size: 16px; font-weight: bold;');
console.log('%cProviding reliable water services to our community', 'color: #6c757d; font-size: 12px;');
