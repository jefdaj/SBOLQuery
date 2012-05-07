__all__ = (
    'RDF', 'RDFS', 'REGISTRY', 'SBOL',
    'Variable', 'BNode', 'URIRef', 'Operator', 'Literal',
    'SBOLQuery', 'SBOLResult', 'SBOLNode',
    'SBPKB2')

import urllib2
from rdflib import Namespace, Literal, URIRef, BNode, URIRef
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.Wrapper import QueryResult

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

SBOL     = Namespace('http://sbols.org/v1#')
REGISTRY = Namespace('http://partsregistry.org/#')

class SBOLQuery(Select):

    # todo remove keyword
    def __init__(self, keyword=None, limit=500):

        # create query elements
        # to be processed during compilation
        self.SELECT   = []
        self.WHERE    = []
        self.OPTIONAL = []
        self.FILTER   = []
        self.DISTINCT = True
        self.LIMIT    = limit
        self.ORDER_BY = None # todo order by Id

        # create the result variable
        # this one is special because it represents
        # the result object itself, rather than one
        # of its attributes
        self.result = Variable('result')

        # set up the default query
        display_id = Variable('displayId')
        self.SELECT.append(display_id)
        Select.__init__(self, self.SELECT)
        self.WHERE.append((self.result, SBOL.displayId, display_id))
        self.WHERE.append((self.result, RDF.type, SBOL.DnaComponent))
        #self.available_only = True

    def compile(self):
        'Builds the query and returns it as a str'

        # To make all the query customizations reversible,
        # this copies them to a new instance and compiles that.
        query = self._clone(_limit=self.LIMIT,
                            _order_by=self.ORDER_BY,
                            _distinct=self.DISTINCT)

        # todo put this back once SBPkb2 has sbol:status
        #if self.available_only:
        #    query = query.where(( self.result, SBOL.status, Literal('Available') ))

        # add each stored graph pattern
        for clause in self.WHERE:
            query = query.where(clause)
        for clause in self.OPTIONAL:
            query = query.where(clause, optional=True)
        for expression in self.FILTER:
            query = query.filter(expression)

        # compile to a str
        return Select.compile(query)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return self.compile()

    def add_keyword(self, keyword, variables=None):
        'Require one Variable to contain the keyword'

        if not variables:
            variables = self.SELECT

        regexes = []
        for var in variables:
            regexes.append( Operator.regex(var, keyword, 'i') )
        self.FILTER.append( Operator.or_(*regexes) )

    def add_attribute(self, rdf_predicate, attr_name, optional=False):
        '''
        Require each result pattern to have a triple like:
            <?result> <rdf_predicate> <?attr_name>
        and make <?attr_name> an attribute of the resulting SBOLResult.
        For example:
            query.add_attribute(SBOL.longDescription, 'long')
        '''
        var = Variable(attr_name)
        self.SELECT.append(var)
        if optional:
            destination = self.OPTIONAL
        else:
            destination = self.WHERE
        destination.append((self.result, rdf_predicate, var))

    # todo change to add_so_type
    def add_registry_type(self, registry_type):
        'Adds a WHERE clause specifying the REGISTRY type of each result'

        # using REGISTRY.registry_type would include 'registry_type'
        # literally, so the URIRef is constructed manually instead
        ref = URIRef(REGISTRY + registry_type)
        self.WHERE.append((self.result, RDF.type, ref))

    # todo add so_type as an optional default attribute

class SBOLResult(QueryResult):

    def convert(self):
        json = QueryResult.convert(self)
        results = []
        for binding in json['results']['bindings']:
            result = SBOLResult()
            for key in binding:
                result.__setattr__(key, binding[key]['value'])
            results.append(result)
        return results

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__dict__)

class SBOLNode(SPARQLWrapper):

    def __init__(self, url, username=None, password=None):
        SPARQLWrapper.__init__(self, url)
        self.setReturnFormat(JSON)
        if username:
            self.setCredentials(username, password)

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.baseURI)

    def query(self):
        return SBOLResult(self._query())

    def execute(self, query):
        # todo remove/rename this?
        self.setQuery(query.compile())
        return self.query()

SBPKB2 = SBOLNode('http://sbpkb2.sbols.org:8989/sbpkb2/query',
                  username='anonymous',
                  password='anonymous')

