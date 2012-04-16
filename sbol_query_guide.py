from sbol_query import *

# create a default query
query = SBOLQuery()

# optional: add a new namespace PREFIX
# todo implement this
# todo will this work without a new endpoint too?
SO = Namespace('http://purl.obolibrary.org/obo/')
query.PREFIX['so'] = (SO)

# optional: create a new SPARQL variable
# and add it to the WHERE statement to define it
# todo example using the SO namespace
long_desc = Variable('long')
triple = (query.result, SBOL.longDescription, long_desc)
query.WHERE.append(triple)

# optional: add it to the SELECT statement to fetch its value
# (each variable SELECTed must also be in the WHERE statement)
query.SELECT['long'] = long_desc

# optional: add FILTERs to restrict the values of Variables
# (each FILTERed variable must also be in the WHERE statement)
# todo implement this and/or rework example
expression = Expression(long_desc != '')
query.FILTER.append(expression)

# optional: limit the number of results
# (default is 100; set None for no limit)
query.LIMIT = 50

# you can see the query at any point
print 'query:'
print query

# executing the query returns a list of SBOLParts
results = query.execute()

# each has attributes based on the SELECT statement
print 'parts:'
for part in results:
    print part.name, part.long

