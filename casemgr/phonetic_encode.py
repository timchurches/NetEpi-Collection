# =============================================================================
# encode.py - Routines for Soundex, NYSIIS and Double-Metaphone string
#             encodings.
#
# Freely extensible biomedical record linkage (Febrl) Version 0.2.2
# See http://datamining.anu.edu.au/projects/linkage.html
#
# =============================================================================
# AUSTRALIAN NATIONAL UNIVERSITY OPEN SOURCE LICENSE (ANUOS LICENSE)
# VERSION 1.1
#
# The contents of this file are subject to the ANUOS License Version 1.1 (the
# "License"); you may not use this file except in compliance with the License.
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for
# the specific language governing rights and limitations under the License.
# The Original Software is "encode.py".
# The Initial Developers of the Original Software are Dr Peter Christen
# (Department of Computer Science, Australian National University) and Dr Tim
# Churches (Centre for Epidemiology and Research, New South Wales Department
# of Health). Copyright (C) 2002, 2003 the Australian National University and
# others. All Rights Reserved.
# Contributors:
#
# =============================================================================

"""Module encode.py - Routines for Soundex, Phonex, NYSIIS and Double-Metaphone
                      string encodings.

   Provides routines for different string encodings (as well as for encodings
   of reversed names).

   ROUTINES
     soundex      Soundex
     mod_soundex  Modified Soundex
     phonex       Phonex
     nysiis       NYSIIS
     dmetaphone   Double-Metaphone

   See doc strings of individual routines for detailed documentation.

   Note that all encoding routines assume the input string only contains
   letters and whitespaces, , but not digits or other ASCII characters.

   If called from command line, a test routine is run which prints example
   encodings for various strings.
"""

verbose = False

# =============================================================================
# Imports go here

import string

# =============================================================================

def soundex(s, maxlen=4):
  """Compute the soundex code for a string.

  USAGE:
    code = soundex(s, maxlen):

  ARGUMENTS:
    s        A string containing a name.
    maxlen   Maximal length of the returned code. If a code is longer than
             'maxlen' it is truncated. Default value is 4.

  DESCRIPTION:
    For more information on Soundex see:
    - http://www.bluepoof.com/Soundex/info.html
    - http://www.nist.gov/dads/HTML/soundex.html
  """

  # Translation table and characters that will not be used for soundex  - - - -
  #
  transtable = string.maketrans('abcdefghijklmnopqrstuvwxyz', \
                                '01230120022455012623010202')
  # deletechars='aeiouhwy '
  deletechars = ' '

  if (not s):
    return maxlen*'0'  # Or 'z000' for compatibility with other implementations

  s2 = string.translate(s[1:],transtable,deletechars)

  s3 = s[0]  # Keep first character of original string

  # Only add numbers if they are not the same as the previous number
  for i in s2:
    if (i != s3[-1]):
      s3 = s3+i

  # Remove all '0'
  s4 = s3.replace('0', '')

  # Fill up with '0' to maxlen length
  #
  s4 = s4+maxlen*'0'

  # A log message for high volume log output (level 3) - - - - - - - - - - - -
  #
  if verbose:
    print '3:  Soundex encoding for string: "%s"' % (s)
    print '3:    Code: %s' % (s4[:maxlen])

  return s4[:maxlen]  # Return first maxlen characters

# =============================================================================

def mod_soundex(s, maxlen=4):
  """Compute the modified soundex code for a string.

  USAGE:
    code = mod_soundex(s, maxlen):

  ARGUMENTS:
    s        A string containing a name.
    maxlen   Maximal length of the returned code. If a code is longer than
             'maxlen' it is truncated. Default value is 4.

  DESCRIPTION:
    For more information on the modified Soundex see:
    - http://www.bluepoof.com/Soundex/info2.html
  """

  # Translation table and characters that will not be used for soundex  - - - -
  #
  transtable = string.maketrans('abcdefghijklmnopqrstuvwxyz', \
                                '01360240043788015936020505')
  deletechars='aeiouhwy '

  if (not s):
    return maxlen*'0'  # Or 'z000' for compatibility with other implementations

  s2 = string.translate(s[1:],transtable, deletechars)

  s3 = s[0]  # Keep first character of original string

  # Only add numbers if they are not the same as the previous number
  for i in s2:
    if (i != s3[-1]):
      s3 = s3+i

  # Fill up with '0' to maxlen length
  #
  s4 = s3+maxlen*'0'

  # A log message for high volume log output (level 3) - - - - - - - - - - - -
  #
  if verbose:
    print '3:  Mod Soundex encoding for string: "%s"' % (s)
    print '3:    Code: %s' % (s4[:maxlen])

  return s4[:maxlen]

# =============================================================================

