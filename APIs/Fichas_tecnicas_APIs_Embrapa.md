# Fichas técnicas — APIs Embrapa (AgroAPI)

Oct 20, 2026 · @Isabela

## Visão geral

As 9 APIs salvas na pasta Embrapa/APIs somam 141 endpoints únicos, mas só 4 delas respondem perguntas de produtor em texto livre: Responde Agro, AgroFit, Bioinsumos e Agritec. As outras pedem entradas estruturadas (coordenadas, código IBGE, perfil de solo, código PDB). Cada ficha abaixo traz utilidade, endpoints, parâmetros, palavras-chave e limites, pensada para virar o "documento" indexado no roteamento por IR.

| API | Pasta | Plano / limite | Domínio | Entrada típica | Endpoints | Relevância para o produtor |
| --- | --- | --- | --- | --- | --- | --- |
| Responde Agro | Gratis | Gratuito, 100.000 req/mês | Perguntas e respostas da Coleção 500 Perguntas 500 Respostas | Texto livre | 2 | Alta |
| AgroFit | Gratis | Gratuito, 100.000 req/mês | Defensivos registrados no Mapa, pragas, plantas daninhas | Nome de praga, cultura, produto | 27 | Alta |
| Bioinsumos | Gratis | Gratuito, 100.000 req/mês | Produtos biológicos e inoculantes registrados no Mapa | Praga, cultura, espécie | 33 | Alta |
| Agritec | Freemium | Teste: 100 requisições | Zarc (época de plantio), cultivares, produtividade, solos | Cultura + município (IBGE) | 22 | Alta |
| ClimAPI | Freemium | Teste: 500 requisições | Previsão do tempo GFS/NOAA, 10 dias | Variável + data + lat/long | 4 | Média |
| SATVeg | Freemium | Teste: 100 req/mês | Séries NDVI/EVI do MODIS desde 2000 | Ponto ou polígono | 3 | Média |
| AgroTermos | Gratis | Gratuito, 100.000 req/mês | Tesauro agrícola (\~55 mil termos) | Termo | 6 | Apoio (expansão de consulta) |
| SmartSolos Expert | Gratis | Gratuito, 100.000 req/mês | Classificação de solo pelo SiBCS | JSON de perfil de solo | 3 | Baixa (uso técnico) |
| BlueStar Sting | Gratis | Gratuito, 100.000 req/mês | Descritores de proteínas do PDB | Código PDB | 41 | Fora do escopo |

Contagem de endpoints inclui `/health` e, no AgroFit e Bioinsumos, ignora as entradas `/search/...` repetidas na documentação.

**Acesso comum a todas.** Todas ficam no portal AgroAPI da Embrapa Agricultura Digital (portal.agroapi.cnptia.embrapa.br). Os PDFs salvos não descrevem autenticação nem URL base. Pelo funcionamento conhecido da plataforma, o acesso é por OAuth2 *client credentials*: cria-se uma aplicação no portal, troca-se a Consumer Key e o Consumer Secret por um token em `https://api.cnptia.embrapa.br/token`, e cada chamada leva `Authorization: Bearer <token>` em `https://api.cnptia.embrapa.br/<api>/v<n>/...`. Isso não está nos arquivos e precisa ser conferido no portal. Respostas em JSON; erros padronizados 400, 401, 404 e 500.

**Como ler os exemplos.** Cada ficha traz exemplos só dos endpoints úteis para o produtor. `{BASE}` é a URL base da API e `{TOKEN}` o token de acesso, os dois a confirmar no portal. Os valores dos parâmetros e as respostas foram copiados dos exemplos da própria documentação. Onde o PDF mostra um campo recolhido, ele aparece como `[ … ]` ou `{ … }`. Onde o PDF não traz exemplo, a ficha diz isso em vez de inventar uma resposta.

## APIs gratuitas

### Responde Agro (v1)

Motor de busca sobre a Coleção 500 Perguntas 500 Respostas da Embrapa: recebe um texto e devolve pares pergunta-resposta ordenados por relevância, já em HTML (com imagens em Base64). É a API mais próxima de "responder uma dúvida do produtor" e a candidata natural a rota padrão quando nenhuma outra casa com a consulta.

- **Base de dados:** livros da coleção 500 Perguntas 500 Respostas (agricultura e pecuária), com perguntas feitas por produtores, associações e cooperativas e respondidas por pesquisadores.
- **Plano:** gratuito, até 100.000 requisições por mês.

| Endpoint | O que recupera | Parâmetros |
| --- | --- | --- |
| `GET /_doc/{id}` | Um par pergunta-resposta específico | `id` (path, obrigatório): ID do par |
| `POST /_search/template` | Busca por conteúdo em um livro ou em todos; também serve para autocompletar perguntas e termos e para listar os IDs dos livros indexados | Corpo JSON de *search template* (estilo Elasticsearch); o PDF salvo não detalha o esquema |

**Exemplo 1: buscar um par pergunta-resposta pelo ID**

O que enviar:

