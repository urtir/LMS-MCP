let currentConfig = {};
let activeTab = 'overview';

function loadConfiguration() {
    return fetch('/admin/api/config')
        .then((response) => response.json())
        .then((data) => {
            if (!data.success) {
                throw new Error(data.error);
            }

            currentConfig = data.config;
            renderConfiguration();
        })
        .catch((error) => {
            showToast(`Failed to load configuration: ${error.message}`, 'error');
            throw error;
        });
}

function renderConfiguration() {
    renderTabs();
    renderTabContent();
}

function renderTabs() {
    const tabsContainer = document.getElementById('config-tabs');
    tabsContainer.innerHTML = '';

    const overviewTab = document.createElement('button');
    overviewTab.className = `relative py-4 px-2 border-b-2 font-medium text-sm transition-all duration-200 flex items-center gap-2 ${
        activeTab === 'overview'
            ? 'border-primary text-primary font-semibold'
            : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
    }`;
    overviewTab.innerHTML = `
        <i data-lucide="activity" class="w-4 h-4"></i>
        Overview
    `;
    overviewTab.onclick = () => switchTab('overview');
    tabsContainer.appendChild(overviewTab);

    Object.keys(currentConfig).forEach((categoryId) => {
        const category = currentConfig[categoryId];
        const tab = document.createElement('button');
        tab.className = `relative py-4 px-2 border-b-2 font-medium text-sm transition-all duration-200 flex items-center gap-2 ${
            activeTab === categoryId
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
        }`;

        const iconName = (() => {
            switch (categoryId) {
                case 'database':
                    return 'database';
                case 'telegram':
                    return 'message-circle';
                case 'security':
                    return 'shield';
                case 'api':
                    return 'globe';
                default:
                    return 'settings';
            }
        })();

        tab.innerHTML = `
            <i data-lucide="${iconName}" class="w-4 h-4"></i>
            ${category.name}
        `;
        tab.onclick = () => switchTab(categoryId);
        tabsContainer.appendChild(tab);
    });

    setTimeout(() => lucide.createIcons(), 100);
}

function switchTab(categoryId) {
    activeTab = categoryId;
    renderConfiguration();
}

function renderTabContent() {
    const contentContainer = document.getElementById('tab-content');
    contentContainer.innerHTML = '';

    if (activeTab === 'overview') {
        renderOverviewContent(contentContainer);
        return;
    }

    if (!currentConfig[activeTab]) {
        return;
    }

    const category = currentConfig[activeTab];
    const header = document.createElement('div');
    header.className = 'mb-8 fade-in';
    header.innerHTML = `
        <div class="card p-6">
            <h2 class="text-xl font-semibold text-foreground mb-2">${category.name}</h2>
            <p class="text-muted-foreground">${category.description}</p>
        </div>
    `;
    contentContainer.appendChild(header);

    const grid = document.createElement('div');
    grid.className = 'grid grid-cols-1 gap-8 sm:grid-cols-2 xl:grid-cols-3 fade-in';

    Object.entries(category.variables).forEach(([varName, varConfig]) => {
        const card = createVariableCard(activeTab, varName, varConfig);
        grid.appendChild(card);
    });

    contentContainer.appendChild(grid);
    bindConfigurationInputs(contentContainer);
}

function createVariableCard(categoryId, varName, varConfig) {
    const card = document.createElement('div');
    card.className = 'card p-6 space-y-4 hover:shadow-lg transition-all duration-200';

    const isRequired = varConfig.required;
    const inputType = getInputType(varConfig.type);
    const currentValue = varConfig.current_value || '';

    card.innerHTML = `
        <div class="flex justify-between items-start">
            <div class="flex-1">
                <h3 class="font-medium text-foreground mb-1">${varName}</h3>
                <p class="text-sm text-muted-foreground">${varConfig.description}</p>
            </div>
            ${isRequired ? '<span class="badge badge-destructive ml-2 text-xs">Required</span>' : ''}
        </div>
        
        <div class="space-y-4">
            ${createInput(categoryId, varName, varConfig, currentValue, inputType)}
            ${varConfig.validation ? createValidationHint(varConfig.validation) : ''}
        </div>
    `;

    return card;
}

function getInputType(configType) {
    switch (configType) {
        case 'password':
            return 'password';
        case 'number':
            return 'number';
        case 'boolean':
            return 'checkbox';
        case 'url':
            return 'url';
        default:
            return 'text';
    }
}

