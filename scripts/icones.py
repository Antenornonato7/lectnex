"""Gera assets/icons/ com só os ícones Phosphor usados no site (CSS + fontes recortadas).

Uso: python3 scripts/icones.py            (baixa o Phosphor v2.1.1 do GitHub se precisar)
Requer: pip install fonttools==4.66.1 (mesma versão do workflow, para a saída ser idêntica)
"""
import glob, os, re, subprocess, sys, tempfile
from fontTools import subset

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RAIZ)
PH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), 'phosphor-web')
if not os.path.isdir(os.path.join(PH, 'src')):
    subprocess.run(['git', 'clone', '-q', '--depth', '1', '--branch', 'v2.1.1', 'https://github.com/phosphor-icons/web', PH], check=True)

usados = set()
for f in glob.glob('*.html') + glob.glob('assets/*.js'):
    usados |= set(re.findall(r'ph-([a-z0-9]+(?:-[a-z0-9]+)*)', open(f, encoding='utf-8').read()))

saida = ['/* Phosphor Icons v2.1.1 (MIT) — https://github.com/phosphor-icons/web\n'
         '   Recorte com só os ícones usados no Lectnex. Para acrescentar ícones, rode: python3 scripts/icones.py */']
os.makedirs('assets/icons', exist_ok=True)
import hashlib
VER = hashlib.sha1(','.join(sorted(usados)).encode()).hexdigest()[:8]  # muda só quando a lista de ícones muda (renova o cache do app)
for peso, fonte, classe in [('regular', 'Phosphor', 'ph'), ('bold', 'Phosphor-Bold', 'ph-bold'),
                            ('fill', 'Phosphor-Fill', 'ph-fill'), ('duotone', 'Phosphor-Duotone', 'ph-duotone')]:
    css = open(os.path.join(PH, 'src', peso, 'style.css'), encoding='utf-8').read()
    manter, codigos = [], set()
    for sel, corpo in re.findall(r'([^{}]+)\{([^}]*)\}', css):
        sel = sel.strip()
        if sel.startswith('@font-face'):
            manter.append('@font-face {\n  font-family: "%s";\n  src: url("./%s.woff?v=%s") format("woff");\n'
                          '  font-weight: normal;\n  font-style: normal;\n  font-display: block;\n}' % (fonte, fonte, VER))
            continue
        m = re.match(r'^\.' + re.escape(classe) + r'\.ph-([a-z0-9-]+):(before|after)$', sel)
        if m:
            if m.group(1) not in usados:
                continue
            c = re.search(r'content:\s*"\\([0-9a-f]+)"', corpo)
            if c:
                codigos.add(int(c.group(1), 16))
        manter.append('%s {%s}' % (sel, corpo))
    saida.append('\n'.join(manter))
    op = subset.Options(); op.flavor = 'woff'; op.layout_features = ['*']; op.notdef_outline = True; op.name_IDs = ['*']
    f = subset.load_font(os.path.join(PH, 'src', peso, fonte + '.ttf'), op)
    s = subset.Subsetter(op); s.populate(unicodes=codigos); s.subset(f)
    f.recalcTimestamp = False  # saída idêntica a cada execução (evita commits à toa)
    subset.save_font(f, os.path.join('assets', 'icons', fonte + '.woff'), op)
    print(f'{peso}: {len(codigos)} glifos')
open('assets/icons/phosphor.css', 'w', encoding='utf-8').write('\n'.join(saida) + '\n')
