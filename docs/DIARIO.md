# Diário da pesquisa

Registro do que foi feito na IC, dia a dia: o que foi feito, as decisões, os números e o que ficou
pendente. As entradas mais recentes ficam no topo. Os horários são de Brasília.

**Como manter:** ao fim de cada dia de trabalho, e a cada commit, acrescentar ou atualizar a entrada
do dia. Uma entrada tem quatro partes: *Feito*, *Decisões*, *Números* e *Pendências*. Quando um
commit entra, ele vai para a tabela de commits no fim do arquivo.

## Estado atual (15/11/2026)

- **Corpus:** 41 livros da coleção *500 Perguntas, 500 Respostas*. Por decisão oficial do orientador
  (até segunda ordem), o corpus usado tem só os pares que vêm de texto: 20.665 chunks de até 512 tokens
  (20.381 perguntas) em `codigo/data/processed/chunks.jsonl`. O corpus completo (20.885 chunks, com
  introduções e pares que dependem de imagem) fica em `auxiliares/chunks_completo.jsonl`. Nenhuma
  etapa do pipeline usa IA; a transcrição das imagens está no `legado/`. A conversão para txt é reproduzível
  (`scripts/converter_para_txt.py`).
- **Índice:** `multilingual-e5-small` em fp32, em `codigo/data/indices/e5-small-fp32/`, regenerado
  com o corpus atual (20.665 × 384, ids iguais aos do `chunks.jsonl`).
- **Busca:** só densa, pela linha de comando (`scripts/buscar.py`).
- **Análise exploratória:** `codigo/notebooks/eda_500perguntas.ipynb`, refeita em 14/11/2026
  com o corpus filtrado (20.665 chunks), já executada e com os gráficos salvos.
- **Dados brutos:** ePubs, PDFs, txt, `fontes.csv` e `indice.csv` em `codigo/data/raw/`. Os
  txt são a saída do `converter_para_txt.py`, e o caminho ePub/PDF → txt → chunks é 100%
  reproduzível (conferido em 14/11/2026).
- **Legado:** o que não faz mais parte do pipeline está em `legado/`, com a mesma estrutura de pastas.
- **Avaliação:** conjunto em `codigo/data/golden/` (205 perguntas, cada uma com a original, 3
  reescritas e 3 vagas, todas com o mesmo gabarito, + 100 fora do escopo), **em revisão**. Medição
  atual em `codigo/results/e5-small-fp32/` (15/11, média das 3 versões): MRR@10 de 0,95 (originais),
  0,62 (reescritas) e 0,38 (vagas); Recall@10 da pior das 3 de 0,45 e 0,16; AUROC do score do 1º de
  0,90 (reescritas + vagas × fora). Gráficos em `codigo/notebooks/avaliacao_busca.ipynb`.
- **Próximo passo:** revisar o conjunto de avaliação e rodar `python scripts/avaliar.py --so-aprovadas`.

---

## 15/11/2026 (domingo, à tarde): três versões de reescrita e de vaga por pergunta

**Feito**
- **`pares.csv` com três versões** (pedido da Isabela): cada pergunta ganhou `reescrita_1` a
  `reescrita_3` e `vaga_1` a `vaga_3`, cada uma com o seu status. A versão 1 é a que já existia (as 8
  primeiras revisadas pela Isabela, as outras no estilo dela). As versões 2 e 3 foram escritas para as
  205 perguntas (820 consultas novas, todas `rascunho`), seguindo as regras que saíram das correções
  dela nos exemplos:
  - uma versão usa o termo do livro (desbaste, liofilização...), outra troca por sinônimo ou nome
    popular e outra só descreve o que a pessoa vê ou quer, sem o termo;
  - o nome da cultura aparece em pelo menos uma das três;
  - o começo da pergunta varia ("como fazer" vira "qual a melhor", "quando", "o que fazer"...);
  - as vagas podem ser uma dúvida curta ("inseminação artificial em porco é ruim?").
  Na prática, a versão 2 ficou com o termo do livro (repete cerca de 70% das palavras da original) e
  a 3, sem o termo (menos de 10%).
- **`avaliar.py`:** lê as três versões (e ainda aceita o `pares.csv` antigo, de uma versão). Métricas
  de ranking agora são a média das versões de cada pergunta e depois a média entre as perguntas, com
  bootstrap sobre as perguntas. Novas saídas: **robustez** (pior das 3 por pergunta), média de cada
  versão separada e a coluna `versao` no `por_consulta.csv`. A análise pareada conta um tipo como
  acerto quando a maioria das versões (2 de 3) acerta.
- **`src/avaliacao.py`:** nova função `agregar_por_pergunta` (média e pior valor das versões).
- **Notebook:** nova seção 4, "Robustez: a pior das três versões" (média × pior das 3, em quantas
  versões a busca acerta, cada versão separada); seções seguintes renumeradas; análise pareada e
  tabelas adaptadas às três versões; resumo dos achados refeito.
- READMEs, `futuro_da_pesquisa.md`, guia (`.md` e `.pdf`) e `data/LEIAME.txt` atualizados.
- **Anotado no `futuro_da_pesquisa.md` (novo item 2b):** como reduzir o erro entre perguntas parecidas de
  livros diferentes (reforço/filtragem por metadados, híbrida, busca hierárquica, reranker,
  fine-tuning contrastivo com negativos difíceis, pedido de esclarecimento). Também anotado que a
  Isabela tem acesso a um computador mais potente no laboratório da faculdade.
- **Anotado no `futuro_da_pesquisa.md` (item 8, Gerador):** recuperar a resposta completa das perguntas
  divididas na montagem do contexto do RAG (*parent document retrieval*), com o cuidado da janela de
  contexto dos geradores pequenos. Ideia da Isabela; só anotado, não implementado.
- **Guia, seção 8.2 (anisotropia)** ampliada a pedido da Isabela: o que é espaço isotrópico × cone,
  como medimos (cosseno médio entre chunks sorteados 0,81; norma do vetor médio 0,90), a faixa de 0,84
  a 0,92 das medianas do score do 1º e por que isso atrapalha a detecção de fora do escopo. PDF gerado
  de novo.
- **Matriz de confusão** (pedido da Isabela, sem F1): nos pontos de operação da detecção de fora do
  escopo, o `avaliar.py` (`resumo.md` e `metricas.json`) e o notebook (seção 12) agora trazem VP, FN,
  FP, VN, precision, recall e accuracy (nova função `matriz_confusao` em `src/avaliacao.py`). No
  limiar 0,880 (no máximo 10% das fora aceitas): precision 0,988, recall 0,693, accuracy 0,709. A
  accuracy engana aqui: com 1.230 válidas e 100 fora do escopo, aceitar tudo já daria 0,925. Os números
  foram acrescentados aos resultados existentes, a partir do `por_consulta.csv` (mesma conta do script,
  sem rodar o modelo de novo).
- **Termos técnicos** (pedido da Isabela, que quer se acostumar com eles; explicar quando forem novos,
  mas usar sempre): "não sei" virou **detecção de fora do escopo** (*out-of-scope detection*) e
  **abstenção** (*abstention*); "pior das 3" virou **pior caso** (*worst-case*). Trocado no notebook,
  no guia (com os três termos no glossário), no `futuro_da_pesquisa.md`, no `codigo/README.md` e no
  `avaliar.py`.

**Decisões**
- A média é feita por pergunta antes da média geral, para cada pergunta pesar igual mesmo que alguma
  versão seja rejeitada na revisão. A "pior das 3" entra como medida de robustez.
- As versões ficaram como três níveis de distância do texto do livro (1 = estilo da Isabela, 2 = com
  o termo, 3 = sem o termo). Isso não era o plano inicial (a ordem seria livre), mas é útil: a
  diferença entre a 2 e a 3 mede o quanto a busca depende das palavras do livro.

**Números** (todas as consultas em rascunho; reescritas e vagas = média das 3 versões)

| Conjunto | MRR@10 | Recall@1 | Recall@5 | Recall@10 | Livro certo no 1º | Recall@10 da pior das 3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Originais | 0,947 | 0,912 | 0,985 | 0,990 | 0,937 | |
| Reescritas | 0,620 | 0,550 | 0,711 | 0,785 | 0,798 | 0,454 |
| Vagas | 0,375 | 0,291 | 0,491 | 0,538 | 0,642 | 0,161 |

