// Teste dos "15 segundos" (combinado em 20/11/2026): num celular de 360 px, sem rolar, a primeira tela precisa mostrar
// o estado da B3, a manchete do dia e o próximo horário importante. Uso: node tests/primeira_tela.cjs [url] [saida.png]
// Sai com código 1 (e imprime o motivo) se algo não aparecer.
const { chromium } = require('playwright');
const URL = process.argv[2] || 'https://lectnex.com.br/', PNG = process.argv[3] || 'primeira-tela.png';
const W = 360, H = 780;
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 2, colorScheme: 'dark', locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
  await ctx.addInitScript(() => { try { localStorage.setItem('lectnex-cookies', 'recusado'); } catch (_) { } });
  const p = await ctx.newPage(), erros = [];
  p.on('pageerror', e => erros.push(e.message));
  await p.goto(URL + (URL.includes('?') ? '&' : '?') + 't=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(8000);
  const r = await p.evaluate(H => {
    const c = document.getElementById('lx-cookies'); if (c) c.remove();
    const vis = (el, linha) => { if (!el) return false; const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0 && b.top >= 0 && (linha ? b.top + 24 : b.bottom) <= H; };
    const b3 = document.querySelector('#fx-lista li'), man = document.getElementById('ms-resumo-t'), ev = document.getElementById('ms-ev');
    return {
      b3: !!b3 && vis(b3) && /Aberta|Fechada|Pré-abertura|Encerrada/.test(b3.innerText), b3t: b3 ? b3.innerText.replace(/\s+/g, ' ') : '',
      manchete: !!man && vis(man) && man.innerText.trim().length > 10 && !/Carregando/.test(man.innerText), mt: man ? man.innerText : '',
      horario: !!ev && vis(ev, true) && /\d{1,2}h|aguardando|Nenhum evento/i.test(ev.innerText), ht: ev ? ev.innerText.replace(/\s+/g, ' ').slice(0, 90) : ''
    };
  }, H);
  await p.screenshot({ path: PNG });
  await b.close();
  const falhas = [!r.b3 && `estado da B3 fora da primeira tela ou sem estado ("${r.b3t}")`, !r.manchete && `manchete fora da primeira tela ou vazia ("${r.mt}")`,
                  !r.horario && `próximo horário fora da primeira tela ("${r.ht}")`, erros.length && `erro na página: ${erros[0]}`].filter(Boolean);
  console.log(falhas.length ? 'FALHOU: ' + falhas.join(' · ') : `OK · ${r.b3t} · ${r.mt.slice(0, 60)} · ${r.ht.slice(0, 60)}`);
  process.exit(falhas.length ? 1 : 0);
})().catch(e => { console.log('FALHOU: ' + e.message); process.exit(1); });
