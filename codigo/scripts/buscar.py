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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from embeddings import load_model, encode  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Busca os chunks mais parecidos com uma consulta.")
    parser.add_argument("consulta", help="texto da consulta")
    parser.add_argument("-k", type=int, default=5, help="quantos resultados mostrar (padrão: 5)")
    parser.add_argument("--cultura", help="filtra por cultura (ex.: soja, milho)")
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--indice", type=Path, default=Path("data/indices/e5-small-fp32"))
    args = parser.parse_args()

    embs = np.load(args.indice / "embeddings.npy")
    ids = json.loads((args.indice / "ids.json").read_text(encoding="utf-8"))
    with open(args.chunks, encoding="utf-8") as f:
        chunks = {c["id"]: c for c in map(json.loads, f)}

    print("Carregando modelo...")
    tokenizer, model = load_model()
    consulta_emb = encode([args.consulta], tokenizer, model, prefix="query: ").numpy()[0]

    # Vetores normalizados: produto escalar = similaridade de cosseno.
    scores = embs @ consulta_emb
    if args.cultura:
        mascara = np.array([chunks[i]["cultura"] == args.cultura for i in ids])
        scores = np.where(mascara, scores, -np.inf)

    melhores = np.argsort(-scores)[:args.k]

    print(f"\nConsulta: {args.consulta}\n")
    for rank, idx in enumerate(melhores, start=1):
        c = chunks[ids[idx]]
        titulo = c["pergunta"] or c["capitulo"]
        num = f"P{c['numero_pergunta']}" if c["numero_pergunta"] else "intro"
        if c.get("total_partes", 1) > 1:
            num += f" (parte {c['parte']}/{c['total_partes']})"
        print(f"{rank}. [{scores[idx]:.4f}] {c['cultura']} {c['ano']} {num} – {titulo}")
        print(f"   {c['resposta'][:200].replace(chr(10), ' ')}...\n")


if __name__ == "__main__":
    main()
