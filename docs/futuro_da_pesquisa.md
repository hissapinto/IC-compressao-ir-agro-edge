# Futuro da pesquisa: possibilidades e argumentos

Caminhos possíveis para a IC e os argumentos por trás das escolhas já feitas. Nada aqui está
decidido: a ordem e o escopo dependem dos resultados intermediários e da conversa com o orientador.
O passo a passo prático do Pi está em [`checklist_IR_pi4.md`](checklist_IR_pi4.md), e os modelos
candidatos em [`Modelos_embedding_e_gerador.md`](Modelos_embedding_e_gerador.md).

## Ponto de partida

- Corpus: 20.665 chunks (20.381 perguntas) dos 41 livros da coleção *500 Perguntas, 500 Respostas*,
  só com pares que vêm de texto, gerados por um pipeline 100% reproduzível e sem IA.
- Busca densa com o `multilingual-e5-small` (fp32), pela linha de comando.
- Conjunto de avaliação (em revisão) e medição do índice: ver o item 0.
- Pergunta de pesquisa: quanto a compressão dos modelos (quantização, modelos menores) afeta a
  qualidade da recuperação num hardware limitado, com o Raspberry Pi 4 como bancada que imita um
  celular intermediário.
- Recursos: o Mac da Isabela para o dia a dia e um computador mais potente no laboratório da
  faculdade, para o que pesar mais (fine-tuning, reindexar várias variantes, rodadas longas).

## Possibilidades

### 0. Medição do índice atual: feita, e o que ela indica
A avaliação do `multilingual-e5-small` (fp32) sobre o corpus atual está em
`codigo/results/e5-small-fp32/` (como rodar: `codigo/README.md`, seção Avaliação). As consultas
ainda estão em revisão, então os números podem mudar um pouco depois dela.

| Conjunto (205 perguntas) | MRR@10 | Recall@1 | Recall@10 | Recall@10 no pior caso | Livro certo no 1º |
| --- | ---: | ---: | ---: | ---: | ---: |
| Originais | 0,95 | 0,91 | 0,99 | | 0,94 |
| Reescritas (3 versões) | 0,62 | 0,55 | 0,79 | 0,45 | 0,80 |
| Vagas (3 versões) | 0,38 | 0,29 | 0,54 | 0,16 | 0,64 |

Reescritas e vagas: média das três versões de cada pergunta, depois média entre as perguntas. O
**pior caso** (*worst-case*) pega, em cada pergunta, a versão em que a busca foi pior.

O que os números dizem:
- **O código e o índice estão certos.** As perguntas originais acham o chunk certo em 99% dos
  casos no top 10. Dos 18 casos em que a original não ficou em 1º, a maioria perdeu para uma
  pergunta igual ou quase igual em outro livro (ou no mesmo livro) (por exemplo, "O que é produção integrada?" existe
  em trigo e em banana; "Onde os fungos sobrevivem de uma safra para outra?", em maçã e em pera).
- **Com outras palavras, o desempenho cai; com a consulta vaga, cai muito.** A reescrita põe a
  resposta certa em 1º em 55% das vezes e no top 10 em 79%; a consulta vaga, em 29% e 54%. Esses são
  os números que importam para o uso real. Nas vagas, 21% das respostas certas ficam abaixo da 200ª
  posição.
- **A busca depende de repetir as palavras do livro.** A versão que usa o termo do livro acha a
  resposta no top 10 em 98% das reescritas e 95% das vagas; a que só descreve, sem o termo, em 53% e
  32%. No pior caso, o top 10 cai para 45% (reescritas) e 16% (vagas).
- **O erro costuma ser "vizinho":** mesmo quando a pergunta certa não vem em 1º, o 1º colocado é do
  livro certo em 64% (vagas) a 80% (reescritas) das vezes. Isso favorece soluções que reordenam perto do topo (reranker,
  busca híbrida) mais do que trocar o modelo inteiro.