```http
GET {BASE}/_doc/{id}
Authorization: Bearer {TOKEN}
```

O que volta: o par pergunta-resposta em HTML, com imagens em Base64. O PDF não traz um exemplo de resposta nem de ID válido; os IDs vêm dos resultados da busca abaixo.

**Exemplo 2: busca por texto**

O que enviar: o PDF só diz que o corpo é um *search template*. O formato abaixo segue o padrão de *search template* do Elasticsearch e é uma suposição: o nome do template e dos parâmetros precisam ser conferidos no portal.

```http
POST {BASE}/_search/template
Authorization: Bearer {TOKEN}
Content-Type: application/json

{
  "id": "<nome do template de busca>",
  "params": { "query": "como controlar lagarta-do-cartucho no milho" }
}
```

O que volta: lista ordenada de pares pergunta-resposta relacionados ao texto (sem exemplo no PDF).

- **Palavras-chave:** pergunta, resposta, dúvida, como fazer, por que, manejo, cultivo, criação, pecuária, doença, adubo, irrigação, colheita, 500 perguntas, livro, Embrapa responde.
- **Consultas de exemplo:** "como controlar a lagarta-do-cartucho no milho?", "qual o espaçamento do melão?", "quando colher mandioca?".
- **Observações:** o retorno em HTML precisa ser limpo antes de ir para um modelo pequeno. O conteúdo é estático (livros), então também é o melhor candidato a virar corpus offline na ideia 2, se a licença permitir.

### AgroFit (v1)

Banco de todos os defensivos agrícolas, agrotóxicos, produtos fitossanitários e bioinsumos registrados no Ministério da Agricultura e Pecuária (Mapa). Responde "que produto registrado controla esta praga nesta cultura".

- **Plano:** gratuito, até 100.000 requisições por mês.
- **Campos de um produto formulado:** `numero_registro`, `marca_comercial`, `titular_registro`, `produto_biologico`, `classe_categoria_agronomica`, `formulacao`, `ingrediente_ativo`, `ingrediente_ativo_detalhado`, `modo_acao`, `tecnica_aplicacao`, `indicacao_uso` (cultura + praga), `produto_agricultura_organica`, `classificacao_toxicologica`, `classificacao_ambiental`, `inflamavel`, `corrosivo`, `documento_cadastrado`, `url_agrofit`.
- **Paginação:** todas as listagens aceitam `page`.

| Endpoint | O que recupera | Parâmetros principais |
| --- | --- | --- |
| `GET /search/produtos-formulados` | Produtos comerciais filtrados (o endpoint central) | `q`, `praga_nome_cientifico`, `praga_nome_comum`, `cultura`, `marca_comercial`, `titular_registro`, `ingrediente_ativo`, `grupo_quimico`, `numero_registro`, `classe_categoria_agronomica`, `classificacao_ambiental`, `classificacao_toxicologica`, `formulacao`, `modo_acao`, `tecnica_aplicacao`, `produto_biologico`, `produto_agricultura_organica`, `inflamavel`, `corrosivo`, `page` |
| `GET /produtos-formulados` | Lista completa de produtos formulados | `page` |
| `GET /produtos-formulados/{numero_registro}` | Um produto formulado | `numero_registro` (path) |
| `GET /search/produtos-tecnicos` | Produtos técnicos (matéria-prima) filtrados | `q`, `numero_registro`, `marca_comercial`, `titular_registro`, `ingrediente_ativo`, `grupo_quimico`, classificações, `formulacao`, `produto_formulado_marca_comercial`, `produto_formulado_numero_registro`, `produto_formulado_titular_registro`, `page` |
| `GET /produtos-tecnicos`, `GET /produtos-tecnicos/{numero_registro}` | Lista completa / um produto técnico | `page` / `numero_registro` |
| `GET /search/pragas-nomes-comuns`, `GET /search/pragas-nomes-cientificos` | Nomes de pragas que casam com a consulta | `q`, `nome`, `page` |
| `GET /pragas`, `/pragas-nomes-comuns`, `/pragas-nomes-cientificos` | Listas de pragas (insetos e doenças) | `page` |
| `GET /plantas-daninhas`, `/plantas-daninhas-nomes-comuns` | Listas de plantas daninhas | `page` |
| `GET /search/titulares-registros`, `GET /titulares-registros` | Empresas titulares de registro | `q`, `nome`, `page` |
| `GET /search/classes-categorias-agronomicas`, `GET /classes-categorias-agronomicas` | Classes agronômicas (inseticida, fungicida, herbicida...) | `q`, `nome`, `page` |
| `GET /culturas`, `/ingredientes-ativos`, `/marcas-comerciais`, `/formulacoes`, `/modos-acoes`, `/tecnicas-aplicacoes`, `/classificacoes-toxicologicas`, `/classificacoes-ambientais` | Vocabulários para preencher os filtros exatos | `page` |
| `GET /versao`, `GET /health` | Versão dos dados / status da API | — |

**Exemplo 1: produtos registrados contra mosca-branca**

