"""Avalia a busca densa com o conjunto de avaliação de data/golden/ (pares.csv e fora_do_escopo.csv).

Uso (a partir da pasta codigo/, com o venv ativo e depois de rodar o indexar.py):
    python scripts/avaliar.py
    python scripts/avaliar.py --so-aprovadas
    python scripts/avaliar.py --indice data/indices/e5-small-fp32 --saida results/e5-small-fp32

O que mede:
  - Consultas dentro do escopo (original, reescrita, vaga): MRR@10, Recall@1/5/10 e acerto do
    livro no 1º lugar, sobre o índice INTEIRO. Conta acerto se qualquer parte com o mesmo
    id_original do gabarito aparecer; o ranking é deduplicado por id_original.
    Cada pergunta tem até 3 reescritas e 3 vagas: primeiro tira-se a média das versões de cada
    pergunta, depois a média entre perguntas. Também sai o pior caso (worst-case, medida de
    robustez): para cada pergunta, o valor da versão em que a busca foi pior.
  - Todas as consultas: score do 1º colocado e diferença entre o 1º e o 2º (mediana e IQR).
  - Separação dentro x fora do escopo: AUROC do score do 1º e da diferença 1º-2º, curva ROC e
    tabela de limiares (válidas recusadas x fora do escopo aceitas), base da detecção de fora do escopo (abstenção por limiar).
  - Anisotropia: cosseno médio entre chunks sorteados e entre a consulta e o corpus inteiro.

Saída em results/<variante>/ (a variante é o nome da pasta do índice):
  resumo.md         tabelas principais, para ler direto
  metricas.json     todos os números (para comparar variantes depois)
  por_consulta.csv  uma linha por consulta: posição do acerto, scores, 1º colocado
  por_livro.csv     MRR@10 e Recall@10 por livro e conjunto
  limiares_top1.csv e limiares_gap.csv   taxas de recusa e aceitação para cada limiar

Os gráficos e a explicação de cada métrica ficam no notebook notebooks/avaliacao_busca.ipynb, que
lê estes arquivos.
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

# Deixa o Python achar os módulos de src/ (embeddings.py e avaliacao.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from embeddings import load_model, encode  # noqa: E402
from avaliacao import (  # noqa: E402
    codificar_grupos, melhor_score_por_pergunta, posicao_do_gabarito, top_n,
    reciprocal_rank, acerto_ate, agregar_por_pergunta, intervalo_bootstrap, auroc, matriz_confusao,
    mediana_iqr,
)

# Os cinco conjuntos de consultas, na ordem em que aparecem nas tabelas e gráficos.
DENTRO = ["original", "reescrita", "vaga"]          # têm gabarito (id_original)
FORA = ["fora_geral", "fora_agro"]                  # não têm resposta nos 41 livros
CONJUNTOS = DENTRO + FORA
NOMES = {
    "original": "Originais", "reescrita": "Reescritas", "vaga": "Vagas",
    "fora_geral": "Fora: outro assunto", "fora_agro": "Fora: agro sem livro",
    "reescrita+vaga": "Reescritas + vagas",
}
# O "uso real" é quem não copia a pergunta do livro: reescritas + vagas.
REAIS = ["reescrita", "vaga"]
# Quantas versões de reescrita e de vaga cada pergunta pode ter no pares.csv.
N_VERSOES = 3


def ler_csv(caminho: Path) -> list[dict]:
    """Lê um CSV como lista de dicionários."""
    # utf-8-sig: aceita o arquivo com ou sem o BOM que o Excel/Numbers colocam no início.
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ler_consultas(pasta: Path, so_aprovadas: bool) -> list[dict]:
    """Monta a lista de consultas (uma por linha) a partir dos dois arquivos do golden set.

    pares.csv: uma linha por pergunta sorteada, com a pergunta_original e as versões lado a lado
        (reescrita_1 a reescrita_3, vaga_1 a vaga_3), cada uma com o seu status. Todas têm o MESMO
        gabarito: o id_original da linha. (Um pares.csv antigo, com só as colunas reescrita e vaga,
        também funciona: elas viram a versão 1.)
    fora_do_escopo.csv: uma linha por consulta sem resposta nos livros (tipo fora_geral ou fora_agro).

    A pergunta original não passa por revisão (é o texto do livro). Reescritas, vagas e consultas
    fora do escopo têm status: rascunho, aprovada ou rejeitada. Rejeitadas nunca entram; com
    --so-aprovadas, os rascunhos também ficam de fora.
    """
    aceitos = ("aprovada",) if so_aprovadas else ("aprovada", "rascunho")
    consultas = []
    for p in ler_csv(pasta / "pares.csv"):
        # Versão 0 = a pergunta original; versões 1 a 3 = as variações escritas para a avaliação.
        versoes = [("original", 0, p["pergunta_original"], "original")]
        for conjunto in REAIS:
            for v in range(1, N_VERSOES + 1):
                if f"{conjunto}_{v}" in p:                         # formato atual (3 versões)
                    texto, status = p[f"{conjunto}_{v}"], p[f"status_{conjunto}_{v}"]
                elif v == 1 and conjunto in p:                     # formato antigo (1 versão)
                    texto, status = p[conjunto], p[f"status_{conjunto}"]
                else:
                    continue
                if (texto or "").strip():                          # célula vazia = versão inexistente
                    versoes.append((conjunto, v, texto, status))
        for conjunto, v, texto, status in versoes:
            status = status.strip().lower()
            if conjunto == "original" or status in aceitos:
                sufixo = conjunto if conjunto == "original" else f"{conjunto}{v}"
                consultas.append({"id_consulta": f"{p['id_original']}:{sufixo}", "conjunto": conjunto,
                                  "versao": v, "id_original": p["id_original"], "cultura": p["cultura"],
                                  "consulta": texto.strip(), "status": status})
    for r in ler_csv(pasta / "fora_do_escopo.csv"):
        status = r["status"].strip().lower()
        if status in aceitos:
            consultas.append({"id_consulta": r["id_consulta"], "conjunto": r["tipo"], "versao": "", "id_original": "",
                              "cultura": "", "consulta": r["consulta"].strip(), "status": status})
    return consultas


def main():
    # 1. Opções da linha de comando.
    parser = argparse.ArgumentParser(description="Avalia a busca densa (MRR, Recall, AUROC, gráficos).")
    parser.add_argument("--golden", type=Path, default=Path("data/golden"), help="pasta com pares.csv e fora_do_escopo.csv")
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--indice", type=Path, default=Path("data/indices/e5-small-fp32"))
    parser.add_argument("--saida", type=Path, default=None, help="padrão: results/<nome da pasta do índice>")
    parser.add_argument("-k", type=int, default=10, help="corte do MRR e do Recall (padrão: 10)")
    parser.add_argument("--so-aprovadas", action="store_true", help="usa só as consultas com status aprovada (e as originais)")
    parser.add_argument("--semente", type=int, default=42, help="semente do bootstrap e dos sorteios")
    parser.add_argument("--bootstrap", type=int, default=1000, help="reamostras do intervalo de confiança")
    args = parser.parse_args()
    saida = args.saida or Path("results") / args.indice.name
    saida.mkdir(parents=True, exist_ok=True)
    k = args.k

    # 2. Carrega o índice (matriz de vetores + ids na mesma ordem) e os chunks.
    embs = np.load(args.indice / "embeddings.npy")
    ids = json.loads((args.indice / "ids.json").read_text(encoding="utf-8"))
    with open(args.chunks, encoding="utf-8") as f:
        chunks = {c["id"]: c for c in map(json.loads, f)}
    # O índice precisa ser do chunks.jsonl atual; se não for, os resultados não valem nada.
    if set(ids) != set(chunks) or len(ids) != embs.shape[0]:
        sys.exit("O índice não corresponde ao chunks.jsonl. Rode scripts/indexar.py de novo.")

    # 3. Cada linha do índice ganha o número da sua pergunta (grupo), para deduplicar as partes.
    grupo_do_chunk, nomes_grupo = codificar_grupos([chunks[i]["id_original"] for i in ids])
    numero_grupo = {nome: g for g, nome in enumerate(nomes_grupo)}
    n_grupos = len(nomes_grupo)
    # Cultura e pergunta de cada grupo (de qualquer parte: são iguais entre as partes).
    info_grupo = {}
    for i in ids:
        c = chunks[i]
        info_grupo.setdefault(numero_grupo[c["id_original"]], (c["cultura"], c["pergunta"]))
    print(f"Índice: {embs.shape[0]} chunks, {n_grupos} perguntas distintas")

    # 4. Lê as consultas e confere que todo gabarito existe no corpus.
    consultas = ler_consultas(args.golden, args.so_aprovadas)
    for r in consultas:
        if r["conjunto"] in DENTRO and r["id_original"] not in numero_grupo:
            sys.exit(f"Gabarito {r['id_original']} (consulta {r['id_consulta']}) não está no corpus.")
    print(f"{len(consultas)} consultas: " + ", ".join(
        f"{c} {sum(r['conjunto'] == c for r in consultas)}" for c in CONJUNTOS))

    # 5. Codifica as consultas com o prefixo "query: " (o mesmo pipeline do buscar.py).
    print("Carregando modelo...")
    tokenizer, model = load_model()
    inicio = time.time()
    q_embs = encode([r["consulta"] for r in consultas], tokenizer, model, prefix="query: ").numpy()
    print(f"Consultas codificadas em {time.time() - inicio:.1f} s")

    # 6. Scores de todas as consultas contra todos os chunks: uma multiplicação de matrizes.
    #    Vetores normalizados -> produto escalar = cosseno. Forma: (n_consultas, n_chunks).
    scores = q_embs @ embs.T

    # 7. Para cada consulta: ranking deduplicado, posição do acerto, 1º e 2º colocados.
    resultados = []
    for r, s in zip(consultas, scores):
        melhor = melhor_score_por_pergunta(s, grupo_do_chunk, n_grupos)
        grupos_top, scores_top = top_n(melhor, k)
        g1 = int(grupos_top[0])
        linha = {
            "id_consulta": r["id_consulta"], "conjunto": r["conjunto"], "versao": r["versao"], "status": r["status"],
            "consulta": r["consulta"], "id_original": r["id_original"], "cultura": r["cultura"],
            "score_top1": float(scores_top[0]), "score_top2": float(scores_top[1]),
            # Diferença entre o 1º e o 2º colocados (perguntas distintas, já deduplicadas).
            "gap_top1_top2": float(scores_top[0] - scores_top[1]),
            # Média dos scores contra o corpus inteiro: mostra o "piso" do E5 (anisotropia).
            "score_medio_corpus": float(s.mean()),
            "top1_id_original": nomes_grupo[g1], "top1_cultura": info_grupo[g1][0],
            "top1_pergunta": info_grupo[g1][1],
            "posicao": "", "rr": "", "livro_certo_top1": "",
        }
        if r["conjunto"] in DENTRO:
            g = numero_grupo[r["id_original"]]
            pos = posicao_do_gabarito(melhor, g)
            linha["posicao"] = pos
            linha["rr"] = float(reciprocal_rank([pos], k)[0])
            linha["score_gabarito"] = float(melhor[g])
            linha["livro_certo_top1"] = int(info_grupo[g1][0] == r["cultura"])
        resultados.append(linha)

    def do_conjunto(nomes_conj):
        """Resultados das consultas dos conjuntos pedidos."""
        return [x for x in resultados if x["conjunto"] in nomes_conj]

    def coluna(linhas, campo):
        return np.array([x[campo] for x in linhas], dtype=np.float64)

    # 8. Métricas de ranking por conjunto (com intervalo de confiança por bootstrap).
    #    Cada métrica é calculada por consulta e depois agregada por pergunta (id_original):
    #      - média: média das versões da pergunta, depois média entre as perguntas;
    #      - pior:  a versão com o pior valor em cada pergunta, depois média entre as perguntas.
    #    O bootstrap sorteia PERGUNTAS (com a média das suas versões), não consultas soltas.
    metricas = {"variante": args.indice.name, "k": k, "n_chunks": int(embs.shape[0]),
                "n_perguntas": n_grupos, "so_aprovadas": args.so_aprovadas, "ranking": {},
                "robustez": {}, "por_versao": {}, "scores": {}, "separacao": {}, "anisotropia": {}}
    grupos_dentro = {c: [c] for c in DENTRO} | {"reescrita+vaga": REAIS}

    def valores_ranking(linhas):
        """Métrica de cada consulta (1 valor por consulta) para as métricas de ranking."""
        pos = coluna(linhas, "posicao")
        return {f"mrr@{k}": reciprocal_rank(pos, k), "recall@1": acerto_ate(pos, 1),
                "recall@5": acerto_ate(pos, 5), f"recall@{k}": acerto_ate(pos, k),
                "livro_certo@1": coluna(linhas, "livro_certo_top1")}

    for nome, conj in grupos_dentro.items():
        linhas = do_conjunto(conj)
        if not linhas:
            continue
        perguntas = [x["id_original"] for x in linhas]
        m = {"n": len(set(perguntas)), "n_consultas": len(linhas)}
        robusto = {}
        for nome_m, v in valores_ranking(linhas).items():
            medias, piores, _ = agregar_por_pergunta(v, perguntas)
            lo, hi = intervalo_bootstrap(medias, args.bootstrap, args.semente)
            m[nome_m] = {"valor": float(medias.mean()), "ic95": [lo, hi]}
            lo, hi = intervalo_bootstrap(piores, args.bootstrap, args.semente)
            robusto[nome_m] = {"valor": float(piores.mean()), "ic95": [lo, hi]}
        m["posicao_mediana"] = float(np.median(coluna(linhas, "posicao")))
        metricas["ranking"][nome] = m
        if nome != "original":   # a original tem uma versão só: a pior é ela mesma
            metricas["robustez"][nome] = robusto

    # 8a. Média de cada versão (1, 2, 3) separada. No golden set atual, a versão 1 é a revisada
    #     pela Isabela (ou no estilo dela), a 2 usa o termo do livro e a 3 só descreve, sem o
    #     termo; a diferença entre elas mostra o quanto a busca depende das palavras do livro.
    for c in REAIS:
        for v in range(1, N_VERSOES + 1):
            linhas = [x for x in do_conjunto([c]) if x["versao"] == v]
            if linhas:
                metricas["por_versao"][f"{c}_{v}"] = {"n": len(linhas)} | {
                    nome_m: float(val.mean()) for nome_m, val in valores_ranking(linhas).items()}

    # 8b. Análise pareada: todos os tipos de uma pergunta miram a mesma resposta, então dá para
    #     ver, pergunta a pergunta, em quais tipos (original, reescrita, vaga) a resposta certa
    #     ficou no top-k. Um tipo com várias versões conta como acerto quando a MAIORIA delas
    #     (2 de 3) acerta. Ex.: "original, reescrita" = acertou na original e na maioria das
    #     reescritas, mas não na maioria das vagas.
    acertos_por_tipo = {}
    for x in do_conjunto(DENTRO):
        acertos_por_tipo.setdefault(x["id_original"], {}).setdefault(x["conjunto"], []).append(x["posicao"] <= k)
    combinacoes = {}
    for por_tipo in acertos_por_tipo.values():
        if len(por_tipo) == len(DENTRO):  # só perguntas com os três tipos avaliados
            acertos = [c for c in DENTRO if np.mean(por_tipo[c]) > 0.5]
            chave = ", ".join(acertos) if acertos else "nenhuma"
            combinacoes[chave] = combinacoes.get(chave, 0) + 1
    metricas["pareado"] = {"criterio": f"acerto no top-{k} (na maioria das versões)",
                           "n_perguntas": sum(combinacoes.values()),
                           "combinacoes": dict(sorted(combinacoes.items(), key=lambda kv: -kv[1]))}

    # 9. Score do 1º colocado e diferença 1º-2º: mediana e IQR por conjunto.
    for c in CONJUNTOS:
        linhas = do_conjunto([c])
        if linhas:
            metricas["scores"][c] = {"n": len(linhas),
                                     "score_top1": mediana_iqr(coluna(linhas, "score_top1")),
                                     "gap_top1_top2": mediana_iqr(coluna(linhas, "gap_top1_top2")),
                                     "score_medio_corpus": mediana_iqr(coluna(linhas, "score_medio_corpus"))}

    # 10. Separação dentro x fora do escopo: AUROC de cada conjunto válido contra os de fora.
    #     Positivo = dentro do escopo (deveria ser respondida); negativo = fora (deveria ser recusada).
    fora_todos = do_conjunto(FORA)
    comparacoes = {}
    for nome_pos, conj_pos in grupos_dentro.items():
        for nome_neg, conj_neg in {"fora": FORA, "fora_geral": ["fora_geral"], "fora_agro": ["fora_agro"]}.items():
            pos_l, neg_l = do_conjunto(conj_pos), do_conjunto(conj_neg)
            if pos_l and neg_l:
                comparacoes[f"{nome_pos} x {nome_neg}"] = {
                    campo: auroc(coluna(pos_l, campo), coluna(neg_l, campo))
                    for campo in ("score_top1", "gap_top1_top2")}
    metricas["separacao"]["auroc"] = comparacoes
    # O score do 1º também serve para prever, entre as válidas, se o 1º colocado está certo:
    # se essa AUROC for alta, um limiar baixo recusaria mais respostas erradas do que certas.
    reais = do_conjunto(REAIS)
    if reais:
        certo = coluna(reais, "posicao") == 1
        if certo.any() and (~certo).any():
            sc = coluna(reais, "score_top1")
            metricas["separacao"]["auroc_acerto_top1_entre_validas"] = auroc(sc[certo], sc[~certo])

    # 11. Tabela de limiares: para cada limiar t, "aceita se valor >= t".
    #     Válidas recusadas = valor < t (erro: deixou de responder o que sabia).
    #     Fora aceitas      = valor >= t (erro: respondeu o que não está nos livros).
    def tabela_limiares(campo, passo):
        todos = coluna(resultados, campo)
        grade = np.round(np.arange(np.floor(todos.min() / passo) * passo,
                                   todos.max() + passo, passo), 4)
        tabela = []
        for t in grade:
            linha = {"limiar": float(t)}
            for c in DENTRO + ["reescrita+vaga"]:
                v = coluna(do_conjunto(grupos_dentro[c]), campo)
                if len(v):
                    linha[f"recusadas_{c}"] = float((v < t).mean())
            for c, conj in {"fora_geral": ["fora_geral"], "fora_agro": ["fora_agro"], "fora": FORA}.items():
                v = coluna(do_conjunto(conj), campo)
                if len(v):
                    linha[f"aceitas_{c}"] = float((v >= t).mean())
            tabela.append(linha)
        with open(saida / f"limiares_{campo.split('_')[0] if campo == 'gap_top1_top2' else 'top1'}.csv",
                  "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(tabela[0]))
            w.writeheader()
            w.writerows(tabela)
        return tabela

    lim_top1 = tabela_limiares("score_top1", 0.005)
    lim_gap = tabela_limiares("gap_top1_top2", 0.002)

    def pontos_de_operacao(tabela, campo):
        """Limiares de referência: o menor que aceita no máximo 5% / 10% das consultas de fora,
        e o maior que recusa no máximo 5% / 10% das válidas (reescritas + vagas).
        Cada ponto também leva a matriz de confusão e precision, recall e accuracy nesse limiar."""
        pontos = {}
        if not fora_todos or not reais:
            return pontos
        val, neg = coluna(reais, campo), coluna(fora_todos, campo)
        for alvo in (0.05, 0.10):
            ok = [x for x in tabela if x["aceitas_fora"] <= alvo]
            if ok:
                x = ok[0]
                pontos[f"fora_aceitas<={alvo:.0%}"] = {"limiar": x["limiar"], "recusadas_reescrita+vaga": x["recusadas_reescrita+vaga"], "aceitas_fora": x["aceitas_fora"]}
            ok = [x for x in tabela if x["recusadas_reescrita+vaga"] <= alvo]
            if ok:
                x = ok[-1]
                pontos[f"validas_recusadas<={alvo:.0%}"] = {"limiar": x["limiar"], "recusadas_reescrita+vaga": x["recusadas_reescrita+vaga"], "aceitas_fora": x["aceitas_fora"]}
        for p in pontos.values():
            p["matriz"] = matriz_confusao(val, neg, p["limiar"])
        return pontos

    metricas["separacao"]["pontos_top1"] = pontos_de_operacao(lim_top1, "score_top1")
    metricas["separacao"]["pontos_gap"] = pontos_de_operacao(lim_gap, "gap_top1_top2")

    # 12. Anisotropia: se os vetores ocupam um "cone" estreito, até textos sem relação têm
    #     cosseno alto. Medimos o cosseno médio entre 5.000 pares de chunks sorteados e o
    #     tamanho do vetor médio do corpus (0 = vetores espalhados; perto de 1 = todos parecidos).
    rng = np.random.default_rng(args.semente)
    a, b = rng.integers(0, len(embs), 5000), rng.integers(0, len(embs), 5000)
    cos_pares = np.einsum("ij,ij->i", embs[a], embs[b])
    metricas["anisotropia"] = {
        "cosseno_medio_entre_chunks": float(cos_pares.mean()),
        "cosseno_entre_chunks": mediana_iqr(cos_pares),
        "norma_do_vetor_medio": float(np.linalg.norm(embs.mean(axis=0))),
    }

    # 13. Desempenho por livro (cultura), para os conjuntos válidos.
    por_livro = []
    for cultura in sorted({x["cultura"] for x in do_conjunto(DENTRO)}):
        linha = {"cultura": cultura}
        for c in DENTRO:
            pos = coluna([x for x in do_conjunto([c]) if x["cultura"] == cultura], "posicao")
            if len(pos):
                linha[f"mrr@{k}_{c}"] = round(float(reciprocal_rank(pos, k).mean()), 4)
                linha[f"recall@{k}_{c}"] = round(float(acerto_ate(pos, k).mean()), 4)
                linha[f"n_{c}"] = len(pos)
        por_livro.append(linha)

    # 14. Grava os arquivos de resultado.
    campos = ["id_consulta", "conjunto", "versao", "status", "consulta", "id_original", "cultura", "posicao", "rr",
              "livro_certo_top1", "score_gabarito", "score_top1", "score_top2", "gap_top1_top2",
              "score_medio_corpus", "top1_id_original", "top1_cultura", "top1_pergunta"]
    with open(saida / "por_consulta.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for x in resultados:
            w.writerow({c: (round(v, 4) if isinstance(v, float) else v) for c, v in x.items()})
    with open(saida / "por_livro.csv", "w", encoding="utf-8", newline="") as f:
        campos_livro = list(dict.fromkeys(c for linha in por_livro for c in linha))
        w = csv.DictWriter(f, fieldnames=campos_livro)
        w.writeheader()
        w.writerows(por_livro)
    (saida / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")

    # 15. Resumo em Markdown (os gráficos ficam no notebook notebooks/avaliacao_busca.ipynb).
    escrever_resumo(metricas, saida / "resumo.md")
    print(f"\nResultados em {saida}/")
    print((saida / "resumo.md").read_text(encoding="utf-8"))


# =============================================================================================
# Resumo em Markdown
# =============================================================================================

def escrever_resumo(m: dict, caminho: Path):
    """Escreve o resumo.md com as tabelas principais."""
    k = m["k"]
    f2 = lambda v: f"{v:.3f}"  # noqa: E731
    lin = [f"# Avaliação da busca: {m['variante']}", "",
           f"Índice com {m['n_chunks']} chunks ({m['n_perguntas']} perguntas). Ranking sobre o índice inteiro, "
           f"deduplicado por id_original. {'Só consultas aprovadas.' if m['so_aprovadas'] else 'Inclui consultas em rascunho.'}",
           "", "## Ranking (consultas dentro do escopo)", "",
           f"| Conjunto | Perguntas | Consultas | MRR@{k} | Recall@1 | Recall@5 | Recall@{k} | Livro certo no 1º | Posição mediana |",
           "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    celula = lambda r, chave: f"{r[chave]['valor']:.3f} ({r[chave]['ic95'][0]:.2f}–{r[chave]['ic95'][1]:.2f})"  # noqa: E731
    for nome, r in m["ranking"].items():
        lin.append(f"| {NOMES.get(nome, nome)} | {r['n']} | {r.get('n_consultas', r['n'])} | {celula(r, f'mrr@{k}')} | "
                   f"{celula(r, 'recall@1')} | {celula(r, 'recall@5')} | {celula(r, f'recall@{k}')} | "
                   f"{celula(r, 'livro_certo@1')} | {r['posicao_mediana']:.0f} |")
    lin += ["", "Média das versões de cada pergunta, depois média entre as perguntas. Entre parênteses, o "
                "intervalo de confiança de 95% (bootstrap sobre as perguntas).", ""]
    if m.get("robustez"):
        lin += ["Robustez, pior caso (worst-case): em cada pergunta, o valor da versão em que a busca foi pior; média entre as perguntas:",
                "", f"| Conjunto | MRR@{k} | Recall@1 | Recall@5 | Recall@{k} | Livro certo no 1º |",
                "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for nome, r in m["robustez"].items():
            lin.append(f"| {NOMES.get(nome, nome)} | {celula(r, f'mrr@{k}')} | {celula(r, 'recall@1')} | "
                       f"{celula(r, 'recall@5')} | {celula(r, f'recall@{k}')} | {celula(r, 'livro_certo@1')} |")
        lin.append("")
    if m.get("por_versao"):
        lin += ["Cada versão separada (referência para a revisão):", "",
                f"| Versão | Consultas | MRR@{k} | Recall@{k} |", "| --- | ---: | ---: | ---: |"]
        for nome, r in m["por_versao"].items():
            lin.append(f"| {nome} | {r['n']} | {r[f'mrr@{k}']:.3f} | {r[f'recall@{k}']:.3f} |")
        lin.append("")
    par = m.get("pareado", {})
    if par.get("n_perguntas"):
        lin += [f"Análise pareada ({par['n_perguntas']} perguntas com os três tipos; em quais tipos houve "
                f"{par['criterio']}):", "", "| Tipos que acertaram | Perguntas | % |", "| --- | ---: | ---: |"]
        for comb, n in par["combinacoes"].items():
            lin.append(f"| {comb} | {n} | {n / par['n_perguntas']:.1%} |")
        lin.append("")
    lin += [
            "## Scores (todas as consultas)", "",
            "| Conjunto | n | Score do 1º: mediana (IQR) | Diferença 1º−2º: mediana (IQR) | Média contra o corpus: mediana |",
            "| --- | ---: | ---: | ---: | ---: |"]
    for c, s in m["scores"].items():
        lin.append(f"| {NOMES[c]} | {s['n']} | {f2(s['score_top1']['mediana'])} ({f2(s['score_top1']['iqr'])}) | "
                   f"{f2(s['gap_top1_top2']['mediana'])} ({f2(s['gap_top1_top2']['iqr'])}) | "
                   f"{f2(s['score_medio_corpus']['mediana'])} |")
    a = m["anisotropia"]
    lin += ["", f"Anisotropia: cosseno médio entre dois chunks sorteados = {a['cosseno_medio_entre_chunks']:.3f}; "
                f"norma do vetor médio do corpus = {a['norma_do_vetor_medio']:.3f} (0 = vetores espalhados, 1 = todos iguais).",
            "", "## Separação dentro × fora do escopo (AUROC)", "",
            "| Válidas × fora | Score do 1º | Diferença 1º−2º |", "| --- | ---: | ---: |"]
    for nome, v in m["separacao"].get("auroc", {}).items():
        lin.append(f"| {nome} | {v['score_top1']:.3f} | {v['gap_top1_top2']:.3f} |")
    if "auroc_acerto_top1_entre_validas" in m["separacao"]:
        lin += ["", "AUROC do score do 1º para separar, entre reescritas e vagas, quem acertou o 1º de quem errou: "
                    f"{m['separacao']['auroc_acerto_top1_entre_validas']:.3f}."]
    for chave, titulo in [("pontos_top1", "score do 1º"), ("pontos_gap", "diferença 1º−2º")]:
        pts = m["separacao"].get(chave, {})
        if pts:
            lin += ["", f"Pontos de operação ({titulo}; válidas = reescritas + vagas):", "",
                    "| Critério | Limiar | Válidas recusadas | Fora aceitas | VP | FN | FP | VN | Precision | Recall | Accuracy |",
                    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
            for crit, p in pts.items():
                mc = p.get("matriz")
                extra = (f" {mc['vp']} | {mc['fn']} | {mc['fp']} | {mc['vn']} | {mc['precision']:.3f} | "
                         f"{mc['recall']:.3f} | {mc['accuracy']:.3f} |") if mc else " | | | | | | |"
                lin.append(f"| {crit} | {p['limiar']:.3f} | {p['recusadas_reescrita+vaga']:.1%} | {p['aceitas_fora']:.1%} |" + extra)
            lin += ["", "Matriz de confusão da detecção de fora do escopo: positivo = consulta válida; VP = válida aceita, "
                        "FN = válida recusada, FP = fora do escopo aceita, VN = fora do escopo recusada. "
                        "Precision = VP/(VP+FP); Recall = VP/(VP+FN); Accuracy = (VP+VN)/total."]
    lin += ["", "Gráficos e explicação das métricas: `notebooks/avaliacao_busca.ipynb`.", ""]
    caminho.write_text("\n".join(lin), encoding="utf-8")


if __name__ == "__main__":
    main()
