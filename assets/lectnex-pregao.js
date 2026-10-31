/* Lectnex — Modo Pregão: tela única para deixar aberta durante o pregão (Mercado Hoje). */
(function () {
    const $ = id => document.getElementById(id);
    const btn = $('pg-open'); if (!btn || !window.LX) return;
    let ov = null, timer = null, lock = null, leitura = null, cot = null;

    const fetchJSON = u => fetch(u + '?t=' + Date.now(), { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null);
    async function wake() {
        try { if ('wakeLock' in navigator && document.visibilityState === 'visible') { lock = await navigator.wakeLock.request('screen'); lock.addEventListener('release', () => { lock = null; paintLock(); }); } } catch (_) { lock = null; }
        paintLock();
    }
    function paintLock() { const el = $('pg-lock'); if (el) el.innerHTML = lock ? '<i class="ph-fill ph-sun"></i> tela acesa' : ('wakeLock' in navigator ? '<i class="ph-bold ph-moon"></i> toque para manter acesa' : ''); }

    function plano() {
        let st = {}; try { st = JSON.parse(localStorage.getItem('lectnex-plano-v1') || '{}'); } catch (_) { }
        const L = Object.assign({ cap: 0, maxloss: 0, goal: 0, maxtr: 0 }, st.limits || {});
        const day = (st.days || {})[LX.iso(LX.todayBRT())] || { trades: [] };
        const tv = t => typeof t === 'number' ? t : (+t.r || 0) - (+t.c || 0);
        const pnl = (day.trades || []).reduce((a, b) => a + tv(b), 0), n = (day.trades || []).length;
        return { lim: (+L.cap || 0) * (+L.maxloss || 0) / 100, goal: +L.goal || 0, maxtr: +L.maxtr || 0, pnl, n, set: !!st.limits };
    }

    function card(title, icon, body, extra = '') { return `<section class="term-panel p-3 sm:p-4 flex flex-col min-h-0 ${extra}"><span class="term-label inline-flex items-center gap-1.5 mb-2"><i class="ph-bold ${icon} text-lect-teal"></i>${title}</span>${body}</section>`; }

    function render() {
        if (!ov) return;
        const now = LX.nowBRT(), hh = now.getHours() * 60 + now.getMinutes();
        const bday = LX.isBusinessDay(LX.todayBRT()), open = bday && hh >= 9 * 60 && hh < 18 * 60 + 25;
        $('pg-clock').textContent = now.toLocaleTimeString('pt-BR');
        $('pg-status').innerHTML = open ? '<span class="text-emerald-500">● FUTUROS ABERTOS</span>' : '<span class="text-slate-500">● FUTUROS FECHADOS</span>';

        // 1. próximo dado forte
        const nx = LX.calNext();
        let ev;
        if (nx) {
            const left = nx.t - Date.now(), s = Math.max(0, Math.floor(left / 1000)), hot = left <= 15 * 60e3;
            const big = left <= 0 ? 'AGORA' : s < 3600 ? `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}` : `${Math.floor(s / 3600)}h${String(Math.floor(s % 3600 / 60)).padStart(2, '0')}`;
            const tags = Object.entries(nx.e.impacto || {}).filter(([, v]) => LX.calArrow[v]).map(([k, v]) => `<span class="px-1 border border-current text-[10px] font-bold">${LX.esc(k.toUpperCase())} ${LX.calArrow[v]}</span>`).join(' ');
            ev = `<div class="flex items-center justify-between gap-3 ${hot ? 'text-lect-orange' : ''}"><div class="min-w-0"><strong class="block text-sm leading-snug ${hot ? '' : 'text-slate-900 dark:text-white'}">${LX.calFlag[nx.e.pais] || ''} ${LX.esc(nx.e.evento)}</strong><span class="font-mono text-[11px] text-slate-500">${LX.esc(nx.e.hora)} · ${nx.e.consenso ? 'cons. ' + LX.esc(nx.e.consenso) : 'sem consenso'}</span><div class="mt-1 flex gap-1 font-mono">${tags}</div></div><span class="font-mono text-3xl sm:text-4xl font-bold tabular-nums ${hot ? 'animate-pulse' : 'text-lect-teal'}">${big}</span></div>`;
        } else ev = '<p class="text-xs text-slate-500">Nenhum dado de alto impacto nas próximas 36 horas.</p>';
        $('pg-ev').innerHTML = ev;
    }

    function renderSlow() {
        if (!ov) return;
        // 2. termômetro
        const T = { bullish: ['▲ ALTA', 'text-emerald-500'], bearish: ['▼ BAIXA', 'text-rose-500'], neutro: ['● NEUTRO', 'text-slate-400'] };
        const today = LX.iso(LX.todayBRT());
        $('pg-term').innerHTML = leitura && leitura.termometro && leitura.data === today
            ? ['win', 'wdo'].filter(k => leitura.termometro[k]).map(k => { const t = leitura.termometro[k], c = T[t.leitura] || T.neutro; return `<div class="flex-1 min-w-0"><span class="font-mono text-[11px] text-slate-500">${k.toUpperCase()}</span><strong class="block font-mono text-lg ${c[1]}">${c[0]}</strong><span class="block text-[11px] text-slate-500 leading-snug line-clamp-2">${LX.esc(t.motivo)}</span></div>`; }).join('<div class="w-px bg-slate-200 dark:bg-lect-borderDark"></div>')
            : `<p class="text-xs text-slate-500">${leitura && leitura.tipo === 'sem-pregao' ? 'Sem pregão hoje: o termômetro volta no próximo pregão.' : 'Termômetro de hoje ainda não publicado (sai às 7h40).'}</p>`;

        // 3. maiores altas e baixas
        const m = (cot && cot.mapa || []).filter(x => typeof x.var_pct === 'number').sort((a, b) => b.var_pct - a.var_pct);
        const row = x => `<li class="flex justify-between gap-2"><span class="font-bold">${LX.esc(x.ticker)}</span><span class="${LX.signClass(x.var_pct)}">${x.var_pct > 0 ? '+' : ''}${LX.num(x.var_pct, 2)}%</span></li>`;
        const ibov = (cot && cot.itens || []).find(x => x.ticker === 'IBOV');
        $('pg-movers').innerHTML = m.length ? `${ibov ? `<div class="flex justify-between font-mono text-xs mb-2 pb-2 border-b border-slate-200 dark:border-lect-borderDark"><span>IBOV ${LX.num(ibov.preco, 0)}</span><span class="${LX.signClass(ibov.var_pct)} font-bold">${ibov.var_pct > 0 ? '+' : ''}${LX.num(ibov.var_pct, 2)}%</span></div>` : ''}
            <div class="grid grid-cols-2 gap-4 font-mono text-xs"><ul class="space-y-1">${m.slice(0, 5).map(row).join('')}</ul><ul class="space-y-1">${m.slice(-5).reverse().map(row).join('')}</ul></div>
            <span class="block mt-2 font-mono text-[10px] text-slate-500">${cot.mapa_em ? 'atualizado ' + new Date(cot.mapa_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' }) + ' · ' : ''}atraso ~30 min</span>`
            : '<p class="text-xs text-slate-500">Cotações indisponíveis.</p>';

        // 4. plano do dia
        const p = plano();
        if (!p.set || !p.lim) $('pg-plano').innerHTML = `<p class="text-xs text-slate-500">Defina capital e perda máxima no <a class="text-lect-teal underline" href="futuros.html#plano">Plano do Dia</a> para ver seu limite aqui.</p>`;
        else {
            const used = p.pnl < 0 ? Math.min(100, -p.pnl / p.lim * 100) : 0, hit = p.pnl <= -p.lim || (p.maxtr && p.n >= p.maxtr);
            $('pg-plano').innerHTML = `<div class="flex items-baseline justify-between font-mono"><strong class="text-2xl ${LX.signClass(p.pnl)}">${p.pnl >= 0 ? '+' : '−'}${LX.brl(Math.abs(p.pnl), 0)}</strong><span class="text-[11px] text-slate-500">${p.n}${p.maxtr ? '/' + p.maxtr : ''} operações</span></div>
                <div class="mt-2 h-2 bg-slate-200 dark:bg-lect-bgDark"><div class="h-full ${used >= 80 ? 'bg-rose-600' : used >= 50 ? 'bg-lect-orange' : 'bg-lect-teal'}" style="width:${used}%"></div></div>
                <div class="flex justify-between font-mono text-[10px] text-slate-500 mt-1"><span>limite −${LX.brl(p.lim, 0)}</span><span>${LX.num(used, 0)}% usado</span></div>
                ${hit ? '<div class="mt-2 p-2 bg-rose-600 text-white text-xs font-bold"><i class="ph-fill ph-hand-palm"></i> Limite do dia atingido. Hora de parar.</div>' : `<a href="futuros.html#plano" class="mt-2 inline-block text-[11px] text-lect-teal underline">registrar operação →</a>`}`;
        }
    }

    async function openPg() {
        if (ov) return;
        ov = document.createElement('div'); ov.id = 'pg-ov';
        ov.className = 'fixed inset-0 z-[80] bg-slate-100 dark:bg-lect-bgDark text-slate-800 dark:text-slate-200 flex flex-col h-[100dvh]';
        ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true'); ov.setAttribute('aria-label', 'Modo Pregão');
        ov.innerHTML = `<header class="flex items-center justify-between gap-3 px-3 sm:px-5 py-2 border-b border-slate-200 dark:border-lect-borderDark bg-white dark:bg-lect-cardDark font-mono text-[11px]">
                <span class="font-bold text-lect-orange inline-flex items-center gap-1.5"><i class="ph-bold ph-device-mobile"></i>MODO PREGÃO</span>
                <span id="pg-status"></span>
                <strong id="pg-clock" class="text-sm text-slate-900 dark:text-white tabular-nums"></strong>
                <button type="button" id="pg-close" class="px-2 py-1 border border-slate-300 dark:border-lect-borderDark hover:text-lect-teal" aria-label="Fechar modo pregão"><i class="ph-bold ph-x"></i></button></header>
            <div class="flex-1 min-h-0 overflow-y-auto p-3 sm:p-5 grid gap-3 content-start lg:grid-cols-2 max-w-5xl w-full mx-auto">
                ${card('Próximo dado forte', 'ph-timer', '<div id="pg-ev"></div>', 'lg:col-span-2')}
                ${card('Termômetro do dia', 'ph-thermometer-simple', '<div id="pg-term" class="flex gap-3"></div>')}
                ${card('Seu Plano do Dia', 'ph-target', '<div id="pg-plano"></div>')}
                ${card('Maiores altas · maiores baixas', 'ph-chart-bar', '<div id="pg-movers"></div>', 'lg:col-span-2')}
            </div>
            <footer class="px-3 sm:px-5 py-1.5 border-t border-slate-200 dark:border-lect-borderDark font-mono text-[10px] text-slate-500 flex justify-between gap-2"><button type="button" id="pg-lock" class="hover:text-lect-teal"></button><span>Educacional · não é recomendação</span></footer>`;
        document.body.appendChild(ov); document.documentElement.style.overflow = 'hidden';
        $('pg-close').onclick = closePg; $('pg-lock').onclick = wake;
        if (location.hash !== '#pregao') history.replaceState(null, '', '#pregao');
        render(); renderSlow(); wake();
        [leitura, cot] = await Promise.all([fetchJSON('data/leitura.json'), fetchJSON('data/cotacoes.json')]); renderSlow();
        timer = [setInterval(render, 1000), setInterval(renderSlow, 15000), setInterval(async () => { cot = await fetchJSON('data/cotacoes.json') || cot; renderSlow(); }, 5 * 60e3)];
        $('pg-close').focus();
    }
    function closePg() {
        if (!ov) return; (timer || []).forEach(clearInterval); timer = null;
        try { lock && lock.release(); } catch (_) { } lock = null;
        ov.remove(); ov = null; document.documentElement.style.overflow = '';
        if (location.hash === '#pregao') history.replaceState(null, '', location.pathname + location.search);
        btn.focus();
    }
    btn.addEventListener('click', openPg);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closePg(); });
    document.addEventListener('visibilitychange', () => { if (ov && document.visibilityState === 'visible' && !lock) wake(); });
    window.addEventListener('storage', e => { if (e.key === 'lectnex-plano-v1') renderSlow(); });
    if (location.hash === '#pregao') openPg();
})();