def phonex(s, maxlen=4):
  """Compute the phonex code for a string.

  USAGE:
    code = phonex(s, maxlen):

  ARGUMENTS:
    s        A string containing a name.
    maxlen   Maximal length of the returned code. If a code is longer than
             'maxlen' it is truncated. Default value is 4.

  DESCRIPTION:
    Based on the algorithm as described in:
    "An Assessment of Name Matching Algorithms, A.J. Lait and B. Randell,
     Technical Report number 550, Department of Computing Science,
     University of Newcastle upon Tyne, 1996"

    Available at: 
      http://www.cs.ncl.ac.uk/~brian.randell/home.informal/
             Genealogy/NameMatching.pdf

    Bug-fixes regarding 'h','ss','hss' etc. strings thanks to Marion Sturtevant
  """

  if (not s):
    return maxlen*'0'  # Or 'z000' for compatibility with other implementations

  # Preprocess input string - - - - - - - - - - - - - - - - - - - - - - - - - -
  #
  while (s and s[-1] == 's'):  # Remove all 's' at the end
    s = s[:-1]

  if (not s):
    return maxlen*'0'

  if (s[:2] == 'kn'):  # Remove 'k' from beginning if followed by 'n'
    s = s[1:]
  elif (s[:2] == 'ph'):  # Replace 'ph' at beginning with 'f'
    s = 'f'+s[2:]
  elif (s[:2] == 'wr'):  # Remove 'w' from beginning if followed by 'r'
    s = s[1:]

  if (s[0] == 'h'):  # Remove 'h' from beginning
    s = s[1:]

  if (not s):
    return maxlen*'0'

  # Make phonetic equivalence of first character
  #
  if (s[0] in 'eiouy'):
    s = 'a'+s[1:]
  elif (s[0] == 'p'):
    s = 'b'+s[1:]
  elif (s[0] == 'v'):
    s = 'f'+s[1:]
  if (s[0] in 'kq'):
    s = 'c'+s[1:]
  elif (s[0] == 'j'):
    s = 'g'+s[1:]
  elif (s[0] == 'z'):
    s = 's'+s[1:]

  # Modified soundex coding - - - - - - - - - - - - - - - - - - - - - - - - - -
  #

  s_len = len(s)
  code = ''  # Phonex code
  i = 0

  while (i < s_len):  # Loop over all characters in s
    s_i = s[i]
    code_i = '0'  # Default code

    if (s_i in 'bfpv'):
      code_i = '1'

    elif (s_i in 'cskgjqxz'):
      code_i = '2'

    elif (s_i in 'dt') and (i < s_len-1) and (s[i+1] != 'c'):
      code_i = '3'

    elif (s_i == 'l') and ((i == s_len-1) or \
                           ((i < s_len-1) and (s[i+1] in 'aeiouy'))):
      code_i = '4'

    elif (s_i in 'mn'):
      code_i = '5'
      if (i < s_len-1) and (s[i+1] in 'dg'):
        s = s[:i+1]+s_i+s[i+2:]  # Replace following D or G with current M or N

    elif (s_i == 'r') and ((i == s_len-1) or \
                           ((i < s_len-1) and (s[i+1] in 'aeiouy'))):
      code_i = '6'

    if (i == 0):  # Handle beginning of string
      last = code_i
      code += s_i  # Start code with a letter

    else:
      if (code_i != last) and (code_i != '0'):

        # If the code differs from previous code and it's not a vowel code
        #
        code += code_i

      last = code[-1]
    i += 1

  # Fill up with '0' to maxlen length
  #
  code += maxlen*'0'

  # A log message for high volume log output (level 3) - - - - - - - - - - - -
  #
  if verbose:
    print '3:  Phonex encoding for string: "%s"' % (s)
    print '3:    Code: %s' % (code[:maxlen])

  return code[:maxlen]  # Return first maxlen characters

# =============================================================================

