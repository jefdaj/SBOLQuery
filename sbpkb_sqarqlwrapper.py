from SPARQLWrapper import SPARQLWrapper, JSON

# maps TinkerCell part families to sbpkb categories
TC_2_SBPKB = {
"coding"                 : "cds",
"rbs"                    : "rbs",
"terminator"             : "terminator",
"vector"                 : "plasmid",
"promoter"               : "promoter",
"constitutive promoter"  : "promoter",
"repressible promoter"   : "promoter",
"operator"               : "operator",
"inducible promoter"     : "promoter",
"activator binding site" : "operator",
"repressor binding site" : "operator"
}

class QueryError(Exception):
    "error fetching query results"

def buildQuery(partType, searchString):
    queryTemplate = """
                    PREFIX pr:<http://partsregistry.org/#>
                    PREFIX sbol:<http://sbols.org/sbol.owl#>

                    SELECT DISTINCT ?name ?short
                    WHERE {
                        ?part a                     sbol:Part   ;
                              %(type restriction)s
                              sbol:name             ?name       ;
                              sbol:status           "Available" ;
                              sbol:shortDescription ?short      .
                        %(keyword matches)s
                    }
                    ORDER BY %(ordering)s
                    LIMIT 200
                    """
    queryInserts = { "type restriction" : "",
                     "keyword matches"  : "",
                     "ordering"         : "?name" }
    if partType != None and partType in TC_2_SBPKB and TC_2_SBPKB[partType] != None:
        queryInserts["type restriction"] = "a pr:%s ;" % TC_2_SBPKB[partType]
    if not searchString in (None, ''):
        queryInserts["keyword matches"] = """ FILTER( regex(?name, "%(searchString)s", "i")  ||
                                                      regex(?short, "%(searchString)s", "i") ||
                                                      regex(?long, "%(searchString)s", "i")     )
                                          """ % {"searchString": searchString}
    query = queryTemplate % queryInserts
    return query

def getResults(query):
    "perform the query and return results as tuples"

    # retrieve results
    sparql = SPARQLWrapper('http://sbpkb.sbolstandard.org/openrdf-sesame/repositories/SBPkb')
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    resultsAsJSON = sparql.query().convert()

    # process results
    resultsAsTuples = []
    for result in resultsAsJSON["results"]["bindings"]:
        biobrickID       = result['name']['value']
        shortDescription = result['short']['value']
        resultsAsTuples.append((biobrickID, shortDescription))

    return resultsAsTuples

def candidateParts(partType=None, searchString=None):
    query = buildQuery(partType, searchString)
    return getResults(query)

def surveyResults(results, max_shown=5):
    print
    print '%i results' % len(results)
    print 'here are the first few:'
    for n in range(min(len(results), max_shown)):
        print results[n]
    print

if __name__ == '__main__':
    surveyResults( candidateParts() )
    surveyResults( candidateParts(searchString='tetr') )
