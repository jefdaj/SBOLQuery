from rdflib import Namespace, Literal, URIRef

from SPARQLWrapper import SPARQLWrapper, JSON

# this package doesn't really have its imports figured out.
# there are a lot of useful objects in there,
# but you have to dig through it to find them yourself
# also see these pages:
#     https://bitbucket.org/exogen/telescope/wiki/SPARQLBuilder
#     http://code.google.com/p/telescope/wiki/QueryBuilderDesign
# 
from telescope.sparql.queryforms  import Select
from telescope.sparql.expressions import and_, or_
from telescope.sparql.helpers     import RDF, RDFS
from telescope.sparql.helpers     import is_a, v, op

__all__ = []
__all__.append('SBOLNode')
__all__.append('SBOLQuery')
__all__.append('SBOLPart')
__all__.append('SBOL')
__all__.append('REGISTRY')
__all__.append('SBPKB')

SBOL     = Namespace('http://sbols.org/sbol.owl#')
REGISTRY = Namespace('http://partsregistry.org/#')

class SBOLQuery(object):

    def __init__(self, keyword, registry_type=None, limit=None):
        'Creates the default query'

        # create variables
        # todo support more variables
        # todo accept strings rather than variable obejcts
        self.part  = v.part
        self.name  = v.name
        self.short = v.short
        self.selects = [self.name, self.short]
        self.wheres  = []
        self.filters = []
        self.limit = limit

        # set up a generic query
        self.add_basics()

        # add restrictions
        if keyword:
            self.add_regex_filter(self.name,  keyword)
            self.add_regex_filter(self.short, keyword)
        if registry_type:
            self.add_registry_type(registry_type)

    def add_basics(self):
        'Add generic WHERE clauses'
        self.add_part_attribute(is_a,                  SBOL.Part            )
        self.add_part_attribute(SBOL.name,             self.name            )
        self.add_part_attribute(SBOL.status,           Literal('Available') )
        self.add_part_attribute(SBOL.shortDescription, self.short           )

    def __str__(self):
        'Returns the query as a str'
        return self.build_query()

    def add_field(self, field):
        'Add to the list of attributes to SELECT'
        # todo add to variables, then check when adding filters
        raise NotImplementedError

    def add_part_attribute(self, attribute, value):
        'Generic method that adds a WHERE clause involving self.part'
        self.wheres.append(( self.part, attribute, value ))

    def add_registry_type(self, registry_type):
        'Adds a WHERE clause specifying the REGISTRY type of self.part'
        self.add_part_attribute(is_a, URIRef(REGISTRY + registry_type))

    def add_regex_filter(self, variable, keyword):
        '''
        Adds a regex to the FILTER clause.
        These will be combined using the || operator.
        '''
        # todo support && operator too
        self.filters.append( op.regex(variable, keyword, "i") )

    def build_query(self):
        'Builds the query and return it as a str'

        # start with a SELECT statement
        query = Select(self.selects, limit=self.limit)

        # add WHERE clauses
        for clause in self.wheres:
            query = query.where(clause)

        # add FILTER clauses
        if self.filters:
            query = query.filter( or_(*self.filters) )

        return query.compile()

class SBOLPart(object):
    def __init__(self, result_dict):
        self.__dict__.update(result_dict)

class SBOLNode(object):
    def __init__(self, server_url):
        self.server = SPARQLWrapper(server_url)

    def execute(self, query):
        'Performs the query and returns results as tuples'

        # fetch JSON
        self.server.setQuery( query.build_query() )
        self.server.setReturnFormat(JSON)
        try:
            json = self.server.query().convert()
        except Exception, e:
            print e
            print query
            return []

        # process into tuples
        # todo process into SBOLParts instead
        tuples = []
        for result in json["results"]["bindings"]:
            biobrickID       = result['name']['value']
            shortDescription = result['short']['value']
            tuples.append((biobrickID, shortDescription))

        return tuples

SBPKB = SBOLNode('http://sbpkb.sbolstandard.org/openrdf-sesame/repositories/SBPkb')

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
    summarize('search: None',      SBPKB.execute(SBOLQuery(None, limit=100))  )
    summarize('search: tetr',      SBPKB.execute(SBOLQuery('tetr', limit=10)) )
    summarize('search: tetr, cds', SBPKB.execute(SBOLQuery('tetr', 'cds'))    )

