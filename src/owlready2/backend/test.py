from SPARQLWrapper import SPARQLWrapper, JSON, POST
from time import time

sparql = SPARQLWrapper("http://127.0.0.1:7200/repositories/compass", returnFormat=JSON)
sparql.setMethod(POST)

sparql.setQuery('''
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
select * where { 
	?s rdf:type owl:Ontology .
}
''')

# import cProfile
#
# cProfile.run('sparql.query().convert()', sort='cumtime')

# import requests
#
# curr = time()
# result = requests.post('http://localhost:7200/repositories/compass', {
#
# })
# print(result)
# print(time() - curr)

#
curr = time()
ret = sparql.query().convert()
for item in ret["results"]["bindings"]:
    print(item["s"]["value"])
print(time() - curr)
#
# curr = time()
# ret = sparql.query().convert()
# for item in ret["results"]["bindings"]:
#     print(item["s"]["value"])
# print(time() - curr)
