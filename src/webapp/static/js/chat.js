// AISOC Chat Interface Logic

// Global variables
let currentSessionId = null;
let isLoading = false;
let sidebarVisible = true;

function refreshIcons(root) {
    if (typeof lucide === 'undefined') {
        return;
    }
    try {
        if (root) {
            lucide.createIcons({ root });
        } else {
            lucide.createIcons();
        }
    } catch (error) {
        console.warn('Unable to refresh icons:', error);
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    loadSessions();
    loadStats();

    const searchInput = document.getElementById('searchSessions');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(searchSessions, 300));
    }

    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('input', function () {
            const sendButton = document.getElementById('sendButton');
            if (sendButton) {
                sendButton.disabled = this.value.trim() === '';
            }
        });
    }

    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
            event.preventDefault();
            toggleSidebar();
        }
    });

    refreshIcons();
});

// Session Management
async function createNewSession() {
    try {
        const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });

        const data = await response.json();
        if (data.session_id) {
            currentSessionId = data.session_id;
            const titleEl = document.getElementById('currentSessionTitle');
            if (titleEl) {
                titleEl.textContent = 'New Chat';
            }
            clearMessages();
            loadSessions();
            loadStats();
        }
    } catch (error) {
        console.error('Error creating session:', error);
    }
}

async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();

        const sessionsList = document.getElementById('sessionsList');
        if (!sessionsList) {
            return;
        }

        sessionsList.innerHTML = '';

        if (data.sessions && data.sessions.length > 0) {
            data.sessions.forEach((session) => {
                sessionsList.appendChild(createSessionElement(session));
            });
        } else {
            sessionsList.innerHTML = '<div class="text-center text-muted-foreground py-8">No chat sessions yet. Start a new conversation!</div>';
        }
        refreshIcons(sessionsList);
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

function createSessionElement(session) {
    const div = document.createElement('div');
    div.className = `sidebar-menu-item group relative flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm outline-none ring-sidebar-ring transition-[width,height,padding] hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 active:bg-sidebar-accent active:text-sidebar-accent-foreground disabled:pointer-events-none disabled:opacity-50 group-has-[[data-sidebar=menu-action]]/menu-item:pr-8 aria-disabled:pointer-events-none aria-disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground cursor-pointer ${currentSessionId === session.id ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium' : ''}`;
    div.onclick = () => loadSession(session.id);

    div.innerHTML = `
        <div class="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
            <i data-lucide="message-circle" class="size-4"></i>
        </div>
        <div class="grid flex-1 text-left text-sm leading-tight">
            <span class="truncate font-semibold">${session.title}</span>
            <span class="truncate text-xs text-sidebar-foreground/70">${session.message_count} messages • ${formatDate(session.updated_at)}</span>
        </div>
        <div class="sidebar-menu-action absolute right-1 top-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <div class="flex gap-1">
                <button onclick="event.stopPropagation(); renameSession('${session.id}', '${session.title}')" class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-xs font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-6 w-6">
                    <i data-lucide="edit-2" class="size-3"></i>
                </button>
                <button onclick="event.stopPropagation(); deleteSession('${session.id}')" class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-xs font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-destructive hover:text-destructive-foreground h-6 w-6">
                    <i data-lucide="trash-2" class="size-3"></i>
                </button>
            </div>
        </div>
    `;

    return div;
}

async function loadSession(sessionId) {
    try {
        currentSessionId = sessionId;
        clearMessages();

        const response = await fetch(`/api/sessions/${sessionId}`);
        const data = await response.json();

        if (data.session && data.messages) {
            const titleEl = document.getElementById('currentSessionTitle');
            if (titleEl) {
                titleEl.textContent = data.session.title;
            }

            data.messages.forEach((message) => {
                if (message.role !== 'system') {
                    displayMessage(message.role, message.content, message.tools_used, message.thinking_process);
                }
            });

            scrollToBottom();
        }

        loadSessions();
    } catch (error) {
        console.error('Error loading session:', error);
    }
}

