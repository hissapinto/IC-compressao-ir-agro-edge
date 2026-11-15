"""Funções de avaliação da busca: ranking por pergunta, MRR, Recall, AUROC e curva ROC.

Usado por scripts/avaliar.py. Só funções, nada roda ao importar. Depende só do numpy.

A ideia vem do mrr_at_k do estudo com o mMARCO (doc-ranker), com duas diferenças:
  1. aqui a busca é sobre o índice inteiro (20.665 chunks), não sobre um pool fechado;
  2. o gabarito é o id_original. Uma pergunta longa virou várias partes (chunks), e qualquer
     parte dela conta como acerto. Por isso o ranking é "deduplicado": cada pergunta aparece uma
     vez só, na posição da sua melhor parte.
"""
import numpy as np


# ---------------------------------------------------------------------------------------------
# Ranking deduplicado por id_original
# ---------------------------------------------------------------------------------------------

def codificar_grupos(ids_originais: list[str]) -> tuple[np.ndarray, list[str]]:
    """Troca cada id_original por um número inteiro (o "grupo" do chunk).

    Devolve:
      grupo_do_chunk -- array (n_chunks,): grupo_do_chunk[i] é o número da pergunta do chunk i
      nomes          -- lista em que nomes[g] é o id_original do grupo g
    """
    # dict.fromkeys mantém a ordem da primeira aparição e tira as repetições
    # (as partes _p1, _p2... de uma pergunta têm o mesmo id_original).
    nomes = list(dict.fromkeys(ids_originais))
    numero = {nome: g for g, nome in enumerate(nomes)}
    grupo_do_chunk = np.array([numero[i] for i in ids_originais], dtype=np.int64)
    return grupo_do_chunk, nomes


def melhor_score_por_pergunta(scores: np.ndarray, grupo_do_chunk: np.ndarray, n_grupos: int) -> np.ndarray:
    """Score de cada pergunta = o maior score entre as suas partes.

    scores -- array (n_chunks,) com o score da consulta contra cada chunk
    Devolve um array (n_grupos,), uma posição por id_original.
    """
    # Começa com -infinito e, para cada chunk, guarda o máximo no grupo dele.
    # np.maximum.at faz isso sem laço em Python, mesmo com índices repetidos.
    melhor = np.full(n_grupos, -np.inf, dtype=np.float64)
    np.maximum.at(melhor, grupo_do_chunk, scores)
    return melhor


def posicao_do_gabarito(melhor: np.ndarray, grupo_certo: int) -> int:
    """Posição (começando em 1) da pergunta certa no ranking deduplicado do índice inteiro.

    É 1 + quantas perguntas tiveram score MAIOR que o da certa. Empates contam a favor da certa
    (raríssimos com floats). Não precisa ordenar o índice inteiro: basta contar.
    """
    return int(1 + np.sum(melhor > melhor[grupo_certo]))


