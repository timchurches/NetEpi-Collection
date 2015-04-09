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
from albatross import SimpleAppContext
import config

from wiki.formatter import wiki_to_html, wiki_to_oneliner
from wiki.env import Environment
from wiki.href import Href

import testcommon

"""
    _post_rules = [
        r"(?P<htmlescape>[&<>])",
#       # shref corresponds to short TracLinks, i.e. sns:stgt
#       r"(?P<shref>!?((?P<sns>%s):(?P<stgt>%s|%s(?:%s*%s)?)))" \
#       % (LINK_SCHEME, QUOTED_STRING,
#          SHREF_TARGET_FIRST, SHREF_TARGET_MIDDLE, SHREF_TARGET_LAST),
#       # lhref corresponds to long TracLinks, i.e. [lns:ltgt label?]
#       r"(?P<lhref>!?\[(?:(?P<lns>%s):(?P<ltgt>%s|[^\]\s]*)|(?P<rel>%s))"
#       r"(?:\s+(?P<label>%s|[^\]]+))?\])" \
#       % (LINK_SCHEME, QUOTED_STRING, LHREF_RELATIVE_TARGET, QUOTED_STRING),
#       # macro call
#       (r"(?P<macro>!?\[\[(?P<macroname>[\w/+-]+)"
#        r"(\]\]|\((?P<macroargs>.*?)\)\]\]))"),
        # heading, list, definition, indent, table...
        r"(?P<heading>^\s*(?P<hdepth>=+)\s.*\s(?P=hdepth)\s*$)",
        r"(?P<list>^(?P<ldepth>\s+)(?:\*|\d+\.) )",
        r"(?P<definition>^\s+(.+)::)\s*",
        r"(?P<indent>^(?P<idepth>\s+)(?=\S))",
        r"(?P<last_table_cell>\|\|\s*$)",
        r"(?P<table_cell>\|\|)"]
"""

LARGE_TEST = """= Pandemic Influenza =
== Important information ==

 * Something
 * Whatever
   * ~~Struck-out~~
 * Something ```monospaced``` (should be `monospaced`) or {{{**monospaced**}}}
   * *Bold*
   * _Italic_
      * **Bold/italic**
  * __underlining__ the *importance* of ^upper^ and ,,lower,, bounds for H,,2,,O consumption or 2^3^ = 8

Line 1[[BR]]Line 2

  1. One
    1. One point one
  1. Two

 llama::
  a hairy, spitting beast
 python::
  a hairless herpetic beasty

A paragraph of words
  And an indented paragraph of words which go on and on and on endlessly like some form of verbal diarrhoea or worse, please stop I can't stand it!

A paragraph of words
  And an indented paragraph of words which go on and on and 
on endlessly like some form of verbal diarrhoea or worse, 
please stop I can't stand it!

A paragraph of words
  And an indented paragraph of words which go on and on and 
  on endlessly like some form of verbal diarrhoea or worse, 
  please stop I can't stand it!

||Cell 1||Cell 2||Cell 3||
||Cell 4||Cell 5||Cell 6||

----

What about URLs?

http://www.cdc.gov 

[http://www.cdc.gov]

[wiki:WonderLand]

WonderLand

http://www.edgewall.com/gfx/trac_example_image.png

[[Timestamp]]
"""