async function renameSession(sessionId, currentTitle) {
    const newTitle = prompt('Enter new session title:', currentTitle);
    if (!newTitle || newTitle === currentTitle) {
        return;
    }

    try {
        const response = await fetch(`/api/sessions/${sessionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ title: newTitle })
        });

        if (response.ok) {
            if (currentSessionId === sessionId) {
                const titleEl = document.getElementById('currentSessionTitle');
                if (titleEl) {
                    titleEl.textContent = newTitle;
                }
            }
            loadSessions();
        }
    } catch (error) {
        console.error('Error renaming session:', error);
    }
}

async function deleteSession(sessionId) {
    if (!confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                const titleEl = document.getElementById('currentSessionTitle');
                if (titleEl) {
                    titleEl.textContent = 'Select a chat session';
                }
                clearMessages();
            }
            loadSessions();
            loadStats();
        }
    } catch (error) {
        console.error('Error deleting session:', error);
    }
}

async function searchSessions() {
    const input = document.getElementById('searchSessions');
    if (!input) {
        return;
    }

    const query = input.value.trim();
    if (!query) {
        loadSessions();
        return;
    }

    try {
        const response = await fetch(`/api/sessions/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        const sessionsList = document.getElementById('sessionsList');
        if (!sessionsList) {
            return;
        }

        sessionsList.innerHTML = '';

        if (data.sessions && data.sessions.length > 0) {
            data.sessions.forEach((session) => {
                sessionsList.appendChild(createSessionElement(session));
            });
        } else {
            sessionsList.innerHTML = '<div class="text-center text-muted-foreground py-8">No sessions found matching your search.</div>';
        }
        refreshIcons(sessionsList);
    } catch (error) {
        console.error('Error searching sessions:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        const sessionsEl = document.getElementById('totalSessions');
        const messagesEl = document.getElementById('totalMessages');
        if (sessionsEl) {
            sessionsEl.textContent = data.total_sessions || 0;
        }
        if (messagesEl) {
            messagesEl.textContent = data.total_messages || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Chat functionality
async function sendMessage() {
    const input = document.getElementById('messageInput');
    if (!input) {
        return;
    }

    const message = input.value.trim();
    if (!message || isLoading) {
        return;
    }

    if (!currentSessionId) {
        await createNewSession();
    }

    isLoading = true;
    input.value = '';
    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.disabled = true;
    }

    displayMessage('user', message);
    scrollToBottom();

    const loadingId = `loading-${Date.now()}`;
    displayMessage('assistant', '', [], null, loadingId, true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                session_id: currentSessionId
            })
        });

        const data = await response.json();

        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }

        if (data.error) {
            displayMessage('assistant', `Error: ${data.error}`, [], null, null, false, true);
        } else if (data.response) {
            displayMessage('assistant', data.response, data.tool_calls, data.thinking);
            if (data.session_id && data.session_id !== currentSessionId) {
                currentSessionId = data.session_id;
                loadSessions();
                loadStats();
            }
        } else {
            displayMessage('assistant', 'Tool executed but no response content available.', data.tool_calls || [], data.thinking);
        }

        scrollToBottom();
    } catch (error) {
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }

        console.error('Error sending message:', error);
        displayMessage('assistant', `Error: ${error.message}`, [], null, null, false, true);
        scrollToBottom();
    }

    isLoading = false;
}