- Recall@10 por versão: reescritas 0,849 / 0,976 / 0,532; vagas 0,341 / 0,951 / 0,322 (versões 1 / 2 / 3).
- Nas vagas, 104 das 205 perguntas só são achadas no top 10 em uma das três versões.
- Pareado (maioria das versões): 46% acertaram nos três tipos, 43% na original e na reescrita, 9% só
  na original.
- AUROC do score do 1º, reescritas + vagas × fora: 0,898 (0,965 contra outro assunto, 0,832 contra
  agro). Com a diferença 1º−2º: 0,626. Aceitar no máximo 10% das fora do escopo exige limiar 0,880 e
  recusa 31% das válidas. AUROC do score do 1º para separar acerto de erro: 0,800.

**Pendências**
- Revisar as versões 2 e 3 no `pares.csv` (status e texto) e rodar de novo com `--so-aprovadas`.
- Decidir como tratar perguntas repetidas entre livros.

---

## 15/11/2026 (domingo, de manhã): consultas fora do escopo conferidas contra o corpus e nova medição

**Feito**
- A Isabela notou consultas dentro do escopo no `fora_do_escopo.csv`. As 100 foram conferidas contra
  o corpus (busca por palavra no `chunks.jsonl` e 1º colocado da busca). Três tinham resposta e foram
  trocadas por temas que não aparecem em nenhum livro (0 ocorrências no corpus), como `rascunho`:
  - fa016 "Como criar abelhas sem ferrão?" → "Como criar chinchila?" (recursos genéticos q380 ensina
    a adquirir enxames de abelhas-sem-ferrão para iniciar uma criação);
  - fa045 "Como cultivar mogno africano?" → "Quando colher o mangostão?" (o livro de ILPF tem várias
    perguntas sobre o plantio de mogno-africano, q149 a q152);
  - fa014 "Como montar um apiário para produzir mel?" → "Como plantar sapoti?" (recursos genéticos
    q381 trata de como iniciar uma criação de abelhas, e caju q124 e Pantanal q494 falam de apicultura).
- Ficaram como estavam, por não terem resposta de verdade: fa025 broca-da-cana (fronteira, já anotada:
  o milho fala dela como praga do milho, não do controle na cana), fa022 vermifugação de equinos (o
  livro de gado de corte só fala de bovinos), fa006 sangria da seringueira (o ILPF fala de seringueira,
  mas não de sangria) e fg017 bolsa de valores (milho e sorgo citam a BM&F só para mercado futuro).
- `avaliar.py` rodado de novo no Mac (já com as reescritas e vagas no estilo da Isabela) e notebook
  `avaliacao_busca.ipynb` reexecutado, com o "Resumo dos achados" atualizado.
- Números atualizados no `codigo/README.md`, `README.md`, `docs/futuro_da_pesquisa.md` e no guia
  (`.md` e `.pdf`, incluindo a tabela de precisão/recall da seção 8.4).

**Números** (todas as consultas em rascunho)

| Conjunto | MRR@10 | Recall@1 | Recall@5 | Recall@10 | Livro certo no 1º |
| --- | ---: | ---: | ---: | ---: | ---: |
| Originais | 0,947 | 0,912 | 0,985 | 0,990 | 0,937 |
| Reescritas | 0,637 | 0,537 | 0,771 | 0,849 | 0,863 |
| Vagas | 0,191 | 0,112 | 0,302 | 0,341 | 0,698 |

- As reescritas subiram muito em relação a 14/11 (MRR@10 de 0,41 para 0,64). A mudança vem da
  reescrita no estilo da Isabela, não da troca das fora do escopo, que não entram no ranking. Vale
  conferir na revisão se as novas reescritas não ficaram perto demais das palavras da original.
- AUROC do score do 1º, reescritas + vagas × fora: 0,895 (0,964 contra outro assunto, 0,826 contra
  agro). Com a diferença 1º−2º: 0,577. Aceitar no máximo 10% das fora do escopo exige limiar 0,880 e
  recusa 31% das válidas.
- AUROC do score do 1º para separar acerto de erro (reescritas + vagas): 0,724.
- Pareado (top 10): 33% acertaram nas três versões, 51% na original e na reescrita, 15% só na original.
- Fora do escopo com score mais alto: broca-da-cana (0,903), fermentação do cacau (0,897),
  vermifugação de equinos (0,892).

**Pendências**
- Revisar `pares.csv` e `fora_do_escopo.csv` e rodar de novo com `--so-aprovadas`.
- Decidir como tratar perguntas repetidas entre livros.

---

## 14/11/2026 (sábado, à noite): conjunto de avaliação e primeira medição da busca

**Feito**
- **Índice conferido:** o `data/indices/e5-small-fp32/` já tinha sido regenerado (20:42 UTC) a partir
  do `chunks.jsonl` atual: 20.665 linhas, e o `ids.json` tem os mesmos ids, na mesma ordem.
- **`scripts/sortear_golden.py`:** sorteia 5 perguntas por livro (205), por `id_original`, com
  semente 42, e grava `data/golden/amostra.csv` com a resposta inteira.
- **Conjunto de avaliação** em `data/golden/`: `pares.csv` (uma linha por pergunta, com a original, a
  reescrita e a vaga lado a lado, todas com o mesmo gabarito) e `fora_do_escopo.csv` (50 perguntas de
  outro assunto e 50 de agricultura fora dos 41 livros). Reescritas, vagas e fora do escopo foram
  escritas com LLM (Claude) e estão como `rascunho`.
- **`src/avaliacao.py`:** ranking deduplicado por `id_original` sobre o índice inteiro (adaptação do
  `mrr_at_k` do doc-ranker, que usava pool fechado), MRR, Recall, bootstrap, AUROC (Mann-Whitney) e
  curva ROC, só com numpy.
- **`scripts/avaliar.py`:** codifica as consultas com `query: `, mede ranking, análise pareada,
  scores do 1º e diferença 1º−2º (mediana e IQR), AUROC dentro × fora, tabelas de limiares,
  anisotropia e desempenho por livro. Grava `resumo.md`, `metricas.json`, 4 CSVs e 10 gráficos em
  `results/e5-small-fp32/`. Testado antes com um modelo falso (bag-of-words) e depois rodado no Mac.
- `LEIAME.txt` de `data/`, `scripts/`, `src/`, `configs/`, `docs/` e `APIs/` com a etapa de
  avaliação ([7] golden, [8] results); `LEIAME.txt` novo em `results/`. Atualizados o
  `codigo/README.md` (seções de avaliação), o `README.md` da pasta Embrapa, o
  `docs/futuro_da_pesquisa.md` (item 0 com os resultados) e o `docs/guia_do_projeto.md` (.md e .pdf:
  etapas [7] e [8], AUROC, bootstrap e IQR).
- `matplotlib==3.11.2` e suas dependências (versões do venv) entraram no `codigo/requirements.txt`.
- Revisão do `pares.csv`: a Isabela revisou as 8 primeiras linhas (até algodão q073). As reescritas e vagas das outras 197 foram reescritas no estilo dela (frases curtas e diretas, palavras do dia a dia, nome comum da praga ou doença mantido). Continuam como `rascunho`, e os números de avaliação acima são de antes dessa mudança.
- **Notebook `notebooks/avaliacao_busca.ipynb`** (pedido da Isabela, no lugar da pasta de PNGs): lê os resultados do `avaliar.py` e traz os gráficos com a explicação de cada métrica (posição deduplicada, Recall@k, MRR@k, IC por bootstrap, mediana e IQR, anisotropia, AUROC e curva ROC, limiares), mais análise pareada posição a posição, erros e desempenho por livro. Executado com os resultados da 1ª rodada. O `avaliar.py` não gera mais gráficos, e a pasta `results/e5-small-fp32/graficos/` foi apagada. Depois, o notebook ganhou um "Resumo dos achados" logo após a introdução, como na EDA.
- Guia de estudo (`docs/guia_do_projeto.md` e `.pdf`, agora com 19 páginas): nova seção 8.4 sobre
  tipos de métricas: matriz de confusão, acurácia, precisão, recall e F1, por que a acurácia não serve
  (1 resposta certa entre 20.665 chunks: dizer "nada é relevante" daria 99,995%), por que a Precisão@k
  vira Recall@k / k, e quando essas métricas voltam a servir (vários relevantes; o "não sei" como
  classificação binária, com a matriz de confusão aplicada aos limiares 0,890 e 0,850 da primeira
  avaliação). Glossário e perguntas frequentes atualizados.

