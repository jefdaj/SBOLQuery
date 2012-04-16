###########
# imports
###########

from rdflib import Namespace, Literal, URIRef
from SPARQLWrapper import SPARQLWrapper, JSON

# there's a lot of useful stuff in this package,
# but it can be hard to find. see these pages:
#     https://bitbucket.org/exogen/telescope/wiki/SPARQLBuilder
#     http://code.google.com/p/telescope/wiki/QueryBuilderDesign
#
from telescope.sparql.queryforms import Select
from telescope.sparql.helpers    import RDF
from telescope.sparql.helpers    import v  as Variable
from telescope.sparql.helpers    import op as Operator

# hack to put all the operators in one place
from telescope.sparql.helpers import is_a, and_, or_
Operator.is_a = is_a
Operator.and_ = and_
Operator.or_  = or_
del is_a, and_, or_

###########
# exports
###########

__all__ = []

# classes defined here
__all__.append('SBOLNode' )
__all__.append('SBOLQuery')
__all__.append('SBOLPart' )

# SBOLNode instances
__all__.append('SBPKB' )

# building blocks of SPARQL queries
__all__.append('RDF'     )
__all__.append('SBOL'    )
__all__.append('REGISTRY')
__all__.append('Variable')
__all__.append('Operator')
__all__.append('Literal' )

###########
# classes
###########

class SBOLQuery(object):

    def __init__(self, keyword=None, limit=100):
        'Creates the default query'
        # todo remove keyword

        # create the result variable
        # this doesn't go in the SELECT statement
        # beacuse it represents the result itself
        # (rather than one of its attributes)
        self.result = Variable('result')

        # create query elements
        self.SELECT = []
        self.WHERE  = []
        self.FILTER = []
        self.LIMIT  = limit

        # set up the default query
        self.add_default_restrictions(keyword)

    def add_default_restrictions(self, keyword=None):
        'Add generic WHERE and FILTER clauses'
        # todo remove keyword
        # todo write a guide to the Operator stuff

        # specify that each result must be an available SBOL Part
        # todo mention that Operator.is_a == RDF.type
        self.WHERE.append((self.result, RDF.type,    SBOL.Part            ))
        self.WHERE.append((self.result, SBOL.status, Literal('Available') ))

        # add a name variable to the results
        name = Variable('name')
        self.SELECT.append(name)

        # specify that each result must have a name,
        # and that it must contain the keyword
        self.WHERE.append((self.result, SBOL.name, name))
        if keyword:
            expr = Operator.regex(name, keyword, 'i')
            self.FILTER.append(expr)

    def __str__(self):
        'Returns the query as a str'
        return self.compile_query()

    def map_attribute(self, rdf_predicate, attr_name):
        '''
        Require each result pattern to have a triple like:
            <?result> <rdf_predicate> <?attr_name>
        and make <?attr_name> an attribute of the resulting SBOLPart.
        For example:
            query.map_attribute(SBOL.longDescription, 'long')
        '''
        var = Variable(attr_name)
        self.SELECT.append(var)
        self.WHERE.append((self.result, rdf_predicate, var))

    def add_registry_type(self, registry_type):
        'Adds a WHERE clause specifying the REGISTRY type of each result'

        # using REGISTRY.registry_type would include 'registry_type'
        # literally, so the URIRef is constructed manually instead
        self.WHERE.append(( RDF.type, URIRef(REGISTRY + registry_type) ))

    def compile_query(self):
        'Builds the query and returns it as a str'

        # start with a SELECT statement
        query = Select(self.SELECT, limit=self.LIMIT, distinct=True)

        # add WHERE clauses
        for clause in self.WHERE:
            query = query.where(clause)

        # add FILTER clauses
        for clause in self.FILTER:
            query = query.filter(clause)

        return query.compile()

class SBOLPart(object):

    def __str__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__dict__)

class SBOLNode(object):

    def __init__(self, server_url):
        self.server = SPARQLWrapper(server_url)

    def execute(self, query):
        'Performs the query and returns results as SBOLParts'

        # fetch JSON
        self.server.setQuery( query.compile_query() )
        self.server.setReturnFormat(JSON)
        try:
            json = self.server.query().convert()
        except Exception, e:
            print e
            print query
            return []

        # process into SBOLParts
        parts = []
        for result in json['results']['bindings']:
            part = SBOLPart()
            for key in result:
                part.__setattr__(key, result[key]['value'])
            parts.append(part)

        return parts

#############
# instances
#############

SBOL     = Namespace('http://sbols.org/sbol.owl#')
REGISTRY = Namespace('http://partsregistry.org/#')

SBPKB = SBOLNode('http://sbpkb.sbolstandard.org/openrdf-sesame/repositories/SBPkb')

#############
# utilities
#############

def summarize(message, results, max_shown=5):
    print
    print message

    if len(results) == 0:
        return
    else:
        if len(results) > max_shown:
            print 'first %i results of %i:' % (max_shown, len(results))
        else:
            print '%i results:' % len(results)

    for n in range(min(len(results), max_shown)):
        print results[n]
    print

if __name__ == '__main__':
    summarize('search: blank', SBPKB.execute( SBOLQuery()        ))
    summarize('search: B0010', SBPKB.execute( SBOLQuery('B0010') ))

