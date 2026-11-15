# Avaliação da busca: e5-small-fp32

Índice com 20665 chunks (20381 perguntas). Ranking sobre o índice inteiro, deduplicado por id_original. Inclui consultas em rascunho.

## Ranking (consultas dentro do escopo)

| Conjunto | Perguntas | Consultas | MRR@10 | Recall@1 | Recall@5 | Recall@10 | Livro certo no 1º | Posição mediana |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Originais | 205 | 205 | 0.947 (0.92–0.97) | 0.912 (0.87–0.95) | 0.985 (0.97–1.00) | 0.990 (0.98–1.00) | 0.937 (0.90–0.97) | 1 |
| Reescritas | 205 | 615 | 0.620 (0.59–0.65) | 0.550 (0.51–0.59) | 0.711 (0.68–0.74) | 0.785 (0.75–0.81) | 0.798 (0.77–0.83) | 1 |
| Vagas | 205 | 615 | 0.375 (0.34–0.40) | 0.291 (0.26–0.33) | 0.491 (0.46–0.53) | 0.538 (0.50–0.58) | 0.642 (0.61–0.68) | 6 |
| Reescritas + vagas | 205 | 1230 | 0.497 (0.47–0.52) | 0.420 (0.39–0.45) | 0.601 (0.57–0.63) | 0.662 (0.63–0.69) | 0.720 (0.69–0.75) | 2 |

Média das versões de cada pergunta, depois média entre as perguntas. Entre parênteses, o intervalo de confiança de 95% (bootstrap sobre as perguntas).

Robustez, pior caso (worst-case): em cada pergunta, o valor da versão em que a busca foi pior; média entre as perguntas:

| Conjunto | MRR@10 | Recall@1 | Recall@5 | Recall@10 | Livro certo no 1º |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reescritas | 0.217 (0.17–0.27) | 0.137 (0.09–0.19) | 0.327 (0.26–0.39) | 0.454 (0.38–0.52) | 0.502 (0.43–0.58) |
| Vagas | 0.073 (0.04–0.10) | 0.044 (0.02–0.07) | 0.107 (0.06–0.15) | 0.161 (0.11–0.22) | 0.254 (0.20–0.31) |
| Reescritas + vagas | 0.049 (0.03–0.08) | 0.029 (0.01–0.05) | 0.073 (0.04–0.11) | 0.117 (0.07–0.17) | 0.176 (0.13–0.23) |

Cada versão separada (referência para a revisão):

| Versão | Consultas | MRR@10 | Recall@10 |
| --- | ---: | ---: | ---: |
| reescrita_1 | 205 | 0.637 | 0.849 |
| reescrita_2 | 205 | 0.907 | 0.976 |
| reescrita_3 | 205 | 0.315 | 0.532 |
| vaga_1 | 205 | 0.191 | 0.341 |
| vaga_2 | 205 | 0.755 | 0.951 |
| vaga_3 | 205 | 0.180 | 0.322 |

Análise pareada (205 perguntas com os três tipos; em quais tipos houve acerto no top-10 (na maioria das versões)):

| Tipos que acertaram | Perguntas | % |
| --- | ---: | ---: |
| original, reescrita, vaga | 95 | 46.3% |
| original, reescrita | 89 | 43.4% |
| original | 18 | 8.8% |
| reescrita | 1 | 0.5% |
| original, vaga | 1 | 0.5% |
| reescrita, vaga | 1 | 0.5% |

## Scores (todas as consultas)

| Conjunto | n | Score do 1º: mediana (IQR) | Diferença 1º−2º: mediana (IQR) | Média contra o corpus: mediana |
| --- | ---: | ---: | ---: | ---: |
| Originais | 205 | 0.924 (0.020) | 0.029 (0.027) | 0.801 |
| Reescritas | 615 | 0.897 (0.036) | 0.009 (0.016) | 0.797 |
| Vagas | 615 | 0.886 (0.029) | 0.004 (0.009) | 0.802 |
| Fora: outro assunto | 50 | 0.839 (0.029) | 0.004 (0.007) | 0.766 |
| Fora: agro sem livro | 50 | 0.864 (0.016) | 0.003 (0.005) | 0.795 |

