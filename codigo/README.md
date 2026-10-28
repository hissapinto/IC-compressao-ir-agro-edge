# RAG offline agrícola (500 Perguntas, 500 Respostas — Embrapa)

Código da IC "Impacto da compressão de modelos de linguagem na qualidade da recuperação da
informação em domínio agrícola sob restrições de hardware".

## Estrutura

```
data/
  raw/          ponteiro para os dados brutos (Embrapa/500PerguntasRespostas)
  processed/    chunks.jsonl (versão final, com transcrições das imagens)
    auxiliares/ chunks_sem_divisao.jsonl, chunks_sem_imagens.jsonl, chunks_alterados.jsonl, imagens_transcritas.csv, relatorio.csv
  golden/       perguntas de teste com o chunk correto
  indices/      um subdiretório por variante (ex.: e5-small-fp32/, e5-small-int8/)
src/            funções reutilizáveis (não rodam sozinhas)
  chunking.py   gera os chunks a partir dos txt
  embeddings.py load_model, encode
scripts/        os "mains" que se executa; importam de src/
configs/        um .yaml por experimento (modelo, quantização, k)
results/        métricas e tempos de cada experimento
notebooks/      análises e gráficos
docs/adr/       registros de decisão (ADRs)
```

Rodar sempre a partir desta pasta, com o `.venv` ativo.

## Pipeline

```
python src/chunking.py              # txt -> auxiliares/chunks_sem_imagens.jsonl (já dividido em até 512 tokens)
python scripts/dividir_chunks.py    # divide o chunks.jsonl final (com imagens) em até 512 tokens
python scripts/indexar.py           # chunks.jsonl -> data/indices/e5-small-fp32/
python scripts/buscar.py "consulta" -k 5 --cultura soja
```