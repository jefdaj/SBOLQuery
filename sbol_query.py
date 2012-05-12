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
from telescope.sparql.helpers import asc, desc, union
from telescope.sparql.operators import invert
Operator.is_a = is_a
Operator.and_ = and_
Operator.or_  = or_
Operator.not_ = invert
Operator.asc  = asc
Operator.desc = desc
Operator.union = union
del union
del is_a, and_, or_
del asc, desc
del invert

__all__ = (
    'RDF', 'RDFS', 'SB', 'PRT', 'PRP', 'SO',
    'Variable', 'BNode', 'URIRef', 'Operator', 'Literal',
    'SBOLQuery', 'SubpartQuery', 'SuperpartQuery', 'ComponentQuery',
    'SBOLResult', 'SBOLComponent', 'SBOLNode',
    'is_composite', 'list_subparts', 'list_categories',
    'SBPKB2',
    'test')

##########################
# SPARQL wrapper classes
##########################

SB  = Namespace('http://sbols.org/v1#')
PRT = Namespace('http://partsregistry.org/type/')
PRP = Namespace('http://partsregistry.org/part/')
SO  = Namespace('http://purl.org/obo/owl/SO#')

class SBOLQuery(Select):
    'Generic query meant to be customized'

    def __init__(self):

        # create query elements
        # to be processed during compilation
        self.PREFIX   = {RDF  : 'rdf',
                         RDFS : 'rdfs',
                         SB   : 'sb', 
                         PRT  : 'prt',
                         PRP  : 'prp',
                         SO   : 'so'}
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
        self.result = Variable('result')
        self.SELECT.append(self.result)

        # results must be available DnaComponents with displayIds
        self.WHERE.append((self.result, Operator.is_a, SB.DnaComponent))
        self.add_attribute(SB.displayId, 'displayId')
        self.available_only = True

    def compile(self):
        'Builds a query string based on stored graph patterns'

        # create the query
        if len(self.SELECT) == 1:
            query = Describe(self.SELECT)
        else:
            query = Select(self.SELECT,
                           limit=self.LIMIT,
                           order_by=self.ORDER_BY,
                           distinct=self.DISTINCT)

        # add each graph pattern
        # todo add status to the SBPKB2
        #if self.available_only:
        #    query = query.where((self.result, SB.status, Literal('Available')))
        for clause in self.WHERE:
            try:
                # add multiple triples
                query = query.where(*clause)
            except TypeError:
                # add single triple
                query = query.where(clause)
        for clause in self.OPTIONAL:
            try:
                # add multiple triples
                query = query.where(*clause, optional=True)
            except TypeError:
                # add single triple
                query = query.where(clause, optional=True)
        for expression in self.FILTER:
            query = query.filter(expression)

        # compile to a str
        if len(self.SELECT) == 1:
            query = Describe.compile(query, self.PREFIX)
        else:
            query = Select.compile(query, self.PREFIX)
        query = self.prettify(query)
        return query

    def prettify(self, query):
        "Format the query so it's closer to human-readable"
        query = query.replace(' . ', ' .\n')
        query = query.replace('WHERE { ', 'WHERE {\n')
        query = query.replace(' } OPTIONAL', ' }\nOPTIONAL')
        query = query.replace(' } FILTER', ' }\nFILTER')
        query = query.replace(') }', ')\n}')
        return query

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return self.compile()

    def add_keyword(self, keyword, variables=None):
        'Require one Variable to contain the keyword'

        # todo rename variables --> subjects?

        if not variables:
            variables = self.SELECT

        regexes = []
        for var in variables:
            regexes.append( Operator.regex(var, keyword, 'i') )
        self.FILTER.append( Operator.or_(*regexes) )

    def add_description(self, subject=None, optional=False):
        '''
        Require each result to have a description.
        This weeds out features but leaves BioBrick parts.
        '''
        # todo avoid adding to self.SELECT?
        # todo how to deal with multiple descriptions?
        if not subject:
            subject = self.result
        if optional:
            dest = self.OPTIONAL
        else:
            dest = self.WHERE
        desc = Variable('description')
        self.SELECT.append(desc)
        dest.append((subject, SB.description, desc))

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
        self.WHERE.append((subject, Operator.is_a, rdf_type))

    def add_type_by_label(self, label, subject=None):
        'Identifies the type by rdfs:label rather than uri'
        if not subject:
            subject = self.result
        type_ = BNode()
        label = Literal(label)
        self.WHERE.append((subject, Operator.is_a, type_))
        self.WHERE.append((type_, RDFS.label, label))

    def add_sequence(self, optional=False):
        seq = BNode()
        nt  = Variable('sequence')
        self.SELECT.append(nt)
        if optional:
            destination = self.OPTIONAL
        else:
            destination = self.WHERE
        clause = []
        clause.append((self.result, SB.dnaSequence, seq))
        clause.append((seq, SB.nucleotides, nt))
        destination.append(clause)

    def add_uri(self, uri, subject=None):
        'Give the exact URI of the expected result'
        if not subject:
            subject = self.result
        uri = URIRef(uri)
        self.FILTER.append( Operator.sameTerm(subject, uri) )

