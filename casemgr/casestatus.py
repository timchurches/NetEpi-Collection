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

# At some point we may reinstate/implement these features:
#  * state transitions dependant on unit access rights
#  * multiple states per case

from casemgr import syndcategorical

class SyndromeCaseStatesInfo(syndcategorical.SyndromeCategoricalInfo):

    title = 'Case Status Values'
    table = 'syndrome_case_status'
    order_by = 'syndcs_id'
    explicit_order = True
    defaults = [
        ('preliminary', 'Preliminary'),
        ('confirmed', 'Confirmed'),
        ('excluded', 'Excluded'),
    ]


class EditSyndromeCaseStates(SyndromeCaseStatesInfo, 
                             syndcategorical.EditSyndromeCategorical):

    pass


class SyndromesCaseStates(SyndromeCaseStatesInfo,
                          syndcategorical.SyndromeCategorical):

    pass


_syndromes_case_states = SyndromesCaseStates()
get_syndrome = _syndromes_case_states.get_syndrome
optionexpr = _syndromes_case_states.optionexpr
get_label = _syndromes_case_states.get_label
normalise_status = _syndromes_case_states.normalise
