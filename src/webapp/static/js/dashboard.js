class AISOCDashboard {
    constructor() {
        this.timelineChart = null;
        this.severityChart = null;
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
        this.userMenu = document.getElementById('userMenu');
        this.lastUpdated = document.getElementById('lastUpdated');
        this.modelName = document.getElementById('modelName');
        this.toolsCount = document.getElementById('toolsCount');
        this.documentClickHandler = (event) => this.handleDocumentClick(event);
        this.severityPalette = [
            '#94a3b8', '#cbd5f5', '#e2e8f0', '#bfdbfe', '#93c5fd', '#60a5fa',
            '#fcd34d', '#fbbf24', '#fca5a5', '#f87171', '#ef4444', '#dc2626',
            '#b91c1c', '#991b1b', '#7f1d1d', '#6b21a8', '#5b21b6', '#3b0764'
        ];
    }

    init() {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        this.bindEvents();
        this.refreshAll();
    }

    bindEvents() {
        document.querySelectorAll('[data-action="navigate"]').forEach((button) => {
            button.addEventListener('click', () => this.navigate(button.dataset.route));
        });

        document.querySelectorAll('[data-action="refresh-dashboard"]').forEach((button) => {
            button.addEventListener('click', () => this.refreshAll());
        });

        const logoutButtons = document.querySelectorAll('[data-action="logout"]');
        logoutButtons.forEach((button) => {
            button.addEventListener('click', () => this.logout());
        });

        const toggleButtons = document.querySelectorAll('[data-action="toggle-user-menu"]');
        toggleButtons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                this.toggleUserMenu();
            });
        });

        document.addEventListener('click', this.documentClickHandler);
    }

    navigate(route) {
        if (!route) {
            return;
        }
        window.location.href = route;
    }

    toggleUserMenu() {
        if (!this.userMenu) {
            return;
        }
        this.userMenu.classList.toggle('hidden');
    }

    handleDocumentClick(event) {
        if (!this.userMenu) {
            return;
        }
        const toggleButton = event.target.closest('[data-action="toggle-user-menu"]');
        if (!toggleButton && !this.userMenu.contains(event.target)) {
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
                window.location.href = '/login';
            } else {
                window.alert('Logout failed, please try again.');
            }
        } catch (error) {
            console.error('Logout error:', error);
            window.alert('Logout failed, please try again.');
        }
    }

    async refreshAll() {
        this.updateLastUpdated();
        try {
            const [securityResponse, statusResponse, toolsResponse] = await Promise.all([
                fetch('/api/security-data'),
                fetch('/api/status'),
                fetch('/api/tools')
            ]);

            if (securityResponse.status === 401) {
                window.location.href = '/login';
                return;
            }

            const securityData = await securityResponse.json();
            const statusData = statusResponse.ok ? await statusResponse.json() : {};
            const toolsData = toolsResponse.ok ? await toolsResponse.json() : {};

            this.renderStats(securityData.stats || {});
            this.renderCharts(securityData.timeline || [], securityData.rule_levels || []);
            this.renderAgents(securityData.agents || []);
            this.renderAlerts(securityData.alerts || []);
            this.renderRuleGroups(securityData.rule_groups || []);
            this.renderChatStats(securityData.chat || {});
            this.renderReports(securityData.reports || []);
            this.renderServices(securityData.services || {}, statusData || {});
            this.updateHeaderStatus(statusData || {});
            this.updateFooterStatus(statusData || {}, toolsData || {});

            if (this.lastUpdated) {
                this.lastUpdated.textContent = `Updated ${new Date().toLocaleString()}`;
            }
        } catch (error) {
            console.error('Failed to refresh dashboard:', error);
            this.setErrorState();
        }
    }

    setErrorState() {
        if (this.statusDot) {
            this.statusDot.className = 'w-2 h-2 rounded-full bg-red-500';
        }
        if (this.statusText) {
            this.statusText.className = 'text-red-600';
            this.statusText.textContent = 'Data fetch failed';
        }
    }

    updateLastUpdated() {
        if (this.lastUpdated) {
            this.lastUpdated.textContent = 'Refreshing...';
        }
    }

    renderStats(stats) {
        const totalAlerts = document.getElementById('stat-total-alerts');
        const activeAgents = document.getElementById('stat-active-agents');
        const criticalEvents = document.getElementById('stat-critical-events');
        const securityScore = document.getElementById('stat-security-score');
        const alertVelocity = document.getElementById('stat-alert-velocity');
        const alertTrend = document.getElementById('stat-alert-trend');

        if (totalAlerts) {
            totalAlerts.textContent = this.formatNumber(stats.total_alerts);
        }
        if (activeAgents) {
            activeAgents.textContent = this.formatNumber(stats.active_agents);
        }
        if (criticalEvents) {
            criticalEvents.textContent = this.formatNumber(stats.critical_events);
        }
        if (securityScore) {
            const score = typeof stats.security_score === 'number' ? stats.security_score : null;
            securityScore.textContent = score !== null ? String(score) : '--';
            securityScore.classList.remove('text-green-500', 'text-amber-500', 'text-red-500', 'text-slate-900');
            if (score !== null) {
                if (score >= 80) {
                    securityScore.classList.add('text-green-500');
                } else if (score >= 60) {
                    securityScore.classList.add('text-amber-500');
                } else {
                    securityScore.classList.add('text-red-500');
                }
            } else {
                securityScore.classList.add('text-slate-900');
            }
        }
        if (alertVelocity) {
            const value = typeof stats.alert_velocity === 'number' ? stats.alert_velocity : null;
            alertVelocity.textContent = value !== null ? `${value > 0 ? '+' : ''}${value}` : '--';
            alertVelocity.classList.remove('text-red-500', 'text-green-500', 'text-slate-900');
            if (value !== null) {
                if (value > 0) {
                    alertVelocity.classList.add('text-red-500');
                } else if (value < 0) {
                    alertVelocity.classList.add('text-green-500');
                } else {
                    alertVelocity.classList.add('text-slate-900');
                }
            } else {
                alertVelocity.classList.add('text-slate-900');
            }
        }
        if (alertTrend) {
            const percent = typeof stats.alert_trend_percent === 'number' ? stats.alert_trend_percent : null;
            if (percent === null) {
                alertTrend.textContent = 'Trend vs previous window';
            } else if (percent === 0) {
                alertTrend.textContent = 'No change from previous day';
            } else {
                const direction = percent > 0 ? 'increase' : 'decrease';
                alertTrend.textContent = `${Math.abs(percent)}% ${direction} vs previous day`;
            }
        }
    }

    renderCharts(timeline, severity) {
        this.renderTimelineChart(timeline);
        this.renderSeverityChart(severity);
    }

    renderTimelineChart(timeline) {
        const canvas = document.getElementById('timelineChart');
        if (!canvas) {
            return;
        }

        const labels = timeline.map((entry) => entry.date);
        const data = timeline.map((entry) => entry.count);

        if (this.timelineChart) {
            this.timelineChart.data.labels = labels;
            this.timelineChart.data.datasets[0].data = data;
            this.timelineChart.update();
            return;
        }

        this.timelineChart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Alerts',
                        data,
                        borderColor: 'rgba(59, 130, 246, 1)',
                        backgroundColor: 'rgba(59, 130, 246, 0.15)',
                        fill: true,
                        tension: 0.35,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    renderSeverityChart(severity) {
        const canvas = document.getElementById('severityChart');
        if (!canvas) {
            return;
        }

        const sorted = [...severity].sort((a, b) => a.level - b.level);
        const labels = sorted.map((item) => `Lvl ${item.level}`);
        const data = sorted.map((item) => item.count);
        const colors = sorted.map((item) => this.getSeverityColor(item.level));
        const total = data.reduce((sum, value) => sum + value, 0);

        if (this.severityChart) {
            this.severityChart.data.labels = labels;
            this.severityChart.data.datasets[0].data = data;
            this.severityChart.data.datasets[0].backgroundColor = colors;
            this.severityChart.update();
            this.renderSeverityLegend(sorted, total, colors);
            return;
        }

        this.severityChart = new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Alerts',
                        data,
                        backgroundColor: colors,
                        borderColor: '#ffffff',
                        borderWidth: 1,
                        hoverOffset: 8
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const value = context.raw || 0;
                                if (total === 0) {
                                    return ` ${value} alerts (0%)`;
                                }
                                const percent = ((value / total) * 100).toFixed(1);
                                return ` ${value} alerts (${percent}%)`;
                            }
                        }
                    }
                },
                cutout: '45%'
            }
        });

        this.renderSeverityLegend(sorted, total, colors);
    }

    renderAgents(agents) {
        const tableBody = document.getElementById('agents-table-body');
        if (!tableBody) {
            return;
        }
        tableBody.innerHTML = '';

        agents.slice(0, 10).forEach((agent) => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-slate-50';

            const nameCell = document.createElement('td');
            nameCell.className = 'px-3 py-2 font-medium text-slate-700';
            nameCell.textContent = agent.name || 'Unknown';

            const countCell = document.createElement('td');
            countCell.className = 'px-3 py-2 text-slate-600';
            countCell.textContent = this.formatNumber(agent.count);

            const levelCell = document.createElement('td');
            levelCell.className = 'px-3 py-2 text-slate-600';
            levelCell.textContent = agent.max_rule_level !== undefined ? `Lv ${agent.max_rule_level}` : '--';

            const lastSeenCell = document.createElement('td');
            lastSeenCell.className = 'px-3 py-2 text-slate-500';
            lastSeenCell.textContent = this.formatRelativeTime(agent.last_seen);

            const statusCell = document.createElement('td');
            statusCell.className = 'px-3 py-2';
            const badge = document.createElement('span');
            badge.className = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium';
            if (agent.status === 'active') {
                badge.classList.add('bg-green-100', 'text-green-700');
                badge.textContent = 'Active';
            } else {
                badge.classList.add('bg-amber-100', 'text-amber-700');
                badge.textContent = 'Monitoring';
            }
            statusCell.appendChild(badge);

            row.appendChild(nameCell);
            row.appendChild(countCell);
            row.appendChild(levelCell);
            row.appendChild(lastSeenCell);
            row.appendChild(statusCell);
            tableBody.appendChild(row);
        });

        if (!agents.length) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.className = 'px-3 py-6 text-center text-sm text-slate-400';
            cell.textContent = 'No agent activity available.';
            row.appendChild(cell);
            tableBody.appendChild(row);
        }
    }

    renderAlerts(alerts) {
        const tableBody = document.getElementById('alerts-table-body');
        if (!tableBody) {
            return;
        }
        tableBody.innerHTML = '';

        alerts.slice(0, 20).forEach((alert) => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-slate-50';

            const timeCell = document.createElement('td');
            timeCell.className = 'px-3 py-2 text-slate-600';
            timeCell.textContent = this.formatTimestamp(alert.timestamp);

            const agentCell = document.createElement('td');
            agentCell.className = 'px-3 py-2 text-slate-600';
            agentCell.textContent = alert.agent_name || 'Unknown';

            const ruleCell = document.createElement('td');
            ruleCell.className = 'px-3 py-2 text-slate-500 truncate max-w-xs';
            ruleCell.title = alert.rule_description || '';
            ruleCell.textContent = alert.rule_description || 'No description';

            const levelCell = document.createElement('td');
            levelCell.className = 'px-3 py-2';
            const badge = document.createElement('span');
            badge.className = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold';
            const level = typeof alert.rule_level === 'number' ? alert.rule_level : parseInt(alert.rule_level, 10);
            if (Number.isFinite(level) && level >= 8) {
                badge.classList.add('bg-red-100', 'text-red-700');
            } else if (Number.isFinite(level) && level >= 6) {
                badge.classList.add('bg-amber-100', 'text-amber-700');
            } else {
                badge.classList.add('bg-slate-100', 'text-slate-600');
            }
            badge.textContent = Number.isFinite(level) ? `Lv ${level}` : 'Lv --';
            levelCell.appendChild(badge);

            row.appendChild(timeCell);
            row.appendChild(agentCell);
            row.appendChild(ruleCell);
            row.appendChild(levelCell);
            tableBody.appendChild(row);
        });

        if (!alerts.length) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 4;
            cell.className = 'px-3 py-6 text-center text-sm text-slate-400';
            cell.textContent = 'No recent alerts available.';
            row.appendChild(cell);
            tableBody.appendChild(row);
        }
    }

    renderRuleGroups(groups) {
        const list = document.getElementById('rule-groups-list');
        if (!list) {
            return;
        }
        list.innerHTML = '';

        groups.slice(0, 6).forEach((group) => {
            const item = document.createElement('li');
            item.className = 'rounded-lg border border-slate-200 bg-slate-50 px-3 py-3';

            const header = document.createElement('div');
            header.className = 'flex items-center justify-between';

            const title = document.createElement('p');
            title.className = 'text-sm font-semibold text-slate-700';
            title.textContent = group.raw || 'Unlabelled';

            const count = document.createElement('span');
            count.className = 'text-xs font-medium text-slate-500';
            count.textContent = `${this.formatNumber(group.count)} alerts`;

            header.appendChild(title);
            header.appendChild(count);
            item.appendChild(header);

            const badgeContainer = document.createElement('div');
            badgeContainer.className = 'mt-2 flex flex-wrap gap-2';
            (group.labels || []).forEach((label) => {
                const badge = document.createElement('span');
                badge.className = 'inline-flex items-center rounded-full bg-white px-2 py-0.5 text-xs text-slate-600 shadow-sm';
                badge.textContent = label;
                badgeContainer.appendChild(badge);
            });

            if ((group.labels || []).length) {
                item.appendChild(badgeContainer);
            }
            list.appendChild(item);
        });

        if (!groups.length) {
            const item = document.createElement('li');
            item.className = 'rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-400';
            item.textContent = 'No rule group data available.';
            list.appendChild(item);
        }
    }

    renderChatStats(chat) {
        const sessions = document.getElementById('stat-total-sessions');
        const messages = document.getElementById('stat-total-messages');
        const recent = document.getElementById('stat-recent-sessions');

        if (sessions) {
            sessions.textContent = this.formatNumber(chat.total_sessions);
        }
        if (messages) {
            messages.textContent = this.formatNumber(chat.total_messages);
        }
        if (recent) {
            recent.textContent = this.formatNumber(chat.recent_sessions);
        }
    }

    renderReports(reports) {
        const tableBody = document.getElementById('report-schedule-body');
        if (!tableBody) {
            return;
        }
        tableBody.innerHTML = '';

        reports.forEach((report) => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-slate-50';

            const periodCell = document.createElement('td');
            periodCell.className = 'px-3 py-2 font-medium text-slate-700';
            periodCell.textContent = this.formatPeriod(report.period);

            const statusCell = document.createElement('td');
            statusCell.className = 'px-3 py-2';
            const badge = document.createElement('span');
            badge.className = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium';
            if (report.enabled) {
                badge.classList.add('bg-green-100', 'text-green-700');
                badge.textContent = 'Enabled';
            } else {
                badge.classList.add('bg-slate-100', 'text-slate-500');
                badge.textContent = 'Disabled';
            }
            statusCell.appendChild(badge);

            const timeCell = document.createElement('td');
            timeCell.className = 'px-3 py-2 text-slate-600';
            timeCell.textContent = report.time || '--';

            const recipientsCell = document.createElement('td');
            recipientsCell.className = 'px-3 py-2 text-slate-500';
            const recipients = (report.recipients || []).join(', ');
                recipientsCell.textContent = recipients || 'N/A';

            row.appendChild(periodCell);
            row.appendChild(statusCell);
            row.appendChild(timeCell);
            row.appendChild(recipientsCell);
            tableBody.appendChild(row);
        });

        if (!reports.length) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 4;
            cell.className = 'px-3 py-6 text-center text-sm text-slate-400';
            cell.textContent = 'No Telegram scheduling data found in configuration.';
            row.appendChild(cell);
            tableBody.appendChild(row);
        }
    }

    renderServices(services, statusData) {
        this.updateServiceCard('service-fastmcp', services.fastmcp_connected, statusData.fastmcp);
        this.updateServiceCard('service-lmstudio', services.lm_studio_connected, statusData.lm_studio);
        this.updateServiceCard('service-telegram', services.telegram_bot_enabled, services.telegram_bot_running);
        this.updateServiceCard('service-wazuh', services.wazuh_realtime_enabled, services.wazuh_realtime_running);
    }

    updateServiceCard(elementId, enabled, connectionStatus) {
        const card = document.getElementById(elementId);
        if (!card) {
            return;
        }
        const statusDot = card.querySelector('span.rounded-full');
        const statusText = card.querySelector('span.text-xs');

        if (statusDot) {
            statusDot.className = 'h-2.5 w-2.5 rounded-full';
            const running = connectionStatus === true || connectionStatus === 'connected';
            if (running) {
                statusDot.classList.add('bg-green-500');
            } else if (connectionStatus === 'partial') {
                statusDot.classList.add('bg-amber-500');
            } else {
                statusDot.classList.add('bg-slate-300');
            }
        }
        if (statusText) {
            if (typeof connectionStatus === 'string') {
                statusText.textContent = connectionStatus === 'connected' ? 'Connected' : connectionStatus === 'partial' ? 'Partial' : 'Disconnected';
            } else if (typeof connectionStatus === 'boolean') {
                statusText.textContent = connectionStatus ? 'Running' : (enabled ? 'Enabled' : 'Stopped');
                if (!connectionStatus && !enabled) {
                    statusText.textContent = 'Disabled';
                }
            } else {
                statusText.textContent = enabled ? 'Enabled' : 'Disabled';
            }
        }
    }

    updateHeaderStatus(statusData) {
        if (!this.statusDot || !this.statusText) {
            return;
        }
        const fastmcpOk = statusData.fastmcp === 'connected';
        const lmOk = statusData.lm_studio === 'connected';

        this.statusDot.className = 'w-2 h-2 rounded-full';
        this.statusText.className = 'text-sm';

        if (fastmcpOk && lmOk) {
            this.statusDot.classList.add('bg-green-500');
            this.statusText.classList.add('text-green-600');
            this.statusText.textContent = 'All systems online';
        } else if (fastmcpOk || lmOk) {
            this.statusDot.classList.add('bg-amber-500');
            this.statusText.classList.add('text-amber-600');
            this.statusText.textContent = 'Partial availability';
        } else {
            this.statusDot.classList.add('bg-red-500');
            this.statusText.classList.add('text-red-600');
            this.statusText.textContent = 'Systems offline';
        }
    }

    updateFooterStatus(statusData, toolsData) {
        if (this.modelName) {
            this.modelName.textContent = statusData.model || 'N/A';
        }
        if (this.toolsCount) {
            const count = Array.isArray(toolsData.tools) ? toolsData.tools.length : 0;
            this.toolsCount.textContent = count ? `${count}` : '0';
        }
    }

    getSeverityColor(level) {
        if (!Array.isArray(this.severityPalette) || !this.severityPalette.length) {
            return '#94a3b8';
        }
        if (level >= 0 && level < this.severityPalette.length) {
            return this.severityPalette[level];
        }
        return this.severityPalette[this.severityPalette.length - 1];
    }

    renderSeverityLegend(items, total, colors) {
        const legendContainer = document.getElementById('severityLegend');
        if (!legendContainer) {
            return;
        }

        legendContainer.innerHTML = '';

        const nonZeroItems = items.filter((item) => item.count && item.count > 0);

        if (!nonZeroItems.length) {
            const emptyMessage = document.createElement('div');
            emptyMessage.className = 'rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-center text-xs text-slate-500';
            emptyMessage.textContent = 'No alerts recorded for the selected range.';
            legendContainer.appendChild(emptyMessage);
            return;
        }

        nonZeroItems.forEach((item) => {
            const index = items.indexOf(item);
            const wrapper = document.createElement('div');
            wrapper.className = 'flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1';

            const chip = document.createElement('span');
            chip.className = 'h-2.5 w-2.5 flex-shrink-0 rounded-full';
            chip.style.backgroundColor = colors[index];

            const content = document.createElement('div');
            content.className = 'flex flex-col';

            const label = document.createElement('span');
            label.className = 'font-semibold text-slate-700';
            label.textContent = `Lvl ${item.level}`;

            const details = document.createElement('span');
            const percent = total > 0 ? ((item.count / total) * 100).toFixed(1) : '0.0';
            details.className = 'text-[11px] text-slate-500';
            details.textContent = `${item.count} alerts (${percent}%) – ${item.description}`;

            content.appendChild(label);
            content.appendChild(details);

            wrapper.appendChild(chip);
            wrapper.appendChild(content);

            legendContainer.appendChild(wrapper);
        });
    }

    formatNumber(value) {
        if (value === undefined || value === null || Number.isNaN(Number(value))) {
            return '--';
        }
        return Number(value).toLocaleString();
    }

    formatTimestamp(timestamp) {
        if (!timestamp) {
            return '--';
        }
        const date = new Date(timestamp);
        if (Number.isNaN(date.getTime())) {
            return timestamp;
        }
        return date.toLocaleString();
    }

    formatRelativeTime(timestamp) {
        if (!timestamp) {
            return 'N/A';
        }
        const date = new Date(timestamp);
        if (Number.isNaN(date.getTime())) {
            return timestamp;
        }
        const diffMs = Date.now() - date.getTime();
        const diffMinutes = Math.floor(diffMs / 60000);
        if (diffMinutes < 1) {
            return 'moments ago';
        }
        if (diffMinutes < 60) {
            return `${diffMinutes} min ago`;
        }
        const diffHours = Math.floor(diffMinutes / 60);
        if (diffHours < 24) {
            return `${diffHours} hr ago`;
        }
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) {
            return `${diffDays} d ago`;
        }
        return date.toLocaleDateString();
    }

    formatPeriod(period) {
        if (!period) {
            return 'N/A';
        }
        const label = String(period).replace(/_/g, ' ');
        return label.charAt(0).toUpperCase() + label.slice(1);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new AISOCDashboard();
    dashboard.init();
});
