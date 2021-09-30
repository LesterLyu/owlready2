## Triplelite SQLite Schema
### Table `store`
> Note: There is only one row.

| column           | type    | default | description                                                  |
|------------------|---------|---------|--------------------------------------------------------------|
| version          | INTEGER | 9       | triplelite version, should run upgrade script if version < 9 |
| current_blank    | INTEGER | 0       | current max blank node id                                    |
| current_resource | INTEGER | 300     | current max resource id                                      |

### Table `objs` (Objects)
> The triples contains object properties
>
> Indexed on `objs(o,p,c,s)`

| column | type    | default | description |
|--------|---------|---------|-------------|
| c      | INTEGER |         | Context/[Ontology ID](#table-ontologies)    |
| s      | INTEGER |         | [Subject](#table-resources)     |
| p      | INTEGER |         | [Predicate](#table-resources)   |
| o      | INTEGER |         | [Object](#table-resources)      |

#### Example
| c | s   | p | o  |
|---|-----|---|----|
| 2 | 301 | 6 | 80 |
| 3 | 303 | 6 | 80 |

### Table `datas`
> The triples contains data properties
> 
> Indexed on `datas(o,p,c,d,s)`

| column | type    | default | description |
|--------|---------|---------|-------------|
| c      | INTEGER |         | Context/[Ontology ID](#table-ontologies)    |
| s      | INTEGER |         | [Subject](#table-resources)     |
| p      | INTEGER |         | [Predicate](#table-resources)   |
| o      | BLOB    |         | Object, the actual data      |
| d      | INTEGER |         | [data type](#table-resources), or could be '@en', '@fr',...  |

#### Example
| c | s   | p   | o                                           | d   |
|---|-----|-----|---------------------------------------------|-----|
| 3 | 303 | 309 | http://creativecommons.org/licenses/by/3.0/ | 0   |
| 3 | 303 | 312 | Common Impact Data Standard                 | @en |
| 3 | 303 | 313 | cids                                        | 0   |
| 3 | 303 | 314 | http://ontology.eil.utoronto.ca/cids/cids#  | 0   |
| 3 | -10 | 26  | 1                                           | 53  |
| 3 | -11 | 29  | Alignment Risk                              | 0   |
| 3 | -19 | 27  | 1                                           | 53  |
| 3 | -21 | 26  | 1                                           | 53  |
| 3 | -22 | 26  | 1                                           | 53  |

### View `quads`
> Combine Table `datas` and Table `objs`. Column `d` is set to `NULL` in Table `objs`
> 
```sqlite
CREATE VIEW quads AS SELECT c,s,p,o,NULL AS d FROM objs UNION ALL SELECT c,s,p,o,d FROM datas
```

| column | type    | default | description |
|--------|---------|---------|-------------|
| c      | INTEGER |         | Context/[Ontology ID](#table-ontologies)    |
| s      | INTEGER |         | [Subject](#table-resources)     |
| p      | INTEGER |         | [Predicate](#table-resources)   |
| o      | BLOB    |         | Object      |
| d      | INTEGER | NULL    | [data type](#table-resources), or could be NULL, '@en', '@fr',...    |

### Table `ontologies`

| column      | type                | default | description |
|-------------|---------------------|---------|-------------|
| c           | INTEGER PRIMARY KEY |         | Context/Ontology ID    |
| iri         | TEXT                |         | IRI         |
| last_update | DOUBLE              |         | last update in timestamp |

#### Example
| c | iri                                                | last_update        |
|---|----------------------------------------------------|--------------------|
| 1 | http://anonymous/                                  | 0                  |
| 2 | http://test.org#                                   | 1633013873.126485  |
| 3 | http://ontology.eil.utoronto.ca/cids/cids#         | 1633013870.9506207 |
| 4 | http://ontology.eil.utoronto.ca/ISO21972/iso21972# | 1633013870.984842  |

### Table `ontology_alias`
> Not sure how this works, `iri` always equals to `alias` from my testing.

| column | type | default | description |
|--------|------|---------|-------------|
| iri    | TEXT |         | IRI         |
| alias  | TEXT |         | Alias       |

### Table `prop_fts`
> Not sure how this works.

| column | type    | default | description |
|--------|---------|---------|-------------|
| storid | INTEGER |         | Store ID    |

### Table `resources`
> Indexed on `resources(iri)`

| column | type                | default | description |
|--------|---------------------|---------|-------------|
| storid | INTEGER PRIMARY KEY |         | Store ID    |
| iri    | TEXT                |         | IRI  (Indexed)       |

#### Examples
| storid | iri                                                                                   |
|--------|---------------------------------------------------------------------------------------|
| 1      | http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#python_module |
| 2      | http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#python_name   |
| 3      | http://www.w3.org/1999/02/22-rdf-syntax-ns#first                                      |
| ...    | ...                                                                                   |
| 6      | http://www.w3.org/1999/02/22-rdf-syntax-ns#type                                       |
| 26     | http://www.w3.org/2002/07/owl#qualifiedCardinality                                    |
| 27     | http://www.w3.org/2002/07/owl#minQualifiedCardinality                                 |
| 29     | http://www.w3.org/2002/07/owl#hasValue                                                |
| 53     | http://www.w3.org/2001/XMLSchema#nonNegativeInteger                                   |
| 60     | http://www.w3.org/2001/XMLSchema#string                                               |
| 80     | http://www.w3.org/2002/07/owl#Ontology                                                |
| 301    | http://test.org                                                                       |
| 303    | http://ontology.eil.utoronto.ca/cids/cids                                             |
| 303    | http://ontology.eil.utoronto.ca/cids/cids                                             |
| 309    | http://creativecommons.org/ns#license                                                 |
| 312    | http://purl.org/dc/elements/1.1/title                                                 |
| 313    | http://purl.org/vocab/vann/preferredNamespacePrefix                                   |
| 314    | http://purl.org/vocab/vann/preferredNamespaceUri                                      |                                       |                                          |                                                                         |

### Table `last_numbered_iri`
> This table saves the max counter for each ontology class defined in Python
> When initiating a named individual of the ontology class, the couter is used to generate individual name.
> 
> Indexed on `last_numbered_iri(prefix)`

| column | type                | default | description                           |
|--------|---------------------|---------|---------------------------------------|
| prefix | INTEGER PRIMARY KEY |         | Ontology class name defined in Python |
| i      | TEXT                |         | Current greatest index                |

#### Example
> 10 `:Drug` exists, The next drug will be `http://test.org/#drug11` 

| prefix                | i  |
|-----------------------|----|
| http://test.org/#drug | 10 |