O que enviar (os filtros são opcionais e podem ser combinados; `praga_nome_comum` e `page` usam os valores de exemplo da documentação):

```http
GET {BASE}/search/produtos-formulados?praga_nome_comum=Mosca%20branca&page=1
Authorization: Bearer {TOKEN}
```

O que volta (200), uma lista de produtos; trecho do exemplo da documentação:

```json
[
  {
    "numero_registro": "5810",
    "marca_comercial": [ … ],
    "titular_registro": "Prentiss Química Ltda.",
    "produto_biologico": false,
    "classe_categoria_agronomica": [ … ],
    "formulacao": "SC - Suspensão Concentrada",
    "ingrediente_ativo": [ … ],
    "ingrediente_ativo_detalhado": [ … ],
    "modo_acao": [ … ],
    "tecnica_aplicacao": [ … ],
    "indicacao_uso": [ … ],
    "classificacao_toxicologica": "Categoria 4 - Produto Pouco Tóxico",
    "classificacao_ambiental": "II - Produto Muito Perigoso ao Meio Ambiente",
    "inflamavel": false,
    "corrosivo": false,
    "documento_cadastrado": [ … ],
    "produto_agricultura_organica": false,
    "url_agrofit": "https://agrofit.agricultura.gov.br/agrofit_cons/..."
  }
]
```

**Exemplo 2: um produto pelo número de registro**

```http
GET {BASE}/produtos-formulados/5810
Authorization: Bearer {TOKEN}
```

O que volta: o mesmo formato do exemplo 1, com um único produto na lista.

**Exemplo 3: normalizar o nome da praga antes de buscar**

```http
GET {BASE}/search/pragas-nomes-comuns?q=acaro&page=1
Authorization: Bearer {TOKEN}
```

O que volta (trecho do exemplo da documentação):

```json
[
  { "nome": "Ácaro" },
  { "nome": "Ácaro branco" },
  { "nome": "Ácaro rajado" },
  { "nome": "Ácaro-da-leprose" }
]
```

- **Palavras-chave:** defensivo, agrotóxico, veneno, fitossanitário, inseticida, fungicida, herbicida, acaricida, nematicida, praga, inseto, lagarta, percevejo, pulgão, mosca-branca, ferrugem, fungo, doença, planta daninha, mato, erva daninha, ingrediente ativo, princípio ativo, marca comercial, registro no Mapa, bula, toxicidade, classe toxicológica, agricultura orgânica, carência.
- **Consultas de exemplo:** "qual veneno posso usar contra mosca-branca no melão?", "herbicida registrado para milho", "produto com glifosato".
- **Observações:** filtros marcados como "exatos" exigem o valor literal da lista correspondente, então o roteador precisa normalizar o termo antes da chamada (os endpoints de lista e o AgroTermos ajudam).

### Bioinsumos (v2)

Recorte do AgroFit focado em insumos biológicos registrados no Mapa, em duas famílias: produtos biológicos para controle de pragas, doenças e plantas daninhas, e inoculantes. Responde "existe alternativa biológica para esta praga" e "que inoculante usar nesta cultura".

- **Plano:** gratuito, até 100.000 requisições por mês.
- **Campos de um inoculante:** identificação e data do registro, razão social e UF do fornecedor, tipo, espécie, garantia, natureza física e culturas.

| Endpoint | O que recupera | Parâmetros principais |
| --- | --- | --- |
| `GET /search/produtos-biologicos` | Produtos biológicos filtrados | Mesmos filtros de `/search/produtos-formulados` do AgroFit (`praga_nome_comum`, `cultura`, `ingrediente_ativo`, `produto_agricultura_organica`...) |
| `GET /produtos-biologicos`, `GET /produtos-biologicos/{numero_registro}` | Lista completa / um produto | `page` / `numero_registro` |
| `GET /search/inoculantes` | Inoculantes filtrados | `q`, `atividade`, `cultura`, `cultura_nome_cientifico`, `especie`, `natureza_fisica`, `razao_social`, `registro_produto`, `tipo`, `uf`, `page` |
| `GET /inoculantes`, `GET /inoculantes/{registro_produto}` | Lista completa / um inoculante | `page` / `registro_produto` |
| `GET /inoculantes/tipos`, `/especies`, `/culturas`, `/atividades`, `/naturezas-fisicas`, `/razoes-sociais` | Vocabulários dos filtros de inoculantes | `page` |
| `GET /search/pragas-nomes-comuns`, `/search/pragas-nomes-cientificos`, `/search/titulares-registros`, `/search/classes-categorias-agronomicas` | Buscas auxiliares | `q`, `nome`, `page` |
| Listas: `/pragas`, `/pragas-nomes-comuns`, `/pragas-nomes-cientificos`, `/plantas-daninhas`, `/plantas-daninhas-nomes-comuns`, `/culturas`, `/ingredientes-ativos`, `/marcas-comerciais`, `/formulacoes`, `/modos-acoes`, `/tecnicas-aplicacoes`, `/titulares-registros`, `/classes-categorias-agronomicas`, `/classificacoes-toxicologicas`, `/classificacoes-ambientais` | Vocabulários | `page` |
| `GET /versao`, `GET /health` | Versão dos dados / status | — |

