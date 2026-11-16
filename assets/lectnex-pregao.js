/* Lectnex — Modo Pregão: tela única para deixar aberta durante o pregão (Mercado Hoje). */
(function () {
    const $ = id => document.getElementById(id);
    const btn = $('pg-open'); if (!btn || !window.LX) return;
    let ov = null, timer = null, lock = null, leitura = null, cot = null, placar = null, cal = null, rx = null;

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

    /* ----- Antes do dado: 15 min antes até 30 min depois de um dado forte, consenso + como WIN/WDO reagiram antes ----- */
    const PAGINAS = ['ipca', 'payroll', 'cpi-eua', 'fomc', 'copom'];  // têm página em dados/
    const quando = e => { const m = /^(\d{1,2})h(\d{2})?/.exec(e.hora || ''); return m ? new Date(`${e.data}T${String(m[1]).padStart(2, '0')}:${m[2] || '00'}:00-03:00`).getTime() : null; };
    const pctS = v => v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + LX.num(Math.abs(v), 2) + '%';
    const corS = v => v == null ? 'text-slate-500' : v > 0 ? 'text-emerald-600 dark:text-emerald-400' : v < 0 ? 'text-rose-600 dark:text-rose-400' : '';
    function historico(tipo) {
        const rs = ((rx && rx.registros) || []).filter(r => r.tipo === tipo);
        const med = (k, f) => { const v = rs.filter(f).map(r => r[k]).filter(x => typeof x === 'number'); return v.length ? { m: v.reduce((a, b) => a + b, 0) / v.length, n: v.length } : null; };
        return { n: rs.length, acima: { win: med('win', r => r.surpresa === 'acima'), wdo: med('wdo', r => r.surpresa === 'acima') },
                 abaixo: { win: med('win', r => r.surpresa === 'abaixo'), wdo: med('wdo', r => r.surpresa === 'abaixo') } };
    }
    function antesDoDado(sozinho) {
        if (!cal || !Array.isArray(cal.eventos)) return '';
        const agora = Date.now();
        const cand = cal.eventos.map(e => ({ e, t: quando(e) })).filter(x => x.t && (x.e.importancia || 1) >= 2 && Object.keys(x.e.impacto || {}).some(k => k === 'win' || k === 'wdo')
            && x.t - 15 * 60e3 <= agora && agora <= x.t + 30 * 60e3).sort((a, b) => Math.abs(a.t - agora) - Math.abs(b.t - agora))[0];
        if (!cand) return '';
        const { e, t } = cand, h = historico(e.tipo), saiu = e.resultado != null && e.resultado !== '';
        const linha = (rot, x) => x.win || x.wdo ? `<div class="flex flex-wrap justify-between gap-x-2"><span class="text-slate-500">${rot}${x.win ? ` (${x.win.n}×)` : ''}</span><span>WIN <b class="${corS(x.win && x.win.m)}">${pctS(x.win && x.win.m)}</b> · WDO <b class="${corS(x.wdo && x.wdo.m)}">${pctS(x.wdo && x.wdo.m)}</b></span></div>` : '';
        const sup = e.surpresa && /^(acima|abaixo)$/.test(e.surpresa.direcao) ? e.surpresa.direcao : null;
        const s = Math.max(0, Math.floor((t - agora) / 1000));
        const topo = saiu
            ? `<div class="flex flex-wrap items-baseline gap-x-3"><span class="font-mono text-[11px] font-bold text-lect-orange">SAIU</span><strong class="text-2xl text-slate-900 dark:text-white">${LX.esc(String(e.resultado))}</strong>${e.consenso ? `<span class="font-mono text-xs text-slate-500">consenso ${LX.esc(String(e.consenso))}</span>` : ''}${sup ? `<span class="px-1.5 font-mono text-[10px] font-bold ${sup === 'acima' ? 'bg-lect-orange text-lect-navy' : 'bg-sky-600 text-white'}">${sup === 'acima' ? '▲ ACIMA' : '▼ ABAIXO'}</span>` : ''}</div>`
            : t > agora ? `<div class="flex flex-wrap items-baseline gap-x-3"><span class="font-mono text-[11px] font-bold text-lect-orange">FALTAM ${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}</span>${e.consenso ? `<span class="font-mono text-xs">consenso <b>${LX.esc(String(e.consenso))}</b></span>` : ''}${e.anterior ? `<span class="font-mono text-xs text-slate-500">anterior ${LX.esc(String(e.anterior))}</span>` : ''}</div>`
            : `<div class="font-mono text-[11px] font-bold text-lect-orange">SAINDO AGORA · aguardando o número…</div>`;
        const hist = h.n >= 2 ? `<div class="mt-2 font-mono text-[11px] space-y-0.5">${saiu && sup ? linha(`Antes, quando veio ${sup}`, h[sup]) : linha('Quando veio acima', h.acima) + linha('Quando veio abaixo', h.abaixo)}</div>
            <p class="mt-1 text-[10px] text-slate-500">Média dos 30 min seguintes em ${h.n} divulgações. Histórico não garante a próxima reação.${PAGINAS.includes(e.tipo) ? ` <a href="dados/${e.tipo}.html" class="text-lect-teal underline">histórico</a>` : ''}</p>`
            : '<p class="mt-1 text-[10px] text-slate-500">Ainda sem histórico suficiente deste dado.</p>';
        return `<div class="${sozinho ? '' : 'mt-3 pt-3 border-t border-dashed border-lect-orange/50'}"><span class="term-label inline-flex items-center gap-1.5 !mb-1"><i class="ph-bold ph-lightning text-lect-orange"></i>${saiu ? 'O dado saiu' : 'Antes do dado'} · ${LX.esc(e.evento)}</span>${topo}${hist}</div>`;
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
        const ad = antesDoDado(!nx);
        $('pg-ev').innerHTML = (nx || !ad ? ev : '') + ad;  // com o dado acontecendo agora, o aviso "nenhum dado" sai
    }

    function renderSlow() {
        if (!ov) return;
        // 2. viés do modelo (manhã/pregão) ou fechamento (noite, madrugada e fim de semana) — mesma regra da página inicial
        const T = { bullish: ['▲ VIÉS DE ALTA', 'text-emerald-500'], bearish: ['▼ VIÉS DE BAIXA', 'text-rose-500'], neutro: ['● NEUTRO', 'text-slate-400'] };
        const today = LX.iso(LX.todayBRT()), agora = LX.nowBRT();
        let ref = LX.todayBRT();
        if (!LX.isBusinessDay(ref) || agora.getHours() < 9) { ref = LX.addDays(ref, -1); while (!LX.isBusinessDay(ref)) ref = LX.addDays(ref, -1); }
        const fech = placar && (placar.dias || []).find(x => x.data === LX.iso(ref));
        const pc = v => v == null ? '—' : `<span class="${LX.signClass(v)}">${v > 0 ? '+' : v < 0 ? '−' : ''}${LX.num(Math.abs(v), 2)}%</span>`;
        const SET = { bullish: '▲ alta', bearish: '▼ baixa', neutro: '● neutro' };
        if (fech && (fech.win || fech.wdo)) {
            $('pg-term-t').textContent = LX.iso(ref) === today ? 'Fechamento de hoje' : `Fechamento de ${LX.weekday(ref)} ${LX.brShort(ref)}`;
            $('pg-term').innerHTML = [['win', 'IBOVESPA · WIN'], ['wdo', 'DÓLAR · WDO']].filter(([k]) => fech[k]).map(([k, nome]) => { const x = fech[k]; return `<div class="flex-1 min-w-0"><span class="font-mono text-[11px] text-slate-500">${nome}</span><strong class="block font-mono text-lg">${pc(x.var_pct)}</strong><span class="block font-mono text-[11px] text-slate-500">viés ${SET[x.leitura] || ''} · <b class="${x.acerto ? 'text-emerald-500' : 'text-rose-500'}">${x.acerto ? '✓ acertou' : '✗ errou'}</b></span></div>`; }).join('');
        } else {
            $('pg-term-t').textContent = 'Viés do modelo na abertura';
            $('pg-term').innerHTML = leitura && leitura.termometro && leitura.data === today
                ? ['win', 'wdo'].filter(k => leitura.termometro[k]).map(k => { const t = leitura.termometro[k], c = T[t.leitura] || T.neutro; return `<div class="flex-1 min-w-0"><span class="font-mono text-[11px] text-slate-500">${k.toUpperCase()}</span><strong class="block font-mono text-base ${c[1]}">${c[0]}</strong><span class="block text-[11px] text-slate-500 leading-snug line-clamp-2">${LX.esc(t.motivo)}</span></div>`; }).join('')
                  + '<p class="basis-full text-[11px] text-slate-500">Medido antes da abertura · não muda durante o dia · não é recomendação.</p>'
                : `<p class="text-xs text-slate-500">${leitura && leitura.tipo === 'sem-pregao' ? 'Sem pregão hoje: o viés do modelo volta no próximo pregão.' : 'Viés do modelo de hoje ainda não publicado (sai às 7h40).'}</p>`;
        }

        // 3. maiores altas e baixas
        const m = (cot && cot.mapa || []).filter(x => typeof x.var_pct === 'number').sort((a, b) => b.var_pct - a.var_pct);
        const row = x => `<li class="flex justify-between gap-2"><span class="font-bold">${LX.esc(x.ticker)}</span><span class="${LX.signClass(x.var_pct)}">${x.var_pct > 0 ? '+' : ''}${LX.num(x.var_pct, 2)}%</span></li>`;
        // Ibovespa: mesmo valor e mesmo status da mesa de acompanhamento (Mercado Hoje); fora dela, brapi
        let ibov = LX.mesaAtivo && LX.mesaAtivo('IBOV');
        if (ibov) ibov = { preco: ibov.preco, var_pct: ibov.var, st: ibov.st };
        else { const i = (cot && cot.itens || []).find(x => x.ticker === 'IBOV'); ibov = i && { preco: i.preco, var_pct: i.var_pct, st: LX.statusCotacao({ quando: i.hora, lido: cot.atualizado_em, mercado: 'b3', atraso: 30, intervalo: 25 }) }; }
        const stMapa = cot && LX.statusCotacao({ quando: cot.mapa_em, lido: cot.atualizado_em, mercado: 'b3', atraso: 30, intervalo: 25 });
        const stTxt = st => `<span class="${st.alerta ? 'text-amber-600 dark:text-amber-400 font-bold' : ''}">${st.curto}</span>`;
        $('pg-movers').innerHTML = m.length ? `${ibov ? `<div class="flex justify-between font-mono text-xs mb-2 pb-2 border-b border-slate-200 dark:border-lect-borderDark"><span>IBOV ${LX.num(ibov.preco, 0)} <span class="text-[10px] font-normal text-slate-500">${stTxt(ibov.st)}</span></span><span class="${LX.signClass(ibov.var_pct)} font-bold">${ibov.var_pct > 0 ? '+' : ''}${LX.num(ibov.var_pct, 2)}%</span></div>` : ''}
            <div class="grid grid-cols-2 gap-4 font-mono text-xs"><ul class="space-y-1">${m.slice(0, 5).map(row).join('')}</ul><ul class="space-y-1">${m.slice(-5).reverse().map(row).join('')}</ul></div>
            <span class="block mt-2 font-mono text-[10px] text-slate-500">Ações: <span class="${stMapa.alerta ? 'text-amber-600 dark:text-amber-400 font-bold' : ''}">${stMapa.rotulo}</span>${stMapa.atraso ? ' · ' + stMapa.atraso : ''}</span>`
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
        // <dialog> nativo em tela cheia: Esc e o gesto de voltar do celular fecham; o resto da página fica inerte por trás
        ov = document.createElement('dialog'); ov.id = 'pg-ov';
        ov.className = 'fixed inset-0 m-0 p-0 w-full max-w-none h-[100dvh] max-h-none border-0 bg-slate-100 dark:bg-lect-bgDark text-slate-800 dark:text-slate-200 flex flex-col';
        ov.setAttribute('aria-label', 'Modo Pregão');
        ov.innerHTML = `<header class="flex items-center justify-between gap-3 px-3 sm:px-5 py-2 border-b border-slate-200 dark:border-lect-borderDark bg-white dark:bg-lect-cardDark font-mono text-[11px]">
                <span class="font-bold text-lect-orange inline-flex items-center gap-1.5"><i class="ph-bold ph-device-mobile"></i>MODO PREGÃO</span>
                <span id="pg-status"></span>
                <strong id="pg-clock" class="text-sm text-slate-900 dark:text-white tabular-nums"></strong>
                <button type="button" id="pg-close" class="px-2 py-1 border border-slate-300 dark:border-lect-borderDark hover:text-lect-teal" aria-label="Fechar modo pregão"><i class="ph-bold ph-x"></i></button></header>
            <div class="flex-1 min-h-0 overflow-y-auto p-3 sm:p-5 grid gap-3 content-start lg:grid-cols-2 max-w-5xl w-full mx-auto">
                ${card('Próximo dado forte', 'ph-timer', '<div id="pg-ev"></div>', 'lg:col-span-2')}
                ${card('<span id="pg-term-t">Viés do modelo na abertura</span> <span class="lx-demo">EXPERIMENTAL</span>', 'ph-thermometer-simple', '<div id="pg-term" class="flex flex-wrap gap-3"></div>')}
                ${card('Seu Plano do Dia', 'ph-target', '<div id="pg-plano"></div>')}
                ${card('Maiores altas · maiores baixas', 'ph-chart-bar', '<div id="pg-movers"></div>', 'lg:col-span-2')}
            </div>
            <footer class="px-3 sm:px-5 py-1.5 border-t border-slate-200 dark:border-lect-borderDark font-mono text-[10px] text-slate-500 flex justify-between gap-2"><span class="flex gap-3"><button type="button" id="pg-lock" class="hover:text-lect-teal"></button><button type="button" data-lx-push class="hidden items-center gap-1 text-lect-orange hover:underline"><i class="ph-bold ph-bell-ringing"></i>alertas</button></span><span>Educacional · não é recomendação</span></footer>`;
        document.body.appendChild(ov); document.documentElement.style.overflow = 'hidden';
        ov.addEventListener('close', closePg);
        if (ov.showModal) ov.showModal(); else ov.setAttribute('open', '');
        $('pg-close').onclick = closePg; $('pg-lock').onclick = wake; if (LX.pushButtons) LX.pushButtons();
        if (location.hash !== '#pregao') history.replaceState(null, '', '#pregao');
        render(); renderSlow(); wake();
        Promise.all([fetchJSON('data/calendario.json'), fetchJSON('data/reacoes.json')]).then(([c, x]) => { cal = c || cal; rx = x || rx; render(); });
        [leitura, cot, placar] = await Promise.all(LX.dados ? [LX.dados('leitura'), LX.dados('cotacoes'), LX.dados('placar-termometro')] : [fetchJSON('data/leitura.json'), fetchJSON('data/cotacoes.json'), fetchJSON('data/placar-termometro.json')]); renderSlow();
        timer = [setInterval(render, 1000), setInterval(renderSlow, 15000), setInterval(async () => { cot = await fetchJSON('data/cotacoes.json') || cot; renderSlow(); }, 5 * 60e3),
            setInterval(async () => { cal = await fetchJSON('data/calendario.json') || cal; }, 60e3)];  // resultado do dado chega pela coleta do calendário
        $('pg-close').focus();
    }
    function closePg() {
        if (!ov) return; (timer || []).forEach(clearInterval); timer = null;
        try { lock && lock.release(); } catch (_) { } lock = null;
        const d = ov; ov = null; if (d.open && d.close) d.close(); d.remove(); document.documentElement.style.overflow = '';
        if (location.hash === '#pregao') history.replaceState(null, '', location.pathname + location.search);
        btn.focus();
    }
    btn.addEventListener('click', openPg);
    document.addEventListener('visibilitychange', () => { if (ov && document.visibilityState === 'visible' && !lock) wake(); });
    window.addEventListener('storage', e => { if (e.key === 'lectnex-plano-v1') renderSlow(); });
    if (location.hash === '#pregao') openPg();
})();
