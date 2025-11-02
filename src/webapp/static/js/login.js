class AISOCLoginPage {
    constructor() {
        this.form = document.getElementById('loginForm');
        this.errorContainer = document.getElementById('errorMessage');
        this.errorText = document.getElementById('errorText');
        this.submitButton = document.getElementById('submitBtn');
        this.submitText = document.getElementById('submitText');
        this.submitSpinner = document.getElementById('submitSpinner');
        this.passwordInput = document.getElementById('password');
        this.passwordToggleIcon = document.getElementById('passwordToggle');
        this.toggleButton = document.querySelector('[data-action="toggle-password"]');

        this.init();
    }

    init() {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', () => this.togglePasswordVisibility());
        }

        if (this.form) {
            this.form.addEventListener('submit', (event) => this.handleSubmit(event));
        }

        document.querySelectorAll('input').forEach((input) => {
            input.addEventListener('input', () => this.hideError());
        });
    }

    togglePasswordVisibility() {
        if (!this.passwordInput || !this.passwordToggleIcon) {
            return;
        }

        const isPassword = this.passwordInput.type === 'password';
        this.passwordInput.type = isPassword ? 'text' : 'password';
        this.passwordToggleIcon.setAttribute('data-lucide', isPassword ? 'eye-off' : 'eye');

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    showError(message) {
        if (!this.errorContainer || !this.errorText) {
            return;
        }

        this.errorText.textContent = message;
        this.errorContainer.classList.add('show');
    }

    hideError() {
        if (!this.errorContainer) {
            return;
        }

        this.errorContainer.classList.remove('show');
    }

    setLoadingState(isLoading) {
        if (!this.submitButton || !this.submitText || !this.submitSpinner) {
            return;
        }

        if (isLoading) {
            this.submitButton.disabled = true;
            this.submitText.textContent = 'Signing In...';
            this.submitSpinner.classList.remove('hidden');
        } else {
            this.submitButton.disabled = false;
            this.submitText.textContent = 'Sign In';
            this.submitSpinner.classList.add('hidden');
        }
    }

    async handleSubmit(event) {
        event.preventDefault();

        if (!this.form) {
            return;
        }

        this.hideError();
        this.setLoadingState(true);

        const formData = new FormData(this.form);
        const payload = {
            username: formData.get('username'),
            password: formData.get('password')
        };

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok) {
                window.location.href = '/';
            } else {
                this.showError(result.error || 'Login failed');
            }
        } catch (error) {
            this.showError('Network error. Please try again.');
        } finally {
            this.setLoadingState(false);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AISOCLoginPage();
});