function createInput(categoryId, varName, varConfig, currentValue, inputType) {
    const inputId = `${categoryId}_${varName}`;

    if (inputType === 'checkbox') {
        const checked = currentValue === 'true' ? 'checked' : '';
        return `
            <div class="flex items-center space-x-3">
                <div class="relative">
                    <input type="checkbox" id="${inputId}" name="${varName}" ${checked}
                           data-config-input data-category="${categoryId}" data-variable="${varName}"
                           class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary focus:ring-2 transition-colors">
                </div>
                <label for="${inputId}" class="text-sm font-medium text-foreground cursor-pointer">Enabled</label>
            </div>
        `;
    }

    const step = varConfig.validation?.step ? `step="${varConfig.validation.step}"` : '';
    const min = varConfig.validation?.min ? `min="${varConfig.validation.min}"` : '';
    const max = varConfig.validation?.max ? `max="${varConfig.validation.max}"` : '';

    return `
        <input type="${inputType}" id="${inputId}" name="${varName}" value="${currentValue}"
               ${step} ${min} ${max}
               data-config-input data-category="${categoryId}" data-variable="${varName}"
               class="input w-full"
               placeholder="Enter ${varName.toLowerCase()}...">
    `;
}

function createValidationHint(validation) {
    const hints = [];
    if (validation.min_length) hints.push(`Min length: ${validation.min_length}`);
    if (validation.min) hints.push(`Min: ${validation.min}`);
    if (validation.max) hints.push(`Max: ${validation.max}`);
    if (validation.pattern) hints.push('Must match required format');

    return hints.length > 0
        ? `<div class="flex items-center gap-2 text-xs text-muted-foreground">
                <i data-lucide="info" class="w-3 h-3"></i>
                <span>${hints.join(', ')}</span>
           </div>`
        : '';
}

function bindConfigurationInputs(container) {
    const inputs = container.querySelectorAll('[data-config-input]');

    inputs.forEach((input) => {
        const { category, variable } = input.dataset;
        if (!category || !variable) {
            return;
        }

        if (input.type === 'checkbox') {
            input.addEventListener('change', (event) => {
                updateConfigValue(category, variable, event.target.checked.toString());
            });
        } else {
            input.addEventListener('change', (event) => {
                updateConfigValue(category, variable, event.target.value);
            });
        }
    });
}

function bindServiceControls(container) {
    const buttons = container.querySelectorAll('[data-service][data-action]');

    buttons.forEach((button) => {
        const { service, action } = button.dataset;
        if (!service || !action) {
            return;
        }

        if (action === 'logs') {
            button.addEventListener('click', () => viewServiceLogs(service));
        } else {
            button.addEventListener('click', () => controlService(service, action));
        }
    });
}

function updateConfigValue(categoryId, varName, value) {
    if (!currentConfig[categoryId]) {
        currentConfig[categoryId] = { variables: {} };
    }
    if (!currentConfig[categoryId].variables) {
        currentConfig[categoryId].variables = {};
    }
    if (!currentConfig[categoryId].variables[varName]) {
        currentConfig[categoryId].variables[varName] = {};
    }

    currentConfig[categoryId].variables[varName].current_value = value;
}

function saveConfiguration() {
    try {
        const configToSave = {};

        Object.keys(currentConfig).forEach((categoryId) => {
            configToSave[categoryId] = {};
            const category = currentConfig[categoryId];

            if (category.variables) {
                Object.keys(category.variables).forEach((varName) => {
                    const variable = category.variables[varName];
                    configToSave[categoryId][varName] = variable.current_value;
                });
            }
        });

        fetch('/admin/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ config: configToSave })
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    showToast('Configuration saved successfully!', 'success');
                } else {
                    throw new Error(data.error || 'Failed to save configuration');
                }
            })
            .catch((error) => {
                showToast(`Failed to save configuration: ${error.message}`, 'error');
            });
    } catch (error) {
        showToast(`Failed to save configuration: ${error.message}`, 'error');
    }
}