**Decisões**
- Três versões por pergunta, com o mesmo `id_original`, para que a comparação entre elas seja pareada
  (pedido da Isabela). Só as consultas fora do escopo são independentes.
- As reescritas podem citar a cultura, mesmo quando a original não cita (o usuário real diz de que
  planta ou animal fala). As originais que dependem da pergunta anterior ("essa doença") ganharam na
  reescrita o nome da doença.
- A diferença 1º−2º é calculada entre perguntas distintas (depois de deduplicar as partes).
- Revisão por status (`rascunho`, `aprovada`, `rejeitada`) direto no CSV; `--so-aprovadas` usa só as
  revisadas.

**Números** (todas as consultas, antes da revisão)

| Conjunto | MRR@10 | Recall@1 | Recall@5 | Recall@10 | Livro certo no 1º |
| --- | ---: | ---: | ---: | ---: | ---: |
| Originais | 0,947 | 0,912 | 0,985 | 0,990 | 0,937 |
| Reescritas | 0,407 | 0,322 | 0,537 | 0,629 | 0,756 |
| Vagas | 0,189 | 0,112 | 0,302 | 0,337 | 0,702 |

- Score do 1º (mediana): originais 0,924, reescritas 0,887, vagas 0,881, fora (outro assunto) 0,839,
  fora (agro) 0,864. Diferença 1º−2º (mediana): 0,029 nas originais e de 0,003 a 0,005 nos demais.
- AUROC do score do 1º, reescritas + vagas × fora: 0,859 (0,955 contra outro assunto, 0,763 contra
  agro). Com a diferença 1º−2º: 0,515. Aceitar no máximo 10% das fora do escopo exigiria limiar 0,885
  e recusaria 52% das válidas.
- Anisotropia: cosseno médio entre chunks sorteados 0,811; norma do vetor médio 0,901.
- Pareado (top 10): 25% das perguntas acertaram nas três versões, 37% na original e na reescrita,
  29% só na original.
- Dos 18 erros das originais no 1º lugar, a maioria perdeu para uma pergunta igual ou quase igual
  em outro livro (por exemplo, "O que é produção integrada?" em trigo e banana).
- Uma consulta "fora do escopo" (abelhas sem ferrão) tem resposta no livro de recursos genéticos;
  ficou marcada na coluna `observacao` para a revisão.

**Pendências**
- Revisar `pares.csv` e `fora_do_escopo.csv` (status e texto) e rodar de novo com `--so-aprovadas`.
- Decidir como tratar perguntas repetidas entre livros (aceitar qualquer idêntica ou relatar à parte).
- Ablação de centralização dos vetores (a AUROC do score do 1º não ficou perto de 0,5, mas a da
  diferença 1º−2º ficou, e a separação contra agro fora dos livros é fraca).
- Pôr `pandas` e `ipykernel` (usados só no notebook) no `requirements.txt`.

---

## 14/11/2026 (sábado): dados brutos em `codigo/data/raw/`

**Feito**
- ePubs, PDFs e txt saíram de `500PerguntasRespostas/dados/` e foram para `codigo/data/raw/`
  (`epub/`, `PDFs/`, `txt/`), junto com o `fontes.csv` e o `indice.csv` (que estava dentro de `PDFs/`).
  O `LEIAME.md` de `data/raw/` foi apagado, porque a pasta agora tem os dados de verdade.
- A pasta `500PerguntasRespostas/` deixou de existir: o checklist do Pi foi para
  `docs/checklist_IR_pi4.md` e o notebook já estava em `codigo/notebooks/`.
- Caminhos atualizados: `src/chunking.py` e `scripts/converter_para_txt.py` (constante `RAW`), colunas
  do `fontes.csv` e do `indice.csv` (agora relativas a `data/raw/`, sem o prefixo `dados/`), os dois
  READMEs, `docs/preparacao_dos_dados.md` e o ADR 0001. O `.gitignore` não precisou mudar (os dados
  brutos continuam versionados).
- Conferência: o `converter_para_txt.py` regenerou os txt e bateu 20.499 de 20.499 pares, sem nenhuma
  diferença nos arquivos; o `chunking.py --sem-divisao` e o `dividir_chunks.py` geraram intermediários
  idênticos; o `chunks.jsonl` final saiu idêntico byte a byte.
- `LEIAME.txt` curto nas pastas principais (raiz, `docs/`, `APIs/`, `codigo/` e suas subpastas
  `src/`, `scripts/`, `configs/`, `data/`, `notebooks/`, `docs/`), com o pipeline numerado de [1] a [6]
  e o papel de cada arquivo. As subpastas de `data/` ficam descritas no `data/LEIAME.txt`. Nenhum vai
  em `data/raw/txt/`, porque o `chunking.py` lê todos os `.txt` dessa pasta.
- READMEs revisados de novo: o `codigo/README.md` agora cita o `pdftotext` (Poppler) no ambiente, e a limitação sobre livros faltando foi corrigida (26 ePubs e 44 PDFs em `data/raw/`,
  41 livros no corpus, só a pergunta 383 de búfalos faltando). Os READMEs não citam os `LEIAME.txt`.
  Números conferidos com os arquivos (20.665 chunks, 20.381 perguntas, 267 divididas, 26 + 15 fontes).
- Novo `docs/futuro_da_pesquisa.md`: possibilidades para a pesquisa (golden set, híbrida, ablações,
  compressão, Pi, Responde Agro, reranker, gerador) e os argumentos discutidos (passage × query, papel
  da pergunta original no chunk, golden set com perguntas reescritas, chunks divididos e `id_original`).
  Depois, o item 6 ganhou o desenho da comparação entre o nosso IR e a API Responde Agro (mesmas
  consultas, resultados ligados pelo `id_original`, mesmas métricas, concordância e latência).
- Comentários explicativos, passo a passo, nos 7 arquivos .py (`src/chunking.py`, `src/embeddings.py` e
  os 5 scripts). Só comentários e docstrings: a árvore do código (AST) ficou idêntica, e o
  `chunking.py --sem-divisao`, o `filtrar_chunks.py` e o `converter_para_txt.py` (abacaxi e algodão)
  geraram arquivos idênticos aos atuais.
- Novo `docs/guia_do_projeto.md` (+ `.pdf`): guia de estudo com o projeto em uma página, como a busca
  funciona, o pipeline etapa por etapa, os arquivos de dados, as pastas, as decisões e um glossário dos
  termos técnicos.
- `docs/futuro_da_pesquisa.md`: novo item 0, a primeira medição do índice atual (MRR@10 e Recall@10
  sobre os 20.665 chunks, acerto pelo `id_original`, partindo do `mrr_at_k` do projeto de estudo).
  A ordem é regenerar o índice, fazer um teste de sanidade com as perguntas originais e depois um piloto
  com cerca de 200 perguntas reescritas. Também entraram os argumentos sobre normalização L2 (tira só a
  magnitude e não muda o ranking) e anisotropia (scores altos e parecidos; opções: centralizar os
  vetores, híbrida, reranker, fine-tuning; ablação E5 puro × centralizado × híbrido).
- Guia de estudo (`docs/guia_do_projeto.md` e `.pdf`, agora com 15 páginas): nova seção 8 com
  normalização L2 (o que é, exemplo [3, 4] → [0,6; 0,8], para que serve e por que não muda o ranking),
  anisotropia (cone estreito, scores entre 0,7 e 0,9, aperto de domínio, mitigações) e métricas
  (Recall@k, MRR@k e nDCG@k com exemplos, pool fechado × corpus inteiro, acerto pelo `id_original`).
  Glossário e perguntas frequentes atualizados.

**Decisões**
- O ADR 0001 foi atualizado: os dados brutos ficam em `codigo/data/raw/`, e a alternativa de mantê-los
  fora de `codigo/` foi descartada (Isabela, 14/11).
