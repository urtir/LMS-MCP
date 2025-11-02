'use strict';

class GlobalNavbar {
    constructor(root) {
        this.root = root;
        this.userMenu = root.querySelector('#userMenu');
        this.toggleButton = root.querySelector('[data-action="toggle-user-menu"]');
        this.logoutButtons = root.querySelectorAll('[data-action="logout"]');
        this.navigateButtons = root.querySelectorAll('[data-action="navigate"]');
        this.documentClickHandler = (event) => this.handleDocumentClick(event);
    }

    init() {
        if (!this.root) {
            return;
        }

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        this.bindEvents();
    }

    bindEvents() {
        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                this.toggleUserMenu();
            });
            document.addEventListener('click', this.documentClickHandler);
        }

        this.logoutButtons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                this.logout();
            });
        });

        this.navigateButtons.forEach((button) => {
            button.addEventListener('click', (event) => {
                const route = button.dataset.route || button.getAttribute('href');
                if (!route) {
                    return;
                }

                if (button.tagName === 'A') {
                    return;
                }

                event.preventDefault();
                this.navigate(route);
            });
        });
    }

    toggleUserMenu() {
        if (this.userMenu) {
            this.userMenu.classList.toggle('hidden');
        }
    }

    handleDocumentClick(event) {
        if (!this.userMenu) {
            return;
        }

        const toggle = event.target.closest('[data-action="toggle-user-menu"]');
        if (!toggle && !this.userMenu.contains(event.target)) {
            this.userMenu.classList.add('hidden');
        }
    }

    async logout() {
        try {
            const response = await fetch('/api/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                window.location.href = '/';
            } else {
                window.alert('Logout failed. Please try again.');
            }
        } catch (error) {
            console.error('Logout error:', error);
            window.alert('Logout failed. Please try again.');
        }
    }

    navigate(route) {
        window.location.href = route;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const navbar = document.querySelector('[data-component="global-navbar"]');
    if (!navbar) {
        return;
    }

    const controller = new GlobalNavbar(navbar);
    controller.init();
});
