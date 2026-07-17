/* ================================
   SANDBOX - Safe code execution
   Runs JavaScript, HTML preview, Python (via Pyodide if available)
   ================================ */

const Sandbox = (() => {
    let pyodide = null;
    let pyodideLoading = null;
    
    // Execute JavaScript safely
    async function runJavaScript(code) {
        const logs = [];
        const startTime = performance.now();
        
        // Create sandboxed console
        const sandboxConsole = {
            log: (...args) => logs.push({ type: 'log', message: args.map(_stringify).join(' ') }),
            info: (...args) => logs.push({ type: 'info', message: args.map(_stringify).join(' ') }),
            warn: (...args) => logs.push({ type: 'warn', message: args.map(_stringify).join(' ') }),
            error: (...args) => logs.push({ type: 'error', message: args.map(_stringify).join(' ') }),
            table: (data) => logs.push({ type: 'log', message: _stringify(data) })
        };
        
        try {
            // Create isolated scope using AsyncFunction
            const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
            const fn = new AsyncFunction('console', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'Math', 'Date', 'JSON', 'Array', 'Object', 'String', 'Number', 'Boolean', 'Promise', 
                `"use strict";\n${code}`);
            
            const result = await Promise.race([
                fn(sandboxConsole, setTimeout, setInterval, clearTimeout, clearInterval, Math, Date, JSON, Array, Object, String, Number, Boolean, Promise),
                new Promise((_, reject) => setTimeout(() => reject(new Error('Execution timeout (5s)')), 5000))
            ]);
            
            if (result !== undefined) {
                logs.push({ type: 'success', message: '→ ' + _stringify(result) });
            }
            
            const elapsed = (performance.now() - startTime).toFixed(2);
            return { success: true, logs, elapsed };
        } catch (err) {
            logs.push({ type: 'error', message: err.name + ': ' + err.message });
            const elapsed = (performance.now() - startTime).toFixed(2);
            return { success: false, logs, elapsed, error: err.message };
        }
    }
    
    // Preview HTML in an iframe
    function previewHTML(html) {
        const blob = new Blob([html], { type: 'text/html' });
        return URL.createObjectURL(blob);
    }
    
    // Load Pyodide for Python execution (needs internet only on first load; then cached)
    async function _loadPyodide() {
        if (pyodide) return pyodide;
        if (pyodideLoading) return pyodideLoading;
        
        pyodideLoading = (async () => {
            // Inject Pyodide script
            if (!window.loadPyodide) {
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js';
                    script.onload = resolve;
                    script.onerror = () => reject(new Error('Failed to load Pyodide runtime'));
                    document.head.appendChild(script);
                });
            }
            
            pyodide = await window.loadPyodide({
                indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.26.2/full/'
            });
            
            return pyodide;
        })();
        
        return pyodideLoading;
    }
    
    // Run Python via Pyodide (offline once cached)
    async function runPython(code) {
        const logs = [];
        const startTime = performance.now();
        
        try {
            logs.push({ type: 'info', message: 'Loading Python runtime...' });
            const py = await _loadPyodide();
            
            // Capture Python stdout
            py.setStdout({
                batched: (msg) => logs.push({ type: 'log', message: msg })
            });
            py.setStderr({
                batched: (msg) => logs.push({ type: 'error', message: msg })
            });
            
            // Clear the loading message
            logs.length = 0;
            
            const result = await py.runPythonAsync(code);
            
            if (result !== undefined && result !== null) {
                logs.push({ type: 'success', message: '→ ' + String(result) });
            }
            
            const elapsed = (performance.now() - startTime).toFixed(2);
            return { success: true, logs, elapsed };
        } catch (err) {
            logs.push({ type: 'error', message: err.message });
            const elapsed = (performance.now() - startTime).toFixed(2);
            return { success: false, logs, elapsed, error: err.message };
        }
    }
    
    function _stringify(value) {
        if (value === undefined) return 'undefined';
        if (value === null) return 'null';
        if (typeof value === 'string') return value;
        if (typeof value === 'number' || typeof value === 'boolean') return String(value);
        if (typeof value === 'function') return value.toString();
        try {
            return JSON.stringify(value, null, 2);
        } catch (e) {
            return String(value);
        }
    }
    
    return {
        runJavaScript,
        runPython,
        previewHTML
    };
})();
