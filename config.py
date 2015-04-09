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

# ==============================================================================
# Branding
apptitle = 'NetEpi Collection'
subbanner = 'Network-enabled tools for epidemiology and public health practice.'
syndrome_label = 'Case Definition'
unit_label = 'Role'
group_label = 'Context'
contact_label = 'Association'
person_label = 'Person'
helpdesk_contact = 'the NetEpi Helpdesk'
login_helpdesk_contact = helpdesk_contact

# ==============================================================================
# Instance selection (Virtualisation)
appname = 'collection'
# Defaults to '::{appname}:'
#dsn = '::collection:'
session_server = 'localhost:34343'
session_timeout = 3600
# Defaults to OFF
#registration_notify = 'nobody@example.com'
#exception_notify = 'nobody@example.com'

# ==============================================================================
# Application behavior

# Suggest using priority, name, syndrome_id or post_date. Append ' DESC' to
# reverse order of an item, for example: 'post_date DESC, priority'
order_syndromes_by = 'priority, name'

# Duplicate-person search done within syndrome or across all syndromes?
dup_per_syndrome = False

# Attempt to roll-forward form data when the form is upgraded (False has not
# been tested in some time and is no longer recommended).
form_rollforward = True

# Immediately create cases and contacts from search results, rather than 
# requiring an explicit "create" from the case/contact screen.
immediate_create = True

# If True, show all syndromes on main page, not just those the user has
# access to.
show_all_syndromes = False

# Exploit <iframe> side-effects to intercept browser <back> button use
nobble_back_button = True

# Date parsing and formatting. Choose one of DMY, MDY or ISO
date_style = 'DMY'

# Cache form summaries - If True, form summaries are only generated when a form
# is updated. If False, they are generated on demand (which requires loading
# the form definition and form instances for each summary generated). The main
# drawback of caching summaries is dates are formatted according to the editing
# user style preferences, rather than the viewing user's style preference
# (which can be particularly confusing when one uses date style DMY and the
# other uses MDY).
cache_form_summaries = False

# If matplotlib is available, this option can be set to True, and additional
# graphing functions will become available.
enable_matplotlib = False

# When many demographic fields are enabled, the screen can become quite
# cluttered. If the count of enabled fields exceeds the threshold given here,
# the application switches to a tabbed rendering of the demographic fields,
# where fields are grouped together by function, and the groups then rendered
# inside tabs. To disable the tabbed rendering, set to 999.
tabbed_demogfields_threshold = 20

# If non-zero, after servicing this many requests, we exit gracefully to
# minimise the impact of memory fragmentation and object leaks (only relevant
# for persistent application servers).
max_requests = 1000

# ==============================================================================
# User controls

# If True, allow users to view details of other users of the system (subject to
# that user's privacy settings).
user_browser = True

# User details check interval in days - if the user has not updated their
# details in this time, remind them to review them. Set it to 0 to disable 
# the details check.
user_check_interval = 30

# New user registration mode. Choices are:
#
# none          Users can only be added by admins.
#
# register      A button on the login page invites the user to register their
#               details. After registering, their details are reviewed by an
#               admin prior to their account being enabled.
#
# invite        An existing user invites a prospective user onto the system 
#               via a one-time URL that takes the prospective user to a
#               registration screen.  After registering, their details are
#               reviewed by an admin prior to their account being enabled.
#
# sponsor       An existing user sponsors a prospective user onto the system
#               via a one-time URL that takes the prospective user to a
#               registration screen. After registering, the sponsoring user
#               verifies the identity of the new user and then enables their
#               access.
# 
user_registration_mode = 'register'

# ==============================================================================
# Change Notification Daemon
#
# The optional notification daemon makes certain data changes propagate between
# application server instances faster. Application processes send the
# notification daemon messages to announce that a certain object has changed,
# and all interested clients then receive a copy of this notification, and
# should discard any cached copies of the referenced object.
#
# Each NetEpi Collection instance should have it's own notification daemon.

# Which server the notification daemon runs on:
#
#   If set to "none", no notification daemon will be started and time-based
#   cache expiry is used. 
#
#   If set to "local", a daemon local to this instance will be automatically
#   started if one is not already running, with communications occuring over
#   unix domain sockets.
#
#   If set to a hostname or ip address, application processes will attempt to
#   connect to that address and no local daemon will be started (use the
#   stand-alone daemon on the server host).
notification_host = 'local'

# If connecting to a non-local notification daemon, this is the port to use:
notification_port = 13535

# ==============================================================================
# Developer/Debugging
debug = False
tracedb = False
install_verbose = False
install_debug = False
create_db = True
compile_py = True
exec_timing = False
