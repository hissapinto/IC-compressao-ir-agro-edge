# Guia do projeto: tudo o que você precisa saber

Este guia explica o projeto do começo ao fim, em linguagem simples: o que ele quer resolver, o que
cada parte do código faz, por que as decisões foram tomadas e o que significa cada termo técnico. A
ideia é ler na ordem uma vez e depois voltar ao **glossário** (seção 9) sempre que um termo aparecer.

Sumário
1. O projeto em uma página
2. Como uma busca funciona (a ideia central)
3. O pipeline, etapa por etapa
4. Os arquivos de dados
5. Organização das pastas
6. Decisões tomadas e por quê
7. Como rodar e como conferir
8. Conceitos em detalhe: normalização, anisotropia, métricas e tipos de métricas
9. Glossário
10. Perguntas frequentes

---

## 1. O projeto em uma página

**Problema.** Produtores rurais de pequeno e médio porte têm dúvidas técnicas (pragas, plantio,
manejo) e muitas vezes estão em lugares sem internet.

**Ideia.** Colocar no celular do produtor um sistema que, dada uma pergunta, encontra a resposta
certa nos livros da Embrapa, **sem internet**. Isso se chama *recuperação de informação* (IR). Se
depois um modelo de linguagem escrever uma resposta a partir do que foi encontrado, o sistema todo
vira um *RAG*.

**Base de conhecimento.** A coleção *500 Perguntas, 500 Respostas* da Embrapa: 41 livros, cada um
com cerca de 500 perguntas reais de produtores, respondidas por pesquisadores. Cada par
pergunta-resposta vira um **chunk** (um pedaço que o sistema pode devolver).

**Pergunta de pesquisa.** Celulares têm pouca memória e processamento. Para caber, os modelos
precisam ser **comprimidos** (quantização, modelos menores). A IC mede **quanto a compressão piora a
qualidade da busca**, e quanto ela ganha em velocidade e memória.

**Bancada de testes.** Um **Raspberry Pi 4** (4 GB de RAM), que tem recursos parecidos com os de um
celular intermediário e é fácil de medir.

**Onde estamos.** O corpus está pronto (20.665 chunks, gerados de forma 100% reproduzível), a busca
densa funciona pela linha de comando no Mac e já existe um **conjunto de avaliação** (golden set, em
revisão) com a medição do índice: com as perguntas reescritas com outras palavras, a resposta certa
aparece entre as 10 primeiras em 79% dos casos (MRR@10 de 0,62); com as consultas vagas, em 54%. Os resultados e os caminhos
futuros estão em [`futuro_da_pesquisa.md`](futuro_da_pesquisa.md).

---

## 2. Como uma busca funciona (a ideia central)

O computador não entende texto, mas sabe comparar números. Então:

1. **Uma vez, no Mac (indexação):** cada chunk passa por um modelo de linguagem (o E5), que o
   transforma num **vetor**: uma lista de 384 números que resume o *significado* do texto. Textos
   sobre o mesmo assunto ficam com vetores parecidos, mesmo que usem palavras diferentes. Os 20.665
   vetores são salvos num arquivo (o **índice**).
2. **A cada pergunta (busca):** a pergunta do usuário passa pelo mesmo modelo e vira outro vetor.
3. **Comparação:** o vetor da pergunta é comparado com os 20.665 vetores salvos. Cada comparação dá
   um **score** (quanto mais alto, mais parecido).
4. **Resultado:** os chunks com maior score (o *top-k*) são devolvidos ao usuário.

Analogia: o chunk é o livro na estante; o vetor é a ficha de catálogo que diz onde ele fica pelo
assunto. A busca procura nas fichas, mas o usuário recebe o livro.

O trabalho pesado (passo 1) é feito uma vez só. Na hora da busca, só a pergunta é transformada em
vetor, e é isso que permite rodar no Pi ou no celular.

**Prefixos `passage:` e `query:`.** O E5 foi treinado com pares "pergunta curta × trecho que
responde". Para ele saber o papel de cada texto, os chunks recebem `passage: ` na frente e as
perguntas recebem `query: `. Sem os prefixos, a qualidade cai. Eles não ficam gravados no arquivo:
são postos na hora de codificar.

