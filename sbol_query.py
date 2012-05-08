#######################
# imports and exports
#######################

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

__all__ = (
    'RDF', 'RDFS', 'SB', 'PR', 'SO',
    'Variable', 'BNode', 'URIRef', 'Operator', 'Literal',
    'SBOLQuery', 'SBOLResult', 'SBOLComponent', 'SBOLNode',
    'SBPKB2',
    'test')

##########################
# SPARQL wrapper classes
##########################

SB = Namespace('http://sbols.org/v1#')
PR = Namespace('http://partsregistry.org/#')
SO = Namespace('http://purl.org/obo/owl/SO#')

class SBOLQuery(Select):

    def __init__(self):

        # create query elements
        # to be processed during compilation
        self.SELECT   = []
        self.WHERE    = []
        self.OPTIONAL = []
        self.FILTER   = []
        self.DISTINCT = True
        self.LIMIT    = None
        self.ORDER_BY = None

        # create the result Variable
        # this one is special because it represents
        # the result object itself, rather than one
        # of its attributes
        self.result = Variable('result')

        # results must be available DnaComponents with displayIds
        self.WHERE.append((self.result, RDF.type, SB.DnaComponent))
        self.add_attribute(SB.displayId, 'displayId')

        # although not a requirement, most people
        # probably want this to be True
        self.available_only = False

        Select.__init__(self, self.SELECT)

    def compile(self):
        'Builds the query and returns it as a str'

        # To make all the query customizations reversible,
        # this copies them to a new instance and compiles that.
        query = self._clone(_limit=self.LIMIT,
                            _order_by=self.ORDER_BY,
                            _distinct=self.DISTINCT)

        if self.available_only:
            query = query.where(( self.result, SB.status, Literal('Available') ))

        # add each stored graph pattern
        for clause in self.WHERE:
            query = query.where(clause)
        for clause in self.OPTIONAL:
            query = query.where(clause, optional=True)
        for expression in self.FILTER:
            query = query.filter(expression)

        # compile to a str
        query = Select.compile(query)
        return query

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
        and make <?attr_name> an attribute of the result.
        For example:
            query.add_attribute(SB.longDescription, 'long')
        '''
        var = Variable(attr_name)
        self.SELECT.append(var)
        if optional:
            destination = self.OPTIONAL
        else:
            destination = self.WHERE
        destination.append((self.result, rdf_predicate, var))

    def add_type(self, rdf_type):
        'Adds a WHERE clause specifying the type of each result'
        self.WHERE.append((self.result, RDF.type, rdf_type))

    # todo add_so_type as an optional default attribute

class SBOLResult(QueryResult):

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__dict__)

    def convert(self):
        json = QueryResult.convert(self)
        components = []
        try:
            for binding in json['results']['bindings']:
                com = SBOLComponent()
                for key in binding:
                    value = binding[key]['value']
                    com[key] = value
                components.append(com)
            return components
        except KeyError:
            return components

class SBOLComponent(dict):

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict.__repr__(self))

    #def __setitem__(self, key, value):
    #    key   = key.encode('utf-8')
    #    value = value.encode('utf-8')
    #    dict.__setitem__(self, key, value)

class SBOLNode(SPARQLWrapper):

    def __init__(self, url, username=None, password=None):
        SPARQLWrapper.__init__(self, url)
        self.setReturnFormat(JSON)
        if username:
            self.setCredentials(username, password)

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.baseURI)

    def query(self):
        try:
            return SBOLResult(self._query())
        except urllib2.URLError:
            message = 'Unable to reach the server'
            LOG.error(message)
            print message
            return []

    def execute(self, query):
        # todo remove/rename this?
        self.setQuery(query.compile())
        result = self.query()
        result = result.convert()
        return result

####################
# known SBOL nodes
####################

SBPKB2 = SBOLNode('http://sbpkb2.sbols.org:8989/sbpkb2/query',
                  username='anonymous',
                  password='anonymous')

####################
# very simple test
####################

def test():
    q = SBOLQuery()
    q.LIMIT = 10
    return SBPKB2.execute(q)

if __name__ == '__main__':
    print test()