CASEMGR_TESTS = [
        ('plaintext',
            '<p>\nplaintext\n</p>\n',
            'plaintext'),
        # 'pre' formatting rules
        ('**hello**',
            '<p>\n<strong><i>hello</i></strong>\n</p>\n',
            '<strong><i>hello</i></strong>'),
        ('*hello*',
            '<p>\n<strong>hello</strong>\n</p>\n',
            '<strong>hello</strong>'),
        ('__hello__',
            '<p>\n<span class="underline">hello</span>\n</p>\n',
            '<span class="underline">hello</span>'),
        ('_hello_',
            '<p>\n<i>hello</i>\n</p>\n',
            '<i>hello</i>'),
        ('~~hello~~',
            '<p>\n<del>hello</del>\n</p>\n',
            '<del>hello</del>'),
        ('^hello^',
            '<p>\n<sup>hello</sup>\n</p>\n',
            '<sup>hello</sup>'),
        (',,hello,,',
            '<p>\n<sub>hello</sub>\n</p>\n',
            '<sub>hello</sub>'),
        ('{{{hello}}}',
            '<p>\n<tt>hello</tt>\n</p>\n',
            '<tt>hello</tt>'),
        ('`hello`',
            '<p>\n<tt>hello</tt>\n</p>\n',
            '<tt>hello</tt>'),
        # 'post' formatting rules
        ('< > &',
            '<p>\n&lt; &gt; &amp;\n</p>\n',
            '&lt; &gt; &amp;'),
        ('= heading 1 =',
            '<h1 id="heading1">heading 1</h1>\n',
            '= heading 1 ='),
        ('== heading 2 ==',
            '<h2 id="heading2">heading 2</h2>\n',
            '== heading 2 =='),
        ('=== heading 3 ===',
            '<h3 id="heading3">heading 3</h3>\n',
            '=== heading 3 ==='),
        ('==== heading 4 ====',
            '<h4 id="heading4">heading 4</h4>\n',
            '==== heading 4 ===='),
        ('===== heading 5 =====',
            '<h5 id="heading5">heading 5</h5>\n',
            '===== heading 5 ====='),
        ('====== heading 6 ======',
            '<h5 id="heading6">heading 6</h5>\n', # no level 6
            '====== heading 6 ======'),
        (' * hello\n * there',
            '<ul><li>hello\n</li><li>there\n</li></ul>',
            '<strong> hello\n </strong> there'),
        (' * list\n   * sublist',
            '<ul><li>list\n<ul><li>sublist\n</li></ul></li></ul>',
            '<strong> list\n   </strong> sublist'),
        ('  term:: definition',
            '<dl><dt>term</dt><dd>definition\n</dd></dl>\n',
            'term:: definition'),
        (' blockquote',
            '<blockquote>\n<p>\nblockquote\n</p>\n</blockquote>\n',
            'blockquote'),
        ('  blockquote',
            '<blockquote>\n<p>\nblockquote\n</p>\n</blockquote>\n',
            'blockquote'),
        ('||heading 1||heading 2||\n||cell 1||cell 2||',
            '<table class="wiki">\n<tr><td>heading 1</td><td>heading 2\n</td></tr><tr><td>cell 1</td><td>cell 2\n</td></tr></table>\n',
            '||heading 1||heading 2||\n||cell 1||cell 2||'),
        ('{{{\n#!html\n<h1 style="text-align: right; color: blue">HTML Test</h1>\n}}}\n',
            '<div class="system-message">\n <strong>Error: Failed to load processor <code>html</code></strong>\n <pre>No macro named [[html]] found</pre>\n</div>\n',
            ' [&hellip;]'),
        # a problematic test from Tim
        (LARGE_TEST,
            '<h1 id="PandemicInfluenza">Pandemic Influenza</h1>\n<h2 id="Importantinformation">Important information</h2>\n<ul><li>Something\n</li><li>Whatever\n<ul><li><del>Struck-out</del>\n</li></ul></li><li>Something <tt></tt><tt>monospaced</tt><tt></tt> (should be <tt>monospaced</tt>) or <tt>**monospaced**</tt>\n<ul><li><strong>Bold</strong>\n</li><li><i>Italic</i>\n<ul><li><strong><i>Bold/italic</i></strong>\n</li></ul></li></ul></li><li><span class="underline">underlining</span> the <strong>importance</strong> of <sup>upper</sup> and <sub>lower</sub> bounds for H<sub>2</sub>O consumption or 2<sup>3</sup> = 8\n</li></ul><p>\nLine 1[[BR]]Line 2\n</p>\n<ol><li>One\n<ol><li>One point one\n</li></ol></li><li>Two\n</li></ol><dl><dt>llama</dt><dd>\na hairy, spitting beast\n</dd><dt>python</dt><dd>\na hairless herpetic beasty\n</dd></dl>\n<p>\nA paragraph of words\n</p>\n<blockquote>\n<p>\nAnd an indented paragraph of words which go on and on and on endlessly like some form of verbal diarrhoea or worse, please stop I can\'t stand it!\n</p>\n</blockquote>\n<p>\nA paragraph of words\n</p>\n<blockquote>\n<p>\nAnd an indented paragraph of words which go on and on and \non endlessly like some form of verbal diarrhoea or worse, \nplease stop I can\'t stand it!\n</p>\n</blockquote>\n<p>\nA paragraph of words\n</p>\n<blockquote>\n<p>\nAnd an indented paragraph of words which go on and on and \non endlessly like some form of verbal diarrhoea or worse, \nplease stop I can\'t stand it!\n</p>\n</blockquote>\n<table class="wiki">\n<tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3\n</td></tr><tr><td>Cell 4</td><td>Cell 5</td><td>Cell 6\n</td></tr></table>\n<hr />\n<p>\nWhat about URLs?\n</p>\n<p>\n<a target="_blank" href="http://www.cdc.gov">http://www.cdc.gov</a> \n</p>\n<p>\n<a target="_blank" href="http://www.cdc.gov">http://www.cdc.gov</a>\n</p>\n<p>\n[wiki:WonderLand]\n</p>\n<p>\nWonderLand\n</p>\n<p>\n<img src="http://www.edgewall.com/gfx/trac_example_image.png" alt="http://www.edgewall.com/gfx/trac_example_image.png" />\n</p>\n<p>\n[[Timestamp]]\n</p>\n',
            '= Pandemic Influenza =\n== Important information ==\n\n <strong> Something\n </strong> Whatever\n   <strong> <del>Struck-out</del>\n </strong> Something <tt></tt><tt>monospaced</tt><tt></tt> (should be <tt>monospaced</tt>) or <tt>**monospaced**</tt>\n   <strong> </strong>Bold<strong>\n   </strong> <i>Italic</i>\n      <strong> </strong><i>Bold/italic</i><strong>\n  </strong> <span class="underline">underlining</span> the <strong>importance</strong> of <sup>upper</sup> and <sub>lower</sub> bounds for H<sub>2</sub>O consumption or 2<sup>3</sup> = 8\n\nLine 1[[BR]]Line 2\n\n  1. One\n    1. One point one\n  1. Two\n\n llama::\n  a hairy, spitting beast\n python::\n  a hairless herpetic beasty\n\nA paragraph of words\n  And an indented paragraph of words which go on and on and on endlessly like some form of verbal diarrhoea or worse, please stop I can\'t stand it!\n\nA paragraph of words\n  And an indented paragraph of words which go on and on and \non endlessly like some form of verbal diarrhoea or worse, \nplease stop I can\'t stand it!\n\nA paragraph of words\n  And an indented paragraph of words which go on and on and \n  on endlessly like some form of verbal diarrhoea or worse, \n  please stop I can\'t stand it!\n\n||Cell 1||Cell 2||Cell 3||\n||Cell 4||Cell 5||Cell 6||\n\n----\n\nWhat about URLs?\n\n<a target="_blank" href="http://www.cdc.gov">http://www.cdc.gov</a> \n\n<a target="_blank" href="http://www.cdc.gov">http://www.cdc.gov</a>\n\n[wiki:WonderLand]\n\nWonderLand\n\n<a target="_blank" href="http://www.edgewall.com/gfx/trac_example_image.png">http://www.edgewall.com/gfx/trac_example_image.png</a>\n\n[[Timestamp]]\n'),
    ]

