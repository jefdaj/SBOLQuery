###########
# imports
###########

import urllib2
from rdflib import Namespace, Literal, URIRef, BNode, URIRef
from SPARQLWrapper import SPARQLWrapper, JSON

# there's a lot of useful stuff in this package,
# but it can be hard to find. see these pages:
#     https://bitbucket.org/exogen/telescope/wiki/SPARQLBuilder
#     http://code.google.com/p/telescope/wiki/QueryBuilderDesign
#
from telescope.sparql.queryforms import Select
from telescope.sparql.helpers    import RDF, RDFS
from telescope.sparql.helpers    import v  as Variable
from telescope.sparql.helpers    import op as Operator

# hack to put all the operators in one place
from telescope.sparql.helpers import is_a, and_, or_
from telescope.sparql.helpers import asc, desc
Operator.is_a = is_a
Operator.and_ = and_
Operator.or_  = or_
Operator.asc  = asc
Operator.desc = desc
del is_a, and_, or_
del asc, desc

###########
# exports
###########

__all__ = []

# classes defined here
__all__.append('SBOLQuery' )
__all__.append('SBOLResult')
__all__.append('SBOLNode'  )

# SBOLNode instances
__all__.append('SBPKB2')

# building blocks of SPARQL queries
__all__.append('RDF'     )
__all__.append('RDFS'    )
__all__.append('SBOL'    )
__all__.append('REGISTRY')
__all__.append('Variable')
__all__.append('BNode'   )
__all__.append('URIRef'  )
__all__.append('Operator')
__all__.append('Literal' )

###########
# classes
###########

class SBOLQuery(object):

    def __init__(self, keyword=None, limit=1000):
        'Creates the default query'
        # todo remove keyword

        # create the result variable
        self.result = Variable('result')

        # create query elements
        self.SELECT   = []
        self.HIDDEN   = [] # variables to keep around but not display
        self.WHERE    = []
        self.FILTER   = []
        self.OPTIONAL = []
        self.ORDER    = []
        self.LIMIT    = limit

        #self.available_only = True

        # set up the default query
        self.add_default_restrictions(keyword)

    def add_default_restrictions(self, keyword=None):
        'Add generic WHERE and FILTER clauses'
        # todo remove keyword
        # todo write a guide to the Operator stuff
        # todo remove the entire default query?

        # specify that each result must be an SBOL DNA component
        # todo mention that Operator.is_a == RDF.type
        self.WHERE.append((self.result, RDF.type, SBOL.DnaComponent))

        # add a name variable to the results
        name = Variable('name')
        self.SELECT.append(name)

        # specify that each result must have a name,
        # and that it must contain the keyword
        self.WHERE.append((self.result, SBOL.displayId, name))
        if keyword:
            expr = Operator.regex(name, keyword, 'i')
            self.FILTER.append(expr)

    def __str__(self):
        'Returns the query as a str'
        return self.compile_query()

    def map_attribute(self, rdf_predicate, attr_name, optional=False):
        '''
        Require each result pattern to have a triple like:
            <?result> <rdf_predicate> <?attr_name>
        and make <?attr_name> an attribute of the resulting SBOLResult.
        For example:
            query.map_attribute(SBOL.longDescription, 'long')
        '''
        var = Variable(attr_name)
        self.SELECT.append(var)
        if optional:
            destination = self.OPTIONAL
        else:
            destination = self.WHERE
        destination.append((self.result, rdf_predicate, var))

    def add_registry_type(self, registry_type):
        'Adds a WHERE clause specifying the REGISTRY type of each result'

        # using REGISTRY.registry_type would include 'registry_type'
        # literally, so the URIRef is constructed manually instead
        ref = URIRef(REGISTRY + registry_type)
        self.WHERE.append((self.result, RDF.type, ref))

    def compile_query(self):
        'Builds the query and returns it as a str'

        # start with a SELECT statement
        kwargs = {'limit'    : self.LIMIT,
                  'order_by' : self.ORDER,
                  'distinct' : True}
        query = Select(self.SELECT, **kwargs)

        # add WHERE clauses
        for clause in self.WHERE:
            query = query.where(clause)

        # todo put this back once SBPkb2 has sbol:status
        #if self.available_only:
        #    query = query.where(( self.result, SBOL.status, Literal('Available') ))

        # add optional WHERE clauses
        for clause in self.OPTIONAL:
            query = query.where(clause, optional=True)

        # add FILTER clauses
        for expression in self.FILTER:
            query = query.filter(expression)

        return query.compile()

class SBOLResult(object):

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__dict__)

class SBOLNode(object):

    def __init__(self, server_url):
        self.server = SPARQLWrapper(server_url)

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.server.baseURI)

    def login(self, username, password):
        self.server.setCredentials(username, password)

    def execute(self, query):
        'Performs the query and returns results as SBOLResults'

        # fetch JSON
        self.server.setQuery( query.compile_query() )
        self.server.setReturnFormat(JSON)
        try:
            json = self.server.query().convert()
        except Exception, e:
            print e
            print query
            return []

        # process into SBOLResults
        results = []
        for binding in json['results']['bindings']:
            result = SBOLResult()
            for key in binding:
                result.__setattr__(key, binding[key]['value'])
            results.append(result)

        return results

#############
# functions
#############

def list_known_nodes(index='http://index.sbolstandard.org/syndex.txt'):
    'Create a list of all known SBOLNodes'
    html = urllib2.urlopen(index).read()
    urls = [url for url in html.split('\n') if len(url) > 0]
    nodes = [SBOLNode(url) for url in urls]
    return nodes

#############
# instances
#############

SBOL     = Namespace('http://sbols.org/v1#')
REGISTRY = Namespace('http://partsregistry.org/#')

SBPKB2 = SBOLNode('http://sbpkb2.sbols.org:8989/sbpkb2/query')
SBPKB2.login('anonymous', 'anonymous')

################
# simple tests
################

def test_blank():
    print 'search: blank, limit=20'
    for result in SBPKB2.execute( SBOLQuery(limit=20) ):
        print result

def test_specific():
    print 'search: B0010'
    for result in SBPKB2.execute( SBOLQuery('B0010')  ):
        print result

if __name__ == '__main__':
    test_blank()
    test_specific()

