"""Busca densa: ranqueia os chunks pela similaridade com uma consulta.

Uso (a partir da pasta codigo/, depois de rodar o indexar.py):
    python scripts/buscar.py "como controlar a ferrugem na soja"
    python scripts/buscar.py "como controlar a ferrugem na soja" -k 10 --cultura soja
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

# Deixa o Python achar os módulos de src/ (aqui, o embeddings.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from embeddings import load_model, encode  # noqa: E402


def main():
    # 1. Lê as opções da linha de comando (a consulta é obrigatória; o resto tem padrão).
    parser = argparse.ArgumentParser(description="Busca os chunks mais parecidos com uma consulta.")
    parser.add_argument("consulta", help="texto da consulta")
    parser.add_argument("-k", type=int, default=5, help="quantos resultados mostrar (padrão: 5)")
    parser.add_argument("--cultura", help="filtra por cultura (ex.: soja, milho)")
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--indice", type=Path, default=Path("data/indices/e5-small-fp32"))
    args = parser.parse_args()

    # 2. Carrega o índice gerado pelo indexar.py:
    #    embs = matriz (n_chunks x 384), um vetor por chunk;
    #    ids  = id do chunk de cada linha da matriz, na mesma ordem.
    embs = np.load(args.indice / "embeddings.npy")
    ids = json.loads((args.indice / "ids.json").read_text(encoding="utf-8"))
    # 3. Carrega os chunks (o texto) num dicionário id -> chunk, para mostrar os resultados.
    with open(args.chunks, encoding="utf-8") as f:
        chunks = {c["id"]: c for c in map(json.loads, f)}

    # 4. Transforma a consulta num vetor, com o prefixo "query: " que o E5 exige.
    print("Carregando modelo...")
    tokenizer, model = load_model()
    consulta_emb = encode([args.consulta], tokenizer, model, prefix="query: ").numpy()[0]

    # 5. Compara a consulta com todos os chunks de uma vez: uma multiplicação de matriz dá um score
    #    por chunk. Vetores normalizados: produto escalar = similaridade de cosseno.
    scores = embs @ consulta_emb
    # 6. Com --cultura, os chunks de outras culturas recebem score -infinito (nunca aparecem).
    if args.cultura:
        mascara = np.array([chunks[i]["cultura"] == args.cultura for i in ids])
        scores = np.where(mascara, scores, -np.inf)

    # 7. Ordena do maior score para o menor e fica com os k primeiros.
    melhores = np.argsort(-scores)[:args.k]

    # 8. Mostra cada resultado: posição, score, cultura, ano, número da pergunta e começo da resposta.
    print(f"\nConsulta: {args.consulta}\n")
    for rank, idx in enumerate(melhores, start=1):
        c = chunks[ids[idx]]
        titulo = c["pergunta"] or c["capitulo"]
        num = f"P{c['numero_pergunta']}" if c["numero_pergunta"] else "intro"
        # Se o chunk é parte de uma resposta dividida, mostra qual parte é.
        if c.get("total_partes", 1) > 1:
            num += f" (parte {c['parte']}/{c['total_partes']})"
        print(f"{rank}. [{scores[idx]:.4f}] {c['cultura']} {c['ano']} {num} – {titulo}")
        print(f"   {c['resposta'][:200].replace(chr(10), ' ')}...\n")


if __name__ == "__main__":
    main()
