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
from telescope.sparql.queryforms import Select, Describe
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
    'SBOLQuery', 'SubpartQuery', 'SuperpartQuery', 'AnnotationQuery',
    'SBOLResult', 'SBOLComponent', 'SBOLNode',
    'SBPKB2',
    'test')

##########################
# SPARQL wrapper classes
##########################

SB = Namespace('http://sbols.org/v1#')
PR = Namespace('http://partsregistry.org/#')
SO = Namespace('http://purl.org/obo/owl/SO#')

class SBOLQuery(Select):
    'Generic query meant to be customized'

    def __init__(self):

        # create query elements
        # to be processed during compilation
        self.SELECT   = []
        self.WHERE    = []
        self.OPTIONAL = []
        self.FILTER   = []
        self.DISTINCT = True
        self.LIMIT    = 500
        self.ORDER_BY = None

        # create the result Variable
        # this one is special because it represents
        # the result object itself, as well as one
        # of its attributes
        self.result = Variable('uri')
        self.SELECT.append(self.result)

        # results must be available DnaComponents with displayIds
        self.WHERE.append((self.result, RDF.type, SB.DnaComponent))
        self.add_attribute(SB.displayId, 'displayId')

        # although not a requirement, most people
        # probably want this to be True
        self.available_only = False

    def compile(self):
        'Builds a query string based on stored graph patterns'

        # create the query
        if len(self.SELECT) == 0:
            query = Describe(limit=self.LIMIT)
        else:
            query = Select(self.SELECT,
                           limit=self.LIMIT,
                           order_by=self.ORDER_BY,
                           distinct=self.DISTINCT)

        # add each graph pattern
        if self.available_only:
            query = query.where((self.result, SB.status, Literal('Available')))
        for clause in self.WHERE:
            query = query.where(clause)
        for clause in self.OPTIONAL:
            query = query.where(clause, optional=True)
        for expression in self.FILTER:
            query = query.filter(expression)

        # compile to a str
        if len(self.SELECT) == 0:
            query = Describe.compile(query)
        else:
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

    def add_description(self, subject=None):
        '''
        Require each result to have a description.
        This weeds out features but leaves BioBrick parts.
        '''
        # todo avoid adding to self.SELECT?
        # todo how to deal with multiple descriptions?
        if not subject:
            subject = self.result
        desc = Variable('description')
        self.SELECT.append(desc)
        self.WHERE.append((subject, SB.description, desc))

    def add_attribute(self, rdf_predicate, attr_name, subject=None, optional=False):
        '''
        Require each result pattern to have a triple like:
            <?result> <rdf_predicate> <?attr_name>
        and make <?attr_name> an attribute of the result.
        For example:
            query.add_attribute(SB.longDescription, 'long')
        '''
        # todo avoid adding to self.SELECT?
        if not subject:
            subject = self.result
        var = Variable(attr_name)
        self.SELECT.append(var)
        if optional:
            destination = self.OPTIONAL
        else:
            destination = self.WHERE
        destination.append((self.result, rdf_predicate, var))

    def add_type(self, rdf_type, subject=None):
        'Adds a WHERE clause specifying the type of each result'
        if not subject:
            subject = self.result
        self.WHERE.append((subject, RDF.type, rdf_type))

    def add_type_by_label(self, label, subject=None):
        'Identifies the type by rdfs:label rather than uri'
        if not subject:
            subject = self.result
        type_ = BNode()
        label = Literal(label)
        self.WHERE.append((subject, RDF.type, type_))
        self.WHERE.append((type_, RDFS.label, label))

class SubpartQuery(SBOLQuery):
    'Finds DNA components whose subparts match a given pattern'

    def __init__(self):
        SBOLQuery.__init__(self)
        self.subparts = []

    def add_subpart(self, subpart, subject=None):
        'Add a single subpart Variable to the subject'
        if not subject:
            subject = self.result
        ann = BNode()
        self.WHERE.append((subject, SB.annotation, ann))
        self.WHERE.append((ann, SB.subComponent, subpart))

    def add_precedes(self, targets=[]):
        'Add precedes relationships between all the targets in order'
        if not targets:
            targets = self.subparts
        for n in range( len(targets[:-1]) ):
            self.WHERE.append((targets[n], SB.precedes, targets[n+1]))

class SuperpartQuery(SubpartQuery):
    'Finds larger constructs that contain the given DNA component(s)'

class AnnotationQuery(SBOLQuery):
    'Describes a single DNA component'

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
                    if key.encode('utf-8') == 'uri':
                        com.uri = value
                    else:
                        com[key] = value
                components.append(com)
            return components
        except KeyError:
            return components

class SBOLComponent(dict):

    def __repr__(self):
        return '<%s uri:"%s>"' % (self.__class__.__name__, self.uri)

    def __str__(self):
        return dict.__repr__(self)

    def __setitem__(self, key, value):
        key   = key.encode('utf-8')
        value = value.encode('utf-8')
        dict.__setitem__(self, key, value)

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
            print 'Unable to reach the server'
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

SBPKB2 = SBOLNode('http://localhost:8989/sbpkb2/query',
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

