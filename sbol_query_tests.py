import unittest
from sbol_query import *

class TestQueryResults(unittest.TestCase):

    def assert_results_match_select_statement(self, query, results):
        'Check that results have the right attributes'
        for part in results:
            names = [str(var.value) for var in query.SELECT]
            for key in part.__dict__:
                self.assertTrue(key in names)

    def test_default_query(self):
        'Check that the default query works'
        query = SBOLQuery()
        results = SBPKB.execute(query)
        self.assert_results_match_select_statement(query, results)

    #def test_add_namespace_prefix(self):
    #    'Check that adding a new PREFIX works'

    def test_add_where_statement(self):
        'Check that adding a triple to the WHERE statement works'

        # build and execute the query
        query = SBOLQuery()
        short_desc = Variable('short')
        query.SELECT.append(short_desc)
        query.WHERE.append((query.result, SBOL.shortDescription, short_desc))
        results = SBPKB.execute(query)

        # check that short_desc is in the SELECT statement,
        # and also made it into the resulting SBOLParts
        for part in results:
            self.assertTrue(hasattr(part, 'short'))
        self.assert_results_match_select_statement(query, results)

    #def test_add_result_attribute(self):
    #    'Check that SELECTing a new variable works'

    #def test_add_filter(self):
    #    'Check that FILTERing by an expression works'

if __name__ == '__main__':
    unittest.main()
