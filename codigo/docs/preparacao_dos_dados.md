# Preparação dos dados: etapas sem script

Este documento registra as duas etapas da preparação do corpus que **não são feitas por script**
neste repositório: a conversão dos livros para texto e a transcrição das imagens. O objetivo é
deixar claro como cada uma foi feita, onde houve uso de IA e o que é preciso para reproduzir o
resultado.

O princípio adotado é: a saída dessas etapas fica **guardada e versionada**, e tudo o que vem depois
dela é determinístico. Quem for reproduzir o trabalho parte dos arquivos guardados e chega ao mesmo
`chunks.jsonl`, sem depender de rodar a IA de novo.

| Etapa | Entrada | Saída guardada | Uso de IA |
| --- | --- | --- | --- |
| 1. Conversão para texto | ePub/PDF da Infoteca | `500PerguntasRespostas/txt/*.txt` | Sim: conversão |
| 2. Transcrição das imagens | PDFs + `chunks_sem_imagens.jsonl` | `auxiliares/imagens_transcritas.csv`, `auxiliares/chunks_alterados.jsonl` | Sim: seleção e transcrição |

---

## 1. Conversão dos livros para texto

### O que se sabe

- **Fontes:** os livros da coleção foram baixados da Infoteca da Embrapa. As URLs, edições e o
  formato de cada um estão em `500PerguntasRespostas/PDFs/indice.csv` (colunas `formato_original`,
  `arquivo`, `url_origem` e `arquivo_txt`).
- **Formato preferido:** sempre que havia ePub, ele foi usado no lugar do PDF. O ePub é HTML por
  dentro, então o texto sai limpo, sem quebra de colunas nem números de página.
- **Resultado:** 41 arquivos `500P_<cultura>_<ano>.txt`, em dois formatos, cada um tratado por um
  parser próprio no `src/chunking.py`:
  - **Formato A** (vindo de ePub): capítulos como `• Capítulo N •`, perguntas como `N) texto` e o
    separador `•••` entre os pares.
  - **Formato B** (vindo de PDF): o número da pergunta aparece sozinho na linha, misturado com números
    de página, rodapés e quebras de página (`\f`).
- **Cobertura:** a pasta `PDFs/` tem 44 PDFs, dos quais 41 entram no corpus. Os 3 de fora são
  edições antigas de livros que têm versão mais nova na coleção: milho 2011 (usado o de 2013),
  feijão 2014 (usado o de 2015) e mandioca 2006 (usado o de 2013). Fica uma edição por título.

### Como foi feita

A autora pediu a conversão ao **Claude (Anthropic)**, numa conversa separada deste projeto, por volta
de 20 a 22/10/2026. O pedido foi converter os livros baixados (ePub ou PDF) para texto puro, um
arquivo por título, usando a edição mais recente de cada um.

As ferramentas que o Claude usou sugerem extração direta do texto, e não reescrita pela IA:
- os txt vindos de PDF guardam artefatos típicos de extração automática, como números de página,
  rodapés, quebras de página (`\f`) e palavras hifenizadas no fim da linha;
- os txt vindos de ePub preservam a marcação do livro (`• Capítulo N •`, `•••`);
- nas comparações pontuais feitas com os PDFs (por exemplo, búfalos, mamão e milho), o texto bateu
  com o original, sem paráfrases nem resumos. Não houve conferência sistemática de todos os livros.

### Reprodutibilidade

Como a conversão foi feita por IA numa conversa, ela não é reprodutível de forma exata. Os txt
guardados em `500PerguntasRespostas/txt/` são a **entrada oficial** do pipeline. Quem quiser refazer
a etapa de forma determinística pode usar uma ferramenta de extração, como `pdftotext` (Poppler) ou
PyMuPDF para os PDFs e Calibre `ebook-convert` ou `pandoc` para os ePub. O resultado, porém, não será
idêntico, e o parser do `chunking.py` pode precisar de ajustes.

O parser (`src/chunking.py`) é determinístico: os mesmos txt sempre geram os mesmos chunks.

---

## 2. Transcrição do conteúdo das imagens

### Motivação

Algumas respostas dos livros dependem de uma imagem: uma fórmula, um gráfico, uma tabela ou um
fluxograma. Sem ela, o texto extraído fica incompleto. Um exemplo é a pergunta 382 de búfalos, que
dizia "Há uma fórmula fácil e prática para esse cálculo:" e terminava ali. O objetivo desta etapa foi
levar a informação dessas imagens para o texto da resposta, já que o modelo de embedding só lê texto.

### Ferramentas e IA

- **Extração e renderização:** PyMuPDF (`fitz`), `pdfimages`/`pdftoppm` (Poppler) e `montage`
  (ImageMagick).
- **IA:** Claude (Anthropic), em sessão do Claude Code, em 27/10/2026. A IA foi usada para triar as
  imagens e transcrever o conteúdo a partir das imagens renderizadas, seguindo as regras do passo
  3. Não houve um prompt único rodado imagem a imagem: as regras foram dadas na conversa, e a IA
  aplicou essas regras olhando as pranchas e os recortes.

### Procedimento

**Passo 1. Localizar as imagens e associar cada uma a uma pergunta.** Para cada PDF:
- Com o PyMuPDF, listar os blocos de texto que começam com número de pergunta e as imagens de cada
  página, com posição (página e coordenada vertical).
- Descartar imagens repetidas mais de duas vezes no livro (vinhetas e ícones), imagens com área menor
  que 400 pt² e imagens das três primeiras páginas (capa e créditos).
