# Checklist: IR offline no Raspberry Pi 4

Ponto de partida: `chunks/chunks.jsonl`, com 20.595 chunks (20.499 pares pergunta-resposta e 96 trechos de introdução).
Hardware: Raspberry Pi 4 com 4 GB de RAM e microSD de 64 GB.

Ideia geral: o trabalho pesado (gerar os embeddings dos 20 mil chunks e montar o índice) é feito uma vez no Mac. O Pi só recebe o arquivo pronto e, a cada busca, gera o embedding da consulta e procura no índice.

## 1. Preparar o Pi
- [ ] Gravar o Raspberry Pi OS Lite 64 bits com o Raspberry Pi Imager, já com SSH ativado. O sistema precisa ser 64 bits, porque as bibliotecas de ML só têm versão para ARM64.
- [ ] Rodar `sudo apt update && sudo apt full-upgrade`.
- [ ] Instalar dissipador ou cooler. Sem isso, o Pi 4 reduz a velocidade quando esquenta, e isso distorce as medidas de latência.
- [ ] Criar um venv no Pi (aqui não há problema, porque o Pi não usa OneDrive): `python3 -m venv ~/ir && source ~/ir/bin/activate`.
- [ ] Confirmar que o SQLite do Python tem FTS5: `python3 -c "import sqlite3; sqlite3.connect(':memory:').execute('create virtual table t using fts5(x)'); print('ok')"`.
- [ ] Se faltar RAM ao carregar o modelo, ativar zram ou um swap pequeno.

## 2. Escolher o modelo de embedding
- [ ] Usar um modelo multilíngue pequeno, com bom português. Minha sugestão é o `intfloat/multilingual-e5-small` (384 dimensões, cerca de 118 milhões de parâmetros, cabe com folga). Uma alternativa para comparar é o `paraphrase-multilingual-MiniLM-L12-v2`. - Testar com variacoes de modelo
- [ ] Se usar o e5, colocar o prefixo `passage: ` nos chunks e `query: ` nas consultas. Sem isso, a qualidade cai.
- [ ] Verificar o limite de 512 tokens. Contar os tokens de cada `texto` e dividir os chunks que passarem (são cerca de 30 respostas acima de 3.000 caracteres), repetindo a pergunta em cada parte. - Testar com variacoes de tokens
- [ ] No Pi, rodar o modelo com ONNX Runtime, de preferência quantizado em int8, em vez de PyTorch. Isso economiza RAM e deixa a consulta mais rápida.
- [ ] Usar exatamente o mesmo modelo, versão e normalização no Mac e no Pi. Para conferir, gerar o embedding de algumas frases nos dois e comparar os vetores.

## 3. Montar o índice (no Mac)
- [ ] Script `indexar.py`: lê o `chunks.jsonl` e gera um arquivo `indice.db`.
  - tabela `chunks`: id, tipo, cultura, livro, ano, capítulo, número, pergunta, resposta, url
  - tabela virtual FTS5 `chunks_fts(pergunta, resposta, capitulo)` com `tokenize='unicode61 remove_diacritics 2'`, que ignora acentos
  - vetores normalizados em float32, guardados como BLOB numa tabela `vetores(id, emb)` ou num `.npy` ao lado. São cerca de 32 MB.
- [ ] Gerar o `.db` numa pasta local ou pausar a sincronização do OneDrive enquanto ele é escrito, e só depois copiar o arquivo final.
- [ ] Opcional: o FTS5 não tem stemmer para português. Se o BM25 errar por plural ou flexão, testar um stemmer (RSLP) aplicado antes de indexar.
- [ ] Copiar o `indice.db` (e o `.npy`, se usar) para o Pi com `scp`.

## 4. Busca híbrida (no Pi)
- [ ] BM25: as 50 melhores do FTS5, ordenadas por `bm25(chunks_fts)`.
- [ ] Densa: embedding da consulta, depois produto escalar com a matriz de vetores carregada na memória (busca exata com numpy, em milissegundos) e as 50 melhores.
- [ ] Fusão: Reciprocal Rank Fusion (`1/(60 + posição)`) somando as duas listas e devolvendo o top 10.
- [ ] Filtros opcionais: por `cultura` e por `tipo`, para incluir ou não a introdução.
- [ ] Interface: primeiro uma linha de comando (`buscar.py "como controlar ferrugem na soja"`). Depois, se quiser, uma API pequena (FastAPI ou Flask) acessível na rede local.
- [ ] Opcional: um reranker cross-encoder no top 10. Medir antes, porque no Pi pode ficar lento demais.

## 5. Avaliação
- [ ] Montar o conjunto de consultas de teste, com o gabarito sendo o id do chunk correto:
  - perguntas originais reescritas com outras palavras (200 a 300, sorteadas entre os livros). As perguntas idênticas às do livro deixam o teste fácil demais para o BM25.
  - perguntas reais de produtores, se conseguir (SAC, fóruns)
  - algumas fora do escopo, para ver como o sistema se comporta
- [ ] Métricas de qualidade: Recall@1, @5 e @10, MRR@10 e nDCG@10.
- [ ] Métricas do Pi: latência por consulta (mediana e p95), RAM usada, tamanho do índice e tempo para indexar.
- [ ] Comparações (ablação): só BM25, só densa e híbrida; com e sem prefixo de cultura/capítulo no `texto`; com e sem os chunks de introdução.
- [ ] Guardar as consultas, o gabarito e os resultados em arquivos versionados, para dar para reproduzir.

## 6. Comparação com a Responde Agro
- [ ] Ler a documentação da API: autenticação/chave, limites de requisição, termos de uso e formato da resposta.
- [ ] Enviar o mesmo conjunto de consultas e salvar as respostas brutas em JSON.
- [ ] Mapear os resultados dela para os seus ids (pelo texto da pergunta e pelo livro), para calcular as mesmas métricas. Se ela devolver uma resposta gerada em vez de trechos, definir como avaliar (por exemplo, se cita o par correto).
- [ ] Comparar também latência, dependência de internet e custo, que são o argumento a favor do offline no Pi.

## 7. Reprodutibilidade
- [ ] Colocar os scripts (`gerar_chunks.py`, `indexar.py`, `buscar.py`, `avaliar.py`) num repositório git.
- [ ] Anotar as versões do modelo, das bibliotecas e do sistema do Pi, além do hardware.
