"""Avisa os buscadores de páginas novas, logo depois que um robô publica (divulgação, dados, juros).

- Bing, Yandex e outros: IndexNow (coletor/indexnow.py), com a lista de PAGINAS.
- Google: não existe "pedir indexação" por API para páginas comuns (a Indexing API do Google é só para vagas de emprego
  e transmissões ao vivo). O que dá para fazer é reenviar o sitemap pelo Search Console, o que pede ao Google para
  ler o sitemap de novo. Precisa que a conta de serviço (segredo GSC_SERVICE_ACCOUNT) seja usuário com permissão
  TOTAL da propriedade; com permissão restrita, só avisa no log.
Nunca derruba o workflow.
"""
import os
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))


def google_sitemap():
    bruto = os.environ.get('GSC_SERVICE_ACCOUNT', '').strip()
    if not bruto:
        print('::notice::Google: sem GSC_SERVICE_ACCOUNT, sitemap não reenviado.')
        return
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        import search_console as sc
        cred = service_account.Credentials.from_service_account_info(sc.ler_chave(bruto), scopes=['https://www.googleapis.com/auth/webmasters'])
        s = AuthorizedSession(cred)
        site = sc.propriedade(s)
        mapa = 'https://lectnex.com.br/sitemap.xml'
        r = s.put(f'{sc.API}/webmasters/v3/sites/{urllib.parse.quote(site, safe="")}/sitemaps/{urllib.parse.quote(mapa, safe="")}', timeout=60)
        if r.status_code < 300:
            print('::notice::Google: sitemap reenviado ao Search Console.')
        elif r.status_code == 403:
            print('::warning::Google: a conta de serviço precisa de permissão TOTAL na propriedade do Search Console para reenviar o sitemap.')
        else:
            print(f'::warning::Google: sitemap recusado (HTTP {r.status_code}): {r.text[:200]}')
    except Exception as e:
        print(f'::warning::Google: {e}')


if __name__ == '__main__':
    paginas = os.environ.get('PAGINAS', '').strip()
    if not paginas:
        print('::notice::Nenhuma página nova para avisar.')
        raise SystemExit
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'indexnow.py')], env={**os.environ, 'PAGINAS': paginas})
    google_sitemap()