- **A detecção de fora do escopo por limiar não funciona bem com o score cru.** O score do 1º separa bem as perguntas
  de outro assunto (AUROC 0,97 contra reescritas + vagas), mas não tão bem as de agricultura fora dos
  livros (AUROC 0,83). Para aceitar no máximo 10% das consultas fora do escopo, o limiar recusaria 31%
  das válidas. A diferença entre o 1º e o 2º colocados ajuda pouco nas consultas realistas
  (AUROC 0,63), e o score do 1º prevê razoavelmente, mas não o bastante, se a resposta está certa
  (AUROC 0,80). As fora do
  escopo com score mais alto são de temas vizinhos de livros que existem (broca-da-cana, cacau,
  vermifugação de equinos, ração de frango).
- **A anisotropia é forte:** dois chunks sorteados têm cosseno médio de 0,81, e o vetor médio do
  corpus tem norma 0,90 (num espaço sem anisotropia, seria perto de 0). As medianas do score do 1º
  colocado de todos os conjuntos ficam entre 0,84 e 0,92.

Próximos passos que saem daqui (a decidir com o orientador):
1. Terminar a revisão do conjunto de avaliação e rodar de novo com `--so-aprovadas`.
2. Decidir como tratar as perguntas repetidas entre livros: aceitar qualquer pergunta idêntica como
   acerto, ou relatar à parte.
3. Ablação de centralização dos vetores (E5 puro × centralizado), olhando sobretudo a separação das
   consultas de agricultura fora dos livros e a diferença 1º−2º.
4. BM25 e busca híbrida, e talvez um reranker sobre o top 10.

### 1. Conjunto de avaliação (golden set)
Está em `codigo/data/golden/`, em revisão:
- 205 perguntas sorteadas entre os 41 livros (5 por livro, semente 42, `scripts/sortear_golden.py`);
- cada uma com **o mesmo gabarito** (`id_original`) em sete consultas: a original, três reescritas
  com outras palavras e três consultas vagas, como a de quem não sabe bem o que procurar. Em cada
  trio, a versão 1 é a revisada pela Isabela, a 2 usa o termo do livro e a 3 só descreve, sem o termo;
- 100 consultas fora do escopo: 50 de outro assunto e 50 de agricultura fora dos 41 livros;
- reescritas, vagas e fora do escopo foram escritas com LLM e precisam de revisão (coluna de status).

O que ainda pode entrar:
- perguntas reais de produtores (SAC, fóruns);
- seguir a proporção de temas e de tipos de pergunta do corpus (ver a EDA);
- casos difíceis, como livros parecidos (gado de corte × gado de corte no Pantanal).

### 2. Busca lexical e híbrida
BM25 com SQLite FTS5 (sem acentos; talvez com stemmer RSLP) e fusão com a densa por Reciprocal
Rank Fusion (RRF). O BM25 é leve e costuma ir bem em termos técnicos (nomes de pragas, produtos).

### 2b. Perguntas parecidas entre livros: como reduzir o erro de livro
A busca erra muito quando livros diferentes têm perguntas parecidas: nas reescritas, 124 dos 277
erros de 1º lugar foram para outro livro; nas vagas, 220 de 436. São dois casos:
1. **A consulta cita a cultura** ("broca no milho") e a busca traz outro livro: dá para corrigir.
2. **A consulta não cita a cultura** ("O que é produção integrada?") e a pergunta existe em mais de um
   livro: é ambígua de verdade; nenhum peso resolve.

Possibilidades, da mais barata para a mais cara:
- **Reforço por metadados** (*metadata boosting*): detectar a cultura na consulta (lista de nomes e
  sinônimos por livro: "mandioca", "aipim", "macaxeira") e somar um bônus pequeno (por exemplo,
  +0,01) ao score dos chunks dessa cultura. Por causa da anisotropia, centésimos já reordenam. A versão
  rígida, **filtragem por metadados** (*metadata filtering*: buscar só no livro detectado), erra feio
  quando o assunto está em outro livro (a broca-da-cana aparece no livro do milho).
- **Busca híbrida com BM25** (item 2): o nome da cultura vira um termo que pesa.
- **Busca hierárquica** (*hierarchical retrieval*): escolher primeiro os 2 ou 3 livros mais
  prováveis (consulta × vetor médio de cada livro) e buscar dentro deles.
