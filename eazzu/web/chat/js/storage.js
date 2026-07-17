/* ================================
   STORAGE - IndexedDB + LocalStorage
   Persistent local data for models, chats, files
   ================================ */

const Storage = (() => {
    const DB_NAME = 'NeuralAI_DB';
    const DB_VERSION = 1;
    let db = null;

    // Initialize IndexedDB
    function init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                db = request.result;
                resolve(db);
            };

            request.onupgradeneeded = (e) => {
                const database = e.target.result;
                
                if (!database.objectStoreNames.contains('models')) {
                    const store = database.createObjectStore('models', { keyPath: 'id' });
                    store.createIndex('name', 'name', { unique: false });
                    store.createIndex('createdAt', 'createdAt', { unique: false });
                }
                
                if (!database.objectStoreNames.contains('chats')) {
                    const store = database.createObjectStore('chats', { keyPath: 'id' });
                    store.createIndex('createdAt', 'createdAt', { unique: false });
                }
                
                if (!database.objectStoreNames.contains('files')) {
                    const store = database.createObjectStore('files', { keyPath: 'id' });
                    store.createIndex('createdAt', 'createdAt', { unique: false });
                    store.createIndex('type', 'type', { unique: false });
                }
                
                if (!database.objectStoreNames.contains('kv')) {
                    database.createObjectStore('kv', { keyPath: 'key' });
                }
            };
        });
    }

    // Generic CRUD
    function _tx(storeName, mode = 'readonly') {
        return db.transaction([storeName], mode).objectStore(storeName);
    }

    function put(storeName, data) {
        return new Promise((resolve, reject) => {
            const req = _tx(storeName, 'readwrite').put(data);
            req.onsuccess = () => resolve(data);
            req.onerror = () => reject(req.error);
        });
    }

    function get(storeName, id) {
        return new Promise((resolve, reject) => {
            const req = _tx(storeName).get(id);
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    function getAll(storeName) {
        return new Promise((resolve, reject) => {
            const req = _tx(storeName).getAll();
            req.onsuccess = () => resolve(req.result || []);
            req.onerror = () => reject(req.error);
        });
    }

    function remove(storeName, id) {
        return new Promise((resolve, reject) => {
            const req = _tx(storeName, 'readwrite').delete(id);
            req.onsuccess = () => resolve();
            req.onerror = () => reject(req.error);
        });
    }

    function clear(storeName) {
        return new Promise((resolve, reject) => {
            const req = _tx(storeName, 'readwrite').clear();
            req.onsuccess = () => resolve();
            req.onerror = () => reject(req.error);
        });
    }

    // Models
    const models = {
        save: (model) => put('models', model),
        get: (id) => get('models', id),
        getAll: () => getAll('models'),
        delete: (id) => remove('models', id),
        clear: () => clear('models')
    };

    // Chats
    const chats = {
        save: (chat) => put('chats', chat),
        get: (id) => get('chats', id),
        getAll: () => getAll('chats'),
        delete: (id) => remove('chats', id),
        clear: () => clear('chats')
    };

    // Files
    const files = {
        save: (file) => put('files', file),
        get: (id) => get('files', id),
        getAll: () => getAll('files'),
        delete: (id) => remove('files', id),
        clear: () => clear('files')
    };

    // Key-value settings
    const settings = {
        set: (key, value) => put('kv', { key, value }),
        get: async (key, defaultValue = null) => {
            const result = await get('kv', key);
            return result ? result.value : defaultValue;
        },
        remove: (key) => remove('kv', key)
    };

    // Storage estimate
    async function getUsage() {
        if (navigator.storage && navigator.storage.estimate) {
            const { usage, quota } = await navigator.storage.estimate();
            return {
                usage,
                quota,
                percentage: (usage / quota) * 100
            };
        }
        return { usage: 0, quota: 0, percentage: 0 };
    }

    // Request persistent storage
    async function requestPersistent() {
        if (navigator.storage && navigator.storage.persist) {
            return await navigator.storage.persist();
        }
        return false;
    }

    // Format bytes
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
    }

    // Clear all data
    async function clearAll() {
        await Promise.all([
            clear('models'),
            clear('chats'),
            clear('files'),
            clear('kv')
        ]);
        localStorage.clear();
        sessionStorage.clear();
    }

    return {
        init,
        models,
        chats,
        files,
        settings,
        getUsage,
        requestPersistent,
        formatBytes,
        clearAll
    };
})();