def nysiis(s, maxlen=4):
  """Compute the NYSIIS code for a string.

  USAGE:
    code = nysiis(s, maxlen):

  ARGUMENTS:
    s        A string containing a name.
    maxlen   Maximal length of the returned code. If a code is longer than
             'maxlen' it is truncated. Default value is 4.

  DESCRIPTION:
    For more information on NYSIIS see:
    - http://www.dropby.com/indexLF.html?content=/NYSIIS.html
    - http://www.nist.gov/dads/HTML/nysiis.html
  """

  if (not s):
    return ''

  # Remove trailing S or Z
  #
  while s and s[-1] in 'sz':
    s = s[:-1]

  # Translate first characters of string  
  #
  if (s[:3] == 'mac'):  # Initial 'MAC' -> 'MC'
    s = 'mc'+s[3:]
  elif (s[:2] == 'pf'):  # Initial 'PF' -> 'F'
    s = s[1:]

  # Translate some suffix characters:
  #
  suff_dict = {'ix':'ic', 'ex':'ec', 'ye':'y', 'ee':'y', 'ie':'y', \
               'dt':'d', 'rt':'d', 'rd':'d', 'nt':'n', 'nd':'n'}
  suff = s[-2:]
  s = s[:-2]+suff_dict.get(suff, suff)  # Replace suffix if in dictionary

  # Replace EV with EF
  #
  if (s[2:].find('ev') > -1):
    s = s[:-2]+s[2:].replace('ev','ef')

  if (not s):
    return ''

  first = s[0]  # Save first letter for final code

  # Replace all vowels with A and delete whitespaces
  #
  voweltable = string.maketrans('eiou', 'aaaa')
  s2 = string.translate(s,voweltable, ' ')

  if (not s2):  # String only contained whitespaces
    return ''

  # Remove all W that follow an A
  #
  s2 = s2.replace('aw','a')

  # Various replacement patterns
  #
  s2 = s2.replace('ght','gt')
  s2 = s2.replace('dg','g')
  s2 = s2.replace('ph','f')
  s2 = s2[0]+s2[1:].replace('ah','a')
  s3 = s2[0]+s2[1:].replace('ha','a')
  s3 = s3.replace('kn','n')
  s3 = s3.replace('k','c')
  s4 = s3[0]+s3[1:].replace('m','n')
  s5 = s4[0]+s4[1:].replace('q','g')
  s5 = s5.replace('sh','s')
  s5 = s5.replace('sch','s')
  s5 = s5.replace('yw','y')
  s5 = s5.replace('wr','r')

  # If not first or last, replace Y with A  
  #
  s6 = s5[0]+s5[1:-1].replace('y','a')+s5[-1]

  # If not first character, replace Z with S
  #
  s7 = s6[0]+s6[1:].replace('z','s')

  # Replace trailing AY with Y
  #
  if (s7[-2:] == 'ay'):
    s7 = s7[:-2]+'y'

  # Remove trailing vowels (now only A)
  #
  while s7 and s7[-1] == 'a':
    s7 = s7[:-1]

  if (len(s7) == 0):
    resstr = ''
  else:
    resstr = s7[0]

    # Only add letters if they differ from the previous letter
    #
    for i in s7[1:]:
      if (i != resstr[-1]):
        resstr=resstr+i

  # Now compile final result string
  #
  if (first in 'aeiou'):
    resstr = first+resstr[1:]

  # A log message for high volume log output (level 3) - - - - - - - - - - - -
  #
  if verbose:
    print '3:  NYSIIS encoding for string: "%s"' % (s)
    print '3:    Code: %s' % (resstr[:maxlen])

  return resstr[:maxlen]

# =============================================================================