- Os próximos passos da busca vão ser decididos conforme o resultado da medição de MRR (Isabela, 14/11).

**Números**
- `data/raw/`: PDFs 253 MB, ePubs 102 MB, txt 15 MB.

**Pendências**
- Regenerar o índice E5 no Mac: `cd codigo && source .venv/bin/activate && python scripts/indexar.py`.
- No próximo commit, usar `git add -A` para o git registrar as mudanças de pasta.

---

## 14/11/2026 (sábado): transcrição das imagens fora do pipeline; filtro oficial

**Feito**
- A etapa de transcrição das imagens saiu do pipeline e foi para `legado/`:
  `scripts/inserir_transcricoes.py`, `data/processed/transcricoes_imagens.csv` e os intermediários
  que tinham as transcrições (`chunks_sem_divisao.jsonl`, com 20.595 chunks, e `chunks_completo.jsonl`,
  com 20.887).
- Pipeline novo: `converter_para_txt.py` → `src/chunking.py --sem-divisao` (agora grava direto
  `auxiliares/chunks_sem_divisao.jsonl`; o `chunks_sem_imagens.jsonl` deixou de existir) →
  `dividir_chunks.py` → `filtrar_chunks.py` → `indexar.py`.
- A lista do filtro virou `configs/ids_respostas_com_imagem.txt` (antes `ids_imagem_nao_transcrita.txt`),
  com três grupos marcados por `# == ... ==`: os 113 pares que tinham imagem transcrita, os 5 que
  remetem a imagem não transcrita e os 4 casos de fronteira (comentados). O `filtrar_chunks.py` não
  usa mais o campo `conteudo_imagem` nem a opção `--manter-imagens`.
- O novo `chunks_completo.jsonl` (sem transcrições) foi gerado com o tokenizer do E5. Antes, conferi
  que o mesmo código reproduz byte a byte o `chunks_completo.jsonl` antigo a partir do
  `chunks_sem_divisao.jsonl` antigo.
- **O `chunks.jsonl` final ficou idêntico byte a byte ao anterior** (20.665 chunks). O índice
  continua pendente pelo mesmo motivo de antes (ainda é o do corpus de 20.887).
- EDA: a seção 10 agora lê os grupos da lista de `configs/` (o campo `conteudo_imagem` não existe
  mais), e os textos foram reescritos para descrever só o estado atual. Notebook executado de novo.
- **Documentação sem histórico:** a pedido da Isabela, READMEs, `preparacao_dos_dados.md`, notebook,
  ADR, checklist, a lista de `configs/` e os comentários dos scripts descrevem só o estado atual,
  sem datas de mudança nem "antes era". O histórico fica só neste diário e no `legado/`.

**Decisões**
- **A remoção das introduções e das respostas que dependem de imagem é oficial até segunda ordem**
  (Isabela, 14/11).
- A transcrição com IA sai do pipeline de vez (escolha da Isabela). Para trazer esses pares de volta,
  é preciso tirar os arquivos do `legado/`.

**Números**
- `chunks_sem_divisao.jsonl`: 20.595 chunks. `chunks_completo.jsonl`: 20.885 (272 chunks viram 562
  partes). Fora do corpus: 220 chunks (96 introduções; 119 chunks de 113 pares com imagem; 5 pares com
  imagem não transcrita). `chunks.jsonl`: 20.665 chunks, 20.381 perguntas.

---

## 14/11/2026 (sábado): análise exploratória refeita com o corpus filtrado

**Feito**
- O notebook `eda_500perguntas.ipynb` foi adaptado ao `chunks.jsonl` filtrado e executado de novo,
  com o tokenizador real do E5 (o mesmo do cache do Mac).
- Mudanças no notebook: o caminho dos dados ficou relativo à pasta do notebook (com o caminho
  absoluto do Mac como alternativa); saiu o uso da coluna `conteudo_imagem`, que não existe mais no
  corpus; a checagem "perguntas de 1 a 500" agora separa as perguntas tiradas pelo filtro (lidas do
  `chunks_completo.jsonl`) das que de fato faltam; a antiga seção 10 (imagens transcritas) virou
  **"O que ficou fora do corpus"**, com a tabela por motivo e um gráfico por livro; o resumo e as
  conclusões foram atualizados.
- Ganhou uma célula **"Resumo dos achados"** no começo, antes de "0. Preparação".
- O notebook foi movido de `500PerguntasRespostas/` para `codigo/notebooks/`, que estava vazia e é a
  pasta prevista no ADR 0001 para análises. O caminho dos dados no notebook, os READMEs e o checklist
  do Pi foram ajustados.
- `codigo/docs/preparacao_dos_dados.md` foi dividido: o relato histórico (conversão com IA em
  outubro, triagem e transcrição das imagens, comparação de 03/11) foi para
  `legado/codigo/docs/preparacao_dos_dados.md`, e no lugar ficou um documento novo, só com o pipeline
  atual: fontes, conversão, extração, transcrições, divisão, filtro, como reproduzir e limitações.

**Números**
- 20.665 chunks, 20.381 perguntas, 41 livros (492 a 559 chunks por livro).
- Fora do corpus: 222 chunks (96 introduções, 121 chunks de 113 perguntas com imagem transcrita e
  5 perguntas com imagem não transcrita). As perguntas com imagem estão espalhadas por 32 livros.
- 267 perguntas divididas em 2+ chunks (antes, 274). Mediana de 86 palavras por chunk; máximo de
  512 tokens; 84,4% dos chunks com até 256 tokens.
- Temas e tipos de pergunta mantiveram as mesmas proporções (pragas e doenças 17%, escolha 36%).
- Única falha de extração continua sendo búfalos q383.

---

## 14/11/2026 (sábado): pipeline 100% reproduzível e pasta `legado/`

**Feito**
- **Conferência da reprodução, do zero** (numa pasta temporária, sem tocar nos arquivos):
  - `converter_para_txt.py --sem-download`: os 41 txt saíram **idênticos byte a byte** aos de
    `dados/txt/`, e 20.499 de 20.499 pares iguais.
  - `chunking.py --sem-divisao` e `inserir_transcricoes.py`: `chunks_sem_imagens.jsonl`,
    `relatorio.csv` e `chunks_sem_divisao.jsonl` idênticos aos atuais.
  - `dividir_chunks.py` precisa do tokenizer do E5 e não rodou aqui. Conferi que as partes do
    `chunks_completo.jsonl` remontam exatamente os 20.595 chunks antes da divisão.
  - `filtrar_chunks.py` é determinístico (já conferido hoje).
- **Pasta `legado/`**, com a mesma estrutura do projeto e um `LEIAME.md` explicando cada item:
  - `legado/500PerguntasRespostas/dados/txt/`: os txt da conversão feita com IA em outubro,
    restaurados do git. Como o conteúdo é igual ao da história, o git não guarda nada duplicado.
  - `legado/500PerguntasRespostas/dados/comparacao_03-11/`: era a `dados/txt_reproduzido/`, a
    primeira execução do conversor no Mac, com a comparação contra os txt antigos.
  - `legado/codigo/data/processed/auxiliares/`: `imagens_transcritas.csv` e `chunks_alterados.jsonl`.
  - `legado/codigo/scripts/historico/`: `ligar_transcricoes_imagens.py`.
- **Sem pastas "_reproduzido":** o `converter_para_txt.py` agora grava direto em `dados/txt/`, e a
  comparação virou opcional (`--comparar-com <pasta>`). A linha do `txt_reproduzido/` saiu do
  `.gitignore`.
- READMEs e `docs/preparacao_dos_dados.md` atualizados.
- A Isabela moveu este diário e os dois levantamentos (`Datasets para RAG offline...` e
  `Modelos_embedding_e_gerador`, .md e .pdf) para a nova pasta `Embrapa/docs/`. Os links do README
  da pasta foram ajustados. Nenhum script dependia desses arquivos.

**Decisões**
- A Isabela quer o pipeline 100% reproduzível. Pastas ficam só com o nome (`txt`, não
  `txt_reproduzido`), e tudo o que é legado vai para `legado/`, espelhando `codigo/`, `dados/` etc.