- Ordenar texto e imagens por posição na página e atribuir cada imagem à última pergunta que aparece
  antes dela. Só conta a última ocorrência de cada número, para ignorar a lista de perguntas do início
  de cada capítulo.

Resultado: **2.597 imagens** nos 41 livros.

**Passo 2. Separar as imagens com informação.** As imagens foram renderizadas em miniaturas e
reunidas em pranchas de 100 (ImageMagick `montage`) para triagem visual. A grande maioria eram
ilustrações decorativas, como os bonecos de abertura de capítulo e as fotos ilustrativas. Os
critérios foram:
- **Mantidas:** fórmulas, gráficos com valores, tabelas em imagem, fluxogramas e diagramas, mapas com
  legenda.
- **Descartadas:** ilustrações sem informação textual ou numérica, e imagens cuja informação já
  estava no texto da resposta (por exemplo, a composição do mamão).

Depois, as candidatas foram renderizadas de novo com a região da página em volta (cerca de 110 pt
acima, para incluir o texto que as introduz) e em resolução maior (95 dpi), para conferência e
transcrição. Resultado: **140 imagens** com informação.

**Passo 3. Transcrever.** Cada imagem foi transcrita a partir da renderização da página, seguindo
estas regras:
- **Fórmulas:** em texto linear, com símbolos Unicode quando necessário. Exemplo:
  `H_F1 = [(P. média da F1 − P. média dos pais) / P. média dos pais] × 100`.
- **Figuras** (gráficos, fluxogramas, mapas): uma descrição do conteúdo informativo, entre
  colchetes, no formato `[Figura: ...]`. A descrição inclui os valores, rótulos e relações que a
  figura mostra, sem interpretações que não estejam nela.
- **Tabelas:** em texto, linha a linha.
- Nada do texto original da resposta é alterado: a transcrição só é acrescentada.

O prompt abaixo **não foi executado literalmente**. Ele reúne as regras acima num formato que pode
ser usado para refazer ou estender a etapa com outro modelo, imagem por imagem:

```text
Você vai receber a imagem de um trecho de página de um livro da coleção "500 Perguntas, 500
Respostas" da Embrapa, com uma figura no meio do texto de uma resposta.

1. Diga se a figura traz informação que não está no texto em volta (fórmula, tabela, gráfico com
   valores, fluxograma, diagrama, mapa com legenda) ou se é só ilustrativa.
2. Se trouxer informação, transcreva:
   - fórmulas em uma linha de texto, com símbolos Unicode (×, −, ÷, ²) e subscritos como _;
   - tabelas linha a linha, separando as colunas com " | ";
   - gráficos, fluxogramas e mapas como "[Figura: <descrição objetiva com os valores e rótulos
     visíveis>]".
3. Não invente valores que não estejam legíveis na imagem e não acrescente explicações.
4. Responda só com a transcrição, ou com "ILUSTRATIVA" se a figura não tiver informação.
```

**Passo 4. Inserir no ponto certo da resposta.** Para cada imagem, foram pegas as últimas linhas de
texto acima dela na página (a "âncora"). A âncora foi procurada na resposta da pergunta associada,
comparando o texto sem acentos, pontuação ou maiúsculas, e a transcrição foi inserida logo depois do
trecho encontrado. Quando a âncora não era encontrada, a transcrição foi para o fim da resposta.

**Passo 5. Revisão.** Os 113 chunks alterados foram conferidos. Três inserções tinham caído no meio
de um parágrafo e foram movidas para o fim da resposta: ILPF q096, sorgo q288 e trigo q487.
Também foi conferido que o texto original de todos os chunks continuou idêntico, apenas com as
transcrições acrescentadas.

### Resultado

- **140 imagens** transcritas, distribuídas em **113 respostas**. Os tipos:
  - fórmulas: calagem, irrigação, vazão, taxas de desfrute e de parição, heterose, umidade;
  - gráficos: Kc do amendoim, produção de milho por estado, pragas do feijoeiro por fase;
  - fluxogramas e diagramas: óleo de gergelim, cadeia produtiva do trigo, instalações de suínos,
    partes das sementes;
  - mapas: regiões de trigo, grupos de maturidade da soja.
- Os chunks alterados têm o campo `"conteudo_imagem": true`.
- `auxiliares/imagens_transcritas.csv` guarda cada transcrição (`livro`, `pagina_pdf`,
  `transcricao`).
- `auxiliares/chunks_alterados.jsonl` guarda os 113 chunks já com a transcrição inserida.

### Como reproduzir

Para chegar ao mesmo `chunks.jsonl` sem refazer a etapa com IA:
1. Gere os chunks com `python src/chunking.py --sem-divisao`.
2. Substitua, pelo `id`, cada chunk que também aparece em `auxiliares/chunks_alterados.jsonl` pela
   versão desse arquivo.
3. Rode `python scripts/dividir_chunks.py`.

O passo 2 depende do `chunks_alterados.jsonl`, e não só do CSV, porque o CSV não guarda o id do
chunk nem a posição exata da inserção.

### Limitações

- **Triagem e transcrição:** foram feitas com IA a partir de imagens em baixa resolução. Valores
  pequenos em gráficos podem ter sido lidos com erro, e a revisão foi por amostragem, não imagem a
  imagem.
- **Possíveis omissões:** imagens com informação podem ter ficado de fora, se tinham área pequena,
  se se repetiam no livro ou se foram julgadas decorativas na triagem visual.
- **Reprodutibilidade da IA:** a transcrição não é determinística. Refazer a etapa com outro modelo,
  ou com o mesmo em outra data, pode gerar textos diferentes. Por isso, a saída guardada é a
  referência.