**Exemplo 1: produto biológico para uma praga**

O que enviar:

```http
GET {BASE}/search/produtos-biologicos?praga_nome_comum=Lagarta-da-soja&page=1
Authorization: Bearer {TOKEN}
```

O que volta (200), no mesmo formato do AgroFit; trecho do exemplo da documentação:

```json
[
  {
    "numero_registro": "7815",
    "marca_comercial": [ … ],
    "titular_registro": "Agbitech Controles Biológicos Ltda",
    "produto_biologico": true,
    "classe_categoria_agronomica": [ … ],
    "formulacao": "SC - Suspensão Concentrada",
    "ingrediente_ativo": [ … ],
    "indicacao_uso": [ … ],
    "classificacao_toxicologica": "Não Classificado - Produto Não Classificado",
    "classificacao_ambiental": "IV - Produto Pouco Perigoso ao Meio Ambiente",
    "produto_agricultura_organica": false,
    "url_agrofit": "https://agrofit.agricultura.gov.br/agrofit_cons/..."
  }
]
```

**Exemplo 2: inoculantes para soja**

O que enviar (valores do exemplo da documentação):

```http
GET {BASE}/search/inoculantes?cultura_nome_cientifico=GLYCINE%20MAX&uf=BA&page=1
Authorization: Bearer {TOKEN}
```

O que volta (200), trecho do exemplo da documentação:

```json
[
  {
    "uf": "BA",
    "razao_social": "JCO - INDUSTRIA E COMERCIO DE FERTILIZANTES LTDA - EP…",
    "registro_produto": "BA0004685-3",
    "atividade": "PRODUTOR",
    "tipo": "MICRO-ORGANISMOS PROMOTORES DE CRESCIMENTO DE PLANTAS",
    "especie": [ … ],
    "data_registro": "2020-12-04",
    "garantia": "200000000 UFC/G",
    "natureza_fisica": "SOLIDO",
    "cultura": "Soja",
    "cultura_nome_cientifico": "GLYCINE MAX"
  }
]
```

- **Palavras-chave:** biológico, bioinsumo, controle biológico, inimigo natural, Trichoderma, Bacillus, Beauveria, Metarhizium, baculovírus, inoculante, Bradyrhizobium, Azospirillum, fixação biológica de nitrogênio, orgânico, sustentável, sem veneno, alternativa ao agrotóxico.
- **Consultas de exemplo:** "tem produto biológico para lagarta na soja?", "inoculante para feijão", "controle de nematoide sem químico".
- **Observações:** sobrepõe-se ao AgroFit (que também tem o filtro `produto_biologico`). O roteador deve preferir Bioinsumos quando a consulta tiver termos de "biológico", "orgânico" ou "inoculante".

### AgroTermos (v1)

Tesauro agrícola da Embrapa com cerca de 55 mil termos, formado pela união do Thesagro e do Agrovoc, com relações entre conceitos. Não responde perguntas de produtor; serve como ferramenta do próprio sistema para normalizar termos e expandir consultas.

- **Plano:** gratuito, até 100.000 requisições por mês.

| Endpoint | O que recupera | Parâmetros |
| --- | --- | --- |
| `GET /termo` | Termo ou conceito com nome idêntico | `label` (obrigatório) |
| `GET /termoParcial` | Termos que contêm a string | `label` (obrigatório) |
| `GET /termoById` | Termo pelo identificador | `id` (obrigatório) |
| `GET /termoComRelacoes` | Termo e todos os seus relacionamentos | `label` (obrigatório) |
| `GET /relacoes` | Lista dos tipos de relação do tesauro | — |
| `GET /relacao` | Uma relação pelo nome | `label` (obrigatório) |

**Exemplo: termo e seus relacionamentos (sinônimos e termos ligados)**

O que enviar:

```http
GET {BASE}/termoComRelacoes?label=mandioca
Authorization: Bearer {TOKEN}
```

O que volta: o termo e todas as suas relações com outros termos (200), ou 404 se o termo não existir. O PDF não traz exemplo do JSON de resposta; vale fazer uma chamada de teste e guardar o formato. Para só confirmar que um termo existe, use `GET {BASE}/termo?label=mandioca`; para busca aproximada, `GET {BASE}/termoParcial?label=mandi`.

- **Palavras-chave:** significado, definição, termo, sinônimo, o que é, nome científico, termo relacionado, vocabulário, tesauro, Agrovoc, Thesagro.
- **Consultas de exemplo:** "o que significa capina?", "sinônimos de mandioca" (aipim, macaxeira).
- **Observações:** útil no pipeline de IR para expandir a consulta com sinônimos regionais antes do roteamento. O Agrovoc, uma das fontes, é distribuído pela FAO para download, o que permitiria uma versão offline dessa etapa.