- **Reranker** (item 7): lê consulta e chunk juntos e percebe que "no milho" importa.
- **Fine-tuning do embedding** com aprendizado contrastivo (*contrastive learning*, por exemplo a
  *MultipleNegativesRankingLoss* do sentence-transformers) e **negativos difíceis** (*hard
  negatives*): o chunk parecido de outro livro como exemplo de "errado". Também ataca a dependência
  das palavras do livro (adaptação de domínio, *domain adaptation*). Pares de treino gerados com LLM,
  **sem** as 205 perguntas do golden set (evitar *data leakage*; separar por `id_original`). O
  e5-small treina em horas; o computador do laboratório serve para isso. Vira mais uma variável da
  pesquisa (puro × ajustado, e o ajustado quantizado): conversar com o orientador sobre o escopo.
- **Caso 2:** na avaliação, decidir se pergunta idêntica de outro livro conta como acerto; no sistema,
  quando os primeiros resultados vêm de livros diferentes com scores quase iguais, fazer um **pedido
  de esclarecimento** (*clarifying question*: "trigo ou banana?").

Como medir: cada uma como **ablação**, separando as consultas que citam a cultura das que não citam
(no golden set, pelo menos uma versão de cada pergunta cita a cultura). Ordem sugerida: metadados,
depois BM25/reranker, e o fine-tuning por último, com uma linha de base clara.

### 3. Avaliação e ablações
Métricas: Recall@1/5/10, MRR@10 e nDCG@10. Ablações possíveis:
- BM25 × densa × híbrida;
- com e sem cabeçalho (cultura e capítulo) no texto codificado;
- **só a resposta × pergunta + resposta** no texto codificado (ver argumentos abaixo);
- com e sem introduções, e com e sem as respostas que dependem de imagem (o filtro é reversível);
- limite de divisão dos chunks (por exemplo, 256 × 512 tokens).

### 4. Variantes comprimidas do embedding (o núcleo da pergunta de pesquisa)
E5 small/base/large em FP32, FP16, INT8 e INT4 (ONNX), e possivelmente EmbeddingGemma-300M, Serafim
(nativo em português) ou granite-embedding. Cada variante tem índice próprio em
`data/indices/<modelo>-<precisão>/` e resultados com o mesmo nome em `results/`.

### 5. Execução no Raspberry Pi 4
ONNX Runtime, medindo latência por consulta (mediana e p95), RAM, tamanho do índice e tempo de
carga. Os formatos escolhidos (ONNX, GGUF) também rodam em Android e iOS.

### 6. IR desenvolvido × API Responde Agro (Embrapa)
A Responde Agro é a API da Embrapa que busca nos mesmos livros da coleção 500 Perguntas: recebe um
texto e devolve pares pergunta-resposta ordenados por relevância (gratuita, até 100.000
requisições por mês). Como as duas buscam na mesma base, dá para comparar diretamente o que cada
uma traz de resposta para a mesma pergunta.

Como testar:
- Enviar as consultas do golden set para os dois sistemas e guardar o top 10 de cada um.
- **Ligar os resultados da API aos nossos chunks:** a API devolve o par em HTML, então é preciso
  casar cada resultado com um `id_original` (pelo livro e pelo texto da pergunta). Assim as duas
  listas ficam comparáveis com o mesmo gabarito.
- **Métricas iguais para os dois:** Recall@k, MRR@10 e nDCG@10, contando acerto pelo `id_original`.
- **Concordância:** quantas vezes o primeiro resultado é o mesmo, e quanto os top 10 se sobrepõem.
  Onde os dois discordam, olhar caso a caso qual resposta ajuda mais o produtor.
- **Por tipo de consulta:** perguntas reescritas, perguntas fora do escopo (o que cada um devolve
  quando não há resposta) e perguntas com termos técnicos.
- **Custo e condições:** latência de cada um (a API depende da rede; o nosso roda local), e o que
  acontece sem internet.
- **Comparação justa:** a API inclui as respostas com imagem e as introduções, que estão fora do
  nosso corpus. Para não penalizar nenhum dos dois, as consultas do golden set devem ter resposta
  nos pares que vêm de texto, ou os resultados da API fora do nosso corpus devem ser contados à
  parte.