Anisotropia: cosseno médio entre dois chunks sorteados = 0.811; norma do vetor médio do corpus = 0.901 (0 = vetores espalhados, 1 = todos iguais).

## Separação dentro × fora do escopo (AUROC)

| Válidas × fora | Score do 1º | Diferença 1º−2º |
| --- | ---: | ---: |
| original x fora | 0.997 | 0.916 |
| original x fora_geral | 1.000 | 0.901 |
| original x fora_agro | 0.994 | 0.930 |
| reescrita x fora | 0.926 | 0.694 |
| reescrita x fora_geral | 0.978 | 0.660 |
| reescrita x fora_agro | 0.874 | 0.729 |
| vaga x fora | 0.871 | 0.558 |
| vaga x fora_geral | 0.951 | 0.516 |
| vaga x fora_agro | 0.791 | 0.600 |
| reescrita+vaga x fora | 0.898 | 0.626 |
| reescrita+vaga x fora_geral | 0.965 | 0.588 |
| reescrita+vaga x fora_agro | 0.832 | 0.665 |

AUROC do score do 1º para separar, entre reescritas e vagas, quem acertou o 1º de quem errou: 0.800.

Pontos de operação (score do 1º; válidas = reescritas + vagas):

| Critério | Limiar | Válidas recusadas | Fora aceitas | VP | FN | FP | VN | Precision | Recall | Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fora_aceitas<=5% | 0.890 | 47.6% | 3.0% | 644 | 586 | 3 | 97 | 0.995 | 0.524 | 0.557 |
| validas_recusadas<=5% | 0.855 | 4.4% | 54.0% | 1176 | 54 | 54 | 46 | 0.956 | 0.956 | 0.919 |
| fora_aceitas<=10% | 0.880 | 30.7% | 10.0% | 853 | 377 | 10 | 90 | 0.988 | 0.693 | 0.709 |
| validas_recusadas<=10% | 0.860 | 6.7% | 40.0% | 1147 | 83 | 40 | 60 | 0.966 | 0.933 | 0.908 |

Matriz de confusão da detecção de fora do escopo: positivo = consulta válida; VP = válida aceita, FN = válida recusada, FP = fora do escopo aceita, VN = fora do escopo recusada. Precision = VP/(VP+FP); Recall = VP/(VP+FN); Accuracy = (VP+VN)/total.

Pontos de operação (diferença 1º−2º; válidas = reescritas + vagas):

| Critério | Limiar | Válidas recusadas | Fora aceitas | VP | FN | FP | VN | Precision | Recall | Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fora_aceitas<=5% | 0.016 | 76.1% | 3.0% | 296 | 934 | 3 | 97 | 0.990 | 0.241 | 0.295 |
| validas_recusadas<=5% | 0.000 | 0.0% | 100.0% | 1230 | 0 | 100 | 0 | 0.925 | 1.000 | 0.925 |
| fora_aceitas<=10% | 0.014 | 72.6% | 6.0% | 337 | 893 | 6 | 94 | 0.983 | 0.274 | 0.324 |
| validas_recusadas<=10% | 0.000 | 0.0% | 100.0% | 1230 | 0 | 100 | 0 | 0.925 | 1.000 | 0.925 |

Matriz de confusão da detecção de fora do escopo: positivo = consulta válida; VP = válida aceita, FN = válida recusada, FP = fora do escopo aceita, VN = fora do escopo recusada. Precision = VP/(VP+FP); Recall = VP/(VP+FN); Accuracy = (VP+VN)/total.

Gráficos e explicação das métricas: `notebooks/avaliacao_busca.ipynb`.