- O `transcricoes_imagens.csv` continua em `codigo/data/processed/`, porque ainda gera o corpus
  completo. Os pares com imagem só ficam fora do `chunks.jsonl`.
- Correção de uma resposta minha anterior: os txt de `dados/txt/` **já eram** a saída do script desde
  03/11. Os txt da IA não estavam mais no pipeline.

**Números**
- 41 de 41 txt idênticos; 20.499 de 20.499 pares; 3 arquivos intermediários idênticos byte a byte.

**Pendências**
- Para os txt saírem idênticos byte a byte, use as versões de `dados/txt/ferramentas.json` (Python
  3.10.12, beautifulsoup4 4.15.0, pdftotext 22.02.0). No Mac, o Poppler é o 26.10, que muda só linhas
  do sumário dos PDFs e não muda os chunks.
- No `git status`, as mudanças aparecem como arquivos apagados e novos, porque as pastas foram
  movidas sem `git mv`. Um `git add -A` faz o git reconhecer as renomeações.
- Regenerar o índice E5 no Mac (pendência anterior).

---

## 14/11/2026 (sábado): corpus só com os pares que vêm de texto

**Feito**
- Novo passo no pipeline, `scripts/filtrar_chunks.py`, com a função `filtrar_chunks` em
  `src/chunking.py`. Ele lê o corpus completo (`auxiliares/chunks_completo.jsonl`) e escreve o
  `chunks.jsonl` sem as introduções, sem os pares com `conteudo_imagem` e sem os pares da lista
  `configs/ids_imagem_nao_transcrita.txt`. Opções: `--manter-introducao`, `--manter-imagens`,
  `--excluir-ids <arquivo>` e `--sem-lista`.
- O `dividir_chunks.py` passou a escrever em `auxiliares/chunks_completo.jsonl` (antes escrevia no
  `chunks.jsonl`), e saiu dele a cópia automática na primeira execução, que não é mais necessária.
- O `chunks.jsonl` anterior (já com a correção do feijão-caupi) foi guardado como
  `auxiliares/chunks_completo.jsonl`. Rodar o filtro com `--manter-introducao --manter-imagens
  --sem-lista` reproduz esse arquivo byte a byte.
- Busca por pares cuja resposta depende de uma imagem que **não** foi transcrita: procurei nas
  respostas referências como "Tabela 1", "Figura 4" e "figura a seguir" e conferi o texto. Quase
  todas as tabelas citadas estão no texto (vieram como texto do ePub/PDF). Os casos em que a
  informação falta estão em `configs/ids_imagem_nao_transcrita.txt`: 5 claros (abacaxi q499,
  feijão-caupi q232, uva q160, suínos q424, trigo q427) e 4 de fronteira, comentados (feijão-caupi
  q236 e sementes q106, q135 e q367).
- READMEs atualizados (estrutura, números e o novo passo 3 do pipeline).

**Decisões**
- **Orientador:** por enquanto, o corpus deve ter só a parte da coleção que vem de texto. Saem as
  introduções e as perguntas cuja resposta veio de imagem, porque a transcrição foi feita com IA e não
  é reprodutível.
- A remoção é um filtro reversível: nada foi apagado. As transcrições continuam em
  `transcricoes_imagens.csv` e o corpus completo em `auxiliares/chunks_completo.jsonl`.
- O filtro decide pelo `id_original`, então as partes de um chunk dividido saem juntas.
- A Isabela confirmou que os 5 pares claros de imagem não transcrita também saem. A lista é aplicada
  por padrão; os 4 casos de fronteira ficaram comentados no arquivo e continuam no corpus.

**Números**
- Corpus completo: 20.887 chunks (20.595 ids originais).
- Removidos: 96 introduções e 113 pares com imagem transcrita (121 chunks, com as partes).
- Removidos também 5 pares com imagem não transcrita (5 chunks).
- Ficam: **20.665 chunks, 20.381 perguntas**, de 41 livros, todos `pergunta_resposta`.

**Pendências**
- Regenerar o índice E5 no Mac: `cd codigo && source .venv/bin/activate && python scripts/indexar.py`.
- O notebook de EDA e o golden set devem usar o `chunks.jsonl` filtrado (o EDA atual foi feito com o
  corpus completo).

---

## 14/11/2026 (sábado): dados brutos na pasta `dados/`

**Feito**
- As pastas `epub/`, `PDFs/` e `txt/` saíram da raiz de `500PerguntasRespostas/` e foram para uma
  nova pasta `500PerguntasRespostas/dados/`, com `git mv` (o git registra como renomeação, então o
  histórico dos arquivos continua). A `txt_reproduzido/`, que fica fora do git, foi junto, e o
  `.gitignore` foi ajustado. O `fontes.csv`, o checklist e o notebook de EDA ficaram onde estavam.
- Caminhos atualizados: `src/chunking.py` e `scripts/converter_para_txt.py` (nova constante
  `DADOS`), `fontes.csv` (coluna `arquivo_fonte`), `dados/PDFs/indice.csv` (colunas `arquivo` e
  `arquivo_txt`), `data/processed/transcricoes_imagens.csv` (coluna `fonte`), os dois READMEs,
  `docs/preparacao_dos_dados.md`, o ADR 0001 e o `data/raw/LEIAME.md`.
- Conferência: o `chunking.py --sem-divisao`, rodado numa pasta temporária, gerou
  `chunks_sem_imagens.jsonl` e `relatorio.csv` idênticos aos atuais. O `converter_para_txt.py`
  (`--sem-download`, algodão e abacaxi) achou as fontes e bateu 1.000 de 1.000 pares com os txt de
  `dados/txt/`. Todos os caminhos do `fontes.csv` e do `transcricoes_imagens.csv` existem. Nenhum
  arquivo fora deste diário aponta mais para os caminhos antigos.

**Decisões**
- Os caminhos nos CSVs continuam relativos a `500PerguntasRespostas/`, agora com o prefixo
  `dados/`. No `indice.csv`, os PDFs que apareciam só com o nome do arquivo (relativos a `PDFs/`)
  passaram a ter o caminho completo (`dados/PDFs/...`), como os outros.
- A pasta `codigo/data/raw/` continua só com o aviso, como decidido no ADR 0001 (não duplicar
  centenas de MB no OneDrive).
- As entradas antigas deste diário ficaram com os caminhos da época.
- O `indice.csv` listava três ePubs que nunca estiveram na pasta (caju 2015, feijão-caupi 2017 e
  ILPF 2015). Esses livros entram pelo PDF (como diz o `fontes.csv`), então as três linhas de ePub
  foram apagadas e ficou só a linha do PDF de cada um. O índice passou de 78 para 75 livros listados.
- Isso corrigiu um erro nos metadados: o `chunking.py` guarda a última linha do `indice.csv` para
  cada livro, e no feijão-caupi a última era a do ePub. Por isso os 506 chunks dele diziam
  `formato_origem: epub` e traziam a URL do ePub. Os campos `formato_origem` e `url_origem` desses
  chunks foram corrigidos (para `pdf` e a URL do PDF) no `chunks_sem_imagens.jsonl`, no
  `chunks_sem_divisao.jsonl` e no `chunks.jsonl`. O texto dos chunks não mudou, então o índice de
  embeddings continua valendo. O `chunking.py` rodado de novo gera um `chunks_sem_imagens.jsonl`
  idêntico ao corrigido. O `chunks_alterados.jsonl` (histórico) não tinha esse erro.

**Pendências**
- Fazer o commit da mudança (nada foi commitado).

---

## 14/11/2026 (sábado): histogramas sem buracos

**Feito**
- A Isabela notou barras faltando no histograma de palavras das perguntas, na seção 6.1 do
  `eda_500perguntas.ipynb`. A causa: `bins=50` dividia o intervalo de 2 a 45 palavras em faixas de
  0,86 palavra, e como a contagem é inteira, algumas faixas caíam entre dois inteiros e ficavam
  vazias.
- Nova função `faixas_inteiras` na célula de preparação: faixas de largura inteira, com as bordas no
  meio entre dois inteiros (ex.: 10,5 a 11,5). Usada em todos os histogramas de contagem
  (perguntas por capítulo, palavras de pergunta, resposta e texto, e tokens). O notebook foi
  executado de novo e ganhou uma explicação do problema logo abaixo do gráfico.

