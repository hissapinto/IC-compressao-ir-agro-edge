# Preparação dos dados

Como o corpus é gerado, dos livros originais até o `data/processed/chunks.jsonl`. Todas as etapas
rodam por script, sem IA, e reproduzem os arquivos de ponta a ponta.

```
fontes.csv (URL e SHA-256)  ──converter_para_txt.py──▶  raw/txt/*.txt
raw/txt + indice.csv        ──src/chunking.py──────▶  auxiliares/chunks_sem_divisao.jsonl
                            ──dividir_chunks.py─────▶  auxiliares/chunks_completo.jsonl
                            ──filtrar_chunks.py─────▶  processed/chunks.jsonl
```

## 1. Fontes

- `data/raw/fontes.csv` lista os 41 livros usados: título, formato da fonte (26 ePubs e
  15 PDFs), URL na Infoteca da Embrapa e o **SHA-256** de cada arquivo. O hash prova que a fonte é a
  mesma usada aqui.
- Os arquivos baixados ficam em `data/raw/epub/` e `data/raw/PDFs/`. O `data/raw/indice.csv` traz
  título, edição e URL de cada livro, e é lido pelo `chunking.py` para os metadados dos chunks.
- **Uma edição por título:** a pasta tem 44 PDFs, e 3 edições antigas ficam de fora (milho 2011,
  feijão 2014 e mandioca 2006), porque há versão mais nova.
- **ePub quando existe:** o ePub é HTML por dentro, e o texto sai limpo. Oito livros têm ePub e PDF
  na Infoteca (caju, feijão-caupi, ILPF, pêssego, recursos genéticos, soja, sorgo e trigo); esses
  usam o PDF.

## 2. Conversão para txt: `scripts/converter_para_txt.py`

1. **Baixar:** baixa o que faltar e confere o SHA-256 de cada arquivo com o `fontes.csv`.
2. **ePub → txt** direto, sem passar por PDF: a ordem das páginas vem do *spine* do ePub, e o texto de
   cada bloco HTML (parágrafo, título, item de lista) sai com o BeautifulSoup, um bloco por vez,
   separados por linha em branco. Tabelas viram uma linha por linha da tabela, com as células
   separadas por espaço; `<br>` e blocos dentro de uma célula viram quebra de linha; `<hr>` vira
   `* * *`.
3. **PDF → txt** com o `pdftotext` (Poppler), com as opções padrão, juntando as palavras que o livro
   quebra com hífen discricionário (U+00AD) no fim da linha.
4. Grava os txt em `data/raw/txt/`, com as versões das ferramentas em
   `data/raw/txt/ferramentas.json`.

Os txt vêm em dois formatos, cada um com um parser no `chunking.py`: **A** (de ePub), com capítulos
como `• Capítulo N •` e perguntas como `N) texto`; e **B** (de PDF), com o número da pergunta sozinho
na linha, misturado com números de página e rodapés.

## 3. Extração dos pares: `src/chunking.py --sem-divisao`

Gera um chunk por par pergunta-resposta (20.499 pares; búfalos q383 não existe no texto) e os trechos
de introdução de cada livro (96), com cultura, livro, ano, edição, capítulo, autores e número da
pergunta. O campo `texto`, que vai para o embedding, junta `cultura | capítulo`, pergunta e resposta.
Saídas: `auxiliares/chunks_sem_divisao.jsonl` (20.595 chunks) e `auxiliares/relatorio.csv`.

## 4. Divisão em 512 tokens: `scripts/dividir_chunks.py`

Divide os chunks que passam de 512 tokens do `intfloat/multilingual-e5-small`, contando o prefixo
`passage: ` e os tokens especiais. Cada parte repete o cabeçalho (cultura, capítulo e pergunta) e leva
um trecho da resposta, cortado em fim de parágrafo, de frase ou, em último caso, entre palavras.
Saída: `auxiliares/chunks_completo.jsonl` (20.885 chunks; 272 chunks viram 562 partes).

## 5. Filtro do corpus: `scripts/filtrar_chunks.py`

**Decisão do orientador:** o corpus usado tem só os pares que vêm de texto. O filtro tira, sempre pelo `id_original` (as partes de um chunk dividido saem juntas):

| Grupo | Chunks | Perguntas |
| --- | --- | --- |
| Introduções (`tipo = introducao`) | 96 | – |
| Resposta cuja informação está numa fórmula, tabela ou figura que só existe como imagem | 119 | 113 |
| Resposta remete a tabela ou figura não transcrita | 5 | 5 |
| **Fica no `chunks.jsonl`** | **20.665** | **20.381** |

Os dois grupos de imagem estão em `configs/ids_respostas_com_imagem.txt`, separados por marcadores
`# == ... ==`, junto com 4 casos de fronteira comentados. Nada é apagado:
`--manter-introducao --sem-lista` gera o corpus completo.

## 6. Como reproduzir

A partir de `codigo/`, com o venv ativo:

```bash
python scripts/converter_para_txt.py            # ou --sem-download, se os livros já estiverem na pasta
python src/chunking.py --sem-divisao
python scripts/dividir_chunks.py
python scripts/filtrar_chunks.py
python scripts/indexar.py
```

Para conferir sem sobrescrever os txt, gere numa pasta à parte e compare:
`python scripts/converter_para_txt.py --sem-download --saida /tmp/txt --comparar-com data/raw/txt`.

**Conferência:** os 41 txt saem idênticos byte a byte (20.499 de 20.499
pares), e `chunks_sem_divisao.jsonl` e `relatorio.csv` também. A divisão reproduz byte a byte o
`chunks_completo.jsonl`, e o filtro reproduz o `chunks.jsonl`.

## Limitações

- **Versões das ferramentas:** os txt saem idênticos byte a byte com as versões de
  `data/raw/txt/ferramentas.json` (Python 3.10.12, beautifulsoup4 4.15.0, pdftotext 22.02.0). Com outro
  `pdftotext`, mudam só linhas do sumário dos PDFs (pontos de preenchimento), que não entram nos
  chunks. A divisão depende do tokenizer do E5 (versões no `requirements.txt`).
- **Pergunta faltando:** búfalos q383 não aparece no texto extraído; ainda falta conferir no livro.
- **Perguntas com imagem:** 118 perguntas estão fora do corpus por decisão oficial (até segunda
  ordem), porque a informação delas está numa imagem. Imagens com informação também podem ter passado
  despercebidas em respostas que não citam "Tabela" ou "Figura".
