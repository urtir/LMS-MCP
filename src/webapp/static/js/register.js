class AISOCRegisterPage {
    constructor() {
        this.form = document.getElementById('registerForm');
        this.errorContainer = document.getElementById('errorMessage');
        this.errorText = document.getElementById('errorText');
        this.successContainer = document.getElementById('successMessage');
        this.successText = document.getElementById('successText');
        this.submitButton = document.getElementById('submitBtn');
        this.submitText = document.getElementById('submitText');
        this.submitSpinner = document.getElementById('submitSpinner');
        this.passwordInput = document.getElementById('password');
        this.confirmPasswordInput = document.getElementById('confirm_password');
        this.toggleButton = document.querySelector('[data-action="toggle-password"]');
        this.passwordToggleIcon = document.getElementById('passwordToggle');

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
            input.addEventListener('input', () => {
                this.hideError();
                this.hideSuccess();
            });
        });

        if (this.confirmPasswordInput) {
            this.confirmPasswordInput.addEventListener('input', () => this.validatePasswordMatch());
        }
    }

    togglePasswordVisibility() {
        if (!this.passwordInput || !this.passwordToggleIcon) {
            return;
        }

        const isHidden = this.passwordInput.type === 'password';
        this.passwordInput.type = isHidden ? 'text' : 'password';
        this.passwordToggleIcon.setAttribute('data-lucide', isHidden ? 'eye-off' : 'eye');

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

    showSuccess(message) {
        if (!this.successContainer || !this.successText) {
            return;
        }

        this.successText.textContent = message;
        this.successContainer.classList.add('show');
    }

    hideSuccess() {
        if (!this.successContainer) {
            return;
        }

        this.successContainer.classList.remove('show');
    }

    setLoadingState(isLoading) {
        if (!this.submitButton || !this.submitText || !this.submitSpinner) {
            return;
        }

        if (isLoading) {
            this.submitButton.disabled = true;
            this.submitText.textContent = 'Creating Account...';
            this.submitSpinner.classList.remove('hidden');
        } else {
            this.submitButton.disabled = false;
            this.submitText.textContent = 'Create Account';
            this.submitSpinner.classList.add('hidden');
        }
    }

    validatePasswordMatch() {
        if (!this.passwordInput || !this.confirmPasswordInput) {
            return;
        }

        const matches = this.confirmPasswordInput.value === this.passwordInput.value || !this.confirmPasswordInput.value;
        this.confirmPasswordInput.style.borderColor = matches ? '#ffffff33' : '#ef4444';
    }

    validateForm(data) {
        if (!data.username.trim()) {
            this.showError('Username is required');
            return false;
        }
        if (!data.email.trim()) {
            this.showError('Email is required');
            return false;
        }
        if (!data.password) {
            this.showError('Password is required');
            return false;
        }
        if (data.password.length < 6) {
            this.showError('Password must be at least 6 characters long');
            return false;
        }
        if (data.password !== data.confirm_password) {
            this.showError('Passwords do not match');
            return false;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(data.email)) {
            this.showError('Please enter a valid email address');
            return false;
        }

        return true;
    }

    async handleSubmit(event) {
        event.preventDefault();

        if (!this.form) {
            return;
        }

        this.hideError();
        this.hideSuccess();

        const formData = new FormData(this.form);
        const payload = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            confirm_password: formData.get('confirm_password'),
            full_name: formData.get('full_name')
        };

        if (!this.validateForm(payload)) {
            return;
        }

        this.setLoadingState(true);

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok) {
                this.showSuccess('Account created successfully! Redirecting...');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            } else {
                this.showError(result.error || 'Registration failed');
            }
        } catch (error) {
            this.showError('Network error. Please try again.');
        } finally {
            this.setLoadingState(false);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AISOCRegisterPage();
});