Pendências antes de começar: confirmar no portal AgroAPI a autenticação (OAuth2), a URL base e o
formato do corpo do `POST /_search/template`, que os PDFs salvos não detalham.

Leitura possível do resultado: se o nosso IR ficar perto da API (ou melhor), com compressão e sem
internet, isso responde a pergunta de pesquisa a favor do uso offline. Se ficar abaixo, a
diferença mostra quanto se perde e onde.

### 7. Reranker (opcional)
Um cross-encoder sobre o top 10. Só vale se couber no tempo de resposta do Pi.

### 8. Gerador (extensão)
Um modelo pequeno (Qwen3 0.6B/1.7B, Gemma 3 1B, Llama 3.2) com fine-tuning LoRA no estilo das
respostas da Embrapa, quantizado em GGUF. Recebe os chunks recuperados e escreve a resposta.

**Montagem do contexto: recuperar a resposta completa.** Quando uma parte de uma resposta dividida
aparece no topo, o ideal é juntar todas as partes com o mesmo `id_original` (na ordem `_p1`, `_p2`...)
e entregar ao gerador a pergunta com a resposta inteira. A técnica se chama **recuperação do
documento pai** (*parent document retrieval* ou *small-to-big retrieval*): busca nas partes menores
(vetores mais precisos), entrega a unidade completa. Não muda as métricas de busca, que já contam
por `id_original`; muda só o contexto do RAG. Cuidado com a **janela de contexto** (*context window*)
dos geradores pequenos: uma resposta pode ter até 6 partes de até 512 tokens (cerca de 3 mil tokens).
Opções de **orçamento de tokens** (*token budget*): juntar as partes só da 1ª pergunta e cortar as das
seguintes se faltar espaço, ou trazer só as partes vizinhas da encontrada. Só 267 respostas foram
divididas; nas outras, o chunk já é a resposta completa.

### 9. Voltar com o que ficou fora
Se o orientador liberar, as respostas que dependem de imagem podem voltar (as transcrições estão em
`legado/`), e as introduções podem entrar como um tipo separado de chunk.

## Argumentos e decisões discutidos

### Por que a coleção 500 Perguntas e não as APIs
Roda 100% offline, está em português e no registro do produtor, cada par pergunta-resposta já é um
chunk natural, e as próprias perguntas servem de base para o golden set. As APIs dependem de
internet e têm limites de requisição. A Responde Agro fica como referência de comparação online.

### Por que só os pares que vêm de texto
Decisão do orientador, oficial até segunda ordem: introduções e respostas cuja informação está numa
imagem saem do corpus. As transcrições das imagens foram feitas com IA e não são reproduzíveis por
script. O filtro é por lista e reversível, então dá para medir o efeito depois.

### Por que reprodutibilidade total
Do ePub/PDF ao `chunks.jsonl`, tudo roda por script, e as fontes são conferidas por SHA-256. Qualquer
pessoa chega aos mesmos arquivos, byte a byte, e qualquer diferença nos resultados vem do
experimento, não dos dados.

### Passage e query
Só os chunks do livro são "passage". "Query" é a pergunta que o usuário digita na hora da busca.
Os dois passam pelo mesmo modelo:
- **Indexação (uma vez, no Mac):** cada chunk vira `"passage: " + texto` e um vetor de 384 números.
- **Busca (a cada pergunta):** a consulta vira `"query: " + pergunta` e um vetor do mesmo tamanho,
  comparado com todos os vetores salvos pelo produto escalar (igual ao cosseno, porque os vetores
  são normalizados). Os maiores scores são os resultados.

O E5 foi treinado com pares assimétricos (pergunta curta × trecho que responde), e os prefixos
dizem ao modelo qual é o papel de cada texto. O prefixo não é gravado no `chunks.jsonl`: é posto só
na hora de codificar. O custo pesado fica na indexação; na busca só a consulta é codificada, e é
isso que permite rodar no Pi ou no celular.