**Decisões**
- Largura de 1 quando o intervalo cabe em até 50 barras (perguntas); senão, a menor largura inteira
  que deixa no máximo 50 barras (respostas e texto) ou 60 (tokens).

**Pendências**
- A célula de tokens voltou a mostrar a estimativa, porque o notebook foi executado sem o
  tokenizador. Rodar a seção 6.2 de novo no Mac para voltar à contagem real.

---

## 10/11/2026 (terça à noite): análise exploratória dos chunks

**Feito**
- **Notebook `500PerguntasRespostas/eda_500perguntas.ipynb`** com a análise exploratória do
  `codigo/data/processed/chunks.jsonl`. Tem comentários didáticos em português (o que é cada
  gráfico, mediana, boxplot, escala log, Spearman, stopwords, TF-IDF) e foi executado, então as
  saídas já estão salvas.
- Seções: dicionário de dados, tipos de chunk e divisão em partes, livros (ano, formato, edição),
  checagem das perguntas 1 a 500, capítulos e grandes temas (com heatmap por livro), tamanho dos
  textos e tokens, tipos de pergunta, vocabulário e palavras características de cada livro,
  repetições, imagens transcritas, autores e um resumo.
- Precisa só de `pandas` e `matplotlib` (que ainda não estão no `requirements.txt`).
- **Página interativa no Claude** ("Corpus 500 Perguntas", privada) com os gráficos da EDA: números
  principais, chunks por livro, livros por ano, temas (barras e mapa de calor), palavras e tokens
  por chunk, tipos de pergunta e perguntas repetidas. Usa tabelas resumidas tiradas do notebook,
  não o `chunks.jsonl` inteiro, e segue o tema claro ou escuro de quem abre.
- **Checklist do Pi:** nova seção 1.5 (análise exploratória) e orientações para o golden set.
- **READMEs revisados:** o da pasta `Embrapa` ganhou a EDA e o `fontes.csv`; o do `codigo` ganhou
  os scripts de conversão e de inserção das transcrições, as dependências do notebook e a correção
  da seção de limitações (a conversão para txt já é feita por script).

**Decisões**
- A contagem de tokens usa o tokenizador do `multilingual-e5-small` se ele estiver em cache. Senão,
  usa a estimativa palavras × 1,6, que superestima alguns chunks (aparece máximo de 635 "tokens",
  mas a divisão real garante no máximo 512).
- Os grandes temas são uma classificação por palavra-chave no nome do capítulo, feita à mão. É
  aproximada. Na primeira versão, 28% das perguntas caíam em "Outros"; depois de listar os
  capítulos que sobravam e completar as palavras-chave (a pedido da Isabela), ficaram 2% (13
  capítulos genéricos, como "Generalidades"). As palavras-chave passaram a casar só no começo
  de uma palavra: antes, "raca" (raça) pegava "floração" e "integração".
- Tipos de pergunta: "Outros" tinha 30% porque a regra de "qual" estava errada (só pegava
  "quais"). Agora os padrões específicos vêm antes, cada trecho depois de vírgula é testado, e
  uma pergunta sem palavra interrogativa é classificada como sim ou não. Não sobra "Outros".
- Gráficos em modo escuro, com a chave `TEMA_ESCURO` na célula de preparação para voltar ao claro.

**Números**
- 20.887 chunks, 41 livros, 20.499 perguntas originais e 96 chunks de introdução.
- Cada livro tem entre 501 e 566 chunks (mediana 506): o corpus é equilibrado.
- 274 perguntas (1,3%) foram divididas em 2 ou mais chunks; 61 delas são do livro de ILPF.
- Mediana de 86 palavras por chunk; perguntas com mediana de 11 palavras e respostas com 67.
- 26 dos 41 livros são de 2013 (o mais antigo é de 2005, o mais novo de 2023).
- 646 capítulos (mediana de 27 perguntas cada); 458 nomes de capítulo diferentes.
- Temas: pragas, doenças e plantas daninhas 17%, plantio, manejo e sistemas de produção 15%,
  animais 14%, solo e adubação 11%. Só 2% das perguntas ficaram sem tema.
- Tipos de pergunta: escolha (qual/quais) 36%, sim ou não 22%, procedimento (como) 20%,
  definição 10%.
- 223 perguntas aparecem com texto igual em mais de um lugar (ex.: "O que é fertirrigação?" 9 vezes)
  e 24 chunks têm resposta idêntica a outro.
- 121 chunks com transcrição de imagem (mais em sementes e suínos).
- 1.145 autores; 20 capítulos sem autor listado (ovinos e suínos).

**Pendências**
- **Falta a pergunta 383 do livro de búfalos.** Conferir no original se é erro do livro ou da extração.
- No golden set, evitar perguntas repetidas entre livros (ou aceitar qualquer um dos ids como certo)
  e seguir a proporção de temas e de tipos de pergunta vista na EDA.
- Testar se livros parecidos se confundem na busca (gado de corte x gado de corte no Pantanal).
- Acrescentar `pandas`, `matplotlib` e `ipykernel` ao `requirements.txt`, se fizer sentido.
- Levar a análise para o Notion (página com o link da versão interativa, números e gráficos).
- Feito no mesmo dia: a Isabela rodou a seção de tokens com o tokenizador real. Média de 172 tokens
  por chunk (desvio padrão 94), mediana de 147 e máximo de exatamente 512: nenhum chunk passa do
  limite.

---

## 02 e 03/11/2026 (segunda à noite e terça): conversão para txt reproduzível

**Feito**
- O orientador pediu que a conversão dos livros para txt seja **reproduzível**. Antes ela tinha sido
  feita pelo Claude numa conversa, sem script.
- **Script `codigo/scripts/converter_para_txt.py`:** baixa cada livro pela URL da Infoteca, confere
  o SHA-256, converte e compara com os txt atuais. ePub → txt direto, **sem passar por PDF**
  (BeautifulSoup sobre o XHTML, na ordem do spine). PDF → txt com `pdftotext` + junção dos hífens
  discricionários (U+00AD).
- **`500PerguntasRespostas/fontes.csv`:** lista os 41 livros com a fonte de cada um (26 ePubs, 15
  PDFs), a URL e o hash. Os hashes dos 15 PDFs já estão preenchidos. Os dos ePubs são gravados no
  primeiro download.
- `requirements.txt` ganhou `beautifulsoup4==4.15.0` e `soupsieve==2.10`. A pasta
  `txt_reproduzido/` (saída de comparação) foi para o `.gitignore`.
- `codigo/docs/preparacao_dos_dados.md` e o `codigo/README.md` foram atualizados com a nova etapa.

**Decisões**
- Pular o PDF para os livros em ePub (pedido da Isabela).
- Cada livro usa a mesma fonte que gerou o txt atual. Oito livros têm ePub e PDF na Infoteca, mas
  continuam pelo PDF para não mudar os chunks.
- **Imagens:** as transcrições feitas com IA ficam como artefato versionado. Vai ser reproduzível o
  que vem antes e depois delas: extrair as imagens direto do ePub/PDF, guardar uma tabela com
  livro, arquivo da imagem, hash, id do chunk, âncora e transcrição, e um script que insere as
  transcrições nos chunks (substituindo o `chunks_alterados.jsonl` colado à mão). Feito no mesmo dia.
- Nos livros em ePub, as imagens agora vêm do próprio ePub, e não do PDF gerado na conversa com a IA.
- Uma figura do PDF de trigo (q494) é feita de 28 pedaços de imagem. Ela ficou registrada com todos
  os pedaços e um hash combinado.

- A Isabela rodou o script no Mac: os **26 ePubs foram baixados** para
  `500PerguntasRespostas/epub/` e os hashes gravados no `fontes.csv`. O extrator de ePub foi ajustado
  (tabelas, `<br>`, `<hr>`) até reproduzir os txt antigos.

**Números**
- **20.493 de 20.499 pares idênticos** aos txt antigos, e as 41 introduções iguais.
- PDFs: 7.500 de 7.500. As poucas linhas diferentes ficam no sumário (pontos de preenchimento, que
  variam com a versão do Poppler). Isso confirma que a conversão original desses livros foi
  `pdftotext`.
