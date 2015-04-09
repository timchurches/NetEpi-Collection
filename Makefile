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

PYTHON = python

COLLECTION_CONFIG = appname=collection dsn='::collection:'

.PHONY: all test liccheck sdist

all: 
	$(PYTHON) install.py $(COLLECTION_CONFIG)

test:
	(cd tests && $(PYTHON) all.py)

liccheck:
	@$(PYTHON) liccheck.py \
		&& echo "All license banners okay" ; exit 0 \
		|| echo "*** License banners in the above file(s) need updating" ; exit 1

sdist:	liccheck
	$(PYTHON) sdist.py
