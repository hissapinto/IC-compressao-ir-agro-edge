"""Insere nos chunks as transcrições das imagens (fórmulas, tabelas e figuras), sem IA.

As transcrições foram feitas uma vez, com IA, e ficam guardadas em
data/processed/transcricoes_imagens.csv. Cada linha da tabela diz:
- de qual livro e de qual imagem veio a transcrição (caminho dentro do ePub, ou página e xref no PDF)
  e o SHA-256 dessa imagem;
- em qual chunk ela entra (id_chunk) e em que posição da resposta (posicao, em caracteres, contada
  na resposta sem transcrições); `ancora` é o trecho logo antes dessa posição, para conferência;
- o texto inserido: prefixo + transcricao + sufixo (\\n representa quebra de linha).

Este script lê os chunks sem imagens (saída de `src/chunking.py --sem-divisao`), confere cada âncora,
insere as transcrições e grava o chunks_sem_divisao.jsonl. Depois disso, `scripts/dividir_chunks.py`
gera o chunks.jsonl final.

Uso (a partir de codigo/):
    python3 src/chunking.py --sem-divisao
    python3 scripts/inserir_transcricoes.py
    python3 scripts/dividir_chunks.py

Com --verificar-imagens, o script também abre cada ePub/PDF e confere o SHA-256 de cada imagem
(precisa do pymupdf para os PDFs).
"""

import argparse
import csv
import hashlib
import json
import zipfile
from collections import defaultdict
from pathlib import Path

CODIGO = Path(__file__).resolve().parent.parent
RAW = CODIGO.parent / "500PerguntasRespostas"
AUX = CODIGO / "data" / "processed" / "auxiliares"


def desescapar(s: str) -> str:
    return s.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


def ler_tabela(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for l in linhas:
        l["posicao"] = int(l["posicao"])
        l["ordem"] = int(l["ordem"])
        l["texto_inserido"] = desescapar(l["prefixo"]) + l["transcricao"] + desescapar(l["sufixo"])
    return linhas


def inserir(chunks: list[dict], tabela: list[dict]) -> int:
    por_chunk = defaultdict(list)
    for l in tabela:
        por_chunk[l["id_chunk"]].append(l)
    ids = {c["id"] for c in chunks}
    faltando = sorted(set(por_chunk) - ids)
    if faltando:
        raise SystemExit(f"ERRO: chunks da tabela que não existem: {faltando}")
    alterados = 0
    for c in chunks:
        linhas = por_chunk.get(c["id"])
        if not linhas:
            continue
        original = c["resposta"]
        for l in linhas:
            ancora = original[max(0, l["posicao"] - 60):l["posicao"]].replace("\n", " ")
            if ancora != l["ancora"]:
                raise SystemExit(f"ERRO: a âncora de {c['id']} (posição {l['posicao']}) não bate. "
                                 f"Esperado {l['ancora']!r}, encontrado {ancora!r}. O texto da resposta mudou?")
        # insere de trás para frente, para as posições continuarem valendo
        nova = original
        for l in sorted(linhas, key=lambda l: (l["posicao"], l["ordem"]), reverse=True):
            nova = nova[:l["posicao"]] + l["texto_inserido"] + nova[l["posicao"]:]
        c["texto"] = c["texto"].replace("Resposta: " + original, "Resposta: " + nova)
        c["resposta"] = nova
        c["conteudo_imagem"] = True
        alterados += 1
    return alterados


def verificar_imagens(tabela: list[dict]) -> int:
    erros = 0
    abertos = {}
    for l in tabela:
        fonte = RAW / l["fonte"]
        if fonte.suffix == ".epub":
            if fonte not in abertos:
                abertos[fonte] = zipfile.ZipFile(fonte)
            h = hashlib.sha256(abertos[fonte].read(l["imagem"])).hexdigest()
        else:
            import pymupdf
            if fonte not in abertos:
                abertos[fonte] = pymupdf.open(fonte)
            xrefs = l["imagem"].split("xref ")[1].split("+")
            hs = [hashlib.sha256(abertos[fonte].extract_image(int(x))["image"]).hexdigest() for x in xrefs]
            h = hs[0] if len(hs) == 1 else hashlib.sha256("".join(hs).encode()).hexdigest()
        if h != l["sha256_imagem"]:
            erros += 1
            print(f"  hash diferente: {l['livro']} {l['imagem']}")
    return erros


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tabela", type=Path, default=CODIGO / "data" / "processed" / "transcricoes_imagens.csv")
    parser.add_argument("--entrada", type=Path, default=AUX / "chunks_sem_imagens.jsonl")
    parser.add_argument("--saida", type=Path, default=AUX / "chunks_sem_divisao.jsonl")
    parser.add_argument("--verificar-imagens", action="store_true")
    args = parser.parse_args()

    tabela = ler_tabela(args.tabela)
    if args.verificar_imagens:
        erros = verificar_imagens(tabela)
        print(f"imagens conferidas: {len(tabela) - erros} de {len(tabela)} com o hash certo")
        if erros:
            raise SystemExit(1)

    with open(args.entrada, encoding="utf-8") as f:
        chunks = [json.loads(linha) for linha in f]
    n = inserir(chunks, tabela)
    with open(args.saida, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(tabela)} transcrições inseridas em {n} chunks; {len(chunks)} chunks em {args.saida}")


if __name__ == "__main__":
    main()
