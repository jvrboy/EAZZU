/* ================================
   UI - User interface helpers
   Toast, modal, rendering utilities
   ================================ */

const UI = (() => {
    
    // TOAST
    function toast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toastContainer');
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        
        const icons = {
            success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>',
            error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
        };
        
        el.innerHTML = `${icons[type] || icons.info}<span>${message}</span>`;
        container.appendChild(el);
        
        setTimeout(() => {
            el.style.animation = 'toastIn 0.3s reverse';
            setTimeout(() => el.remove(), 300);
        }, duration);
    }
    
    // MODAL
    function modal({ title, body, actions = [], onClose }) {
        const container = document.getElementById('modalContainer');
        container.innerHTML = '';
        
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';
        
        const modalEl = document.createElement('div');
        modalEl.className = 'modal';
        modalEl.innerHTML = `
            <div class="modal-header">
                <div class="modal-title">${title}</div>
                <button class="modal-close">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <div class="modal-body">${body}</div>
            <div class="modal-footer"></div>
        `;
        
        container.appendChild(backdrop);
        container.appendChild(modalEl);
        container.classList.add('active');
        
        const close = () => {
            container.classList.remove('active');
            container.innerHTML = '';
            if (onClose) onClose();
        };
        
        modalEl.querySelector('.modal-close').addEventListener('click', close);
        backdrop.addEventListener('click', close);
        
        const footer = modalEl.querySelector('.modal-footer');
        actions.forEach(action => {
            const btn = document.createElement('button');
            btn.className = action.class || 'btn-secondary';
            btn.textContent = action.label;
            btn.addEventListener('click', () => {
                if (action.onClick) action.onClick();
                if (action.closeOnClick !== false) close();
            });
            footer.appendChild(btn);
        });
        
        return { close };
    }
    
    function confirm(message, onConfirm) {
        modal({
            title: 'Confirm',
            body: `<p>${message}</p>`,
            actions: [
                { label: 'Cancel', class: 'btn-secondary' },
                { label: 'Confirm', class: 'btn-primary', onClick: onConfirm }
            ]
        });
    }
    
    // MARKDOWN RENDERING (simple)
    function renderMarkdown(text) {
        if (!text) return '';
        let html = _escapeHTML(text);
        
        // Code blocks with language
        html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (m, lang, code) => {
            const langLabel = lang || 'code';
            const escaped = code.trim();
            return `<div class="code-header"><span>${langLabel}</span><div class="code-actions"><button class="code-action-btn" onclick="UI.copyCode(this)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>Copy</button></div></div><pre><code>${escaped}</code></pre>`;
        });
        
        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Bold and italic
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // Headings
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
        
        // Lists
        html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*?<\/li>\s*)+/gs, '<ul>$&</ul>');
        
        // Line breaks (double newlines = paragraph)
        html = html.split(/\n\n+/).map(p => {
            if (/^<(h[1-6]|ul|ol|pre|div)/.test(p)) return p;
            return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
        }).join('');
        
        return html;
    }
    
    function _escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    
    // Copy code from button
    function copyCode(btn) {
        const pre = btn.closest('.code-header').nextElementSibling;
        const code = pre.textContent;
        navigator.clipboard.writeText(code).then(() => {
            toast('Code copied to clipboard!', 'success');
        }).catch(() => {
            const textarea = document.createElement('textarea');
            textarea.value = code;
            document.body.appendChild(textarea);
            textarea.select();
            try { document.execCommand('copy'); toast('Code copied!', 'success'); } catch(e) {}
            document.body.removeChild(textarea);
        });
    }
    
    // Download blob as file
    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    
    function downloadText(text, filename) {
        const blob = new Blob([text], { type: 'text/plain' });
        downloadBlob(blob, filename);
    }
    
    function downloadDataURL(dataUrl, filename) {
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = filename;
        a.click();
    }
    
    // Format helpers
    function formatSize(bytes) {
        return Storage.formatBytes(bytes);
    }
    
    function formatDate(timestamp) {
        const d = new Date(timestamp);
        const now = new Date();
        const diff = now - d;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
        if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
        if (diff < 604800000) return Math.floor(diff / 86400000) + 'd ago';
        return d.toLocaleDateString();
    }
    
    // Refresh feather icons
    function refreshIcons() {
        if (window.feather) {
            try { feather.replace({ 'stroke-width': 2 }); } catch(e) {}
        }
    }
    
    return {
        toast,
        modal,
        confirm,
        renderMarkdown,
        copyCode,
        downloadBlob,
        downloadText,
        downloadDataURL,
        formatSize,
        formatDate,
        refreshIcons
    };
})();
