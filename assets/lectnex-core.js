/* =====================================================================================
   LECTNEX CORE — núcleo compartilhado por todas as páginas
   - Dados reais: Banco Central (SGS / PTAX / Focus) e AwesomeAPI (câmbio, cripto)
   - Calendário B3: feriados, dias úteis, vencimentos de WIN, WDO, DI1 e opções
   - Status dos pregões, relógio, tema claro/escuro e widgets TradingView
   Nenhuma dependência externa. Carregue com <script src="assets/lectnex-core.js"></script>
   ===================================================================================== */
(function () {
    'use strict';

    const LX = (window.LX = window.LX || {});

    /* ------------------------------------------------------------------ CONFIG */
    LX.config = Object.assign({
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
    }, LX.config || {});

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
    try { if (localStorage.getItem('lectnex-theme') === 'dark') document.documentElement.classList.add('dark'); } catch (_) { }
    window.toggleTheme = function () {
        const dark = document.documentElement.classList.toggle('dark');
        try { localStorage.setItem('lectnex-theme', dark ? 'dark' : 'light'); } catch (_) { }
        LX._tvWidgets.forEach(w => LX.tv(w.id, w.type, w.cfg));
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
        const j = await getJSON(`https://api.bcb.gov.br/dados/serie/bcdata.sgs.${code}/dados/ultimos/${n}?formato=json`);
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
        await Promise.allSettled(jobs);
        LX.data.realRate = ((1 + LX.data.selic.value / 100) / (1 + LX.data.ipca12m.value / 100) - 1) * 100;
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
                    LX.fill();
                    return;
                }
            } catch (_) { return; }
            d = addDays(d, -1);
        }
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
            LX.data.fxOk = true;
        } catch (_) { LX.data.fxOk = false; }
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
            ptax: d.ptax ? `${LX.num(d.ptax.sell, 4)} (${d.ptax.date})` : '—'
        };
        Object.entries(map).forEach(([k, v]) => document.querySelectorAll(`[data-lx="${k}"]`).forEach(el => { el.textContent = v; }));
        if (usd) document.querySelectorAll('[data-lx="usd-pct"]').forEach(el => el.className = LX.signClass(usd.pct));
        document.querySelectorAll('[data-lx-feed]').forEach(el => {
            const live = d.selic.src !== 'ref' || d.fxOk;
            el.innerHTML = live
                ? '<span class="w-2 h-2 bg-emerald-400 inline-block animate-pulse"></span>DADOS OFICIAIS CONECTADOS'
                : `<span class="w-2 h-2 bg-amber-400 inline-block"></span>VALORES DE REFERÊNCIA (${d.selic.date})`;
        });
    };

    /* ------------------------------------------------------------------ TRADINGVIEW */
    LX._tvWidgets = [];
    LX.tv = function (id, type, cfg) {
        const host = document.getElementById(id);
        if (!host) return;
        if (!LX._tvWidgets.find(w => w.id === id)) LX._tvWidgets.push({ id, type, cfg });
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
    LX.parseISO = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };

    /* ------------------------------------------------------------------ CABEÇALHO / RODAPÉ COMUNS */
    const LOGO = `<svg class="w-11 h-11 shrink-0" viewBox="0 0 120 120" fill="none" aria-hidden="true">
        <polygon points="60,8 106,34.5 106,85.5 60,112 14,85.5 14,34.5" stroke="#00756C" stroke-width="7.5" stroke-linejoin="round" class="fill-white dark:fill-[#0B1626]"/>
        <path d="M34 48.5 L60 34.5 L86 48.5" stroke="#F39200" stroke-width="4.5" stroke-linecap="round"/>
        <circle cx="60" cy="34.5" r="8.5" fill="#F39200"/>
        <path d="M34 49.5 L60 62 L60 91.5 L34 79 Z" fill="#00756C"/><path d="M60 62 L86 49.5 L86 79 L60 91.5 Z" fill="#00B4A2"/></svg>`;
    const NAV = [
        { key: 'mercado', href: 'index.html', label: 'Mercado Hoje', icon: 'ph-pulse' },
        { key: 'agenda', href: 'index.html#agenda', label: 'Agenda', icon: 'ph-calendar-dots' },
        { key: 'futuros', href: 'futuros.html', label: 'Futuros WIN · WDO · DI', icon: 'ph-chart-line-up', badge: 'NOVO' },
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
              <button onclick="LX.openPalette()" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 inline-flex items-center gap-1.5"><i class="ph ph-terminal-window text-lect-orange"></i>BUSCA RÁPIDA <kbd>/</kbd></button>
              <span data-lx-clock class="text-slate-300 font-semibold"></span>
            </div>
          </div>
        </div>`;
        const head = document.getElementById('lx-header');
        if (head) {
            head.className = 'sticky top-0 z-40 bg-white/95 dark:bg-lect-bgDark/95 border-b border-slate-300 dark:border-lect-borderDark backdrop-blur-md';
            const link = (n, mobile) => {
                const on = n.key === active;
                const badge = n.badge ? `<span class="ml-1 px-1 text-[8px] font-bold bg-lect-orange text-white">${n.badge}</span>` : '';
                if (mobile) return `<a href="${n.href}" class="px-2.5 py-1 ${on ? 'bg-lect-navy text-white font-bold' : 'border border-slate-300 dark:border-lect-borderDark'}">${n.label}${badge}</a>`;
                return `<a href="${n.href}" class="flex items-center gap-1.5 px-2.5 py-2 transition-colors ${on ? 'text-lect-navy dark:text-white font-bold border-b-2 border-lect-teal' : 'hover:text-lect-teal'}"><i class="ph-bold ${n.icon} ${on ? 'text-lect-teal' : 'text-slate-400'}"></i>${n.label}${badge}</a>`;
            };
            head.innerHTML = `
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-[72px] flex items-center justify-between gap-4">
              <a href="index.html" class="flex items-center gap-3 shrink-0 group">${LOGO}
                <div><div class="flex items-center gap-2"><div class="text-2xl font-display font-bold tracking-tight leading-none"><span class="text-[#0C1A2A] dark:text-white">Lect</span><span class="text-[#009988] dark:text-[#00B4A2]">nex</span></div>
                <span class="px-1.5 py-0.5 bg-lect-navy text-white dark:bg-lect-teal/20 dark:text-lect-tealLight font-mono text-[9px] font-bold uppercase tracking-widest">TERMINAL</span></div>
                <span class="text-[11px] text-[#64748B] block mt-1">Inteligência de Mercado &amp; Educação Financeira</span></div></a>
              <nav class="hidden lg:flex items-center gap-1 text-[13px] font-medium text-slate-600 dark:text-slate-300">${NAV.map(n => link(n)).join('')}</nav>
              <div class="flex items-center gap-2">
                <button onclick="LX.openPalette()" class="hidden sm:flex xl:w-52 items-center justify-between gap-3 px-3 py-2 border border-slate-300 dark:border-lect-borderDark bg-slate-50 dark:bg-lect-cardDark text-xs font-mono text-slate-500 hover:border-lect-teal"><span class="inline-flex items-center gap-1.5"><i class="ph ph-magnifying-glass text-lect-teal"></i><span class="hidden xl:inline">Ativo, ferramenta...</span></span><kbd class="px-1.5 text-[10px] border border-slate-300 dark:border-lect-borderDark">/</kbd></button>
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
              </div>
              <div class="lg:col-span-3 space-y-1.5 font-mono text-xs">
                <span class="text-white font-bold uppercase tracking-wider block mb-2">Módulos</span>
                ${NAV.map(n => `<a href="${n.href}" class="block hover:text-lect-tealLight">${n.label}</a>`).join('')}
              </div>
              <div class="lg:col-span-5 space-y-1.5 font-mono text-[11px]">
                <span class="text-white font-bold uppercase tracking-wider block mb-2">Fontes de dados</span>
                <span class="block">• Selic, CDI, IPCA, PTAX e Focus: Banco Central do Brasil (SGS / Olinda) — oficiais</span>
                <span class="block">• Câmbio e cripto: AwesomeAPI — cotações com atraso de alguns segundos</span>
                <span class="block">• Gráficos, notícias e agenda global: widgets TradingView</span>
                <span class="block">• Ações: brapi.dev (atraso de até 15 min) · Calendário de vencimentos: regras B3</span>
                <span class="block text-amber-400/90">• Itens marcados <span class="lx-demo">SIMULAÇÃO</span> são dados fictícios para fins didáticos</span>
              </div>
            </div>
            <div class="pt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[11px] text-slate-500">
              <p class="max-w-4xl"><strong class="text-slate-300">Aviso legal:</strong> conteúdo exclusivamente educacional e informativo. Nada aqui constitui recomendação de compra, venda ou manutenção de valores mobiliários, nem relatório de análise nos termos da Resolução CVM nº 20. Operar derivativos envolve alavancagem e risco de perdas superiores ao capital. Rentabilidade passada ou simulada não garante resultado futuro. Confirme sempre dados e horários nas fontes oficiais.</p>
              <span class="font-mono shrink-0">&copy; ${new Date().getFullYear()} Lectnex</span>
            </div>
          </div>
        </footer>`;
        buildPalette();
    };

    /* ------------------------------------------------------------------ BUSCA RÁPIDA ("/" ou Ctrl/Cmd+K) */
    LX.paletteItems = [
        ['FUTUROS', 'Vencimentos WIN, WDO, DI e opções', 'futuros.html#vencimentos'],
        ['FUTUROS', 'Calculadora de risco por operação (WIN/WDO)', 'futuros.html#risco'],
        ['FUTUROS', 'Preço justo do dólar futuro (paridade)', 'futuros.html#paridade'],
        ['MERCADO', 'Agenda: Copom, FOMC, IPCA, vencimentos', 'index.html#agenda'],
        ['MERCADO', 'Boletim Focus ao vivo', 'index.html#juros'],
        ['MERCADO', 'Câmbio e cripto ao vivo', 'index.html#cambio'],
        ['LAB', 'Simulador Compra/Venda vs. CDI (IR)', 'laboratorio.html?tab=trade'],
        ['LAB', 'Simulador Dividendos & JCP (regras 2026)', 'laboratorio.html?tab=proventos'],
        ['LAB', 'Preço teto Bazin & Graham', 'laboratorio.html?tab=valuation'],
        ['LAB', 'Comparador CDB × LCI/LCA × IPCA+', 'laboratorio.html?tab=rf'],
        ...['PETR4', 'VALE3', 'ITUB4', 'BBAS3', 'BBDC4', 'B3SA3', 'WEGE3', 'PRIO3', 'ABEV3', 'ELET3', 'SUZB3', 'RENT3', 'MGLU3', 'BPAC11', 'TAEE11']
            .map(t => ['AÇÃO', t + ' · gráfico, múltiplos e opções', 'acoes.html?ticker=' + t])
    ];
    function buildPalette() {
        if (document.getElementById('lx-palette')) return;
        const el = document.createElement('div');
        el.id = 'lx-palette';
        el.setAttribute('data-lx-modal', '');
        el.className = 'fixed inset-0 z-50 bg-lect-navy/80 hidden items-start justify-center pt-20 p-4';
        el.innerHTML = `
          <div class="bg-white dark:bg-lect-cardDark border-2 border-lect-navy dark:border-lect-teal max-w-2xl w-full shadow-2xl">
            <div class="p-3 bg-lect-navy text-white flex items-center justify-between font-mono text-xs">
              <span class="inline-flex items-center gap-2"><i class="ph-bold ph-terminal-window text-lect-orange"></i>BUSCA RÁPIDA LECTNEX</span>
              <button onclick="LX.closePalette()" class="px-2 py-0.5 bg-slate-800 border border-slate-700 text-[10px]">ESC</button>
            </div>
            <div class="p-3 border-b border-slate-200 dark:border-lect-borderDark">
              <input id="lx-palette-input" class="lx-input" placeholder="Ticker (ex.: PETR4) ou ferramenta (ex.: DI, vencimento, JCP)... Enter abre o ticker">
            </div>
            <div id="lx-palette-list" class="divide-y divide-slate-100 dark:divide-lect-borderDark font-mono text-xs max-h-80 overflow-y-auto thin-scroll"></div>
          </div>`;
        document.body.appendChild(el);
        el.addEventListener('click', e => { if (e.target === el) LX.closePalette(); });
        const inp = el.querySelector('#lx-palette-input');
        const render = () => {
            const q = inp.value.toLowerCase().trim();
            el.querySelector('#lx-palette-list').innerHTML = LX.paletteItems
                .filter(([a, b]) => !q || (a + ' ' + b).toLowerCase().includes(q)).slice(0, 30)
                .map(([tag, label, href]) => `<a href="${href}" class="flex items-center justify-between p-3 hover:bg-slate-50 dark:hover:bg-lect-bgDark"><span>${LX.esc(label)}</span><span class="text-[10px] text-lect-teal font-bold">${tag} →</span></a>`).join('');
        };
        inp.addEventListener('input', render);
        inp.addEventListener('keydown', e => {
            if (e.key !== 'Enter') return;
            const v = inp.value.trim().toUpperCase();
            if (/^[A-Z]{4}\d{1,2}$/.test(v)) location.href = 'acoes.html?ticker=' + v;
            else { const first = el.querySelector('#lx-palette-list a'); if (first) location.href = first.href; }
        });
        render();
    }
    LX.openPalette = function () {
        const el = document.getElementById('lx-palette'); if (!el) return;
        el.classList.remove('hidden'); el.classList.add('flex');
        const inp = document.getElementById('lx-palette-input'); inp.value = ''; inp.dispatchEvent(new Event('input'));
        setTimeout(() => inp.focus(), 30);
    };
    LX.closePalette = function () { const el = document.getElementById('lx-palette'); if (el) { el.classList.add('hidden'); el.classList.remove('flex'); } };
    document.addEventListener('keydown', e => {
        const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);
        if (!typing && (e.key === '/' || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k'))) { e.preventDefault(); LX.openPalette(); }
    });

    /* ------------------------------------------------------------------ BOOT */
    function boot() {
        LX.renderChrome(document.body.dataset.page || '');
        tickClock(); paintSessions(); LX.fill();
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
