"""Divide os chunks que passam do limite de tokens do modelo de embedding.

Usa a divisão do src/chunking.py (dividir_chunks), aplicada aos chunks extraídos por
`src/chunking.py --sem-divisao`. A saída é o corpus completo (auxiliares/chunks_completo.jsonl); o
chunks.jsonl usado na indexação sai dele por scripts/filtrar_chunks.py.

Uso (a partir de codigo/):
    python scripts/dividir_chunks.py
    python scripts/filtrar_chunks.py

A entrada é data/processed/auxiliares/chunks_sem_divisao.jsonl (gerada por
src/chunking.py --sem-divisao), então o script pode ser rodado de novo (com outro --limite, por
exemplo) sem dividir duas vezes.
"""

import argparse
import json
import sys
from pathlib import Path

# Deixa o Python achar os módulos de src/ (aqui, o chunking.py, onde está a lógica da divisão).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from chunking import PREFIXO, contador_de_tokens, dividir_chunks  # noqa: E402


def main():
    # 1. Opções: arquivos de entrada e saída, modelo cujo tokenizer conta os tokens e o limite.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/auxiliares/chunks_completo.jsonl"),
                        help="saída: corpus completo dividido (o chunks.jsonl sai dele por filtrar_chunks.py)")
    parser.add_argument("--original", type=Path, default=Path("data/processed/auxiliares/chunks_sem_divisao.jsonl"),
                        help="chunks antes da divisão (saída de src/chunking.py --sem-divisao)")
    parser.add_argument("--modelo", default="intfloat/multilingual-e5-small")
    parser.add_argument("--limite", type=int, default=512)
    args = parser.parse_args()

    # 2. Lê os chunks sem divisão (um JSON por linha).
    with open(args.original, encoding="utf-8") as f:
        chunks = [json.loads(linha) for linha in f]

    # 3. n_tokens é uma função que conta os tokens de um texto com o tokenizer do E5.
    n_tokens = contador_de_tokens(args.modelo)
    # 4. Divide os chunks que passam do limite; os outros passam iguais (ver src/chunking.py).
    saida = dividir_chunks(chunks, n_tokens, args.limite)

    # 5. Grava o corpus completo dividido, um JSON por linha.
    with open(args.chunks, "w", encoding="utf-8") as f:
        for s in saida:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # 6. Resumo: quantos chunks foram divididos e o total antes e depois.
    divididos = len({s["id_original"] for s in saida if s["total_partes"] > 1})
    print(f"{divididos} chunks divididos; {len(chunks)} -> {len(saida)} chunks em {args.chunks}")
    # 7. Conferência: nenhuma parte deveria continuar acima do limite.
    maiores = [s["id"] for s in saida if n_tokens(PREFIXO + s["texto"]) > args.limite]
    if maiores:
        print(f"Atenção: {len(maiores)} partes ainda passam de {args.limite} tokens: {maiores[:10]}")


if __name__ == "__main__":
    main()