function validateConfiguration() {
    fetch('/admin/api/validate')
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                let errorCount = 0;
                Object.values(data.validation).forEach((category) => {
                    Object.values(category).forEach((variable) => {
                        if (!variable.valid) {
                            errorCount += variable.errors.length;
                        }
                    });
                });

                if (errorCount === 0) {
                    showToast('Configuration validation passed!', 'success');
                } else {
                    showToast(`Configuration has ${errorCount} validation errors`, 'error');
                }
            } else {
                throw new Error(data.error);
            }
        })
        .catch((error) => {
            showToast(`Validation failed: ${error.message}`, 'error');
        });
}

function createBackup() {
    fetch('/admin/api/backup', {
        method: 'POST'
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                showToast('Configuration backup created successfully!', 'success');
            } else {
                throw new Error(data.error);
            }
        })
        .catch((error) => {
            showToast(`Backup failed: ${error.message}`, 'error');
        });
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');

    let bgColorClass;
    let textColorClass;
    let iconName;
    switch (type) {
        case 'success':
            bgColorClass = 'bg-success';
            textColorClass = 'text-success-foreground';
            iconName = 'check-circle';
            break;
        case 'error':
            bgColorClass = 'bg-destructive';
            textColorClass = 'text-destructive-foreground';
            iconName = 'x-circle';
            break;
        default:
            bgColorClass = 'bg-primary';
            textColorClass = 'text-primary-foreground';
            iconName = 'info';
            break;
    }

    toast.className = `${bgColorClass} ${textColorClass} px-4 py-4 rounded-lg shadow-lg border border-border/20 backdrop-blur-sm transition-all duration-300 transform translate-x-full flex items-center gap-4 min-w-[300px]`;
    toast.innerHTML = `
        <i data-lucide="${iconName}" class="w-4 h-4 flex-shrink-0"></i>
        <span class="text-sm font-medium">${message}</span>
    `;

    const container = document.getElementById('toast-container');
    container.appendChild(toast);

    lucide.createIcons();

    setTimeout(() => {
        toast.classList.remove('translate-x-full');
    }, 100);

    setTimeout(() => {
        toast.classList.add('translate-x-full');
        setTimeout(() => {
            if (container.contains(toast)) {
                container.removeChild(toast);
            }
        }, 300);
    }, 5000);
}

