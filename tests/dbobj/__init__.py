#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "NetEpi Collection". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.
#
#   Copyright (C) 2004-2011 Health Administration Corporation, Australian
#   Government Department of Health and Ageing, and others.
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#
import unittest

class AllTestSuite(unittest.TestSuite):
    # add modules with tests here
    all_tests = [
        'query_builder',
        'result',
        'participation_table',
    ]
    def __init__(self):
        unittest.TestSuite.__init__(self)
        for module_name in self.all_tests:
            module = __import__(module_name, globals())
            self.addTest(module.suite())

def suite():
    return AllTestSuite()

if __name__ == '__main__':
    unittest.main(defaultTest='AllTestSuite')
