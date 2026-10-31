/* Lectnex — service worker: abre rápido e funciona com internet ruim.
   Páginas e dados: rede primeiro (sempre o mais novo), cache se a rede falhar.
   CSS/JS/ícones/imagens locais: cache primeiro, atualizando por trás (os arquivos têm ?v= de versão).
   Outros domínios (TradingView, APIs) passam direto, sem cache. */
const CACHE = 'lectnex-v1';
const PAGINAS = ['./', 'index.html', 'macro.html', 'futuros.html', 'acoes.html', 'laboratorio.html', 'sobre.html'];

self.addEventListener('install', e => {
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(PAGINAS)).catch(() => { }).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
    e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

async function guardar(req, res) {
    if (!res || !res.ok || res.type === 'opaque') return;
    const c = await caches.open(CACHE), url = new URL(req.url);
    if (url.search) { // remove versões antigas do mesmo arquivo (?v=…)
        for (const k of await c.keys()) { const u = new URL(k.url); if (u.pathname === url.pathname && u.search !== url.search) c.delete(k); }
    }
    await c.put(req, res);
}
async function redePrimeiro(req, chave) {
    try {
        const res = await fetch(req);
        guardar(chave || req, res.clone());
        return res;
    } catch (_) {
        const hit = await caches.match(chave || req, { ignoreSearch: !!chave });
        if (hit) return hit;
        if (req.mode === 'navigate') return (await caches.match('index.html')) || Response.error();
        return Response.error();
    }
}
async function cachePrimeiro(req, ev) {
    const hit = await caches.match(req);
    const rede = fetch(req).then(res => { guardar(req, res.clone()); return res; }).catch(() => null);
    if (hit) { ev.waitUntil(rede); return hit; }
    return (await rede) || Response.error();
}

self.addEventListener('fetch', e => {
    const req = e.request;
    if (req.method !== 'GET') return;
    const url = new URL(req.url);
    if (url.origin !== location.origin) return;
    if (req.mode === 'navigate' || url.pathname.endsWith('.html')) {
        e.respondWith(redePrimeiro(req, new Request(url.origin + url.pathname)));
    } else if (url.pathname.includes('/data/') || url.pathname.endsWith('.json') || url.pathname.endsWith('.webmanifest')) {
        e.respondWith(redePrimeiro(req, new Request(url.origin + url.pathname))); // ?t= anticache vira uma entrada só
    } else if (/\.(css|js|woff2?|png|jpg|svg|webp)$/.test(url.pathname)) {
        e.respondWith(cachePrimeiro(req, e));
    }
});
