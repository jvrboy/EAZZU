/* ================================
   CHAT - Message handling & rendering
   ================================ */

const Chat = (() => {
    let currentChatId = null;
    let messages = [];
    let attachments = [];
    let isGenerating = false;
    
    function _uid() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    }
    
    function _msgId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6);
    }
    
    // Create a new chat
    async function newChat() {
        currentChatId = _uid();
        messages = [];
        attachments = [];
        return currentChatId;
    }
    
    // Load a chat
    async function loadChat(id) {
        const chat = await Storage.chats.get(id);
        if (!chat) return false;
        currentChatId = id;
        messages = chat.messages || [];
        attachments = [];
        return chat;
    }
    
    // Save current chat
    async function save() {
        if (!currentChatId || messages.length === 0) return;
        
        const chat = {
            id: currentChatId,
            title: _generateTitle(),
            messages: messages,
            createdAt: messages[0]?.timestamp || Date.now(),
            updatedAt: Date.now()
        };
        
        await Storage.chats.save(chat);
        return chat;
    }
    
    function _generateTitle() {
        const firstUserMsg = messages.find(m => m.role === 'user');
        if (!firstUserMsg) return 'New Chat';
        const text = firstUserMsg.content.replace(/[\n\r]/g, ' ').trim();
        return text.length > 40 ? text.slice(0, 40) + '...' : text;
    }
    
    // Get all chats
    async function getAll() {
        const chats = await Storage.chats.getAll();
        return chats.sort((a, b) => b.updatedAt - a.updatedAt);
    }
    
    // Delete a chat
    async function deleteChat(id) {
        await Storage.chats.delete(id);
        if (currentChatId === id) {
            currentChatId = null;
            messages = [];
        }
    }
    
    // Add message
    function addMessage(role, content, extra = {}) {
        const msg = {
            id: _msgId(),
            role,
            content,
            timestamp: Date.now(),
            ...extra
        };
        messages.push(msg);
        return msg;
    }
    
    // Get all messages
    function getMessages() {
        return messages;
    }
    
    // Attachments
    function addAttachment(att) {
        attachments.push(att);
    }
    
    function clearAttachments() {
        attachments = [];
    }
    
    function getAttachments() {
        return attachments;
    }
    
    // Process user input (detect commands)
    async function processInput(input, options = {}) {
        if (isGenerating) return { pending: true };
        isGenerating = true;
        
        try {
            const trimmed = input.trim();
            
            // Command detection
            if (trimmed.startsWith('/image ')) {
                return await _handleImage(trimmed.slice(7).trim());
            }
            if (trimmed.startsWith('/html ')) {
                return await _handleHTML(trimmed.slice(6).trim());
            }
            if (trimmed.startsWith('/code ')) {
                return await _handleCode(trimmed.slice(6).trim());
            }
            if (trimmed.startsWith('/music') || trimmed.startsWith('/midi')) {
                return await _handleMusic(trimmed.replace(/^\/(music|midi)/, '').trim());
            }
            if (trimmed.startsWith('/run ')) {
                return await _handleRun(trimmed.slice(5).trim());
            }
            
            // Auto-detect intent from content
            const lower = trimmed.toLowerCase();
            if (/generate|create|draw|make.*image|picture of/.test(lower) && /image|picture|photo|visual/.test(lower)) {
                return await _handleImage(trimmed);
            }
            if (/write.*html|create.*html|make.*html|html.*page/.test(lower)) {
                return await _handleHTML(trimmed);
            }
            if (/write.*(code|function|script|program)|(python|javascript|js).*(code|function)/.test(lower)) {
                return await _handleCode(trimmed);
            }
            if (/compose.*music|generate.*melody|create.*song|midi/.test(lower)) {
                return await _handleMusic(trimmed);
            }
            
            // Default: text response
            return await _handleText(trimmed, options);
        } finally {
            isGenerating = false;
        }
    }
    
    async function _handleText(input, options) {
        const response = Neural.engine.respond(input, options);
        return { type: 'text', content: response };
    }
    
    async function _handleImage(prompt) {
        const dataUrl = await Pipelines.image.generate(prompt);
        // Save to files
        const fileId = 'file_' + Date.now();
        const blob = _dataURLtoBlob(dataUrl);
        await Storage.files.save({
            id: fileId,
            name: `image_${Date.now()}.png`,
            type: 'image',
            mime: 'image/png',
            blob: blob,
            prompt: prompt,
            createdAt: Date.now()
        });
        return {
            type: 'image',
            content: `Generated image for: "${prompt}"`,
            mediaUrl: dataUrl,
            fileId: fileId
        };
    }
    
    async function _handleHTML(prompt) {
        const html = Pipelines.html.generate(prompt);
        const url = Sandbox.previewHTML(html);
        const fileId = 'file_' + Date.now();
        await Storage.files.save({
            id: fileId,
            name: `page_${Date.now()}.html`,
            type: 'html',
            mime: 'text/html',
            content: html,
            prompt: prompt,
            createdAt: Date.now()
        });
        return {
            type: 'html',
            content: `Generated HTML page for: "${prompt}"`,
            html: html,
            mediaUrl: url,
            fileId: fileId
        };
    }
    
    async function _handleCode(prompt) {
        const { language, code } = Pipelines.code.generate(prompt);
        const fileId = 'file_' + Date.now();
        const ext = { python: 'py', javascript: 'js', jsx: 'jsx', html: 'html' }[language] || 'txt';
        await Storage.files.save({
            id: fileId,
            name: `code_${Date.now()}.${ext}`,
            type: 'code',
            mime: 'text/plain',
            content: code,
            language: language,
            prompt: prompt,
            createdAt: Date.now()
        });
        return {
            type: 'code',
            content: `Generated ${language} code for: "${prompt}"`,
            code: code,
            language: language,
            fileId: fileId
        };
    }
    
    async function _handleMusic(prompt) {
        const wavUrl = await Pipelines.music.playMelody(prompt);
        const midiUrl = Pipelines.music.generateMIDI(prompt);
        
        const fileId = 'file_' + Date.now();
        // Fetch back blob for storage
        const response = await fetch(wavUrl);
        const blob = await response.blob();
        await Storage.files.save({
            id: fileId,
            name: `melody_${Date.now()}.wav`,
            type: 'audio',
            mime: 'audio/wav',
            blob: blob,
            prompt: prompt || 'Melody',
            createdAt: Date.now()
        });
        
        return {
            type: 'audio',
            content: `🎵 Composed a melody${prompt ? ' for: "' + prompt + '"' : ''}`,
            audioUrl: wavUrl,
            midiUrl: midiUrl,
            fileId: fileId
        };
    }
    
    async function _handleRun(code) {
        const result = await Sandbox.runJavaScript(code);
        return {
            type: 'run',
            content: `Executed code (${result.elapsed}ms)`,
            result: result
        };
    }
    
    function _dataURLtoBlob(dataURL) {
        const parts = dataURL.split(',');
        const mime = parts[0].match(/:(.*?);/)[1];
        const bin = atob(parts[1]);
        const arr = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        return new Blob([arr], { type: mime });
    }
    
    // Export chat as JSON/Markdown
    function exportChat(format = 'markdown') {
        if (format === 'json') {
            return JSON.stringify({ id: currentChatId, messages }, null, 2);
        }
        
        let md = `# ${_generateTitle()}\n\n`;
        md += `Exported: ${new Date().toLocaleString()}\n\n---\n\n`;
        messages.forEach(m => {
            const role = m.role === 'user' ? '**You**' : '**Neural.AI**';
            md += `${role}:\n\n${m.content}\n\n---\n\n`;
        });
        return md;
    }
    
    return {
        newChat,
        loadChat,
        save,
        getAll,
        deleteChat,
        addMessage,
        getMessages,
        addAttachment,
        clearAttachments,
        getAttachments,
        processInput,
        exportChat,
        get currentId() { return currentChatId; },
        get isGenerating() { return isGenerating; }
    };
})();
