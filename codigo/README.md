# Código: RAG offline sobre a coleção "500 Perguntas, 500 Respostas"

Pipeline de recuperação de informação da IC "Impacto da compressão de modelos de linguagem na
qualidade da recuperação da informação em domínio agrícola sob restrições de hardware". O contexto
do projeto (objetivo, opções consideradas, caminhos futuros) está no [README da pasta
Embrapa](../README.md).

Em resumo, o pipeline:
1. transforma os 41 livros da coleção em chunks (um por par pergunta-resposta);
2. gera os embeddings desses chunks uma única vez, no Mac;
3. busca os chunks mais parecidos com a pergunta do usuário, codificando só a consulta.

## Sumário

- [Ambiente](#ambiente)
- [Estrutura](#estrutura)
- [Dados](#dados)
- [Pipeline passo a passo](#pipeline-passo-a-passo)
- [Convenções](#convenções)
- [Limitações conhecidas](#limitações-conhecidas)

## Ambiente

Python 3.10 ou mais novo. Todos os comandos rodam **a partir desta pasta (`codigo/`)**, com o venv
ativo:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

As dependências principais são `torch`, `transformers` e `numpy`. Na primeira execução, o modelo
`intfloat/multilingual-e5-small` é baixado do Hugging Face e fica em cache em
`~/.cache/huggingface`. Depois disso, tudo funciona offline.

O notebook de análise exploratória (`notebooks/eda_500perguntas.ipynb`) usa também
`pandas`, `matplotlib` e `ipykernel`, que ainda não estão no `requirements.txt`:
`pip install pandas matplotlib ipykernel`.

O `converter_para_txt.py` precisa também do `pdftotext`, do Poppler (`brew install poppler` no Mac).

No VS Code, selecione o interpretador `codigo/.venv/bin/python`. O arquivo
`../.vscode/settings.json` adiciona `codigo/src` ao caminho do Pylance, para que ele encontre os
imports dos scripts.

## Estrutura

```
codigo/
├── data/
│   ├── raw/                 dados brutos: epub/, PDFs/, txt/, fontes.csv e indice.csv
│   ├── processed/
│   │   ├── chunks.jsonl     corpus usado na indexação: só pares de texto (20.665 chunks)
│   │   └── auxiliares/      versões intermediárias e relatórios (ver "Dados")
│   ├── golden/              conjunto de avaliação (a construir)
│   └── indices/             um subdiretório por variante de modelo; fora do git
│       └── e5-small-fp32/   embeddings.npy + ids.json
├── src/                     biblioteca: só funções, nada roda ao importar
│   ├── chunking.py          extração dos pares pergunta-resposta e divisão por tokens
│   └── embeddings.py        load_model, encode (E5, mean pooling, normalização L2)
├── scripts/                 pontos de entrada; importam de src/
│   ├── converter_para_txt.py   baixa os livros da Infoteca e converte ePub/PDF para txt
│   ├── dividir_chunks.py    divide os chunks em partes de até 512 tokens (corpus completo)
│   ├── filtrar_chunks.py    gera o chunks.jsonl a partir do corpus completo (filtro do corpus)
│   ├── indexar.py           gera o índice de embeddings
│   └── buscar.py            busca densa pela linha de comando
├── configs/                 configurações: ids_respostas_com_imagem.txt (lista do filtro); um .yaml por experimento (a construir)
├── results/                 métricas e tempos por experimento (a construir)
├── notebooks/               análises e gráficos (eda_500perguntas.ipynb: análise exploratória dos chunks)
├── docs/
│   ├── preparacao_dos_dados.md   como o corpus é gerado, passo a passo, e como reproduzir
│   └── adr/                 registros de decisão de arquitetura
└── requirements.txt
```

A separação entre `src/` (o que é reutilizável) e `scripts/` (o que se executa) está justificada
na [ADR 0001](docs/adr/0001-estrutura-do-codigo.md).

## Dados

### Origem

Os 41 livros estão em `data/raw/`: os ePubs em `epub/`, os PDFs em `PDFs/` e os textos extraídos
em `txt/`. O `fontes.csv` lista a fonte de cada livro, com URL e SHA-256, e o `indice.csv` traz
título, edição, formato de origem e URL de todos os livros da coleção baixados. Os livros vêm em dois formatos de txt, e o `chunking.py` tem um parser para cada:

- **Formato A** (vindo de ePub): capítulos marcados como `• Capítulo N •` e perguntas como
  `N) texto`. Cada capítulo começa com a lista das perguntas, e depois elas se repetem com as
  respostas.
- **Formato B** (vindo de PDF): o número da pergunta aparece sozinho na linha, misturado com
  números de página, rodapés e quebras de página.

### `data/processed/chunks.jsonl`

Um JSON por linha. São 20.665 chunks de 41 culturas e temas, todos pares pergunta-resposta (ou
partes deles), que correspondem a 20.381 perguntas.

**Filtro do corpus (decisão do orientador):** o corpus tem só os pares que vêm de texto. Ficam de
fora os 96 chunks de introdução e os 118 pares cuja resposta depende de uma imagem, listados em
`configs/ids_respostas_com_imagem.txt`: 113 cuja informação está numa fórmula, tabela ou figura que
só existe como imagem, e 5 que remetem a uma tabela ou figura ausente do texto. O corpus completo
(20.885 chunks) está em `auxiliares/chunks_completo.jsonl`, e o `scripts/filtrar_chunks.py` gera o
`chunks.jsonl` a partir dele (ver o passo 3 do pipeline). O valor `tipo = introducao` descrito abaixo
só aparece no corpus completo.

| Campo | Exemplo | Descrição |
| --- | --- | --- |
| `id` | `soja_2019_q245`, `sorgo_2015_q159_p2` | Identificador único. O sufixo `_pN` indica a parte de um chunk dividido |
| `id_original` | `sorgo_2015_q159` | Id antes da divisão (igual ao `id` quando o chunk não foi dividido) |
| `parte`, `total_partes` | `2`, `6` | Posição da parte e total de partes (1 e 1 quando não houve divisão) |
| `tipo` | `pergunta_resposta`, `introducao` | Tipo do chunk |
| `cultura` | `soja` | Tema do livro, tirado do nome do arquivo |
| `titulo_livro`, `ano`, `edicao` | | Metadados do livro (do `indice.csv`) |
| `capitulo_num`, `capitulo`, `autores_capitulo` | `5`, `"Doenças"`, `[...]` | Capítulo (0 = Introdução) |
| `numero_pergunta` | `245` | Número da pergunta no livro (`null` na introdução) |
| `pergunta`, `resposta` | | Texto original. Num chunk dividido, `resposta` é só o trecho daquela parte |
| `texto` | ver abaixo | **O que é codificado pelo modelo de embedding** |
| `formato_origem`, `url_origem`, `arquivo_txt` | | Rastreabilidade até o livro original |

O campo `texto` junta contexto e conteúdo, para que o vetor carregue também a cultura e o capítulo:

```
<cultura> | <capítulo>
Pergunta: <pergunta>
Resposta: <resposta>
```

Na introdução, o formato é `<cultura> | Introdução` seguido do texto. O prefixo `passage: ` do E5
**não** é gravado no arquivo. Ele é colocado na hora de codificar.

### `data/processed/auxiliares/`

| Arquivo | O que é |
| --- | --- |
| `chunks_sem_divisao.jsonl` | Saída do `src/chunking.py --sem-divisao`: pares e introduções antes da divisão em 512 tokens (20.595 chunks); é a entrada do `dividir_chunks.py` |
| `chunks_completo.jsonl` | Corpus completo já dividido (20.885 chunks, com introduções e pares que dependem de imagem); é a entrada do `filtrar_chunks.py` |
| `relatorio.csv` | Por livro: formato, pares extraídos, capítulos, respostas curtas e números faltando |

### `data/indices/<variante>/`

| Arquivo | O que é |
| --- | --- |
| `embeddings.npy` | Matriz `(n_chunks, dim)` em float32, com cada linha normalizada (norma 1) |
| `ids.json` | Lista de ids na mesma ordem das linhas da matriz: `ids[i]` é o chunk da linha `i` |

Os índices são regeráveis e ficam **fora do git** (`.gitignore`). Sempre que o `chunks.jsonl` mudar,
rode o `indexar.py` de novo.

## Pipeline passo a passo

```
ePub/PDF da Infoteca (data/raw/fontes.csv: URL e SHA-256 de cada livro)
        │  scripts/converter_para_txt.py   (ePub → txt direto; PDF → txt com pdftotext)
        ▼
data/raw/txt/*.txt
        │  src/chunking.py --sem-divisao
        ▼
auxiliares/chunks_sem_divisao.jsonl
        │  scripts/dividir_chunks.py
        ▼
auxiliares/chunks_completo.jsonl
        │  scripts/filtrar_chunks.py   (por padrão: tira introduções e os pares de configs/ids_respostas_com_imagem.txt)
        ▼
processed/chunks.jsonl
        │  scripts/indexar.py
        ▼
indices/e5-small-fp32/{embeddings.npy, ids.json}
        │  scripts/buscar.py "consulta"
        ▼
top-k chunks
```

### 1. Gerar os chunks: `src/chunking.py`

```bash
python src/chunking.py --sem-divisao   # só extrai; roda sem o venv (biblioteca padrão)
python src/chunking.py                 # extrai e já divide (atalho para o passo 2; usa o tokenizer do E5)
```

Lê os txt e o `indice.csv` e escreve `auxiliares/chunks_sem_divisao.jsonl` (ou, sem
`--sem-divisao`, direto o `auxiliares/chunks_completo.jsonl`) e `auxiliares/relatorio.csv`. **Não sobrescreve o `chunks.jsonl` final.** As opções são `--modelo`
(tokenizer usado na contagem) e `--limite` (padrão 512).

As funções de divisão (`dividir_chunks`, `contador_de_tokens`) também ficam neste módulo e são
reaproveitadas pelo `dividir_chunks.py`.

### 2. Dividir os chunks longos: `scripts/dividir_chunks.py`

```bash
python scripts/dividir_chunks.py
```

O E5 aceita no máximo 512 tokens, e o que passa disso é cortado sem aviso. Este script divide os
chunks que passam do limite. A contagem usa o tokenizer do modelo e inclui o prefixo `passage: ` e
os tokens especiais. Cada parte:
- repete o cabeçalho (cultura, capítulo e pergunta);
- leva um trecho da resposta, cortado em fim de parágrafo, depois em fim de frase e, em último caso,
  entre palavras.

No corpus completo, 272 chunks viram 562 partes. Depois do filtro, ficam 267 perguntas divididas.

A entrada é `auxiliares/chunks_sem_divisao.jsonl` e a saída é `auxiliares/chunks_completo.jsonl`,
então o script pode ser rodado de novo (por exemplo, com outro `--limite`) sem dividir duas vezes.

### 3. Filtrar o corpus: `scripts/filtrar_chunks.py`

```bash
python scripts/filtrar_chunks.py                                   # padrão: só pares de texto
python scripts/filtrar_chunks.py --manter-introducao --sem-lista   # corpus completo
```

Lê `auxiliares/chunks_completo.jsonl` e escreve o `chunks.jsonl`. Por padrão, tira as introduções e
os pares listados em `configs/ids_respostas_com_imagem.txt`. A decisão é sempre pelo `id_original`,
então as partes de um chunk dividido saem juntas. `--excluir-ids` troca o arquivo da lista (um
`id_original` por linha) e `--sem-lista` desliga a lista. A lista tem três grupos, marcados por
`# == ... ==`: 113 pares cuja informação está numa imagem, 5 que remetem a uma tabela ou figura
ausente do texto e 4 casos de fronteira, comentados (não saem do corpus). Roda sem o venv (biblioteca padrão). Depois de mudar o
filtro, gere o índice de novo.

### 4. Gerar o índice: `scripts/indexar.py`

```bash
python scripts/indexar.py
python scripts/indexar.py --chunks data/processed/chunks.jsonl --saida data/indices/e5-small-fp32 --batch-size 32
```

Codifica o campo `texto` de todos os chunks com o prefixo `passage: `. Os chunks são processados
em ordem de tamanho, para reduzir o padding e acelerar, e o resultado volta para a ordem original
antes de ser salvo. Avisa se algum chunk passar de 512 tokens. Leva alguns minutos na CPU do Mac.

### 5. Buscar: `scripts/buscar.py`

```bash
python scripts/buscar.py "como controlar a ferrugem na soja"
python scripts/buscar.py "como controlar a ferrugem na soja" -k 10 --cultura soja
```

Carrega o índice, codifica a consulta com o prefixo `query: ` e ordena os chunks pelo produto
escalar. Como os vetores são normalizados, isso equivale à similaridade de cosseno. Para cada
resultado, mostra o score, a cultura, o ano, o número da pergunta (e a parte, se for um chunk
dividido) e o começo da resposta. `--cultura` restringe a busca a um livro.

### Funções de `src/embeddings.py`

| Função | O que faz |
| --- | --- |
| `load_model(model_name)` | Carrega o tokenizer e o modelo do Hugging Face, em modo de avaliação |
| `average_pool(hidden, mask)` | Média dos vetores dos tokens, ignorando o padding (pooling do E5) |
| `encode(texts, tokenizer, model, prefix, batch_size=32, max_length=512)` | Embeddings normalizados (L2) em lotes; `prefix` é `"query: "` ou `"passage: "` |

## Convenções

- **Prefixos do E5:** ficam só no código (`encode(..., prefix=...)`): `passage: ` para os chunks e
  `query: ` para as consultas. Sem eles, a qualidade do E5 cai.
- **Uma pasta por variante:** cada índice fica em `data/indices/<modelo>-<precisão>/` (por exemplo,
  `e5-small-fp32`, `e5-small-int8`), e os resultados seguem o mesmo nome em `results/`. Isso mantém
  rastreável a comparação entre níveis de compressão.
- **Avaliação por pergunta:** como uma pergunta pode ter virado várias partes, a avaliação deve
  comparar pelo `id_original`. Qualquer parte da pergunta certa conta como acerto.
- **Dados finais protegidos:** scripts de reprocessamento escrevem em `auxiliares/`. O
  `chunks.jsonl` só muda por decisão explícita.
- **Novas decisões de arquitetura** viram ADRs numeradas em `docs/adr/`.

## Limitações conhecidas

- **Reprodutibilidade:** do ePub/PDF ao `chunks.jsonl`, tudo roda por script e sem IA. O
  `converter_para_txt.py` gera os 41 txt idênticos byte a byte aos de
  `data/raw/txt/` (com as versões de `data/raw/txt/ferramentas.json`; com outro `pdftotext`, mudam só
  linhas do sumário dos PDFs, e os pares não mudam), e o `chunking.py` gera `relatorio.csv` e
  `chunks_sem_divisao.jsonl` idênticos aos atuais. Nenhuma etapa usa IA.
- **Respostas que dependem de imagem:** os 118 pares cuja informação está numa imagem ficam fora do
  `chunks.jsonl` pela lista de `configs/`. O passo a passo da preparação está em
  [`docs/preparacao_dos_dados.md`](docs/preparacao_dos_dados.md).
- **Legado:** arquivos que não fazem parte do pipeline ficam em `../legado/`, com a mesma estrutura
  de pastas (ver `../legado/LEIAME.md`).
- **Livros e perguntas faltando:** `data/raw/` tem 26 ePubs e 44 PDFs (cópias em PDF dos ePubs e
  edições antigas), mas o corpus usa 41 livros: os 26 ePubs e 15 PDFs, listados no `fontes.csv`.
  O `relatorio.csv` mostra os números de pergunta faltando por livro; só falta um, a pergunta 383
  do livro de búfalos, que ainda precisa ser conferida no original.
- **Busca só densa por enquanto:** BM25, busca híbrida e avaliação ainda não estão implementados.
