// DPE Prospector — Service Worker minimal
// Requis pour l'installation PWA, pas de logique de cache

const CACHE_NAME = 'dpe-prospector-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// Pas de cache — toutes les requêtes passent directement au réseau
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});// DPE Prospector — Service Worker minimal
// Requis pour l'installation PWA, pas de logique de cache

const CACHE_NAME = 'dpe-prospector-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// Pas de cache — toutes les requêtes passent directement au réseau
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