class SubpartQuery(SBOLQuery):
    'Finds DNA components whose subparts match a given pattern'

    def __init__(self):
        SBOLQuery.__init__(self)

        # map of superpart --> [(annotation, subpart), ...]
        # for automatically adding precedes relationships
        # note: these are added during add_subparts calls,
        #       and assumed to be in order
        self.subparts = {}
        self.num_subparts = 0

        # Whether at least one result-->annotation-->subpart
        # link has been made. only the first one is really needed.
        self._attached = False

    def add_subpart(self, component, subject=None):
        'Add a single subpart Variable to the subject'
        if not subject:
            subject = self.result
        ann = Variable('ann%d' % self.num_subparts)

        # add triples to the graph
        if not self._attached:
            self.WHERE.append((subject, SB.annotation, ann))
            self._attached = True
        self.WHERE.append((ann, SB.subComponent, component))
        #self.WHERE.append((ann, Operator.is_a, SB.SequenceAnnotation))
        #self.WHERE.append((component, Operator.is_a, SB.DnaComponent))
        #self.add_description(subject=component)

        # keep track of annotations, subparts for later
        if not subject in self.subparts:
            self.subparts[subject] = []
        self.subparts[subject].append((ann, component))

        # parts list features with the same name
        # as subparts, which should probably be filtered out
        #same = Operator.sameTerm(self.result, component)
        #diff = Operator.not_(same)
        #self.FILTER.append(diff)

        self.num_subparts += 1

    # todo move this to SBOLQuery?
    def add_precedes(self, upstream, downstream):
        'Add a single precedes relationship'
        self.WHERE.append((upstream, SB.precedes, downstream))

    def add_precedes_list(self, subjects=[]):
        'Add precedes relationships between an ordered list of components'
        if not subjects:
            subjects=self.subparts[self.result]
        for n in range( len(subjects[:-1]) ):
            self.add_precedes(subjects[n][0], subjects[n+1][0])

    def add_all_precedes(self):
        'Fill in all the precedes relationships automatically'
        self.add_precedes_list()

class SuperpartQuery(SubpartQuery):
    'Finds larger constructs that contain the given DNA component(s)'

    def __init__(self):
        SubpartQuery.__init__(self)

        # DNA component containing self.result,
        # plus all the ones upstream and downstream
        # note: self.result itself isn't mentioned;
        #       the superpart is assumed to contain
        #       it if it contains all of its subparts
        self.superpart = Variable('super')

        # ensures the result and superpart are both attached
        self._result_attached = False
        
    def add_subpart(self, component, in_result=False):
        'Adds a subpart to self.superpart, and maybe also self.result'
        SubpartQuery.add_subpart(self, component, subject=self.superpart)
        if in_result:
            SubpartQuery.add_subpart(self, component, subject=self.result)
            self._result_attached = True

    def add_all_precedes(self):
        self.add_precedes_list( self.subparts[self.superpart] )

