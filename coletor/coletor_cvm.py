#!/usr/bin/env python3
"""
Coletor Lectnex — dados abertos da CVM (licença ODbL, republicação permitida citando a fonte).

Gera dois arquivos lidos pelo site:
  data/fundos-acoes.json    Quem é dono de cada ação (carteiras de fundos — CDA, bloco 4)
  data/captacao-acoes.json  Captação líquida diária dos fundos de ações (Informe Diário)

Fontes:
  https://dados.cvm.gov.br/dataset/fi-doc-cda
  https://dados.cvm.gov.br/dataset/fi-doc-inf_diario
  https://dados.cvm.gov.br/dataset/fi-cad

Uso:   python coletor/coletor_cvm.py            (só biblioteca padrão do Python 3.9+)
       python coletor/coletor_cvm.py --teste DIR (processa ZIPs locais de DIR, sem baixar)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

BASE = "https://dados.cvm.gov.br/dados/FI"
URL_CDA = BASE + "/DOC/CDA/DADOS/cda_fi_{ym}.zip"
URL_INF = BASE + "/DOC/INF_DIARIO/DADOS/inf_diario_fi_{ym}.zip"
URL_CAD_NOVO = BASE + "/CAD/DADOS/registro_fundo_classe.zip"
URL_CAD_LEGADO = BASE + "/CAD/DADOS/cad_fi.csv"

UA = "Lectnex-coletor/1.0 (site educacional; dados abertos CVM)"
TICKER_RE = re.compile(r"^[A-Z]{4}(3|4|5|6|7|8|11)$")
TOP_HOLDERS = 10
TOP_MOVES = 5
MAX_TICKERS = 250
DIAS_CAPTACAO = 90

csv.field_size_limit(10_000_000)


# ----------------------------------------------------------------------------- utilidades
def log(*a):
    print("[coletor]", *a, file=sys.stderr, flush=True)


def baixar(url: str, tentativas: int = 3) -> bytes | None:
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            log(f"HTTP {e.code} em {url} (tentativa {i + 1})")
        except Exception as e:  # rede instável
            log(f"falha em {url}: {e} (tentativa {i + 1})")
        time.sleep(3 * (i + 1))
    return None


def meses_para_tras(n: int, de: dt.date | None = None):
    d = (de or dt.date.today()).replace(day=1)
    for _ in range(n):
        yield d.strftime("%Y%m")
        d = (d - dt.timedelta(days=1)).replace(day=1)


def ler_csv(zf: zipfile.ZipFile, nome: str):
    with zf.open(nome) as f:
        texto = io.TextIOWrapper(f, encoding="latin-1", newline="")
        yield from csv.DictReader(texto, delimiter=";")


def col(row_keys, *candidatos):
    """Acha a coluna pelo nome, tolerando renomeações (ex.: CNPJ_FUNDO → CNPJ_FUNDO_CLASSE)."""
    keys = {k.upper(): k for k in row_keys}
    for c in candidatos:
        if c.upper() in keys:
            return keys[c.upper()]
    return None


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def so_digitos(s):
    return re.sub(r"\D", "", s or "")


# ----------------------------------------------------------------------------- CDA (carteiras)
def posicoes_acoes(zbytes: bytes):
    """Retorna {ticker: {cnpj: {fund, qty, value}}} do bloco 4 (ativos codificados, inclui ações)."""
    zf = zipfile.ZipFile(io.BytesIO(zbytes))
    nomes = [n for n in zf.namelist() if re.search(r"BLC_4", n, re.I)]
    if not nomes:
        log("bloco 4 não encontrado em", zf.namelist())
        return {}
    pos = defaultdict(dict)
    for nome in nomes:
        cols = None
        for r in ler_csv(zf, nome):
            if cols is None:
                k = r.keys()
                cols = {
                    "cnpj": col(k, "CNPJ_FUNDO_CLASSE", "CNPJ_FUNDO"),
                    "nome": col(k, "DENOM_SOCIAL"),
                    "aplic": col(k, "TP_APLIC"),
                    "ativo": col(k, "CD_ATIVO"),
                    "qty": col(k, "QT_POS_FINAL"),
                    "val": col(k, "VL_MERC_POS_FINAL"),
                }
                if not cols["ativo"] or not cols["cnpj"]:
                    log("layout inesperado em", nome, list(k)[:25])
                    break
            aplic = (r.get(cols["aplic"]) or "").strip().lower() if cols["aplic"] else "ações"
            if not aplic.startswith("aç") and not aplic.startswith("ac"):
                continue
            tk = (r.get(cols["ativo"]) or "").strip().upper()
            if not TICKER_RE.match(tk):
                continue
            cnpj = so_digitos(r.get(cols["cnpj"]))
            atual = pos[tk].get(cnpj)
            q, v = num(r.get(cols["qty"])), num(r.get(cols["val"]))
            if atual:
                atual["qty"] += q
                atual["value"] += v
            else:
                pos[tk][cnpj] = {"fund": (r.get(cols["nome"]) or "").strip(), "qty": q, "value": v}
    return pos


def montar_fundos_acoes(fonte_zip):
    """Pega o mês mais recente com volume relevante e compara com o mês anterior."""
    meses = []
    for ym in meses_para_tras(8):
        z = fonte_zip("cda", ym)
        if not z:
            continue
        pos = posicoes_acoes(z)
        n = sum(len(v) for v in pos.values())
        log(f"CDA {ym}: {len(pos)} ações, {n} posições")
        if n > 2000:  # meses recentes vêm quase vazios por causa do sigilo
            meses.append((ym, pos))
        if len(meses) == 2:
            break
    if not meses:
        return None
    ref, atual = meses[0]
    prev_ref, anterior = meses[1] if len(meses) > 1 else (None, {})

    ranking = sorted(atual.items(), key=lambda kv: -sum(p["value"] for p in kv[1].values()))[:MAX_TICKERS]
    out = {}
    for tk, fundos in ranking:
        prev = anterior.get(tk, {})
        holders = sorted(fundos.items(), key=lambda kv: -kv[1]["value"])
        moves = []
        for cnpj in set(fundos) | set(prev):
            q1 = fundos.get(cnpj, {}).get("qty", 0.0)
            q0 = prev.get(cnpj, {}).get("qty", 0.0)
            if q1 != q0:
                nome = (fundos.get(cnpj) or prev.get(cnpj))["fund"]
                moves.append({"fund": nome, "cnpj": cnpj, "delta": q1 - q0, "qty": q1})
        moves.sort(key=lambda m: m["delta"])
        total_qty = sum(p["qty"] for p in fundos.values())
        prev_qty = sum(p["qty"] for p in prev.values())
        out[tk] = {
            "funds": len(fundos),
            "fundsPrev": len(prev),
            "qty": round(total_qty),
            "qtyPrev": round(prev_qty),
            "value": round(sum(p["value"] for p in fundos.values())),
            "holders": [{"fund": p["fund"], "cnpj": c, "qty": round(p["qty"]), "value": round(p["value"])}
                        for c, p in holders[:TOP_HOLDERS]],
            "buyers": [{**m, "delta": round(m["delta"]), "qty": round(m["qty"])} for m in moves[::-1][:TOP_MOVES] if m["delta"] > 0],
            "sellers": [{**m, "delta": round(m["delta"]), "qty": round(m["qty"])} for m in moves[:TOP_MOVES] if m["delta"] < 0],
        }
    return {
        "source": "CVM — Carteiras de Fundos de Investimento (CDA), licença ODbL",
        "sourceUrl": "https://dados.cvm.gov.br/dataset/fi-doc-cda",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "ref": f"{ref[:4]}-{ref[4:]}",
        "prevRef": f"{prev_ref[:4]}-{prev_ref[4:]}" if prev_ref else None,
        "note": "Posições não confidenciais. Fundos podem pedir sigilo temporário; por isso o mês de referência fica alguns meses para trás.",
        "tickers": out,
    }


# ----------------------------------------------------------------------------- Cadastro (quais são fundos de ações)
def cnpjs_fundos_acoes(fonte_cad):
    cnpjs = set()
    novo = fonte_cad("novo")
    if novo:
        zf = zipfile.ZipFile(io.BytesIO(novo))
        for nome in zf.namelist():
            if "classe" not in nome.lower() or "subclasse" in nome.lower():
                continue
            cols = None
            for r in ler_csv(zf, nome):
                if cols is None:
                    k = list(r.keys())
                    cols = {
                        "cnpj": next((c for c in k if "cnpj" in c.lower() and "classe" in c.lower()), None)
                                or next((c for c in k if "cnpj" in c.lower()), None),
                        "classif": next((c for c in k if c.lower() == "classificacao"), None)
                                   or next((c for c in k if "classifica" in c.lower() and "anbima" not in c.lower()), None),
                    }
                    log("cadastro novo:", nome, cols)
                    if not cols["cnpj"] or not cols["classif"]:
                        break
                if (r.get(cols["classif"]) or "").strip().lower().startswith("aç"):
                    cnpjs.add(so_digitos(r.get(cols["cnpj"])))
    legado = fonte_cad("legado")
    if legado:
        texto = io.StringIO(legado.decode("latin-1"))
        for r in csv.DictReader(texto, delimiter=";"):
            if (r.get("CLASSE") or "").strip().lower() in ("fundo de ações", "fundo de acoes") and (r.get("SIT") or "").upper().startswith("EM FUNC"):
                cnpjs.add(so_digitos(r.get("CNPJ_FUNDO")))
    log(f"fundos de ações identificados: {len(cnpjs)}")
    return cnpjs


# ----------------------------------------------------------------------------- Informe diário (captação)
def montar_captacao(fonte_zip, fonte_cad):
    alvo = cnpjs_fundos_acoes(fonte_cad)
    if not alvo:
        return None
    por_dia = defaultdict(lambda: {"in": 0.0, "out": 0.0, "pl": 0.0, "n": 0})
    for ym in list(meses_para_tras(5))[::-1]:
        z = fonte_zip("inf", ym)
        if not z:
            continue
        zf = zipfile.ZipFile(io.BytesIO(z))
        for nome in zf.namelist():
            cols = None
            for r in ler_csv(zf, nome):
                if cols is None:
                    k = r.keys()
                    cols = {"cnpj": col(k, "CNPJ_FUNDO_CLASSE", "CNPJ_FUNDO"), "dt": col(k, "DT_COMPTC"),
                            "cap": col(k, "CAPTC_DIA"), "res": col(k, "RESG_DIA"), "pl": col(k, "VL_PATRIM_LIQ"),
                            "sub": col(k, "ID_SUBCLASSE")}
                if cols["sub"] and (r.get(cols["sub"]) or "").strip():
                    continue  # evita contar subclasse e classe duas vezes
                if so_digitos(r.get(cols["cnpj"])) not in alvo:
                    continue
                d = por_dia[r[cols["dt"]]]
                d["in"] += num(r.get(cols["cap"]))
                d["out"] += num(r.get(cols["res"]))
                d["pl"] += num(r.get(cols["pl"]))
                d["n"] += 1
        log(f"informe diário {ym}: {len(por_dia)} dias acumulados")
    if not por_dia:
        return None
    # descarta dias com cobertura baixa (envio atrasado dos últimos dias)
    mediana_n = sorted(v["n"] for v in por_dia.values())[len(por_dia) // 2]
    dias = sorted(d for d, v in por_dia.items() if v["n"] >= 0.8 * mediana_n)[-DIAS_CAPTACAO:]
    serie = [{"date": d, "inflow": round(por_dia[d]["in"]), "outflow": round(por_dia[d]["out"]),
              "net": round(por_dia[d]["in"] - por_dia[d]["out"]), "aum": round(por_dia[d]["pl"]), "funds": por_dia[d]["n"]}
             for d in dias]
    return {
        "source": "CVM — Informe Diário de Fundos + Cadastro (classificação Ações), licença ODbL",
        "sourceUrl": "https://dados.cvm.gov.br/dataset/fi-doc-inf_diario",
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "series": serie,
    }


# ----------------------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default="data", help="pasta de saída (padrão: data)")
    ap.add_argument("--teste", help="pasta com ZIPs locais (cda_fi_*.zip, inf_diario_fi_*.zip, registro_fundo_classe.zip)")
    a = ap.parse_args()
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)

    if a.teste:
        base = Path(a.teste)
        def fonte_zip(tipo, ym):
            p = base / (f"cda_fi_{ym}.zip" if tipo == "cda" else f"inf_diario_fi_{ym}.zip")
            return p.read_bytes() if p.exists() else None
        def fonte_cad(tipo):
            p = base / ("registro_fundo_classe.zip" if tipo == "novo" else "cad_fi.csv")
            return p.read_bytes() if p.exists() else None
    else:
        def fonte_zip(tipo, ym):
            return baixar((URL_CDA if tipo == "cda" else URL_INF).format(ym=ym))
        def fonte_cad(tipo):
            return baixar(URL_CAD_NOVO if tipo == "novo" else URL_CAD_LEGADO)

    ok = 0
    fa = montar_fundos_acoes(fonte_zip)
    if fa:
        (saida / "fundos-acoes.json").write_text(json.dumps(fa, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        log(f"fundos-acoes.json: {len(fa['tickers'])} ações, referência {fa['ref']}")
        ok += 1
    cap = montar_captacao(fonte_zip, fonte_cad)
    if cap:
        (saida / "captacao-acoes.json").write_text(json.dumps(cap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        log(f"captacao-acoes.json: {len(cap['series'])} dias")
        ok += 1
    if not ok:
        log("nenhum arquivo gerado — mantendo os anteriores")
        sys.exit(1)


if __name__ == "__main__":
    main()
