/* Lectnex · Simulador de fluxo do mini índice (fluxo.html)
   Mercado SINTÉTICO para treino de leitura de fluxo: livro de ofertas com fila, agressões, players grandes
   (absorção, varredura, notícia) e um "professor" com regras simples que explica o que aparece no tape.
   Nada aqui é dado real da B3 nem previsão: é gerado por computador a partir de uma semente (mesma semente = mesmo pregão). */
(function () {
    'use strict';
    const $ = id => document.getElementById(id);
    const TICK = 5, PV = 0.2, CUSTO = 0.5, FIM = 9 * 3600, LINHAS = 12;
    const fmt = v => (window.LX ? LX.num(v, 0) : String(v));
    const brl = v => (v > 0 ? '+' : v < 0 ? '−' : '') + (window.LX ? LX.brl(Math.abs(v)) : 'R$ ' + Math.abs(v).toFixed(2));
    const pts = v => (v > 0 ? '+' : v < 0 ? '−' : '') + fmt(Math.abs(v)) + ' pts';
    const cor = v => v > 0 ? 'text-emerald-600 dark:text-emerald-400' : v < 0 ? 'text-rose-600 dark:text-rose-400' : '';
    const hora = t => { const s = 9 * 3600 + Math.floor(t); return [s / 3600, s / 60 % 60, s % 60].map(x => String(Math.floor(x)).padStart(2, '0')).join(':'); };
    const ls = { get: k => { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { } } };
    const track = (n, p) => { try { LX.track(n, p); } catch (e) { } };

    /* ---------- aleatório com semente ---------- */
    let rnd = Math.random;
    function semear(txt) {
        let h = 1779033703 ^ txt.length;
        for (const c of txt) { h = Math.imul(h ^ c.charCodeAt(0), 3432918353); h = h << 13 | h >>> 19; }
        let a = h >>> 0;
        rnd = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    }
    const gauss = () => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
    const poisson = l => { const L = Math.exp(-l); let k = 0, p = 1; do { k++; p *= rnd(); } while (p > L); return k - 1; };
    const lote = () => Math.max(1, Math.min(60, Math.round(Math.exp(1.0 + 0.95 * gauss()))));
    const novaSemente = () => Array.from({ length: 6 }, () => 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'[Math.floor(Math.random() * 32)]).join('');

    /* ---------- estado ---------- */
    let S = null, rodando = false, vel = 5, timer = null, acum = 0, ultRender = 0, inicio = 170000;
    function novoPregao() {
        const seed = ($('dm-seed').value || '').toUpperCase().replace(/[^A-Z0-9]/g, '') || novaSemente();
        $('dm-seed').value = seed; semear(seed);
        const vf = +$('dm-vol').value || 1;
        S = {
            seed, vf, t: 0, ask: new Map(), bid: new Map(), bestAsk: inicio, bestBid: inicio - TICK,
            ult: inicio, abert: inicio, max: inicio, min: inicio, ant: inicio, vol: 0, neg: 0, vwN: 0, vwD: 0,
            velas: [], tape: [], agS: [], volP: new Map(),
            regime: { tipo: 'lat', bias: 0, ancora: inicio, ate: 0 }, ev: [], dicas: [], ultDica: -999, longe: false,
            pos: 0, medio: 0, realizado: 0, custos: 0, ordens: [], ops: [], entradas: [], aberta: null, pico: 0, maxDD: 0, nid: 1, fim: false, ultLado: 1
        };
        for (let k = 0; k < 40; k++) { S.ask.set(inicio + k * TICK, prof(k)); S.bid.set(inicio - TICK - k * TICK, prof(k)); }
        S.velas.push({ t0: 0, o: inicio, h: inicio, l: inicio, c: inicio, v: 0 });
        $('dm-prof-feed').innerHTML = '<li class="text-slate-500">Inicie o pregão. Quando o fluxo mostrar algo que vale estudar, aparece aqui com a explicação.</li>';
        $('dm-fim').classList.add('hidden');
        botoes(); render(true);
    }
    const prof = k => Math.round((28 + 13 * k) * (0.55 + 0.9 * rnd()) * (k > 25 ? 0.6 : 1));
    const best = () => {
        let a = Infinity, b = -Infinity;
        S.ask.forEach((q, p) => { if (q > 0 && p < a) a = p; }); S.bid.forEach((q, p) => { if (q > 0 && p > b) b = p; });
        if (a === Infinity) { a = S.ult + TICK; S.ask.set(a, prof(2)); }
        if (b === -Infinity) { b = S.ult - TICK; S.bid.set(b, prof(2)); }
        S.bestAsk = a; S.bestBid = b;
    };

    /* ---------- motor do mercado (1 passo = 1 segundo simulado) ---------- */
    function regime() {
        const r = S.regime, cen = $('dm-regime').value;
        if (S.t >= r.ate || (cen !== 'auto' && ((cen === 'lat') !== (r.tipo === 'lat')))) {
            const tend = cen === 'tend' || (cen !== 'lat' && rnd() < (cen === 'noticia' ? 0.55 : 0.45));
            r.tipo = tend ? 'tend' : 'lat'; r.bias = tend ? (rnd() < 0.5 ? -1 : 1) * (0.12 + 0.18 * rnd()) : 0;
            r.ancora = S.ult; r.ate = S.t + 900 + Math.floor(rnd() * 1800);
        }
    }
    function eventos() {
        if (!$('dm-big').checked) return;
        const cen = $('dm-regime').value, ativos = t => S.ev.some(e => e.tipo === t && e.ate > S.t);
        if (!ativos('absorcao') && rnd() < 1 / 420) {
            const lado = rnd() < 0.5 ? 1 : -1;                         // 1 = vendedor grande na oferta (absorve compras)
            const p = lado > 0 ? S.bestAsk + TICK * Math.floor(rnd() * 3) : S.bestBid - TICK * Math.floor(rnd() * 3);
            S.ev.push({ tipo: 'absorcao', lado, p, total: 400 + Math.floor(rnd() * 900), ate: S.t + 60 + Math.floor(rnd() * 120) });
        }
        if (rnd() < 1 / 650) S.ev.push({ tipo: 'varrer', lado: rnd() < 0.5 + S.regime.bias ? 1 : -1, ate: S.t + 1 });
        if (!ativos('noticia') && rnd() < (cen === 'noticia' ? 1 / 700 : 1 / 3200)) {
            const lado = rnd() < 0.5 ? 1 : -1; S.ev.push({ tipo: 'noticia', lado, ate: S.t + 25 + Math.floor(rnd() * 40) });
            dica('noticia', lado, S.ult, `Notícia (simulada): o fluxo ficou agressivo ${lado > 0 ? 'na compra' : 'na venda'} e o book afinou.`, 'Em notícia o preço anda rápido, o spread abre e o stop pode sair bem pior que o planejado. Muita gente espera a poeira baixar antes de entrar.', true);
        }
    }
    function agredir(lado, q, quem) {
        const livro = lado > 0 ? S.ask : S.bid, p0 = lado > 0 ? S.bestAsk : S.bestBid;
        let resto = q, niveis = 0, soma = 0, n = 0, guard = 0;
        while (resto > 0 && guard++ < 200) {
            const p = lado > 0 ? S.bestAsk : S.bestBid, disp = livro.get(p) || 0;
            if (disp <= 0) { livro.delete(p); lado > 0 ? (S.bestAsk += TICK) : (S.bestBid -= TICK); if (!livro.has(lado > 0 ? S.bestAsk : S.bestBid)) livro.set(lado > 0 ? S.bestAsk : S.bestBid, prof(3)); continue; }
            const f = Math.min(resto, disp);
            livro.set(p, disp - f); resto -= f; soma += f * p; n += f;
            negocio(p, f, lado, quem);
            if (disp - f <= 0) { niveis++; livro.delete(p); lado > 0 ? (S.bestAsk += TICK) : (S.bestBid -= TICK); if (!livro.has(lado > 0 ? S.bestAsk : S.bestBid)) livro.set(lado > 0 ? S.bestAsk : S.bestBid, prof(4)); }
        }
        S.ultLado = lado;
        if (niveis >= 4 && quem !== 'eu') dica('varredura', lado, S.ult, `Varredura: ${lado > 0 ? 'um comprador' : 'um vendedor'} levou ${niveis} níveis de uma vez (${fmt(p0)} → ${fmt(S.ult)}).`, 'Agressão com pressa. O preço às vezes continua um pouco na direção da varredura, mas também pode ser stop sendo executado no fim de um movimento. Vale ver a reação dos próximos segundos antes de seguir.');
        return n ? soma / n : p0;
    }
    function negocio(p, q, lado, quem) {
        S.ult = p; S.max = Math.max(S.max, p); S.min = Math.min(S.min, p); S.vol += q; S.neg++; S.vwN += p * q; S.vwD += q;
        S.volP.set(p, (S.volP.get(p) || 0) + q);
        const s = S.agS[S.agS.length - 1]; if (s) s[lado > 0 ? 0 : 1] += q;
        const ult = S.tape[0];
        if (ult && ult.t === Math.floor(S.t) && ult.p === p && ult.s === lado && ult.quem === quem) ult.q += q;
        else { S.tape.unshift({ t: Math.floor(S.t), p, q, s: lado, quem }); if (S.tape.length > 80) S.tape.pop(); }
        if (q >= 100 && quem !== 'eu') dica('lote', lado, p, `Lote grande: ${fmt(q)} contratos ${lado > 0 ? 'comprando' : 'vendendo'} a mercado em ${fmt(p)}.`, 'Lote grande chama atenção, mas sozinho não diz muito: pode ser alguém montando posição ou zerando. O que importa é o que o preço faz depois.');
        const v = S.velas[S.velas.length - 1]; v.h = Math.max(v.h, p); v.l = Math.min(v.l, p); v.c = p; v.v += q;
        filaMinha(p, q, lado);
    }
    function repor() {
        const vf = S.vf;
        // spread de 1 tick: alguém encosta logo
        if (S.bestAsk - S.bestBid > TICK && rnd() < 0.75) {
            if (S.ultLado > 0) { S.bid.set(S.bestAsk - TICK, (S.bid.get(S.bestAsk - TICK) || 0) + 3 + Math.floor(rnd() * 25)); }
            else { S.ask.set(S.bestBid + TICK, (S.ask.get(S.bestBid + TICK) || 0) + 3 + Math.floor(rnd() * 25)); }
            best();
        }
        for (let k = 0; k < 30; k++) {
            for (const [livro, p] of [[S.ask, S.bestAsk + k * TICK], [S.bid, S.bestBid - k * TICK]]) {
                const alvo = (28 + 13 * k) / vf, q = livro.get(p) || 0;
                if (q < alvo * 0.6 && rnd() < 0.22) livro.set(p, q + lote() * 2);
                else if (q > 0 && rnd() < 0.04) livro.set(p, Math.max(1, Math.round(q * (0.75 + 0.2 * rnd()))));
            }
        }
        // absorção: o lote escondido se renova enquanto durar
        for (const e of S.ev) {
            if (e.tipo !== 'absorcao' || e.ate <= S.t || e.total <= 0) continue;
            const livro = e.lado > 0 ? S.ask : S.bid, q = livro.get(e.p) || 0;
            const vivo = e.lado > 0 ? S.bestAsk === e.p || S.bestAsk < e.p : S.bestBid === e.p || S.bestBid > e.p;
            if (!vivo) { e.ate = 0; continue; }
            if (q < 60) { const r = Math.min(e.total, 80 + Math.floor(rnd() * 80)); livro.set(e.p, q + r); e.total -= r; }
        }
        // limpa o que ficou longe
        for (const livro of [S.ask, S.bid]) livro.forEach((q, p) => { if (Math.abs(p - S.ult) > 60 * TICK) livro.delete(p); });
        for (let k = 0; k < 40; k++) { if (!S.ask.has(S.bestAsk + k * TICK)) S.ask.set(S.bestAsk + k * TICK, prof(k)); if (!S.bid.has(S.bestBid - k * TICK)) S.bid.set(S.bestBid - k * TICK, prof(k)); }
    }
    function passo() {
        S.t += 1;
        if (S.t % 60 === 0) S.velas.push({ t0: S.t, o: S.ult, h: S.ult, l: S.ult, c: S.ult, v: 0 });
        S.agS.push([0, 0]); if (S.agS.length > 900) S.agS.shift();
        regime(); eventos();
        const not = S.ev.find(e => e.tipo === 'noticia' && e.ate > S.t);
        const r = S.regime;
        let b = r.bias + (r.tipo === 'lat' ? -(S.ult - r.ancora) / (TICK * 60) * 0.18 : 0) + (not ? not.lado * 0.55 : 0);
        S.ruido = 0.97 * (S.ruido || 0) + 0.06 * gauss();  // ondas curtas de pressão (o mercado não é moeda jogada)
        b = Math.max(-0.75, Math.min(0.75, b + S.ruido));
        const n = poisson(2.0 * S.vf * (not ? 3.2 : 1));
        for (let i = 0; i < n; i++) {
            const lado = rnd() < 0.5 + b / 2 ? 1 : -1;
            let q = lote(); if (rnd() < 0.012 * S.vf) q = 60 + Math.floor(rnd() * 160);
            // compradores insistem contra o lote escondido (é isso que a absorção mostra no tape)
            const abs = S.ev.find(e => e.tipo === 'absorcao' && e.ate > S.t && e.total > 0);
            if (abs && rnd() < 0.35) { agredir(abs.lado, lote() + 5, 'mercado'); continue; }
            agredir(lado, q, 'mercado');
        }
        const vr = S.ev.find(e => e.tipo === 'varrer' && e.ate >= S.t && !e.feito);
        if (vr) { vr.feito = true; let soma = 0; const livro = vr.lado > 0 ? S.ask : S.bid; for (let k = 0; k < 3 + Math.floor(rnd() * 4); k++) soma += livro.get((vr.lado > 0 ? S.bestAsk : S.bestBid) + vr.lado * k * TICK) || 0; agredir(vr.lado, soma, 'mercado'); }
        best(); repor(); best();
        minhasOrdens(); professor();
        const tot = total(); S.pico = Math.max(S.pico, tot); S.maxDD = Math.max(S.maxDD, S.pico - tot);
        if (S.t >= FIM) encerrar();
    }

    /* ---------- professor (regras simples sobre o tape) ---------- */
    function dica(tipo, lado, preco, txt, sig, forcar) {
        if (!$('dm-prof').checked && !forcar) { S.dicas.push({ t: S.t, tipo, lado, preco, oculta: true }); return; }
        const espera = { varredura: 900, lote: 600, absorcao: 240, exaustao: 600, vwap: 600 }[tipo] || 60;
        S.ultTipo = S.ultTipo || {};
        if (!forcar && (S.t - S.ultDica < 40 || S.t - (S.ultTipo[tipo] ?? -1e9) < espera)) return;
        S.ultDica = S.t; S.ultTipo[tipo] = S.t; S.dicas.push({ t: S.t, tipo, lado, preco });
        const ic = { varredura: 'ph-broom', absorcao: 'ph-shield', exaustao: 'ph-battery-low', noticia: 'ph-megaphone', lote: 'ph-cube', vwap: 'ph-crosshair' }[tipo] || 'ph-lightbulb';
        const li = document.createElement('li'); li.className = 'dm-dica';
        li.innerHTML = `<span class="font-mono text-[10px] text-lect-orange">${hora(S.t)}</span><span class="flex gap-2 mt-0.5"><i class="ph-duotone ${ic} text-lg text-lect-orange shrink-0"></i><span><strong class="block">${LX.esc(txt)}</strong><span class="text-slate-600 dark:text-slate-400">${LX.esc(sig)}</span></span></span>`;
        const feed = $('dm-prof-feed'); if (feed.firstElementChild && !feed.firstElementChild.classList.contains('dm-dica')) feed.innerHTML = '';
        feed.prepend(li); while (feed.children.length > 30) feed.lastChild.remove();
    }
    function professor() {
        if (S.t < 120) return;
        const ag = S.agS, soma = (a, b, i) => ag.slice(a, b).reduce((s, x) => s + x[i], 0), N = ag.length;
        // absorção: muita agressão de um lado em 30 s e o preço parado
        const c30 = S.tape.filter(x => x.t > S.t - 30);
        if (c30.length > 10) {
            const comp = c30.filter(x => x.s > 0).reduce((s, x) => s + x.q, 0), vend = c30.filter(x => x.s < 0).reduce((s, x) => s + x.q, 0);
            const ps = c30.map(x => x.p), amp = Math.max(...ps) - Math.min(...ps);
            if (comp > 220 && comp > 1.8 * vend && amp <= TICK) dica('absorcao', -1, S.bestAsk, `Absorção na venda em ${fmt(S.bestAsk)}: compradores agrediram ${fmt(comp)} contratos em 30 s e o preço não passou.`, 'Tem alguém grande vendendo ali, provavelmente com lote escondido que se renova. Se o preço não romper, é comum voltar; se romper com força, o vendedor saiu de cena.');
            else if (vend > 220 && vend > 1.8 * comp && amp <= TICK) dica('absorcao', 1, S.bestBid, `Absorção na compra em ${fmt(S.bestBid)}: vendedores agrediram ${fmt(vend)} contratos em 30 s e o preço não caiu.`, 'Tem alguém grande comprando ali. Se o nível segurar, o preço costuma reagir para cima; se cair com força, o comprador desistiu.');
        }
        // exaustão: andou muito em 5 min e a agressão do lado do movimento caiu pela metade
        if (N >= 300 && S.velas.length >= 6) {
            const ini = S.velas[S.velas.length - 6].o, mov = S.ult - ini;
            if (Math.abs(mov) >= 30 * TICK) {
                const i = mov > 0 ? 0 : 1, agora = soma(N - 60, N, i), antes = soma(N - 300, N - 60, i) / 4;
                if (antes > 0 && agora < antes * 0.5) dica('exaustao', mov > 0 ? -1 : 1, S.ult, `Exaustão: depois de ${mov > 0 ? 'subir' : 'cair'} ${fmt(Math.abs(mov))} pts em 5 min, a agressão ${mov > 0 ? 'compradora' : 'vendedora'} caiu pela metade.`, 'Movimento perdendo força. Não quer dizer que vai virar, mas entrar a favor agora costuma ter pior relação risco/retorno. Muitos esperam um respiro ou um rompimento com volume.');
            }
        }
        // volta à VWAP depois de ficar longe
        const vw = S.vwD ? S.vwN / S.vwD : S.ult, dist = Math.abs(S.ult - vw);
        if (dist >= 40 * TICK) S.longe = true;
        else if (S.longe && dist <= TICK) { S.longe = false; dica('vwap', 0, S.ult, `O preço voltou à VWAP (${fmt(Math.round(vw / TICK) * TICK)}), o preço médio do dia ponderado pelo volume.`, 'Muitos participantes usam a VWAP como referência de preço justo do dia. Ela costuma atrair o preço em dias laterais e servir de suporte ou resistência em dias de tendência.'); }
    }

    /* ---------- as suas ordens ---------- */
    const total = () => S.realizado + (S.pos ? (S.ult - S.medio) * S.pos * PV : 0) - S.custos;
    function ordemLimitada(lado, p) {
        if (!rodando || S.fim) return;
        const q = qtd();
        if ((lado > 0 && p >= S.bestAsk) || (lado < 0 && p <= S.bestBid)) return mercado(lado);   // limitada que cruza o book executa já
        const fila = (lado > 0 ? S.bid : S.ask).get(p) || 0;
        S.ordens.push({ id: S.nid++, tipo: 'lim', lado, p, q, ahead: fila });
        render(true);
    }
    function mercado(lado, motivo) {
        if (S.fim) return;
        const q = motivo ? Math.abs(S.pos) : qtd();
        const px = agredir(lado, q, 'eu');
        execucao(lado, q, Math.round(px), motivo || 'manual'); best(); render(true);
    }
    function filaMinha(p, q, ladoAgr) {
        for (const o of S.ordens) {
            if (o.tipo === 'stop') continue;
            if (o.lado === -ladoAgr && o.p === p) o.ahead -= q;
        }
    }
    function minhasOrdens() {
        const feitas = [];
        for (const o of S.ordens) {
            if (o.tipo === 'stop') { if ((o.lado < 0 && S.ult <= o.p) || (o.lado > 0 && S.ult >= o.p)) feitas.push(o); continue; }
            const atravessou = o.lado > 0 ? S.ult < o.p : S.ult > o.p;
            if (atravessou || o.ahead < 0) feitas.push(o);
        }
        for (const o of feitas) {
            if (!S.ordens.includes(o)) continue;
            S.ordens = S.ordens.filter(x => x !== o);
            if (o.tipo === 'stop') { if (S.pos) mercado(o.lado, 'stop'); }
            else if (o.tipo === 'alvo') { if (S.pos) execucao(o.lado, Math.abs(S.pos), o.p, 'alvo'); }
            else execucao(o.lado, o.q, o.p, 'limitada');
        }
    }
    function execucao(lado, q, p, motivo) {
        if (!q) return;
        S.custos += q * CUSTO;
        const antes = S.pos;
        if (S.pos && Math.sign(lado) !== Math.sign(S.pos)) {
            const fecha = Math.min(q, Math.abs(S.pos)), r = (p - S.medio) * Math.sign(S.pos) * fecha * PV;
            S.realizado += r;
            S.ops.push({ r, lado: S.pos > 0 ? 1 : -1, ini: S.aberta ? S.aberta.t : S.t, fim: S.t, pIni: S.medio, pFim: p, motivo, stop: S.aberta ? S.aberta.stop : false, qMax: S.aberta ? S.aberta.qMax : fecha });
            S.pos += Math.sign(lado) * fecha;
            const resto = q - fecha;
            if (resto) { S.pos = Math.sign(lado) * resto; S.medio = p; S.aberta = { t: S.t, stop: (+$('dm-stop').value || 0) > 0, qMax: resto }; }
            else if (!S.pos) S.aberta = null;
        } else {
            S.medio = S.pos ? (S.medio * Math.abs(S.pos) + p * q) / (Math.abs(S.pos) + q) : p;
            S.pos += Math.sign(lado) * q;
            if (S.aberta) S.aberta.qMax = Math.max(S.aberta.qMax, Math.abs(S.pos)); else S.aberta = { t: S.t, stop: (+$('dm-stop').value || 0) > 0, qMax: Math.abs(S.pos) };
        }
        S.entradas.push({ t: S.t, p, q: Math.sign(lado) * q, motivo });
        if (antes !== S.pos) oco();
        botoes();
    }
    function oco() {
        S.ordens = S.ordens.filter(o => o.tipo === 'lim');
        if (!S.pos) return;
        const sg = Math.sign(S.pos), st = +$('dm-stop').value || 0, al = +$('dm-alvo').value || 0, base = Math.round(S.medio / TICK) * TICK;
        if (st > 0) S.ordens.push({ id: S.nid++, tipo: 'stop', lado: -sg, p: base - sg * st, q: Math.abs(S.pos) });
        if (al > 0) { const p = base + sg * al; S.ordens.push({ id: S.nid++, tipo: 'alvo', lado: -sg, p, q: Math.abs(S.pos), ahead: (sg > 0 ? S.ask : S.bid).get(p) || 0 }); }
    }
    const qtd = () => Math.max(1, Math.min(50, Math.round(+$('dm-qtd').value || 1)));

    /* ---------- desenho ---------- */
    function render(forcar) {
        const agora = performance.now(); if (!forcar && agora - ultRender < 120) return; ultRender = agora;
        if (!S) return;
        const v = S.ult - S.ant, vp = v / S.ant * 100;
        $('dm-ult').textContent = fmt(S.ult); $('dm-var').textContent = `${v >= 0 ? '+' : '−'}${LX.num(Math.abs(vp), 2)}%`; $('dm-var').className = 'font-bold ' + cor(v);
        $('dm-hora').textContent = hora(S.t); $('dm-max').textContent = fmt(S.max); $('dm-min').textContent = fmt(S.min);
        $('dm-volume').textContent = fmt(S.vol); $('dm-neg').textContent = fmt(S.neg);
        escada(); fita(); agressao(); grafico(); posicao();
    }
    function escada() {
        const centro = Math.round(((S.bestAsk + S.bestBid) / 2) / TICK) * TICK;
        let maxQ = 1; for (let k = -LINHAS; k <= LINHAS; k++) { const p = centro + k * TICK; maxQ = Math.max(maxQ, S.ask.get(p) || 0, S.bid.get(p) || 0); }
        const minhas = (lado, p) => S.ordens.filter(o => o.lado === lado && o.p === p).map(o => `<span class="dm-ord dm-ord-${o.tipo}" title="${o.tipo === 'lim' ? 'ordem limitada' : o.tipo}">${o.tipo === 'stop' ? 'S' : o.tipo === 'alvo' ? 'A' : ''}${o.q}</span>`).join('');
        let h = '<div class="dm-row dm-head"><span>Minhas</span><span>Compra</span><span>Preço</span><span>Venda</span><span>Minhas</span></div>';
        for (let k = LINHAS; k >= -LINHAS; k--) {
            const p = centro + k * TICK, a = p >= S.bestAsk ? S.ask.get(p) || 0 : 0, b = p <= S.bestBid ? S.bid.get(p) || 0 : 0;
            const cls = (p === S.ult ? ' dm-ult' : '') + (S.pos && Math.round(S.medio / TICK) * TICK === p ? ' dm-medio' : '');
            h += `<div class="dm-row${cls}"><span class="dm-mc">${minhas(1, p)}</span>`
                + `<button type="button" class="dm-b" data-l="1" data-p="${p}" aria-label="Comprar limitado a ${p}">${b ? `<i style="width:${b / maxQ * 100}%"></i><b>${b}</b>` : ''}</button>`
                + `<span class="dm-p">${fmt(p)}</span>`
                + `<button type="button" class="dm-a" data-l="-1" data-p="${p}" aria-label="Vender limitado a ${p}">${a ? `<i style="width:${a / maxQ * 100}%"></i><b>${a}</b>` : ''}</button>`
                + `<span class="dm-mv">${minhas(-1, p)}</span></div>`;
        }
        $('dm-ladder').innerHTML = h;
    }
    function fita() {
        $('dm-tape').innerHTML = S.tape.slice(0, 28).map(x => `<div class="dm-tr${x.q >= 50 ? ' dm-big' : ''}${x.quem === 'eu' ? ' dm-eu' : ''}"><span>${hora(x.t)}</span><span>${fmt(x.p)}</span><span class="${x.s > 0 ? 'dm-c' : 'dm-v'}">${x.q}</span><span class="${x.s > 0 ? 'dm-c' : 'dm-v'}">${x.quem === 'eu' ? 'VOCÊ' : x.s > 0 ? 'COMPRA' : 'VENDA'}</span></div>`).join('') || '<div class="text-slate-500 p-2">Sem negócios ainda.</div>';
    }
    function agressao() {
        const ag = S.agS, um = ag.slice(-60).reduce((s, x) => [s[0] + x[0], s[1] + x[1]], [0, 0]);
        const set = (id, c, v) => { const t = c + v || 1; $(id).style.width = (c / t * 100) + '%'; $(id + '-txt').innerHTML = `<span class="dm-c">${fmt(c)}</span> × <span class="dm-v">${fmt(v)}</span>`; };
        set('dm-ag1', um[0], um[1]); set('dm-agd', S.diaC || 0, S.diaV || 0);
    }
    /* ---------- gráfico: tempos 1m a 60m e indicadores ---------- */
    const G = Object.assign({ tf: 1, vwap: true, mm9: true, mm21: true, bb: false, volume: true, ifr: false }, ls.get('lx-fluxo-graf') || {});
    let mira = null;   // posição do mouse/dedo para a cruz e o OHLC
    function agrupar(tf) {
        if (tf === 1) return S.velas;
        const out = [];
        for (const v of S.velas) {
            const k = Math.floor(v.t0 / (tf * 60)) * tf * 60, u = out[out.length - 1];
            if (u && u.t0 === k) { u.h = Math.max(u.h, v.h); u.l = Math.min(u.l, v.l); u.c = v.c; u.v += v.v; }
            else out.push({ t0: k, o: v.o, h: v.h, l: v.l, c: v.c, v: v.v });
        }
        return out;
    }
    const mme = (xs, n) => { const k = 2 / (n + 1); let e = null; return xs.map((x, i) => (e = e == null ? x : x * k + e * (1 - k), i >= n - 1 ? e : null)); };
    const bollinger = (xs, n = 20, d = 2) => xs.map((_, i) => { if (i < n - 1) return null; const a = xs.slice(i - n + 1, i + 1), m = a.reduce((s, x) => s + x, 0) / n, sd = Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / n); return [m - d * sd, m, m + d * sd]; });
    const ifr = (xs, n = 14) => { let g = 0, p = 0; return xs.map((x, i) => { if (!i) return null; const d = x - xs[i - 1]; if (i <= n) { g += Math.max(d, 0); p += Math.max(-d, 0); if (i < n) return null; g /= n; p /= n; } else { g = (g * (n - 1) + Math.max(d, 0)) / n; p = (p * (n - 1) + Math.max(-d, 0)) / n; } return p === 0 ? 100 : 100 - 100 / (1 + g / p); }); };
    function grafico() {
        const cv = $('dm-graf'), dpr = window.devicePixelRatio || 1, W = cv.clientWidth || 600;
        const cheia = document.body.classList.contains('dm-cheia-on');
        const H = cheia ? Math.max(320, innerHeight - 90) : (innerWidth < 640 ? 380 : 470);
        if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); cv.style.height = H + 'px'; }
        const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, W, H);
        const dark = document.documentElement.classList.contains('dark'), grade = dark ? '#1E2D42' : '#E2E8F0', txt = dark ? '#94A3B8' : '#64748B';
        const todas = agrupar(G.tf), PR = 58, PB = 16, cw = innerWidth < 640 ? 7 : 9;
        const nVis = Math.min(Math.max(15, Math.floor((W - PR) / cw)), Math.max(20, todas.length + 3)), ini = Math.max(0, todas.length - nVis), vis = todas.slice(ini);
        const fech = todas.map(v => v.c), e9 = G.mm9 ? mme(fech, 9) : [], e21 = G.mm21 ? mme(fech, 21) : [], bb = G.bb ? bollinger(fech) : [], rs = G.ifr ? ifr(fech) : [];
        // áreas: preço, volume, IFR
        const hIfr = G.ifr ? Math.round(H * 0.17) : 0, hVol = G.volume ? Math.round(H * 0.14) : 0;
        const yP0 = 6, yP1 = H - PB - hVol - hIfr - (G.volume || G.ifr ? 6 : 0);
        let lo = Math.min(...vis.map(v => v.l)), hi = Math.max(...vis.map(v => v.h));
        const vw = S.vwD ? S.vwN / S.vwD : S.ult;
        if (G.vwap) { lo = Math.min(lo, vw); hi = Math.max(hi, vw); }
        bb.slice(ini).forEach(b => { if (b) { lo = Math.min(lo, b[0]); hi = Math.max(hi, b[2]); } });
        S.ordens.forEach(o => { if (o.tipo !== 'lim') { lo = Math.min(lo, o.p); hi = Math.max(hi, o.p); } });
        const pad = Math.max((hi - lo) * 0.06, TICK * 6); lo -= pad; hi += pad;
        const Y = v => yP0 + (hi - v) / (hi - lo) * (yP1 - yP0), bw = (W - PR) / nVis, X = i => i * bw + bw / 2;
        c.font = '10px "JetBrains Mono", monospace'; c.lineWidth = 1;
        for (let k = 0; k <= 5; k++) { const v = Math.round((lo + (hi - lo) * k / 5) / TICK) * TICK, y = Y(v); c.strokeStyle = grade; c.beginPath(); c.moveTo(0, y); c.lineTo(W - PR, y); c.stroke(); c.fillStyle = txt; c.fillText(fmt(v), W - PR + 4, y + 3); }
        // Bollinger (área)
        if (G.bb) {
            const pts = bb.slice(ini).map((b, i) => b && [X(i), Y(b[0]), Y(b[1]), Y(b[2])]).filter(Boolean);
            if (pts.length > 1) {
                c.fillStyle = dark ? 'rgba(148,163,184,.08)' : 'rgba(100,116,139,.08)'; c.beginPath();
                pts.forEach((p, i) => i ? c.lineTo(p[0], p[3]) : c.moveTo(p[0], p[3])); [...pts].reverse().forEach(p => c.lineTo(p[0], p[1])); c.closePath(); c.fill();
                c.strokeStyle = '#94A3B8'; for (const k of [1, 3]) { c.beginPath(); pts.forEach((p, i) => i ? c.lineTo(p[0], p[k]) : c.moveTo(p[0], p[k])); c.stroke(); }
                c.setLineDash([3, 3]); c.beginPath(); pts.forEach((p, i) => i ? c.lineTo(p[0], p[2]) : c.moveTo(p[0], p[2])); c.stroke(); c.setLineDash([]);
            }
        }
        // candles
        vis.forEach((v, i) => {
            const x = X(i), col = v.c >= v.o ? '#10B981' : '#F43F5E';
            c.strokeStyle = col; c.beginPath(); c.moveTo(x, Y(v.h)); c.lineTo(x, Y(v.l)); c.stroke();
            c.fillStyle = col; const y1 = Y(Math.max(v.o, v.c)), y2 = Y(Math.min(v.o, v.c)); c.fillRect(x - bw * 0.36, y1, Math.max(1, bw * 0.72), Math.max(1, y2 - y1));
        });
        // médias
        const linhaS = (arr, col) => { c.strokeStyle = col; c.lineWidth = 1.6; c.beginPath(); let on = false; arr.slice(ini).forEach((v, i) => { if (v == null) return; on ? c.lineTo(X(i), Y(v)) : c.moveTo(X(i), Y(v)); on = true; }); c.stroke(); c.lineWidth = 1; };
        if (G.mm9) linhaS(e9, '#38BDF8');
        if (G.mm21) linhaS(e21, '#A78BFA');
        if (G.vwap) { c.strokeStyle = '#F39200'; c.lineWidth = 1.6; c.beginPath(); c.moveTo(0, Y(vw)); c.lineTo(W - PR, Y(vw)); c.stroke(); c.lineWidth = 1; }
        // suas linhas e entradas
        const linha = (p, col, rot) => { c.strokeStyle = col; c.setLineDash([5, 3]); c.beginPath(); c.moveTo(0, Y(p)); c.lineTo(W - PR, Y(p)); c.stroke(); c.setLineDash([]); c.fillStyle = col; c.fillText(rot, 4, Y(p) - 3); };
        if (S.pos) linha(S.medio, '#009988', `médio ${fmt(Math.round(S.medio))}`);
        S.ordens.forEach(o => { if (o.tipo === 'stop') linha(o.p, '#F43F5E', 'stop'); if (o.tipo === 'alvo') linha(o.p, '#10B981', 'alvo'); });
        const t0 = vis[0] ? vis[0].t0 : 0;
        S.entradas.forEach(e => { const i = Math.floor((e.t - t0) / (60 * G.tf)); if (i < 0 || i >= vis.length) return; const x = X(i), y = Y(e.p); c.fillStyle = e.q > 0 ? '#10B981' : '#F43F5E'; c.beginPath(); if (e.q > 0) { c.moveTo(x, y + 4); c.lineTo(x - 5, y + 13); c.lineTo(x + 5, y + 13); } else { c.moveTo(x, y - 4); c.lineTo(x - 5, y - 13); c.lineTo(x + 5, y - 13); } c.fill(); });
        // volume
        if (G.volume && vis.length) {
            const yv1 = yP1 + 6 + hVol, mv = Math.max(...vis.map(v => v.v), 1);
            c.strokeStyle = grade; c.beginPath(); c.moveTo(0, yP1 + 6); c.lineTo(W - PR, yP1 + 6); c.stroke();
            vis.forEach((v, i) => { const h = v.v / mv * (hVol - 4); c.fillStyle = v.c >= v.o ? 'rgba(16,185,129,.45)' : 'rgba(244,63,94,.45)'; c.fillRect(X(i) - bw * 0.36, yv1 - h, Math.max(1, bw * 0.72), h); });
            c.fillStyle = txt; c.fillText('VOL ' + fmt(vis[vis.length - 1].v), W - PR + 4, yP1 + 16);
        }
        // IFR
        if (G.ifr) {
            const y0 = H - PB - hIfr + 4, y1 = H - PB, Yr = v => y0 + (100 - v) / 100 * (y1 - y0);
            c.strokeStyle = grade; c.beginPath(); c.moveTo(0, y0 - 2); c.lineTo(W - PR, y0 - 2); c.stroke();
            c.setLineDash([2, 3]); for (const nv of [70, 30]) { c.beginPath(); c.moveTo(0, Yr(nv)); c.lineTo(W - PR, Yr(nv)); c.stroke(); c.fillStyle = txt; c.fillText(String(nv), W - PR + 4, Yr(nv) + 3); } c.setLineDash([]);
            linhaIfr(c, rs.slice(ini), X, Yr);
            const u = rs[rs.length - 1]; if (u != null) { c.fillStyle = '#E879F9'; c.fillText('IFR ' + u.toFixed(0), W - PR + 4, y0 + 8); }
        }
        // eixo do tempo
        c.fillStyle = txt; const passo = Math.max(1, Math.ceil(70 / bw));
        vis.forEach((v, i) => { if ((ini + i) % passo === 0) c.fillText(hora(v.t0).slice(0, 5), X(i) - 14, H - 3); });
        // preço atual
        c.fillStyle = S.ult >= S.ant ? '#10B981' : '#F43F5E'; c.fillRect(W - PR, Y(S.ult) - 7, PR, 14); c.fillStyle = '#fff'; c.fillText(fmt(S.ult), W - PR + 4, Y(S.ult) + 3);
        // cruz + OHLC da vela sob o mouse (ou da última)
        let iv = vis.length - 1;
        if (mira && mira.x < W - PR) { iv = Math.min(vis.length - 1, Math.max(0, Math.floor(mira.x / bw))); c.strokeStyle = txt; c.setLineDash([2, 3]); c.beginPath(); c.moveTo(X(iv), 0); c.lineTo(X(iv), H - PB); c.moveTo(0, mira.y); c.lineTo(W - PR, mira.y); c.stroke(); c.setLineDash([]);
            if (mira.y >= yP0 && mira.y <= yP1) { const pv = Math.round((hi - (mira.y - yP0) / (yP1 - yP0) * (hi - lo)) / TICK) * TICK; c.fillStyle = dark ? '#334155' : '#CBD5E1'; c.fillRect(W - PR, mira.y - 7, PR, 14); c.fillStyle = dark ? '#fff' : '#0C1A2A'; c.fillText(fmt(pv), W - PR + 4, mira.y + 3); } }
        const v = vis[iv];
        if (v) {
            const k = ini + iv, ex = [G.mm9 && e9[k] != null ? `<span style="color:#38BDF8">MME9 ${fmt(Math.round(e9[k]))}</span>` : '', G.mm21 && e21[k] != null ? `<span style="color:#A78BFA">MME21 ${fmt(Math.round(e21[k]))}</span>` : '', G.ifr && rs[k] != null ? `<span style="color:#E879F9">IFR ${rs[k].toFixed(0)}</span>` : ''].filter(Boolean).join(' ');
            $('dm-ohlc').innerHTML = `<span class="font-bold">WIN ${G.tf}m</span> ${hora(v.t0).slice(0, 5)} A <b>${fmt(v.o)}</b> M <b>${fmt(v.h)}</b> m <b>${fmt(v.l)}</b> F <b class="${v.c >= v.o ? 'dm-c' : 'dm-v'}">${fmt(v.c)}</b> V ${fmt(v.v)} ${ex}`;
        }
    }
    function linhaIfr(c, arr, X, Yr) { c.strokeStyle = '#E879F9'; c.lineWidth = 1.5; c.beginPath(); let on = false; arr.forEach((v, i) => { if (v == null) return; on ? c.lineTo(X(i), Yr(v)) : c.moveTo(X(i), Yr(v)); on = true; }); c.stroke(); c.lineWidth = 1; }
    function controlesGrafico() {
        const marcar = () => {
            document.querySelectorAll('#dm-tf [data-tf]').forEach(b => b.classList.toggle('dm-on', +b.dataset.tf === G.tf));
            document.querySelectorAll('#dm-ind [data-ind]').forEach(b => { b.classList.toggle('dm-on', !!G[b.dataset.ind]); b.setAttribute('aria-pressed', String(!!G[b.dataset.ind])); });
            ls.set('lx-fluxo-graf', G); if (S) render(true);
        };
        document.querySelectorAll('#dm-tf [data-tf]').forEach(b => b.onclick = () => { G.tf = +b.dataset.tf; marcar(); });
        document.querySelectorAll('#dm-ind [data-ind]').forEach(b => b.onclick = () => { G[b.dataset.ind] = !G[b.dataset.ind]; marcar(); });
        $('dm-cheia').onclick = () => { const on = document.body.classList.toggle('dm-cheia-on'); $('dm-cheia').innerHTML = `<i class="ph-bold ${on ? 'ph-arrows-in' : 'ph-arrows-out'}"></i>`; render(true); };
        document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && document.body.classList.contains('dm-cheia-on')) $('dm-cheia').click(); });
        const cv = $('dm-graf'), pos = ev => { const r = cv.getBoundingClientRect(), p = ev.touches ? ev.touches[0] : ev; mira = { x: p.clientX - r.left, y: p.clientY - r.top }; if (S) render(true); };
        cv.addEventListener('mousemove', pos); cv.addEventListener('touchmove', pos, { passive: true }); cv.addEventListener('touchstart', pos, { passive: true });
        cv.addEventListener('mouseleave', () => { mira = null; if (S) render(true); }); cv.addEventListener('touchend', () => { setTimeout(() => { mira = null; if (S) render(true); }, 1500); });
        marcar();
    }
    function posicao() {
        const t = total(), a = S.pos ? (S.ult - S.medio) * S.pos : 0;
        $('dm-res').textContent = brl(t); $('dm-res').className = cor(t);
        $('dm-res-pts').textContent = `${S.ops.length} operação(ões) · custos ${LX.brl(S.custos)}`;
        $('dm-pos').innerHTML = S.pos ? `<strong class="${S.pos > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">${S.pos > 0 ? 'COMPRADO' : 'VENDIDO'} ${Math.abs(S.pos)}</strong> a ${fmt(Math.round(S.medio))} · <span class="${cor(a)}">${pts(Math.round(a / Math.abs(S.pos)))}</span>` : (S.ordens.length ? `${S.ordens.length} ordem(ns) no book` : 'Sem posição');
    }
    function botoes() {
        const ok = rodando && S && !S.fim;
        $('dm-compra').disabled = $('dm-venda').disabled = !ok;
        $('dm-zera').disabled = !(ok && S.pos); $('dm-cancela').disabled = !(ok && S.ordens.some(o => o.tipo === 'lim'));
        $('dm-fim-btn').disabled = !(S && S.t > 0 && !S.fim);
        document.querySelectorAll('[data-espelho]').forEach(x => { x.disabled = $(x.dataset.espelho).disabled; });
    }

    /* ---------- relógio ---------- */
    function laco() {
        if (!rodando) return;
        acum += vel / 10;
        while (acum >= 1 && !S.fim) {
            acum -= 1;
            passo();
            const a = S.agS[S.agS.length - 1]; S.diaC = (S.diaC || 0) + a[0]; S.diaV = (S.diaV || 0) + a[1];
        }
        render(); botoes();
    }
    function tocar() {
        if (!S || S.fim) novoPregao();
        rodando = true; clearInterval(timer); timer = setInterval(laco, 100);
        $('dm-play').innerHTML = '<i class="ph-fill ph-pause"></i><span>PAUSAR</span>'; botoes();
        if (S.t === 0) track('fluxo_inicio', { semente: S.seed });
    }
    function pausar() { rodando = false; clearInterval(timer); $('dm-play').innerHTML = '<i class="ph-fill ph-play"></i><span>CONTINUAR</span>'; botoes(); }

    /* ---------- relatório ---------- */
    function encerrar() {
        if (!S || S.fim) return;
        if (S.pos) mercado(-Math.sign(S.pos), 'fechamento');
        S.ordens = []; S.fim = true; pausar();
        $('dm-play').innerHTML = '<i class="ph-bold ph-arrow-counter-clockwise"></i><span>NOVO PREGÃO</span>';
        const ops = S.ops, r = total(), ganhos = ops.filter(o => o.r > 0), perdas = ops.filter(o => o.r < 0);
        const erros = [];
        if (ops.length > 15) erros.push(['ph-repeat', 'Excesso de operações', `${ops.length} operações. No fluxo é fácil operar cada lote que aparece; os custos e as decisões ruins somam rápido.`]);
        const semStop = ops.filter(o => !o.stop).length; if (semStop) erros.push(['ph-shield-slash', 'Operou sem stop', `${semStop} operação(ões) sem stop automático.`]);
        const vinganca = ops.filter((o, n) => n && ops[n - 1].r < 0 && o.ini - ops[n - 1].fim <= 60 && o.qMax > ops[n - 1].qMax).length;
        if (vinganca) erros.push(['ph-fire', 'Trade de vingança', `${vinganca} vez(es) você voltou em menos de 1 minuto depois de uma perda e com mais contratos.`]);
        const noNoticia = S.entradas.filter(e => e.motivo !== 'stop' && e.motivo !== 'alvo' && e.motivo !== 'fechamento' && S.ev.some(v => v.tipo === 'noticia' && e.t >= v.ate - 65 && e.t <= v.ate)).length;
        if (noNoticia) erros.push(['ph-megaphone', 'Entrou no meio da notícia', `${noNoticia} entrada(s) durante a notícia simulada, quando o book fica fino e o preço salta.`]);
        const pm = ganhos.length && perdas.length ? (ganhos.reduce((s, o) => s + o.r, 0) / ganhos.length) / Math.abs(perdas.reduce((s, o) => s + o.r, 0) / perdas.length) : null;
        if (pm != null && pm < 1 && ganhos.length >= perdas.length) erros.push(['ph-scales', 'Ganha pouco, perde muito', `Ganho médio de ${LX.num(pm, 2)}× a perda média.`]);
        // leitura do fluxo: entradas até 60 s depois de um alerta do professor
        const lidas = [];
        S.entradas.filter(e => e.motivo === 'manual' || e.motivo === 'limitada').forEach(e => {
            const d = S.dicas.filter(x => x.lado && e.t - x.t >= 0 && e.t - x.t <= 60).pop();
            if (d) lidas.push({ a_favor: Math.sign(e.q) === d.lado, tipo: d.tipo });
        });
        const melhor = ls.get('lx-fluxo-melhor') || {}, rec = ops.length && (melhor[S.seed] == null || r > melhor[S.seed]);
        if (rec) { melhor[S.seed] = Math.round(r); ls.set('lx-fluxo-melhor', melhor); }
        const url = `${location.origin}${location.pathname}?seed=${S.seed}`;
        $('dm-fim').innerHTML = `
            <div class="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div><span class="term-label text-lect-orange font-bold">FIM DO PREGÃO · SEMENTE ${S.seed}</span>
                    <strong class="block font-display text-4xl font-bold mt-1 ${cor(r)}">${brl(r)}</strong>
                    <span class="text-sm text-slate-600 dark:text-slate-400">${ops.length} operação(ões) · acerto ${ops.length ? LX.num(ganhos.length / ops.length * 100, 0) + '%' : '—'} · pior momento −${LX.brl(S.maxDD)} · custos ${LX.brl(S.custos)}${rec ? ' · <strong class="text-lect-orange">seu recorde nesta semente</strong>' : ''}</span></div>
                <div class="flex flex-wrap gap-2 font-mono text-xs">
                    <button type="button" id="dm-share" class="pg-btn pg-btn-teal min-h-[44px]"><i class="ph-bold ph-share-network"></i><span>DESAFIAR UM AMIGO</span></button>
                    <button type="button" id="dm-novo" class="pg-btn min-h-[44px]"><i class="ph-bold ph-shuffle"></i>OUTRO PREGÃO</button>
                </div>
            </div>
            ${lidas.length ? `<p class="text-sm mt-4"><strong>Leitura do fluxo:</strong> ${lidas.length} entrada(s) logo depois de um alerta do professor, ${lidas.filter(x => x.a_favor).length} a favor da leitura dele. Compare com o resultado dessas operações no gráfico.</p>` : ''}
            <div class="mt-4"><span class="term-label">Erros de risco</span>${erros.length ? `<ul class="mt-2 grid grid-cols-1 md:grid-cols-2 gap-3">${erros.map(e => `<li class="flex gap-3 p-3 bg-slate-50 dark:bg-lect-bgDark border border-slate-200 dark:border-lect-borderDark"><i class="ph-duotone ${e[0]} text-2xl text-lect-orange shrink-0"></i><span class="text-sm"><strong class="block">${e[1]}</strong><span class="text-slate-600 dark:text-slate-400">${e[2]}</span></span></li>`).join('')}</ul>` : `<p class="text-sm mt-2 text-slate-600 dark:text-slate-400">${ops.length ? 'Nenhum erro clássico de risco. Disciplina vale mais que o resultado de um pregão.' : 'Você não operou. Ler o fluxo sem operar também é treino.'}</p>`}</div>
            <p class="text-xs text-slate-500 mt-4">Mesma semente = mesmo pregão: mande o link para um amigo e comparem o resultado. <a href="simulador.html" class="text-lect-teal underline">Treine também com dias reais no Simulador de pregão.</a></p>`;
        $('dm-fim').classList.remove('hidden'); $('dm-fim').scrollIntoView({ behavior: 'smooth', block: 'start' });
        $('dm-novo').onclick = () => { $('dm-seed').value = ''; novoPregao(); window.scrollTo({ top: 0, behavior: 'smooth' }); };
        $('dm-share').onclick = () => { const t = `Fiz ${brl(r)} no simulador de fluxo do mini índice da Lectnex (semente ${S.seed}). Consegue mais no mesmo pregão? ${url}`; (navigator.share ? navigator.share({ text: t }).catch(() => { }) : navigator.clipboard.writeText(t).then(() => { $('dm-share').querySelector('span').textContent = 'COPIADO!'; }).catch(() => { })); track('fluxo_compartilhar', {}); };
        track('fluxo_fim', { resultado: Math.round(r), operacoes: ops.length });
        setTimeout(() => window.LX && LX.convite && LX.convite('simulador'), 4000);
        render(true);
    }

    /* ---------- eventos da tela ---------- */
    $('dm-play').onclick = () => rodando ? pausar() : tocar();
    document.querySelectorAll('.pg-vel[data-v]').forEach(b => b.onclick = () => { vel = +b.dataset.v; document.querySelectorAll('.pg-vel[data-v]').forEach(x => x.classList.toggle('pg-on', x === b)); });
    $('dm-compra').onclick = () => mercado(1); $('dm-venda').onclick = () => mercado(-1);
    $('dm-zera').onclick = () => { S.ordens = S.ordens.filter(o => o.tipo === 'lim'); if (S.pos) mercado(-Math.sign(S.pos), 'manual'); };
    $('dm-cancela').onclick = () => { S.ordens = S.ordens.filter(o => o.tipo !== 'lim'); render(true); botoes(); };
    $('dm-fim-btn').onclick = encerrar;
    document.querySelectorAll('[data-espelho]').forEach(x => x.onclick = () => $(x.dataset.espelho).click());
    $('dm-ladder').addEventListener('click', ev => { const b = ev.target.closest('button[data-p]'); if (b) ordemLimitada(+b.dataset.l, +b.dataset.p); });
    ['dm-stop', 'dm-alvo'].forEach(id => $(id).addEventListener('change', () => { if (S && S.pos) { oco(); render(true); } }));
    ['dm-vol', 'dm-seed'].forEach(id => $(id).addEventListener('change', () => { if (!rodando && S && S.t === 0) novoPregao(); }));
    document.addEventListener('keydown', ev => {
        if (/INPUT|SELECT|TEXTAREA/.test(ev.target.tagName)) return;
        const k = ev.key.toLowerCase();
        if (k === 'c' && rodando) mercado(1); else if (k === 'v' && rodando) mercado(-1);
        else if (k === 'z' && S && S.pos) $('dm-zera').click();
        else if (k === ' ') { ev.preventDefault(); rodando ? pausar() : tocar(); }
    });
    controlesGrafico();
    // abas no celular
    const aba = a => { document.body.dataset.aba = a; document.querySelectorAll('.dm-nav [data-ir]').forEach(b => b.classList.toggle('dm-on', b.dataset.ir === a)); render(true); };
    document.querySelectorAll('.dm-nav [data-ir]').forEach(b => b.onclick = () => aba(b.dataset.ir));
    document.body.dataset.aba = 'dom';
    let rz; window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => render(true), 150); });

    // começa no último fechamento real do Ibovespa (data/dias), arredondado para o tick do WIN
    const q = new URLSearchParams(location.search);
    if (q.get('teste') === '1') window.__dm = { rodar: n => { rodando = true; for (let i = 0; i < n && !S.fim; i++) passo(); render(true); }, S: () => S };
    if (q.get('seed')) $('dm-seed').value = q.get('seed').toUpperCase().slice(0, 8);
    fetch('data/dias/indice.json').then(r => r.json()).then(j => fetch(`data/dias/${j.dias[j.dias.length - 1]}.json`)).then(r => r.json())
        .then(d => { const p = (d.ibov || {}).pontos || []; if (p.length) inicio = Math.round(p[p.length - 1][1] / TICK) * TICK; })
        .catch(() => { }).finally(() => novoPregao());
})();
