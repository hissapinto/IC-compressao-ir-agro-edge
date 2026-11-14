"""Gera os embeddings de todos os chunks e salva o índice (roda uma vez, no Mac).

Uso (a partir da pasta codigo/):
    python scripts/indexar.py
    python scripts/indexar.py --chunks data/processed/chunks.jsonl --saida data/indices/e5-small-fp32

Saída em data/indices/e5-small-fp32/:
    embeddings.npy  matriz (n_chunks, 384) em float32, já normalizada (L2)
    ids.json        id de cada linha da matriz, na mesma ordem
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

# Deixa o Python achar os módulos de src/ (aqui, o embeddings.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from embeddings import load_model, encode  # noqa: E402


def ler_chunks(caminho: Path) -> list[dict]:
    """Lê o .jsonl (um chunk em JSON por linha), pulando linhas vazias."""
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def main():
    # 1. Opções: de onde ler os chunks, onde salvar o índice e quantos textos por lote.
    parser = argparse.ArgumentParser(description="Gera o índice de embeddings dos chunks (multilingual-e5-small).")
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"), help="arquivo .jsonl com os chunks")
    parser.add_argument("--saida", type=Path, default=Path("data/indices/e5-small-fp32"), help="pasta onde salvar o índice")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    # 2. Lê os chunks e separa o campo "texto" de cada um, que é o que vira vetor
    #    (cultura | capítulo, pergunta e resposta).
    chunks = ler_chunks(args.chunks)
    textos = [c["texto"] for c in chunks]
    print(f"{len(chunks)} chunks lidos de {args.chunks}")

    # 3. Carrega o tokenizer e o modelo E5.
    print("Carregando modelo...")
    tokenizer, model = load_model()

    # 4. Conferência de tamanho.
    # O E5 aceita no máximo 512 tokens (contando o prefixo); o que passar disso é cortado sem aviso.
    n_tokens = [len(tokenizer("passage: " + t)["input_ids"]) for t in textos]
    longos = [c["id"] for c, n in zip(chunks, n_tokens) if n > 512]
    if longos:
        print(f"Atenção: {len(longos)} chunks passam de 512 tokens e serão truncados. Exemplos: {longos[:5]}")

    # 5. Gera os vetores.
    # Ordenar por tamanho deixa os batches com menos padding (bem mais rápido).
    # "ordem" guarda as posições originais, do texto mais curto ao mais longo.
    ordem = sorted(range(len(textos)), key=lambda i: n_tokens[i])
    inicio = time.time()
    embs_ordenados = encode([textos[i] for i in ordem], tokenizer, model,
                            prefix="passage: ", batch_size=args.batch_size)
    print(f"Embeddings gerados em {time.time() - inicio:.0f} s")

    # 6. Volta para a ordem original do arquivo.
    # embs[ordem] = ... põe cada vetor de volta na posição do seu chunk no chunks.jsonl.
    embs = np.empty((len(textos), embs_ordenados.shape[1]), dtype=np.float32)
    embs[ordem] = embs_ordenados.numpy().astype(np.float32)

    # 7. Salva o índice: a matriz de vetores e, na mesma ordem, o id do chunk de cada linha.
    #    É assim que a busca sabe que a linha i da matriz é o chunk ids[i].
    args.saida.mkdir(parents=True, exist_ok=True)
    np.save(args.saida / "embeddings.npy", embs)
    (args.saida / "ids.json").write_text(json.dumps([c["id"] for c in chunks]), encoding="utf-8")
    print(f"Índice salvo em {args.saida}/ ({embs.shape[0]} x {embs.shape[1]})")


if __name__ == "__main__":
    main()
