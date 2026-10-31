// Apex Library Management System - Main Interactive Script

document.addEventListener('DOMContentLoaded', function () {
    // 1. Dark Mode / Light Mode Management
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const htmlElement = document.documentElement;

    // Load saved theme preference
    const savedTheme = localStorage.getItem('apex_library_theme') || 'light';
    htmlElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            const currentTheme = htmlElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            htmlElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('apex_library_theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    function updateThemeIcon(theme) {
        if (!themeToggleBtn) return;
        const icon = themeToggleBtn.querySelector('i');
        if (icon) {
            if (theme === 'dark') {
                icon.className = 'bi bi-sun-fill text-warning';
            } else {
                icon.className = 'bi bi-moon-stars-fill';
            }
        }
    }

    // 2. Mobile Responsive Sidebar Toggle
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const appSidebar = document.querySelector('.app-sidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    if (sidebarToggleBtn && appSidebar) {
        sidebarToggleBtn.addEventListener('click', function () {
            appSidebar.classList.toggle('show');
            if (sidebarBackdrop) {
                sidebarBackdrop.classList.toggle('show');
            }
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', function () {
            appSidebar.classList.remove('show');
            sidebarBackdrop.classList.remove('show');
        });
    }

    // 3. Auto-Dismiss Flash Alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // 4. Generic Confirm Delete Modal Setup
    const confirmDeleteModal = document.getElementById('confirmDeleteModal');
    if (confirmDeleteModal) {
        confirmDeleteModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const actionUrl = button.getAttribute('data-action');
            const itemName = button.getAttribute('data-name') || 'this record';
            
            const form = confirmDeleteModal.querySelector('#deleteForm');
            const textTarget = confirmDeleteModal.querySelector('#deleteItemName');
            
            if (form && actionUrl) form.action = actionUrl;
            if (textTarget) textTarget.textContent = itemName;
        });
    }
});

// Helper for marking notification as read asynchronously
function markNotificationRead(notifId, el) {
    fetch(`/student/notifications/mark-read/${notifId}`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    }).then(res => res.json()).then(data => {
        if (data.success) {
            if (el) {
                el.classList.remove('bg-light');
                el.style.opacity = '0.7';
            }
            const badge = document.querySelector('.notif-badge');
            if (badge) {
                let cnt = parseInt(badge.textContent) || 0;
                if (cnt > 1) {
                    badge.textContent = cnt - 1;
                } else {
                    badge.remove();
                }
            }
        }
    }).catch(err => console.error(err));
}