- ePubs: 12.993 de 12.999. Os 6 pares que mudam têm só diferença de quebra de linha, ou perdem um
  `•••` que tinha entrado por engano (hortas q409). Nenhum tem transcrição de imagem.

- **Txt substituídos** (decisão da Isabela): `txt/` agora é a saída do script
  (`--saida ../500PerguntasRespostas/txt`), com as versões das ferramentas em `txt/ferramentas.json`.
- **Chunks regenerados até antes da divisão:** `chunking.py --sem-divisao` gerou um novo
  `chunks_sem_imagens.jsonl`, e o `chunks_sem_divisao.jsonl` foi refeito trocando, pelo id, os 113
  chunks de `chunks_alterados.jsonl`. Mudam 7 chunks: os 6 da conversão e mamão q304, em que o
  arquivo antigo tinha "pinta-preta" corrigido à mão e o parser gera "pintapreta" (o PDF usa hífen
  discricionário ali). Ficou a saída do parser, sem correção manual.
- No Mac: `dividir_chunks.py` gerou o `chunks.jsonl` (20.887 chunks, como antes; só os 7 chunks
  esperados mudaram) e o `indexar.py` refez o índice `e5-small-fp32`.
- **Commit `446dbb4`** (22:52), com os 26 ePubs incluídos no repositório.
- **Imagens ligadas às fontes:** `data/processed/transcricoes_imagens.csv` tem as 140 transcrições,
  cada uma com a imagem de origem (no ePub ou no PDF), o SHA-256 da imagem, o id do chunk, a posição
  e a âncora. A tabela foi montada por `scripts/historico/ligar_transcricoes_imagens.py` (sem IA). O
  novo `scripts/inserir_transcricoes.py` insere as transcrições a partir dela e substitui a cópia
  manual do `chunks_alterados.jsonl`. O resultado é **idêntico byte a byte** ao
  `chunks_sem_divisao.jsonl`. Os hashes das 140 imagens foram conferidos também no Mac, com
  `--verificar-imagens` (pymupdf 2.1 entrou no `requirements.txt`).
- **Commit `486a7d5`** (23:23): imagens reproduzíveis.
- O `chunks_sem_imagens.jsonl` antigo estava desatualizado em relação ao `chunking.py` (5 pares
  diferentes, como milho q062 sem resposta). O novo bate com o parser atual.

**Pendências**
- Nenhuma pendência desta frente. A conversão e as imagens estão reproduzíveis.

---

## 29/10/2026 (quinta): repositório renomeado

**Feito**
- **Repositório no GitHub renomeado** de `IC-IAgro` para `IC-compressao-ir-agro-edge`. O novo
  endereço é `https://github.com/hissapinto/IC-compressao-ir-agro-edge`. O GitHub redireciona o
  nome antigo, mas o remoto local (`origin`) deve apontar para o novo.

**Decisões**
- O nome do repositório passa a refletir o tema da IC: compressão de modelos, recuperação de
  informação, domínio agrícola e execução na borda (celular/Pi).

---

## 27/10/2026 (terça): reorganização do código e primeiro índice

