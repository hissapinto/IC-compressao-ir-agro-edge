# ADR 0001: Estrutura da pasta de código

- **Status:** Aceito
- **Data:** 2026-10-28
- **Autora:** Isabela

## Contexto

A IC "Impacto da compressão de modelos de linguagem na qualidade da recuperação da informação em
domínio agrícola sob restrições de hardware" constrói um RAG offline sobre a coleção *500 Perguntas,
500 Respostas* da Embrapa (41 livros, 20.595 pares e introduções, divididos em 20.887 chunks de até 512 tokens). O pipeline tem quatro etapas: geração dos
chunks, embeddings, recuperação (densa, BM25 e híbrida com RRF) e geração de respostas por um SLM.

A pergunta da pesquisa é comparativa: o mesmo pipeline roda com várias versões do modelo (fp32,
int8, GGUF etc.) e em duas máquinas (Mac para preparar os dados e Raspberry Pi 4 de 4 GB para
executar). Por isso a organização do código precisa:

1. reaproveitar as mesmas funções (por exemplo `encode`) em todas as etapas, sem cópias divergentes;
2. manter separados os artefatos de cada variante (índices, métricas e tempos), para que as comparações
   sejam rastreáveis e reproduzíveis;
3. evitar que o reprocessamento de uma etapa sobrescreva dados finais curados à mão (por exemplo, os
   chunks com a transcrição das imagens);
4. não duplicar dados brutos grandes (PDFs e txt).

Até então, os scripts e os dados estavam espalhados (`Embrapa/chunks/`, `codigo/data/`) e um script
de exemplo (`main` do doc-ranker) misturava indexação e busca em uma única execução, recodificando
todos os documentos a cada consulta. Com 20 mil chunks, isso é inviável.

## Decisão

Adotar a estrutura abaixo em `Embrapa/codigo/`:

```
data/
  raw/          ponteiro para Embrapa/500PerguntasRespostas (dados brutos não são copiados)
  processed/    chunks.jsonl final
    auxiliares/ saídas intermediárias (sem_divisao, sem_imagens, alterados, transcrições, relatório)
  golden/       conjunto de avaliação (pergunta -> chunk relevante)
  indices/      um subdiretório por variante: <modelo>-<precisão>/ (ex.: e5-small-fp32/)
src/            biblioteca: apenas funções, sem efeitos ao importar
scripts/        pontos de entrada (mains) que importam de src/
configs/        um .yaml por experimento (modelo, quantização, k, máquina)
results/        métricas e tempos por experimento
notebooks/      análises e gráficos
docs/adr/       registros de decisão
```

Regras associadas:

- **Biblioteca × execução.** Código em `src/` não lê argumentos nem roda nada ao ser importado. Cada
  etapa executável fica em `scripts/` e importa de `src/`.
- **Indexar uma vez, buscar muitas.** A geração de embeddings dos chunks é uma etapa separada, que
  roda uma vez por variante e persiste o resultado em `data/indices/<variante>/`
  (`embeddings.npy` + `ids.json`). A busca só codifica a consulta.
- **Nome da variante no caminho.** Índices e resultados levam o nome do modelo e da precisão no
  caminho, e cada experimento é descrito por um arquivo em `configs/`.
- **Dados finais protegidos.** Scripts de reprocessamento escrevem em `processed/auxiliares/`;
  `processed/chunks.jsonl` só muda por decisão explícita.
- **Prefixos do E5 no código.** Os prefixos `query: ` e `passage: ` são aplicados no `encode`,
  e não gravados nos chunks, para que os mesmos chunks sirvam a modelos sem prefixo.
- **Execução a partir de `codigo/`**, com o `.venv` ativo e dependências em `requirements.txt`.

## Alternativas consideradas

- **Script único (estilo `main` do doc-ranker).** É simples, mas recodifica o corpus a cada
  consulta e mistura etapas com custos e máquinas diferentes. Foi descartado.
- **Estrutura plana (todos os scripts na raiz).** Funciona no início, mas não escala com as variantes
  e dificulta separar o que é reutilizável do que é experimento. Foi descartada.
- **Pacote Python instalável (`pip install -e .`).** É mais robusto para imports, mas é um overhead
  desnecessário agora; os scripts ajustam o `sys.path` para `src/`. Pode ser revisto depois.
- **Copiar os dados brutos para `data/raw/`.** Duplicaria centenas de MB no OneDrive. Foi descartado
  em favor de um ponteiro.

## Consequências

- **Positivas:**
  - Cada comparação entre variantes tem um índice, uma config e um resultado identificáveis.
  - A busca no Pi só precisa carregar o `.npy` e o modelo de consulta.
  - Reprocessar os chunks não destrói o trabalho de transcrição das imagens.
- **Negativas:**
  - Mais pastas e convenções a seguir.
  - Os imports dependem do ajuste de `sys.path` nos scripts.
  - Os índices em `data/indices/` precisam ser regerados sempre que `processed/chunks.jsonl` mudar,
    porque a correspondência é feita pela ordem em `ids.json`.
- **A acompanhar:**
  - Decidir se `data/indices/` e `results/` entram no `.gitignore`.
  - Registrar em ADRs próprias as escolhas de modelo de embedding, de quantização e de métricas.
