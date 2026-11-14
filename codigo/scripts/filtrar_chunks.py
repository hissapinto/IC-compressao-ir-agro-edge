"""Gera o chunks.jsonl usado na indexação a partir do corpus completo, aplicando o filtro do corpus.

Decisão do orientador: o corpus tem só os pares pergunta-resposta que vêm de texto. Saem as 96
introduções e os pares listados em configs/ids_respostas_com_imagem.txt, cuja resposta depende de
uma imagem (118). Partes de um chunk dividido (mesmo id_original) saem
juntas. Nada é apagado: o corpus completo continua em data/processed/auxiliares/chunks_completo.jsonl.

Uso (a partir de codigo/):
    python scripts/filtrar_chunks.py                                 # só pares de texto (padrão)
    python scripts/filtrar_chunks.py --manter-introducao --sem-lista # corpus completo
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Deixa o Python achar os módulos de src/ (aqui, o chunking.py, onde está a função do filtro).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from chunking import filtrar_chunks  # noqa: E402


def ler_ids(caminho: Path) -> set[str]:
    """Lê a lista de ids a remover: um id por linha; o que vem depois de # é comentário."""
    ids = set()
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        # Tira o comentário e os espaços; linhas que ficam vazias são ignoradas.
        linha = linha.split("#", 1)[0].strip()
        if linha:
            ids.add(linha)
    return ids


def main():
    # 1. Opções: entrada, saída e o que remover (por padrão, introduções + lista de ids).
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entrada", type=Path, default=Path("data/processed/auxiliares/chunks_completo.jsonl"))
    parser.add_argument("--saida", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--manter-introducao", action="store_true", help="não remove os chunks de introdução")
    parser.add_argument("--excluir-ids", type=Path, default=Path("configs/ids_respostas_com_imagem.txt"),
                        help="arquivo com id_original a remover (um por linha)")
    parser.add_argument("--sem-lista", action="store_true", help="não aplica o arquivo de --excluir-ids")
    args = parser.parse_args()

    # 2. Lê o corpus completo (um JSON por linha).
    with open(args.entrada, encoding="utf-8") as f:
        chunks = [json.loads(linha) for linha in f if linha.strip()]

    # 3. Lê a lista de ids a remover e confere que todos existem no corpus (pega erro de digitação).
    ids = set() if args.sem_lista else ler_ids(args.excluir_ids)
    faltando = sorted(ids - {c["id_original"] for c in chunks})
    if faltando:
        raise SystemExit(f"ERRO: ids de --excluir-ids que não existem no corpus: {faltando}")

    # 4. Aplica o filtro (ver filtrar_chunks em src/chunking.py): a decisão é pelo id_original,
    #    então todas as partes de uma resposta dividida saem juntas.
    saida = filtrar_chunks(chunks, args.manter_introducao, ids)

    # 5. Grava o corpus filtrado: é o chunks.jsonl usado na indexação.
    with open(args.saida, "w", encoding="utf-8") as f:
        for c in saida:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 6. Resumo: quantos chunks saíram por cada motivo e quantos ficaram.
    ficam = {c["id_original"] for c in saida}
    removidos = Counter("introducao" if c.get("tipo") == "introducao" else "lista de ids"
                        for c in chunks if c["id_original"] not in ficam)
    print(f"{len(chunks)} chunks em {args.entrada}; removidos: {dict(removidos)}")
    print(f"{len(saida)} chunks ({len(ficam)} perguntas) em {args.saida}")


if __name__ == "__main__":
    main()