function renderOverviewContent(container) {
    container.innerHTML = `
        <div class="space-y-8">
            <div class="card p-6 fade-in">
                <div class="flex items-center gap-4 mb-6">
                    <div class="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                        <i data-lucide="monitor" class="w-5 h-5 text-primary"></i>
                    </div>
                    <div>
                        <h2 class="text-xl font-semibold text-foreground">System Overview</h2>
                        <p class="text-sm text-muted-foreground">Monitor and control system services</p>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 md:grid-cols-4 gap-8">
                    <div class="text-center p-4 bg-muted/50 rounded-lg">
                        <div class="text-2xl font-bold text-foreground">2</div>
                        <div class="text-sm text-muted-foreground">Services</div>
                    </div>
                    <div class="text-center p-4 bg-success/10 rounded-lg">
                        <div class="text-2xl font-bold text-success">Live</div>
                        <div class="text-sm text-muted-foreground">Monitoring</div>
                    </div>
                    <div class="text-center p-4 bg-primary/10 rounded-lg">
                        <div class="text-2xl font-bold text-primary">Active</div>
                        <div class="text-sm text-muted-foreground">Configuration</div>
                    </div>
                    <div class="text-center p-4 bg-warning/10 rounded-lg">
                        <div class="text-sm font-medium text-warning" id="last-updated">-</div>
                        <div class="text-sm text-muted-foreground">Last Updated</div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="card p-6 fade-in">
                    <div class="flex items-center justify-between mb-6">
                        <div class="flex items-center gap-4">
                            <div class="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                                <i data-lucide="shield" class="w-5 h-5 text-blue-500"></i>
                            </div>
                            <div>
                                <h3 class="font-semibold text-foreground">Wazuh Realtime Server</h3>
                                <p class="text-sm text-muted-foreground">Security monitoring service</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-4">
                            <div id="wazuh-status-indicator" class="status-unknown"></div>
                            <span id="wazuh-status-text" class="text-sm font-medium text-muted-foreground">Unknown</span>
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <div class="text-sm text-muted-foreground">
                            Monitors security events and provides real-time alerting capabilities.
                        </div>
                        <div class="flex flex-wrap gap-4">
                            <button id="start-wazuh-btn" data-service="wazuh_realtime" data-action="start" class="btn-success text-xs px-4 py-2 gap-2">
                                <i data-lucide="play" class="w-3 h-3"></i>Start
                            </button>
                            <button id="stop-wazuh-btn" data-service="wazuh_realtime" data-action="stop" class="btn-destructive text-xs px-4 py-2 gap-2">
                                <i data-lucide="stop" class="w-3 h-3"></i>Stop
                            </button>
                            <button id="restart-wazuh-btn" data-service="wazuh_realtime" data-action="restart" class="btn-secondary text-xs px-4 py-2 gap-2">
                                <i data-lucide="refresh-cw" class="w-3 h-3"></i>Restart
                            </button>
                            <button data-service="wazuh_realtime" data-action="logs" class="btn-secondary text-xs px-4 py-2 gap-2">
                                <i data-lucide="file-text" class="w-3 h-3"></i>Logs
                            </button>
                        </div>
                    </div>
                </div>

                <div class="card p-6 fade-in">
                    <div class="flex items-center justify-between mb-6">
                        <div class="flex items-center gap-4">
                            <div class="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
                                <i data-lucide="message-circle" class="w-5 h-5 text-green-500"></i>
                            </div>
                            <div>
                                <h3 class="font-semibold text-foreground">Telegram Bot</h3>
                                <p class="text-sm text-muted-foreground">Notification and reporting bot</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <div id="telegram-status-indicator" class="status-unknown"></div>
                            <span id="telegram-status-text" class="text-sm font-medium text-muted-foreground">Unknown</span>
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <div class="text-sm text-muted-foreground">
                            Provides automated reporting and notification services via Telegram.
                        </div>
                        <div class="flex flex-wrap gap-4">
                            <button id="start-telegram-btn" data-service="telegram_bot" data-action="start" class="btn-success text-xs px-4 py-2 gap-2">
                                <i data-lucide="play" class="w-3 h-3"></i>Start
                            </button>
                            <button id="stop-telegram-btn" data-service="telegram_bot" data-action="stop" class="btn-destructive text-xs px-4 py-2 gap-2">
                                <i data-lucide="stop" class="w-3 h-3"></i>Stop
                            </button>
                            <button id="restart-telegram-btn" data-service="telegram_bot" data-action="restart" class="btn-secondary text-xs px-4 py-2 gap-2">
                                <i data-lucide="refresh-cw" class="w-3 h-3"></i>Restart
                            </button>
                            <button data-service="telegram_bot" data-action="logs" class="btn-secondary text-xs px-4 py-2 gap-2">
                                <i data-lucide="file-text" class="w-3 h-3"></i>Logs
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    bindServiceControls(container);

    setTimeout(() => {
        lucide.createIcons();
        loadServicesStatus();
    }, 100);
}

function controlService(service, action) {
    fetch(`/admin/api/services/${service}/${action}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then((response) => response.json())
        .then((result) => {
            if (result.success) {
                showToast(`${service} service ${action}ed successfully`, 'success');
                setTimeout(loadServicesStatus, 2000);
            } else {
                showToast(`Failed to ${action} ${service} service: ${result.message}`, 'error');
            }
        })
        .catch((error) => {
            console.error(`Error controlling ${service} service:`, error);
            showToast(`Error controlling ${service} service`, 'error');
        });
}

function loadServicesStatus() {
    fetch('/admin/api/services/status')
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                const wazuhStatus = data.services.wazuh_realtime?.running ? 'running' : 'stopped';
                const telegramStatus = data.services.telegram_bot?.running ? 'running' : 'stopped';

                updateServiceStatus('wazuh_realtime', wazuhStatus);
                updateServiceStatus('telegram_bot', telegramStatus);

                const lastUpdated = document.getElementById('last-updated');
                if (lastUpdated) {
                    lastUpdated.textContent = new Date().toLocaleTimeString();
                }

                console.log('Services status loaded:', {
                    wazuh: wazuhStatus,
                    telegram: telegramStatus,
                    raw_data: data.services
                });
            }
        })
        .catch((error) => {
            console.error('Error loading services status:', error);
        });
}

