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


from casemgr import syndcategorical

class SyndromeCaseAssignmentInfo(syndcategorical.SyndromeCategoricalInfo):

    title = 'Case Assignment Values'
    table = 'syndrome_case_assignments'
    order_by = 'syndca_id'
    explicit_order = True
    defaults = [
        ('A', 'Assignment A'),
        ('B', 'Assignment B'),
        ('C', 'Assignment C'),
    ]


class EditSyndromeCaseAssignment(SyndromeCaseAssignmentInfo, 
                                 syndcategorical.EditSyndromeCategorical):

    pass


class SyndromesCaseAssignment(SyndromeCaseAssignmentInfo,
                              syndcategorical.SyndromeCategorical):

    pass


_syndromes_case_assignments = SyndromesCaseAssignment()
get_syndrome = _syndromes_case_assignments.get_syndrome
optionexpr = _syndromes_case_assignments.optionexpr
get_label = _syndromes_case_assignments.get_label
normalise_status = _syndromes_case_assignments.normalise
