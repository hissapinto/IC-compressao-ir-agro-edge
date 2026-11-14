# Futuro da pesquisa: possibilidades e argumentos

Caminhos possíveis para a IC e os argumentos por trás das escolhas já feitas. Nada aqui está
decidido: a ordem e o escopo dependem dos resultados intermediários e da conversa com o orientador.
O passo a passo prático do Pi está em [`checklist_IR_pi4.md`](checklist_IR_pi4.md), e os modelos
candidatos em [`Modelos_embedding_e_gerador.md`](Modelos_embedding_e_gerador.md).

## Ponto de partida

- Corpus: 20.665 chunks (20.381 perguntas) dos 41 livros da coleção *500 Perguntas, 500 Respostas*,
  só com pares que vêm de texto, gerados por um pipeline 100% reproduzível e sem IA.
- Busca densa com o `multilingual-e5-small` (fp32), pela linha de comando.
- Pergunta de pesquisa: quanto a compressão dos modelos (quantização, modelos menores) afeta a
  qualidade da recuperação num hardware limitado, com o Raspberry Pi 4 como bancada que imita um
  celular intermediário.

## Possibilidades

### 1. Conjunto de avaliação (golden set): o passo que destrava o resto
Sem ele não dá para comparar nada. Ideia:
- 200 a 300 perguntas originais **reescritas com outras palavras**, sorteadas entre os livros, com
  o chunk de origem como gabarito;
- algumas perguntas fora do escopo, para ver como o sistema se comporta;
- se possível, perguntas reais de produtores (SAC, fóruns);
- seguir a proporção de temas e de tipos de pergunta do corpus (ver a EDA);
- evitar as perguntas repetidas entre livros, ou aceitar qualquer um dos ids repetidos;
- incluir casos difíceis, como livros parecidos (gado de corte × gado de corte no Pantanal).

### 2. Busca lexical e híbrida
BM25 com SQLite FTS5 (sem acentos; talvez com stemmer RSLP) e fusão com a densa por Reciprocal
Rank Fusion (RRF). O BM25 é leve e costuma ir bem em termos técnicos (nomes de pragas, produtos).

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

### Por que o Raspberry Pi 4 como bancada
Tem recursos parecidos com os de um celular intermediário (CPU ARM, poucos GB de RAM, sem GPU útil
para ML) e é mais fácil de instrumentar e medir. O trabalho pesado (indexar) fica no Mac; o Pi só
recebe o índice pronto.