class ComponentQuery(SBOLQuery):
    'DESCRIBEs a single SBOLComponent'

    def __init__(self, component=None, uri=None):
        SBOLQuery.__init__(self)
        if uri:
            self.add_uri(uri)
        elif component:
            self.add_uri(component.uri)

        # add some descriptive attributes
        # todo see if this can be made into a DESCRIBE query
        # todo add author, etc. if they're added to the SBPKB
        attributes = {SB.name        : 'name',
                      SB.description : 'description'}
        for p in attributes:
            self.add_attribute(p, attributes[p], optional=True)

        # add sequence
        self.add_sequence(optional=True)

        # add SO type
        so_type = Variable('so_type')
        label = BNode()
        self.SELECT.append(so_type)
        clause = ((self.result, Operator.is_a, so_type),
                  (so_type,     RDFS.label,    label))
        self.OPTIONAL.append(clause)

        # add PR type
        pr_type = Variable('pr_type')
        self.SELECT.append(pr_type)
        clause = ((self.result, Operator.is_a, pr_type),
                  (pr_type,     Operator.is_a, PRT    ))
        self.OPTIONAL.append(clause)

class SBOLResult(QueryResult):

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.__dict__)

    def convert(self):
        'Build SBOLComponents from JSON results'
        json = QueryResult.convert(self)
        components = []
        try:
            for binding in json['results']['bindings']:
                com = SBOLComponent()
                for key in binding:
                    value = binding[key]['value']
                    if key.encode('utf-8') == 'result':
                        com.uri = value
                    else:
                        com[key] = value
                components.append(com)
            return components
        except KeyError:
            return components

class SBOLComponent(dict):

    def __repr__(self):
        try:
            return '<%s uri:"%s>"' % (self.__class__.__name__, self.uri)
        except:
            return dict.__repr__(self)

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
        return SBOLResult(self._query())

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

##############################################
# functions for exploring the Parts Registry
##############################################

def list_precedes(uri):
    'List subparts of a given part'
    # todo write a version that handles composite parts
    superpart   = Variable('superpart')
    annotation1 = BNode()
    annotation2 = BNode()
    upstream    = Variable('upstream')
    downstream  = Variable('downstream')
    query = Select([upstream, downstream], distinct=True)
    query = query.where((superpart, SB.annotation, annotation1))
    query = query.where((superpart, SB.annotation, annotation2))
    query = query.where((annotation1, SB.subComponent, upstream))
    query = query.where((annotation2, SB.subComponent, downstream))
    query = query.where((annotation1, SB.precedes, annotation2))
    query = query.filter(Operator.sameTerm(superpart, URIRef(uri)))
    rfc10 = URIRef('http://partsregistry.org/part/RFC_10')
    query = query.filter(Operator.not_(Operator.sameTerm(upstream, rfc10)))
    query = query.filter(Operator.not_(Operator.sameTerm(downstream, rfc10)))
    query = query.compile({SB:'sb', PRP:'prp'})
    SBPKB2.setQuery(query)
    results = SBPKB2.queryAndConvert()
    results = [(r['upstream'], r['downstream']) for r in results]
    return results

def list_categories():
    'List possible types of DnaComponent'
    com = Variable('component')
    cat = Variable('category')
    #lab = Variable('label')
    query = Select([cat], distinct=True)
    query = query.where((com, Operator.is_a, SB.DnaComponent))
    query = query.where((com, Operator.is_a, cat))
    query = query.filter((Operator.not_(Operator.sameTerm(cat, SB.DnaComponent))))
    query = query.compile({SB:'sb'})
    SBPKB2.setQuery(query)
    results = SBPKB2.queryAndConvert()
    results = [r['category'] for r in results]
    results.sort()
    return results

def is_composite(uri):
    return list_precedes(uri) != []

def list_basic_precedes(uri):
    'List precedes, excluding composite parts'
    precedes = list_precedes(uri)
    output = []
    for pre in precedes:
        if not is_composite(pre[0]) and not is_composite(pre[1]):
            output.append(pre)
    return output

def list_subparts(uri):
    'List subparts in order'
    precedes = list_basic_precedes(uri)
    if len(precedes) == 0:
        return []
    else:
        # find the first part
        upstream   = [p[0] for p in precedes]
        downstream = [p[1] for p in precedes]
        first = [p for p in upstream if not p in downstream][0]

        # put the rest in order
        ordered = [first]
        for n in range(len(downstream)):
            index = upstream.index(first)
            first = downstream[index]
            ordered.append(first)
        return ordered

####################
# very simple test
####################

def test():
    q = SBOLQuery()
    q.LIMIT = 10
    return SBPKB2.execute(q)

if __name__ == '__main__':
    print test()

