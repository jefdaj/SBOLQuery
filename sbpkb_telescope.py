from rdflib import Namespace, Literal

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

SBOL = Namespace('http://sbols.org/sbol.owl#')

def buildQuery(keyword):

    # create variables
    part  = v.part
    name  = v.name
    short = v.short

    # start with a SELECT statement
    query = Select((name, short))

    # add WHERE clauses
    query = query.where(( part, is_a,                  SBOL.Part            ))
    query = query.where(( part, SBOL.name,             name                 ))
    query = query.where(( part, SBOL.status,           Literal('Available') ))
    query = query.where(( part, SBOL.shortDescription, short                ))

    # add FILTER clauses
    if keyword:
        filters = []
        filters.append( op.regex(name,  keyword, "i") )
        filters.append( op.regex(short, keyword, "i") )
        query = query.filter( or_(*filters) )

    # return as a string
    return query.compile()

if __name__ == '__main__':
    print
    print buildQuery(None)
    print
    print buildQuery('tetr')
    print