### SmartSolos Expert (v1)

Sistema especialista (em SWI-Prolog) que classifica perfis de solo nos quatro primeiros níveis do Sistema Brasileiro de Classificação de Solos (SiBCS, 5ª edição) ou valida uma classificação já feita.

- **Plano:** gratuito, até 100.000 requisições por mês.

| Endpoint | O que recupera | Parâmetros |
| --- | --- | --- |
| `POST /classification` | Classificação SiBCS dos perfis enviados | Corpo JSON com dados de perfis e horizontes (esquema não detalhado no PDF) |
| `POST /verification` | Classifica e compara com a classificação informada, com resumo de quantos perfis foram validados em cada nível (0 a 4) | Corpo JSON com perfis + classificação prévia |
| `GET /health` | Status | — |

**Exemplo: classificar um perfil**

```http
POST {BASE}/classification
Authorization: Bearer {TOKEN}
Content-Type: application/json

{ … perfis de solo no formato JSON do SmartSolos … }
```

O que volta: a classificação SiBCS de cada perfil até o 4º nível. O PDF salvo não mostra o esquema do corpo nem um exemplo de resposta, então este exemplo fica incompleto até ser conferido no portal.

- **Palavras-chave:** classificação de solo, SiBCS, perfil de solo, horizonte, pedologia, Latossolo, Argissolo, Neossolo, Cambissolo, ordem, subordem.
- **Consultas de exemplo:** "classificar este perfil de solo", "meu laudo diz Latossolo Vermelho, está certo?".
- **Observações:** exige dados de laboratório e descrição de campo; um pequeno produtor raramente terá essas entradas. Baixa prioridade no roteador.

### BlueStar Sting (v1)

Acesso a descritores físico-químicos e estruturais de qualquer estrutura proteica depositada no Protein Data Bank (PDB), a partir do banco STING\_RDB. É uma API de bioinformática e não tem relação com dúvidas de produtor.

- **Plano:** gratuito, até 100.000 requisições por mês.
- **Formato de todos os endpoints:** `GET /descriptors/<descritor>/{pdbCode}`, com `pdbCode` de 4 caracteres (obrigatório) e filtros opcionais como `chainName`, `number`, `insCode`, `nb` (vizinhança: `all`, `gn`, `sw`, `vd`, `wna`), `atomSerial`, `pocketNumber`, `contactType`, `structuralType`. A resposta traz `meta` (nomes das colunas) e `data`.
- **40 descritores:** air, atom, atom-asa, chain, contact, cross-link-order, cross-presence-order, curvature, curvature-atom, density-sponge, distances, dssp, electrostatic-potential, energy-density, entropy-density, epatom, evolutionary-pressure, fpocket, fpocket-atom, graph-descriptor, hssp, hydrophobic-patch, hydrophobicity, ligand-pocket-and-water-contact, mouth, mouth-atom, pocket, pocket-atom, prosite, residue, residue-contacts, rotamer, side-chain-orientation, solvation, space-clash, sting-hssp, stride, structure, unused-contacts, weighted-contact-number. Mais `GET /health`.
- **Palavras-chave:** proteína, PDB, aminoácido, resíduo, estrutura proteica, hidrofobicidade, potencial eletrostático, bioinformática.
- **Observações:** recomendo deixar fora do índice do roteador, ou mantê-la como "distrator" para testar se o IR evita rotas erradas.

## APIs freemium

### Agritec (v2)

Dados e modelos para planejar a safra: janela de plantio pelo Zoneamento Agrícola de Risco Climático (Zarc), cultivares mais aptas por local, estimativa de produtividade e balanço hídrico. Quase tudo depende de uma cultura (`idCultura`) e de um município (`codigoIBGE`), então o roteador precisa extrair esses dois da consulta.

- **Cobertura:** Zarc para cerca de 45 culturas; cultivares do Registro Nacional de Cultivares para 12 culturas (amendoim, arroz, algodão, cevada, feijão, feijão-caupi, girassol, mamona, milho, soja, sorgo, trigo); produtividade e balanço hídrico para 5 (arroz, feijão, milho, soja, trigo). Safras de 2017-2018 a 2026-2027.
- **Plano:** teste gratuito de até 100 requisições; acima disso, pago.

