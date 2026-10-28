# IC: RAG offline agrícola para o celular do produtor

Pasta de trabalho da IC **"Impacto da compressão de modelos de linguagem na qualidade da recuperação
da informação em domínio agrícola sob restrições de hardware"**.

O objetivo é que **produtores rurais de pequeno e médio porte** possam tirar dúvidas técnicas
**pelo próprio celular, sem internet**, usando recuperação de informação (RAG) sobre material da
Embrapa. Para isso, os modelos precisam caber e rodar bem num aparelho com pouca memória e
processamento.

O **Raspberry Pi 4 (4 GB)** é usado como **bancada de testes**: tem recursos parecidos com os de um
celular intermediário (CPU ARM, poucos GB de RAM, sem GPU utilizável para ML) e é mais fácil de
instrumentar e medir. A pergunta de pesquisa é quanto a compressão dos modelos (quantização,
modelos menores) afeta a qualidade da recuperação nessas condições.

## As duas opções consideradas

### Opção 1: APIs da Embrapa (AgroAPI), pasta `APIs/`

A AgroAPI oferece 9 APIs: Responde Agro, AgroFit, Bioinsumos, Agritec, ClimAPI, SATVeg,
AgroTermos, SmartSolos Expert e BlueStar Sting. Juntas, elas têm 141 endpoints. Nessa opção, o
sistema faria **roteamento por IR**: a partir da pergunta do produtor, escolheria a API e o
endpoint certos, preencheria os parâmetros e chamaria a API.

- **A favor:** dados oficiais e atualizados (defensivos registrados, Zarc, clima, NDVI).
- **Contra:**
  - Depende de internet, que muitas vezes não existe ou é instável no campo.
  - As APIs freemium só permitem de 100 a 500 requisições de teste.
  - Só 4 das 9 APIs aceitam texto livre; as outras pedem entradas estruturadas.
  - A autenticação e o formato de busca precisam ser confirmados no portal.

As fichas técnicas de cada API estão em
[`APIs/Fichas_tecnicas_APIs_Embrapa.md`](APIs/Fichas_tecnicas_APIs_Embrapa.md), e os PDFs da
documentação estão em `APIs/Gratis/` e `APIs/Freemium/`.

### Opção 2: Coleção "500 Perguntas, 500 Respostas", pasta `500PerguntasRespostas/`

Os livros da coleção são escritos por pesquisadores da Embrapa e respondem perguntas reais de
produtores. Nessa opção, eles viram a base de conhecimento local do RAG.

- **A favor:**
  - Roda 100% offline.
  - O texto já está em português e no registro do produtor.
  - Cada par pergunta-resposta é um chunk natural.
  - As próprias perguntas servem de ponto de partida para o conjunto de avaliação.
- **Contra:**
  - Conteúdo estático (livros de 2005 a 2023).
  - A extração dos PDFs exige cuidado: quebras de página, tabelas, imagens.
  - Licença não comercial: serve para a IC, mas os chunks não devem ser publicados.

O levantamento das fontes está em
[`Datasets para RAG offline em culturas brasileiras.md`](Datasets%20para%20RAG%20offline%20em%20culturas%20brasileiras.md).

### Decisão

A **opção 2** é a base do projeto, porque é a única que funciona offline no celular do produtor. A
API **Responde Agro**, que busca justamente nesses livros, fica como **referência de comparação
online**: as mesmas consultas são enviadas a ela e ao sistema offline, e os resultados são
comparados em qualidade, latência e dependência de rede.

## O que já está construído

Todo o código fica em [`codigo/`](codigo/README.md). As decisões de organização estão em
[`codigo/docs/adr/`](codigo/docs/adr/).

- **Corpus:** 41 livros da coleção (PDF/ePub, convertidos para txt), com metadados em
  `500PerguntasRespostas/PDFs/indice.csv`.
- **Chunking** (`codigo/src/chunking.py`): extrai 20.499 pares pergunta-resposta e 96 trechos de
  introdução. Cada chunk guarda cultura, livro, ano, capítulo, autores e número da pergunta.
- **Imagens:** 140 imagens com conteúdo (tabelas, receitas, esquemas) foram transcritas e incluídas
  nas respostas correspondentes.
- **Divisão em 512 tokens:** os chunks maiores que o limite do E5 são divididos em partes. Cada parte
  repete o cabeçalho (cultura, capítulo e pergunta). O resultado são 20.887 chunks em
  `codigo/data/processed/chunks.jsonl`.
- **Embeddings:** índice denso com o `intfloat/multilingual-e5-small` (384 dimensões, fp32, prefixos
  `passage:`/`query:`), gerado no Mac em `codigo/data/indices/e5-small-fp32/` (fora do git).
- **Busca densa** (`codigo/scripts/buscar.py`): busca por linha de comando, com filtro por cultura.

## Caminhos em avaliação

Os itens abaixo são direções possíveis, ainda não decididas. A ordem, o escopo e o que de fato
entra no trabalho dependem dos resultados intermediários e da conversa com o orientador.

1. **Busca lexical e híbrida:** BM25 com SQLite FTS5 e fusão com a busca densa por Reciprocal Rank
   Fusion (RRF).
2. **Conjunto de avaliação** (`codigo/data/golden/`): perguntas reescritas com outras palavras,
   algumas perguntas fora do escopo e o chunk correto de cada uma.
3. **Avaliação:** Recall@k, MRR@10 e nDCG@10, com ablações (BM25 × densa × híbrida, com e sem
   cabeçalho, com e sem introduções).
4. **Variantes comprimidas do embedding:** E5 small/base/large em FP32, FP16, INT8 e INT4 (ONNX), e
   possivelmente EmbeddingGemma-300M. Cada variante tem índice e resultados próprios.
5. **Execução no Raspberry Pi 4 (como proxy do celular):** ONNX Runtime, com medidas de latência
   (mediana e p95), RAM e tamanho do índice. Os formatos escolhidos (ONNX, GGUF) também rodam em
   Android e iOS, o que facilita levar o sistema para o celular depois.
6. **Comparação com a Responde Agro:** as mesmas consultas, enviadas à API online e ao sistema
   offline.
7. **Gerador (extensão):** um SLM (Qwen3 0.6B/1.7B, Gemma 3 1B ou Llama 3.2) com fine-tuning LoRA no
   estilo das respostas da Embrapa, quantizado em GGUF para rodar no aparelho. Os modelos candidatos estão discutidos em
   [`Modelos_embedding_e_gerador.md`](Modelos_embedding_e_gerador.md).

O passo a passo detalhado do Pi está em
[`500PerguntasRespostas/checklist_IR_pi4.md`](500PerguntasRespostas/checklist_IR_pi4.md).

## Estrutura da pasta

```
Embrapa/
├── 500PerguntasRespostas/   PDFs, txt e índice da coleção; checklist do Pi
├── APIs/                    documentação e fichas técnicas da AgroAPI (opção 1)
├── codigo/                  pipeline do RAG offline (ver codigo/README.md)
├── DIARIO.md                diário da pesquisa: o que foi feito em cada dia, decisões e pendências
├── Datasets para RAG offline em culturas brasileiras.md/.pdf   levantamento de fontes
└── Modelos_embedding_e_gerador.md/.pdf                         escolha dos modelos
```
