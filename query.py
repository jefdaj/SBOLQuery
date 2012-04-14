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

SBOL     = Namespace('http://sbols.org/sbol.owl#')
REGISTRY = Namespace('http://partsregistry.org/#')

SBPKB_URL = 'http://sbpkb.sbolstandard.org/openrdf-sesame/repositories/SBPkb'

class SBOLQuery(object):

    def __init__(self, keyword, registry_type=None):
        'Creates the default query'
    
        # create variables
        # todo support more variables
        self.part  = v.part
        self.name  = v.name
        self.short = v.short
        self.wheres  = []
        self.filters = []

        # start with a SELECT statement
        self.query = Select((self.name, self.short))

        # add basic WHERE clauses
        self.add_part_attribute(is_a,                  SBOL.Part            )
        self.add_part_attribute(SBOL.name,             self.name            )
        self.add_part_attribute(SBOL.status,           Literal('Available') )
        self.add_part_attribute(SBOL.shortDescription, self.short           )

        # restrict to a specific type
        if registry_type:
            self.add_registry_type(registry_type)

        # add FILTER clauses
        if keyword:
            self.add_regex_filter(self.name,  keyword)
            self.add_regex_filter(self.short, keyword)

    def __str__(self):
        'Returns the query as a str'
        return self.build_query()

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

        # apply changes to a local variable
        # rather than the stored "vanilla" query
        query = self.query

        # add WHERE clauses
        for clause in self.wheres:
            query = query.where(clause)

        # add FILTER clauses
        if self.filters:
            query = query.filter( or_(*self.filters) )

        return query.compile()

    def fetch_results(self):
        'Performs the query and returns results as tuples'
        # todo return custom objects instead?

        # compile query
        query = self.build_query()

        # fetch JSON
        sparql = SPARQLWrapper(SBPKB_URL)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        try:
            json = sparql.query().convert()
        except Exception, e:
            print e
            print query
            return []

        # process into tuples
        tuples = []
        for result in json["results"]["bindings"]:
            biobrickID       = result['name']['value']
            shortDescription = result['short']['value']
            tuples.append((biobrickID, shortDescription))

        return tuples

def summarize(message, results, max_shown=5):
    print
    print message
    print '%i results' % len(results)
    if len(results) == 0:
        return
    else:
        print 'here are the first %i:' % max_shown
        for n in range(min(len(results), max_shown)):
            print results[n]
        print

if __name__ == '__main__':
    summarize('searched for tetr',      SBOLQuery('tetr'       ).fetch_results())
    summarize('searched for tetr, cds', SBOLQuery('tetr', 'cds').fetch_results())

    # this works, but takes a long time
    #summarize('searched for None', SBOLQuery(None).fetch_results())

