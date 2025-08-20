/**
 * EAA Scanner - Service Worker
 * Basic PWA functionality with offline fallback
 */

const CACHE_NAME = 'eaa-scanner-v1';
const STATIC_CACHE = 'eaa-scanner-static-v1';

// Files to cache for offline functionality
const STATIC_FILES = [
  '/static/css/main.css',
  '/static/js/scanner.js',
  '/static/js/history.js',
  '/',
  '/history'
];

// Install event - cache static files
self.addEventListener('install', event => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Caching static files...');
        return cache.addAll(STATIC_FILES);
      })
      .catch(error => {
        console.error('Failed to cache static files:', error);
      })
  );
  
  // Force activation of new service worker
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  
  // Take control of all pages immediately
  return self.clients.claim();
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }
  
  // Handle API requests with network-first strategy
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/start') || url.pathname.startsWith('/status')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache successful API responses
          if (response.ok && url.pathname.startsWith('/api/')) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Return cached response if available
          return caches.match(request);
        })
    );
    return;
  }
  
  // Handle static files and pages with cache-first strategy
  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        
        // Not in cache, fetch from network
        return fetch(request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response.ok) {
              return response;
            }
            
            // Cache static files
            if (url.pathname.startsWith('/static/') || 
                url.pathname === '/' || 
                url.pathname === '/history') {
              const responseClone = response.clone();
              caches.open(STATIC_CACHE).then(cache => {
                cache.put(request, responseClone);
              });
            }
            
            return response;
          })
          .catch(() => {
            // Network failed, try to serve offline fallback
            if (url.pathname === '/' || !url.pathname.startsWith('/static/')) {
              return caches.match('/').then(indexResponse => {
                if (indexResponse) {
                  return indexResponse;
                }
                // Ultimate fallback
                return new Response(
                  '<html><body><h1>Offline</h1><p>EAA Scanner non è disponibile offline. Controlla la connessione.</p></body></html>',
                  { headers: { 'Content-Type': 'text/html' } }
                );
              });
            }
            
            // For other requests, return a generic error
            return new Response('Risorsa non disponibile offline', {
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
      })
  );
});

// Background sync for offline form submissions (if supported)
self.addEventListener('sync', event => {
  if (event.tag === 'scan-submission') {
    console.log('Background sync: scan-submission');
    
    event.waitUntil(
      // Get pending scan data from IndexedDB and submit when online
      handleOfflineScanSubmission()
    );
  }
});

async function handleOfflineScanSubmission() {
  try {
    // This would integrate with IndexedDB to store and retry offline submissions
    console.log('Handling offline scan submissions...');
    
    // For now, just log - would need IndexedDB integration
    // to store form data when offline and retry when online
    
  } catch (error) {
    console.error('Failed to handle offline submission:', error);
  }
}

// Push notifications (if supported)
self.addEventListener('push', event => {
  if (!event.data) {
    return;
  }
  
  const data = event.data.json();
  const options = {
    body: data.body || 'Scansione completata',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/badge-72.png',
    tag: 'eaa-scanner-notification',
    requireInteraction: true,
    data: {
      url: data.url || '/'
    }
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'EAA Scanner', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  const targetUrl = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        // Check if a window is already open
        for (const client of clientList) {
          if (client.url === targetUrl && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(targetUrl);
        }
      })
  );
});

// Handle messages from the main thread
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }
});

console.log('EAA Scanner Service Worker loaded');