| Endpoint | O que recupera | Parâmetros principais |
| --- | --- | --- |
| `GET /zoneamento` | Datas de plantio por decêndio com risco de perda de 20%, 30% ou 40% | `idCultura`, `codigoIBGE`, `risco` (`20`, `30`, `40`, `todos`) |
| `GET /zoneamento/municipios/{codigoIBGE}/culturas/{idCultura}` | Janela de plantio Zarc para cultura e município | path: `codigoIBGE`, `idCultura` |
| `GET .../culturas/{idCultura}/ciclos` e `.../ciclos/{ciclo}` | Ciclos disponíveis (GRUPO I a VI, PERENE, SEMIPERENE) e janela por ciclo | `ciclo` |
| `GET .../ciclos/{ciclo}/solos`, `/zoneamento/municipios/{codigoIBGE}/solos`, `.../solos/{solo}` | Tipos de solo do Zarc e janela por solo | `solo`: ARENOSO, ARGILOSO, TEXTURA MEDIA, AD1 a AD6 |
| `GET .../culturas/{idCultura}/informacoes-adicionais`, `GET /zoneamento/informacoes-adicionais` | Safra vigente, portaria do Zarc e descrição dos grupos de maturação | path |
| `GET /cultivares` | Cultivares indicadas por safra, cultura e UF | `safra`, `idCultura`, `uf` (obrigatórios); `regiao`, `grupo`, `cultivar`, `obtentorMantenedor`, `dataAtualizacao` |
| `GET /cultivares/{id}` | Uma cultivar | `id` |
| `GET /obtentores` | Empresas obtentoras ou mantenedoras de cultivares | `safra` (obrigatório), `idCultura`, `uf`, `regiao`, `grupo` |
| `GET /produtividade` | Estimativa de produtividade e séries diárias de temperatura, chuva, graus-dia, balanço, déficit e excedente hídrico | `idCultura`, `idCultivar`, `codigoIBGE`, `cad` (água no solo), `dataPlantio`, `expectativaProdutividade`; opcional `latitude`/`longitude` |
| `GET /culturas`, `/culturas/{id}`, `/culturas/{id}/informacoes-adicionais` | Catálogo de culturas e seus IDs | `id` |
| `GET /municipios`, `/municipios/{codigoIBGE}`, `/municipios/{codigoIBGE}/culturas` | Municípios, código IBGE e culturas com Zarc no município | `uf`, `codigoIBGE` |
| `GET /solos`, `/solos/{tipo}` | Tipos de solo | `tipo` |
| `GET /health` | Status | — |

**Exemplo 1: converter município em código IBGE e coordenadas**

```http
GET {BASE}/municipios/3100104
Authorization: Bearer {TOKEN}
```

O que volta (200), exemplo completo da documentação:

```json
{
  "data": {
    "codigoIBGE": 3100104,
    "nome": "ABADIA DOS DOURADOS",
    "uf": "MG",
    "latitude": -18.3528004,
    "longitude": -47.4574013,
    "dataAtualizacao": "2018-05-02"
  }
}
```

**Exemplo 2: janela de plantio pelo Zarc**

O que enviar (valores do exemplo da documentação):

```http
GET {BASE}/zoneamento?idCultura=60&codigoIBGE=3502804&risco=20
Authorization: Bearer {TOKEN}
```

O que volta (200): uma lista de janelas de plantio com risco de até 20%. O PDF mostra os itens recolhidos, então os campos de cada item precisam ser vistos numa chamada real:

```json
{
  "meta": { "totalCount": 18 },
  "data": [ { … }, { … }, … ]
}
```

**Exemplo 3: cultivares indicadas**

O que enviar (`safra`, `idCultura` e `uf` são obrigatórios):

```http
GET {BASE}/cultivares?safra=2026-2027&idCultura=1262&uf=SP
Authorization: Bearer {TOKEN}
```

O que volta (200): `{ "meta": { "totalCount": … }, "data": [ … ] }`, com um objeto por cultivar. Exemplo da documentação para uma cultivar (`GET {BASE}/cultivares/365295`):

```json
{
  "data": {
    "idCultivar": 365295,
    "idCultura": 60,
    "safra": "2021-2022",
    "numeroRnc": "40254",
    "obtentorMantenedor": "AVANTI SEEDS",
    "cultivar": "AV DIGNA RR",
    "cultura": "SOJA",
    "potencialProdutivo": 5500,
    "duracaoCiclo": 100,
    "uf": "SP",
    "grupo": "I",
    "maturacaoFisiologica": 100,
    "floracao": 35,
    "enchimentoGraos": null,
    "sistemaCultivo": null,
    "genetica": null,
    "regiao": "3",
    "grupoBioClimatico": "6,6",
    "observacao": null,
    "dataAtualizacao": "2021-04-23"
  }
}
```

**Exemplo 4: estimativa de produtividade**

O que enviar (valores do exemplo da documentação):

```http
GET {BASE}/produtividade?idCultura=60&idCultivar=24507&codigoIBGE=2112001&cad=70&dataPlantio=2024-05-01&expectativaProdutividade=3
Authorization: Bearer {TOKEN}
```

O que volta (200): séries diárias que começam na data de plantio. O PDF mostra as listas recolhidas:

```json
{
  "data": {
    "produtividadeAlmejada": [ … ],
    "produtividadeMediaMunicipio": [ … ],
    "temperaturaMinima": [ … ],
    "temperaturaMaxima": [ … ],
    "precipitacao": [ … ],
    "grausDia": [ … ],
    "balancoHidrico": [ … ],
    "deficienciaHidrica": [ … ],
    "excedenteHidrico": [ … ],
    "isna": [ … ]
  }
}
```

