/* ================================
   APP - Main application controller
   Wires up all components
   ================================ */

const App = (() => {
    const state = {
        currentView: 'chat',
        temperature: 0.7,
        maxTokens: 512,
        topP: 0.9
    };
    
    // ==========================================
    // INITIALIZATION
    // ==========================================
    async function init() {
        try {
            await Storage.init();
            Neural.init();
            await Storage.requestPersistent();
            
            // Load saved settings
            state.temperature = await Storage.settings.get('temperature', 0.7);
            state.maxTokens = await Storage.settings.get('maxTokens', 512);
            state.topP = await Storage.settings.get('topP', 0.9);
            
            _bindEvents();
            _initSidebar();
            _initChat();
            _initModels();
            _initSandbox();
            _initTools();
            _initSettings();
            _initFiles();
            
            await Chat.newChat();
            await _refreshHistory();
            await _refreshModels();
            await _refreshFiles();
            await _refreshStorage();
            
            UI.refreshIcons();
            
            UI.toast('Neural.AI ready • Fully offline', 'success', 2500);
            
            console.log('%c🧠 Neural.AI initialized', 'color:#8b5cf6;font-weight:bold;font-size:14px');
        } catch (err) {
            console.error('Init error:', err);
            UI.toast('Startup error: ' + err.message, 'error');
        }
    }
    
    // ==========================================
    // EVENTS
    // ==========================================
    function _bindEvents() {
        // Menu toggle
        document.getElementById('menuBtn').addEventListener('click', _openSidebar);
        document.getElementById('closeSidebar').addEventListener('click', _closeSidebar);
        document.getElementById('sidebarOverlay').addEventListener('click', _closeSidebar);
        
        // Navigation
        document.querySelectorAll('.nav-item[data-view]').forEach(item => {
            item.addEventListener('click', () => {
                _switchView(item.dataset.view);
                if (window.innerWidth < 1024) _closeSidebar();
            });
        });
        
        // New chat
        document.getElementById('newChatBtn').addEventListener('click', async () => {
            await Chat.newChat();
            _renderMessages();
            _switchView('chat');
            await _refreshHistory();
            if (window.innerWidth < 1024) _closeSidebar();
        });
        
        // Clear chat
        document.getElementById('clearChatBtn').addEventListener('click', () => {
            UI.confirm('Clear this chat?', async () => {
                await Chat.newChat();
                _renderMessages();
                UI.toast('Chat cleared', 'info');
            });
        });
        
        // Export chat
        document.getElementById('exportChatBtn').addEventListener('click', () => {
            const md = Chat.exportChat('markdown');
            UI.downloadText(md, `chat_${Date.now()}.md`);
            UI.toast('Chat exported!', 'success');
        });
    }
    
    // ==========================================
    // SIDEBAR
    // ==========================================
    function _initSidebar() {
        // Auto-open sidebar on desktop
        if (window.innerWidth >= 1024) {
            document.getElementById('sidebar').classList.add('open');
        }
    }
    
    function _openSidebar() {
        document.getElementById('sidebar').classList.add('open');
        document.getElementById('sidebarOverlay').classList.add('active');
    }
    
    function _closeSidebar() {
        if (window.innerWidth < 1024) {
            document.getElementById('sidebar').classList.remove('open');
            document.getElementById('sidebarOverlay').classList.remove('active');
        }
    }
    
    function _switchView(view) {
        state.currentView = view;
        
        // Update nav
        document.querySelectorAll('.nav-item').forEach(el => {
            el.classList.toggle('active', el.dataset.view === view);
        });
        
        // Update views
        document.querySelectorAll('.view').forEach(el => {
            el.classList.toggle('active', el.id === `view-${view}`);
        });
        
        // Update top title
        const titles = { chat: 'Chat', models: 'My Models', sandbox: 'Code Sandbox', tools: 'AI Tools', files: 'Files', settings: 'Settings', about: 'About' };
        document.getElementById('topTitle').textContent = titles[view] || view;
        
        // Refresh view-specific data
        if (view === 'models') _refreshModels();
        else if (view === 'files') _refreshFiles();
        else if (view === 'settings') _refreshStorage();
    }
    
    async function _refreshHistory() {
        const container = document.getElementById('chatHistory');
        const chats = await Chat.getAll();
        
        if (chats.length === 0) {
            container.innerHTML = '<div class="history-empty">No chats yet</div>';
            return;
        }
        
        container.innerHTML = chats.slice(0, 10).map(c => `
            <div class="history-item ${c.id === Chat.currentId ? 'active' : ''}" data-chat-id="${c.id}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span class="history-title">${c.title}</span>
                <button class="history-delete" data-delete-id="${c.id}">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 01-2 2H9a2 2 0 01-2-2L5 6"/></svg>
                </button>
            </div>
        `).join('');
        
        container.querySelectorAll('.history-item').forEach(el => {
            el.addEventListener('click', async (e) => {
                if (e.target.closest('.history-delete')) return;
                const id = el.dataset.chatId;
                await Chat.loadChat(id);
                _renderMessages();
                _switchView('chat');
                await _refreshHistory();
                if (window.innerWidth < 1024) _closeSidebar();
            });
        });
        
        container.querySelectorAll('.history-delete').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.dataset.deleteId;
                await Chat.deleteChat(id);
                await _refreshHistory();
                if (id === Chat.currentId) {
                    await Chat.newChat();
                    _renderMessages();
                }
                UI.toast('Chat deleted', 'info');
            });
        });
    }
    
    // ==========================================
    // CHAT
    // ==========================================
    function _initChat() {
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        
        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });
        
        // Send on Enter (Shift+Enter for newline)
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                _sendMessage();
            }
        });
        
        sendBtn.addEventListener('click', _sendMessage);
        
        // Suggestion cards
        document.querySelectorAll('.suggestion-card').forEach(card => {
            card.addEventListener('click', () => {
                input.value = card.dataset.prompt;
                input.focus();
                _sendMessage();
            });
        });
        
        // Command hints
        document.querySelectorAll('.hint-badge').forEach(badge => {
            badge.addEventListener('click', () => {
                input.value = badge.dataset.cmd + ' ';
                input.focus();
            });
        });
        
        // Attach button
        document.getElementById('attachBtn').addEventListener('click', () => {
            const file = document.createElement('input');
            file.type = 'file';
            file.accept = 'image/*,.txt,.md,.json,.csv';
            file.onchange = (e) => {
                const f = e.target.files[0];
                if (f) _handleAttachment(f);
            };
            file.click();
        });
        
        // Voice button
        document.getElementById('voiceBtn').addEventListener('click', _toggleVoice);
    }
    
    async function _sendMessage() {
        const input = document.getElementById('chatInput');
        const text = input.value.trim();
        if (!text) return;
        if (Chat.isGenerating) {
            UI.toast('Still generating...', 'warning');
            return;
        }
        
        // Hide welcome
        const welcome = document.getElementById('welcomeScreen');
        if (welcome) welcome.remove();
        
        // Clear input
        input.value = '';
        input.style.height = 'auto';
        
        // Add user message
        Chat.addMessage('user', text);
        _renderMessages();
        _scrollToBottom();
        
        // Show typing indicator
        _showTyping();
        
        try {
            // Process
            const result = await Chat.processInput(text, {
                temperature: state.temperature,
                maxTokens: state.maxTokens
            });
            
            _hideTyping();
            
            // Add response
            Chat.addMessage('assistant', result.content, result);
            _renderMessages();
            _scrollToBottom();
            
            // Save
            await Chat.save();
            await _refreshHistory();
            await _refreshFiles();
        } catch (err) {
            _hideTyping();
            console.error(err);
            Chat.addMessage('assistant', '❌ Error: ' + err.message);
            _renderMessages();
            UI.toast('Error: ' + err.message, 'error');
        }
    }
    
    function _renderMessages() {
        const container = document.getElementById('chatMessages');
        const messages = Chat.getMessages();
        
        if (messages.length === 0) {
            container.innerHTML = document.getElementById('welcomeScreen')?.outerHTML || '';
            _restoreWelcome();
            return;
        }
        
        container.innerHTML = messages.map(m => _renderMessage(m)).join('');
        UI.refreshIcons();
        _attachMessageHandlers();
    }
    
    function _restoreWelcome() {
        const container = document.getElementById('chatMessages');
        container.innerHTML = `
            <div class="welcome-screen" id="welcomeScreen">
                <div class="welcome-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/></svg>
                </div>
                <h2>Neural.AI</h2>
                <p>Fully offline AI. Your data never leaves the device.</p>
                <div class="suggestion-grid">
                    <div class="suggestion-card" data-prompt="Write a Python function to sort a list using quicksort"><i data-feather="code"></i><span>Write Python code</span></div>
                    <div class="suggestion-card" data-prompt="Create an HTML landing page with glassmorphism design"><i data-feather="layout"></i><span>Create HTML page</span></div>
                    <div class="suggestion-card" data-prompt="Generate an image of a futuristic city at sunset"><i data-feather="image"></i><span>Generate image</span></div>
                    <div class="suggestion-card" data-prompt="Compose a simple MIDI melody in C major"><i data-feather="music"></i><span>Create music</span></div>
                </div>
            </div>
        `;
        UI.refreshIcons();
        // Re-bind suggestion cards
        document.querySelectorAll('.suggestion-card').forEach(card => {
            card.addEventListener('click', () => {
                document.getElementById('chatInput').value = card.dataset.prompt;
                _sendMessage();
            });
        });
    }
    
    function _renderMessage(m) {
        const isUser = m.role === 'user';
        const avatar = isUser ? 
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' :
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m7.08 7.08l4.24 4.24M1 12h6m6 0h6"/></svg>';
        
        let extras = '';
        if (m.type === 'image' && m.mediaUrl) {
            extras = `<div class="generated-media">
                <img src="${m.mediaUrl}" alt="Generated">
                <div class="media-actions">
                    <button data-download-image="${m.mediaUrl}" data-name="image.png"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>Download</button>
                </div>
            </div>`;
        } else if (m.type === 'html' && m.html) {
            const blobUrl = m.mediaUrl || Sandbox.previewHTML(m.html);
            extras = `<div class="generated-media">
                <iframe src="${blobUrl}" sandbox="allow-scripts"></iframe>
                <div class="media-actions">
                    <button data-download-html="${encodeURIComponent(m.html)}" data-name="page.html"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>Download</button>
                    <button data-open-html="${blobUrl}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/></svg>Open</button>
                </div>
            </div>`;
        } else if (m.type === 'audio' && m.audioUrl) {
            extras = `<div class="generated-media" style="padding:12px">
                <audio controls src="${m.audioUrl}"></audio>
                <div class="media-actions" style="margin-top:8px;background:none;padding:0">
                    <button data-download-audio="${m.audioUrl}" data-name="melody.wav"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>WAV</button>
                    ${m.midiUrl ? `<button data-download-midi="${m.midiUrl}" data-name="melody.mid"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>MIDI</button>` : ''}
                </div>
            </div>`;
        } else if (m.type === 'code' && m.code) {
            extras = `<div class="code-header"><span>${m.language || 'code'}</span><div class="code-actions"><button class="code-action-btn" onclick="UI.copyCode(this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>Copy</button></div></div><pre><code>${_escapeHTML(m.code)}</code></pre>`;
        } else if (m.type === 'run' && m.result) {
            const logsHtml = m.result.logs.map(l => 
                `<div class="log-${l.type}">${_escapeHTML(l.message)}</div>`
            ).join('');
            extras = `<div class="output-container" style="margin-top:8px"><div class="output-header"><span>Output</span><span class="output-status ${m.result.success ? '' : 'error'}">${m.result.elapsed}ms</span></div><pre class="output-content">${logsHtml}</pre></div>`;
        }
        
        const content = UI.renderMarkdown(m.content);
        
        return `
            <div class="message ${m.role}">
                <div class="msg-avatar">${avatar}</div>
                <div class="msg-content">${content}${extras}</div>
            </div>
        `;
    }
    
    function _escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    
    function _attachMessageHandlers() {
        document.querySelectorAll('[data-download-image]').forEach(btn => {
            btn.addEventListener('click', () => UI.downloadDataURL(btn.dataset.downloadImage, btn.dataset.name));
        });
        document.querySelectorAll('[data-download-html]').forEach(btn => {
            btn.addEventListener('click', () => UI.downloadText(decodeURIComponent(btn.dataset.downloadHtml), btn.dataset.name));
        });
        document.querySelectorAll('[data-open-html]').forEach(btn => {
            btn.addEventListener('click', () => window.open(btn.dataset.openHtml, '_blank'));
        });
        document.querySelectorAll('[data-download-audio]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const resp = await fetch(btn.dataset.downloadAudio);
                const blob = await resp.blob();
                UI.downloadBlob(blob, btn.dataset.name);
            });
        });
        document.querySelectorAll('[data-download-midi]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const resp = await fetch(btn.dataset.downloadMidi);
                const blob = await resp.blob();
                UI.downloadBlob(blob, btn.dataset.name);
            });
        });
    }
    
    function _scrollToBottom() {
        const container = document.getElementById('chatMessages');
        setTimeout(() => { container.scrollTop = container.scrollHeight; }, 50);
    }
    
    function _showTyping() {
        const container = document.getElementById('chatMessages');
        const el = document.createElement('div');
        el.className = 'message assistant';
        el.id = 'typingIndicator';
        el.innerHTML = `
            <div class="msg-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m7.08 7.08l4.24 4.24M1 12h6m6 0h6"/></svg>
            </div>
            <div class="msg-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        container.appendChild(el);
        _scrollToBottom();
    }
    
    function _hideTyping() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }
    
    function _handleAttachment(file) {
        Chat.addAttachment({ name: file.name, size: file.size, type: file.type });
        const preview = document.getElementById('attachmentsPreview');
        const chip = document.createElement('div');
        chip.className = 'attachment-chip';
        chip.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg><span>${file.name}</span>`;
        preview.appendChild(chip);
        UI.toast(`Attached: ${file.name}`, 'success', 2000);
    }
    
    function _toggleVoice() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            UI.toast('Voice input not supported on this device', 'warning');
            return;
        }
        
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SR();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        recognition.onstart = () => UI.toast('🎤 Listening...', 'info', 1500);
        recognition.onresult = (e) => {
            const transcript = e.results[0][0].transcript;
            document.getElementById('chatInput').value = transcript;
            UI.toast('Voice captured!', 'success');
        };
        recognition.onerror = (e) => UI.toast('Voice error: ' + e.error, 'error');
        
        try { recognition.start(); } 
        catch (err) { UI.toast('Voice error', 'error'); }
    }
    
    // ==========================================
    // MODELS
    // ==========================================
    function _initModels() {
        const importZone = document.getElementById('importZone');
        const browseBtn = document.getElementById('browseModelBtn');
        const fileInput = document.getElementById('modelFileInput');
        
        const openPicker = () => fileInput.click();
        importZone.addEventListener('click', (e) => {
            if (!e.target.closest('button')) openPicker();
        });
        browseBtn.addEventListener('click', (e) => { e.stopPropagation(); openPicker(); });
        
        fileInput.addEventListener('change', async (e) => {
            const files = Array.from(e.target.files);
            for (const file of files) {
                await _importModel(file);
            }
            fileInput.value = '';
        });
        
        // Drag & drop
        importZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            importZone.classList.add('dragover');
        });
        importZone.addEventListener('dragleave', () => {
            importZone.classList.remove('dragover');
        });
        importZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            importZone.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            for (const file of files) {
                await _importModel(file);
            }
        });
    }
    
    async function _importModel(file) {
        try {
            UI.toast(`Importing ${file.name}...`, 'info');
            const model = await ModelManager.importFile(file);
            UI.toast(`✓ Imported ${model.name} (${UI.formatSize(model.size)})`, 'success', 3500);
            await _refreshModels();
            await _refreshStorage();
        } catch (err) {
            console.error(err);
            UI.toast('Import failed: ' + err.message, 'error');
        }
    }
    
    async function _refreshModels() {
        const models = await ModelManager.list();
        const list = document.getElementById('modelsList');
        const badge = document.getElementById('modelCount');
        
        badge.textContent = models.length;
        
        if (models.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width:48px;height:48px;margin-bottom:12px;opacity:0.5"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/></svg>
                    <div>No models imported yet</div>
                    <div style="font-size:12px;margin-top:4px;opacity:0.7">Import a .gguf or .safetensors file above</div>
                </div>
            `;
        } else {
            list.innerHTML = models.map(m => `
                <div class="model-item ${m.active ? 'active' : ''}" data-model-id="${m.id}">
                    <div class="model-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>
                    </div>
                    <div class="model-info">
                        <div class="model-name">${m.name}</div>
                        <div class="model-meta">
                            <span>${m.format}</span>
                            <span>•</span>
                            <span>${UI.formatSize(m.size)}</span>
                            ${m.active ? '<span>• <span style="color:#10b981">Active</span></span>' : ''}
                        </div>
                    </div>
                    <div class="model-actions">
                        <button data-model-activate="${m.id}" title="${m.active ? 'Deactivate' : 'Activate'}">
                            <svg viewBox="0 0 24 24" fill="${m.active ? '#10b981' : 'none'}" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        </button>
                        <button data-model-export="${m.id}" title="Export">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                        </button>
                        <button data-model-delete="${m.id}" class="danger" title="Delete">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 01-2 2H9a2 2 0 01-2-2L5 6"/></svg>
                        </button>
                    </div>
                </div>
            `).join('');
            
            list.querySelectorAll('[data-model-activate]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.dataset.modelActivate;
                    const model = await ModelManager.get(id);
                    if (model.active) {
                        await ModelManager.deactivate();
                        UI.toast('Model deactivated', 'info');
                    } else {
                        await ModelManager.activate(id);
                        UI.toast(`✓ Activated: ${model.name}`, 'success');
                    }
                    await _refreshModels();
                    await _updateActiveModelUI();
                });
            });
            
            list.querySelectorAll('[data-model-export]').forEach(btn => {
                btn.addEventListener('click', () => {
                    ModelManager.exportModel(btn.dataset.modelExport);
                    UI.toast('Downloading model...', 'info');
                });
            });
            
            list.querySelectorAll('[data-model-delete]').forEach(btn => {
                btn.addEventListener('click', () => {
                    UI.confirm('Delete this model? File will be removed from local storage.', async () => {
                        await ModelManager.remove(btn.dataset.modelDelete);
                        await _refreshModels();
                        await _refreshStorage();
                        await _updateActiveModelUI();
                        UI.toast('Model deleted', 'info');
                    });
                });
            });
        }
        
        await _updateActiveModelUI();
    }
    
    async function _updateActiveModelUI() {
        const active = await ModelManager.getActive();
        const container = document.getElementById('activeModelInfo');
        const nameEl = document.getElementById('activeModelName');
        const statsEl = document.getElementById('modelStats');
        
        if (active) {
            container.classList.add('loaded');
            nameEl.textContent = active.name;
            statsEl.textContent = `${active.format} • ${UI.formatSize(active.size)}`;
        } else {
            container.classList.remove('loaded');
            nameEl.textContent = 'Built-in Neural Engine';
            statsEl.textContent = 'Ready • No external model';
        }
    }
    
    // ==========================================
    // SANDBOX
    // ==========================================
    function _initSandbox() {
        let currentLang = 'javascript';
        
        const samples = {
            javascript: `// Try running JavaScript here
const greet = (name) => \`Hello, \${name}!\`;
console.log(greet('Neural.AI'));

// Compute fibonacci
function fib(n) {
    return n < 2 ? n : fib(n-1) + fib(n-2);
}
console.log('Fibonacci(10):', fib(10));`,
            html: `<!DOCTYPE html>
<html>
<head><style>
body { font-family: sans-serif; background: linear-gradient(135deg,#667eea,#764ba2); color: white; padding: 40px; text-align: center; }
h1 { font-size: 3rem; }
</style></head>
<body>
<h1>Hello from Sandbox!</h1>
<p>Edit the code and run to see live preview.</p>
</body>
</html>`,
            python: `# Try running Python here
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

print("Fibonacci sequence:")
print(list(fibonacci(10)))

# Math
import math
print(f"Pi = {math.pi}")
print(f"Square root of 2 = {math.sqrt(2)}")`
        };
        
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentLang = btn.dataset.lang;
                document.getElementById('codeEditor').value = samples[currentLang];
                document.getElementById('codeOutput').textContent = '// Output will appear here...';
            });
        });
        
        document.getElementById('runCodeBtn').addEventListener('click', async () => {
            const code = document.getElementById('codeEditor').value;
            const output = document.getElementById('codeOutput');
            const status = document.getElementById('outputStatus');
            
            output.innerHTML = '';
            status.textContent = 'Running...';
            status.className = 'output-status running';
            
            try {
                let result;
                if (currentLang === 'javascript') {
                    result = await Sandbox.runJavaScript(code);
                } else if (currentLang === 'python') {
                    result = await Sandbox.runPython(code);
                } else if (currentLang === 'html') {
                    const url = Sandbox.previewHTML(code);
                    output.innerHTML = `<iframe src="${url}" style="width:100%;height:300px;border:none;background:white;border-radius:8px" sandbox="allow-scripts"></iframe>`;
                    status.textContent = 'Preview';
                    status.className = 'output-status';
                    return;
                }
                
                output.innerHTML = result.logs.map(l => 
                    `<div class="log-${l.type}">${_escapeHTML(l.message)}</div>`
                ).join('') || '<div class="log-info">// No output</div>';
                
                status.textContent = `${result.elapsed}ms`;
                status.className = 'output-status' + (result.success ? '' : ' error');
            } catch (err) {
                output.innerHTML = `<div class="log-error">${_escapeHTML(err.message)}</div>`;
                status.textContent = 'Error';
                status.className = 'output-status error';
            }
        });
        
        document.getElementById('clearOutputBtn').addEventListener('click', () => {
            document.getElementById('codeOutput').textContent = '// Output cleared';
            const status = document.getElementById('outputStatus');
            status.textContent = 'Ready';
            status.className = 'output-status';
        });
        
        document.getElementById('saveCodeBtn').addEventListener('click', async () => {
            const code = document.getElementById('codeEditor').value;
            const ext = { javascript: 'js', python: 'py', html: 'html' }[currentLang];
            const filename = `code_${Date.now()}.${ext}`;
            
            await Storage.files.save({
                id: 'file_' + Date.now(),
                name: filename,
                type: 'code',
                mime: 'text/plain',
                content: code,
                language: currentLang,
                createdAt: Date.now()
            });
            
            UI.downloadText(code, filename);
            UI.toast('Code saved & downloaded', 'success');
            await _refreshFiles();
        });
    }
    
    // ==========================================
    // TOOLS
    // ==========================================
    function _initTools() {
        document.querySelectorAll('.tool-card').forEach(card => {
            card.addEventListener('click', () => {
                const tool = card.dataset.tool;
                const prompts = {
                    'image-gen': 'Generate an image of ',
                    'html-gen': '/html Create a ',
                    'code-gen': '/code Write a ',
                    'midi-gen': '/music Compose a ',
                    'text-tools': '',
                    'tokenizer': ''
                };
                
                if (tool === 'tokenizer') {
                    _showTokenizerModal();
                } else {
                    _switchView('chat');
                    document.getElementById('chatInput').value = prompts[tool];
                    document.getElementById('chatInput').focus();
                }
            });
        });
    }
    
    function _showTokenizerModal() {
        UI.modal({
            title: '🔤 Tokenizer',
            body: `
                <p style="margin-bottom:12px">Enter text to see how it tokenizes:</p>
                <textarea id="tokenInput" style="width:100%;min-height:80px;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.15);border-radius:8px;color:white;font-family:monospace;font-size:13px;user-select:text" placeholder="Type or paste text here...">Hello, world! This is Neural.AI tokenizer.</textarea>
                <div id="tokenResult" style="margin-top:12px;padding:10px;background:rgba(0,0,0,0.3);border-radius:8px;font-family:monospace;font-size:12px;max-height:150px;overflow:auto;user-select:text"></div>
            `,
            actions: [
                { label: 'Tokenize', class: 'btn-primary', closeOnClick: false, onClick: () => {
                    const text = document.getElementById('tokenInput').value;
                    const tk = new Neural.Tokenizer();
                    const ids = tk.encode(text);
                    const result = document.getElementById('tokenResult');
                    result.innerHTML = `
                        <div style="color:#93c5fd;margin-bottom:6px">Tokens: ${ids.length} | Vocab: ${tk.getVocabSize()}</div>
                        <div style="color:#86efac">IDs: [${ids.join(', ')}]</div>
                        <div style="color:#fcd34d;margin-top:6px">Decoded: "${tk.decode(ids)}"</div>
                    `;
                }},
                { label: 'Close', class: 'btn-secondary' }
            ]
        });
    }
    
    // ==========================================
    // FILES
    // ==========================================
    function _initFiles() {
        // Handled by refresh
    }
    
    async function _refreshFiles() {
        const files = await Storage.files.getAll();
        files.sort((a, b) => b.createdAt - a.createdAt);
        
        const grid = document.getElementById('filesGrid');
        if (files.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column:1/-1">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width:48px;height:48px;margin-bottom:12px;opacity:0.5"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
                    <div>No files yet</div>
                    <div style="font-size:12px;margin-top:4px;opacity:0.7">Generated content will appear here</div>
                </div>
            `;
            return;
        }
        
        const iconMap = {
            image: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>',
            html: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
            code: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
            audio: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>'
        };
        
        grid.innerHTML = files.map(f => `
            <div class="file-item" data-file-id="${f.id}">
                <div class="file-icon">${iconMap[f.type] || iconMap.code}</div>
                <div class="file-name">${f.name}</div>
                <div class="file-date">${UI.formatDate(f.createdAt)}</div>
            </div>
        `).join('');
        
        grid.querySelectorAll('.file-item').forEach(el => {
            el.addEventListener('click', async () => {
                const file = await Storage.files.get(el.dataset.fileId);
                _showFilePreview(file);
            });
        });
    }
    
    function _showFilePreview(file) {
        let bodyHtml = '';
        if (file.type === 'image' && file.blob) {
            const url = URL.createObjectURL(file.blob);
            bodyHtml = `<img src="${url}" style="max-width:100%;border-radius:8px">`;
        } else if (file.type === 'html' && file.content) {
            const url = Sandbox.previewHTML(file.content);
            bodyHtml = `<iframe src="${url}" style="width:100%;height:300px;border:none;border-radius:8px;background:white" sandbox="allow-scripts"></iframe>`;
        } else if (file.type === 'audio' && file.blob) {
            const url = URL.createObjectURL(file.blob);
            bodyHtml = `<audio controls src="${url}" style="width:100%"></audio>`;
        } else if (file.type === 'code' && file.content) {
            bodyHtml = `<pre style="background:rgba(0,0,0,0.5);padding:12px;border-radius:8px;overflow:auto;max-height:400px;font-size:12px;user-select:text"><code>${_escapeHTML(file.content)}</code></pre>`;
        }
        
        UI.modal({
            title: file.name,
            body: `
                <div style="font-size:12px;color:rgba(255,255,255,0.5);margin-bottom:12px">${file.type.toUpperCase()} • ${UI.formatDate(file.createdAt)}${file.prompt ? ' • ' + file.prompt : ''}</div>
                ${bodyHtml}
            `,
            actions: [
                { label: 'Download', class: 'btn-primary', onClick: () => {
                    if (file.blob) UI.downloadBlob(file.blob, file.name);
                    else if (file.content) UI.downloadText(file.content, file.name);
                }},
                { label: 'Delete', class: 'btn-danger', onClick: async () => {
                    await Storage.files.delete(file.id);
                    await _refreshFiles();
                    UI.toast('File deleted', 'info');
                }},
                { label: 'Close', class: 'btn-secondary' }
            ]
        });
    }
    
    // ==========================================
    // SETTINGS
    // ==========================================
    function _initSettings() {
        // Sliders
        const setupSlider = (id, valueId, key, formatter = v => v) => {
            const slider = document.getElementById(id);
            const valueEl = document.getElementById(valueId);
            slider.value = state[key];
            valueEl.textContent = formatter(state[key]);
            slider.addEventListener('input', async () => {
                state[key] = parseFloat(slider.value);
                valueEl.textContent = formatter(state[key]);
                await Storage.settings.set(key, state[key]);
            });
        };
        
        setupSlider('temperatureSlider', 'tempValue', 'temperature');
        setupSlider('tokensSlider', 'tokensValue', 'maxTokens');
        setupSlider('topPSlider', 'topPValue', 'topP');
        
        // Toggles
        document.getElementById('darkModeToggle').addEventListener('change', (e) => {
            document.body.classList.toggle('light-mode', !e.target.checked);
            UI.toast(e.target.checked ? 'Dark mode' : 'Light mode', 'info', 1500);
        });
        
        document.getElementById('glassToggle').addEventListener('change', (e) => {
            document.body.classList.toggle('no-glass', !e.target.checked);
        });
        
        document.getElementById('animToggle').addEventListener('change', (e) => {
            document.body.classList.toggle('no-animations', !e.target.checked);
        });
        
        // Clear data
        document.getElementById('clearDataBtn').addEventListener('click', () => {
            UI.confirm('⚠️ This will delete ALL data (models, chats, files, settings). Continue?', async () => {
                await Storage.clearAll();
                UI.toast('All data cleared. Reloading...', 'warning');
                setTimeout(() => location.reload(), 1500);
            });
        });
        
        // Permissions
        document.getElementById('permMic').addEventListener('click', async () => {
            try {
                await navigator.mediaDevices.getUserMedia({ audio: true });
                document.querySelector('#permMic .perm-status').textContent = 'Granted';
                UI.toast('Microphone access granted', 'success');
            } catch (err) {
                UI.toast('Microphone access denied', 'error');
            }
        });
    }
    
    async function _refreshStorage() {
        const usage = await Storage.getUsage();
        const fill = document.getElementById('storageFill');
        const text = document.getElementById('storageText');
        if (fill && text) {
            fill.style.width = Math.min(100, usage.percentage) + '%';
            text.textContent = `${UI.formatSize(usage.usage)} / ${UI.formatSize(usage.quota)} (${usage.percentage.toFixed(1)}%)`;
        }
    }
    
    // Boot
    document.addEventListener('DOMContentLoaded', init);
    
    return { state };
})();
