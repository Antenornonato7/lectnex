/* Lectnex — "Meu painel": foco (WIN, WDO ou os dois), ações favoritas e seções escondidas no Mercado Hoje.
   Tudo salvo só neste navegador (localStorage), sem login. */
(function () {
    const KEY = 'lectnex-painel-v1', $ = id => document.getElementById(id);
    const SECOES = [['leitura', 'Leitura do Dia'], ['indicadores', 'Juros, inflação e câmbio'], ['noticias', 'Calendário e notícias'], ['placar-term', 'Placar do viés do modelo'], ['mapa', 'Mapa da bolsa'], ['agenda', 'Vencimentos e câmbio']];
    const ler = () => Object.assign({ alertaAcoes: false }, window.lxPainel ? window.lxPainel() : { foco: 'ambos', acoes: [], ocultas: [] });
    const salvar = p => { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (_) { } document.dispatchEvent(new CustomEvent('lx:painel', { detail: p })); aplicar(); };
    let mapa = [];

    function aplicar() {
        const p = ler();
        SECOES.forEach(([id]) => { const el = $(id); if (el) el.classList.toggle('lx-oculta', p.ocultas.includes(id)); document.querySelectorAll(`nav a[href="#${id}"]`).forEach(a => a.classList.toggle('lx-oculta', p.ocultas.includes(id))); });
        const box = $('pn-acoes');
        if (box) {
            const lista = p.acoes.map(t => mapa.find(x => x.ticker === t)).filter(Boolean);
            box.classList.toggle('hidden', !lista.length);
            box.innerHTML = lista.length ? `<span class="term-label !mb-0 inline-flex items-center gap-1"><i class="ph-bold ph-star text-lect-orange"></i>Minhas ações</span>` + lista.map(x => `<a href="acoes.html?ticker=${x.ticker}" class="hover:text-lect-teal"><strong>${x.ticker}</strong> <span class="${LX.signClass(x.var_pct)}">${x.var_pct > 0 ? '+' : x.var_pct < 0 ? '−' : ''}${LX.num(Math.abs(x.var_pct), 2)}%</span></a>`).join('') : '';
        }
    }

    function abrir() {
        let el = $('pn-modal'); if (el) { el.remove(); return; }
        const p = ler();
        el = document.createElement('div'); el.id = 'pn-modal'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', 'Personalizar o Mercado Hoje');
        el.className = 'fixed z-[90] inset-x-3 bottom-3 sm:inset-x-auto sm:right-4 sm:w-[420px] max-h-[85vh] overflow-y-auto term-panel shadow-2xl p-4 text-slate-800 dark:text-slate-200';
        const chip = (on, attr, label) => `<button type="button" ${attr} class="px-2.5 py-1 font-mono text-[11px] ${on ? 'bg-lect-navy text-white dark:bg-lect-teal font-bold' : 'border border-slate-300 dark:border-lect-borderDark hover:text-lect-teal'}">${label}</button>`;
        el.innerHTML = `<div class="flex items-start justify-between gap-2"><strong class="font-display inline-flex items-center gap-2"><i class="ph-bold ph-sliders-horizontal text-lect-teal"></i>Meu painel</strong><button type="button" data-x class="text-slate-400 hover:text-lect-teal" aria-label="Fechar"><i class="ph-bold ph-x"></i></button></div>
            <p class="text-[11px] text-slate-500 mt-1">Salvo só neste navegador. Muda a ordem do que você vê, não os dados.</p>
            <span class="term-label block mt-4 mb-1.5">O que você opera</span>
            <div class="flex gap-1.5">${chip(p.foco === 'ambos', 'data-foco="ambos"', 'WIN e WDO')}${chip(p.foco === 'win', 'data-foco="win"', 'Só WIN')}${chip(p.foco === 'wdo', 'data-foco="wdo"', 'Só WDO')}</div>
            <p class="text-[10px] text-slate-500 mt-1">Filtra o calendário e o viés do modelo da Leitura do Dia.</p>
            <span class="term-label block mt-4 mb-1.5">Minhas ações (até 8)</span>
            <div class="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto thin-scroll">${(mapa.length ? mapa.map(x => x.ticker) : p.acoes).sort().map(t => chip(p.acoes.includes(t), `data-acao="${t}"`, t)).join('') || '<span class="text-xs text-slate-500">carregando…</span>'}</div>
            ${LX.config && LX.config.onesignal ? `<label class="mt-3 flex items-start gap-2 text-sm cursor-pointer"><input type="checkbox" data-alerta class="mt-0.5 accent-[#009988]" ${p.alertaAcoes ? 'checked' : ''}><span><strong class="inline-flex items-center gap-1"><i class="ph-bold ph-bell-ringing text-lect-orange"></i>Avisar no celular</strong> quando ${p.acoes.length ? p.acoes.slice(0, 3).join(', ') : 'minhas ações'} subir ou cair mais de 3% no dia (e de novo a 6%).<span class="block text-[10px] text-slate-500">Vale para as 3 primeiras da lista. Cotações com atraso de ~30 min.</span><span data-alerta-msg class="block text-[11px] font-mono"></span></span></label>` : ''}
            <span class="term-label block mt-4 mb-1.5">Seções que aparecem</span>
            <div class="space-y-1.5">${SECOES.map(([id, nome]) => `<label class="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" data-sec="${id}" class="accent-[#009988]" ${p.ocultas.includes(id) ? '' : 'checked'}>${nome}</label>`).join('')}</div>
            <span class="term-label block mt-4 mb-1.5">Leitura</span>
            <label class="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" data-hc class="accent-[#009988]" ${document.documentElement.classList.contains('lx-hc') ? 'checked' : ''}>Alto contraste <span class="text-[11px] text-slate-500">(textos mais fortes e maiores, vale para todo o site)</span></label>
            <button type="button" data-reset class="mt-4 font-mono text-[11px] text-slate-500 hover:text-lect-teal underline">voltar ao padrão</button>`;
        document.body.appendChild(el);
        el.querySelector('[data-x]').onclick = () => el.remove();
        const redraw = () => { el.remove(); abrir(); };
        el.querySelectorAll('[data-foco]').forEach(b => b.onclick = () => { const q = ler(); q.foco = b.dataset.foco; salvar(q); redraw(); });
        el.querySelectorAll('[data-acao]').forEach(b => b.onclick = () => { const q = ler(), t = b.dataset.acao; q.acoes = q.acoes.includes(t) ? q.acoes.filter(x => x !== t) : q.acoes.concat(t).slice(-8); salvar(q); if (q.alertaAcoes && LX.pushAcoes) LX.pushAcoes(q.acoes.slice(0, 3)).catch(() => { }); redraw(); });
        el.querySelectorAll('[data-sec]').forEach(c => c.onchange = () => { const q = ler(); q.ocultas = c.checked ? q.ocultas.filter(x => x !== c.dataset.sec) : q.ocultas.concat(c.dataset.sec); salvar(q); });
        const al = el.querySelector('[data-alerta]');
        if (al) al.onchange = async () => {
            const q = ler(), msg = el.querySelector('[data-alerta-msg]');
            msg.textContent = 'conectando…';
            try {
                await LX.pushAcoes(al.checked ? q.acoes.slice(0, 3) : []);
                q.alertaAcoes = al.checked; salvar(q);
                msg.innerHTML = al.checked ? '<span class="text-emerald-500">✓ alertas ligados</span>' : 'alertas desligados';
            } catch (err) { al.checked = !al.checked; msg.textContent = 'não deu para ativar: libere as notificações do site e tente de novo'; }
        };
        el.querySelector('[data-hc]').onchange = e2 => { document.documentElement.classList.toggle('lx-hc', e2.target.checked); try { localStorage.setItem('lectnex-hc', e2.target.checked ? '1' : '0'); } catch (_) { } };
        el.querySelector('[data-reset]').onclick = () => { try { localStorage.removeItem(KEY); } catch (_) { } document.dispatchEvent(new CustomEvent('lx:painel')); aplicar(); redraw(); };
    }

    const st = document.createElement('style'); st.textContent = '.lx-oculta{display:none!important}'; document.head.appendChild(st);
    const btn = $('pn-open'); if (btn) btn.addEventListener('click', abrir);
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && $('pn-modal')) $('pn-modal').remove(); });
    LX.dados('cotacoes').then(c => { mapa = (c && c.mapa || []).filter(x => typeof x.var_pct === 'number'); aplicar(); }).catch(() => { });
    aplicar();
})();
