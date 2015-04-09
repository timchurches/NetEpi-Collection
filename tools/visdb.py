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

"""
Generate a DOT (graphviz) file from the database describer
"""

from casemgr.schema import schema

db = schema.define_db('::collection:')
print 'digraph appname {'
print 'pack=true;'
print 'center=true;'
#    print 'ratio=compress;'
#    print 'size="11,8";'
#    print 'rotate=90";'
#    print 'model=resistance;'
#    print 'overlap=false;'
print 'overlap=scale;'
print 'splines=true;'
print 'nodesep=.1;'
print 'epsilon=.1;'
print 'mclimit=4;'
print 'size="11.69x8.27";'
print "node [shape=ellipse]"
for table_desc in db.get_tables():
    print '"%s";' % table_desc.name
print 'edge [style=solid,weight=4]'
for table_desc in db.get_tables():
    for dep in table_desc.dependancies():
        print '"%s" -> "%s";' % (table_desc.name, dep)
print '};'