**Feito**
- **Cronograma da IC:** montado mês a mês, de set/2026 a ago/2027, conforme a vigência do Termo PIVIC
  ([link](https://claude.ai/artifact/M8M1Jr6bkyVdkDEg4fi91w)).
- **Conferência dos chunks:** o `chunks.jsonl` cobre 41 dos 44 PDFs. Os 3 que ficam de fora são
  edições antigas: milho 2011, feijão 2014 e mandioca 2006.
- **Búfalos q383:** a pergunta não existe no próprio livro, que pula da 382 para a 384, e por isso o
  livro tem 499 pares.
- **Conteúdo das imagens:** foram localizadas as 2.597 imagens dos 41 PDFs. Dessas, 140 têm
  informação (fórmulas, gráficos, fluxogramas, mapas) e foram transcritas em 113 respostas. Esses
  chunks receberam o campo `conteudo_imagem: true`.
- **Ambiente:** venv criado em `codigo/.venv`. O `.gitignore` já cobria a pasta, e o Pylance foi
  configurado em `.vscode/settings.json`.
- **Reorganização da pasta `codigo/`:** a estrutura agora tem `data/` (`raw`, `processed`, `golden`,
  `indices`), `src/`, `scripts/`, `configs/`, `results/`, `notebooks/` e `docs/adr/`. O
  `gerar_chunks.py` virou `src/chunking.py`.
- **ADR 0001** (`codigo/docs/adr/0001-estrutura-do-codigo.md`): registra a estrutura do código.
- **Divisão em 512 tokens:** a divisão foi implementada em `src/chunking.py` e em
  `scripts/dividir_chunks.py`. Cada parte repete o cabeçalho e ganha `id_original`, `parte` e
  `total_partes`.
- **Índice do E5:** gerado com `scripts/indexar.py`. A revisão conferiu norma 1, ausência de NaN e
  que o `ids.json` segue a ordem do `chunks.jsonl`.
- **Respostas vazias:** quatro estavam vazias (coco q499, mamão q304, milho q62 e pequenas frutas
  q54). Todas têm resposta no livro, e o erro era da extração. Foram corrigidas, e o parser também,
  para os dois casos (o `•••` antes da resposta e a pergunta que vem antes do número). Gerando tudo
  do zero, só os 5 chunks esperados mudaram.
- **READMEs:** escrito o README da pasta `Embrapa` (objetivo, as duas opções e a decisão) e
  detalhado o `codigo/README.md`.
- **Documentação da preparação dos dados:** `codigo/docs/preparacao_dos_dados.md` registra a
  conversão para txt e a transcrição das imagens, com o uso de IA em cada uma.
- **Diário:** criado este arquivo.
- **Commit `e6cbfac`** (22:35): README do código, documentação do uso de IA e este diário.

**Decisões**
- O objetivo final é o **celular do produtor rural** de pequeno e médio porte, sem internet. O Pi 4 é
  a bancada de testes, por ter recursos parecidos.
- A **opção 2** (livros 500 Perguntas, offline) é a base do projeto. A API Responde Agro fica como
  referência de comparação online.
- Os itens futuros ficam na seção "Caminhos em avaliação" do README, porque ainda não são certeza.
- Os prefixos `query: ` e `passage: ` do E5 ficam **no código**, e não gravados nos chunks.
- Os embeddings são gerados uma vez e salvos, e a busca só codifica a consulta. São dois scripts
  separados.
- O `codigo/data/indices/` fica fora do git, porque é regerável.
- As etapas feitas com IA (conversão e transcrição) ficam **só documentadas**, sem virar script. A
  saída delas é a referência.
- Fica no corpus só a edição mais recente de cada título.

**Números**
- 20.595 chunks antes da divisão: 20.499 pares e 96 trechos de introdução.
- 274 chunks passavam de 512 tokens e viraram 566 partes, então o total foi para 20.887 chunks.
- Índice: 20.887 × 384 em float32, cerca de 32 MB.
- Imagens: 2.597 localizadas, 140 transcritas, 113 respostas alteradas.

**Pendências**
- Datas exatas de entrega do relatório parcial, do artigo e da Jornada de IC 2027. O cronograma usa
  datas provisórias.
- Decidir se o gerador com fine-tuning entra no escopo do trabalho (combinar com o orientador).
- Se ainda existir, anexar o link da conversa em que o Claude converteu os PDFs para txt.
- Os PDFs antigos (milho 2011, feijão 2014, mandioca 2006) continuam em `PDFs/`. Decidir se ficam.
- Golden set, BM25 com FTS5, busca híbrida (RRF), `avaliar.py` e métricas.

---

## 24/10/2026 (sábado): escolha dos modelos

**Feito**
- **Checklist do Pi 4 clicável:** o checklist virou uma página com caixas que salvam o progresso
  ([link](https://claude.ai/artifact/4P2tRSaqXUYDa495cVYdiz)). Entrou nela o item "gerar os embeddings
  no Mac".
- **SLMs para o Pi 4:** levantamento de 7 geradores com prós e contras, em `SLMs_para_testar_no_Pi4.md`.
- **Modelos de embedding e gerador:** documento com critérios, candidatos, artigos de apoio e uma
  matriz de experimentos, a partir do pré-projeto e dos artigos da pasta
  (`Modelos_embedding_e_gerador.md` e `.pdf`, na pasta `Embrapa`).
- **Dúvidas respondidas:** as restrições da licença Gemma em relação a MIT/Apache; o E5 é da Microsoft
  Research, com licença MIT; e usar EmbeddingGemma com Gemma 3 não traz ganho de qualidade só por
  serem da mesma família.

**Decisões**
- O RAG tem **dois modelos**: um de embedding, para a recuperação, e um generativo, que
  provavelmente vai passar por fine-tuning no estilo das respostas da Embrapa.
- **Embedding:** o eixo principal é a família multilingual-E5 (small, base e large). Para comparar,
  entram o EmbeddingGemma-300M e o Serafim.
- **Gerador:** Qwen3 1.7B como principal e Qwen3 0.6B para testar o fine-tuning. A segunda família
  é o Gemma 3 1B ou o Llama 3.2.
- O fine-tuning ensina estilo e fidelidade aos trechos. O conhecimento vem da recuperação.
- Os dados de treino e de teste do gerador devem ser separados **por livro**, e não por pergunta.

**Pendências**
- Conferir os números arXiv e os autores das referências antes de citar (só três foram conferidos na
  web).
- Se o gerador entrar, definir métricas próprias para ele.

---

## 22/10/2026 (quinta): primeiro commit e checklist do Pi

**Feito**
- **Repositório git** criado na pasta `Embrapa`, com os commits `2937987` (primeiro commit) e
  `7dfe0ba` (PDFs movidos para `500PerguntasRespostas/PDFs/`).
- **Checklist do IR no Pi 4** (`500PerguntasRespostas/checklist_IR_pi4.md`), em 7 etapas: preparar o
  Pi, escolher o embedding, montar o índice, busca híbrida, avaliação, comparação com a Responde Agro
  e reprodutibilidade.
- **Como gerar os embeddings:** venv, `multilingual-e5-small`, prefixos `passage:`/`query:` e
  arquivos `embeddings.npy` + `ids.json`.

**Decisões**
- O trabalho pesado (embeddings e índice) roda uma vez no Mac. O Pi só recebe o índice pronto e
  codifica a consulta.
- O modelo de embedding sugerido é o `multilingual-e5-small`, rodando com ONNX no Pi.
- O armazenamento planejado é um SQLite com FTS5 para o BM25, mais os vetores numa matriz.

---

## 21/10/2026 (quarta, à noite): txt e chunks

**Feito**
- **Transcrição para txt:** 41 arquivos `.txt`, um por título, só da edição mais recente (23 vindos
  de ePub e 18 de PDF, nenhum precisou de OCR). Ficaram em `500PerguntasRespostas/txt/`.
- **Pasta do OneDrive completada** com os 26 PDFs convertidos e os txt. O `indice.csv` foi unificado
  em 78 linhas, com a coluna `arquivo_txt`.
- **Fichas das APIs:** receberam 16 exemplos de requisição e resposta nos endpoints relevantes.
- **Responde Agro:** é um sistema de IR (busca estilo Elasticsearch, provavelmente BM25) sobre os
  mesmos livros. A pergunta não precisa ser idêntica à do livro, e a API não gera respostas novas.
- **Chunking:** foi criado o `gerar_chunks.py`, que usa só a biblioteca padrão, com um parser para
  cada formato de txt (vindo de ePub ou de PDF). Ele extraiu 20.499 dos 20.500 pares e as
  introduções dos 41 livros, em 96 chunks. A saída é o `chunks.jsonl` mais o `relatorio.csv`.

**Decisões**
- O chunking é por estrutura do documento: **um chunk por par pergunta-resposta**, com cabeçalho
  `cultura | capítulo` no campo `texto`.
- O conteúdo pré-textual fica fora do índice (ficha técnica, catalogação, sumário). A **Introdução
  entra** como chunk com `tipo = introducao`, a pedido da autora.
- Metadados de cada chunk: id estável (ex.: `soja_2019_q215`), cultura, livro, ano, edição, capítulo,
  autores, número, pergunta, resposta e URL de origem.
- O código e o JSONL ficam no OneDrive. O venv e os bancos em escrita não deveriam ficar lá.

**Números**
- 41 livros × 500 = 20.500 pares esperados. Foram extraídos 20.499, porque búfalos q383 não existe
  no livro.

---

## 20/10/2026 (terça): início, as duas ideias e a coleta dos livros

**Feito**
- **Definição do teste de RI em duas ideias:**
  1. **APIs da Embrapa (AgroAPI):** usar IR para escolher o melhor endpoint para cada pergunta.
     Depende de internet.
  2. **RAG offline:** um dataset pequeno, dividido em chunks, com IR do trecho mais relevante. Roda
     no Raspberry Pi 4 (4 GB de RAM, microSD de 64 GB).
- **Fichas técnicas das 9 APIs** (AgroFit, Bioinsumos, BlueStarSting, RespondeAgro, SmartSolosExpert,
  AgroTermos, ClimAPI, Agritec e SATVeg), em `APIs/Fichas_tecnicas_APIs_Embrapa.md`, `.docx` e `.pdf`.
- **Levantamento de datasets** para o RAG offline, em `Datasets para RAG offline em culturas
  brasileiras.md` e `.pdf`. Não foi encontrado nenhum dataset pronto de perguntas e respostas sobre
  culturas em português.
- **Coleta da coleção 500 Perguntas** na Infoteca: 41 títulos. Os 26 ePubs foram convertidos para
  PDF, e no total ficaram 44 PDFs (cerca de 253 MB) e um `indice.csv`.
- **Erro de sincronização do OneDrive** (`_vendor/.lock`): não veio da pasta IC. O suspeito é um
  `.venv` de outra pasta do OneDrive.

**Decisões**
- A recomendação foi a coleção **500 Perguntas, 500 Respostas** como base. Cada par já é um chunk, e
  as próprias perguntas servem de gabarito para o MRR.
- A API Responde Agro busca nos mesmos livros, então dá para comparar a ideia 1 com a 2 usando as
  mesmas consultas.

**Pendências deixadas**
- Conferir no portal a URL base, a autenticação OAuth2 e o formato de busca da Responde Agro.
- Conferir a licença exata dos livros.

---

## Commits

| Data | Hash | Mensagem | Resumo |
| --- | --- | --- | --- |
| 22/10/2026 08:42 | `2937987` | fist commit | PDFs, txt, chunks, `gerar_chunks.py`, checklist, fichas das APIs, levantamento de datasets |
| 22/10/2026 08:51 | `7dfe0ba` | minor organization fix | PDFs movidos para `500PerguntasRespostas/PDFs/` |
| 27/10/2026 22:03 | `5017bc3` | Reorganiza código: estrutura src/scripts/data, divisão de chunks em 512 tokens e índice E5 | Nova estrutura de `codigo/`, ADR 0001, `chunks.jsonl` com 20.887 chunks, scripts de divisão, indexação e busca |
| 27/10/2026 22:13 | `81b5cac` | read me da pasta | README da pasta `Embrapa` |
| 27/10/2026 22:35 | `e6cbfac` | readme do código, docs de info de IA e diario | `codigo/README.md` detalhado, `codigo/docs/preparacao_dos_dados.md`, `DIARIO.md` e link no README |
| 02/11/2026 22:52 | `446dbb4` | Conversão reproduzível para txt: script ePub/PDF -> txt, fontes.csv com hashes, txt e chunks regenerados | `scripts/converter_para_txt.py`, `fontes.csv`, 26 ePubs, txt e chunks regenerados, índice refeito |
| 02/11/2026 23:23 | `486a7d5` | Imagens reproduzíveis: transcricoes_imagens.csv com hash das imagens e script de inserção | `transcricoes_imagens.csv`, `scripts/inserir_transcricoes.py`, `scripts/historico/ligar_transcricoes_imagens.py`, documentação |
| 10/11/2026 22:58 | `4f7bc63` | análise exploratória dos dados | `eda_500perguntas.ipynb` (EDA com modo escuro, temas e tipos de pergunta), checklist do Pi, READMEs e diário |
