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
from cocklebur import dbobj
import core

class AgeInput(core.IntInput):
    type_name = 'Age Input'
    post_text = '(years)'
    minimum = 0
    maximum = 140

class BodyTemperatureInput(core.FloatInput):
    type_name = 'Body Temperature Input (20-50 degree C)'
    post_text = 'Degrees C'
    minimum = 20
    maximum = 50

TemperatureInput = BodyTemperatureInput         # Backward compat

class LabTestResult(core.RadioList):
    type_name = 'Lab Test Results'
    choices = [
        ('NotPerformed', 'Not performed'),
        ('Positive', 'Positive'),
        ('Negative', 'Negative'),
        ('Pending', 'Pending'),
        ('None', 'Unknown'),
    ]

TestResult = LabTestResult                      # Backward compat

from cocklebur.countries import country_optionexpr

class Countries(core.DropList):
    type_name = 'Countries'
    choices = country_optionexpr

from cocklebur.languages import language_optionexpr

class Languages(core.DropList):
    type_name = 'Languages'
    choices = language_optionexpr
