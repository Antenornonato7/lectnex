// Teste de fumaça do Lectnex: abre cada página num Chromium de verdade e procura problemas visíveis.
// Uso: servir a pasta do site (python3 -m http.server 8766) e rodar `node tests/smoke.cjs [http://localhost:8766]`.
// Falha (exit 1) se achar: erro de JavaScript, link interno quebrado, imagem interna quebrada,
// texto "undefined"/"NaN"/"[object Object]" na tela, página quase vazia ou rolagem lateral no celular.
const { chromium } = require('playwright');
const { readdirSync, existsSync, appendFileSync } = require('node:fs');

const BASE = (process.argv[2] || 'http://localhost:8766').replace(/\/$/, '');
const raiz = readdirSync('.').filter(f => f.endsWith('.html'));
const sub = d => existsSync(d) ? readdirSync(d).filter(f => f.endsWith('.html')).map(f => `${d}/${f}`) : [];
// acoes/: 217 páginas do mesmo molde; testa o índice e uma amostra
const PAGINAS = [...raiz, ...sub('semana'), ...sub('leitura'), ...sub('acoes').filter(f => /\/(index|petr4|vale3|taee11)\.html$/.test(f)),
    ...sub('glossario').filter(f => /\/(rolagem|dv01|mini-indice-win|risk-on-e-risk-off)\.html$/.test(f))];
const MOBILE = ['index.html', 'macro.html', 'futuros.html', 'acoes.html', 'laboratorio.html', 'status.html', 'glossario.html', 'comece.html', 'copom.html', 'links.html', 'hoje.html', 'manchetes.html', 'placar.html'];
// Terceiros fora do nosso controle: bloqueados para o teste ser estável e rápido.
const BLOQUEAR = /(tradingview|googleapis|gstatic|onesignal|googletagmanager|google-analytics|t\.me|instagram|tiktok|x\.com)/;
const LIXO = /\b(undefined|NaN)\b|\[object Object\]/;

(async () => {
const problemas = [];
const erro = (pg, msg) => { problemas.push(`${pg}: ${msg}`); console.log(`::error title=${pg}::${msg}`); };
const linksVistos = new Map();

const browser = await chromium.launch();
for (const pg of PAGINAS) {
    for (const largura of MOBILE.includes(pg) ? [1280, 390] : [1280]) {
        const ctx = await browser.newContext({ viewport: { width: largura, height: 900 }, serviceWorkers: 'block' });
        const p = await ctx.newPage();
        const tag = `${pg}${largura < 500 ? ' (celular)' : ''}`;
        p.on('pageerror', e => erro(tag, `erro de JavaScript: ${e.message.split('\n')[0]}`));
        p.on('console', m => {
            if (m.type() !== 'error') return;
            const t = m.text();
            if (/Failed to load resource|net::ERR_|ERR_BLOCKED|CORS|Access-Control|status of 4\d\d|status of 5\d\d|Content Security/i.test(t)) return; // rede/terceiros
            erro(tag, `console: ${t.slice(0, 160)}`);
        });
        await p.route(BLOQUEAR, r => r.abort());
        try {
            const resp = await p.goto(`${BASE}/${pg}`, { waitUntil: 'load', timeout: 30000 });
            if (!resp || resp.status() >= 400) { erro(tag, `página respondeu HTTP ${resp && resp.status()}`); await ctx.close(); continue; }
        } catch (e) { erro(tag, `não carregou: ${e.message.split('\n')[0]}`); await ctx.close(); continue; }
        await p.waitForTimeout(2500);

        const info = await p.evaluate(() => {
            const main = document.querySelector('main') || document.body;
            const vis = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden'; };
            const textos = [];
            const w = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
            while (w.nextNode()) { const n = w.currentNode; if (n.parentElement && !['SCRIPT', 'STYLE', 'CODE', 'PRE'].includes(n.parentElement.tagName) && vis(n.parentElement)) textos.push(n.textContent); }
            const before = window.scrollX; window.scrollTo(400, window.scrollY); const rola = window.scrollX > 0; window.scrollTo(before, window.scrollY);
            return {
                texto: textos.join(' ').replace(/\s+/g, ' '),
                tamanho: (main.innerText || '').trim().length,
                rolaLateral: rola,
                links: [...document.querySelectorAll('a[href]')].map(a => a.href),
                imgs: [...document.images].filter(i => i.src.startsWith(location.origin) && i.complete && i.naturalWidth === 0 && vis(i)).map(i => i.src),
                h1: document.querySelectorAll('h1').length,
                titulo: document.title,
            };
        });
        const m = info.texto.match(new RegExp(`.{0,40}(${LIXO.source}).{0,40}`));
        if (m) erro(tag, `texto quebrado na tela: "…${m[0].trim()}…"`);
        if (info.tamanho < 200) erro(tag, `página quase vazia (${info.tamanho} caracteres no conteúdo)`);
        if (largura < 500 && info.rolaLateral) erro(tag, 'rolagem lateral no celular (algo mais largo que a tela)');
        if (!info.titulo) erro(tag, 'sem <title>');
        if (largura >= 500 && info.h1 !== 1) erro(tag, `deveria ter 1 título <h1>, tem ${info.h1}`);
        info.imgs.forEach(src => erro(tag, `imagem quebrada: ${src.replace(BASE, '')}`));
        for (const href of info.links) {
            const u = new URL(href);
            if (u.origin !== new URL(BASE).origin) continue;
            const chave = u.pathname;
            if (!linksVistos.has(chave)) linksVistos.set(chave, new Set());
            linksVistos.get(chave).add(pg);
        }
        await ctx.close();
    }
}

// Links internos: cada destino precisa existir.
const ctx = await browser.newContext();
for (const [caminho, origens] of linksVistos) {
    if (/\.(txt|xml|json|webmanifest)$/.test(caminho) && caminho.includes('/data/')) continue;
    const r = await ctx.request.get(BASE + caminho, { maxRedirects: 3 }).catch(() => null);
    if (!r || r.status() >= 400) erro([...origens][0], `link interno quebrado: ${caminho} (HTTP ${r ? r.status() : 'sem resposta'})${origens.size > 1 ? ` · em ${origens.size} páginas` : ''}`);
}
await browser.close();

const resumo = problemas.length
    ? `### ❌ Teste do site: ${problemas.length} problema(s)\n\n${problemas.map(p => `- ${p}`).join('\n')}\n`
    : `### ✅ Teste do site: ${PAGINAS.length} páginas, ${linksVistos.size} links internos, nenhum problema\n`;
console.log(resumo);
if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, resumo);
process.exit(problemas.length ? 1 : 0);
})();
