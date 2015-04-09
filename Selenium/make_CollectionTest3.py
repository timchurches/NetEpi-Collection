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

import csv

test_head = """
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<!--

    The contents of this file are subject to the HACOS License Version 1.2
    (the "License"); you may not use this file except in compliance with
    the License.  Software distributed under the License is distributed
    on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
    implied. See the LICENSE file for the specific language governing
    rights and limitations under the License.  The Original Software
    is "NetEpi Collection". The Initial Developer of the Original
    Software is the Health Administration Corporation, incorporated in
    the State of New South Wales, Australia.
    
    Copyright (C) 2004, 2005 Health Administration Corporation and others. 
    All Rights Reserved.

    Contributors: See the CONTRIBUTORS file for details of contributions.

-->

<html>
<head>
  <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type">
  <title>NetEpi Collection Test 3%s - load synthetic cases</title>
  <!-- Loads a few hundred synthesised cases. The names and addresses were
       synthesised using the dbgen utility from the Febrl v0.3 open source
       probabilistic record linkage suite, which is available from
       http://febrl.sourceforge.net Any resemblance of the names and addresses
       in this test to real persons is entirely coincidental.-->
</head>
<body>
<table cellpadding="1" cellspacing="1" border="1">
  <tbody>
    <tr>
      <td rowspan="1" colspan="3">NetEpi Collection Test 3%s - load synthetic cases<br>
      </td>
    </tr>
    <!-- Test login and logout -->
    <tr>
      <td>open</td>
      <td>../../cgi-bin/casemgr/app.py</td>
      <td>&nbsp;</td>
    </tr>
    <tr>
      <td>verifyLocation</td>
      <td>/cgi-bin/casemgr/app.py</td>
      <td>&nbsp;</td>
    </tr>
    <tr>
      <td>verifyTextPresent</td>
      <td>NetEpi Collection<br>
      </td>
      <td>&nbsp;</td>
    </tr>
    <tr>
      <td>type</td>
      <td>user</td>
      <td>admin</td>
    </tr>
    <tr>
      <td>type</td>
      <td>password</td>
      <td>sn00Py</td>
    </tr>
    <tr>
      <td>clickAndWait</td>
      <td>login</td>
      <td>&nbsp;</td>
    </tr>
    <tr>
      <td>verifyTextPresent</td>
      <td>Welcome Administrator</td>
      <td>&nbsp;</td>
    </tr>
    <tr>
      <td>verifyTextPresent</td>
      <td>You are a member of the Administrator Unit.</td>
      <td>&nbsp;</td>
    </tr>
    <tr>
      <td>verifyTextPresent</td>
      <td>SARS</td>
      <td>&nbsp;</td>
    </tr>
"""

offsets_dict = {'a':0,'b':250,'c':500,'d':750}

for series in ['a','b','c','d']:

    # Use the dbgen utility from Febrl (see http://febrl.sourceforge.net)
    # to generate a suitable syntheised dataset.
    data = open('CollectionTest3_data.csv','rb')

    reader = csv.reader(data)
    rownum = -1

    testfile = open('CollectionTest3%s.html' % series,'w')

    print >> testfile, test_head % (series, series)

    template = """
        <!-- Add a new case of SARS -->
        <tr>
          <td>clickAndWait</td>
          <td>new:2</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>Add Case</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>Please search to make sure the person you are going to add is not already in the database.</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>clickAndWait</td>
          <td>do_search</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>Search Results</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>clickAndWait</td>
          <td>new_case</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>Local Case ID</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>Onset Date</td>
          <td>&nbsp;</td>
        </tr>
        <!-- Fill in the details of the new case -->
        <tr>
          <td>type</td>
          <td>local_case_id</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>type</td>
          <td>given_names</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>type</td>
          <td>surname</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>type</td>
          <td>street_address</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>type</td>
          <td>locality</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>type</td>
          <td>postcode</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>select</td>
          <td>state</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>type</td>
          <td>DOB</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>type</td>
          <td>home_phone</td>
          <td>%s</td>
        </tr>
        <!-- Save the data and verify -->
        <tr>
          <td>clickAndWait</td>
          <td>update</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>Onset symptoms (SARS)</td>
          <td>&nbsp;</td>
        </tr>
        <!-- Return to home page -->
        <tr>
          <td>clickAndWait</td>
          <td>home</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>Welcome Administrator</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>You are a member of the Administrator Unit.</td>
          <td>&nbsp;</td>
        </tr>
        <tr>
          <td>verifyTextPresent</td>
          <td>SARS</td>
          <td>&nbsp;</td>
        </tr>
    """

    statesdict = {'NSW':'New South Wales','VIC':'Victoria',
                  'QLD':'Queensland', 'ACT':'Australian Capital Territory',
                  'NT':'Northern Territory', 'SA':'South Australia',
                  'TAS':'Tasmania', 'WA':'Western Australia','':''}

    offset = offsets_dict[series]
    print series, offset
    
    for row in reader:
        rownum += 1
        if rownum > (0 + offset) and rownum < (201 + offset):
            params = (row[12].strip(), row[1].strip(), row[2].strip(), row[3].strip() + ' ' + row[4].strip(),
                     row[6].strip(), row[7].strip(), statesdict[row[8].upper().strip()],
                     str(row[9])[7:9].strip() + '/' + str(row[9])[5:7].strip() + '/' + str(row[9])[1:5].strip(),
                     row[11].strip())
            if params[-2] != '//' and params[-3] != '' and params[2] != '':
                print >> testfile, template % params

    footer = """
            <!-- Return to home page -->
            <tr>
              <td>clickAndWait</td>
              <td>logout</td>
              <td>&nbsp;</td>
            </tr>
    """

    print >> testfile, footer
    testfile.close()

    data.close()