**Por que a pergunta original fica dentro do chunk.** O vetor de cada chunk é feito com cultura,
capítulo, pergunta e resposta juntos. A pergunta do usuário tende a se parecer mais com a pergunta do
livro do que com a resposta ("quando plantar soja no cerrado?" combina com "Qual a época de semeadura
da soja no Cerrado?"). Na tela, dá para mostrar só a resposta, porque `pergunta` e `resposta` são
campos separados.

---

## 3. O pipeline, etapa por etapa

*Pipeline* é a sequência de etapas que transforma os livros no índice de busca. Cada etapa lê o
arquivo da anterior e grava o seu. Todos os comandos rodam de dentro da pasta `codigo/`.

```
[1] ePubs e PDFs (data/raw/epub, data/raw/PDFs)
      │ scripts/converter_para_txt.py
[2] um txt por livro (data/raw/txt)
      │ src/chunking.py --sem-divisao
[3] um chunk por pergunta (auxiliares/chunks_sem_divisao.jsonl, 20.595)
      │ scripts/dividir_chunks.py
[4] chunks de até 512 tokens (auxiliares/chunks_completo.jsonl, 20.885)
      │ scripts/filtrar_chunks.py
[5] corpus final, só pares de texto (data/processed/chunks.jsonl, 20.665)
      │ scripts/indexar.py
[6] índice de vetores (data/indices/e5-small-fp32)
      │ scripts/buscar.py "pergunta"
    resultados

Avaliação:
[5] corpus final
      │ scripts/sortear_golden.py  (+ variações escritas com LLM e revisadas)
[7] conjunto de avaliação (data/golden)
      │ scripts/avaliar.py  (usa também o índice [6])
[8] métricas e tabelas (results/e5-small-fp32)
      │ notebooks/avaliacao_busca.ipynb
    gráficos e explicação das métricas
```

### [1] → [2] Converter os livros em texto: `converter_para_txt.py`
- **Baixar:** se um livro não está na pasta, baixa da Infoteca pela URL do `fontes.csv`.
- **Conferir:** calcula o **SHA-256** de cada arquivo e compara com o do `fontes.csv`. Se bater, é
  exatamente o mesmo arquivo usado antes.
- **ePub → txt:** o ePub é um zip com páginas HTML. O script lê as páginas na ordem do livro e tira o
  texto com o **BeautifulSoup**, um bloco (parágrafo, título, item) por vez.
- **PDF → txt:** usa o programa **pdftotext**, e junta as palavras que o livro quebrou com hífen no
  fim da linha.
- Grava em `data/raw/txt/ferramentas.json` as versões usadas. Com as mesmas versões, os txt saem
  idênticos byte a byte.
- Por que ePub quando existe: o texto sai limpo, sem números de página e quebras do PDF. Dos 41
  livros, 26 vêm de ePub e 15 de PDF.

### [2] → [3] Separar as perguntas: `src/chunking.py --sem-divisao`
- Lê cada txt e descobre o formato: **A** (veio de ePub, tem "• Capítulo N •") ou **B** (veio de PDF).
- Cada formato tem um *parser* (leitor) próprio, que acha capítulos, perguntas e respostas:
  - **Formato A:** perguntas no formato `15) texto`. Cada capítulo começa com a lista das perguntas;
    depois elas se repetem, cada uma seguida da resposta.
  - **Formato B:** o número da pergunta aparece sozinho na linha, misturado com números de página e
    rodapés. O parser usa várias regras para não confundir número de página com número de pergunta.
- Também extrai a **introdução** de cada livro (que depois sai do corpus).
- Grava `chunks_sem_divisao.jsonl` e o `relatorio.csv` (conferência por livro: quantos pares,
  capítulos e números faltando; só falta a pergunta 383 do livro de búfalos).

### [3] → [4] Dividir os chunks longos: `dividir_chunks.py`
- O E5 lê no máximo **512 tokens**; o que passar disso é cortado sem aviso.
- O script conta os tokens de cada chunk com o **tokenizer** do E5. Os que passam do limite viram
  partes: cada parte repete o cabeçalho (cultura, capítulo, pergunta) e leva um trecho da resposta,
  cortado em fim de parágrafo, de frase ou, em último caso, entre palavras.
- As partes ganham id `..._p1`, `..._p2` e mantêm o mesmo `id_original`. Assim continuam ligadas à
  mesma pergunta.
- No corpus final, 267 perguntas foram divididas (de 2 a 6 partes).

### [4] → [5] Filtrar o corpus: `filtrar_chunks.py`
- Tira as **96 introduções** e os **118 pares cuja resposta depende de uma imagem** (lista em
  `configs/ids_respostas_com_imagem.txt`).
- A decisão é pelo `id_original`, então as partes de uma resposta dividida saem juntas.
- Nada é apagado: o corpus completo continua em `chunks_completo.jsonl`, e o filtro pode ser
  desligado (`--manter-introducao --sem-lista`).

### [5] → [6] Gerar o índice: `indexar.py`
- Lê o `texto` de cada chunk, põe `passage: ` na frente e gera um vetor de 384 números com o E5.
- Processa em **lotes** de 32, ordenados por tamanho (mais rápido), e depois volta à ordem original.
- Salva `embeddings.npy` (matriz 20.665 × 384, cerca de 32 MB) e `ids.json` (o id do chunk de cada
  linha).
- Precisa rodar de novo sempre que o `chunks.jsonl` mudar.

### Busca: `buscar.py`
- Transforma a pergunta em vetor (`query: `), multiplica pela matriz (um score por chunk), ordena e
  mostra os k melhores. `--cultura soja` restringe a um livro.

### [5] → [7] Sortear o conjunto de avaliação: `sortear_golden.py`
- Sorteia 5 perguntas de cada livro (205 no total), sempre com a mesma semente (42), e grava
  `data/golden/amostra.csv` com a pergunta e a resposta.
- Cada pergunta ganha mais seis versões, escritas com LLM e revisadas à mão, todas com **o mesmo
  gabarito** (`id_original`): três **reescritas** (mesmo sentido, outras palavras) e três **vagas** (o
  que alguém que não sabe bem o que procurar digitaria). Em cada trio, uma versão usa o termo do
  livro, outra é a revisada no estilo da Isabela e outra só descreve, sem o termo. Ficam lado a lado
  em `pares.csv`.
- Na avaliação, primeiro se faz a média das três versões de cada pergunta e depois a média entre as
  perguntas. O **pior caso** (*worst-case*: em cada pergunta, a versão em que a busca foi pior) mede a robustez:
  o quanto o resultado depende de como a pessoa escreve.
- `fora_do_escopo.csv` tem 100 consultas sem resposta nos livros: 50 de outro assunto e 50 de
  agricultura fora dos 41 livros.

### [6] + [7] → [8] Avaliar: `avaliar.py`
- Codifica todas as consultas, compara com os 20.665 chunks e anota em que posição a pergunta certa
  apareceu (seção 8.3).
- Mede também o score do 1º colocado e a diferença para o 2º, e o quanto eles separam as consultas
  válidas das fora do escopo (AUROC, seção 8.3).
- Grava tabelas e um `resumo.md` em `results/e5-small-fp32/`.
- Os gráficos ficam no notebook `notebooks/avaliacao_busca.ipynb`, que lê essas tabelas e explica
  cada métrica.

### Funções de apoio: `src/embeddings.py`
- `load_model`: carrega o tokenizer e o modelo E5.
- `encode`: põe o prefixo, tokeniza, roda o modelo, faz a média dos vetores dos tokens (*mean
  pooling*) e normaliza o resultado.

### Funções de apoio: `src/avaliacao.py`
- Ranking por `id_original` (cada pergunta aparece uma vez, na posição da sua melhor parte), MRR,
  Recall, intervalo de confiança por bootstrap, AUROC e curva ROC.

---

## 4. Os arquivos de dados

### `.jsonl` (JSON Lines)
Um objeto JSON por linha. Cada linha do `chunks.jsonl` é um chunk, por exemplo:

```json
{
  "id": "soja_2019_q245",
  "id_original": "soja_2019_q245",
  "parte": 1, "total_partes": 1,
  "tipo": "pergunta_resposta",
  "cultura": "soja",
  "titulo_livro": "Soja: o produtor pergunta, a Embrapa responde.",
  "ano": 2019, "edicao": "1. ed.",
  "capitulo_num": 11, "capitulo": "Manejo de Plantas Daninhas",
  "autores_capitulo": ["Dionisio Luiz Pisa Gazziero", "..."],
  "numero_pergunta": 245,
  "pergunta": "Quais são as espécies de cobertura do solo que possuem maior capacidade de reduzir a infestação de plantas daninhas na cultura da soja?",
  "resposta": "Na região Sul do Brasil, espécies como azevém, aveia-preta e centeio...",
  "texto": "soja | Manejo de Plantas Daninhas\nPergunta: Quais são...\nResposta: Na região Sul...",
  "formato_origem": "pdf",
  "url_origem": "https://www.infoteca.cnptia.embrapa.br/...",
  "arquivo_txt": "500P_soja_2019.txt"
}
```

- `id`: identificador único (cultura_ano_qNÚMERO; `_pN` se for parte de uma resposta dividida).
- `id_original`: o id antes da divisão; é ele que liga as partes à pergunta.
- `texto`: **o que vira vetor**. Os outros campos são metadados (para mostrar e rastrear).

### `.csv`
Tabela em texto, com colunas separadas por vírgula. O `fontes.csv` diz de onde vem cada livro (URL e
hash); o `indice.csv` traz título, ano e edição; o `relatorio.csv` confere a extração.

### `.npy` e `ids.json`
O `.npy` é uma matriz de números do NumPy (o índice). O `ids.json` é a lista de ids na mesma ordem: a
linha *i* da matriz é o chunk `ids[i]`.

### `.ipynb`
Notebook do Jupyter: código, gráficos e texto juntos. O da EDA está em `codigo/notebooks/`.

---

## 5. Organização das pastas

```
Embrapa/
├── codigo/                 tudo que roda
│   ├── src/                funções reutilizáveis (chunking.py, embeddings.py, avaliacao.py)
│   ├── scripts/            um script por etapa do pipeline
│   ├── configs/            lista de ids que saem do corpus
│   ├── data/
│   │   ├── raw/            dados brutos: epub/, PDFs/, txt/, fontes.csv, indice.csv
│   │   ├── processed/      chunks.jsonl (corpus final) e auxiliares/ (intermediários)
│   │   ├── indices/        índice de vetores (fora do git, regerável)
│   │   └── golden/         conjunto de avaliação (pares.csv, fora_do_escopo.csv)
│   ├── notebooks/          análise exploratória (EDA) e análise da avaliação
│   ├── docs/               preparação dos dados e ADRs
│   └── results/            resultados de avaliação, uma pasta por variante do índice
├── docs/                   diário, checklist do Pi, pesquisas, este guia
├── APIs/                   fichas das APIs da Embrapa
└── legado/                 o que saiu do pipeline, guardado como registro
```

- **`src/` × `scripts/`:** `src/` só tem funções (nada roda ao importar); `scripts/` são os programas
  que você executa. A razão está na ADR 0001 (`codigo/docs/adr/`).
- **`legado/`:** material antigo (transcrições das imagens feitas com IA, txt antigos), com a mesma
  estrutura de pastas. Não é usado pelo pipeline.
- **Diário (`docs/DIARIO.md`):** o histórico de tudo o que foi feito. Os outros documentos descrevem
  só o estado atual.

---

## 6. Decisões tomadas e por quê

| Decisão | Por quê |
| --- | --- |
| Usar a coleção 500 Perguntas, e não as APIs da Embrapa | Funciona 100% offline, está em português e no registro do produtor, cada par já é um chunk natural, e as perguntas servem de base para a avaliação. As APIs dependem de internet. |
| Um chunk por par pergunta-resposta | É a unidade natural do livro: uma dúvida, uma resposta. |
| ePub quando existe, PDF só quando não há | O texto do ePub sai limpo; o do PDF tem números de página, rodapés e quebras. |
| Pipeline 100% reproduzível, sem IA | Qualquer pessoa chega aos mesmos arquivos; diferenças nos resultados vêm do experimento, não dos dados. |
| Tirar introduções e respostas que dependem de imagem | Decisão do orientador, oficial até segunda ordem. As transcrições de imagem foram feitas com IA e não são reproduzíveis. O filtro é reversível. |
| Dividir em 512 tokens repetindo o cabeçalho | O E5 corta o que passa de 512 tokens; repetir a pergunta mantém cada parte encontrável. |
| `multilingual-e5-small` como modelo base | Pequeno (cerca de 118 milhões de parâmetros), bom em português e com versões base e large para comparar. |
| Indexar no Mac, buscar no Pi | O trabalho pesado é feito uma vez; o aparelho só codifica a consulta. |
| Responde Agro como referência | É a API da Embrapa que busca nos mesmos livros; serve para comparar o sistema offline com o online. |

---

## 7. Como rodar e como conferir

```bash
cd codigo
source .venv/bin/activate                    # ativa o ambiente com as bibliotecas

python scripts/converter_para_txt.py --sem-download   # [1]→[2] (precisa do pdftotext)
python src/chunking.py --sem-divisao                   # [2]→[3]
python scripts/dividir_chunks.py                       # [3]→[4]
python scripts/filtrar_chunks.py                       # [4]→[5]
python scripts/indexar.py                              # [5]→[6]
python scripts/buscar.py "como controlar a ferrugem na soja" -k 5
python scripts/sortear_golden.py                       # [5]→[7] (o sorteio já está feito)
python scripts/avaliar.py                              # [6]+[7]→[8]; gráficos em notebooks/avaliacao_busca.ipynb
```

Para conferir que a conversão reproduz os txt sem sobrescrever nada:

```bash
python scripts/converter_para_txt.py --sem-download --saida /tmp/txt --comparar-com data/raw/txt
```

O resultado esperado é "20499 de 20499 pares idênticos aos atuais".

---

## 8. Conceitos em detalhe: normalização, anisotropia, métricas e tipos de métricas

### 8.1 Normalização L2

**O que é.** Todo vetor tem um *comprimento* (a norma L2): a raiz da soma dos quadrados dos seus
números. Normalizar é dividir cada número do vetor por esse comprimento, para o vetor ficar com
tamanho 1 sem mudar a direção.

Exemplo com 2 dimensões (os nossos têm 384, mas a conta é a mesma):

```
v = [3, 4]
comprimento = raiz(3² + 4²) = raiz(25) = 5
v normalizado = [3/5, 4/5] = [0,6; 0,8]     → comprimento 1
```

Pense numa seta: normalizar mantém para onde ela aponta e só ajusta o tamanho dela para 1.

**Para que serve.** Sim, a razão principal é facilitar o cosseno, mas isso traz várias vantagens:

1. **O produto escalar vira o cosseno.** A fórmula do cosseno é
   `cos(a, b) = (a · b) / (|a| × |b|)`. Se os dois vetores têm tamanho 1, o denominador é 1 e sobra
   só `a · b`. Não é preciso calcular comprimentos a cada busca.
2. **A busca vira uma multiplicação de matrizes.** Com todos os vetores normalizados, comparar a
   consulta com os 20.665 chunks é uma única conta (`embs @ consulta`), muito rápida inclusive no Pi.
3. **Evita viés de magnitude.** Sem normalizar, textos que geram vetores "mais compridos" (por
   exemplo, mais longos) ganhariam scores maiores no produto escalar sem serem mais relevantes. Com
   tamanho 1, só a direção (o significado) conta.
4. **Compatível com as ferramentas de busca e com a quantização.** Bibliotecas de busca vetorial
   (FAISS, sqlite-vec) trabalham com produto escalar sobre vetores normalizados, e números dentro de
   uma faixa conhecida (entre −1 e 1) são mais fáceis de quantizar para INT8.
5. **Foi assim que o E5 foi treinado.** O modelo aprendeu comparando vetores normalizados; usar do
   mesmo jeito mantém a qualidade.

**O que ela não faz.** A normalização **não muda a ordem do ranking** pelo cosseno, porque o cosseno
já ignora o tamanho dos vetores. Ela também não "desensibiliza" nem separa melhor os textos. Para
isso existem outras técnicas (ver anisotropia, a seguir).

### 8.2 Anisotropia: por que todos os scores são altos

**O que é.** Cada chunk vira um vetor de 384 números; dá para imaginá-lo como uma seta. O cosseno
mede o ângulo entre duas setas: 1 = mesma direção (textos iguais), 0 = perpendiculares (sem
relação). Num espaço **isotrópico** (*isotropic*), as setas apontam para todos os lados por igual, e
dois textos sem relação teriam cosseno perto de 0. Na prática, modelos como o E5 colocam **todos** os
vetores dentro de um **cone** estreito: eles apontam mais ou menos para a mesma região. Isso se chama
**anisotropia** (*anisotropy*: o espaço não é usado por igual em todas as direções). Resultado: até
textos sem relação nenhuma parecem bastante "parecidos" pelo cosseno.

**Como medimos.** O `avaliar.py` calcula dois números:
- **Cosseno médio entre chunks sorteados: 0,81.** São 5.000 pares de chunks escolhidos ao acaso, que
  quase nunca têm relação entre si. Num espaço isotrópico, a média seria perto de 0; aqui é 0,81.
- **Norma do vetor médio do corpus: 0,90.** Faz-se a média dos 20.665 vetores. Cada um tem tamanho
  (**norma**) 1. Se apontassem para todos os lados, eles se cancelariam e a média teria norma perto
  de 0; se apontassem todos para o mesmo lado, a norma seria 1. Deu 0,90: quase todos apontam para
  o mesmo lado.

**Consequência.** Os scores do E5 ficam espremidos numa faixa estreita, mesmo entre textos que não
têm nada a ver. No nosso índice, a mediana do score do 1º colocado vai de **0,84** (perguntas de
outro assunto, como "Qual é a capital da Austrália?", cujo 1º colocado tem 0,79) a **0,92** (as
perguntas originais do livro); as reescritas ficam em 0,90 e as vagas em 0,89. Ou seja, toda a
diferença entre "não tem nada a ver" e "é exatamente isso" cabe numa faixa de cerca de 0,08. O
gráfico da seção 10 do notebook `avaliacao_busca.ipynb` mostra isso: o histograma cinza são os
pares sorteados, e as linhas coloridas, as medianas de cada conjunto, todas logo à direita dele.

**O aperto de domínio.** No nosso corpus isso fica mais forte: todos os chunks são de agricultura.
Eles já estão perto uns dos outros dentro do cone, e uma pergunta de agricultura cai perto de todos.
O chunk certo pode ter 0,86 e os vizinhos 0,84 ou 0,85.

**Por que a busca ainda funciona.** O que importa é a **ordem**, não o valor: o chunk certo só
precisa ter score maior que os outros, mesmo que por pouco. Por isso a medição (MRR, Recall) olha a
posição do chunk certo, não o score dele.

**Onde a anisotropia atrapalha.**
- Quando a diferença entre o certo e os vizinhos é tão pequena que qualquer ruído troca a ordem.
- Na **detecção de fora do escopo**, quando se quer um **limiar** de score: "se o melhor score for
  menor que X, o sistema se abstém" (**abstenção**). Com tudo espremido numa faixa de 0,08, fica
  difícil achar um limiar que separe "tem resposta" de "não tem". É por isso que a AUROC contra
  perguntas de agricultura fora dos livros é só 0,83, enquanto contra outro assunto é 0,97.
- Na compressão: com scores tão próximos, a pequena perda de precisão da quantização pode trocar a
  ordem com mais facilidade.

**Como mitigar** (a escolha depende do resultado da medição):
- **Centralizar os vetores** (*mean centering*): calcular o vetor médio do corpus e subtraí-lo de
  cada vetor (e da consulta) antes de normalizar. Isso "abre" o cone e espalha os scores. É barato e
  não exige treinar nada; está nos próximos passos do `futuro_da_pesquisa.md`.
- **Busca híbrida com BM25:** a busca por palavras não tem esse problema e desempata pelos termos
  técnicos (nome da praga, do produto).
- **Reranker:** um segundo modelo reordena os 10 primeiros lendo a pergunta e o chunk juntos.
- **Fine-tuning do embedding:** treinar o modelo com pares de agricultura para ele separar melhor
  textos do mesmo domínio.

### 8.3 Métricas de avaliação

Para medir a busca, é preciso um **conjunto de avaliação**: consultas cujo chunk certo já se sabe.
Para cada consulta, a busca devolve uma lista ordenada, e a métrica olha **em que posição** o chunk
certo apareceu.

Exemplo com 4 consultas (top 10 de cada uma):

| Consulta | Posição do chunk certo |
| --- | --- |
| A | 1ª |
| B | 3ª |
| C | 2ª |
| D | não apareceu no top 10 |

**Recall@k** — "achou entre os k primeiros?". Para cada consulta vale 1 se o certo está no top k e 0
se não está; depois tira-se a média.
- Recall@1 = (1 + 0 + 0 + 0) / 4 = **0,25**
- Recall@5 = (1 + 1 + 1 + 0) / 4 = **0,75**
- Recall@10 = **0,75**

Use quando importa *se* a resposta aparece, por exemplo quando os k primeiros vão ser entregues a um
gerador (RAG) ou mostrados numa lista.

**MRR@k (Mean Reciprocal Rank)** — "quão no topo ficou?". Cada consulta vale 1/posição do certo (1
se em 1º, 1/2 se em 2º, 1/3 se em 3º...) e 0 se ficou fora do top k; depois tira-se a média.
- MRR@10 = (1 + 1/3 + 1/2 + 0) / 4 = (1 + 0,333 + 0,5 + 0) / 4 = **0,458**

Use quando há **uma** resposta certa por consulta e importa que ela venha em primeiro, que é o nosso
caso (o produtor vai ler o primeiro resultado). Repare que o MRR cai rápido: estar em 2º já vale
metade.

**nDCG@k (normalized Discounted Cumulative Gain)** — parecido com o MRR, mas aceita **várias**
respostas certas e **graus** de relevância (por exemplo: 2 = responde, 1 = ajuda em parte, 0 = não
serve). Cada acerto vale `relevância / log2(posição + 1)`, somam-se os valores (DCG) e divide-se
pelo melhor DCG possível (o da ordem perfeita), para o resultado ficar entre 0 e 1.
- Com um único certo de relevância 1 na posição 3: DCG = 1 / log2(4) = 0,5; o ideal (na 1ª) é 1;
  nDCG = **0,5**.

Use quando uma consulta tem mais de uma resposta boa (por exemplo, perguntas repetidas entre livros)
ou quando se quer dar meio ponto a respostas parciais.

**Quando usar cada uma (resumo).**

| Métrica | Pergunta que responde | Bom para |
| --- | --- | --- |
| Recall@k | O certo apareceu no top k? | Saber se o gerador/usuário vai receber a resposta |
| MRR@k | Quão perto do topo ele ficou? | Uma resposta certa por consulta (nosso caso principal) |
| nDCG@k | A ordem toda está boa, com graus? | Várias respostas certas ou relevância graduada |

**Pool fechado × corpus inteiro.** No projeto de estudo, cada consulta competia com um **pool
fechado** de 200 documentos, e o MRR deu 0,97. É mais fácil acertar entre 200 do que entre 20.665:
há menos concorrentes parecidos. Aqui a avaliação é sobre o **corpus inteiro**, então o número deve
ser menor, mas é o que representa o uso real.

**Acerto pelo `id_original`.** Como 267 respostas foram divididas em partes, achar *qualquer* parte
da resposta certa conta como acerto. Na prática: antes de procurar a posição, troca-se o id de cada
chunk da lista pelo seu `id_original` e considera-se a primeira ocorrência.

**Cuidado com consultas fáceis demais.** Usar a pergunta original do livro como consulta infla
todas as métricas, porque ela está dentro do texto do chunk. Serve como teto e teste de sanidade
(MRR@10 de 0,95 no nosso índice); os números que valem são os das reescritas (0,62) e das vagas (0,38).

**Intervalo de confiança.** Com 205 consultas por conjunto, a média varia de amostra para amostra. O
`avaliar.py` mostra o intervalo de 95% por *bootstrap*: sorteia de novo, com reposição, as 205
consultas mil vezes e vê entre que valores a média fica. Se os intervalos de duas variantes se
sobrepõem muito, a diferença entre elas pode ser só acaso.

**Detecção de consultas fora do escopo: AUROC, curva ROC e limiar.** A *detecção de fora do escopo*
(*out-of-scope detection*) é perceber que a pergunta não tem resposta nos livros; deixar de responder
por causa disso se chama *abstenção* (*abstention*). Para o sistema recusar perguntas que os livros não
respondem, ele precisa de um sinal que seja alto nas válidas e baixo nas fora do escopo. Os
candidatos são o **score do 1º colocado** e a **diferença entre o 1º e o 2º**.
- Um **limiar** é a regra "responde se o sinal ≥ t". Cada t erra dos dois lados: recusa algumas
  válidas e aceita algumas fora do escopo. A tabela de limiares mostra os dois erros para cada t.
- A **curva ROC** desenha todos os limiares de uma vez: no eixo x, a fração das fora do escopo
  aceitas; no y, a fração das válidas aceitas. Quanto mais a curva sobe colada no eixo y, melhor.
- A **AUROC** é a área sob essa curva: a chance de uma consulta válida sorteada ter sinal maior que
  uma fora do escopo sorteada. 1 é separação perfeita; 0,5 é igual a cara ou coroa.

No nosso índice, o score do 1º dá AUROC 0,97 contra perguntas de outro assunto, mas só 0,83 contra
perguntas de agricultura fora dos livros, e a diferença 1º−2º fica em 0,63 (ajuda pouco). É o
efeito da anisotropia (seção 8.2).

**Mediana e IQR.** Para resumir os scores, o `avaliar.py` usa a mediana (o valor do meio) e o
intervalo interquartil (IQR = Q3 − Q1, a largura da faixa onde ficam os 50% do meio), que não se
deixam levar por valores extremos.

### 8.4 Tipos de métricas: acurácia, precisão, recall e F1 (e por que usamos Recall@k e MRR)

As métricas mais conhecidas (acurácia, precisão, recall e F1) vêm da **classificação**: o sistema
diz "sim" ou "não" para cada item, e compara-se com a resposta certa. Elas partem da **matriz de
confusão**, que conta os quatro casos possíveis:

|  | Era relevante (positivo) | Não era relevante (negativo) |
| --- | --- | --- |
| **Sistema disse "sim"** | VP (verdadeiro positivo) | FP (falso positivo) |
| **Sistema disse "não"** | FN (falso negativo) | VN (verdadeiro negativo) |

- **Acurácia** = (VP + VN) / total. "Em quantos itens o sistema acertou, no total?"
- **Precisão** = VP / (VP + FP). "Dos que o sistema disse sim, quantos eram mesmo relevantes?"
  (mede o lixo nos resultados)
- **Recall (revocação, sensibilidade)** = VP / (VP + FN). "Dos relevantes, quantos o sistema
  achou?" (mede o que ficou de fora)
- **F1** = 2 × precisão × recall / (precisão + recall). Média harmônica das duas: só é alta se as duas
  forem altas.

Exemplo de classificação: um filtro marca 10 e-mails como spam; 8 eram spam (VP = 8, FP = 2). Havia
12 spams no total (FN = 4), entre 100 e-mails (VN = 86). Acurácia = (8 + 86)/100 = 0,94; precisão =
8/10 = 0,80; recall = 8/12 = 0,67; F1 = 0,73.

**Por que a acurácia não serve para a nossa busca.** Para cada consulta existe **um** chunk certo
entre 20.665. Se a busca fosse vista como "classificar cada chunk em relevante ou não", um sistema
que dissesse "nenhum chunk é relevante" para tudo acertaria 20.664 de 20.665 itens: **acurácia de
99,995%**, sem nunca responder nada. Quando a classe positiva é muito rara (dados desbalanceados), a
acurácia é dominada pelos verdadeiros negativos e não diz nada.

**Por que a precisão também não ajuda.** Na busca, a versão usada é a **Precisão@k**: dos k
resultados mostrados, quantos são relevantes. Com uma única resposta certa por consulta, o top 10
tem no máximo 1 relevante, então a Precisão@10 é 1/10 quando acerta e 0 quando erra. Ou seja,
**Precisão@k = Recall@k / k**: carrega a mesma informação do Recall@k, só que dividida por k, e
nunca passa de 1/k. No nosso índice, com as reescritas, Recall@10 = 0,79, então Precisão@10 = 0,079.
O número parece péssimo, mas é só uma escala diferente. Por isso não se reporta.

**Por que Recall@k e MRR.** Com uma resposta certa por consulta, o que interessa é: a resposta
apareceu nos k primeiros (Recall@k)? E em que posição (MRR)? O F1 também não acrescenta nada aqui,
porque a precisão é só o recall dividido por k.

| Métrica | Serve no nosso ranking? | Por quê |
| --- | --- | --- |
| Acurácia | Não | Os negativos (20.664 por consulta) dominam: ~100% sem achar nada |
| Precisão@k | Não (redundante) | Com 1 relevante, é Recall@k / k |
| F1@k | Não (redundante) | Combina duas medidas que aqui são a mesma |
| Recall@k | Sim | "A resposta chegou ao usuário ou ao gerador?" |
| MRR@k | Sim (principal) | "Ela veio no topo?" |
| nDCG@k | Quando houver vários relevantes | Aceita várias respostas certas e graus |

**Quando acurácia, precisão e F1 voltam a servir.**
1. **Vários relevantes por consulta.** Se uma consulta tiver mais de uma resposta boa (por exemplo,
   perguntas repetidas entre livros), a Precisão@k passa a dizer quanto dos k resultados é útil, e o
   nDCG passa a ser a métrica natural.
2. **A detecção de fora do escopo é uma classificação binária.** Decidir se o sistema responde ou recusa é um "sim ou
   não" por consulta, e aí a matriz de confusão volta a fazer sentido. Positivo = consulta que os
   livros respondem (válida); o sistema "diz sim" quando o score do 1º passa do limiar.

   Com os resultados atuais (`results/e5-small-fp32/`), usando as 1.230 válidas
   (reescritas + vagas) e as 100 fora do escopo:

   | Limiar do score do 1º | Válidas aceitas (recall) | Fora aceitas (FP) | Precisão | F1 | Acurácia |
   | --- | ---: | ---: | ---: | ---: | ---: |
   | 0,890 (rígido) | 52% (644 de 1.230) | 3% (3 de 100) | 1,00 | 0,69 | 0,56 |
   | 0,850 (frouxo) | 98% (1.200 de 1.230) | 61% (61 de 100) | 0,95 | 0,96 | 0,93 |

   O limiar rígido quase não deixa passar pergunta fora do escopo (precisão alta), mas recusa metade
   das válidas (recall baixo). O frouxo responde quase tudo, mas aceita 61% das fora do
   escopo. A acurácia parece melhor no frouxo, mas isso depende da proporção: como há 12 vezes mais
   válidas que fora do escopo no teste, aceitar tudo já daria 0,92. Por isso, também aqui, a acurácia
   engana.

   A **AUROC** (seção 8.3) resume a separação **sem escolher limiar**: é por isso que ela é a métrica
   principal para a detecção de fora do escopo. Precisão, recall e F1 entram depois, para escolher o ponto de operação
   (qual erro é mais caro: recusar uma pergunta válida ou responder uma que o livro não cobre).
   O `avaliar.py` e o notebook trazem, para cada ponto de operação, a matriz de confusão (VP, FN,
   FP, VN) com precision, recall e accuracy.

**Como as métricas se relacionam (resumo).**
- Ranking com uma resposta certa: **MRR@k** (posição) e **Recall@k** (chegou ou não).
- Ranking com várias respostas certas ou graus: **nDCG@k** e **Precisão@k**.
- Decisão "responde ou não": **AUROC** (sem limiar) e, para um limiar escolhido, **precisão, recall,
  F1** e a taxa de **falsos positivos**.
- **Acurácia:** só quando as classes são equilibradas, o que não é o nosso caso em nenhum dos dois.

---

## 9. Glossário

### Busca e recuperação
- **IR (Information Retrieval, recuperação de informação):** encontrar, numa coleção de textos, os
  que respondem a uma consulta. É o que um buscador faz.
- **RAG (Retrieval-Augmented Generation):** recuperar trechos relevantes (IR) e entregá-los a um
  modelo de linguagem, que escreve a resposta com base neles. O IR é a primeira metade do RAG.
- **Corpus:** o conjunto de textos onde se busca. Aqui, os 20.665 chunks.
- **Chunk:** um pedaço do corpus que a busca pode devolver. Aqui, um par pergunta-resposta (ou uma
  parte dele).
- **Consulta (query):** a pergunta que o usuário digita.
- **Passage:** um trecho do corpus (um chunk), no vocabulário do E5.
- **Índice:** a estrutura salva que permite buscar rápido. Aqui, a matriz de vetores + a lista de ids.
- **Top-k:** os k primeiros resultados da lista ordenada.
- **Score:** a nota de semelhança entre a consulta e um chunk.
- **Busca densa:** busca por significado, comparando vetores (embeddings). Acha sinônimos e
  paráfrases, mas pode errar em nomes técnicos raros.
- **Busca lexical (esparsa):** busca por palavras em comum. O método clássico é o **BM25**, que dá
  mais peso a palavras raras e repetidas no texto. Bom para nomes de pragas e produtos.
- **SQLite FTS5:** módulo do banco SQLite que faz busca lexical com BM25, leve o suficiente para o Pi.
- **Stemmer:** reduz palavras ao radical ("plantas", "plantio" → "plant"), para a busca lexical
  casar variações. O RSLP é um stemmer para português.
- **Busca híbrida:** combina a densa e a lexical.
- **RRF (Reciprocal Rank Fusion):** forma simples de juntar duas listas de resultados: cada chunk
  ganha 1/(60 + posição) em cada lista, e somam-se os pontos.
- **Reranker (cross-encoder):** um segundo modelo, mais caro, que reordena só os primeiros resultados
  lendo consulta e chunk juntos. Melhora a ordem, mas é mais lento.

### Modelos e vetores
- **Modelo de linguagem:** rede neural treinada com muito texto. Pode gerar texto (gerador) ou
  transformar texto em vetor (modelo de embedding).
- **Embedding (vetor):** lista de números que representa o significado de um texto. No E5-small, 384
  números.
- **Dimensão:** quantos números o vetor tem (384 no E5-small, 768 no base, 1024 no large).
- **E5 (`intfloat/multilingual-e5-small`):** o modelo de embedding usado, multilíngue, com cerca de
  118 milhões de parâmetros.
- **Parâmetros:** os números internos que o modelo aprendeu no treino. Mais parâmetros costumam
  significar mais qualidade e mais memória.
- **Token:** pedaço de texto que o modelo lê (uma palavra, parte dela ou um sinal). "Plantio" pode
  virar dois tokens.
- **Tokenizer:** o programa que quebra o texto em tokens e converte cada um num número.
- **Tokens especiais:** marcadores de início e fim que o tokenizer acrescenta; também contam no
  limite.
- **Limite de 512 tokens (max_length):** o máximo que o E5 lê de uma vez. O resto é cortado
  (**truncation**).
- **Lote (batch):** grupo de textos processados juntos, para ganhar velocidade.
- **Padding:** tokens vazios que completam os textos curtos de um lote até o tamanho do maior.
- **Attention mask:** marca quais tokens são reais (1) e quais são padding (0).
- **Mean pooling (average_pool):** o modelo devolve um vetor por token; a média deles (sem o padding)
  vira o vetor do texto.
- **Normalização L2:** dividir o vetor pelo seu comprimento para ele ter tamanho 1 ([3, 4] → [0,6; 0,8]).
  O produto escalar vira o cosseno; a ordem do ranking não muda. Ver seção 8.1.
- **Produto escalar:** multiplicar os números dos dois vetores posição a posição e somar. Com
  vetores normalizados, é igual à **similaridade de cosseno**.
- **Similaridade de cosseno:** mede o ângulo entre dois vetores: 1 = mesma direção (muito parecidos),
  0 = sem relação. Fórmula: (a · b) / (|a| × |b|).
- **Norma L2 (comprimento do vetor):** raiz da soma dos quadrados dos números do vetor. [3, 4] tem
  norma 5.
- **Anisotropia:** os vetores do modelo ocupam um cone estreito do espaço, então até textos sem
  relação têm cosseno alto (0,7 a 0,9 no E5). Ver seção 8.2.
- **Centralização:** subtrair a média dos vetores do corpus antes de normalizar, para abrir o cone e
  espalhar os scores.
- **FAISS / sqlite-vec:** bibliotecas de busca vetorial rápida (a segunda roda dentro do SQLite).
- **Prefixo (`query:` / `passage:`):** texto posto na frente para o E5 saber se é pergunta ou trecho.
- **Hugging Face:** site e biblioteca (`transformers`) de onde os modelos são baixados. Depois da
  primeira vez, ficam em cache e funcionam offline.
- **PyTorch (`torch`):** biblioteca que roda as redes neurais.
- **NumPy:** biblioteca de matrizes e contas numéricas em Python.

### Compressão e execução no aparelho
- **Compressão de modelo:** deixar o modelo menor e mais rápido, aceitando alguma perda de qualidade.
- **Quantização:** guardar os números do modelo com menos bits. **FP32** (32 bits, o padrão),
  **FP16** (metade), **INT8** (inteiros de 8 bits, cerca de 4× menor que FP32), **INT4** (8× menor).
- **Destilação / modelos menores:** usar uma versão menor do mesmo modelo (small × base × large).
- **ONNX / ONNX Runtime:** formato de modelo e programa que o executa rápido em CPU, inclusive em ARM
  (Pi, celular).
- **GGUF:** formato de modelos geradores quantizados, usado pelo llama.cpp; roda em celulares.
- **ARM / ARM64:** a arquitetura de processador do Pi e dos celulares (diferente da do Mac Intel ou de
  PCs).
- **Latência:** tempo de resposta de uma busca. **Mediana** = o tempo típico; **p95** = o tempo que
  95% das buscas não passam (mostra os casos lentos).
- **RAM:** memória de trabalho do aparelho; o modelo e o índice precisam caber nela.

### Gerador (extensão futura)
- **LLM / SLM:** modelo de linguagem grande / pequeno. Um SLM (0,5 a 3 bilhões de parâmetros) cabe
  num celular.
- **Fine-tuning:** continuar o treino de um modelo com dados próprios, para ele se adaptar ao domínio.
- **LoRA:** forma barata de fine-tuning, que treina só pequenas matrizes extras em vez do modelo todo.

### Avaliação
- **Golden set (conjunto de avaliação):** consultas de teste com a resposta certa conhecida (o chunk
  correto). Aqui, 205 perguntas do livro, cada uma como a original, três reescritas e três vagas (todas com o
  mesmo gabarito), e 100 consultas fora do escopo.
- **Gabarito:** o chunk certo de cada consulta. Como as respostas divididas têm várias partes, conta
  como acerto achar qualquer parte (pelo `id_original`).
- **Recall@k:** em quantas consultas o chunk certo aparece entre os k primeiros. Ver seção 8.3.
- **MRR@10 (Mean Reciprocal Rank):** média de 1/posição do chunk certo (1 se em primeiro, 0,5 se em
  segundo...; 0 se fora do top 10). Premia acertar no topo.
- **nDCG@10:** parecido com o MRR, mas aceita mais de uma resposta certa e dá notas graduadas.
- **Pool fechado:** avaliação em que cada consulta compete só com um grupo pequeno de documentos
  (por exemplo, 200). Dá números mais altos que a avaliação sobre o corpus inteiro.
- **Matriz de confusão:** tabela com os quatro casos de uma decisão sim/não: verdadeiro positivo (VP),
  falso positivo (FP), falso negativo (FN) e verdadeiro negativo (VN). Ver seção 8.4.
- **Acurácia:** (VP + VN) / total. Engana quando uma classe é muito mais comum que a outra.
- **Precisão:** VP / (VP + FP), dos que o sistema disse sim, quantos estavam certos. Na busca,
  **Precisão@k** = relevantes no top k / k; com uma só resposta certa, é Recall@k / k.
- **Recall (revocação, sensibilidade):** VP / (VP + FN), dos relevantes, quantos foram achados. Na
  busca, o Recall@k.
- **F1:** média harmônica de precisão e recall; só é alta se as duas forem.
- **Taxa de falsos positivos:** fração dos negativos aceitos por engano (aqui, perguntas fora do
  escopo que o sistema responderia). É o eixo x da curva ROC.
- **Dados desbalanceados:** quando uma classe é muito mais rara que a outra (1 chunk certo entre
  20.665).
- **AUROC:** área sob a curva ROC; a chance de uma consulta válida ter score maior que uma fora do
  escopo (1 = separa perfeitamente, 0,5 = acaso). Ver seção 8.3.
- **Curva ROC:** gráfico de válidas aceitas × fora do escopo aceitas para todos os limiares.
- **Bootstrap:** sortear de novo, com reposição, as consultas avaliadas muitas vezes, para ver o
  quanto a média varia (intervalo de confiança).
- **IQR (intervalo interquartil):** Q3 − Q1, a largura da faixa dos 50% do meio dos valores.
- **Limiar (threshold):** valor de score abaixo do qual o sistema se abstém (não responde), por considerar a consulta fora do escopo.
- **Detecção de fora do escopo (out-of-scope detection):** perceber que a consulta não tem resposta
  nos livros. Aqui, medida pela AUROC entre consultas válidas e fora do escopo.
- **Abstenção (abstention):** o sistema deixar de responder (por exemplo, quando o score fica abaixo
  do limiar), em vez de devolver uma resposta provavelmente errada.
- **Pior caso (worst-case):** em cada pergunta, o resultado da versão (das três
  reescritas ou das três vagas) em que a busca foi pior; a média disso mede a robustez.
- **Ablação:** tirar ou trocar uma peça e medir o efeito (por exemplo, codificar com e sem a pergunta).
- **Baseline:** o sistema de referência contra o qual os outros são comparados.
- **Fora do escopo:** consultas que o corpus não responde; servem para ver como o sistema se comporta.

### Dados e processamento
- **Pipeline:** sequência de etapas em que cada uma usa a saída da anterior.
- **Reprodutibilidade:** rodar de novo e obter exatamente o mesmo resultado.
- **Byte a byte:** dois arquivos idênticos até o último caractere.
- **SHA-256 (hash):** "impressão digital" de um arquivo; se um único byte mudar, o hash muda.
- **ePub:** formato de livro digital; por dentro, um zip com páginas HTML.
- **HTML / XHTML:** linguagem das páginas web (e das páginas do ePub).
- **BeautifulSoup:** biblioteca Python que lê HTML e extrai o texto.
- **pdftotext (Poppler):** programa que extrai texto de PDFs.
- **Hífen discricionário (U+00AD):** hífen invisível que o PDF usa para quebrar palavras no fim da
  linha; o script junta essas palavras.
- **Parser:** código que lê um texto com uma estrutura e separa as partes (capítulos, perguntas...).
- **Expressão regular (regex):** padrão de texto usado para reconhecer, por exemplo, "15) ..." ou
  "• Capítulo 3 •".
- **Metadados:** dados sobre os dados (livro, ano, capítulo, autores).
- **EDA (Exploratory Data Analysis, análise exploratória):** olhar os dados com estatísticas e
  gráficos antes de usá-los.

### Ferramentas e organização
- **venv (`.venv`):** ambiente Python isolado, com as bibliotecas do projeto. Ativa-se com
  `source .venv/bin/activate`.
- **`requirements.txt`:** lista das bibliotecas (e versões) que o projeto usa.
- **Git:** controle de versões. **Commit** = um ponto salvo do histórico; **`git add -A`** = prepara
  todas as mudanças para o commit; **`.gitignore`** = o que o git não deve guardar (venv, índices).
- **ADR (Architecture Decision Record):** documento curto que registra uma decisão de organização e
  por que ela foi tomada.
- **Linha de comando (CLI):** rodar programas digitando comandos no terminal, com opções como
  `--cultura soja`.
- **Docstring / comentário:** texto explicativo dentro do código; não muda o que o código faz.

---

## 10. Perguntas frequentes

**Por que usamos Recall@k e MRR, e não acurácia ou precisão?** Porque há uma só resposta certa
entre 20.665 chunks: dizer "nada é relevante" já daria 99,995% de acurácia, e a Precisão@k vira só
Recall@k / k. Precisão, recall e F1 voltam a servir para a detecção de fora do escopo (seção 8.4).

**Qual a diferença entre chunk e vetor?** O chunk é o texto (o que o usuário lê); o vetor são os 384
números calculados a partir dele (o que a busca compara). Cada chunk tem um vetor.

**Quando uma resposta é dividida, as partes continuam ligadas à pergunta?** Sim: mesmo
`id_original`, mesmos metadados e a pergunta repetida no texto de cada parte.

**Por que preciso regerar o índice?** Porque ele precisa corresponder linha a linha ao
`chunks.jsonl`. Sempre que o corpus mudar, rode `python scripts/indexar.py`.

**Por que o golden set não pode usar só as perguntas originais?** Elas estão dentro do texto de cada
chunk, então a busca acha o chunk certo com facilidade demais (MRR@10 de 0,95). Elas ficam como teto;
as reescritas e as vagas imitam o uso real.

**O que está fora do corpus e por quê?** As introduções dos livros e as 118 respostas que dependem de
uma imagem (tabela, fórmula ou figura). É decisão do orientador e é reversível.

**Para que serve normalizar os vetores?** Para o produto escalar virar o cosseno e a busca virar uma
multiplicação de matrizes rápida. Não muda a ordem dos resultados (seção 8.1).

**Por que todos os scores ficam entre 0,7 e 0,9?** Por causa da anisotropia do E5 e de o corpus ser
só de agricultura. A busca funciona mesmo assim, porque o que importa é a ordem (seção 8.2).

**Onde vejo o que foi feito em cada dia?** No `docs/DIARIO.md`.