function displayMessage(role, content, toolCalls = [], thinking = null, messageId = null, isLoading = false, isError = false) {
    const messagesDiv = document.getElementById('messages');
    if (!messagesDiv) {
        return;
    }

    const messageDiv = document.createElement('div');
    if (messageId) {
        messageDiv.id = messageId;
    }

    messageDiv.className = `w-full flex gap-4 px-4 ${role === 'user' ? 'justify-end' : 'justify-start'}`;

    if (role === 'user') {
        messageDiv.innerHTML = `
            <div class="flex flex-col gap-2 max-w-[80%]">
                <div class="rounded-2xl bg-slate-950 text-white px-4 py-3 shadow-sm">
                    <div class="text-sm">
                        ${markdownToHTML(content)}
                    </div>
                </div>
            </div>
            <div class="w-8 h-8 rounded-full bg-slate-950 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                <i data-lucide="user" class="w-4 h-4"></i>
            </div>
        `;
    } else {
        let messageContent = '';

        if (isLoading) {
            messageContent = `
                <div class="rounded-2xl bg-card border border-border px-4 py-3 shadow-sm">
                    <div class="flex items-center gap-4 text-muted-foreground">
                        <div class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                        <span class="text-sm">AI is thinking...</span>
                    </div>
                </div>
            `;
        } else {
            const contentSections = [];

            if (thinking) {
                contentSections.push(createThinkingSection(thinking));
            }

            if (toolCalls && toolCalls.length > 0) {
                toolCalls.forEach((tool, index) => {
                    const toolId = `tool-${Date.now()}-${index}`;
                    contentSections.push(`
                        <div class="border border-border rounded-lg overflow-hidden mb-2 transition-all hover:border-primary/50 hover:shadow-md">
                            <div class="bg-slate-950 text-white px-4 py-3 cursor-pointer flex items-center gap-2 hover:bg-slate-800 transition-colors" onclick="toggleTool('${toolId}')">
                                <i data-lucide="wrench" class="w-4 h-4 flex-shrink-0"></i>
                                <span class="font-medium flex-1 text-sm">🔧 Executed: ${tool.name}</span>
                                <i id="${toolId}-icon" data-lucide="chevron-down" class="w-4 h-4 transition-transform"></i>
                            </div>
                            <div id="${toolId}" class="tool-content collapsed bg-card border-t border-border p-4">
                                <div class="space-y-3">
                                    <div>
                                        <h4 class="text-sm font-semibold mb-2 text-foreground">Parameters:</h4>
                                        <div class="bg-muted rounded-md p-3 border">
                                            <pre class="text-xs text-muted-foreground overflow-x-auto">${JSON.stringify(tool.arguments, null, 2)}</pre>
                                        </div>
                                    </div>
                                    <div>
                                        <h4 class="text-sm font-semibold mb-2 text-foreground">Result:</h4>
                                        <div class="bg-muted rounded-md p-3 max-h-48 overflow-y-auto border">
                                            <pre class="text-xs whitespace-pre-wrap text-muted-foreground">${JSON.stringify(tool.result, null, 2)}</pre>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `);
                });
            }

            if (content) {
                const bgClass = isError ? 'bg-destructive/10 border-destructive/20' : 'bg-card border-border';
                const textClass = isError ? 'text-destructive' : 'text-card-foreground';

                contentSections.push(`
                    <div class="rounded-2xl border ${bgClass} px-4 py-3 shadow-sm">
                        <div class="text-sm ${textClass}">
                            ${markdownToHTML(content)}
                        </div>
                    </div>
                `);
            }

            messageContent = `<div class="space-y-2">${contentSections.join('')}</div>`;
        }

        messageDiv.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-muted text-muted-foreground flex items-center justify-center flex-shrink-0 shadow-sm border border-border">
                <i data-lucide="bot" class="w-4 h-4"></i>
            </div>
            <div class="flex-1 min-w-0 max-w-full">
                ${messageContent}
            </div>
        `;
    }

    messagesDiv.appendChild(messageDiv);
    refreshIcons(messageDiv);
}

function createThinkingSection(thinking) {
    const thinkingId = `thinking-${Date.now()}`;
    return `
        <div class="collapsible rounded-lg border border-border" data-state="closed">
            <button type="button" class="collapsible-trigger flex w-full items-center justify-between p-3 text-sm font-medium hover:bg-muted/50 focus:bg-muted focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 [&[data-state=open]>svg]:rotate-180" onclick="toggleThinking('${thinkingId}')">
                <div class="flex items-center gap-2">
                    <i data-lucide="brain" class="h-4 w-4 text-muted-foreground"></i>
                    <span>🤔 Thinking Process</span>
                </div>
                <i id="${thinkingId}-icon" data-lucide="chevron-down" class="h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200"></i>
            </button>
            <div id="${thinkingId}" class="collapsible-content overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down" data-state="closed">
                <div class="border-t p-4 pt-3">
                    <div class="text-sm text-muted-foreground whitespace-pre-wrap">
${thinking}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Utility functions
function clearMessages() {
    const container = document.getElementById('messages');
    if (container) {
        container.innerHTML = '';
    }
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function toggleTool(toolId) {
    const content = document.getElementById(toolId);
    const icon = document.getElementById(`${toolId}-icon`);

    if (!content || !icon) {
        return;
    }

    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.style.transform = 'rotate(180deg)';
    } else {
        content.classList.add('collapsed');
        icon.style.transform = 'rotate(0deg)';
    }
}

function toggleThinking(thinkingId) {
    const content = document.getElementById(thinkingId);
    const icon = document.getElementById(`${thinkingId}-icon`);

    if (!content || !icon) {
        return;
    }

    if (content.classList.contains('thinking-content')) {
        if (content.classList.contains('collapsed')) {
            content.classList.remove('collapsed');
            icon.style.transform = 'rotate(180deg)';
        } else {
            content.classList.add('collapsed');
            icon.style.transform = 'rotate(0deg)';
        }
        return;
    }

    const trigger = content.parentElement ? content.parentElement.querySelector('.collapsible-trigger') : null;
    const isOpen = content.getAttribute('data-state') === 'open';

    if (isOpen) {
        content.setAttribute('data-state', 'closed');
        content.style.height = '0';
        if (trigger) {
            trigger.setAttribute('data-state', 'closed');
        }
        icon.style.transform = 'rotate(0deg)';
    } else {
        content.setAttribute('data-state', 'open');
        content.style.height = 'auto';
        if (trigger) {
            trigger.setAttribute('data-state', 'open');
        }
        icon.style.transform = 'rotate(180deg)';
    }
}

function markdownToHTML(text) {
    return formatMessage(text);
}

function formatMessage(content) {
    const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
    let processedText = content;
    const thinkingSections = [];

    let match;
    while ((match = thinkRegex.exec(content)) !== null) {
        thinkingSections.push(match[1].trim());
        processedText = processedText.replace(match[0], `__THINKING_PLACEHOLDER_${thinkingSections.length - 1}__`);
    }

    processedText = processedText
        .replace(/```(\w+)?\n([\s\S]*?)```/g, (full, lang, code) => {
            const language = lang ? `<span class="code-lang text-xs bg-slate-950 text-white px-2 py-1 rounded-t-md">${lang}</span>` : '';
            return `<div class="code-block bg-muted border rounded-md my-2 overflow-hidden">${language}<div class="p-3"><pre class="text-sm overflow-x-auto"><code>${escapeHtml(code.trim())}</code></pre></div></div>`;
        })
        .replace(/```([\s\S]*?)```/g, '<div class="code-block bg-muted border rounded-md p-3 my-2 overflow-x-auto"><pre class="text-sm"><code>$1</code></pre></div>')
        .replace(/`([^`]+)`/g, (full, code) => `<code class="bg-muted text-muted-foreground px-2 py-1 rounded text-xs font-mono">${escapeHtml(code)}</code>`)
        .replace(/^###### (.*)$/gm, '<h6 class="text-xs font-medium mt-2 mb-1">$1</h6>')
        .replace(/^##### (.*)$/gm, '<h5 class="text-sm font-medium mt-2 mb-1">$1</h5>')
        .replace(/^#### (.*)$/gm, '<h4 class="text-base font-semibold mt-3 mb-2">$1</h4>')
        .replace(/^### (.*)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
        .replace(/^## (.*)$/gm, '<h2 class="text-xl font-semibold mt-6 mb-3">$1</h2>')
        .replace(/^# (.*)$/gm, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
        .replace(/^---+$/gm, '<hr class="my-4 border-border">')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>')
        .replace(/\*(.*?)\*/g, '<em class="italic">$1</em>')
        .replace(/\n/g, '<span class="line-gap"></span>')
        .replace(/^- (.*)$/gm, '<li class="list-item-bullet">$1</li>')
        .replace(/^[0-9]+\. (.*)$/gm, '<li class="list-item-number">$1</li>');

    processedText = processMarkdownTables(processedText);

    processedText = processedText.replace(/(<li class="list-item-bullet"[^>]*>.*?<\/li>)(<span[^>]*><\/span><li class="list-item-bullet"[^>]*>.*?<\/li>)*/g, (match) => {
        return '<ul class="my-1 space-y-0 list-disc pl-6">' + match.replace(/<span[^>]*><\/span>/g, '').replace(/class="list-item-bullet"/g, 'class="mb-0"') + '</ul>';
    });

    processedText = processedText.replace(/(<li class="list-item-number"[^>]*>.*?<\/li>)(<span[^>]*><\/span><li class="list-item-number"[^>]*>.*?<\/li>)*/g, (match) => {
        return '<ol class="my-1 space-y-0 list-decimal pl-6">' + match.replace(/<span[^>]*><\/span>/g, '').replace(/class="list-item-number"/g, 'class="mb-0"') + '</ol>';
    });

    thinkingSections.forEach((thinking, index) => {
        const thinkingId = `thinking-auto-${Date.now()}-${index}`;
        const thinkingHtml = `
            <div class="border border-border rounded-lg overflow-hidden mb-2 transition-all hover:border-primary hover:shadow-sm">
                <div class="bg-muted text-muted-foreground px-4 py-3 cursor-pointer flex items-center gap-2 hover:bg-muted/80 transition-colors" onclick="toggleThinking('${thinkingId}')">
                    <i data-lucide="brain" class="w-4 h-4 flex-shrink-0"></i>
                    <span class="font-medium flex-1 text-sm">🤔 Thinking Process</span>
                    <i id="${thinkingId}-icon" data-lucide="chevron-down" class="w-4 h-4 transition-transform"></i>
                </div>
                <div id="${thinkingId}" class="thinking-content collapsed bg-card border-t border-border p-4">
                    <div class="prose prose-sm max-w-full text-foreground">
                        ${formatMessage(thinking)}
                    </div>
                </div>
            </div>
        `;
        processedText = processedText.replace(`__THINKING_PLACEHOLDER_${index}__`, thinkingHtml);
    });

    return processedText;
}

function processMarkdownTables(text) {
    const lines = text.split('<span class="line-gap"></span>');
    const result = [];
    let i = 0;

    while (i < lines.length) {
        const line = lines[i].trim();

        if (line.includes('|') && lines[i + 1] && lines[i + 1].trim().match(/^\|[\s\-|]+\|$/)) {
            const tableLines = [];
            tableLines.push(line);
            tableLines.push(lines[i + 1]);
            i += 2;

            while (i < lines.length && lines[i].trim().includes('|') && !lines[i].trim().match(/^\|[\s\-|]+\|$/)) {
                tableLines.push(lines[i].trim());
                i++;
            }

            result.push(convertTableToHTML(tableLines));
        } else {
            result.push(line);
            i++;
        }
    }

    return result.join('<span class="line-gap"></span>');
}

function convertTableToHTML(tableLines) {
    if (tableLines.length < 2) {
        return tableLines.join('\n');
    }

    const header = tableLines[0];
    const rows = tableLines.slice(2);

    const headerCells = header.split('|').map((cell) => cell.trim()).filter((cell) => cell !== '');

    const bodyRows = rows.map((row) => row.split('|').map((cell) => cell.trim()).filter((cell) => cell !== ''));

    let html = `
        <div class="table-container my-4 overflow-x-auto border border-border rounded-lg">
            <table class="w-full text-sm">
                <thead class="bg-muted/50">
                    <tr>
    `;

    headerCells.forEach((cell) => {
        html += `<th class="px-3 py-2 text-left font-medium border-b border-border">${cell}</th>`;
    });

    html += `
                    </tr>
                </thead>
                <tbody>
    `;

    bodyRows.forEach((row, rowIndex) => {
        html += `<tr class="${rowIndex % 2 === 0 ? 'bg-card' : 'bg-muted/20'}">`;
        row.forEach((cell) => {
            html += `<td class="px-3 py-2 border-b border-border">${cell}</td>`;
        });
        html += '</tr>';
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        if (!statusDot || !statusText) {
            return;
        }

        const fastmcpOk = data.fastmcp === 'connected';

        if (fastmcpOk) {
            statusDot.className = 'w-2 h-2 rounded-full bg-green-500';
            statusText.textContent = 'MCP operational';
            statusText.className = 'text-green-600';
        } else {
            statusDot.className = 'w-2 h-2 rounded-full bg-red-500';
            statusText.textContent = 'MCP connection issues';
            statusText.className = 'text-red-600';
        }

        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        if (messageInput && sendButton) {
            sendButton.disabled = messageInput.value.trim() === '';
        }
    } catch (error) {
        console.error('Status check failed:', error);
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        if (statusDot && statusText) {
            statusDot.className = 'w-2 h-2 rounded-full bg-red-500';
            statusText.textContent = 'Status check failed';
            statusText.className = 'text-red-600';
        }

        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        if (messageInput && sendButton) {
            sendButton.disabled = messageInput.value.trim() === '';
        }
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) {
        return 'Today';
    }
    if (diffDays === 2) {
        return 'Yesterday';
    }
    if (diffDays <= 7) {
        return `${diffDays - 1} days ago`;
    }
    return date.toLocaleDateString();
}

function debounce(func, wait) {
    let timeout;
    return function debounced(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) {
        return;
    }

    const mainContent = document.querySelector('.sidebar-inset');
    const isOpen = sidebar.getAttribute('data-state') === 'open';

    if (isOpen) {
        sidebar.setAttribute('data-state', 'closed');
        sidebar.style.width = '0';
        sidebar.style.minWidth = '0';
        sidebar.style.opacity = '0';
        sidebar.style.pointerEvents = 'none';
        sidebar.style.borderRight = 'none';
        if (mainContent) {
            mainContent.style.marginLeft = '0';
        }
        sidebarVisible = false;
    } else {
        sidebar.setAttribute('data-state', 'open');
        sidebar.style.width = '16rem';
        sidebar.style.minWidth = '16rem';
        sidebar.style.opacity = '1';
        sidebar.style.pointerEvents = 'auto';
        sidebar.style.borderRight = '1px solid hsl(var(--border))';
        if (mainContent) {
            mainContent.style.marginLeft = '16rem';
        }
        sidebarVisible = true;
    }

    document.querySelectorAll('.sidebar-trigger').forEach((button) => {
        const icon = button.querySelector('i');
        if (icon) {
            icon.setAttribute('data-lucide', sidebarVisible ? 'panel-left-close' : 'panel-left-open');
        }
        button.title = sidebarVisible ? 'Close Sidebar' : 'Open Sidebar';
    });

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function toggleToolContent(toolId) {
    const content = document.getElementById(`tool-content-${toolId}`);
    const button = document.querySelector(`[onclick="toggleToolContent('${toolId}')"]`);
    if (!content || !button) {
        return;
    }

    const icon = button.querySelector('i');
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        content.style.display = 'block';
        if (icon) {
            icon.setAttribute('data-lucide', 'chevron-down');
        }
        button.title = 'Collapse';
    } else {
        content.classList.add('collapsed');
        content.style.display = 'none';
        if (icon) {
            icon.setAttribute('data-lucide', 'chevron-right');
        }
        button.title = 'Expand';
    }

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function toggleThinkingContent(thinkingId) {
    const content = document.getElementById(`thinking-content-${thinkingId}`);
    const button = document.querySelector(`[onclick="toggleThinkingContent('${thinkingId}')"]`);
    if (!content || !button) {
        return;
    }

    const icon = button.querySelector('i');
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        content.style.display = 'block';
        if (icon) {
            icon.setAttribute('data-lucide', 'chevron-down');
        }
        button.title = 'Collapse';
    } else {
        content.classList.add('collapsed');
        content.style.display = 'none';
        if (icon) {
            icon.setAttribute('data-lucide', 'chevron-right');
        }
        button.title = 'Expand';
    }

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

async function logout() {
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
            console.error('Logout failed');
            alert('Logout failed. Please try again.');
        }
    } catch (error) {
        console.error('Logout error:', error);
        alert('Logout failed. Please try again.');
    }
}

// Status check removed - no periodic checks
