# import an SBOLQuery,
# and optionally some namespaces
# and other stuff
from sbol_query import SBPKBQuery, SBOL

# create a skeleton query
# (if you execute this one as-is it will take a while)
query = SBOLQuery()

# optional: add a new namespace PREFIX
# todo will this work without a new endpoint too?
SO = Namespace('http://purl.obolibrary.org/obo/')
query.PREFIX.append(SO)

# optional: create a new SPARQL variable
# and add it to the WHERE statement to define it
# todo example using the SO namespace
long_desc = Variable('long')
triple = (query.part, SBOL.longDescription, long_desc)
query.WHERE.append(triple)

# optional: add it to the SELECT statement to fetch its value
# (each variable SELECTed must also be in the WHERE statement)
# todo make this a dict to allow renaming?
query.SELECT.append(long_desc)

# optional: add FILTERs to restrict the values of Variables
# (each FILTERed variable must also be in the WHERE statement)
expression = Expression(long_desc != '')
query.FILTER.append(expression)

# optional: limit the number of results
query.LIMIT = 100

# you can see the query at any point
print 'query:'
print query

# executing the query returns a list of SBOLParts
results = query.execute()

# each has attributes based on the SELECT statement
print 'parts:'
for part in results:
    print part.name, part.long_desc

