class AISOCLandingPage {
    constructor() {
        this.statusIndicator = document.getElementById('statusIndicator');
        this.refreshButton = document.querySelector('[data-action="refresh-status"]');
        this.navigateButtons = Array.from(document.querySelectorAll('[data-action="navigate"]')).filter((button) => {
            return !button.closest('[data-component="global-navbar"]');
        });
        this.demoButtons = document.querySelectorAll('[data-action="show-demo"]');
        this.anchorLinks = document.querySelectorAll('a[href^="#"]');
    }

    init() {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        this.bindEvents();
        this.checkAllSystems();
        this.loadStats();
    }

    bindEvents() {
        this.demoButtons.forEach((button) => {
            button.addEventListener('click', () => this.showDemo());
        });

        this.anchorLinks.forEach((anchor) => {
            anchor.addEventListener('click', (event) => this.handleAnchorClick(event, anchor));
        });

        if (this.refreshButton) {
            this.refreshButton.addEventListener('click', () => this.checkAllSystems());
        }

        this.navigateButtons.forEach((button) => {
            button.addEventListener('click', () => this.navigate(button.dataset.route));
        });
    }


    navigate(route) {
        if (!route) {
            return;
        }
        window.location.href = route;
    }

    handleAnchorClick(event, anchor) {
        const targetSelector = anchor.getAttribute('href');
        if (!targetSelector || !targetSelector.startsWith('#')) {
            return;
        }

        event.preventDefault();
        const target = document.querySelector(targetSelector);
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    showDemo() {
        window.alert('Demo feature coming soon! For now, try the live chat interface.');
        this.navigate('/chat');
    }

    async checkAllSystems() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            this.updateSystemStatus('fastmcp', data.fastmcp);
            this.updateSystemStatus('lm-studio', data.lm_studio);
            this.updateOverallStatus(data);
            await this.loadToolsCount();
        } catch (error) {
            console.error('Status check failed:', error);
            this.updateSystemStatus('fastmcp', 'error');
            this.updateSystemStatus('lm-studio', 'error');
            this.updateOverallStatus({ fastmcp: 'error', lm_studio: 'error' });
        }
    }

    updateSystemStatus(system, status) {
        const statusDot = document.getElementById(`${system}-status`);
        const statusText = document.getElementById(`${system}-text`);

        if (!statusDot || !statusText) {
            return;
        }

        statusDot.classList.remove('bg-green-500', 'bg-yellow-500', 'bg-red-500', 'bg-muted', 'animate-pulse');
        statusText.classList.remove('text-green-600', 'text-yellow-600', 'text-red-600', 'text-muted-foreground');

        switch (status) {
            case 'connected':
                statusDot.classList.add('bg-green-500');
                statusText.classList.add('text-green-600');
                statusText.textContent = 'Connected';
                break;
            case 'partial':
                statusDot.classList.add('bg-yellow-500');
                statusText.classList.add('text-yellow-600');
                statusText.textContent = 'Partial';
                break;
            case 'error':
            default:
                statusDot.classList.add('bg-red-500');
                statusText.classList.add('text-red-600');
                statusText.textContent = 'Disconnected';
                break;
        }
    }

    updateOverallStatus(data) {
        const overallDot = document.getElementById('overall-status');
        const overallText = document.getElementById('overall-text');
        const headerStatusDot = document.getElementById('statusDot');
        const headerStatusText = document.getElementById('statusText');

        if (!overallDot || !overallText) {
            return;
        }

        overallDot.classList.remove('bg-green-500', 'bg-yellow-500', 'bg-red-500', 'bg-muted', 'animate-pulse');
        overallText.classList.remove('text-green-600', 'text-yellow-600', 'text-red-600', 'text-muted-foreground');

        const lmStudioOk = data.lm_studio === 'connected';
        const fastmcpOk = data.fastmcp === 'connected';

        if (lmStudioOk && fastmcpOk) {
            overallDot.classList.add('bg-green-500');
            overallText.classList.add('text-green-600');
            overallText.textContent = 'All systems operational';
            this.setHeaderStatus('w-2 h-2 rounded-full bg-green-500', 'Systems Online', 'text-green-600');
        } else if (lmStudioOk || fastmcpOk) {
            overallDot.classList.add('bg-yellow-500');
            overallText.classList.add('text-yellow-600');
            overallText.textContent = 'Partial system availability';
            this.setHeaderStatus('w-2 h-2 rounded-full bg-yellow-500', 'Partial Service', 'text-yellow-600');
        } else {
            overallDot.classList.add('bg-red-500');
            overallText.classList.add('text-red-600');
            overallText.textContent = 'System maintenance required';
            this.setHeaderStatus('w-2 h-2 rounded-full bg-red-500', 'Maintenance Mode', 'text-red-600');
        }

        if (headerStatusDot && !headerStatusDot.classList.contains('bg-green-500') &&
            !headerStatusDot.classList.contains('bg-yellow-500') &&
            !headerStatusDot.classList.contains('bg-red-500')) {
            headerStatusDot.classList.add('bg-muted');
        }

        if (headerStatusText && !headerStatusText.textContent) {
            headerStatusText.textContent = 'Checking...';
            headerStatusText.classList.add('text-muted-foreground');
        }
    }

    setHeaderStatus(dotClasses, text, textClasses) {
        const headerStatusDot = document.getElementById('statusDot');
        const headerStatusText = document.getElementById('statusText');

        if (!headerStatusDot || !headerStatusText) {
            return;
        }

        headerStatusDot.className = dotClasses;
        headerStatusText.className = textClasses;
        headerStatusText.textContent = text;
    }

    async loadToolsCount() {
        const toolsCountElement = document.getElementById('tools-count');
        if (!toolsCountElement) {
            return;
        }

        try {
            const response = await fetch('/api/tools');
            const data = await response.json();
            const toolsCount = Array.isArray(data.tools) ? data.tools.length : 0;
            toolsCountElement.textContent = `${toolsCount} available`;
        } catch (error) {
            toolsCountElement.textContent = 'Error loading';
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();

            const totalSessions = document.getElementById('totalSessions');
            const totalMessages = document.getElementById('totalMessages');

            if (totalSessions) {
                this.animateNumber(totalSessions, data.total_sessions || 0);
            }

            if (totalMessages) {
                this.animateNumber(totalMessages, data.total_messages || 0);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    animateNumber(element, targetNumber) {
        if (!element) {
            return;
        }

        const currentNumber = parseInt(element.textContent, 10) || 0;
        if (currentNumber === targetNumber) {
            return;
        }

        const increment = targetNumber > currentNumber ? 1 : -1;
        let current = currentNumber;

        const timer = window.setInterval(() => {
            current += increment;
            element.textContent = String(current);

            if (current === targetNumber) {
                window.clearInterval(timer);
            }
        }, 50);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const page = new AISOCLandingPage();
    page.init();
});
