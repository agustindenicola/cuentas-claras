// Cuentas Claras: trabajador de fondo. Guarda la app para abrir rápido y recibe las notificaciones.
const CACHE = "cuentas-v2";
const SHELL = ["/", "/static/style.css", "/static/app.js", "/manifest.webmanifest", "/static/icons/icon-192.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

// la app: primero la red (para tener lo último) y, sin conexión, lo guardado. Los datos (/api) siempre van a la red.
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.pathname.startsWith("/api/") || url.origin !== location.origin) return;
  e.respondWith(
    fetch(e.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return r;
    }).catch(() => caches.match(e.request).then(r => r || caches.match("/")))
  );
});

self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { title: "Cuentas Claras", body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(d.title || "Cuentas Claras", {
    body: d.body || "", tag: d.tag || "cuentas", icon: "/static/icons/icon-192.png", badge: "/static/icons/badge-96.png",
    data: { url: d.url || "/#inicio" }, lang: "es-AR", actions: d.actions || [],
  }));
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  // «Hoy no gasté» desde la notificación: se anota el día sin abrir la app
  if (e.action === "nogaste") {
    e.waitUntil(fetch("/api/checkin", { method: "POST", credentials: "include", headers: { "X-CC": "1", "Content-Type": "application/json" } })
      .then(r => self.registration.showNotification(r.ok ? "¡Listo! Día anotado 🔥" : "No se pudo anotar", {
        body: r.ok ? "Tu racha sigue. ¡Buenas noches!" : "Abrí la app para anotarlo.", tag: "checkin", icon: "/static/icons/icon-192.png", badge: "/static/icons/badge-96.png" })));
    return;
  }
  const url = e.action === "anotar" ? "/#cargar" : (e.notification.data && e.notification.data.url) || "/#inicio";
  const target = new URL(url, self.location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(cs => {
    for (const c of cs) { if ("focus" in c) { c.navigate(target); return c.focus(); } }
    return self.clients.openWindow(target);
  }));
});
