# Datasets para RAG offline em culturas brasileiras

20 de outubro de 2026 · Isabela

A melhor base para começar é a coleção "500 Perguntas, 500 Respostas" da Embrapa (milho, feijão e mandioca): está em português, foi escrita para o pequeno produtor, já vem dividida em perguntas e respostas e cabe com folga no Raspberry Pi 4.

## Comparativo

Não encontrei nenhum dataset pronto (por exemplo no Hugging Face) de perguntas e respostas em português sobre culturas como milho ou mandioca. As opções reais são livros e boletins abertos da Embrapa, um corpus de documentos da Embrapa já extraído, e recursos de apoio.

| Candidato | Conteúdo | Tamanho | Formato | Licença | Serve para |
| --- | --- | --- | --- | --- | --- |
| [500 Perguntas, 500 Respostas: Milho, 2ª ed. 2013](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/1124498) | ~500 perguntas de produtores respondidas por pesquisadores da Embrapa Milho e Sorgo, em 21 capítulos | ePub ~4 MB (1ª ed. 2011: [PDF 9,28 MB, 338 p.](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/921542)) | ePub ou PDF | Acesso aberto; Infoteca indica CC BY-NC (ND ou SA, ver abaixo) | Corpus principal + gabarito de avaliação |
| [500 Perguntas, 500 Respostas: Feijão, 2014](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1014894/1/Feijao2014500P500R.pdf) | Mesmo formato, cultura do feijão | Não confirmado | PDF | Igual ao acima | Corpus principal |
| [500 Perguntas, 500 Respostas: Mandioca, 2006](https://www.infoteca.cnptia.embrapa.br/handle/doc/120506) | Mesmo formato, Embrapa Mandioca e Fruticultura; há registro mais novo ([doc 1132151](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/1132151)) | Não confirmado | PDF | Igual ao acima | Corpus principal |
| Mesma coleção: [sorgo](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1015482/1/500-perguntas-sorgo.pdf), [banana](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/952716/1/500perguntasbanana.pdf), [abacaxi](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/976862/1/500perguntasabacaxi.pdf), [mamão](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/976856/1/500perguntasmamao.pdf), [maracujá](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1061917/1/Maracuja500perguntas500respostasebookpdf.pdf) | Outras culturas de pequeno produtor; não há volume de melão | Não confirmado | PDF | Igual ao acima | Ampliar o corpus depois |
| [CGIAR/embrapa-ai-documents](https://huggingface.co/datasets/CGIAR/embrapa-ai-documents) (Hugging Face) | Documentos de pesquisa da Embrapa já extraídos em texto, ~81% português, com metadados (título, idioma, palavras-chave, direitos) | Card cita 130.922 docs e ~11,8 M tokens, mas a faixa de tamanho diz 10K–100K linhas | Parquet | Repositório CC BY 4.0, mas cada documento tem seu campo `rights` e muitos parecem CC BY-NC-ND | Filtrar por cultura e ter muito texto sem fazer OCR |
| [br-llm-data/embrapa-corpus-cs](https://huggingface.co/datasets/br-llm-data/embrapa-corpus-cs) | Corpus Embrapa sem descrição pública | ~1,25 GB, 100K–1M linhas | Parquet | Exige aceitar termos de acesso | Só exploração; grande demais para começar |
| Boletins de sistema de produção: [melão (1980, 28 p.)](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/922237/1/472121.pdf), [feijão, milho e mandioca (EMATER-BA, 1982)](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/908310/1/EMATERDOCUMENTOS05BASISTEMADEPRODUCAOPARAFEIJAOMILHOEMANDIOCACDU633493.pdf), [melão no Vale do São Francisco (2017)](https://embrapa.br/busca-de-publicacoes/-/publicacao/1075706/sistema-convencional-de-producao-de-melao-no-submedio-do-vale-do-sao-francisco) | Recomendações técnicas em texto corrido | Dezenas de páginas cada | PDF (os antigos são digitalizados) | Infoteca, igual ao acima | Única fonte achada para melão |
| [MilkQA](https://arxiv.org/abs/1801.03460) | 2.657 perguntas e respostas reais do SAC da Embrapa, em português | Pequeno | Não confirmado | Não confirmada | Avaliação de IR em português agro, mas é sobre leite |
| [AGROVOC](https://aims.fao.org/standards/agrovoc/access-agrovoc) (FAO) | Tesauro agrícola com rótulos em português (ex.: mandioca, aipim, macaxeira) | Centenas de MB em RDF | RDF/SKOS, JSON-LD | CC BY nas línguas da FAO; o português pertence à instituição autora | Expandir a query com sinônimos, não é corpus |

## Recomendação

Comece com os três livros da coleção 500 Perguntas, 500 Respostas: milho, feijão e mandioca. São cerca de 1.500 pares pergunta-resposta escritos para o pequeno e médio produtor.

- **Chunking quase de graça.** Cada par pergunta-resposta vira um chunk natural, sem precisar decidir janela ou sobreposição no primeiro teste. Depois dá para comparar com chunks de tamanho fixo.
- **Gabarito de avaliação pronto.** A pergunta do livro é a query e a resposta dela é o chunk relevante, então dá para medir MRR@10 como no seu doc-ranker. Para não ficar fácil demais, reescreva parte das perguntas com outras palavras (ex.: "quando plantar milho no Nordeste" em vez do texto exato).
- **Ligação direta com a ideia 1.** A API Responde Agro, que está na sua pasta Embrapa, busca justamente nos livros dessa coleção. Com o mesmo conteúdo nos dois caminhos, você compara a busca online da Embrapa com o seu índice offline usando as mesmas queries.
- **Prefira o ePub ao PDF.** O ePub do milho (2013) é HTML por dentro, então o texto sai limpo, sem OCR nem quebra de colunas.

Para melão não há volume da coleção. Se quiser essa cultura, os boletins de sistema de produção da tabela servem, mas o texto é corrido e o chunking precisa ser por tamanho. O corpus CGIAR no Hugging Face é o próximo passo para escalar, filtrando por palavra-chave da cultura.

Sobre licença: o material da Infoteca é não comercial, o que cobre uma IC. Evite publicar os chunks em repositório público e cite as obras; publique só o código e o script que baixa e processa os livros.

## Cabe no Raspberry Pi 4

Sim, com folga. O gargalo é o modelo de embedding, não os dados. Os números abaixo são estimativas minhas, não medições.

| Cenário | Chunks | Índice (vetores float32) | Observação |
| --- | --- | --- | --- |
| 3 livros, multilingual-e5-small (384 dim) | ~1.500 | ~2,3 MB | Modelo ~470 MB em fp32, menos com int8 |
| 3 livros, multilingual-e5-base (768 dim, o do doc-ranker) | ~1.500 | ~4,6 MB | Modelo ~1,1 GB em fp32; cabe nos 4 GB, mas sobra menos para um SLM |
| Corpus CGIAR inteiro, ~300 tokens por chunk | ~40.000 | ~120 MB (768 dim) | Gere os embeddings no Mac e copie o índice; no Pi isso levaria horas |
| Baseline BM25 (SQLite FTS5 ou rank_bm25) | qualquer | poucos MB | Sem modelo; bom para comparar com o denso |

O cartão de 64 GB não é limitação em nenhum cenário. Na RAM, o que pesa é manter o embedder e o SLM carregados juntos, então o e5-small quantizado deixa mais espaço para o modelo de geração.

## O que não consegui confirmar

Não consegui abrir as páginas do Hugging Face nem da Infoteca diretamente daqui, então os dados da tabela vêm dos resultados de busca. Vale conferir estes pontos antes de baixar.

- [ ] Licença exata da Infoteca: as buscas citam tanto CC BY-NC-ND 4.0 quanto CC BY-NC-SA 4.0. Confira o rodapé da página de cada livro.
- [ ] Tamanho real do corpus CGIAR: o card cita 130.922 documentos e 11,8 M tokens, o que dá ~90 tokens por documento. Pode ser que boa parte seja só resumo; abra algumas linhas antes de contar com ele.
- [ ] Tamanho dos PDFs de feijão e mandioca e se há versão ePub deles.
- [ ] Onde baixar o MilkQA e sob qual licença; o artigo diz que é público, mas não achei o link.
- [ ] Se os termos da API Responde Agro permitem usar as respostas dela como gabarito na comparação com a ideia 1.

## Fontes

- [Infoteca: Milho, 500 Perguntas 500 Respostas, 2ª ed. (ePub)](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/1124498)
- [Infoteca: Milho, 1ª ed. (PDF)](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/921542)
- [Infoteca: Feijão, 500 Perguntas 500 Respostas (PDF)](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1014894/1/Feijao2014500P500R.pdf)
- [Infoteca: Mandioca, 500 Perguntas 500 Respostas](https://www.infoteca.cnptia.embrapa.br/handle/doc/120506)
- [Hugging Face: CGIAR/embrapa-ai-documents](https://huggingface.co/datasets/CGIAR/embrapa-ai-documents)
- [Hugging Face: br-llm-data/embrapa-corpus-cs](https://huggingface.co/datasets/br-llm-data/embrapa-corpus-cs)
- [MilkQA (arXiv 1801.03460)](https://arxiv.org/abs/1801.03460)
- [FAO: acesso ao AGROVOC](https://aims.fao.org/standards/agrovoc/access-agrovoc)
- [AgroAPI: Responde Agro](https://www.portal.agroapi.cnptia.embrapa.br/api-docs/responde-agro)
- [GPT-4 as an Agronomist Assistant? (usa a coleção 500 Perguntas como avaliação)](https://arxiv.org/abs/2310.06225)