- **Palavras-chave:** quando plantar, época de plantio, janela de semeadura, calendário agrícola, zoneamento, Zarc, risco climático, seguro rural, Proagro, cultivar, variedade, semente, híbrido, produtividade, rendimento, sacas por hectare, colheita esperada, balanço hídrico, déficit hídrico, seca, município.
- **Consultas de exemplo:** "qual a melhor época para plantar milho em Petrolina?", "que variedade de feijão plantar no Paraná?", "quanto vou colher de soja se plantei em 10 de outubro?".
- **Observações:** `/culturas` e `/municipios` podem ser baixados uma vez e guardados no Raspberry, para converter nomes em IDs sem gastar requisições. O PDF corta os nomes de dois caminhos de ciclo; os nomes acima seguem o padrão dos vizinhos e precisam ser conferidos.

### ClimAPI (v1)

Previsão do tempo por ponto (latitude e longitude) a partir do Global Forecast System (GFS) da NOAA, em quatro medições por dia, até 10 dias à frente e 10 dias para trás, com resolução de cerca de 25 km e atualização a cada 6 horas.

- **Plano:** teste gratuito de até 500 requisições. O FAQ salvo cita um limite de 60.000 requisições mensais nos planos pagos, sem detalhar.
- **Uso dos dados:** as condições da NOAA proíbem reivindicar autoria dos dados, sugerir endosso da NOAA ou apresentar dados modificados como oficiais.

| Endpoint | O que recupera | Parâmetros |
| --- | --- | --- |
| `GET /ncep-gfs` | Lista das variáveis disponíveis | — |
| `GET /ncep-gfs/{variavel}` | Datas de execução do GFS disponíveis para a variável | `variavel` |
| `GET /ncep-gfs/{variavel}/{data}/{longitude}/{latitude}` | Série de previsão da variável no ponto | `variavel`, `data` (aaaa-mm-dd), `longitude`, `latitude` (graus decimais; atenção à ordem) |
| `GET /health` | Status | — |

| Variável | Significado | Unidade |
| --- | --- | --- |
| `apcpsfc` | Precipitação acumulada | mm por 6 h |
| `tmax2m`, `tmin2m` | Temperatura máxima e mínima a 2 m | °C |
| `tmpsfc` | Temperatura da superfície | °C |
| `dpt2m` | Ponto de orvalho a 2 m | °C |
| `rh2m` | Umidade relativa a 2 m | % |
| `gustsfc` | Rajada de vento | m/s |
| `ugrd10m`, `vgrd10m` | Componentes leste-oeste e norte-sul do vento a 10 m | m/s |
| `pevprsfc` | Evaporação potencial | mm por 6 h |
| `soill0_10cm`, `soill10_40cm`, `soill40_100cm` | Umidade do solo por camada | fração volumétrica |
| `sunsdsfc` | Radiação solar de onda curta | W/m² |
| `lcdclcll`, `mcdcmcll`, `hcdchcll` | Cobertura de nuvens baixas, médias e altas | % |

**Exemplo: chuva prevista em um ponto**

O que enviar: primeiro as datas de execução disponíveis, depois a previsão. Atenção à ordem: longitude antes da latitude. As coordenadas abaixo (perto de Petrolina, PE) são só ilustrativas.

```http
GET {BASE}/ncep-gfs/apcpsfc
Authorization: Bearer {TOKEN}

GET {BASE}/ncep-gfs/apcpsfc/2026-10-20/-40.50/-9.39
Authorization: Bearer {TOKEN}
```

O que volta: a primeira chamada lista as datas de execução do GFS; a segunda, a série de valores de chuva (mm a cada 6 h) para os próximos 10 dias. O PDF não traz exemplo do JSON de resposta. Para "dá para pulverizar amanhã?" seriam três chamadas: `apcpsfc`, `gustsfc` e `rh2m`.

- **Palavras-chave:** previsão do tempo, chuva, vai chover, precipitação, temperatura, geada, calor, umidade, orvalho, vento, rajada, evaporação, umidade do solo, radiação, nuvens, clima, janela de pulverização, janela de plantio, próximos dias.
- **Consultas de exemplo:** "vai chover essa semana no meu sítio?", "dá para pulverizar amanhã?" (vento + chuva), "risco de geada nos próximos dias".
- **Observações:** uma pergunta pode exigir várias variáveis (cada uma é uma requisição). A localização precisa vir do GPS do dispositivo ou de uma tabela município para coordenada.

### SATVeg (v2)

Séries temporais dos índices de vegetação NDVI e EVI do sensor MODIS (satélites Terra e Aqua) para o Brasil e a América do Sul, de 2000 até hoje, com uma imagem a cada 16 dias e pixel de 250 m. Mostra o vigor da vegetação de uma área ao longo do tempo.

- **Plano:** teste gratuito de até 100 requisições por mês.