def dmetaphone(s, maxlen=4):
  """Compute the Double Metaphone code for a string.

  USAGE:
    code = dmetaphone(s, maxlen):

  ARGUMENTS:
    s        A string containing a name.
    maxlen   Maximal length of the returned code. If a code is longer than
             'maxlen' it is truncated. Default value is 4.

  DESCRIPTION:
    Based on:
    - Lawrence Philips C++ code as published in C/C++ Users Journal (June 2000)
      and available at:
      http://www.cuj.com/articles/2000/0006/0006d/0006d.htm
    - Perl/C implementation
      http://www.cpan.org/modules/by-authors/id/MAURICE/
    See also:
    - http://aspell.sourceforge.net/metaphone/
    - http://www.nist.gov/dads/HTML/doubleMetaphone.html
  """

  if (not s):
    return ''

  primary = ''
  secondary = ''
  alternate = ''
  primary_len = 0
  secondary_len = 0

  # Sub routines  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
  #
  def isvowel(c):
    if (c in 'aeiouy'):
      return 1
    else:
      return 0

  def slavogermanic(str):
    if (str.find('w')>-1) or (str.find('k')>-1) or (str.find('cz')>-1) or \
       (str.find('witz')>-1):
      return 1
    else:
      return 0

  # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

  length = len(s)
  if (len < 1):
    return ''
  last = length-1

  current = 0  # Current position in string
  workstr = s+'      '

  if (workstr[0:2] in ['gn','kn','pn','wr','ps']):
    current = current+1  # Skip first character

  if (workstr[0] == 'x'):  # Initial 'x' is pronounced like 's'
    primary = primary+'s'
    primary_len = primary_len+1
    secondary = secondary+'s'
    secondary_len = secondary_len+1
    current = current+1

  while (primary_len < maxlen) or (secondary_len < maxlen):
    if (current >= length):
      break

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # Main loop, analyse current character
    #
    c = workstr[current]

    if (c in 'aeiouy'):
      if (current == 0):  # All initial vowels map to 'a'
        primary = primary+'a'
        primary_len = primary_len+1
        secondary = secondary+'a'
        secondary_len = secondary_len+1
      current=current+1

    elif (c == 'b'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      primary = primary+'p'
      primary_len = primary_len+1
      secondary = secondary+'p'
      secondary_len = secondary_len+1
      if (workstr[current+1] == 'b'):
        current=current+2
      else:
        current=current+1

    # elif (s == 'c'):  # C
    #    primary = primary+'s'
    #    primary_len = primary_len+1
    #    secondary = secondary+'s'
    #    secondary_len = secondary_len+1
    #    current = current+1

    elif (c == 'c'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (current > 1) and (not isvowel(workstr[current-2])) and \
         workstr[current-1:current+2] == 'ach' and \
         (workstr[current+2] != 'i' and \
         (workstr[current+2] != 'e' or \
          workstr[current-2:current+4] in ['bacher','macher'])):
        primary = primary+'k'  # Various germanic special cases
        primary_len = primary_len+1
        secondary = secondary+'k'
        secondary_len = secondary_len+1
        current = current+2
      elif (current == 0) and (workstr[0:6] == 'caesar'):
        primary = primary+'s'
        primary_len = primary_len+1
        secondary = secondary+'s'
        secondary_len = secondary_len+1
        current = current+2
      elif (workstr[current:current+4] == 'chia'): # Italian 'chianti'
        primary = primary+'k'
        primary_len = primary_len+1
        secondary = secondary+'k'
        secondary_len = secondary_len+1
        current = current+2
      elif (workstr[current:current+2] == 'ch'):
        if (current > 0) and (workstr[current:current+4] == 'chae'):
          primary = primary+'k'  # Find 'michael'
          primary_len = primary_len+1
          secondary = secondary+'x'
          secondary_len = secondary_len+1
          current = current+2
        elif (current == 0) and \
           (workstr[current+1:current+6] in ['harac','haris'] or \
            workstr[current+1:current+4] in \
              ['hor','hym','hia','hem']) and \
           workstr[0:6] != 'chore':
          primary = primary+'k'  # Greek roots, eg. 'chemistry'
          primary_len = primary_len+1
          secondary = secondary+'k'
          secondary_len = secondary_len+1
          current = current+2
        elif (workstr[0:4] in ['van ','von '] or \
              workstr[0:3] == 'sch') or \
            workstr[current-2:current+4] in \
              ['orches','archit','orchid'] or \
            workstr[current+2] in ['t','s'] or \
            ((workstr[current-1] in ['a','o','u','e'] or \
              current==0) and \
            workstr[current+2] in \
              ['l','r','n','m','b','h','f','v','w',' ']):
          primary = primary+'k'
          primary_len = primary_len+1
          secondary = secondary+'k'
          secondary_len = secondary_len+1
          current = current+2
        else:
          if (current > 0):
            if (workstr[0:2] == 'mc'):
              primary = primary+'k'
              primary_len = primary_len+1
              secondary = secondary+'k'
              secondary_len = secondary_len+1
              current = current+2
            else:
              primary = primary+'x'
              primary_len = primary_len+1
              secondary = secondary+'k'
              secondary_len = secondary_len+1
              current = current+2
          else:
            primary = primary+'x'
            primary_len = primary_len+1
            secondary = secondary+'x'
            secondary_len = secondary_len+1
            current=current+2
      elif (workstr[current:current+2] == 'cz') and \
         (workstr[current-2:current+2] != 'wicz'):
        primary = primary+'s'
        primary_len = primary_len+1
        secondary = secondary+'x'
        secondary_len = secondary_len+1
        current=current+2
      elif (workstr[current+1:current+4] == 'cia'):
        primary = primary+'x'
        primary_len = primary_len+1
        secondary = secondary+'x'
        secondary_len = secondary_len+1
        current=current+3
      elif (workstr[current:current+2] == 'cc') and \
           not (current==1 and workstr[0] == 'm'):
        if (workstr[current+2] in ['i','e','h']) and \
           (workstr[current+2:current+4] != 'hu'):
          if (current == 1 and workstr[0] == 'a') or \
             (workstr[current-1:current+4] in ['uccee','ucces']):
            primary = primary+'ks'
            primary_len = primary_len+2
            secondary = secondary+'ks'
            secondary_len = secondary_len+2
            current=current+3
          else:
            primary = primary+'x'
            primary_len = primary_len+1
            secondary = secondary+'x'
            secondary_len = secondary_len+1
            current=current+3
        else:  # Pierce's rule
          primary = primary+'k'
          primary_len = primary_len+1
          secondary = secondary+'k'
          secondary_len = secondary_len+1
          current=current+2
      elif (workstr[current:current+2] in ['ck','cg','cq']):
        primary = primary+'k'
        primary_len = primary_len+1
        secondary = secondary+'k'
        secondary_len = secondary_len+1
        current=current+2
      elif (workstr[current:current+2] in ['ci','ce','cy']):
        if (workstr[current:current+3] in ['cio','cie','cia']):
          primary = primary+'s'
          primary_len = primary_len+1
          secondary = secondary+'x'
          secondary_len = secondary_len+1
          current=current+2
        else:
          primary = primary+'s'
          primary_len = primary_len+1
          secondary = secondary+'s'
          secondary_len = secondary_len+1
          current=current+2
      else:
        primary = primary+'k'
        primary_len = primary_len+1
        secondary = secondary+'k'
        secondary_len = secondary_len+1
        if (workstr[current+1:current+3] in [' c',' q',' g']):
          current=current+3
        else:
          if (workstr[current+1] in ['c','k','q']) and \
             (workstr[current+1:current+3] not in ['ce','ci']):
            current=current+2
          else:
            current=current+1

    elif (c == 'd'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current:current+2] == 'dg'):
        if (workstr[current+2] in ['i','e','y']):  # Eg. 'edge'
          primary = primary+'j'
          primary_len = primary_len+1
          secondary = secondary+'j'
          secondary_len = secondary_len+1
          current=current+3
        else:  # Eg. 'edgar'
          primary = primary+'tk'
          primary_len = primary_len+2
          secondary = secondary+'tk'
          secondary_len = secondary_len+2
          current=current+2
      elif (workstr[current:current+2] in ['dt','dd']):
        primary = primary+'t'
        primary_len = primary_len+1
        secondary = secondary+'t'
        secondary_len = secondary_len+1
        current=current+2
      else:
        primary = primary+'t'
        primary_len = primary_len+1
        secondary = secondary+'t'
        secondary_len = secondary_len+1
        current=current+1

    elif (c == 'f'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'f'):
        current=current+2
      else:
        current=current+1
      primary = primary+'f'
      primary_len = primary_len+1
      secondary = secondary+'f'
      secondary_len = secondary_len+1

    elif (c == 'g'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'h'):
        if (current > 0 and not isvowel(workstr[current-1])):
          primary = primary+'k'
          primary_len = primary_len+1
          secondary = secondary+'k'
          secondary_len = secondary_len+1
          current=current+2
        elif (current==0):
          if (workstr[current+2] == 'i'): # Eg. ghislane, ghiradelli
            primary = primary+'j'
            primary_len = primary_len+1
            secondary = secondary+'j'
            secondary_len = secondary_len+1
            current=current+2
          else:
            primary = primary+'k'
            primary_len = primary_len+1
            secondary = secondary+'k'
            secondary_len = secondary_len+1
            current=current+2
        elif (current>1 and workstr[current-2] in ['b','h','d']) or \
             (current>2 and workstr[current-3] in ['b','h','d']) or \
             (current>3 and workstr[current-4] in ['b','h']):
          current=current+2
        else:
          if (current > 2) and (workstr[current-1] == 'u') and \
             (workstr[current-3] in ['c','g','l','r','t']):
            primary = primary+'f'
            primary_len = primary_len+1
            secondary = secondary+'f'
            secondary_len = secondary_len+1
            current=current+2
          else:
            if (current > 0) and (workstr[current-1] != 'i'):
              primary = primary+'k'
              primary_len = primary_len+1
              secondary = secondary+'k'
              secondary_len = secondary_len+1
              current=current+2
            else:
              current=current+2
      elif (workstr[current+1] == 'n'):
        if (current==1) and (isvowel(workstr[0])) and \
           (not slavogermanic(workstr)):
          primary = primary+'kn'
          primary_len = primary_len+2
          secondary = secondary+'n'
          secondary_len = secondary_len+1
          current=current+2
        else:
          if (workstr[current+2:current+4] != 'ey') and \
             (workstr[current+1] != 'y') and \
             (not slavogermanic(workstr)):
            primary = primary+'n'
            primary_len = primary_len+1
            secondary = secondary+'kn'
            secondary_len = secondary_len+2
            current=current+2
          else:
            primary = primary+'kn'
            primary_len = primary_len+2
            secondary = secondary+'kn'
            secondary_len = secondary_len+2
            current=current+2
      elif (workstr[current+1:current+3] == 'li') and \
           (not slavogermanic(workstr)):
        primary = primary+'kl'
        primary_len = primary_len+2
        secondary = secondary+'l'
        secondary_len = secondary_len+1
        current=current+2
      elif (current==0) and ((workstr[current+1] == 'y') or \
           (workstr[current+1:current+3] in \
           ['es','ep','eb','el','ey','ib','il','in','ie','ei','er'])):
        primary = primary+'k'
        primary_len = primary_len+1
        secondary = secondary+'j'
        secondary_len = secondary_len+1
        current=current+2
      elif (workstr[current+1:current+3] == 'er' or \
           workstr[current+1] == 'y') and \
           workstr[0:6] not in ['danger','ranger','manger'] and \
           workstr[current-1] not in ['e','i'] and \
           workstr[current-1:current+2] not in ['rgy','ogy']:
        primary = primary+'k'
        primary_len = primary_len+1
        secondary = secondary+'j'
        secondary_len = secondary_len+1
        current=current+2
      elif (workstr[current+1] in ['e','i','y']) or \
           (workstr[current-1:current+3] in ['aggi','oggi']):
        if (workstr[0:4] in ['van ','von ']) or \
           (workstr[0:3] == 'sch') or \
           (workstr[current+1:current+3] == 'et'):
          primary = primary+'k'
          primary_len = primary_len+1
          secondary = secondary+'k'
          secondary_len = secondary_len+1
          current=current+2
        else:
          if (workstr[current+1:current+5] == 'ier '):
            primary = primary+'j'
            primary_len = primary_len+1
            secondary = secondary+'j'
            secondary_len = secondary_len+1
            current=current+2
          else:
            primary = primary+'j'
            primary_len = primary_len+1
            secondary = secondary+'k'
            secondary_len = secondary_len+1
            current=current+2
      else:
        if (workstr[current+1] == 'g'):
          current=current+2
        else:
          current=current+1
        primary = primary+'k'
        primary_len = primary_len+1
        secondary = secondary+'k'
        secondary_len = secondary_len+1

    elif (c =='h'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (current == 0 or isvowel(workstr[current-1])) and \
         isvowel(workstr[current+1]):
        primary = primary+'h'
        primary_len = primary_len+1
        secondary = secondary+'h'
        secondary_len = secondary_len+1
        current=current+2
      else:
        current=current+1

    elif (c =='j'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current:current+4] == 'jose') or \
         (workstr[0:4] == 'san '):
        if (current == 0 and workstr[4] == ' ') or \
           (workstr[0:4] == 'san '):
          primary = primary+'h'
          primary_len = primary_len+1
          secondary = secondary+'h'
          secondary_len = secondary_len+1
          current=current+1
        else:
          primary = primary+'j'
          primary_len = primary_len+1
          secondary = secondary+'h'
          secondary_len = secondary_len+1
          current=current+1
      elif (current==0) and (workstr[0:4] != 'jose'):
        primary = primary+'j'
        primary_len = primary_len+1
        secondary = secondary+'a'
        secondary_len = secondary_len+1
        if (workstr[current+1] == 'j'):
          current=current+2
        else:
          current=current+1
      else:
        if (isvowel(workstr[current-1])) and \
           (not slavogermanic(workstr)) and \
           (workstr[current+1] in ['a','o']):
          primary = primary+'j'
          primary_len = primary_len+1
          secondary = secondary+'h'
          secondary_len = secondary_len+1
        else:
          if (current == last):
            primary = primary+'j'
            primary_len = primary_len+1
            #secondary = secondary+''
            #secondary_len = secondary_len+0
          else:
            if (workstr[current+1] not in \
               ['l','t','k','s','n','m','b','z']) and \
               (workstr[current-1] not in ['s','k','l']):
              primary = primary+'j'
              primary_len = primary_len+1
              secondary = secondary+'j'
              secondary_len = secondary_len+1
        if (workstr[current+1] == 'j'):
          current=current+2
        else:
          current=current+1

    elif (c =='k'):  #  - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'k'):
        current=current+2
      else:
        current=current+1
      primary = primary+'k'
      primary_len = primary_len+1
      secondary = secondary+'k'
      secondary_len = secondary_len+1

    elif (c == 'l'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'l'):
        if (current == (length-3)) and \
           (workstr[current-1:current+3] in ['illo','illa','alle']) or \
           ((workstr[last-1:last+1] in ['as','os']  or
           workstr[last] in ['a','o']) and \
           workstr[current-1:current+3] == 'alle'):
          primary = primary+'l'
          primary_len = primary_len+1
          #secondary = secondary+''
          #secondary_len = secondary_len+0
          current=current+2
        else:
          primary = primary+'l'
          primary_len = primary_len+1
          secondary = secondary+'l'
          secondary_len = secondary_len+1
          current=current+2
      else:
        primary = primary+'l'
        primary_len = primary_len+1
        secondary = secondary+'l'
        secondary_len = secondary_len+1
        current=current+1

    elif (c == 'm'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current-1:current+2] == 'umb' and \
         ((current+1) == last or \
          workstr[current+2:current+4] == 'er')) or \
         workstr[current+1] == 'm':
        current=current+2
      else:
        current=current+1
      primary = primary+'m'
      primary_len = primary_len+1
      secondary = secondary+'m'
      secondary_len = secondary_len+1

    elif (c == 'n'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'n'):
        current=current+2
      else:
        current=current+1
      primary = primary+'n'
      primary_len = primary_len+1
      secondary = secondary+'n'
      secondary_len = secondary_len+1

    elif (c == 'p'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'h'):
        primary = primary+'f'
        primary_len = primary_len+1
        secondary = secondary+'f'
        secondary_len = secondary_len+1
        current=current+2
      elif (workstr[current+1] in ['p','b']):
        primary = primary+'p'
        primary_len = primary_len+1
        secondary = secondary+'p'
        secondary_len = secondary_len+1
        current=current+2
      else:
        primary = primary+'p'
        primary_len = primary_len+1
        secondary = secondary+'p'
        secondary_len = secondary_len+1
        current=current+1

    elif (c == 'q'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'q'):
        current=current+2
      else:
        current=current+1
      primary = primary+'k'
      primary_len = primary_len+1
      secondary = secondary+'k'
      secondary_len = secondary_len+1

    elif (c == 'r'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (current==last) and (not slavogermanic(workstr)) and \
         (workstr[current-2:current] == 'ie') and \
         (workstr[current-4:current-2] not in ['me','ma']):
        # primary = primary+''
        # primary_len = primary_len+0
        secondary = secondary+'r'
        secondary_len = secondary_len+1
      else:
        primary = primary+'r'
        primary_len = primary_len+1
        secondary = secondary+'r'
        secondary_len = secondary_len+1
      if (workstr[current+1] == 'r'):
        current=current+2
      else:
        current=current+1

    elif (c == 's'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current-1:current+2] in ['isl','ysl']):
        current=current+1
      elif (current==0) and (workstr[0:5] == 'sugar'):
        primary = primary+'x'
        primary_len = primary_len+1
        secondary = secondary+'s'
        secondary_len = secondary_len+1
        current=current+1
      elif (workstr[current:current+2] == 'sh'):
        if (workstr[current+1:current+5] in \
           ['heim','hoek','holm','holz']):
          primary = primary+'s'
          primary_len = primary_len+1
          secondary = secondary+'s'
          secondary_len = secondary_len+1
          current=current+2
        else:
          primary = primary+'x'
          primary_len = primary_len+1
          secondary = secondary+'x'
          secondary_len = secondary_len+1
          current=current+2
      elif (workstr[current:current+3] in ['sio','sia']) or \
           (workstr[current:current+4] == 'sian'):
        if (not slavogermanic(workstr)):
          primary = primary+'s'
          primary_len = primary_len+1
          secondary = secondary+'x'
          secondary_len = secondary_len+1
          current=current+3
        else:
          primary = primary+'s'
          primary_len = primary_len+1
          secondary = secondary+'s'
          secondary_len = secondary_len+1
          current=current+3
      elif ((current==0) and (workstr[1] in ['m','n','l','w'])) or \
           (workstr[current+1] == 'z'):
        primary = primary+'s'
        primary_len = primary_len+1
        secondary = secondary+'x'
        secondary_len = secondary_len+1
        if (workstr[current+1] == 'z'):
          current=current+2
        else:
          current=current+1
      elif (workstr[current:current+2] == 'sc'):
        if (workstr[current+2] == 'h'):
          if (workstr[current+3:current+5] in \
             ['oo','er','en','uy','ed','em']):
            if (workstr[current+3:current+5] in ['er','en']):
              primary = primary+'x'
              primary_len = primary_len+1
              secondary = secondary+'sk'
              secondary_len = secondary_len+2
              current=current+3
            else:
              primary = primary+'sk'
              primary_len = primary_len+2
              secondary = secondary+'sk'
              secondary_len = secondary_len+2
              current=current+3
          else:
            if (current==0) and (not isvowel(workstr[3])) and \
               (workstr[3] != 'w'):
              primary = primary+'x'
              primary_len = primary_len+1
              secondary = secondary+'s'
              secondary_len = secondary_len+1
              current=current+3
            else:
              primary = primary+'x'
              primary_len = primary_len+1
              secondary = secondary+'x'
              secondary_len = secondary_len+1
              current=current+3
        elif (workstr[current+2] in ['i','e','y']):
          primary = primary+'s'
          primary_len = primary_len+1
          secondary = secondary+'s'
          secondary_len = secondary_len+1
          current=current+3
        else:
          primary = primary+'sk'
          primary_len = primary_len+2
          secondary = secondary+'sk'
          secondary_len = secondary_len+2
          current=current+3
      elif (current==last) and \
           (workstr[current-2:current] in ['ai','oi']):
        # primary = primary+''
        # primary_len = primary_len+0
        secondary = secondary+'s'
        secondary_len = secondary_len+1
        if (workstr[current+1] in ['s','z']):
          current=current+2
        else:
          current=current+1
      else:
        primary = primary+'s'
        primary_len = primary_len+1
        secondary = secondary+'s'
        secondary_len = secondary_len+1
        if (workstr[current+1] in ['s','z']):
          current=current+2
        else:
          current=current+1

    elif (c == 't'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current:current+4] == 'tion'):
        primary = primary+'x'
        primary_len = primary_len+1
        secondary = secondary+'x'
        secondary_len = secondary_len+1
        current=current+3
      elif (workstr[current:current+3] in ['tia','tch']):
        primary = primary+'x'
        primary_len = primary_len+1
        secondary = secondary+'x'
        secondary_len = secondary_len+1
        current=current+3
      elif (workstr[current:current+2] == 'th') or \
           (workstr[current:current+3] == 'tth'):
        if (workstr[current+2:current+4] in ['om','am']) or \
           (workstr[0:4] in ['von ','van ']) or (workstr[0:3] == 'sch'):
          primary = primary+'t'
          primary_len = primary_len+1
          secondary = secondary+'t'
          secondary_len = secondary_len+1
          current=current+2
        else:
          primary = primary+'0'
          primary_len = primary_len+1
          secondary = secondary+'t'
          secondary_len = secondary_len+1
          current=current+2
      elif (workstr[current+1] in ['t','d']):
        primary = primary+'t'
        primary_len = primary_len+1
        secondary = secondary+'t'
        secondary_len = secondary_len+1
        current=current+2
      else:
        primary = primary+'t'
        primary_len = primary_len+1
        secondary = secondary+'t'
        secondary_len = secondary_len+1
        current=current+1

    elif (c == 'v'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'v'):
        current=current+2
      else:
        current=current+1 
      primary = primary+'f'
      primary_len = primary_len+1
      secondary = secondary+'f'
      secondary_len = secondary_len+1

    elif (c == 'w'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current:current+2] == 'wr'):
        primary = primary+'r'
        primary_len = primary_len+1
        secondary = secondary+'r'
        secondary_len = secondary_len+1
        current=current+2
      else:
        if (current==0) and (isvowel(workstr[1]) or \
           workstr[0:2] == 'wh'):
          if (isvowel(workstr[current+1])):
            primary = primary+'a'
            primary_len = primary_len+1
            secondary = secondary+'f'
            secondary_len = secondary_len+1
            #current=current+1
          else:
            primary = primary+'a'
            primary_len = primary_len+1
            secondary = secondary+'a'
            secondary_len = secondary_len+1
            #current=current+1
        if (current==last and isvowel(workstr[current-1])) or \
           workstr[current-1:current+4] in \
           ['ewski','ewsky','owski','owsky'] or \
           workstr[0:3] == 'sch':
          # primary = primary+''
          # primary_len = primary_len+0
          secondary = secondary+'f'
          secondary_len = secondary_len+1
          current=current+1
        elif (workstr[current:current+4] in ['witz','wicz']):
          primary = primary+'ts'
          primary_len = primary_len+2
          secondary = secondary+'fx'
          secondary_len = secondary_len+2
          current=current+4
        else:
          current=current+1

    elif (c == 'x'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if not (current==last and \
         (workstr[current-3:current] in ['iau','eau'] or \
          workstr[current-2:current] in ['au','ou'])):
        primary = primary+'ks'
        primary_len = primary_len+2
        secondary = secondary+'ks'
        secondary_len = secondary_len+2
      if (workstr[current+1] in ['c','x']):
        current=current+2
      else:
        current=current+1

    elif (c == 'z'):  # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      if (workstr[current+1] == 'h'):
        primary = primary+'j'
        primary_len = primary_len+1
        secondary = secondary+'j'
        secondary_len = secondary_len+1
        current=current+2
      else:
        if (workstr[current+1:current+3] in ['zo','zi','za']) or \
           (slavogermanic(workstr) and \
           (current > 0 and workstr[current-1] != 't')):
          primary = primary+'s'
          primary_len = primary_len+1
          secondary = secondary+'ts'
          secondary_len = secondary_len+2
          if (workstr[current+1] == 'z'):
            current=current+2
          else:
            current=current+1
        else:
          primary = primary+'s'
          primary_len = primary_len+1
          secondary = secondary+'s'
          secondary_len = secondary_len+1
          if (workstr[current+1] == 'z'):
            current=current+2
          else:
            current=current+1

    else:   # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      current=current+1

    # End main loop

  if (primary == secondary):
    # If both codes are the same set the second's length to 0 so it's not used
    secondary_len = 0

  # if (secondary_len > 0):
  #   return [primary[:maxlen], secondary[:maxlen]]
  # else:
  #   return [primary[:maxlen]]

  # A log message for high volume log output (level 3) - - - - - - - - - - - -
  #
  if verbose:
    print '3:  Double Metaphone encoding for string: "%s"' %(s)
    print '3:    Code: %s, secondary code: %s' % \
            (primary[:maxlen], secondary[:maxlen])

  return primary[:maxlen]  # Only return primary encoding

# =============================================================================

#
# Do some tests if called from command line
#

if (__name__ == '__main__'):

  print 'Febrl module "encode.py"'
  print '------------------------'
  print

  print 'Original names:'
  print '            Name     Phonex   Soundex  ModSoundex      NYSIIS  ',
  print '  D-Metaphone'
  print '---------------------------------------------------------------'+ \
        '--------------'

  namelist = ['peter','christen','ole','nielsen','markus','hegland',\
              'stephen','steve','roberts','tim','churches','xiong',\
              'ng','miller','millar','foccachio','van de hooch', \
              'xiao ching','asawakun','prapasri','von der felde','vest',
              'west','oioi','ohio','oihcca', 'nielsen', 'kim', 'lim', \
              'computer','record','linkage','probabilistic']

  for n in namelist:
    soundex_my     = soundex(n)
    soundex_mod_my = mod_soundex(n)
    phonex_my     = phonex(n)
    nysiis_my     = nysiis(n)
    dmeta_my      = dmetaphone(n)

    print '%16s %10s %9s %11s %11s %15s'% \
          (n, phonex_my, soundex_my, soundex_mod_my, nysiis_my, dmeta_my)

  print
  print 'Reversed names:'
  print '            Name     Phonex   Soundex  ModSoundex      NYSIIS  ',
  print '  D-Metaphone'
  print '---------------------------------------------------------------'+ \
        '--------------'

  for n in namelist:
    rn = list(n)
    rn.reverse()
    rn = ''.join(rn)
    soundex_my     = soundex(rn)
    soundex_mod_my = mod_soundex(rn)
    phonex_my     = phonex(rn)
    nysiis_my     = nysiis(rn)
    dmeta_my      = dmetaphone(rn)

    print '%16s %10s %9s %11s %11s %15s'% \
          (rn, phonex_my, soundex_my, soundex_mod_my, nysiis_my, dmeta_my)

# =============================================================================
