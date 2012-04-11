import urllib, urllib2
import re
from xml.dom import minidom

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
    queryPrefix = "http://sbpkb.sbolstandard.org/openrdf-sesame/repositories/SBPkb?query=%s"
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
        #queryInserts["keyword matches"] = """
                                           #OPTIONAL {
                                               #?something a ?match . #any triple OK here
                                               #FILTER (regex(?short, "%(searchString)s", "i"))
                                           #}
                                           #OPTIONAL {
                                               #?something a ?match .  #any triple OK here
                                               #FILTER (regex(?long, "%(searchString)s", "i"))
                                           #}
                                           #""" % {"searchString": searchString}
        #queryInserts["ordering"] = "ORDER BY DESC(?match)"
    query = queryTemplate % queryInserts
    #print query
    query = re.sub("\s{2,}", ' ', query) # removes extra whitespace
    query = queryPrefix % urllib.quote(query)
    return query

def getResults(query):
    "perform the query and return results as tuples"
    request = urllib2.Request(query, headers={'Accept':'application/xml'})
    # retrieve results
    try:
        resultsAsXML = minidom.parse( urllib2.urlopen(request) )
        #print resultsAsXML.toxml()
    except:
        return None
    # process results
    resultsAsTuples = []
    for element in resultsAsXML.getElementsByTagName("result"):
        shortDescription = element.childNodes[1].childNodes[1].childNodes[0].toxml()
        biobrickID       = element.childNodes[3].childNodes[1].childNodes[0].toxml()
        resultsAsTuples.append( (biobrickID, shortDescription) )
    #print resultsAsTuples
    return resultsAsTuples

def candidateParts(partType=None, searchString=None):
    query = buildQuery(partType, searchString)
    return getResults(query)

