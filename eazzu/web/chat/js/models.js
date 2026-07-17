/* ================================
   MODELS - Model File Manager
   Import, store, load .gguf/.safetensors/.bin/etc
   ================================ */

const ModelManager = (() => {
    let activeModel = null;
    let listeners = [];
    
    function _uid() {
        return 'model_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    }
    
    function _detectFormat(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const formats = {
            gguf: { name: 'GGUF', desc: 'Quantized LLM (llama.cpp)' },
            safetensors: { name: 'Safetensors', desc: 'Safe tensor format' },
            bin: { name: 'BIN', desc: 'Binary weights' },
            onnx: { name: 'ONNX', desc: 'Open Neural Network Exchange' },
            pt: { name: 'PyTorch', desc: 'PyTorch weights' },
            pth: { name: 'PyTorch', desc: 'PyTorch weights' },
            ggml: { name: 'GGML', desc: 'Legacy quantized format' },
            q4_0: { name: 'GGUF Q4_0', desc: '4-bit quantized' },
            q4_1: { name: 'GGUF Q4_1', desc: '4-bit quantized' },
            q5_0: { name: 'GGUF Q5_0', desc: '5-bit quantized' },
            q5_1: { name: 'GGUF Q5_1', desc: '5-bit quantized' },
            q8_0: { name: 'GGUF Q8_0', desc: '8-bit quantized' }
        };
        return formats[ext] || { name: ext.toUpperCase(), desc: 'Model file' };
    }
    
    async function _readFileHeader(file) {
        // Read first 4KB to inspect file header
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const buf = new Uint8Array(e.target.result);
                const info = {};
                
                // GGUF signature: 'GGUF'
                if (buf[0] === 0x47 && buf[1] === 0x47 && buf[2] === 0x55 && buf[3] === 0x46) {
                    info.magic = 'GGUF';
                    // Read version (uint32 LE)
                    info.version = buf[4] | (buf[5] << 8) | (buf[6] << 16) | (buf[7] << 24);
                }
                // Safetensors: first 8 bytes = header size, then JSON
                else if (file.name.endsWith('.safetensors')) {
                    info.magic = 'SAFETENSORS';
                    const headerLen = Number(new BigUint64Array(buf.buffer.slice(0, 8))[0]);
                    if (headerLen < 4000) {
                        try {
                            const json = new TextDecoder().decode(buf.slice(8, 8 + headerLen));
                            info.metadata = JSON.parse(json).__metadata__ || {};
                        } catch(e) { /* ignore */ }
                    }
                }
                // ONNX: starts with 0x08
                else if (buf[0] === 0x08) {
                    info.magic = 'ONNX';
                }
                
                resolve(info);
            };
            reader.onerror = () => resolve({});
            reader.readAsArrayBuffer(file.slice(0, 4096));
        });
    }
    
    async function importFile(file, onProgress) {
        const format = _detectFormat(file.name);
        const header = await _readFileHeader(file);
        
        // For large files, we store the File reference in IndexedDB (which supports Blobs)
        // instead of loading everything into memory.
        const model = {
            id: _uid(),
            name: file.name,
            size: file.size,
            format: format.name,
            formatDesc: format.desc,
            header: header,
            createdAt: Date.now(),
            active: false,
            file: file // IndexedDB can store Blob/File
        };
        
        if (onProgress) onProgress(50);
        
        await Storage.models.save(model);
        
        if (onProgress) onProgress(100);
        
        _emit('imported', model);
        return model;
    }
    
    async function list() {
        const models = await Storage.models.getAll();
        return models.sort((a, b) => b.createdAt - a.createdAt);
    }
    
    async function get(id) {
        return await Storage.models.get(id);
    }
    
    async function activate(id) {
        const models = await list();
        for (const m of models) {
            m.active = (m.id === id);
            await Storage.models.save(m);
        }
        activeModel = await Storage.models.get(id);
        _emit('activated', activeModel);
        return activeModel;
    }
    
    async function deactivate() {
        if (activeModel) {
            activeModel.active = false;
            await Storage.models.save(activeModel);
            activeModel = null;
            _emit('deactivated');
        }
    }
    
    async function remove(id) {
        if (activeModel && activeModel.id === id) {
            activeModel = null;
        }
        await Storage.models.delete(id);
        _emit('removed', id);
    }
    
    async function getActive() {
        if (activeModel) return activeModel;
        const models = await list();
        activeModel = models.find(m => m.active) || null;
        return activeModel;
    }
    
    async function exportModel(id) {
        const model = await get(id);
        if (!model || !model.file) return null;
        
        const url = URL.createObjectURL(model.file);
        const a = document.createElement('a');
        a.href = url;
        a.download = model.name;
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    
    // Event system
    function on(event, callback) {
        listeners.push({ event, callback });
    }
    
    function _emit(event, data) {
        listeners.filter(l => l.event === event).forEach(l => l.callback(data));
    }
    
    return {
        importFile,
        list,
        get,
        activate,
        deactivate,
        remove,
        getActive,
        exportModel,
        on
    };
})();
