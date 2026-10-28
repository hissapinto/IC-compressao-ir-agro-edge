# Diário da pesquisa

Registro do que foi feito na IC, dia a dia: o que foi feito, as decisões, os números e o que ficou
pendente. As entradas mais recentes ficam no topo. Os horários são de Brasília.

**Como manter:** ao fim de cada dia de trabalho, e a cada commit, acrescentar ou atualizar a entrada
do dia. Uma entrada tem quatro partes: *Feito*, *Decisões*, *Números* e *Pendências*. Quando um
commit entra, ele vai para a tabela de commits no fim do arquivo.

## Estado atual (28/10/2026)

- **Corpus:** 41 livros da coleção *500 Perguntas, 500 Respostas*, transformados em 20.887 chunks
  de até 512 tokens (`codigo/data/processed/chunks.jsonl`).
- **Índice:** `multilingual-e5-small` em fp32, com 20.887 × 384 vetores, em
  `codigo/data/indices/e5-small-fp32/`. Foi regenerado depois das últimas correções dos chunks.
- **Busca:** só densa, pela linha de comando (`scripts/buscar.py`).
- **Próximo passo que destrava o resto:** o conjunto de avaliação (golden set).

---

## 27/10/2026 (segunda): reorganização do código e primeiro índice

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
- Commitar o `codigo/README.md` detalhado, o `docs/preparacao_dos_dados.md` e este diário.
- Se ainda existir, anexar o link da conversa em que o Claude converteu os PDFs para txt.
- Os PDFs antigos (milho 2011, feijão 2014, mandioca 2006) continuam em `PDFs/`. Decidir se ficam.
- Golden set, BM25 com FTS5, busca híbrida (RRF), `avaliar.py` e métricas.

---

## 24/10/2026 (sexta): escolha dos modelos

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

## 22/10/2026 (quarta): primeiro commit e checklist do Pi

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

## 21/10/2026 (terça, à noite): txt e chunks

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

## 20/10/2026 (segunda): início, as duas ideias e a coleta dos livros

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