| Endpoint | O que recupera | Parâmetros (corpo JSON) |
| --- | --- | --- |
| `POST /series` | Série NDVI ou EVI de um ponto, com as datas | `tipoPerfil` (`ndvi`/`evi`), `satelite` (`terra`/`aqua`/`comb`), `longitude`, `latitude` (obrigatórios); `preFiltro` (0 a 3: nenhum, nodata, nuvem, nuvem e nodata), `filtro` (`flt` FlatBottom, `wav` Wavelet, `sav` Savitzky-Golay), `parametroFiltro` |
| `POST /seriespoligono` | Série média de um polígono; com `todasEstatisticas=true` também mínimo, máximo e desvio padrão | Os mesmos, trocando ponto por `poligono` (pares "lon lat" separados por vírgula, fechado, EPSG 4326) |
| `GET /health` | Status | — |

**Exemplo: série NDVI de um ponto**

O que enviar (exemplo da documentação):

```http
POST {BASE}/series
Authorization: Bearer {TOKEN}
Content-Type: application/json

{
  "tipoPerfil": "ndvi",
  "satelite": "comb",
  "preFiltro": 3,
  "filtro": "sav",
  "parametroFiltro": 4,
  "longitude": -58.88645,
  "latitude": -13.5302
}
```

O que volta (200), trecho do exemplo da documentação: um valor do índice para cada data de imagem, de 16 em 16 dias desde 2000.

```json
{
  "listaSerie": [0.2474, 0.2846, 0.3134, 0.3305, 0.3308],
  "listaDatas": ["2000-02-18", "2000-03-05", "2000-03-21", "2000-04-06", "2000-04-22"]
}
```

Com `POST {BASE}/seriespoligono`, troca-se `longitude`/`latitude` por `"poligono": "lon lat,lon lat,..."` (o último ponto igual ao primeiro). Com `"todasEstatisticas": true`, a resposta também traz `listaMinima`, `listaMaxima` e `listaDesvioPadrao`.

- **Palavras-chave:** satélite, imagem de satélite, NDVI, EVI, índice de vegetação, vigor da lavoura, biomassa, sensoriamento remoto, MODIS, monitoramento, desmatamento, pastagem degradada, perda de safra, seca na lavoura, histórico da área.
- **Consultas de exemplo:** "como está o vigor da minha lavoura comparado ao ano passado?", "minha pastagem está degradando?".
- **Observações:** o pixel de 250 m é grosso para lotes pequenos. A resposta é uma lista de números e precisa de interpretação antes de virar resposta ao produtor.

## Notas para o roteamento por IR

O roteamento fica mais confiável em duas etapas: primeiro escolher a API (9 documentos curtos, um por ficha), depois o endpoint dentro dela (um documento por linha das tabelas acima). Indexar direto os 141 endpoints mistura muitos `/health` e listas quase iguais.

| Par confuso | Sinal que decide | Rota sugerida |
| --- | --- | --- |
| AgroFit × Bioinsumos | "biológico", "orgânico", "inoculante", nome de microrganismo | Bioinsumos; senão AgroFit |
| Agritec (Zarc) × ClimAPI | "época", "quando plantar", "risco" = longo prazo; "amanhã", "semana", "vai chover" = 10 dias | Agritec × ClimAPI |
| Agritec (`/produtividade`) × SATVeg | Estimativa por modelo × observação de satélite da área | Agritec para "quanto vou colher"; SATVeg para "como está a lavoura" |
| Responde Agro × todas | Pergunta aberta de manejo sem entidade estruturada | Responde Agro como rota padrão |
| AgroTermos | Nunca é rota final | Pré-processamento: sinônimos e normalização |

- **Extração de entidades:** depois de escolher o endpoint, ainda é preciso preencher parâmetros (cultura, praga, município, coordenadas, data). Tabelas locais de `/culturas`, `/municipios` e das listas do AgroFit resolvem boa parte disso no próprio Raspberry.
- **Custo das chamadas:** as três freemium têm limites de teste baixos (100 a 500 requisições), então os testes de roteamento devem avaliar a escolha do endpoint sem chamar a API, e só validar uma amostra com chamadas reais.
- **Conjunto de avaliação:** as consultas de exemplo de cada ficha podem servir de semente para um conjunto rotulado (consulta → API → endpoint); BlueStar Sting e SmartSolos funcionam como distratores.

**Limitações destas fichas.** Tudo foi tirado dos 18 PDFs em `IC/Embrapa/APIs` (páginas do portal salvas em 20/10/2026). Autenticação, URL base e o corpo das buscas do Responde Agro e do SmartSolos não aparecem neles. O documento do projeto da IC (`PreProjeto/PROJETO_IC01_IAGROSLM-ENVIADO.pdf`) está só na nuvem do OneDrive e não pôde ser aberto; a ligação com o objetivo offline vem da sua descrição na conversa.

## Fontes

- [Portal AgroAPI — catálogo de APIs](https://www.portal.agroapi.cnptia.embrapa.br/), páginas `api-docs/<api>` e `api-docs/<api>/v<n>` salvas como PDF na pasta Embrapa/APIs (Gratis e Freemium).
