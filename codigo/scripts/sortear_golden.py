"""Sorteia as perguntas do conjunto de avaliação (golden set), estratificado pelos 41 livros.

Uso (a partir da pasta codigo/; roda sem o venv, só com a biblioteca padrão):
    python scripts/sortear_golden.py
    python scripts/sortear_golden.py --por-livro 5 --semente 42

Saída: data/golden/amostra.csv, uma linha por pergunta sorteada, com o id_original (o gabarito),
a cultura, o capítulo, a pergunta e a resposta completa (para ajudar a escrever e revisar as
variações da pergunta).

O sorteio é feito por id_original, não por chunk: uma pergunta dividida em várias partes conta uma
vez só. Com a mesma semente e o mesmo chunks.jsonl, a amostra sai sempre igual.
"""
import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


def main():
    # 1. Opções: quantas perguntas por livro e a semente do sorteio (fixa, para reproduzir).
    parser = argparse.ArgumentParser(description="Sorteia perguntas para o conjunto de avaliação.")
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--saida", type=Path, default=Path("data/golden/amostra.csv"))
    parser.add_argument("--por-livro", type=int, default=5, help="perguntas sorteadas por livro (padrão: 5)")
    parser.add_argument("--semente", type=int, default=42, help="semente do sorteio (padrão: 42)")
    args = parser.parse_args()

    # 2. Junta as partes de cada pergunta pelo id_original.
    #    perguntas[id_original] guarda os metadados e a resposta inteira (as partes concatenadas).
    perguntas = {}
    with open(args.chunks, encoding="utf-8") as f:
        for linha in f:
            c = json.loads(linha)
            if c["tipo"] != "pergunta_resposta":
                continue
            p = perguntas.setdefault(c["id_original"], {
                "id_original": c["id_original"], "cultura": c["cultura"], "ano": c["ano"],
                "capitulo": c["capitulo"], "numero_pergunta": c["numero_pergunta"],
                "pergunta": c["pergunta"], "partes": [],
            })
            p["partes"].append((c["parte"], c["resposta"]))

    # 3. Agrupa as perguntas por livro. O livro é cultura + ano, porque a cultura sozinha já
    #    identifica o livro hoje, mas assim o script continua certo se entrar outra edição.
    por_livro = defaultdict(list)
    for p in perguntas.values():
        por_livro[f"{p['cultura']}_{p['ano']}"].append(p["id_original"])

    # 4. Sorteia: um único gerador com semente fixa, percorrendo os livros em ordem alfabética e
    #    as perguntas de cada livro em ordem de id. A ordem fixa é o que torna o sorteio
    #    reproduzível (a ordem de um dict ou de um set poderia mudar).
    rng = random.Random(args.semente)
    sorteados = []
    for livro in sorted(por_livro):
        ids = sorted(por_livro[livro])
        sorteados += rng.sample(ids, min(args.por_livro, len(ids)))

    # 5. Escreve o CSV. A resposta vai inteira (partes em ordem), para a revisão das variações.
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with open(args.saida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id_original", "cultura", "ano", "capitulo", "numero_pergunta", "pergunta", "resposta"])
        for i in sorteados:
            p = perguntas[i]
            resposta = "\n".join(r for _, r in sorted(p["partes"]))
            w.writerow([i, p["cultura"], p["ano"], p["capitulo"], p["numero_pergunta"], p["pergunta"], resposta])
    print(f"{len(sorteados)} perguntas de {len(por_livro)} livros sorteadas (semente {args.semente}) -> {args.saida}")


if __name__ == "__main__":
    main()
