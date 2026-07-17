/* Service Worker - offline caching */
const CACHE_NAME = 'neural-ai-v1';
const CORE_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './assets/icon.svg',
    './css/style.css',
    './css/sidebar.css',
    './css/chat.css',
    './css/components.css',
    './js/storage.js',
    './js/neural.js',
    './js/pipelines.js',
    './js/models.js',
    './js/sandbox.js',
    './js/chat.js',
    './js/ui.js',
    './js/app.js',
    'https://unpkg.com/feather-icons'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => 
            cache.addAll(CORE_ASSETS).catch(err => console.warn('Cache error:', err))
        )
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
        ))
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;
    
    event.respondWith(
        caches.match(event.request).then(cached => {
            if (cached) return cached;
            
            return fetch(event.request).then(response => {
                if (!response || response.status !== 200) return response;
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseClone).catch(() => {});
                });
                return response;
            }).catch(() => {
                // Offline fallback for navigation
                if (event.request.mode === 'navigate') {
                    return caches.match('./index.html');
                }
            });
        })
    );
});
