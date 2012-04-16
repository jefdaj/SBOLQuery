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
        self.SELECT = {}
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
        self.WHERE.append((self.result, RDF.type,    SBOL.Part            ))
        self.WHERE.append((self.result, SBOL.status, Literal('Available') ))

        # add name and short description variables to the results
        self.SELECT['name' ] = Variable('name' )
        self.SELECT['short'] = Variable('short')

        # specify that each result must have a name and short description,
        # and that one of them must contain the keyword
        self.WHERE.append((self.result, SBOL.name,             self.SELECT['name' ]))
        self.WHERE.append((self.result, SBOL.shortDescription, self.SELECT['short']))
        if keyword:
            options = []
            options.append( Operator.regex(self.SELECT['name' ], keyword, 'i') )
            options.append( Operator.regex(self.SELECT['short'], keyword, 'i') )
            self.FILTER.append( Operator.or_(*options) )

    def __str__(self):
        'Returns the query as a str'
        return self.compile_query()

    def add_result_attribute(self, predicate, variable):
        '''
        Require each result pattern in the graph to have an edge like:
        <self.result> <predicate> <variable>
        and store variable as an attribute of the result object
        '''
        self.SELECT[attr_name] = Variable(attr_name)
        self.WHERE.append((self.result, attr, self.SELECT[attr_name]))

    def add_registry_type(self, registry_type):
        'Adds a WHERE clause specifying the REGISTRY type of self.result'
        self.add_part_attribute(RDF.type, URIRef(REGISTRY + registry_type))

    def compile_query(self):
        'Builds the query and returns it as a str'

        # start with a SELECT statement
        query = Select(self.SELECT, limit=self.LIMIT)

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
        'Performs the query and returns results as tuples'

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
    summarize('search: blank', SBPKB.execute( SBOLQuery()       ))
    summarize('search: tetr',  SBPKB.execute( SBOLQuery('tetr') ))

