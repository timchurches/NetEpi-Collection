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

languages = [
    'Arabic',
    'Armenian',
    'Assyrian',
    'Bosnian',
    'Chinese',
    'Croatian',
    'Farsi/Persian',
    'Filipino/Tagalog',
    'French',
    'German',
    'Greek',
    'Hindi',
    'Hungarian',
    'Indonesian',
    'Italian',
    'Japanese',
    'Khmer/Cambodian',
    'Korean',
    'Lao',
    'Macedonian',
    'Maltese',
    'Polish',
    'Portuguese',
    'Punjabi',
    'Russian',
    'Samoan',
    'Serbian',
    'Somali',
    'Spanish',
    'Thai',
    'Tongan',
    'Turkish',
    'Ukrainian',
    'Vietnamese',
]

language_optionexpr = [(l, l) for l in languages]
language_optionexpr.insert(0, ('', 'None required'))
search_language_optionexpr = [(l, l) for l in languages]
search_language_optionexpr.insert(0, ('!', 'None required'))
search_language_optionexpr.insert(0, ('', 'Any'))
