/*
 * Root sweeper service worker (deployed 2026-09-16, alongside CampusDesk v1.4.2).
 *
 * The old CampusDesk build used to live at https://ronie728.github.io/ and registered
 * its service worker at the ROOT scope ("/"). Even after every server file was
 * deleted, devices that had that registration keep serving the old cached app
 * (users saw v1.2.2 / v1.3.9) and the old worker hijacks navigations to
 * /cd-8f4k2q/ via workbox navigateFallback.
 *
 * This script keeps the SAME url (/sw.js) and the SAME scope ("/") so every stuck
 * client picks it up through the normal update check, then it:
 *   1. deletes every Cache Storage entry on the origin (old precaches die),
 *   2. claims + reloads any open tabs so they come back from the network,
 *   3. unregisters itself (root scope must stay clean forever after).
 *
 * It has NO fetch handler on purpose: while it is alive (a few milliseconds)
 * every request simply goes to the network. The real app's worker lives at
 * /cd-8f4k2q/sw.js with scope /cd-8f4k2q/ and is never touched by this file
 * (cache wiping is shared per-origin, but the app re-precaches on next load).
 */
self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    (function () {
      return Promise.resolve()
        .then(function () {
          if (!self.caches) return [];
          return caches.keys().then(function (keys) {
            return Promise.all(keys.map(function (k) { return caches.delete(k); }));
          });
        })
        .then(function () {
          return self.clients.claim();
        })
        .then(function () {
          return self.clients.matchAll({ type: 'window', includeUncontrolled: true });
        })
        .then(function (clients) {
          clients.forEach(function (c) {
            try { c.navigate(c.url); } catch (e) { /* reload not supported: user refreshes manually */ }
          });
        })
        .then(function () {
          return self.registration.unregister();
        })
        .catch(function () { /* never block activation */ });
    })()
  );
});