def top_n(melhor: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Os n grupos de maior score, em ordem decrescente. Devolve (grupos, scores)."""
    # argpartition separa os n maiores sem ordenar tudo (mais rápido); depois só esses são ordenados.
    candidatos = np.argpartition(-melhor, n)[:n]
    ordem = candidatos[np.argsort(-melhor[candidatos])]
    return ordem, melhor[ordem]


# ---------------------------------------------------------------------------------------------
# Métricas de ranking
# ---------------------------------------------------------------------------------------------

def reciprocal_rank(posicoes: np.ndarray, k: int = 10) -> np.ndarray:
    """1/posição se a pergunta certa está no top-k, senão 0. Uma posição por consulta.

    A média disso é o MRR@k: 1,0 = sempre em 1º; 0,5 = em média na 2ª posição; 0 = nunca no top-k.
    """
    posicoes = np.asarray(posicoes, dtype=np.float64)
    return np.where(posicoes <= k, 1.0 / posicoes, 0.0)


def acerto_ate(posicoes: np.ndarray, k: int) -> np.ndarray:
    """1 se a pergunta certa está entre as k primeiras, senão 0. A média é o Recall@k.

    Com um único documento relevante por consulta, Recall@k = Hit@k (acertou ou não).
    """
    return (np.asarray(posicoes) <= k).astype(np.float64)


def agregar_por_pergunta(valores: np.ndarray, perguntas: list[str]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Junta as várias versões de cada pergunta numa linha só: a média e o pior valor.

    Cada pergunta do golden set tem até 3 reescritas e 3 vagas, todas com a mesma resposta certa.
    Tirar a média direto sobre as consultas daria mais peso às perguntas com mais versões
    avaliadas; por isso primeiro se faz a média DENTRO de cada pergunta e só depois entre perguntas.

    valores   -- array (n_consultas,): a métrica de cada consulta (ex.: 1/posição, acerto no top-10)
    perguntas -- lista (n_consultas,): o id_original de cada consulta
    Devolve (medias, piores, ids), uma posição por pergunta, na ordem da primeira aparição:
      medias[i] -- média das versões da pergunta ids[i]
      piores[i] -- o menor valor entre as versões (a versão em que a busca foi pior)
    """
    valores = np.asarray(valores, dtype=np.float64)
    grupo, ids = codificar_grupos(list(perguntas))      # número de cada pergunta (0, 1, 2...)
    n = len(ids)
    soma = np.bincount(grupo, weights=valores, minlength=n)
    quantas = np.bincount(grupo, minlength=n)
    piores = np.full(n, np.inf)
    np.minimum.at(piores, grupo, valores)               # mínimo por pergunta, sem laço em Python
    return soma / quantas, piores, ids


def intervalo_bootstrap(valores: np.ndarray, n_reamostras: int = 1000, semente: int = 42,
                        alfa: float = 0.05) -> tuple[float, float]:
    """Intervalo de confiança da média por bootstrap (percentis 2,5% e 97,5% por padrão).

    Sorteia, com reposição, n valores entre os n avaliados, n_reamostras vezes, e olha como a
    média varia. No avaliar.py, cada valor é uma PERGUNTA (já com a média das suas versões), não
    uma consulta: as versões de uma mesma pergunta não são independentes entre si. Com ~200
    perguntas, isso mostra o quanto uma diferença entre conjuntos (ou entre modelos, mais tarde)
    pode ser só acaso da amostra.
    """
    valores = np.asarray(valores, dtype=np.float64)
    rng = np.random.default_rng(semente)
    idx = rng.integers(0, len(valores), size=(n_reamostras, len(valores)))
    medias = valores[idx].mean(axis=1)
    return float(np.quantile(medias, alfa / 2)), float(np.quantile(medias, 1 - alfa / 2))


# ---------------------------------------------------------------------------------------------
# Separação dentro x fora do escopo
# ---------------------------------------------------------------------------------------------

def auroc(positivos: np.ndarray, negativos: np.ndarray) -> float:
    """Área sob a curva ROC: a chance de um positivo sorteado ter score maior que um negativo.

    Aqui, positivo = consulta dentro do escopo; negativo = fora do escopo. 1,0 = separação
    perfeita; 0,5 = o score não ajuda nada a separar (igual a cara ou coroa).

    Cálculo pela estatística U de Mann-Whitney, com postos médios para os empates:
        AUROC = (soma dos postos dos positivos - n_pos (n_pos + 1) / 2) / (n_pos * n_neg)
    """
    positivos = np.asarray(positivos, dtype=np.float64)
    negativos = np.asarray(negativos, dtype=np.float64)
    todos = np.concatenate([positivos, negativos])
    # Postos (1 = menor score). Valores empatados recebem a média dos postos que ocupam.
    ordem = np.argsort(todos, kind="mergesort")
    postos = np.empty(len(todos), dtype=np.float64)
    postos[ordem] = np.arange(1, len(todos) + 1)
    valores, inverso, contagem = np.unique(todos, return_inverse=True, return_counts=True)
    soma_postos = np.zeros(len(valores))
    np.add.at(soma_postos, inverso, postos)
    postos = (soma_postos / contagem)[inverso]
    n_pos, n_neg = len(positivos), len(negativos)
    u = postos[:n_pos].sum() - n_pos * (n_pos + 1) / 2
    return float(u / (n_pos * n_neg))


def curva_roc(positivos: np.ndarray, negativos: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pontos da curva ROC, varrendo o limiar do maior score para o menor.

    Para cada limiar t, a regra é "aceita a consulta se score >= t":
      TPR (taxa de verdadeiros positivos) = fração das consultas válidas aceitas;
      FPR (taxa de falsos positivos)      = fração das consultas fora do escopo aceitas.
    Devolve (fpr, tpr, limiares), começando em (0, 0) e terminando em (1, 1).
    """
    positivos = np.asarray(positivos, dtype=np.float64)
    negativos = np.asarray(negativos, dtype=np.float64)
    limiares = np.unique(np.concatenate([positivos, negativos]))[::-1]
    tpr = np.array([(positivos >= t).mean() for t in limiares])
    fpr = np.array([(negativos >= t).mean() for t in limiares])
    return np.r_[0.0, fpr], np.r_[0.0, tpr], np.r_[np.inf, limiares]


def matriz_confusao(positivos: np.ndarray, negativos: np.ndarray, limiar: float) -> dict:
    """Matriz de confusão e métricas de classificação para a regra "aceita se valor >= limiar".

    Na detecção de fora do escopo, a decisão do sistema é binária: responder (aceitar) ou se abster.
      positivos -- valores das consultas válidas (deveriam ser aceitas)
      negativos -- valores das consultas fora do escopo (deveriam ser recusadas)
    Devolve:
      vp (verdadeiro positivo) -- válidas aceitas;      fn (falso negativo) -- válidas recusadas;
      fp (falso positivo)      -- fora aceitas;         vn (verdadeiro negativo) -- fora recusadas;
      precision = vp / (vp + fp): das aceitas, a fração que era válida;
      recall    = vp / (vp + fn): das válidas, a fração aceita;
      accuracy  = (vp + vn) / total: a fração de decisões certas. Depende muito da proporção entre
                  válidas e fora do escopo no teste (com muito mais válidas, aceitar tudo já dá alto).
    """
    positivos = np.asarray(positivos, dtype=np.float64)
    negativos = np.asarray(negativos, dtype=np.float64)
    vp = int((positivos >= limiar).sum())
    fn = len(positivos) - vp
    fp = int((negativos >= limiar).sum())
    vn = len(negativos) - fp
    return {"vp": vp, "fn": fn, "fp": fp, "vn": vn,
            "precision": vp / (vp + fp) if vp + fp else float("nan"),
            "recall": vp / (vp + fn) if vp + fn else float("nan"),
            "accuracy": (vp + vn) / (vp + fn + fp + vn)}


def mediana_iqr(valores: np.ndarray) -> dict:
    """Mediana, quartis (Q1, Q3) e intervalo interquartil (IQR = Q3 - Q1) de uma lista de valores."""
    q1, med, q3 = np.quantile(np.asarray(valores, dtype=np.float64), [0.25, 0.5, 0.75])
    return {"mediana": float(med), "q1": float(q1), "q3": float(q3), "iqr": float(q3 - q1)}
