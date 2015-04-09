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

.PHONY: all
all: Collection-ER.pdf Collection-ER.png

# old dia: --export-to-format=eps-builtin
#
# Sigh, dia borked again
#	dia --nosplash --filter=pdf \
#		--export=$(subst .dia,.pdf,$<) $<
%.pdf: %.dia
	dia --nosplash --filter=svg \
		--export=$(subst .dia,.svg,$<) $<
	inkscape --without-gui --export-area-snap \
		--export-pdf=$(subst .dia,.pdf,$<) \
		$(subst .dia,.svg,$<)

# old dia: --export-to-format=png
%.png: %.dia
	dia --nosplash --filter=png --size 1600 \
		--export=$(subst .dia,.png,$<) $<
