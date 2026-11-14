# Legado

Arquivos que **não fazem parte do pipeline atual** e ficam só como registro histórico. Nada aqui é
lido pelos scripts de `codigo/`. A estrutura de pastas espelha a do projeto, para ficar claro de onde
cada coisa veio.

| Caminho | O que é | Por que é legado |
| --- | --- | --- |
| `500PerguntasRespostas/dados/txt/` | Os 41 txt da primeira conversão, feita numa conversa com o Claude (20 a 22/10/2026). Restaurados do git (commit anterior ao `446dbb4`) | Substituídos em 03/11/2026 pela saída do `codigo/scripts/converter_para_txt.py`, que é reproduzível |
| `500PerguntasRespostas/dados/comparacao_03-11/` | Saída da primeira execução do conversor no Mac (03/11/2026), antes dos últimos ajustes do extrator de ePub; `comparacao.csv` compara os pares com os txt acima | Era a antiga pasta `dados/txt_reproduzido/`. Fica como prova da comparação com a conversão antiga |
| `codigo/data/processed/auxiliares/imagens_transcritas.csv` | As 140 transcrições de imagens no formato antigo (livro, página do PDF, transcrição) | Substituído pelo `transcricoes_imagens.csv` (também no legado, abaixo) |
| `codigo/data/processed/auxiliares/chunks_alterados.jsonl` | Os 113 chunks com as transcrições coladas à mão na primeira versão | Substituído pelo `inserir_transcricoes.py` (também no legado, abaixo) |
| `codigo/scripts/historico/ligar_transcricoes_imagens.py` | Script usado uma vez para montar o `transcricoes_imagens.csv` a partir dos dois arquivos acima | Já cumpriu o papel; os caminhos dentro dele são os da época |
| `codigo/docs/preparacao_dos_dados.md` | Relato histórico da preparação: conversão com IA (outubro), triagem e transcrição das imagens, comparação de 03/11/2026 | Substituído por um documento só com o pipeline atual, no mesmo caminho em `codigo/docs/` |
| `codigo/data/processed/transcricoes_imagens.csv` | As 140 transcrições de imagens feitas com IA (27/10/2026), cada uma ligada à imagem original (com SHA-256), ao chunk e à posição na resposta | Saiu do pipeline em 14/11/2026: por decisão oficial do orientador, os pares que dependem de imagem ficam fora do corpus, e a transcrição com IA não é reprodutível |
| `codigo/scripts/inserir_transcricoes.py` | Script que inseria as transcrições acima nas respostas (marcando `conteudo_imagem: true`) | Idem. Os caminhos dentro dele são os de quando estava em `codigo/scripts/` |
| `codigo/data/processed/auxiliares/chunks_sem_divisao.jsonl` e `chunks_completo.jsonl` | Os intermediários do pipeline **com** as transcrições (20.595 e 20.887 chunks) | Os atuais, em `codigo/data/processed/auxiliares/`, não têm transcrições (20.595 e 20.885 chunks). O `chunks.jsonl` final é o mesmo nos dois casos |
