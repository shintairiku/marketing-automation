/// BlogAI Service Worker
/// Handles: offline fallback, static asset caching, push notifications

const CACHE_NAME = 'blogai-v1';
const OFFLINE_URL = '/offline';

// Static assets to precache on install
const PRECACHE_ASSETS = [
  '/offline',
  '/favicon.png',
  '/icon-192.png',
  '/icon-512.png',
  '/apple-touch-icon.png',
];

// Install: precache essential assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// Fetch: network-first for navigation, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip API routes and auth-related requests
  const url = new URL(request.url);
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/sign-in') ||
    url.pathname.startsWith('/sign-up') ||
    url.pathname.includes('clerk')
  ) {
    return;
  }

  // Navigation requests: network-first with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Static assets (images, fonts, CSS, JS): stale-while-revalidate
  if (
    request.destination === 'image' ||
    request.destination === 'font' ||
    request.destination === 'style' ||
    request.destination === 'script'
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const fetchPromise = fetch(request)
          .then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            }
            return response;
          })
          .catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }
});

// Push notification handler
self.addEventListener('push', (event) => {
  if (!event.data) return;

  try {
    const data = event.data.json();
    const options = {
      body: data.body || '',
      icon: data.icon || '/icon-192.png',
      badge: '/favicon.png',
      vibrate: [100, 50, 100],
      data: {
        url: data.url || '/',
        dateOfArrival: Date.now(),
      },
    };
    event.waitUntil(
      self.registration.showNotification(data.title || 'BlogAI', options)
    );
  } catch {
    // If data is not JSON, show as plain text
    const options = {
      body: event.data.text(),
      icon: '/icon-192.png',
      badge: '/favicon.png',
    };
    event.waitUntil(self.registration.showNotification('BlogAI', options));
  }
});

// Notification click: open the target URL
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        // Focus existing window if available
        for (const client of clients) {
          if (client.url.includes(url) && 'focus' in client) {
            return client.focus();
          }
        }
        // Otherwise open new window
        return self.clients.openWindow(url);
      })
  );
});
