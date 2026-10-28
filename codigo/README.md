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

No VS Code, selecione o interpretador `codigo/.venv/bin/python`. O arquivo
`../.vscode/settings.json` adiciona `codigo/src` ao caminho do Pylance, para que ele encontre os
imports dos scripts.

## Estrutura

```
codigo/
├── data/
│   ├── raw/                 aviso apontando para Embrapa/500PerguntasRespostas (PDFs e txt)
│   ├── processed/
│   │   ├── chunks.jsonl     corpus final usado em todo o resto (20.887 chunks)
│   │   └── auxiliares/      versões intermediárias e relatórios (ver "Dados")
│   ├── golden/              conjunto de avaliação (a construir)
│   └── indices/             um subdiretório por variante de modelo; fora do git
│       └── e5-small-fp32/   embeddings.npy + ids.json
├── src/                     biblioteca: só funções, nada roda ao importar
│   ├── chunking.py          extração dos pares pergunta-resposta e divisão por tokens
│   └── embeddings.py        load_model, encode (E5, mean pooling, normalização L2)
├── scripts/                 pontos de entrada; importam de src/
│   ├── dividir_chunks.py    divide o chunks.jsonl final em partes de até 512 tokens
│   ├── indexar.py           gera o índice de embeddings
│   └── buscar.py            busca densa pela linha de comando
├── configs/                 um .yaml por experimento (a construir)
├── results/                 métricas e tempos por experimento (a construir)
├── notebooks/               análises e gráficos
├── docs/adr/                registros de decisão de arquitetura
└── requirements.txt
```

A separação entre `src/` (o que é reutilizável) e `scripts/` (o que se executa) está justificada
na [ADR 0001](docs/adr/0001-estrutura-do-codigo.md).

## Dados

### Origem

Os 41 livros estão em `../500PerguntasRespostas/`. Os PDFs ficam em `PDFs/`, junto com o
`indice.csv`, que traz título, edição, formato de origem e URL de cada livro. Os textos extraídos
ficam em `txt/`. Os livros vêm em dois formatos de txt, e o `chunking.py` tem um parser para cada:

- **Formato A** (vindo de ePub): capítulos marcados como `• Capítulo N •` e perguntas como
  `N) texto`. Cada capítulo começa com a lista das perguntas, e depois elas se repetem com as
  respostas.
- **Formato B** (vindo de PDF): o número da pergunta aparece sozinho na linha, misturado com
  números de página, rodapés e quebras de página.

### `data/processed/chunks.jsonl`

Um JSON por linha. São 20.887 chunks de 41 culturas e temas: 20.791 pares pergunta-resposta (ou
partes deles) e 96 trechos de introdução.

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
| `conteudo_imagem` | `true` | Presente quando a resposta recebeu a transcrição de uma imagem |
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
| `chunks_sem_imagens.jsonl` | Saída do `src/chunking.py`, sem as transcrições de imagens |
| `chunks_alterados.jsonl` | Os 113 chunks que receberam transcrições de imagens |
| `imagens_transcritas.csv` | As 140 transcrições (`livro`, `pagina_pdf`, `transcricao`) |
| `chunks_sem_divisao.jsonl` | `chunks.jsonl` antes da divisão em 512 tokens (20.595 chunks); é a entrada do `dividir_chunks.py` |
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
500PerguntasRespostas/txt/*.txt
        │  src/chunking.py
        ▼
auxiliares/chunks_sem_imagens.jsonl
        │  transcrição das imagens (ver docs/preparacao_dos_dados.md)
        ▼
auxiliares/chunks_sem_divisao.jsonl
        │  scripts/dividir_chunks.py
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
python src/chunking.py                 # extrai e já divide em até 512 tokens (usa o tokenizer do E5)
python src/chunking.py --sem-divisao   # só extrai; roda sem o venv (biblioteca padrão)
```

Lê os txt e o `indice.csv` e escreve `auxiliares/chunks_sem_imagens.jsonl` e
`auxiliares/relatorio.csv`. **Não sobrescreve o `chunks.jsonl` final.** As opções são `--modelo`
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

Hoje, 274 chunks viram 566 partes.

Na primeira execução, o script copia o `chunks.jsonl` para `auxiliares/chunks_sem_divisao.jsonl`.
Depois, sempre lê dessa cópia, então pode ser rodado de novo (por exemplo, com outro `--limite`)
sem dividir duas vezes.

### 3. Gerar o índice: `scripts/indexar.py`

```bash
python scripts/indexar.py
python scripts/indexar.py --chunks data/processed/chunks.jsonl --saida data/indices/e5-small-fp32 --batch-size 32
```

Codifica o campo `texto` de todos os chunks com o prefixo `passage: `. Os chunks são processados
em ordem de tamanho, para reduzir o padding e acelerar, e o resultado volta para a ordem original
antes de ser salvo. Avisa se algum chunk passar de 512 tokens. Leva alguns minutos na CPU do Mac.

### 4. Buscar: `scripts/buscar.py`

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

- **Conversão PDF → txt e transcrição das imagens:** não são feitas por script neste repositório.
  O procedimento, o uso de IA e como reproduzir o resultado estão documentados em
  [`docs/preparacao_dos_dados.md`](docs/preparacao_dos_dados.md). Se o `chunking.py` for rodado de
  novo, as transcrições precisam ser reaplicadas a partir de `auxiliares/chunks_alterados.jsonl`.
- **Livros e perguntas faltando:** a coleção tem 44 PDFs, dos quais 41 entram no corpus. Alguns
  livros têm números de pergunta faltando no original. O `relatorio.csv` lista esses casos por
  livro.
- **Busca só densa por enquanto:** BM25, busca híbrida e avaliação ainda não estão implementados.
