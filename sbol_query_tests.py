import unittest
from sbol_query import *

class TestQueryResults(unittest.TestCase):
    def setUp(self):
        self.query = SBOLQuery()

    def assertResultsMatchSelectStatement(self, query, results):
        'Check that results have the right attributes'
        for part in results:
            names = [key.__name__ for key in part.__dict__]
            for var in query.SELECT:
                self.assertTrue(var.__name__ in names)

    def testSimpleQuery(self):
        'Check that the default query works'
        results = self.query.execute()
        self.assertResultsMatchSelectStatement(self.query, results)

    def testAddNamespacePrefix(self):
        'Check that adding a new PREFIX works'

    def testAddWhereStatement(self):
        'Check that adding a triple to the WHERE statement works'

    def testSelectVariable(self):
        'Check that SELECTing a new variable works'

    def testFilterExpression(self):
        'Check that FILTERing by an expression works'

if __name__ == '__main__':
    unittest.main()
