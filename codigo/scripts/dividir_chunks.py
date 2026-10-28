"""Divide os chunks do chunks.jsonl que passam do limite de tokens do modelo de embedding.

Usa a mesma divisão do src/chunking.py (dividir_chunks), mas aplicada ao chunks.jsonl final, que já
tem as transcrições das imagens.

Uso (a partir de codigo/):
    python scripts/dividir_chunks.py

Na primeira execução, o chunks.jsonl atual é copiado para
data/processed/auxiliares/chunks_sem_divisao.jsonl. Essa cópia é sempre a entrada, então o script
pode ser rodado de novo (com outro --limite, por exemplo) sem dividir duas vezes.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from chunking import PREFIXO, contador_de_tokens, dividir_chunks  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--original", type=Path, default=Path("data/processed/auxiliares/chunks_sem_divisao.jsonl"),
                        help="cópia dos chunks antes da divisão (criada na primeira execução)")
    parser.add_argument("--modelo", default="intfloat/multilingual-e5-small")
    parser.add_argument("--limite", type=int, default=512)
    args = parser.parse_args()

    if not args.original.exists():
        shutil.copy2(args.chunks, args.original)
        print(f"Cópia dos chunks originais salva em {args.original}")

    with open(args.original, encoding="utf-8") as f:
        chunks = [json.loads(linha) for linha in f]

    n_tokens = contador_de_tokens(args.modelo)
    saida = dividir_chunks(chunks, n_tokens, args.limite)

    with open(args.chunks, "w", encoding="utf-8") as f:
        for s in saida:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    divididos = len({s["id_original"] for s in saida if s["total_partes"] > 1})
    print(f"{divididos} chunks divididos; {len(chunks)} -> {len(saida)} chunks em {args.chunks}")
    maiores = [s["id"] for s in saida if n_tokens(PREFIXO + s["texto"]) > args.limite]
    if maiores:
        print(f"Atenção: {len(maiores)} partes ainda passam de {args.limite} tokens: {maiores[:10]}")


if __name__ == "__main__":
    main()