### Para que serve a pergunta original dentro do chunk
É preciso separar o que é **codificado** do que é **mostrado**:
- **Na busca:** o vetor de cada chunk é feito com cultura, capítulo, pergunta e resposta. A consulta
  do usuário é uma pergunta, então tende a se parecer mais com a pergunta do livro do que com a
  resposta. Por exemplo, "quando plantar soja no cerrado?" combina com "Qual a época de semeadura da
  soja no Cerrado?", enquanto a resposta pode nem usar essas palavras.
- **No resultado:** `pergunta` e `resposta` são campos separados, então a interface (ou o gerador)
  pode mostrar só a resposta. Mostrar a pergunta junto ajuda o produtor a conferir se o resultado é
  sobre o que ele perguntou.
- **Na avaliação:** as perguntas originais são o ponto de partida do golden set.

A aposta é que pergunta + resposta ganha de só a resposta, mas isso deve ser medido (ablação do item 3).

### Por que o golden set precisa de perguntas reescritas
Como a pergunta original está no texto codificado, uma consulta igual a ela cai quase em cima do
chunk certo, e a avaliação fica fácil demais (sobretudo para o BM25). Reescrever com outras
palavras aproxima o teste do uso real.

### Chunks divididos continuam ligados à mesma pergunta
O E5 aceita no máximo 512 tokens, então 267 respostas longas foram divididas em 2 a 6 partes. Todas
as partes têm o mesmo `id_original`, os mesmos metadados (número, pergunta, cultura, capítulo) e
repetem o cabeçalho com a pergunta no texto codificado; só o trecho da resposta muda. Por isso o
filtro tira as partes juntas, e a avaliação deve contar acerto pelo `id_original`: achar qualquer
parte da pergunta certa vale.

### Normalização L2: o que ela faz (e o que não faz)
A normalização só ajusta cada vetor para ter tamanho 1, ou seja, tira a **magnitude** e mantém a
**direção**. Ela não muda o ângulo entre os vetores, então **não muda a ordem do ranking** pelo
cosseno e não "desensibiliza" a resposta. O que ela traz é praticidade: com vetores de tamanho 1, o
produto escalar já é o cosseno, e a busca vira uma multiplicação de matriz.

### Anisotropia: por que todos os scores ficam altos e parecidos
Modelos como o E5 concentram os vetores num "cone" estreito do espaço (anisotropia): mesmo textos
sem relação têm cosseno alto. Com um corpus só de agricultura, isso se soma ao aperto de domínio, e
todos os chunks ficam perto de qualquer consulta do nicho. No nosso índice, dois chunks sorteados
têm cosseno médio de 0,81, e até perguntas sem relação com agricultura têm o 1º colocado em torno
de 0,84.

Isso **não quebra a busca**, porque o que importa é a **ordem** dos scores, não o valor. Mas pode
atrapalhar quando a diferença entre o chunk certo e os vizinhos é pequena, e torna inútil um limiar
fixo de score (por exemplo, para a abstenção em perguntas fora do escopo).

A medição do item 0 mostrou que isso atrapalha a detecção de fora do escopo: o score do 1º separa mal as consultas
de agricultura fora dos livros, e a diferença 1º−2º não separa nada. As opções são:
- **Centralizar os vetores:** subtrair a média do corpus de cada vetor antes de normalizar. Abre o
  cone e espalha os scores, sem treinar nada. A consulta recebe a mesma média subtraída.
- **BM25 / busca híbrida:** a busca lexical não sofre de anisotropia e desempata termos técnicos.
- **Reranker:** reordena o top 10 lendo consulta e chunk juntos.
- **Fine-tuning do embedding:** ensina o modelo a separar melhor textos de agricultura.

Ablação proposta: **E5 puro × E5 centralizado × híbrido**, com as mesmas consultas do conjunto de avaliação.

### Por que o Raspberry Pi 4 como bancada
Tem recursos parecidos com os de um celular intermediário (CPU ARM, poucos GB de RAM, sem GPU útil
para ML) e é mais fácil de instrumentar e medir. O trabalho pesado (indexar) fica no Mac; o Pi só
recebe o índice pronto.
