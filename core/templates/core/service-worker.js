const CACHE_NAME = "comunicacao-cache-v3";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then(() => {}));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    )
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Nunca usar cache para navegação (páginas HTML): evita CSRF antigo no logout/login
  if (request.method !== "GET" || request.mode === "navigate") {
    return;
  }

  event.respondWith(
    caches.match(request).then((response) => {
      return response || fetch(request);
    })
  );
});

