/* =====================================================================================
   LECTNEX CORE — núcleo compartilhado por todas as páginas
   - Dados reais: Banco Central (SGS / PTAX / Focus) e AwesomeAPI (câmbio, cripto)
   - Calendário B3: feriados, dias úteis, vencimentos de WIN, WDO, DI1 e opções
   - Status dos pregões, relógio, tema claro/escuro e widgets TradingView
   Nenhuma dependência externa. Carregue com <script src="assets/lectnex-core.js?v=20261030c"></script>
   ===================================================================================== */
(function () {
    'use strict';

    const LX = (window.LX = window.LX || {});

    /* ------------------------------------------------------------------ CONFIG */
    LX.config = Object.assign({}, LX.config || {}, {
        // Token gratuito em https://brapi.dev (sem token, só PETR4/VALE3/ITUB4/MGLU3 respondem)
        brapiToken: 'uRJnTfjL6jypdHfJ8b5LJd',
        // Valores de referência usados até a resposta das APIs (ou se elas falharem).
        // Atualize aqui quando necessário — a página mostra a data de referência.
        fallback: {
            refDate: '30/10/2026',
            selic: 13.75,          // Meta Selic — Copom 281ª reunião (16/09/2026)
            cdi: 13.65,            // Taxa DI / Selic efetiva (% a.a.)
            ipca12m: 4.57,         // IPCA acumulado 12 meses até set/2026
            ipcaMes: 0.82,         // IPCA set/2026
            ipcaRef: 'set/2026'
        }
    });
    LX.config.brapiToken = 'uRJnTfjL6jypdHfJ8b5LJd';
    // Newsletter (Buttondown): usuário da conta. Vazio = formulários de inscrição ficam escondidos.
    LX.config.newsletter = 'lectnex';
    LX.config.telegram = 'lectnex';   // canal público t.me/lectnex
    LX.config.onesignal = 'c0be7d93-6afb-4bb0-bf56-6f9171302071';
    LX.config.ga = 'G-5D8GS46BN1';   // Google Analytics 4 (ID G-XXXXXXX). Vazio = desligado. Só grava cookies depois do "Aceitar" (LGPD).
    LX.config.onesignalSafari = 'web.onesignal.auto.201c9c11-2835-4563-82b9-55a6f9094e87';         // App ID do OneSignal (notificações no celular); vazio = desligado

    /* ------------------------------------------------------------------ FORMATOS */
    const nf = (min, max) => new Intl.NumberFormat('pt-BR', { minimumFractionDigits: min, maximumFractionDigits: max });
    LX.num = (v, d = 2) => (v == null || isNaN(v)) ? '—' : nf(d, d).format(v);
    LX.brl = (v, d = 2) => (v == null || isNaN(v)) ? '—' : 'R$ ' + nf(d, d).format(v);
    LX.pct = (v, d = 2, sign = false) => (v == null || isNaN(v)) ? '—' : (sign && v > 0 ? '+' : '') + nf(d, d).format(v) + '%';
    LX.signClass = (v) => v > 0 ? 'text-emerald-600 dark:text-emerald-400' : (v < 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-500');
    LX.esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

    /* ------------------------------------------------------------------ DATAS (fuso de Brasília) */
    const pad = (n) => String(n).padStart(2, '0');
    LX.iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    LX.br = (d) => `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
    LX.brShort = (d) => `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`;
    LX.weekday = (d) => ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'][d.getDay()];

    // "Agora" em horário de Brasília, como objeto Date local com os campos de SP
    LX.nowBRT = function () {
        const parts = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
        }).formatToParts(new Date()).reduce((a, p) => (a[p.type] = p.value, a), {});
        return new Date(+parts.year, +parts.month - 1, +parts.day, +parts.hour % 24, +parts.minute, +parts.second);
    };
    LX.todayBRT = function () { const n = LX.nowBRT(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); };

    // Hora/minuto num fuso qualquer
    function hmIn(tz) {
        const p = new Intl.DateTimeFormat('en-US', { timeZone: tz, hour: '2-digit', minute: '2-digit', weekday: 'short', hour12: false })
            .formatToParts(new Date()).reduce((a, x) => (a[x.type] = x.value, a), {});
        return { min: (+p.hour % 24) * 60 + +p.minute, wd: p.weekday };
    }

    /* ------------------------------------------------------------------ FERIADOS */
    function easter(y) {
        const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4,
            f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30,
            i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451),
            month = Math.floor((h + l - 7 * m + 114) / 31), day = ((h + l - 7 * m + 114) % 31) + 1;
        return new Date(y, month - 1, day);
    }
    const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
    LX.addDays = addDays;

    const holidayCache = {};
    // Feriados nacionais (calendário ANBIMA — base da contagem de dias úteis do DI)
    LX.nationalHolidays = function (y) {
        if (holidayCache['n' + y]) return holidayCache['n' + y];
        const e = easter(y);
        const list = [
            [new Date(y, 0, 1), 'Confraternização Universal'],
            [addDays(e, -48), 'Carnaval'], [addDays(e, -47), 'Carnaval'],
            [addDays(e, -2), 'Sexta-feira Santa'],
            [new Date(y, 3, 21), 'Tiradentes'], [new Date(y, 4, 1), 'Dia do Trabalho'],
            [addDays(e, 60), 'Corpus Christi'],
            [new Date(y, 8, 7), 'Independência'], [new Date(y, 9, 12), 'N. Sra. Aparecida'],
            [new Date(y, 10, 2), 'Finados'], [new Date(y, 10, 15), 'Proclamação da República'],
            [new Date(y, 11, 25), 'Natal']
        ];
        if (y >= 2024) list.push([new Date(y, 10, 20), 'Consciência Negra']);
        const map = new Map(list.map(([d, n]) => [LX.iso(d), n]));
        return (holidayCache['n' + y] = map);
    };
    // Dias sem pregão na B3 = feriados nacionais + 24/12 e 31/12
    LX.b3Holidays = function (y) {
        if (holidayCache['b' + y]) return holidayCache['b' + y];
        const map = new Map(LX.nationalHolidays(y));
        map.set(`${y}-12-24`, 'Véspera de Natal (sem pregão)');
        map.set(`${y}-12-31`, 'Último dia do ano (sem pregão)');
        return (holidayCache['b' + y] = map);
    };
    LX.isBusinessDay = function (d, b3 = true) {
        const wd = d.getDay();
        if (wd === 0 || wd === 6) return false;
        return !(b3 ? LX.b3Holidays(d.getFullYear()) : LX.nationalHolidays(d.getFullYear())).has(LX.iso(d));
    };
    LX.nextBusinessDay = function (d, b3 = true) { let x = new Date(d); while (!LX.isBusinessDay(x, b3)) x = addDays(x, 1); return x; };
    // Dias úteis entre "from" (exclusive) e "to" (inclusive) — convenção do DI1 (base ANBIMA)
    LX.businessDaysBetween = function (from, to, b3 = false) {
        let n = 0, d = addDays(from, 1);
        while (d <= to) { if (LX.isBusinessDay(d, b3)) n++; d = addDays(d, 1); }
        return n;
    };

    /* ------------------------------------------------------------------ VENCIMENTOS B3 */
    LX.monthCode = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'];
    LX.monthName = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

    // WIN / IND / opções de Ibovespa: quarta-feira mais próxima do dia 15; sem pregão → dia útil seguinte
    LX.winExpiry = function (y, m) {
        const d15 = new Date(y, m, 15);
        const diff = (3 - d15.getDay() + 7) % 7;              // dias até a próxima quarta
        const wed = diff <= 3 ? addDays(d15, diff) : addDays(d15, diff - 7);
        return LX.nextBusinessDay(wed);
    };
    // WDO / DOL / DI1: primeiro dia útil do mês de vencimento
    LX.firstBusinessDay = function (y, m) { return LX.nextBusinessDay(new Date(y, m, 1)); };
    // Opções sobre ações: terceira sexta-feira do mês; sem pregão → antecipado p/ o dia útil ANTERIOR
    // (ex.: nov/2026 — 20/11 é feriado, vencimento em 19/11)
    LX.optionExpiry = function (y, m) {
        const first = new Date(y, m, 1);
        let d = addDays(addDays(first, (5 - first.getDay() + 7) % 7), 14);
        while (!LX.isBusinessDay(d)) d = addDays(d, -1);
        return d;
    };

    function upcoming(kind, count, from) {
        const today = from || LX.todayBRT();
        const out = [];
        let y = today.getFullYear(), m = today.getMonth();
        for (let i = 0; out.length < count && i < 60; i++) {
            const yy = y + Math.floor((m + i) / 12), mm = (m + i) % 12;
            if (kind === 'WIN' && mm % 2 !== 1) continue;      // meses pares: fev, abr, jun, ago, out, dez
            const exp = kind === 'WIN' ? LX.winExpiry(yy, mm)
                : kind === 'OPC' ? LX.optionExpiry(yy, mm)
                    : LX.firstBusinessDay(yy, mm);
            if (exp < today) continue;
            const code = kind === 'OPC' ? null : `${kind}${LX.monthCode[mm]}${String(yy).slice(2)}`;
            out.push({
                kind, code, year: yy, month: mm, expiry: exp,
                callLetter: String.fromCharCode(65 + mm), putLetter: String.fromCharCode(77 + mm),
                du: LX.businessDaysBetween(today, exp, true),
                dc: Math.round((exp - today) / 86400000)
            });
        }
        return out;
    };
    LX.upcomingWIN = (n = 6) => upcoming('WIN', n);
    LX.upcomingWDO = (n = 6) => upcoming('WDO', n);
    LX.upcomingOptions = (n = 6) => upcoming('OPC', n);
    // Vértices de janeiro do DI1 (os mais líquidos), a partir do próximo janeiro
    LX.diJanuaryVertices = function (n = 8) {
        const today = LX.todayBRT(), out = [];
        for (let y = today.getFullYear() + 1; out.length < n; y++) {
            const exp = LX.firstBusinessDay(y, 0);
            if (exp < today) continue;
            out.push({ code: `DI1F${String(y).slice(2)}`, expiry: exp, du: LX.businessDaysBetween(today, exp, false) });
        }
        return out;
    };
    /* ------------------------------------------------------------------ STATUS DOS PREGÕES */
    // Horários aproximados (BRT). A B3 ajusta a grade quando os EUA entram/saem do horário de verão.
    LX.sessions = {
        b3: { label: 'B3 AÇÕES', tz: 'America/Sao_Paulo', open: 10 * 60, close: 17 * 60 + 55, pre: 9 * 60 + 45, holidays: true },
        b3f: { label: 'B3 FUTUROS', tz: 'America/Sao_Paulo', open: 9 * 60, close: 18 * 60 + 25, pre: 8 * 60 + 55, holidays: true },
        nyse: { label: 'NYSE', tz: 'America/New_York', open: 9 * 60 + 30, close: 16 * 60, pre: 4 * 60 },
        lse: { label: 'LONDRES', tz: 'Europe/London', open: 8 * 60, close: 16 * 60 + 30, pre: 7 * 60 + 50 },
        tse: { label: 'TÓQUIO', tz: 'Asia/Tokyo', open: 9 * 60, close: 15 * 60 + 30, pre: 8 * 60 }
    };
    LX.sessionStatus = function (key) {
        const s = LX.sessions[key];
        const { min, wd } = hmIn(s.tz);
        if (wd === 'Sat' || wd === 'Sun') return { state: 'closed', text: 'FECHADO' };
        if (s.holidays && !LX.isBusinessDay(LX.todayBRT())) return { state: 'closed', text: 'FERIADO' };
        if (min >= s.open && min < s.close) return { state: 'open', text: 'ABERTO' };
        if (min >= s.pre && min < s.open) return { state: 'pre', text: 'PRÉ-ABERTURA' };
        return { state: 'closed', text: 'FECHADO' };
    };
    function paintSessions() {
        document.querySelectorAll('[data-lx-session]').forEach(el => {
            const st = LX.sessionStatus(el.dataset.lxSession);
            const dot = st.state === 'open' ? 'bg-emerald-400' : st.state === 'pre' ? 'bg-amber-400' : 'bg-slate-500';
            el.innerHTML = `<span class="w-1.5 h-1.5 ${dot} inline-block"></span>${LX.sessions[el.dataset.lxSession].label}: <strong class="${st.state === 'open' ? 'text-white' : 'text-slate-400'}">${st.text}</strong>`;
        });
    }

    /* ------------------------------------------------------------------ RELÓGIO */
    function tickClock() {
        const t = LX.nowBRT();
        document.querySelectorAll('[data-lx-clock]').forEach(el => {
            el.textContent = `${LX.weekday(t)} ${LX.brShort(t)} · ${pad(t.getHours())}:${pad(t.getMinutes())}:${pad(t.getSeconds())} BRT`;
        });
    }

    /* ------------------------------------------------------------------ TEMA */
    LX.isDark = () => document.documentElement.classList.contains('dark');
    // Modo escuro é o padrão; o claro só quando o visitante escolheu
    try { if (localStorage.getItem('lectnex-theme') !== 'light') document.documentElement.classList.add('dark'); } catch (_) { document.documentElement.classList.add('dark'); }
    window.toggleTheme = function () {
        const dark = document.documentElement.classList.toggle('dark');
        try { localStorage.setItem('lectnex-theme', dark ? 'dark' : 'light'); } catch (_) { }
        LX._tvWidgets.forEach(w => { const h = document.getElementById(w.id); if (h && h.dataset.tvLoaded) LX.tv(w.id, w.type, w.cfg, true); });
        document.dispatchEvent(new CustomEvent('lx:theme', { detail: { dark } }));
    };

    /* ------------------------------------------------------------------ DADOS REAIS */
    LX.data = {
        selic: { value: LX.config.fallback.selic, src: 'ref', date: LX.config.fallback.refDate },
        cdi: { value: LX.config.fallback.cdi, src: 'ref', date: LX.config.fallback.refDate },
        ipca12m: { value: LX.config.fallback.ipca12m, src: 'ref', date: LX.config.fallback.ipcaRef },
        ipcaMes: { value: LX.config.fallback.ipcaMes, src: 'ref', date: LX.config.fallback.ipcaRef },
        fx: {}, ptax: null
    };

    /* Cache local: abre a página já com os últimos números e atualiza em seguida */
    const CACHE_KEY = 'lectnex-cache-v1';
    const CACHE_TTL = { macro: 7 * 864e5, ptax: 3 * 864e5, fx: 12 * 36e5 };
    function cacheAll() { try { return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}'); } catch (_) { return {}; } }
    function cacheSet(k, v) { try { const c = cacheAll(); c[k] = { t: Date.now(), v }; localStorage.setItem(CACHE_KEY, JSON.stringify(c)); } catch (_) { } }
    (function hydrate() {
        const c = cacheAll(), now = Date.now(), fresh = k => c[k] && now - c[k].t < CACHE_TTL[k];
        let newest = 0;
        if (fresh('macro')) { Object.assign(LX.data, c.macro.v); newest = Math.max(newest, c.macro.t); }
        if (fresh('ptax')) LX.data.ptax = c.ptax.v;
        if (fresh('fx')) {
            Object.entries(c.fx.v).forEach(([k, q]) => { q.time = new Date(q.time); LX.data.fx[k] = q; });
            LX.data.fxOk = true; LX.data.fxCached = true; newest = Math.max(newest, c.fx.t);
        }
        if (newest) LX.data.cachedAt = new Date(newest).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' });
    })();

    async function getJSON(url, ms = 9000) {
        const ctl = new AbortController();
        const t = setTimeout(() => ctl.abort(), ms);
        try {
            const r = await fetch(url, { signal: ctl.signal, cache: 'no-store' });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return await r.json();
        } finally { clearTimeout(t); }
    }
    LX.getJSON = getJSON;

    async function sgs(code, n = 1) {
        const count = Math.min(n || 1, 20);
        const j = await getJSON(`https://api.bcb.gov.br/dados/serie/bcdata.sgs.${code}/dados/ultimos/${count}?formato=json`);
        return j.map(r => ({ date: r.data, value: parseFloat(String(r.valor).replace(',', '.')) }));
    }
    LX.sgs = sgs;

    LX.loadMacro = async function () {
        const jobs = [
            sgs(432).then(r => LX.data.selic = { value: r[0].value, src: 'BCB · SGS 432', date: r[0].date }),
            sgs(4389).then(r => LX.data.cdi = { value: r[0].value, src: 'BCB · SGS 4389', date: r[0].date }),
            sgs(13522).then(r => LX.data.ipca12m = { value: r[0].value, src: 'IBGE via BCB · SGS 13522', date: r[0].date.slice(3) }),
            sgs(433).then(r => LX.data.ipcaMes = { value: r[0].value, src: 'IBGE via BCB · SGS 433', date: r[0].date.slice(3) })
        ];
        const res = await Promise.allSettled(jobs);
        const macroOk = res.some(r => r.status === 'fulfilled');
        LX.data.realRate = ((1 + LX.data.selic.value / 100) / (1 + LX.data.ipca12m.value / 100) - 1) * 100;
        if (macroOk) { LX.data.live = true; cacheSet('macro', { selic: LX.data.selic, cdi: LX.data.cdi, ipca12m: LX.data.ipca12m, ipcaMes: LX.data.ipcaMes }); }
        LX.fill();
        document.dispatchEvent(new CustomEvent('lx:macro', { detail: LX.data }));
    };

    LX.loadPTAX = async function () {
        // Procura a PTAX do dia útil mais recente (até 7 dias para trás)
        let d = LX.todayBRT();
        for (let i = 0; i < 7; i++) {
            const s = `${pad(d.getMonth() + 1)}-${pad(d.getDate())}-${d.getFullYear()}`;
            try {
                const j = await getJSON(`https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='${s}'&$format=json`);
                if (j.value && j.value.length) {
                    const v = j.value[j.value.length - 1];
                    LX.data.ptax = { buy: v.cotacaoCompra, sell: v.cotacaoVenda, date: LX.br(d) };
                    cacheSet('ptax', LX.data.ptax);
                    LX.data.ptaxTried = true; LX.fill();
                    return;
                }
            } catch (_) { break; }
            d = addDays(d, -1);
        }
        LX.data.ptaxTried = true; LX.fill();
    };

    LX.fxPairs = ['USD-BRL', 'EUR-BRL', 'GBP-BRL', 'BTC-BRL', 'ETH-BRL', 'USD-JPY', 'EUR-USD', 'ARS-BRL', 'CNY-BRL'];
    LX.loadFX = async function () {
        try {
            const j = await getJSON('https://economia.awesomeapi.com.br/last/' + LX.fxPairs.join(','));
            Object.values(j).forEach(q => {
                LX.data.fx[q.code + q.codein] = {
                    bid: parseFloat(q.bid), ask: parseFloat(q.ask), pct: parseFloat(q.pctChange),
                    high: parseFloat(q.high), low: parseFloat(q.low), name: q.name,
                    time: new Date(+q.timestamp * 1000)
                };
            });
            LX.data.fxOk = true; LX.data.live = true; LX.data.fxCached = false;
            cacheSet('fx', LX.data.fx);
        } catch (_) { if (!LX.data.fxCached) LX.data.fxOk = false; }
        LX.data.fxTried = true;
        LX.fill();
        document.dispatchEvent(new CustomEvent('lx:fx', { detail: LX.data.fx }));
    };

    // Boletim Focus — mediana das expectativas anuais (base de cálculo 0 = todos os respondentes)
    LX.loadFocus = async function (indicators, years) {
        const out = {};
        await Promise.allSettled(indicators.map(async (ind) => {
            const filter = encodeURIComponent(`Indicador eq '${ind}' and baseCalculo eq 0`);
            const url = `https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?$top=40&$filter=${filter}&$orderby=Data%20desc&$format=json&$select=Indicador,IndicadorDetalhe,Data,DataReferencia,Mediana,numeroRespondentes`;
            const j = await getJSON(url, 12000);
            const rows = (j.value || []).filter(r => !r.IndicadorDetalhe || r.IndicadorDetalhe === 'null');
            const latest = rows.length ? rows[0].Data : null;
            out[ind] = { date: latest, byYear: {}, prevByYear: {} };
            years.forEach(y => {
                const sameYear = rows.filter(r => r.DataReferencia === String(y));
                if (sameYear[0]) out[ind].byYear[y] = sameYear[0].Mediana;
                const prev = sameYear.find(r => r.Data < (sameYear[0] && sameYear[0].Data));
                if (prev) out[ind].prevByYear[y] = prev.Mediana;
            });
        }));
        return out;
    };

    // Preenche elementos declarativos: <span data-lx="selic"></span>
    LX.fill = function () {
        const d = LX.data, usd = d.fx.USDBRL;
        const map = {
            selic: LX.pct(d.selic.value), 'selic-src': `${d.selic.src} · ${d.selic.date}`,
            cdi: LX.pct(d.cdi.value), 'cdi-src': `${d.cdi.src} · ${d.cdi.date}`,
            ipca12m: LX.pct(d.ipca12m.value), 'ipca-src': `${d.ipca12m.src} · ${d.ipca12m.date}`,
            ipcames: LX.pct(d.ipcaMes.value, 2, true),
            real: d.realRate != null ? LX.pct(d.realRate) : LX.pct(((1 + d.selic.value / 100) / (1 + d.ipca12m.value / 100) - 1) * 100),
            usd: usd ? LX.num(usd.bid, 4) : '—',
            'usd-pct': usd ? LX.pct(usd.pct, 2, true) : '',
            ptax: d.ptax ? `${LX.num(d.ptax.sell, 4)} (${d.ptax.date})` : '—',
            'ptax-v': d.ptax ? LX.num(d.ptax.sell, 4) : '—', 'ptax-d': d.ptax ? d.ptax.date : ''
        };
        const waiting = { usd: !usd && !d.fxTried, 'usd-pct': !usd && !d.fxTried, ptax: !d.ptax && !d.ptaxTried, 'ptax-v': !d.ptax && !d.ptaxTried };
        Object.entries(map).forEach(([k, v]) => document.querySelectorAll(`[data-lx="${k}"]`).forEach(el => { el.textContent = v; el.classList.toggle('lx-skel', !!waiting[k]); }));
        if (d.fxTried || usd) document.querySelectorAll('[data-lx-skel="fx"]').forEach(el => el.classList.remove('lx-skel'));
        if (usd) document.querySelectorAll('[data-lx="usd-pct"]').forEach(el => el.className = LX.signClass(usd.pct));
        document.querySelectorAll('[data-lx-feed]').forEach(el => {
            el.innerHTML = d.live
                ? '<span class="w-2 h-2 bg-emerald-400 inline-block animate-pulse"></span>DADOS OFICIAIS CONECTADOS'
                : d.cachedAt
                    ? `<span class="w-2 h-2 bg-sky-400 inline-block"></span>ÚLTIMOS DADOS · ${d.cachedAt}`
                    : `<span class="w-2 h-2 bg-amber-400 inline-block"></span>VALORES DE REFERÊNCIA (${d.selic.date})`;
        });
    };

    /* ------------------------------------------------------------------ TRADINGVIEW */
    LX._tvWidgets = [];
    // Widgets só carregam quando chegam perto da tela (economiza dezenas de requisições no primeiro acesso)
    const tvIO = 'IntersectionObserver' in window ? new IntersectionObserver(entries => entries.forEach(en => {
        if (!en.isIntersecting) return;
        tvIO.unobserve(en.target);
        const w = LX._tvWidgets.find(x => x.id === en.target.id); if (w) LX.tv(w.id, w.type, w.cfg, true);
    }), { rootMargin: '400px 0px' }) : null;
    LX.tv = function (id, type, cfg, now) {
        const host = document.getElementById(id);
        if (!host) return;
        // guarda sempre a configuração mais recente (ex.: trocar de ação troca o gráfico)
        const reg = LX._tvWidgets.find(w => w.id === id);
        if (reg) { reg.type = type; reg.cfg = cfg; } else LX._tvWidgets.push({ id, type, cfg });
        if (!now && host.dataset.tvLoaded) now = true;  // já carregado uma vez: recarrega na hora com o símbolo novo
        // Faixa de cotações (topo): carrega quando o navegador estiver livre, depois da primeira pintura
        if (!now && type === 'ticker-tape') {
            if (!host.dataset.tvWaiting) {
                host.dataset.tvWaiting = '1'; host.innerHTML = '<div class="lx-skel-block"></div>';
                const go = () => LX.tv(id, type, cfg, true);
                const idle = () => ('requestIdleCallback' in window ? requestIdleCallback(go, { timeout: 2500 }) : setTimeout(go, 1200));
                if (document.readyState === 'complete') idle(); else addEventListener('load', idle, { once: true });
            }
            return;
        }
        if (!now && tvIO) {
            if (!host.dataset.tvWaiting) { host.dataset.tvWaiting = '1'; host.innerHTML = '<div class="lx-skel-block"></div>'; tvIO.observe(host); }
            return;
        }
        host.dataset.tvLoaded = '1';
        host.innerHTML = '';
        const wrap = document.createElement('div');
        wrap.className = 'tradingview-widget-container';
        wrap.style.height = '100%';
        wrap.innerHTML = '<div class="tradingview-widget-container__widget" style="height:100%"></div>';
        const s = document.createElement('script');
        s.src = `https://s3.tradingview.com/external-embedding/embed-widget-${type}.js`;
        s.async = true;
        s.text = JSON.stringify(Object.assign({ colorTheme: LX.isDark() ? 'dark' : 'light', isTransparent: true, locale: 'br' }, cfg));
        wrap.appendChild(s);
        host.appendChild(wrap);
    };

    /* ------------------------------------------------------------------ EVENTOS FIXOS 2026 */
    // Fontes: calendário oficial Copom 2026 (BCB, 24/06/2025) e calendário FOMC 2026 (Federal Reserve)
    LX.copom2026 = [
        ['2026-01-28', '15,00% (manutenção)'], ['2026-03-18', '14,75% (−0,25)'], ['2026-04-29', '14,50% (−0,25)'],
        ['2026-06-17', '14,25% (−0,25)'], ['2026-08-05', '14,00% (−0,25)'], ['2026-09-16', '13,75% (−0,25)'],
        ['2026-11-04', null], ['2026-12-09', null]
    ];
    LX.fomc2026 = ['2026-01-28', '2026-03-18', '2026-04-29', '2026-06-17', '2026-07-29', '2026-09-16', '2026-10-28', '2026-12-09'];
    // Agenda fixa (eventos que não são calculados por regra). Usada no Mercado Hoje e no Plano do Dia.
    // Formato: [data ISO, tipo, título, nota]. Tipos: copom, inflacao, global, feriado, focus, venc.
    LX.agendaFixed = [
        ['2026-11-02', 'feriado', 'Finados — B3 fechada', 'Sem pregão. Liquidações ficam para o dia útil seguinte.'],
        ['2026-11-03', 'global', 'Eleições de meio de mandato (EUA)', 'Composição do Congresso americano: impacto em Treasuries, dólar global e risco.'],
        ['2026-11-04', 'copom', 'Decisão do Copom (282ª reunião)', 'Comunicado após 18h30. Selic atual: 13,75%. Mercado acompanha ritmo de cortes.'],
        ['2026-11-06', 'global', 'Payroll — emprego nos EUA (out)', '10h30 BRT aprox. Mexe com Treasuries, DXY e, por tabela, WDO.'],
        ['2026-11-10', 'copom', 'Ata do Copom', '8h. Detalha o balanço de riscos e sinais para as próximas reuniões.'],
        ['2026-11-12', 'inflacao', 'IPCA de outubro (IBGE)', '9h. Inflação oficial — impacto direto nos vértices curtos do DI.'],
        ['2026-11-20', 'feriado', 'Consciência Negra — B3 fechada', 'Feriado nacional. Vencimento de opções de novembro antecipado para 19/11.'],
        ['2026-11-26', 'inflacao', 'IPCA-15 de novembro', '9h. Prévia da inflação.'],
        ['2026-12-09', 'copom', 'Superquarta: Copom + FOMC', 'Decisões de juros no Brasil (18h30) e nos EUA (16h BRT) no mesmo dia.'],
        ['2026-12-11', 'inflacao', 'IPCA de novembro (IBGE)', '9h.'],
        ['2026-12-24', 'feriado', 'Véspera de Natal — sem pregão', 'B3 fechada.'],
        ['2026-12-31', 'feriado', 'Último dia do ano — sem pregão', 'B3 fechada.']
    ];
    LX.parseISO = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };

    /* ------------------------------------------------------------------ CABEÇALHO / RODAPÉ COMUNS */
    const LOGO = `<svg class="w-11 h-11 shrink-0" viewBox="0 0 120 120" fill="none" aria-hidden="true">
        <polygon points="60,8 106,34.5 106,85.5 60,112 14,85.5 14,34.5" stroke="#00756C" stroke-width="7.5" stroke-linejoin="round" class="fill-white dark:fill-[#0B1626]"/>
        <path d="M34 48.5 L60 34.5 L86 48.5" stroke="#F39200" stroke-width="4.5" stroke-linecap="round"/>
        <circle cx="60" cy="34.5" r="8.5" fill="#F39200"/>
        <path d="M34 49.5 L60 62 L60 91.5 L34 79 Z" fill="#00756C"/><path d="M60 62 L86 49.5 L86 79 L60 91.5 Z" fill="#00B4A2"/></svg>`;
    const NAV = [
        { key: 'mercado', href: 'index.html', label: 'Mercado Hoje', icon: 'ph-pulse' },
        { key: 'macro', href: 'macro.html', label: 'Macro & Juros', icon: 'ph-chart-line' },
        { key: 'futuros', href: 'futuros.html', label: 'Futuros B3', icon: 'ph-chart-line-up', badge: 'NOVO' },
        { key: 'acoes', href: 'acoes.html', label: 'Ações B3', icon: 'ph-chart-bar' },
        { key: 'lab', href: 'laboratorio.html', label: 'Laboratório', icon: 'ph-student' }
    ];
    LX.renderChrome = function (active) {
        const top = document.getElementById('lx-topbar');
        if (top) top.innerHTML = `
        <div class="bg-[#07111E] text-slate-300 border-b border-slate-800 text-[11px] font-mono tabular-nums">
          <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-9 flex items-center justify-between gap-4 overflow-x-auto whitespace-nowrap thin-scroll">
            <div class="flex items-center gap-4">
              <span data-lx-feed class="inline-flex items-center gap-1.5 text-emerald-400 font-semibold"></span>
              <span class="text-slate-700">|</span>
              <span data-lx-session="b3f" class="inline-flex items-center gap-1"></span>
              <span data-lx-session="nyse" class="hidden sm:inline-flex items-center gap-1"></span>
              <span data-lx-session="lse" class="hidden md:inline-flex items-center gap-1"></span>
              <span class="text-slate-700">|</span>
              <span>SELIC <strong class="text-white" data-lx="selic"></strong></span>
              <span>CDI <strong class="text-lect-tealLight" data-lx="cdi"></strong></span>
              <span class="hidden sm:inline">IPCA 12M <strong class="text-white" data-lx="ipca12m"></strong></span>
              <span>USD/BRL <strong class="text-lect-orange" data-lx="usd"></strong> <span data-lx="usd-pct"></span></span>
            </div>
            <div class="flex items-center gap-3 text-[10px] text-slate-400">
              <span data-lx-clock class="text-slate-300 font-semibold"></span>
            </div>
          </div>
        </div>`;
        const head = document.getElementById('lx-header');
        if (head) {
            head.className = 'sticky top-0 z-40 bg-white/95 dark:bg-lect-bgDark/95 border-b border-slate-300 dark:border-lect-borderDark backdrop-blur-md';
            const link = (n, mobile) => {
                const on = n.key === active;
                const badge = n.badge ? `<span class="ml-1 px-1 text-[8px] font-bold bg-lect-orange text-lect-navy">${n.badge}</span>` : '';
                if (mobile) return `<a href="${n.href}" class="px-2.5 py-1 ${on ? 'bg-lect-navy text-white font-bold' : 'border border-slate-300 dark:border-lect-borderDark'}">${n.label}${badge}</a>`;
                return `<a href="${n.href}" class="flex items-center gap-1.5 px-2 xl:px-2.5 py-2 whitespace-nowrap transition-colors ${on ? 'text-lect-navy dark:text-white font-bold border-b-2 border-lect-teal' : 'hover:text-lect-teal'}"><i class="ph-bold ${n.icon} hidden xl:inline-block ${on ? 'text-lect-teal' : 'text-slate-400'}"></i>${n.label}${badge}</a>`;
            };
            head.innerHTML = `
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-[72px] flex items-center justify-between gap-4">
              <a href="index.html" class="flex items-center gap-3 shrink-0 group">${LOGO}
                <div><div class="flex items-center gap-2"><div class="text-2xl font-display font-bold tracking-tight leading-none"><span class="text-[#0C1A2A] dark:text-white">Lect</span><span class="text-[#009988] dark:text-[#00B4A2]">nex</span></div>
                <span class="px-1.5 py-0.5 bg-lect-navy text-white dark:bg-lect-teal/20 dark:text-lect-tealLight font-mono text-[9px] font-bold uppercase tracking-widest">TERMINAL</span></div>
                <span class="text-[11px] text-[#64748B] block mt-1">Inteligência de Mercado &amp; Educação Financeira</span></div></a>
              <nav class="hidden lg:flex items-center gap-0.5 xl:gap-1 text-[13px] font-medium text-slate-600 dark:text-slate-300">${NAV.map(n => link(n)).join('')}</nav>
              <div class="flex items-center gap-2">
                <button onclick="LX.openPalette()" class="hidden sm:flex shrink-0 whitespace-nowrap items-center justify-between gap-3 px-3 py-2 border border-slate-300 dark:border-lect-borderDark bg-slate-50 dark:bg-lect-cardDark text-xs font-mono text-slate-500 hover:border-lect-teal"><span class="inline-flex items-center gap-1.5"><i class="ph ph-magnifying-glass text-lect-teal"></i><span class="hidden xl:inline">Buscar ativo ou ferramenta</span></span></button>
                <button onclick="LX.openPalette()" title="Buscar" aria-label="Buscar ativo ou ferramenta" class="sm:hidden p-2.5 border border-slate-300 dark:border-lect-borderDark bg-white dark:bg-lect-cardDark hover:border-lect-teal"><i class="ph-bold ph-magnifying-glass text-lg text-lect-teal"></i></button>
                <button onclick="toggleTheme()" title="Alternar tema" aria-label="Alternar tema claro/escuro" class="p-2.5 border border-slate-300 dark:border-lect-borderDark bg-white dark:bg-lect-cardDark hover:border-lect-teal"><i class="ph-fill ph-moon text-lg dark:hidden"></i><i class="ph-fill ph-sun text-lg hidden dark:block text-lect-orange"></i></button>
              </div>
            </div>
            <div class="lg:hidden border-t border-slate-200 dark:border-lect-borderDark bg-slate-50 dark:bg-lect-cardDark px-4 py-2 flex items-center gap-2 overflow-x-auto font-mono text-xs whitespace-nowrap thin-scroll">${NAV.map(n => link(n, true)).join('')}</div>`;
        }
        const foot = document.getElementById('lx-footer');
        if (foot) foot.innerHTML = `
        <footer class="bg-[#07111E] text-slate-400 border-t-2 border-lect-teal mt-12">
          <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-8 pb-8 border-b border-slate-800">
              <div class="lg:col-span-4 space-y-3">
                <div class="text-2xl font-display font-bold text-white">Lect<span class="text-lect-tealLight">nex</span></div>
                <p class="text-xs leading-relaxed">Leitura de mercado conectada à educação financeira: macroeconomia, juros, câmbio, futuros e ações da B3 explicados com dados oficiais.</p>
                <div data-lx-news="compacto" class="hidden pt-2"></div>
              </div>
              <div class="lg:col-span-3 space-y-1.5 font-mono text-xs">
                <span class="text-white font-bold uppercase tracking-wider block mb-2">Módulos</span>
                ${NAV.map(n => `<a href="${n.href}" class="block hover:text-lect-tealLight">${n.label}</a>`).join('')}
                <a href="glossario.html" class="block hover:text-lect-tealLight">Glossário do Trader</a>
                <a href="semana/" class="block hover:text-lect-tealLight">Agenda da semana</a>
                <a href="leitura/" class="block hover:text-lect-tealLight">Arquivo da Leitura</a>
                <a href="comece.html" class="block hover:text-lect-tealLight">Comece por aqui</a>
                <a href="sobre.html" class="block hover:text-lect-tealLight">Sobre o Lectnex</a>
                <a href="status.html" class="block hover:text-lect-tealLight">Status do site</a>
                <a href="privacidade.html" class="block hover:text-lect-tealLight">Privacidade e cookies</a>
                <button type="button" id="lx-install" class="hidden mt-2 items-center gap-1.5 px-2.5 py-1.5 border border-lect-tealLight/50 text-lect-tealLight hover:bg-lect-tealLight/10"><i class="ph-bold ph-download-simple"></i>Instalar app no celular</button>
                <a href="https://www.instagram.com/lectnex.oficial/" target="_blank" rel="noopener" class="mt-2 flex items-center gap-1.5 hover:text-lect-tealLight"><i class="ph-bold ph-instagram-logo"></i>Instagram @lectnex.oficial</a>
                <a href="https://www.tiktok.com/@lectnex" target="_blank" rel="noopener" class="flex items-center gap-1.5 hover:text-lect-tealLight"><i class="ph-bold ph-tiktok-logo"></i>TikTok @lectnex</a>
                <a href="https://x.com/lectnex" target="_blank" rel="noopener" class="flex items-center gap-1.5 hover:text-lect-tealLight"><i class="ph-bold ph-x-logo"></i>X @lectnex</a>
                <a href="mailto:contato@lectnex.com.br" class="mt-2 flex items-center gap-1.5 hover:text-lect-tealLight"><i class="ph-bold ph-envelope-simple"></i>contato@lectnex.com.br</a>
                <button type="button" id="lx-hc" class="mt-2 flex items-center gap-1.5 hover:text-lect-tealLight"><i class="ph-bold ph-circle-half"></i>Alto contraste</button>
                <button type="button" data-lx-push class="hidden mt-2 items-center gap-1.5 px-2.5 py-1.5 border border-lect-orange/60 text-lect-orange hover:bg-lect-orange/10"><i class="ph-bold ph-bell-ringing"></i>Alertas no celular</button>
                <span id="lx-install-ios" class="hidden mt-2 text-[10px] leading-snug text-slate-400"><i class="ph-bold ph-device-mobile"></i> iPhone: toque em Compartilhar e depois em "Adicionar à Tela de Início" para usar como app.</span>
              </div>
              <div class="lg:col-span-5 space-y-1.5 font-mono text-[11px]">
                <span class="text-white font-bold uppercase tracking-wider block mb-2">Fontes de dados</span>
                <span class="block">• Selic, CDI, IPCA, PTAX e Focus: Banco Central do Brasil (SGS / Olinda) — oficiais</span>
                <span class="block">• Câmbio e cripto: AwesomeAPI — cotações com atraso de alguns segundos</span>
                <span class="block">• Gráficos, notícias e agenda global: widgets TradingView</span>
                <span class="block">• Ações: brapi.dev (atraso de ~30 min) · Calendário de vencimentos: regras B3</span>
                <span class="block text-amber-400/90">• Itens marcados <span class="lx-demo">SIMULAÇÃO</span> são dados fictícios para fins didáticos</span>
              </div>
            </div>
            <div class="pt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[11px] text-slate-500">
              <p class="max-w-4xl"><strong class="text-slate-300">Aviso legal:</strong> conteúdo exclusivamente educacional e informativo. Nada aqui constitui recomendação de compra, venda ou manutenção de valores mobiliários, nem relatório de análise nos termos da Resolução CVM nº 20. Operar derivativos envolve alavancagem e risco de perdas superiores ao capital. Rentabilidade passada ou simulada não garante resultado futuro. Confirme sempre dados e horários nas fontes oficiais.</p>
              <div class="shrink-0 flex flex-col items-start sm:items-end gap-1.5 font-mono">
                <a href="status.html" id="lx-status" class="inline-flex items-start gap-1.5 text-slate-400 hover:text-lect-tealLight" title="Horário da última atualização de cada dado (Brasília) · ver página de status"><span class="lx-dot mt-1 shrink-0 w-2 h-2 rounded-full bg-slate-500"></span><span>Verificando dados…</span></a>
                <span>&copy; ${new Date().getFullYear()} Lectnex</span>
              </div>
            </div>
          </div>
        </footer>`;
        buildPalette();
    };

    /* ------------------------------------------------------------------ COMANDO LECTNEX ("/" ou Ctrl/Cmd+K) */
    // [categoria, código, título, descrição, link, ícone, palavras-chave]
    const CMD = [
        ['futuros', 'PLANO', 'Plano do Dia', 'Checklist pré-mercado, limite de perda e placar do dia', 'futuros.html#plano', 'ph-clipboard-text', 'plano dia checklist pre mercado disciplina limite perda placar rotina'],
        ['futuros', 'DIARIO', 'Diário de Trades', 'Histórico mensal, curva de capital, calendário e DARF automático', 'futuros.html#diario', 'ph-notebook', 'diario journal historico operacoes darf imposto ir curva capital calendario exportar planilha'],
        ['futuros', 'ROLAGEM', 'Placar de vencimento', 'Contagem regressiva até o último pregão de WIN e WDO', 'futuros.html#placar', 'ph-timer', 'rolagem placar contagem vencimento ultimo pregao win wdo contrato vigente'],
        ['futuros', 'VENC', 'Vencimentos', 'WIN, WDO, DI1 e opções pelas regras da B3', 'futuros.html#vencimentos', 'ph-calendar-check', 'vencimento rolagem contrato vigente serie'],
        ['futuros', 'SPEC', 'Especificações dos contratos', 'Valor do ponto, tick, horário, margem', 'futuros.html#specs', 'ph-list-checks', 'especificacao ponto tick lote horario'],
        ['futuros', 'RISCO', 'Calculadora de risco', 'Tamanho de posição, stop, alvo, expectativa', 'futuros.html#risco', 'ph-shield-check', 'gestao stop alvo posicao contratos day trade'],
        ['futuros', 'KELLY', 'Quanto arriscar por trade', 'Critério de Kelly e zona de quebra', 'futuros.html#risco', 'ph-chart-line-up', 'kelly risco percentual capital drawdown'],
        ['futuros', 'DJ', 'Dólar futuro justo', 'Paridade: spot × diferencial de juros', 'futuros.html#paridade', 'ph-currency-dollar', 'dolar justo paridade wdo cupom cambial'],
        ['futuros', 'IRDT', 'IR de day trade', 'DARF automático no Diário: 20% sobre o lucro e dedo-duro', 'futuros.html#diario', 'ph-receipt', 'imposto darf day trade irrf dedo duro'],
        ['mercado', 'AGENDA', 'Agenda da semana', 'Copom, FOMC, IPCA, payroll, vencimentos', 'index.html#agenda', 'ph-calendar-dots', 'agenda eventos calendario copom fomc payroll'],
        ['mercado', 'COPOM', 'Copom: o que esperar', 'Expectativa, cenários e reação de juros, dólar e bolsa', 'copom.html', 'ph-bank', 'copom selic decisao juros reuniao banco central comunicado'],
        ['mercado', 'COMECE', 'Comece por aqui', 'O Lectnex em 1 minuto: as principais ferramentas', 'comece.html', 'ph-rocket-launch', 'comece inicio novo tour guia como usar'],
        ['mercado', 'FOCUS', 'Boletim Focus e Copom', 'Expectativas do mercado e decisões da Selic', 'macro.html#juros', 'ph-trend-up', 'focus expectativa juros curva selic copom'],
        ['mercado', 'FX', 'Câmbio e cripto ao vivo', 'Dólar, euro, bitcoin, PTAX', 'index.html#cambio', 'ph-arrows-left-right', 'cambio dolar euro bitcoin cripto ptax moeda'],
        ['mercado', 'CURVA', 'Curva de juros (DI1)', 'Como ler a curva e os vértices vigentes', 'macro.html#curva', 'ph-chart-line', 'curva juros di di1 vertice estrutura termo'],
        ['mercado', 'ESE', 'E se…? Mapa de reações', 'Como Copom, IPCA, Fed e fiscal chegam ao WIN e WDO', 'macro.html#educacao', 'ph-git-branch', 'cenario reacao noticia transmissao copom ipca fed payroll fiscal china e se'],
        ['mercado', 'REGIME', 'Regimes de risco', 'Risk-on, risk-off e como os ativos reagem', 'macro.html#regimes', 'ph-gauge', 'regime risco risk on off aversao apetite intermercado'],
        ['mercado', 'MAPA', 'Mapa de calor da B3', 'Ações do Ibovespa por setor, coloridas pela variação do dia', 'index.html#mapa', 'ph-squares-four', 'mapa calor heatmap setores acoes ibovespa fluxo variacao'],
        ['mercado', 'NEWS', 'Agora no mercado', 'Manchetes de maior impacto, a cada ~10 min', 'index.html#ultimas', 'ph-newspaper', 'noticias manchetes'],
        ['acoes', 'DONOS', 'Quem é dono da ação', 'Fundos com a ação na carteira (CVM)', 'acoes.html#donos', 'ph-users-three', 'fundos donos carteira cvm'],
        ['acoes', 'OPC', 'Laboratório de opções', 'Strangle, venda de call e de put', 'acoes.html#opcoes', 'ph-flask', 'opcoes call put strangle'],
        ['acoes', 'FLUXO', 'Fluxo estrangeiro', 'Entrada de capital estrangeiro em ações', 'acoes.html#fluxo', 'ph-arrows-down-up', 'fluxo estrangeiro captacao gringo'],
        ['lab', 'TRADE', 'Simulador compra/venda × CDI', 'Resultado com IR comparado ao CDI', 'laboratorio.html?tab=trade', 'ph-calculator', 'simulador compra venda cdi ir swing'],
        ['lab', 'JCP', 'Dividendos & JCP', 'Simulador com as regras de 2026', 'laboratorio.html?tab=proventos', 'ph-coins', 'dividendos jcp proventos renda passiva'],
        ['lab', 'BAZIN', 'Preço teto Bazin & Graham', 'Valuation simples por dividendos e lucro', 'laboratorio.html?tab=valuation', 'ph-scales', 'bazin graham preco teto valuation'],
        ['lab', 'RF', 'Comparador renda fixa', 'CDB × LCI/LCA × IPCA+', 'laboratorio.html?tab=rf', 'ph-bank', 'renda fixa cdb lci lca tesouro ipca'],
        ['lab', 'GLOSS', 'Glossário do Trader', '68 termos de juros, futuros, ações e risco explicados', 'glossario.html', 'ph-book-open-text', 'glossario termos dicionario significado o que e breakeven rolagem ajuste payroll kelly spread tick'],
        ['lab', 'SFN', 'Enciclopédia: Selic e CDI', 'Como funciona o sistema financeiro', 'laboratorio.html?tab=academia&licao=A1', 'ph-book-open', 'aprender selic cdi copom sistema financeiro enciclopedia'],
        ['lab', 'GUIA', 'Guia de ações', 'Ações, dividendos e JCP para iniciantes', 'laboratorio.html?tab=academia&licao=B1', 'ph-graduation-cap', 'aprender guia acoes iniciante enciclopedia']
    ];
    const STOCKS = [
        ['PETR4', 'Petrobras', 'Petróleo'], ['VALE3', 'Vale', 'Mineração'], ['ITUB4', 'Itaú Unibanco', 'Bancos'], ['BBAS3', 'Banco do Brasil', 'Bancos'],
        ['BBDC4', 'Bradesco', 'Bancos'], ['B3SA3', 'B3', 'Serviços financeiros'], ['WEGE3', 'WEG', 'Bens de capital'], ['PRIO3', 'PRIO', 'Petróleo'],
        ['ABEV3', 'Ambev', 'Bebidas'], ['ELET3', 'Eletrobras', 'Energia'], ['SUZB3', 'Suzano', 'Papel e celulose'], ['RENT3', 'Localiza', 'Locação'],
        ['MGLU3', 'Magazine Luiza', 'Varejo'], ['BPAC11', 'BTG Pactual', 'Bancos'], ['TAEE11', 'Taesa', 'Energia'], ['ITSA4', 'Itaúsa', 'Holding'],
        ['GGBR4', 'Gerdau', 'Siderurgia'], ['RADL3', 'Raia Drogasil', 'Farmácias'], ['EQTL3', 'Equatorial', 'Energia'], ['SBSP3', 'Sabesp', 'Saneamento'],
        ['VIVT3', 'Vivo', 'Telecom'], ['EMBR3', 'Embraer', 'Aeronáutica'], ['RAIL3', 'Rumo', 'Logística'], ['CMIG4', 'Cemig', 'Energia']
    ];
    const SHORT = { ROLAGEM: 'Rolagem', MAPA: 'Mapa de calor', PLANO: 'Plano do dia', DIARIO: 'Diário', CURVA: 'Curva DI', ESE: 'E se…?', REGIME: 'Regimes', VENC: 'Vencimentos', SPEC: 'Contratos', RISCO: 'Risco', KELLY: 'Kelly', DJ: 'Dólar justo', IRDT: 'IR day trade', AGENDA: 'Agenda', FOCUS: 'Focus', FX: 'Câmbio', NEWS: 'Notícias', DONOS: 'Fundos donos', OPC: 'Opções', FLUXO: 'Fluxo', TRADE: 'Simulador', JCP: 'Dividendos', BAZIN: 'Preço teto', RF: 'Renda fixa', SFN: 'Selic e CDI', GUIA: 'Guia ações', GLOSS: 'Glossário' };
    LX.paletteItems = CMD.map(c => [c[0].toUpperCase(), c[2], c[4]]); // compatibilidade
    const CATS = [['tudo', 'Tudo'], ['acoes', 'Ações'], ['futuros', 'Futuros'], ['mercado', 'Mercado'], ['lab', 'Laboratório']];
    const norm = t => String(t).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    const recents = {
        get() { try { return JSON.parse(localStorage.getItem('lectnex-recent') || '[]'); } catch (_) { return []; } },
        add(it) { try { const r = recents.get().filter(x => x.href !== it.href); r.unshift(it); localStorage.setItem('lectnex-recent', JSON.stringify(r.slice(0, 5))); } catch (_) { } }
    };
    let pal = { cat: 'tudo', sel: 0, rows: [] };

    // Respostas instantâneas: contas de pontos, indicadores, contrato vigente, expressões
    function instant(qRaw) {
        const q = norm(qRaw).replace(',', '.').trim(); if (!q) return null;
        const PVv = { win: 0.2, wdo: 10, ind: 1, dol: 50 };
        let m = q.match(/^(\d+(?:\.\d+)?)\s*(?:pts?|pontos?)?\s*(?:de\s+|no\s+|do\s+)?(win|wdo|ind|dol)\s*(?:x\s*)?(\d+)?\s*(?:contratos?|ctts?)?$/);
        if (m) {
            const pts = +m[1], a = m[2], n = +(m[3] || 1), v = pts * PVv[a] * n;
            return { icon: 'ph-calculator', title: `${LX.num(pts, pts % 1 ? 1 : 0)} pts de ${a.toUpperCase()}${n > 1 ? ' × ' + n + ' contratos' : ''} = ${LX.brl(v)}`,
                sub: `Cada ponto vale ${LX.brl(PVv[a])} por contrato · digite "150 win 3" para 3 contratos`, href: 'futuros.html#risco', tag: 'CONTA' };
        }
        const now = () => {
            if (/^(win|indice|mini indice|ibov futuro)$/.test(q)) { const c = LX.upcomingWIN(1)[0]; return { icon: 'ph-chart-line-up', title: `Mini Índice vigente: ${c.code}`, sub: `vence ${LX.weekday(c.expiry)} ${LX.br(c.expiry)} · faltam ${c.du} dias úteis · R$ 0,20 por ponto`, href: 'futuros.html#vencimentos', tag: 'WIN' }; }
            if (/^(wdo|mini dolar|dolar futuro)$/.test(q)) { const c = LX.upcomingWDO(2), t = c[0].du <= 1 ? c[1] : c[0]; return { icon: 'ph-currency-dollar', title: `Mini Dólar vigente: ${t.code}`, sub: `vence ${LX.weekday(t.expiry)} ${LX.br(t.expiry)} · faltam ${t.du} dias úteis · R$ 10 por ponto`, href: 'futuros.html#vencimentos', tag: 'WDO' }; }
            if (/^(usd|dolar|dollar|usdbrl|usd\/brl)$/.test(q)) { const f = LX.data.fx.USDBRL; return { icon: 'ph-currency-dollar', title: f ? `Dólar comercial: R$ ${LX.num(f.bid, 4)}` : 'Dólar comercial', sub: f ? `${f.pct >= 0 ? '+' : ''}${LX.num(f.pct, 2)}% no dia · máx ${LX.num(f.high, 4)} · mín ${LX.num(f.low, 4)}` : 'carregando cotação...', href: 'index.html#cambio', tag: 'AO VIVO', cls: f ? LX.signClass(f.pct) : '' }; }
            if (/^(eur|euro)$/.test(q)) { const f = LX.data.fx.EURBRL; return { icon: 'ph-currency-eur', title: f ? `Euro: R$ ${LX.num(f.bid, 4)}` : 'Euro', sub: f ? `${f.pct >= 0 ? '+' : ''}${LX.num(f.pct, 2)}% no dia` : 'carregando...', href: 'index.html#cambio', tag: 'AO VIVO' }; }
            if (/^(btc|bitcoin)$/.test(q)) { const f = LX.data.fx.BTCBRL; return { icon: 'ph-currency-btc', title: f ? `Bitcoin: ${LX.brl(f.bid, 0)}` : 'Bitcoin', sub: f ? `${f.pct >= 0 ? '+' : ''}${LX.num(f.pct, 2)}% no dia` : 'carregando...', href: 'index.html#cambio', tag: 'AO VIVO' }; }
            if (/^(selic|copom)$/.test(q)) return { icon: 'ph-bank', title: `Selic: ${LX.pct(LX.data.selic.value)} ao ano`, sub: `CDI ${LX.pct(LX.data.cdi.value)} · fonte BCB · ${LX.data.selic.date || ''}`, href: 'macro.html#juros', tag: 'BCB' };
            if (/^cdi$/.test(q)) return { icon: 'ph-bank', title: `CDI: ${LX.pct(LX.data.cdi.value)} ao ano`, sub: `≈ ${LX.pct((Math.pow(1 + LX.data.cdi.value / 100, 1 / 12) - 1) * 100)} ao mês`, href: 'laboratorio.html?tab=rf', tag: 'BCB' };
            if (/^(ipca|inflacao)$/.test(q)) return { icon: 'ph-shopping-cart', title: `IPCA 12 meses: ${LX.pct(LX.data.ipca12m.value)}`, sub: `no mês: ${LX.pct(LX.data.ipcaMes.value)} (${LX.data.ipcaMes.date}) · juro real ≈ ${LX.pct(((1 + LX.data.selic.value / 100) / (1 + LX.data.ipca12m.value / 100) - 1) * 100)}`, href: 'macro.html#juros', tag: 'IBGE' };
            return null;
        };
        const r = now(); if (r) return r;
        if (/^[\d\s.+\-*/()%]+$/.test(q) && /[+\-*/%]/.test(q) && /\d/.test(q)) {
            try { const v = Function('"use strict";return (' + q.replace(/(\d+(?:\.\d+)?)%/g, '($1/100)') + ')')(); if (isFinite(v)) return { icon: 'ph-equals', title: `= ${LX.num(v, Math.abs(v) < 100 && v % 1 ? 4 : 2)}`, sub: 'calculadora rápida', tag: 'CONTA' }; } catch (_) { }
        }
        return null;
    }

    function search(qRaw) {
        const q = norm(qRaw).trim(), toks = q.split(/\s+/).filter(Boolean), out = [];
        const score = (code, hay) => {
            if (!q) return 1;
            const c = norm(code);
            if (c === q) return 100; if (c.startsWith(q)) return 80;
            const h = ' ' + hay.replace(/[^a-z0-9]+/g, ' ');
            return toks.every(t => h.includes(' ' + t)) ? 40 + (h.startsWith(' ' + toks[0]) ? 10 : 0) : 0;
        };
        if (pal.cat === 'tudo' || pal.cat === 'acoes') STOCKS.forEach(([t, n, sec]) => {
            const sc = score(t, norm(`${t} ${n} ${sec}`)); if (sc && (q || pal.cat === 'acoes')) out.push({ sc: sc + 5, cat: 'acoes', code: t, title: n, sub: `${sec} · cotação, gráfico, fundos donos e opções`, href: 'acoes.html?ticker=' + t, icon: 'ph-chart-bar' });
        });
        CMD.forEach(([cat, code, title, sub, href, icon, kw]) => {
            if (pal.cat !== 'tudo' && pal.cat !== cat) return;
            const sc = score(code, norm(`${code} ${title} ${sub} ${kw}`)); if (sc) out.push({ sc, cat, code, title, sub, href, icon });
        });
        const tk = qRaw.trim().toUpperCase();
        if (/^[A-Z][A-Z0-9]{3}\d{1,2}$/.test(tk) && !STOCKS.some(s => s[0] === tk)) out.unshift({ sc: 200, cat: 'acoes', code: tk, title: `Abrir ${tk}`, sub: 'buscar cotação e gráfico em Ações B3', href: 'acoes.html?ticker=' + tk, icon: 'ph-magnifying-glass' });
        return out.sort((a, b) => b.sc - a.sc).slice(0, q ? 12 : 40);
    }

    const catLabel = { acoes: 'AÇÃO', futuros: 'FUTUROS', mercado: 'MERCADO', lab: 'LAB' };
    function rowHTML(r, i) {
        const on = i === pal.sel;
        return `<a href="${r.href || '#'}" data-i="${i}" class="lx-pr flex items-center gap-3 px-4 py-2.5 border-l-2 ${on ? 'bg-lect-teal/10 border-lect-orange' : 'border-transparent hover:bg-slate-50 dark:hover:bg-lect-bgDark'}">
            <span class="w-8 h-8 shrink-0 grid place-items-center ${r.instant ? 'bg-lect-orange text-white' : 'bg-slate-100 dark:bg-lect-bgDark text-lect-teal'}"><i class="ph-bold ${r.icon} text-base"></i></span>
            <span class="min-w-0 flex-1"><span class="flex items-center gap-2"><span class="font-bold text-[13px] ${r.cls || 'text-slate-800 dark:text-white'} truncate">${LX.esc(r.title)}</span></span>
            <span class="block text-[11px] text-slate-500 truncate">${LX.esc(r.sub || '')}</span></span>
            ${r.code ? `<span class="shrink-0 px-1.5 py-0.5 text-[10px] font-bold font-mono bg-lect-navy text-white">${LX.esc(r.code)}</span>` : ''}
            <span class="shrink-0 hidden sm:inline text-[9px] font-bold text-slate-400 w-14 text-right">${r.tag || catLabel[r.cat] || ''}</span></a>`;
    }

    function renderPalette() {
        const el = document.getElementById('lx-palette'); if (!el) return;
        const qRaw = el.querySelector('#lx-palette-input').value, list = el.querySelector('#lx-palette-list');
        el.querySelectorAll('[data-cat]').forEach(b => b.className = 'px-2.5 py-1 text-[11px] font-bold whitespace-nowrap ' + (b.dataset.cat === pal.cat ? 'bg-lect-navy text-white dark:bg-lect-teal' : 'text-slate-500 hover:text-lect-teal'));
        let html = '', rows = [];
        const sec = t => `<div class="px-4 pt-3 pb-1 text-[10px] font-bold tracking-widest text-slate-400">${t}</div>`;
        const ans = instant(qRaw);
        if (ans) { ans.instant = true; rows.push(ans); html += sec('RESPOSTA RÁPIDA') + rowHTML(ans, 0); }
        if (!qRaw.trim() && pal.cat === 'tudo') {
            const rec = recents.get();
            if (rec.length) { html += sec('RECENTES'); rec.forEach(r => { r.icon = r.icon || 'ph-clock-counter-clockwise'; html += rowHTML(r, rows.length); rows.push(r); }); }
            const w = LX.upcomingWIN(1)[0], dd = LX.upcomingWDO(2), d = dd[0].du <= 1 ? dd[1] : dd[0], usd = LX.data.fx.USDBRL;
            html += sec('AGORA') + `<div class="grid grid-cols-2 sm:grid-cols-4 gap-px bg-slate-200 dark:bg-lect-borderDark mx-4 mb-1 font-mono tabular-nums">` +
                [['WIN vigente', w.code, `${w.du} DU p/ vencer`], ['WDO vigente', d.code, `${d.du} DU p/ vencer`], ['Selic', LX.pct(LX.data.selic.value), `CDI ${LX.pct(LX.data.cdi.value)}`], ['Dólar', usd ? 'R$ ' + LX.num(usd.bid, 3) : '—', usd ? `${usd.pct >= 0 ? '+' : ''}${LX.num(usd.pct, 2)}%` : 'carregando']]
                    .map(([l, v, n]) => `<div class="bg-white dark:bg-lect-cardDark p-2"><span class="block text-[9px] text-slate-400 uppercase">${l}</span><strong class="block text-sm text-slate-800 dark:text-white">${v}</strong><span class="text-[10px] text-slate-500">${n}</span></div>`).join('') + `</div>`;
            html += sec('COMANDOS · DIGITE O CÓDIGO E ENTER') + `<div class="flex flex-wrap gap-1.5 px-4 pb-3">` +
                CMD.map(c => `<button type="button" data-code="${c[1]}" title="${LX.esc(c[2])}" class="px-2 py-1 text-[10px] font-mono font-bold border border-slate-300 dark:border-lect-borderDark hover:border-lect-orange hover:text-lect-orange"><span class="text-lect-teal">${c[1]}</span> <span class="font-normal text-slate-500">${LX.esc(SHORT[c[1]] || c[2])}</span></button>`).join('') + `</div>`;
            html += sec('EXPERIMENTE') + `<div class="flex flex-wrap gap-1.5 px-4 pb-3">` + ['150 win', '5 wdo 2', 'PETR4', 'dólar', 'selic', '10000*1.5%'].map(x => `<button type="button" data-try="${x}" class="px-2 py-1 text-[11px] font-mono bg-slate-100 dark:bg-lect-bgDark hover:text-lect-orange">${x}</button>`).join('') + `</div>`;
        } else {
            const res = search(qRaw);
            if (res.length) {
                let last = null;
                res.forEach(r => { const g = qRaw.trim() ? 'RESULTADOS' : (catLabel[r.cat] || ''); if (g !== last) { html += sec(g); last = g; } html += rowHTML(r, rows.length); rows.push(r); });
            } else if (!ans) html += `<div class="p-6 text-center text-xs text-slate-500">Nada encontrado para “${LX.esc(qRaw)}”. Tente um ticker (PETR4), um código (VENC, RISCO) ou uma conta (150 win).</div>`;
        }
        pal.rows = rows; if (pal.sel >= rows.length) pal.sel = Math.max(0, rows.length - 1);
        list.innerHTML = html;
        list.querySelectorAll('[data-code]').forEach(b => b.onclick = () => go(CMD.find(c => c[1] === b.dataset.code)));
        list.querySelectorAll('[data-try]').forEach(b => b.onclick = () => { const i = el.querySelector('#lx-palette-input'); i.value = b.dataset.try; pal.sel = 0; renderPalette(); i.focus(); });
        list.querySelectorAll('.lx-pr').forEach(a => {
            a.addEventListener('mousemove', () => { const i = +a.dataset.i; if (i !== pal.sel) { pal.sel = i; paintSel(); } });
            a.addEventListener('click', e => { e.preventDefault(); openRow(pal.rows[+a.dataset.i]); });
        });
    }
    function paintSel() {
        document.querySelectorAll('#lx-palette-list .lx-pr').forEach(a => {
            const on = +a.dataset.i === pal.sel;
            a.classList.toggle('bg-lect-teal/10', on); a.classList.toggle('border-lect-orange', on); a.classList.toggle('border-transparent', !on);
            if (on) a.scrollIntoView({ block: 'nearest' });
        });
    }
    function go(c) { if (c) openRow({ code: c[1], title: c[2], sub: c[3], href: c[4], icon: c[5], cat: c[0] }); }
    function openRow(r) {
        if (!r || !r.href) return;
        recents.add({ code: r.code, title: r.title, sub: r.sub, href: r.href, icon: r.icon, cat: r.cat, tag: r.tag && !r.instant ? r.tag : undefined });
        LX.closePalette();
        LX.track('select_content', { content_type: 'comando', item_id: r.code || r.title });
        const [path, hash] = r.href.split('#'), here = location.pathname.split('/').pop() || 'index.html';
        if (path === here && hash && !path.includes('?')) { const t = document.getElementById(hash); if (t) { t.scrollIntoView({ behavior: 'smooth' }); history.replaceState(null, '', '#' + hash); return; } }
        location.href = r.href;
    }

    function buildPalette() {
        if (document.getElementById('lx-palette')) return;
        const el = document.createElement('div');
        el.id = 'lx-palette';
        el.setAttribute('data-lx-modal', '');
        el.className = 'fixed inset-0 z-50 bg-lect-navy/70 backdrop-blur-sm hidden items-start justify-center pt-[8vh] p-3';
        el.innerHTML = `
          <div class="bg-white dark:bg-lect-cardDark border border-slate-300 dark:border-lect-borderDark border-t-4 border-t-lect-orange max-w-2xl w-full shadow-2xl flex flex-col max-h-[84vh]">
            <div class="flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-lect-borderDark">
              <span class="font-mono font-bold text-lect-orange text-lg leading-none">&gt;</span>
              <input id="lx-palette-input" autocomplete="off" spellcheck="false" class="flex-1 min-w-0 bg-transparent outline-none text-base font-mono text-slate-800 dark:text-white placeholder:text-slate-400" placeholder="Buscar ativo, ferramenta ou fazer uma conta — ex.: PETR4, VENC, 150 win">
              <button onclick="LX.closePalette()" class="shrink-0 px-1.5 py-0.5 text-[10px] font-mono border border-slate-300 dark:border-lect-borderDark text-slate-500">ESC</button>
            </div>
            <div class="flex items-center gap-1 px-3 py-2 border-b border-slate-200 dark:border-lect-borderDark overflow-x-auto thin-scroll">${CATS.map(([k, l]) => `<button type="button" data-cat="${k}">${l}</button>`).join('')}</div>
            <div id="lx-palette-list" class="flex-1 overflow-y-auto thin-scroll pb-2"></div>
            <div class="hidden sm:flex items-center justify-between gap-3 px-4 py-2 border-t border-slate-200 dark:border-lect-borderDark bg-slate-50 dark:bg-lect-bgDark text-[10px] font-mono text-slate-500">
              <span class="flex items-center gap-3"><span><kbd class="px-1 border border-slate-300 dark:border-lect-borderDark">↑</kbd><kbd class="px-1 border border-slate-300 dark:border-lect-borderDark">↓</kbd> navegar</span><span><kbd class="px-1 border border-slate-300 dark:border-lect-borderDark">Enter</kbd> abrir</span><span><kbd class="px-1 border border-slate-300 dark:border-lect-borderDark">Tab</kbd> categoria</span></span>
              <span class="inline-flex items-center gap-1.5"><i class="ph-bold ph-terminal-window text-lect-orange"></i>COMANDO LECTNEX</span>
            </div>
          </div>`;
        document.body.appendChild(el);
        el.addEventListener('click', e => { if (e.target === el) LX.closePalette(); });
        el.querySelectorAll('[data-cat]').forEach(b => b.onclick = () => { pal.cat = b.dataset.cat; pal.sel = 0; renderPalette(); el.querySelector('#lx-palette-input').focus(); });
        const inp = el.querySelector('#lx-palette-input');
        inp.addEventListener('input', () => { pal.sel = 0; renderPalette(); });
        inp.addEventListener('keydown', e => {
            if (e.key === 'ArrowDown') { e.preventDefault(); if (pal.rows.length) { pal.sel = (pal.sel + 1) % pal.rows.length; paintSel(); } }
            else if (e.key === 'ArrowUp') { e.preventDefault(); if (pal.rows.length) { pal.sel = (pal.sel - 1 + pal.rows.length) % pal.rows.length; paintSel(); } }
            else if (e.key === 'Tab') { e.preventDefault(); const i = CATS.findIndex(c => c[0] === pal.cat); pal.cat = CATS[(i + (e.shiftKey ? CATS.length - 1 : 1)) % CATS.length][0]; pal.sel = 0; renderPalette(); }
            else if (e.key === 'Enter') {
                e.preventDefault();
                const exact = CMD.find(c => c[1] === inp.value.trim().toUpperCase());
                if (exact) return go(exact);
                const r = pal.rows[pal.sel]; if (r && r.href) openRow(r);
            }
        });
        document.addEventListener('lx:fx', () => { if (!el.classList.contains('hidden')) renderPalette(); });
    }
    LX.openPalette = function () {
        const el = document.getElementById('lx-palette'); if (!el) return;
        el.classList.remove('hidden'); el.classList.add('flex');
        const inp = document.getElementById('lx-palette-input'); inp.value = ''; pal.cat = 'tudo'; pal.sel = 0; renderPalette();
        setTimeout(() => inp.focus(), 30);
    };
    LX.closePalette = function () { const el = document.getElementById('lx-palette'); if (el) { el.classList.add('hidden'); el.classList.remove('flex'); } };
    document.addEventListener('keydown', e => {
        const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);
        if ((!typing && e.key === '/') || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k')) { e.preventDefault(); LX.openPalette(); }
    });

    /* ------------------------------------------------------------------ NEWSLETTER (Buttondown) */
    // Qualquer elemento <div data-lx-news="compacto|completo"> vira um formulário de inscrição quando LX.config.newsletter está preenchido.
    let newsCount = null;
    let tgCount = 0;
    function tgBtn(kind) { // botão "Seguir no Telegram" (kind: escuro | claro | link)
        const tg = LX.config.telegram; if (!tg) return '';
        const href = 'https://t.me/' + encodeURIComponent(tg), n = tgCount >= 25 ? ` · ${tgCount.toLocaleString('pt-BR')}` : '';
        if (kind === 'link') return `<a href="${href}" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 text-[#1C7FB3] dark:text-[#4CB9F0] hover:underline font-mono text-[11px] font-bold"><i class="ph-fill ph-telegram-logo text-sm"></i>Seguir no Telegram${n}</a>`;
        return `<a href="${href}" target="_blank" rel="noopener" class="inline-flex items-center justify-center gap-2 px-4 py-2 bg-[#1C7FB3] hover:bg-[#176B97] text-white font-mono text-xs font-bold whitespace-nowrap"><i class="ph-fill ph-telegram-logo text-base"></i>SEGUIR NO TELEGRAM${n}</a>`;
    }
    function newsForms() {
        const user = LX.config.newsletter;
        // prova social: só a partir de 25 inscritos
        const social = newsCount >= 25 ? `Junte-se a ${newsCount.toLocaleString('pt-BR')} traders que recebem a Leitura do Dia.` : '';
        document.querySelectorAll('[data-lx-news]').forEach(el => {
            if (!user) { el.classList.add('hidden'); return; }
            const kind = el.dataset.lxNews, full = kind === 'completo', action = 'https://buttondown.com/api/emails/embed-subscribe/' + encodeURIComponent(user);
            const form = `<form action="${action}" method="post" target="_blank" class="flex flex-col sm:flex-row gap-2 ${full ? 'mt-4' : ''}">
                <input type="hidden" name="embed" value="1"><input type="hidden" name="tag" value="site">
                <label class="sr-only" for="nl-${full ? 'f' : 'c'}">Seu e-mail</label>
                <input id="nl-${full ? 'f' : 'c'}" type="email" name="email" required placeholder="seu@email.com" autocomplete="email" class="lx-input flex-1 !text-sm">
                <button type="submit" class="px-4 py-2 bg-lect-orange hover:brightness-110 text-lect-navy font-mono text-xs font-bold whitespace-nowrap"><i class="ph-bold ph-envelope-simple"></i> RECEBER GRÁTIS</button></form>`;
            el.classList.remove('hidden');
            if (kind === 'chamada') {
                el.innerHTML = `<div class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 border border-dashed border-lect-orange/50 bg-lect-orange/5">
                    <div class="flex items-start gap-3"><i class="ph-duotone ph-envelope-simple-open text-3xl text-lect-orange shrink-0"></i><div><strong class="block font-display">${LX.esc(el.dataset.titulo || 'Gostou desta ferramenta?')}</strong><span class="text-sm text-slate-600 dark:text-slate-400">Receba a <strong>Leitura do Dia</strong> às 7h40: termômetro de WIN e WDO, agenda e as notícias que mexem no preço. Grátis.${social ? ` <strong class="text-lect-orange">${social}</strong>` : ''}</span></div></div>
                    <div class="md:w-[420px] shrink-0">${form}${LX.config.telegram ? `<div class="mt-2 text-right">${tgBtn('link')} <span class="text-[11px] text-slate-500 font-mono">· alertas de surpresa em tempo real</span></div>` : ''}</div></div>`;
                return;
            }
            el.innerHTML = full
                ? `<div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center p-6 bg-lect-navy text-white border-l-4 border-lect-orange relative overflow-hidden"><div class="absolute inset-0 grid-bg opacity-30 pointer-events-none"></div>
                    <div class="relative lg:col-span-7"><span class="term-label !text-lect-orange font-bold">LEITURA DO DIA NO SEU E-MAIL</span><h3 class="font-display text-2xl font-bold mt-1">Comece o pregão já sabendo o que importa.</h3>
                    <p class="text-sm text-slate-300 mt-2">Todo dia às 7h40: termômetro de WIN e WDO, agenda com horários, as 5 notícias que mexem no preço e o que esperar. Grátis, sem spam, cancele quando quiser.</p></div>
                    <div class="relative lg:col-span-5">${form}<p class="text-[10px] text-slate-400 mt-2 font-mono">${social ? `<strong class="text-lect-orange">${social}</strong> · ` : ''}Conteúdo educacional · você confirma a inscrição pelo e-mail.</p>${LX.config.telegram ? `<div class="mt-3 pt-3 border-t border-white/10 flex flex-wrap items-center gap-3">${tgBtn('escuro')}<button type="button" data-lx-push class="hidden items-center justify-center gap-2 px-4 py-2 border border-lect-orange text-lect-orange hover:bg-lect-orange/10 font-mono text-xs font-bold"><i class="ph-bold ph-bell-ringing"></i>ALERTAS NO CELULAR</button><span class="text-[11px] text-slate-400">Prefere celular? A Leitura e os alertas de surpresa chegam no canal.</span></div>` : ''}</div></div>`
                : `<div class="font-mono text-[11px]"><span class="block text-slate-300 font-bold mb-1.5"><i class="ph-bold ph-envelope-simple text-lect-orange"></i> Leitura do Dia por e-mail, todo dia às 7h40</span>${form}${LX.config.telegram ? `<div class="mt-2">${tgBtn('link')}</div>` : ''}</div>`;
        });
        pushButtons();
    }

    /* ------------------------------------------------------------------ CONTRATOS VIGENTES E ÚLTIMO PREGÃO */
    // WIN: negocia até o próprio vencimento (quarta mais próxima do dia 15). WDO: até o último dia útil ANTES do vencimento
    // (1º dia útil do mês). Fechamento considerado: 18h25 de Brasília.
    LX.FUT_CLOSE = 18 * 60 + 25;
    LX.liveContracts = function () {
        const now = LX.nowBRT(), mins = now.getHours() * 60 + now.getMinutes();
        const prevBiz = d => { let x = LX.addDays(d, -1); while (!LX.isBusinessDay(x)) x = LX.addDays(x, -1); return x; };
        const pick = (list, lastOf) => {
            const rows = list.map(c => Object.assign({}, c, { lastTrade: lastOf(c) }));
            const i = rows.findIndex(c => { const t = LX.iso(c.lastTrade), td = LX.iso(LX.todayBRT()); return t > td || (t === td && mins < LX.FUT_CLOSE); });
            const cur = rows[Math.max(0, i)], next = rows[Math.max(0, i) + 1];
            const end = new Date(cur.lastTrade.getFullYear(), cur.lastTrade.getMonth(), cur.lastTrade.getDate(), 18, 25);
            return Object.assign(cur, { next, end, msLeft: end - now, duLeft: LX.businessDaysBetween(LX.todayBRT(), cur.lastTrade, true) });
        };
        return { WIN: pick(LX.upcomingWIN(3), c => c.expiry), WDO: pick(LX.upcomingWDO(3), c => prevBiz(c.expiry)) };
    };
    // Aviso no topo de todas as páginas quando o último pregão de WIN/WDO é hoje ou no próximo pregão
    function rollBanner() {
        const head = document.getElementById('lx-header'); if (!head) return;
        let el = document.getElementById('lx-roll');
        const lc = LX.liveContracts(), today = LX.iso(LX.todayBRT()), nextB = LX.iso(LX.nextBusinessDay(LX.addDays(LX.todayBRT(), 1)));
        const msgs = ['WDO', 'WIN'].map(k => {
            const c = lc[k], d = LX.iso(c.lastTrade);
            if (d !== today && d !== nextB) return '';
            const when = d === today ? 'HOJE até 18h25' : `${LX.weekday(c.lastTrade)} ${LX.brShort(c.lastTrade)} (próximo pregão)`;
            return `<span class="inline-flex items-center gap-2"><i class="ph-fill ph-warning"></i><strong>Último pregão do ${c.code}: ${when}</strong><span class="opacity-90">→ a liquidez migra para o ${c.next ? c.next.code : 'próximo contrato'}</span></span>`;
        }).filter(Boolean);
        if (!msgs.length) { if (el) el.remove(); return; }
        if (!el) { el = document.createElement('div'); el.id = 'lx-roll'; head.insertAdjacentElement('afterend', el); }
        const hot = msgs.some(m => m.includes('HOJE'));
        el.className = (hot ? 'bg-rose-600' : 'bg-lect-orange') + ' text-white font-mono text-[11px]';
        el.innerHTML = `<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-1.5 flex flex-wrap items-center justify-between gap-x-6 gap-y-1"><div class="flex flex-wrap gap-x-6 gap-y-1">${msgs.join('')}</div><a href="futuros.html#placar" class="underline decoration-dotted whitespace-nowrap">ver placar de vencimento →</a></div>`;
    }

    /* ---------- Próximo evento de alto impacto (data/calendario.json) ---------- */
    let calEvs = null;
    const CAL_FLAG = { BR: '🇧🇷', US: '🇺🇸', CN: '🇨🇳', EU: '🇪🇺', JP: '🇯🇵', UK: '🇬🇧' };
    const CAL_ARROW = { alta: '▲', baixa: '▼', volatil: '↕' };
    function evTime(e) { // horário de Brasília (UTC−3, sem horário de verão) → instante absoluto
        const m = /^(\d{1,2})h(\d{2})?$/.exec(String(e.hora || '').trim()); if (!m || !e.data) return null;
        const [y, mo, d] = e.data.split('-').map(Number);
        return Date.UTC(y, mo - 1, d, +m[1] + 3, +(m[2] || 0));
    }
    LX.calNext = function () { // próximo evento de alto impacto (até 36 h); null se não houver
        if (!calEvs) return null; const now = Date.now();
        return calEvs.map(e => ({ e, t: evTime(e) })).filter(x => x.t && (x.e.importancia || 1) >= 3 && x.t > now - 5 * 60e3 && x.t - now < 36 * 3600e3 && !(x.e.resultado != null && x.e.resultado !== '')).sort((a, b) => a.t - b.t)[0] || null;
    };
    LX.calFlag = CAL_FLAG; LX.calArrow = CAL_ARROW;
    // Faixa com altura fixa criada junto com o cabeçalho: preencher depois não empurra a página (CLS)
    const NB_BASE = 'h-[26px] bg-slate-100 dark:bg-lect-cardDark border-b border-slate-200 dark:border-lect-borderDark font-mono text-[11px]';
    function nextSlot() {
        const head = document.getElementById('lx-header'); if (!head || document.getElementById('lx-next')) return;
        const el = document.createElement('div'); el.id = 'lx-next'; el.className = NB_BASE + ' text-slate-500';
        el.innerHTML = '<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center gap-2"><i class="ph-bold ph-timer text-lect-orange"></i>carregando agenda…</div>';
        head.insertAdjacentElement('afterend', el);
    }
    function nextBar() {
        const head = document.getElementById('lx-header'); if (!head || !calEvs) return;
        const now = Date.now();
        const ev = calEvs.map(e => ({ e, t: evTime(e) })).filter(x => x.t && (x.e.importancia || 1) >= 3 && x.t > now - 5 * 60e3 && x.t - now < 36 * 3600e3 && !(x.e.resultado != null && x.e.resultado !== '')).sort((a, b) => a.t - b.t)[0];
        let el = document.getElementById('lx-next');
        if (!el) return;
        if (!ev) { el.innerHTML = `<a href="index.html#cal-wrap" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center gap-2 whitespace-nowrap overflow-hidden hover:underline decoration-dotted"><i class="ph-bold ph-calendar-check text-lect-teal"></i>Sem dado de alto impacto nas próximas 36 h <span class="opacity-60">· ver calendário</span></a>`; el.className = NB_BASE + ' text-slate-500'; return; }
        const left = ev.t - now, min = Math.max(0, Math.round(left / 60e3)), hot = left <= 15 * 60e3;
        const when = left <= 0 ? 'AGORA' : min < 60 ? `em ${min} min` : min < 24 * 60 ? `em ${Math.floor(min / 60)}h${String(min % 60).padStart(2, '0')}min` : `amanhã ${LX.esc(ev.e.hora)}`;
        const tags = Object.entries(ev.e.impacto || {}).filter(([, v]) => CAL_ARROW[v]).map(([k, v]) => `${LX.esc(k.toUpperCase())} ${CAL_ARROW[v]}`).join(' · ');
        el.className = NB_BASE + (hot ? ' !bg-lect-orange text-lect-navy' : ' text-slate-700 dark:text-slate-300');
        el.innerHTML = `<a href="index.html#cal-wrap" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center gap-x-3 whitespace-nowrap overflow-hidden hover:underline decoration-dotted">
            <span class="inline-flex items-center gap-1.5 font-bold ${hot ? '' : 'text-lect-orange'}"><i class="ph-bold ph-timer"></i>${hot ? 'ATENÇÃO' : 'PRÓXIMO DADO FORTE'}</span>
            <span>${CAL_FLAG[ev.e.pais] || ''} <strong class="${hot ? '' : 'text-slate-900 dark:text-white'}">${LX.esc(ev.e.evento)}</strong> ${when}${left > 0 && min < 24 * 60 ? ` <span class="opacity-70">(${LX.esc(ev.e.hora)})</span>` : ''}</span>
            ${tags ? `<span class="opacity-80">${tags}</span>` : ''}
            ${hot ? '<span class="font-bold">· spread e volatilidade sobem no horário do dado</span>' : ''}</a>`;
    }

    /* ------------------------------------------------------------------ APP (PWA) */
    let installEvt = null;
    function pwa() {
        if ('serviceWorker' in navigator && window.isSecureContext) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => { }));
        const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
        if (standalone) return;
        const btn = document.getElementById('lx-install');
        window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); installEvt = e; if (btn) { btn.classList.remove('hidden'); btn.classList.add('inline-flex'); } });
        if (btn) btn.onclick = async () => { if (!installEvt) return; installEvt.prompt(); try { await installEvt.userChoice; } catch (_) { } installEvt = null; btn.classList.add('hidden'); btn.classList.remove('inline-flex'); };
        window.addEventListener('appinstalled', () => btn && btn.classList.add('hidden'));
        if (/iphone|ipad|ipod/i.test(navigator.userAgent)) { const ios = document.getElementById('lx-install-ios'); if (ios) ios.classList.remove('hidden'); }
    }

    /* ------------------------------------------------------------------ GOOGLE ANALYTICS 4 + CONSENTIMENTO (LGPD) */
    // Modo de consentimento do Google: começa NEGADO (sem cookies). Cookies de análise só depois do "Aceitar".
    // Anúncios ficam sempre negados. A escolha fica em localStorage "lectnex-cookies" (sim/nao) e muda em privacidade.html.
    const CK = 'lectnex-cookies';
    const ckGet = () => { try { return localStorage.getItem(CK); } catch (_) { return null; } };
    LX.cookies = function (sim) {
        try { localStorage.setItem(CK, sim ? 'sim' : 'nao'); } catch (_) { }
        if (window.gtag) gtag('consent', 'update', { analytics_storage: sim ? 'granted' : 'denied' });
        const b = document.getElementById('lx-cookies'); if (b) b.remove();
        document.dispatchEvent(new CustomEvent('lx:cookies', { detail: sim }));
    };
    LX.cookiesEscolha = ckGet;
    // Eventos no Analytics (só se o GA estiver ligado). Nomes curtos e estáveis: aparecem assim nos relatórios.
    LX.track = function (nome, p) { try { if (LX.config.ga && window.gtag) gtag('event', nome, Object.assign({ pagina: document.body.dataset.page || '' }, p || {})); } catch (_) { } };
    function rastrear() {
        const usadas = new Set();
        document.addEventListener('submit', ev => { if (ev.target.matches && ev.target.matches('form[action*="buttondown"]')) LX.track('sign_up', { method: 'newsletter' }); }, true);
        document.addEventListener('click', ev => {
            const a = ev.target.closest && ev.target.closest('a[href]'); if (!a) return;
            const h = a.getAttribute('href') || '';
            if (/t\.me\//.test(h)) LX.track('join_group', { group_id: 'telegram_lectnex' });
            else if (/instagram\.com|tiktok\.com|x\.com\//.test(h)) LX.track('rede_social', { rede: h.includes('instagram') ? 'instagram' : h.includes('tiktok') ? 'tiktok' : 'x' });
            else if (h.startsWith('mailto:')) LX.track('contato_email');
        }, true);
        const usou = ev => {
            const t = ev.target; if (!t || !t.closest || t.closest('#lx-palette, #lx-cookies, form[action*="buttondown"], header, #lx-topbar')) return;
            const sec = t.closest('section[id], [data-ferramenta]'); if (!sec) return;
            const nome = sec.dataset.ferramenta || sec.id; if (usadas.has(nome)) return;
            usadas.add(nome); LX.track('ferramenta_usada', { ferramenta: nome });
        };
        document.addEventListener('input', usou, true);
        document.addEventListener('change', usou, true);
        window.addEventListener('appinstalled', () => LX.track('app_instalado'));
    }
    function analytics() {
        const id = LX.config.ga; if (!id || !/^G-[A-Z0-9]+$/.test(id)) return;
        const esc = ckGet();
        window.dataLayer = window.dataLayer || [];
        window.gtag = function () { dataLayer.push(arguments); };
        gtag('consent', 'default', { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: esc === 'sim' ? 'granted' : 'denied', wait_for_update: 500 });
        gtag('js', new Date());
        gtag('config', id, { page_title: document.title });
        const load = () => { const sc = document.createElement('script'); sc.async = true; sc.src = 'https://www.googletagmanager.com/gtag/js?id=' + id; document.head.appendChild(sc); };
        (window.requestIdleCallback || (f => setTimeout(f, 1200)))(load);
        rastrear();
        if (!esc) banner();
    }
    function banner() {
        if (document.getElementById('lx-cookies')) return;
        const d = document.createElement('div');
        d.id = 'lx-cookies';
        d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', 'Cookies de análise');
        d.className = 'fixed z-[60] bottom-3 left-3 right-3 sm:left-auto sm:right-4 sm:bottom-4 sm:max-w-sm bg-white dark:bg-[#0B1826] border border-slate-300 dark:border-lect-borderDark shadow-2xl p-4 text-sm';
        d.innerHTML = `<p class="text-slate-700 dark:text-slate-200 leading-relaxed"><i class="ph-bold ph-cookie text-lect-orange"></i> Usamos cookies do <strong>Google Analytics</strong> só para saber quais páginas e ferramentas são mais úteis. Nada de anúncios. <a href="privacidade.html" class="text-lect-teal underline">Saiba mais</a></p>
            <div class="flex gap-2 mt-3"><button type="button" data-ck="0" class="flex-1 px-3 py-2 border border-slate-300 dark:border-lect-borderDark font-semibold hover:border-lect-teal">Recusar</button><button type="button" data-ck="1" class="flex-1 px-3 py-2 bg-lect-teal hover:bg-teal-700 text-white font-bold">Aceitar</button></div>`;
        d.addEventListener('click', ev => { const b = ev.target.closest('[data-ck]'); if (b) LX.cookies(b.dataset.ck === '1'); });
        document.body.appendChild(d);
    }

    /* ------------------------------------------------------------------ ALERTAS NO CELULAR (OneSignal) */
    // Qualquer [data-lx-push] vira botão. As escolhas viram tags: surpresa, agenda (15 min antes), leitura.
    const PUSH_OPTS = [['surpresa', 'Surpresas do calendário', 'Quando um dado sai fora do consenso'], ['agenda', 'Dado forte em 15 min', 'Payroll, IPCA, Copom, CPI…'], ['leitura', 'Leitura do Dia', 'Todo dia por volta das 7h45']];
    let osReady = null;
    function oneSignal() {
        if (osReady) return osReady;
        osReady = new Promise((ok, fail) => {
            window.OneSignalDeferred = window.OneSignalDeferred || [];
            OneSignalDeferred.push(async OS => {
                try {
                    const base = location.pathname.replace(/[^/]*$/, ''); // /lectnex/
                    await OS.init({ appId: LX.config.onesignal, safari_web_id: LX.config.onesignalSafari, serviceWorkerPath: base.slice(1) + 'push/OneSignalSDKWorker.js', serviceWorkerParam: { scope: base + 'push/' }, notifyButton: { enable: false } });
                    ok(OS);
                } catch (e) { fail(e); }
            });
            const sc = document.createElement('script'); sc.src = 'https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js'; sc.defer = true; sc.onerror = fail; document.head.appendChild(sc);
        });
        return osReady;
    }
    function pushPanel() {
        let el = document.getElementById('lx-push'); if (el) { el.remove(); return; }
        let saved = {}; try { saved = JSON.parse(localStorage.getItem('lectnex-push-v1') || '{}'); } catch (_) { }
        el = document.createElement('div'); el.id = 'lx-push'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', 'Alertas no celular');
        el.className = 'fixed z-[90] bottom-3 left-3 right-3 sm:left-auto sm:w-[360px] term-panel shadow-2xl p-4 text-slate-800 dark:text-slate-200';
        const ios = /iphone|ipad|ipod/i.test(navigator.userAgent), standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
        el.innerHTML = `<div class="flex items-start justify-between gap-2"><strong class="font-display inline-flex items-center gap-2"><i class="ph-bold ph-bell-ringing text-lect-orange"></i>Alertas no celular</strong><button type="button" data-x class="text-slate-400 hover:text-lect-teal" aria-label="Fechar"><i class="ph-bold ph-x"></i></button></div>
            ${ios && !standalone ? '<p class="mt-2 text-xs text-slate-500">No iPhone, primeiro instale o app: toque em Compartilhar → "Adicionar à Tela de Início", abra o Lectnex pelo ícone e volte aqui.</p>' : ''}
            <div class="mt-3 space-y-2">${PUSH_OPTS.map(([k, t, d]) => `<label class="flex items-start gap-2.5 cursor-pointer"><input type="checkbox" data-k="${k}" class="mt-0.5 accent-[#009988]" ${saved[k] !== false ? 'checked' : ''}><span><strong class="block text-sm">${t}</strong><span class="text-[11px] text-slate-500">${d}</span></span></label>`).join('')}</div>
            <button type="button" data-go class="mt-4 w-full px-4 py-2 bg-lect-orange hover:brightness-110 text-lect-navy font-mono text-xs font-bold">ATIVAR ALERTAS</button>
            <p data-msg class="mt-2 text-[11px] text-slate-500 font-mono">Grátis. Você pode desligar quando quiser. Educacional, não é recomendação.</p>`;
        document.body.appendChild(el);
        el.querySelector('[data-x]').onclick = () => el.remove();
        el.querySelector('[data-go]').onclick = async () => {
            const msg = el.querySelector('[data-msg]'), tags = {};
            el.querySelectorAll('[data-k]').forEach(c => { tags[c.dataset.k] = c.checked ? '1' : '0'; });
            try { localStorage.setItem('lectnex-push-v1', JSON.stringify(Object.fromEntries(Object.entries(tags).map(([k, v]) => [k, v === '1'])))); } catch (_) { }
            msg.textContent = 'Conectando…';
            try {
                const OS = await oneSignal();
                if (!OS.Notifications.permission) await OS.Notifications.requestPermission();
                if (!OS.Notifications.permission) { msg.textContent = 'Permissão negada. Libere as notificações do site nas configurações do navegador.'; return; }
                await OS.User.PushSubscription.optIn();
                await OS.User.addTags(tags);
                LX.track('push_ativado', { tipos: Object.keys(tags).filter(k => tags[k] === '1').join(',') });
                msg.innerHTML = '<span class="text-emerald-500">✓ Alertas ativados.</span> Para mudar, abra este painel de novo.';
                setTimeout(() => el.remove(), 2500);
            } catch (e) { msg.textContent = 'Não foi possível ativar agora. Tente de novo em instantes.'; }
        };
    }
    // Liga/desliga alertas das ações favoritas (até 3, limite de etiquetas do plano grátis do OneSignal): tags a1, a2, a3
    LX.pushAcoes = async function (lista) {
        if (!LX.config.onesignal) throw new Error('alertas desligados');
        const OS = await oneSignal();
        if (lista.length) {
            if (!OS.Notifications.permission) await OS.Notifications.requestPermission();
            if (!OS.Notifications.permission) throw new Error('permissão negada');
            await OS.User.PushSubscription.optIn();
        }
        const tags = {}; ['a1', 'a2', 'a3'].forEach((k, i) => { if (lista[i]) tags[k] = lista[i]; });
        const tirar = ['a1', 'a2', 'a3'].filter((k, i) => !lista[i]);
        if (tirar.length) await OS.User.removeTags(tirar);
        if (Object.keys(tags).length) await OS.User.addTags(tags);
        LX.track('alerta_acoes', { quantidade: lista.length });
        return true;
    };
    LX.pushButtons = () => pushButtons();
    function pushButtons() {
        if (!LX.config.onesignal || !('Notification' in window || navigator.standalone)) return;
        document.querySelectorAll('[data-lx-push]').forEach(b => { b.classList.remove('hidden'); b.classList.add('inline-flex'); b.onclick = pushPanel; });
    }

    /* ------------------------------------------------------------------ STATUS DOS DADOS (rodapé) */
    function footStatus() {
        const el = document.getElementById('lx-status'); if (!el) return;
        const tz = { timeZone: 'America/Sao_Paulo' };
        const brt = d => new Date(d.toLocaleString('en-US', tz)); // relógio de Brasília
        const now = new Date(), nb = brt(now), hojeISO = LX.iso(nb);
        const hm = d => d.toLocaleTimeString('pt-BR', { ...tz, hour: '2-digit', minute: '2-digit' }).replace(':', 'h');
        const quando = d => { const min = Math.round((now - d) / 6e4); if (min < 60) return `há ${Math.max(1, min)} min`; return LX.iso(brt(d)) === hojeISO ? `às ${hm(d)}` : `${d.toLocaleDateString('pt-BR', { ...tz, weekday: 'short' }).replace('.', '')} ${hm(d)}`; };
        const pega = f => fetch(`data/${f}.json?t=${Math.floor(Date.now() / 3e5)}`, { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null);
        Promise.all([pega('cotacoes'), pega('leitura'), pega('calendario')]).then(([cot, lei, cal]) => {
            if (!cot && !lei && !cal) { pinta('bg-slate-500', 'Status indisponível', ''); return; }
            const mins = nb.getHours() * 60 + nb.getMinutes();
            const pregao = LX.isBusinessDay(nb) && mins >= 10 * 60 + 45 && mins <= 18 * 60 + 45;
            const partes = [], atrasos = [];
            if (cot && cot.atualizado_em) {
                const t = new Date(cot.atualizado_em), h = (now - t) / 36e5;
                partes.push(`Cotações ${quando(t)}`);
                if (pregao && h > 1.5) atrasos.push('cotações');
            }
            if (lei && lei.data) {
                const hoje = lei.data === hojeISO;
                partes.push(hoje ? 'Leitura de hoje' : `Leitura de ${lei.data.slice(8, 10)}/${lei.data.slice(5, 7)}`);
                if (!hoje && mins >= 9 * 60) atrasos.push('Leitura');
            }
            if (cal && cal.atualizado_em) {
                const t = new Date(cal.atualizado_em);
                partes.push(`Agenda ${quando(t)}`);
                if ((now - t) / 36e5 > 28) atrasos.push('agenda');
            }
            if (atrasos.length) pinta('bg-amber-400', `Atualização atrasada (${atrasos.join(', ')})`, partes.join(' · '));
            else pinta('bg-emerald-400 lx-pulse', pregao ? 'Dados em dia' : 'Dados em dia · mercado fechado', partes.join(' · '));
        });
        function pinta(cor, titulo, det) {
            el.innerHTML = `<span class="lx-dot mt-1 shrink-0 w-2 h-2 rounded-full ${cor}"></span><span><strong class="text-slate-300 font-semibold">${titulo}</strong>${det ? `<span class="block sm:inline text-slate-400 sm:ml-1.5">${det}</span>` : ''}</span>`;
        }
    }

    /* ------------------------------------------------------------------ BOOT */
    function boot() {
        LX.renderChrome(document.body.dataset.page || '');
        tickClock(); paintSessions(); LX.fill();
        nextSlot(); rollBanner(); setInterval(rollBanner, 60000);
        pwa(); pushButtons(); analytics();
        const hc = document.getElementById('lx-hc'); if (hc) hc.onclick = () => { const on = document.documentElement.classList.toggle('lx-hc'); try { localStorage.setItem('lectnex-hc', on ? '1' : '0'); } catch (_) { } };
        fetch('data/calendario.json?t=' + Math.floor(Date.now() / 6e5), { cache: 'no-store' }).then(r => r.ok ? r.json() : null).then(j => { calEvs = j && Array.isArray(j.eventos) ? j.eventos : []; nextBar(); setInterval(nextBar, 30000); }).catch(() => { calEvs = []; nextBar(); });
        newsForms();
        (window.requestIdleCallback || (f => setTimeout(f, 1500)))(footStatus); setInterval(footStatus, 5 * 6e4);
        if (LX.config.newsletter) fetch('data/newsletter.json?t=' + Date.now(), { cache: 'no-store' }).then(r => r.ok ? r.json() : null).then(j => { if (j && j.inscritos >= 25) { newsCount = j.inscritos; newsForms(); } }).catch(() => { });
        if (LX.config.telegram) fetch('data/telegram.json?t=' + Math.floor(Date.now() / 36e5), { cache: 'no-store' }).then(r => r.ok ? r.json() : null).then(j => { if (j && j.seguidores >= 25) { tgCount = j.seguidores; newsForms(); } }).catch(() => { });
        // Com cache, as páginas já desenham câmbio e indicadores antes da resposta das APIs
        if (LX.data.cachedAt) document.dispatchEvent(new CustomEvent('lx:macro', { detail: LX.data }));
        if (LX.data.fxCached) document.dispatchEvent(new CustomEvent('lx:fx', { detail: LX.data.fx }));
        setInterval(tickClock, 1000);
        setInterval(paintSessions, 30000);
        LX.loadMacro(); LX.loadPTAX(); LX.loadFX();
        setInterval(LX.loadFX, 30000);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') document.querySelectorAll('[data-lx-modal]').forEach(m => { m.classList.add('hidden'); m.classList.remove('flex'); });
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
