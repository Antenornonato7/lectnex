/* Lectnex — Plantão / FLASH no Mercado Hoje.
   Lê data/plantao.json e preenche #plantao. Para o próximo FLASH, troque só o JSON. */
(function () {
    const root = document.getElementById('plantao');
    const list = document.getElementById('plantao-list');
    const when = document.getElementById('plantao-when');
    const aviso = document.getElementById('plantao-aviso');
    if (!root || !list || !window.LX) return;

    const esc = LX.esc;

    function quandoCT(iso) {
        const d = new Date(iso);
        if (!iso || Number.isNaN(d.getTime())) return '';
        const data = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'America/Chicago', year: 'numeric', month: '2-digit', day: '2-digit'
        }).format(d);
        const hora = new Intl.DateTimeFormat('en-GB', {
            timeZone: 'America/Chicago', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
        }).format(d);
        return `${data} · ${hora} CT`;
    }

    fetch('data/plantao.json?t=' + Date.now(), { cache: 'no-store' })
        .then(r => r.ok ? r.json() : null)
        .then(j => {
            if (!j || !Array.isArray(j.itens)) return;
            const itens = j.itens.filter(n => n && String(n.titulo || '').trim() && /^https?:\/\//i.test(String(n.url || ''))).slice(0, 9);
            if (!itens.length) return;
            const selo = quandoCT(j.atualizado_em) || quandoCT(itens[0].publicado_em);
            if (when) {
                when.textContent = selo || '';
                when.title = 'America/Chicago (CT)';
            }
            if (aviso && j.aviso) aviso.textContent = String(j.aviso);
            list.innerHTML = itens.map(n => {
                const hora = quandoCT(n.publicado_em) || selo;
                const ctx = String(n.contexto || '').trim();
                const fonte = String(n.fonte || '').trim();
                return `<a href="${esc(n.url)}" target="_blank" rel="noopener" class="group block min-w-0 p-3.5 bg-slate-50 dark:bg-lect-bgDark border border-slate-200 dark:border-lect-borderDark hover:border-lect-teal transition-colors">
                    <div class="flex items-center justify-between gap-2 font-mono text-[10px] text-slate-500"><span class="truncate">${fonte ? 'Fonte: ' + esc(fonte) : 'Fonte'}</span><i class="ph-bold ph-arrow-up-right shrink-0 group-hover:text-lect-teal" aria-hidden="true"></i></div>
                    <strong class="block text-sm leading-snug mt-1.5">${esc(n.titulo)}</strong>
                    ${ctx ? `<p class="text-[11px] text-slate-600 dark:text-slate-300 mt-1.5 leading-snug">${esc(ctx)}</p>` : ''}
                    <span class="block font-mono text-[10px] text-slate-500 mt-2" title="America/Chicago">${esc(hora)} · America/Chicago</span>
                </a>`;
            }).join('');
            root.classList.remove('hidden');
        })
        .catch(() => { });
})();