# These should remain unchanged
WIKI_TESTS = [
		'Tickets: #1 or ticket:1',
		'Reports: {1} or report:1',
		'Changesets: r1, [1] or changeset:1',
		'Revision Logs: r1:3, [1:3] or log:branches/0.8-stable#1:3',
		'Wiki pages: CamelCase or wiki:CamelCase',
		'Milestones: milestone:1.0 or milestone:"End-of-days Release"',
		'Files: source:trunk/COPYING',
		'Attachments: attachment:"file name.doc"',
		'A specific file revision: source:/trunk/COPYING#200',
		'A filename with embedded space: source:"/trunk/README FIRST"',
    ]

class WikiFmt(testcommon.TestCase):
    def _test(self, fn, args, expect):
        result = fn(*args)
        self.assertEqLines(result, expect, 'input %s' % args[0])
#        self.assertEqual(result, expect, 
#                         'input %s, expected %r, got %r' % \
#                            (args[0], expect, result))

    def setUp(self):
        self.app = SimpleAppContext(None)
        self.app.config = config
        self.env = Environment(self.app)
        self.env.href = Href(self.env.config.appname)

    def test_casemgr_wiki(self):
        for input, html_output, oneliner_output in CASEMGR_TESTS:
            self._test(wiki_to_html, (input, self.env), html_output);
            self._test(wiki_to_oneliner, (input, self.env), oneliner_output);

    def test_trac_disabled(self):
        # These Trac markup strings should come through unchanged
        # (the functionality has been removed)
        for input in WIKI_TESTS:
            self._test(wiki_to_html, (input, self.env), 
                       '<p>\n%s\n</p>\n' % input);
            self._test(wiki_to_oneliner, (input, self.env), input);