function updateServiceStatus(service, status) {
    const serviceMap = {
        wazuh_realtime: 'wazuh',
        telegram_bot: 'telegram'
    };

    const uiServiceName = serviceMap[service] || service;

    const statusIndicator = document.getElementById(`${uiServiceName}-status-indicator`);
    const statusText = document.getElementById(`${uiServiceName}-status-text`);
    const startBtn = document.getElementById(`start-${uiServiceName}-btn`);
    const stopBtn = document.getElementById(`stop-${uiServiceName}-btn`);
    const restartBtn = document.getElementById(`restart-${uiServiceName}-btn`);

    if (statusIndicator && statusText) {
        if (status === 'running') {
            statusIndicator.className = 'status-running';
            statusText.textContent = 'Running';
            statusText.className = 'text-sm font-medium text-success';
            if (startBtn) startBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
            if (restartBtn) restartBtn.disabled = false;
        } else {
            statusIndicator.className = 'status-stopped';
            statusText.textContent = 'Stopped';
            statusText.className = 'text-sm font-medium text-destructive';
            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
            if (restartBtn) restartBtn.disabled = true;
        }
    }
}

function viewServiceLogs(service) {
    fetch(`/admin/api/services/${service}/logs`)
        .then((response) => response.json())
        .then((result) => {
            if (result.success) {
                const logModal = document.createElement('div');
                logModal.className = 'fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4';
                logModal.innerHTML = `
                    <div class="card max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                        <div class="flex justify-between items-center p-6 border-b border-border">
                            <div class="flex items-center gap-4">
                                <div class="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                                    <i data-lucide="file-text" class="w-4 h-4 text-primary"></i>
                                </div>
                                <div>
                                    <h3 class="text-lg font-semibold text-foreground">Service Logs</h3>
                                    <p class="text-sm text-muted-foreground">${service}</p>
                                </div>
                            </div>
                            <button class="btn-secondary w-8 h-8 p-0 rounded-full" data-action="close-log-modal">
                                <i data-lucide="x" class="w-4 h-4"></i>
                            </button>
                        </div>
                        
                        <div class="flex-1 overflow-y-auto bg-slate-950 text-green-400 p-6 font-mono text-sm">
                            <pre class="whitespace-pre-wrap">${result.logs || 'No logs available'}</pre>
                        </div>
                        
                        <div class="p-6 border-t border-border bg-muted/20">
                            <div class="flex items-center justify-between">
                                <div class="text-sm text-muted-foreground">
                                    <div class="flex items-center gap-2">
                                        <i data-lucide="folder" class="w-4 h-4"></i>
                                        <span>Log file: ${result.log_file || 'N/A'}</span>
                                    </div>
                                </div>
                                <div class="flex gap-4">
                                    <button class="btn-primary gap-2" data-action="refresh-log-modal">
                                        <i data-lucide="refresh-cw" class="w-4 h-4"></i>
                                        Refresh
                                    </button>
                                    <button class="btn-secondary" data-action="close-log-modal">
                                        Close
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

                document.body.appendChild(logModal);
                logModal.dataset.service = service;

                logModal.querySelectorAll('[data-action="close-log-modal"]').forEach((btn) => {
                    btn.addEventListener('click', () => logModal.remove());
                });

                const refreshButton = logModal.querySelector('[data-action="refresh-log-modal"]');
                if (refreshButton) {
                    refreshButton.addEventListener('click', () => refreshServiceLogs(service, logModal));
                }

                setTimeout(() => lucide.createIcons(), 100);
            } else {
                showToast(`Failed to get logs for ${service}: ${result.error}`, 'error');
            }
        })
        .catch((error) => {
            console.error(`Error getting logs for ${service}:`, error);
            showToast(`Error getting logs for ${service}`, 'error');
        });
}

function refreshServiceLogs(service, modal) {
    fetch(`/admin/api/services/${service}/logs`)
        .then((response) => response.json())
        .then((result) => {
            if (result.success) {
                const logsContainer = modal.querySelector('pre');
                logsContainer.textContent = result.logs || 'No logs available';
            }
        })
        .catch((error) => {
            console.error(`Error refreshing logs for ${service}:`, error);
        });
}

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();

    const validateButton = document.getElementById('validate-config-btn');
    if (validateButton) {
        validateButton.addEventListener('click', () => validateConfiguration());
    }

    const backupButton = document.getElementById('create-backup-btn');
    if (backupButton) {
        backupButton.addEventListener('click', () => createBackup());
    }

    const saveButton = document.getElementById('save-config-btn');
    if (saveButton) {
        saveButton.addEventListener('click', () => saveConfiguration());
    }

    loadConfiguration();
    loadServicesStatus();
});
