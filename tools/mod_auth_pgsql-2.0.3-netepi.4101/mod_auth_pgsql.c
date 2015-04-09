/* =====================================================================
 * Copyright (c) 1996 Vidya Media Ventures, Inc. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of this source code or a derived source code must
 *    retain the above copyright notice, this list of conditions and the
 *    following disclaimer. 
 *
 * 2. Redistributions of this module or a derived module in binary form
 *    must reproduce the above copyright notice, this list of conditions
 *    and the following disclaimer in the documentation and/or other
 *    materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY VIDYA MEDIA VENTURES, INC. ``AS IS'' AND 
 * ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL VIDYA MEDIA VENTURES, INC.
 * OR ITS EMPLOYEES BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 * ====================================================================
 *
 * This software is a contribution to and makes use of the Apache HTTP
 * server which is written, maintained and copywritten by the Apache Group.
 * See http://www.apache.org/ for more information.
 *
 * This software makes use of libpq which an interface to the PostgreSQL
 * database.  PostgreSQL is copyright (c) 1994 by the Regents of the
 * University of California.  As of this writing, more information on
 * PostgreSQL can be found at http://www.postgresSQL.org/
 *
 */

/*
 * 
 * PostgreSQL authentication
 *
 *
 * Needs libpq-fe.h and libpq.a
 *
 * Outline:
 *
 * - Authentication
 *   One database, and one (or two) tables.  One table holds the username and
 *   the encryped (or plain) password.  The other table holds the username and the names
 *   of the group to which the user belongs.  It is possible to have username,
 *   groupname and password in the same table.
 * - Access Logging
 *   Every authentication access is logged in the same database of the 
 *   authentication table, but in different table.
 *   User name and date of the request are logged.
 *   As option, it can log password, ip address, request line.
 *
 * Module Directives:  See html documentation
 * 
 * Changelog: See html documentation
 *
 * see http://www.postgreSQL.org/
 *
 *
 *
 *		Homepage	http://www.giuseppetanzilli.it/mod_auth_pgsql/
 *
 *		Latest sources  http://www.giuseppetanzilli.it/mod_auth_pgsql/dist/
 *
 *		Maintainer:
 *		Giuseppe Tanzilli
 *			info@giuseppetanzilli.it
 *			g.tanzilli@gruppocsf.com		
 *
 *		Original source: 
 * 		Adam Sussman (asussman@vidya.com) Feb, 1996
 *		Matthias Eckermann
 *		eckerman@lrz.uni-muenchen.de
 *
 */


#define 	AUTH_PGSQL_VERSION		"2.0.3"

#include "apr_hooks.h"
#include "apr.h"
#include "apr_lib.h"
#include "apr_strings.h"
#include "apr_buckets.h"
#include "apr_md5.h"
#include "apr_sha1.h"
#include "apr_network_io.h"
#include "apr_pools.h"
#include "apr_uri.h"
#include "apr_date.h"
#include "apr_fnmatch.h"
#define APR_WANT_STRFUNC
#include "apr_want.h"

#include "httpd.h"
#include "http_config.h"
#include "http_core.h"
#include "http_log.h"
#include "http_main.h"
#include "http_protocol.h"
#include "http_request.h"
#include "util_script.h"

#ifdef WIN32
#define crypt apr_password_validate
#else
#include <unistd.h>
#endif
#include "libpq-fe.h"

#if (MODULE_MAGIC_NUMBER_MAJOR < 20020628)
#error  Apache 2.0.40 required
#endif

/*
** uncomment the following line if you're having problem. The debug messages
** will be written to the server error log.
** WARNING: we log sensitive data, do not use on production systems
*/

/* #define DEBUG_AUTH_PGSQL 1 */



#ifndef MAX_STRING_LEN
#define MAX_STRING_LEN 8192
#endif

/* Cache table size */
#ifndef MAX_TABLE_LEN
#define MAX_TABLE_LEN 50
#endif

#define AUTH_PG_HASH_TYPE_CRYPT 	1
#define AUTH_PG_HASH_TYPE_MD5   	2
#define AUTH_PG_HASH_TYPE_BASE64	3
#define AUTH_PG_HASH_TYPE_NETEPI	4


typedef struct {
	const char *dir;
	const char *auth_pg_host;
	const char *auth_pg_database;
	const char *auth_pg_port;
	const char *auth_pg_options;
	const char *auth_pg_user;
	const char *auth_pg_pwd;
	const char *auth_pg_pwd_table;
	const char *auth_pg_uname_field;
	const char *auth_pg_pwd_field;
	const char *auth_pg_grp_table;
	const char *auth_pg_grp_group_field;
	const char *auth_pg_grp_user_field;
	const char *auth_pg_pwd_whereclause;
	const char *auth_pg_grp_whereclause;

	int auth_pg_nopasswd;
	int auth_pg_authoritative;
	int auth_pg_lowercaseuid;
	int auth_pg_uppercaseuid;
	int auth_pg_pwdignorecase;
	int auth_pg_encrypted;
	int auth_pg_hash_type;
	int auth_pg_cache_passwords;
	int auth_pg_netepi_old_passwords;

	const char *auth_pg_log_table;
	const char *auth_pg_log_addrs_field;
	const char *auth_pg_log_uname_field;
	const char *auth_pg_log_pwd_field;
	const char *auth_pg_log_date_field;
	const char *auth_pg_log_uri_field;

	apr_table_t *cache_pass_table;

} pg_auth_config_rec;

static apr_pool_t *auth_pgsql_pool = NULL;
static apr_pool_t *auth_pgsql_pool_base64 = NULL;

static char *netepi_pw_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";

module AP_MODULE_DECLARE_DATA auth_pgsql_module;


static int pg_log_auth_user(request_rec * r, pg_auth_config_rec * sec, 
		char *user, char *sent_pw);
static char *do_pg_query(request_rec * r, char *query, 
		pg_auth_config_rec * sec);

static void *create_pg_auth_dir_config(apr_pool_t * p, char *d)
{
	pg_auth_config_rec *new_rec;

#ifdef DEBUG_AUTH_PGSQL
	ap_log_perror(APLOG_MARK, APLOG_WARNING, 0, p,
				  "[mod_auth_pgsql.c] - going to configure directory \"%s\" ",
				  d);
#endif							/* DEBUG_AUTH_PGSQL */

	new_rec = apr_pcalloc(p, sizeof(pg_auth_config_rec));
	if (new_rec == NULL)
		return NULL;

	if (auth_pgsql_pool == NULL)
		apr_pool_create_ex(&auth_pgsql_pool, NULL, NULL, NULL);
	if (auth_pgsql_pool == NULL)
		return NULL;
	/* sane defaults */
	if (d != NULL)
		new_rec->dir = apr_pstrdup(p, d);
	else
		new_rec->dir = NULL;
	new_rec->auth_pg_host = NULL;
	new_rec->auth_pg_database = NULL;
	new_rec->auth_pg_port = NULL;
	new_rec->auth_pg_options = NULL;
	new_rec->auth_pg_user = NULL;
	new_rec->auth_pg_pwd = NULL;
	new_rec->auth_pg_pwd_table = NULL;
	new_rec->auth_pg_uname_field = NULL;
	new_rec->auth_pg_pwd_field = NULL;
	new_rec->auth_pg_grp_table = NULL;
	new_rec->auth_pg_grp_user_field = NULL;
	new_rec->auth_pg_grp_group_field = NULL;
	new_rec->auth_pg_pwd_whereclause = NULL;
	new_rec->auth_pg_grp_whereclause = NULL;

	new_rec->auth_pg_nopasswd = 0;
	new_rec->auth_pg_authoritative = 1;
	new_rec->auth_pg_lowercaseuid = 0;
	new_rec->auth_pg_uppercaseuid = 0;
	new_rec->auth_pg_pwdignorecase = 0;
	new_rec->auth_pg_encrypted = 1;
	new_rec->auth_pg_hash_type = AUTH_PG_HASH_TYPE_CRYPT;
	new_rec->auth_pg_cache_passwords = 0;
	new_rec->auth_pg_netepi_old_passwords = 0;

	new_rec->auth_pg_log_table = NULL;
	new_rec->auth_pg_log_addrs_field = NULL;
	new_rec->auth_pg_log_uname_field = NULL;
	new_rec->auth_pg_log_pwd_field = NULL;
	new_rec->auth_pg_log_date_field = NULL;
	new_rec->auth_pg_log_uri_field = NULL;

	/* make a per directory cache table */
	new_rec->cache_pass_table =
		apr_table_make(auth_pgsql_pool, MAX_TABLE_LEN);
	if (new_rec->cache_pass_table == NULL)
		return NULL;

#ifdef DEBUG_AUTH_PGSQL
	ap_log_perror(APLOG_MARK, APLOG_WARNING, 0, p,
				  "[mod_auth_pgsql.c] - configured directory \"%s\" ", d);
#endif							/* DEBUG_AUTH_PGSQL */

	return new_rec;
}


static const char *pg_set_hash_type(cmd_parms * cmd, void *mconfig,
			 const char *hash_type)
{
	pg_auth_config_rec *sec = mconfig;

	if (!strcasecmp(hash_type, "MD5"))
		sec->auth_pg_hash_type = AUTH_PG_HASH_TYPE_MD5;
	else if (!strcasecmp(hash_type, "CRYPT"))
		sec->auth_pg_hash_type = AUTH_PG_HASH_TYPE_CRYPT;
	else if (!strcasecmp(hash_type, "BASE64"))
		sec->auth_pg_hash_type = AUTH_PG_HASH_TYPE_BASE64;
	else if (!strcasecmp(hash_type, "NETEPI"))
		sec->auth_pg_hash_type = AUTH_PG_HASH_TYPE_NETEPI;
	else
		return apr_pstrcat(cmd->pool,
						   "Invalid hash type for Auth_PG_hash_type: ",
						   hash_type, NULL);
	return NULL;
}

static const char *pg_set_authoritative_flag(cmd_parms * cmd,
		  pg_auth_config_rec * sec, const int arg)
{
	sec->auth_pg_authoritative = arg;
	return NULL;
}

static const char *pg_set_lowercaseuid_flag(cmd_parms * cmd, void *sec,
											const int arg)
{
	((pg_auth_config_rec *) sec)->auth_pg_lowercaseuid = arg;
	((pg_auth_config_rec *) sec)->auth_pg_uppercaseuid = 0;
	return NULL;
}

static const char *pg_set_uppercaseuid_flag(cmd_parms * cmd, void *sec,
											int arg)
{
	((pg_auth_config_rec *) sec)->auth_pg_uppercaseuid = arg;
	((pg_auth_config_rec *) sec)->auth_pg_lowercaseuid = 0;
	return NULL;
}


static const command_rec pg_auth_cmds[] = {
	AP_INIT_TAKE1("Auth_PG_host", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec, auth_pg_host),
				  OR_AUTHCFG,
				  "the host name of the postgreSQL server."),
	AP_INIT_TAKE1("Auth_PG_database", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_database), OR_AUTHCFG,
				  "the name of the database that contains authorization information."),
	AP_INIT_TAKE1("Auth_PG_port", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec, auth_pg_port),
				  OR_AUTHCFG,
				  "the port the postmaster is running on."),
	AP_INIT_TAKE1("Auth_PG_options", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_options), OR_AUTHCFG,
				  "an options string to be sent to the postgres backed process."),
	AP_INIT_TAKE1("Auth_PG_user", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec, auth_pg_user),
				  OR_AUTHCFG,
				  "user name connect as"),
	AP_INIT_TAKE1("Auth_PG_pwd", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec, auth_pg_pwd),
				  OR_AUTHCFG,
				  "password to connect"),
	AP_INIT_TAKE1("Auth_PG_pwd_table", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_pwd_table), OR_AUTHCFG,
				  "the name of the table containing username/password tuples."),
	AP_INIT_TAKE1("Auth_PG_pwd_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_pwd_field), OR_AUTHCFG,
				  "the name of the password field."),
	AP_INIT_TAKE1("Auth_PG_uid_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_uname_field), OR_AUTHCFG,
				  "the name of the user-id field."),
	AP_INIT_TAKE1("Auth_PG_grp_table", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_grp_table), OR_AUTHCFG,
				  "the name of the table containing username/group tuples."),
	AP_INIT_TAKE1("Auth_PG_grp_group_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_grp_group_field),
				  OR_AUTHCFG,
				  "the name of the group-name field."),
	AP_INIT_TAKE1("Auth_PG_grp_user_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_grp_user_field),
				  OR_AUTHCFG,
				  "the name of the group-name field."),
	AP_INIT_FLAG("Auth_PG_nopasswd", ap_set_flag_slot,
				 (void *) APR_OFFSETOF(pg_auth_config_rec,
									   auth_pg_nopasswd),
				 OR_AUTHCFG,
				 "'on' or 'off'"),
	AP_INIT_FLAG("Auth_PG_encrypted", ap_set_flag_slot,
				 (void *) APR_OFFSETOF(pg_auth_config_rec,
									   auth_pg_encrypted),
				 OR_AUTHCFG,
				 "'on' or 'off'"),
	AP_INIT_TAKE1("Auth_PG_hash_type", pg_set_hash_type, NULL, OR_AUTHCFG,
				  "password hash type (CRYPT|MD5|BASE64|NETEPI)."),
	AP_INIT_FLAG("Auth_PG_netepi_old_passwords", ap_set_flag_slot,
				 (void *) APR_OFFSETOF(pg_auth_config_rec,
									   auth_pg_netepi_old_passwords),
				 OR_AUTHCFG,
				 "'on' or 'off'"),
	AP_INIT_FLAG("Auth_PG_cache_passwords", ap_set_flag_slot,
				 (void *) APR_OFFSETOF(pg_auth_config_rec,
									   auth_pg_cache_passwords),
				 OR_AUTHCFG,
				 "'on' or 'off'"),
	AP_INIT_FLAG("Auth_PG_authoritative", ap_set_flag_slot,
				 (void *) APR_OFFSETOF(pg_auth_config_rec,
									   auth_pg_authoritative), OR_AUTHCFG,
				 "'on' or 'off'"),
	AP_INIT_FLAG("Auth_PG_lowercase_uid", pg_set_lowercaseuid_flag, NULL,
				 OR_AUTHCFG,
				 "'on' or 'off'"),
	AP_INIT_FLAG("Auth_PG_uppercase_uid", pg_set_uppercaseuid_flag, NULL,
				 OR_AUTHCFG,
				 "'on' or 'off'"),
	AP_INIT_FLAG("Auth_PG_pwd_ignore_case", ap_set_flag_slot,
				 (void *) APR_OFFSETOF(pg_auth_config_rec,
									   auth_pg_pwdignorecase), OR_AUTHCFG,
				 "'on' or 'off'"),
	AP_INIT_TAKE1("Auth_PG_grp_whereclause", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_grp_whereclause),
				  OR_AUTHCFG,
				  "an SQL fragement that can be attached to the end of a where clause."),
	AP_INIT_TAKE1("Auth_PG_pwd_whereclause", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_pwd_whereclause),
				  OR_AUTHCFG,
				  "an SQL fragement that can be attached to the end of a where clause."),
	AP_INIT_TAKE1("Auth_PG_log_table", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_log_table),
				  OR_AUTHCFG,
				  "the name of the table containing log tuples."),
	AP_INIT_TAKE1("Auth_PG_log_addrs_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_log_addrs_field),
				  OR_AUTHCFG,
				  "the name of the field containing addrs in the log table (type char)."),
	AP_INIT_TAKE1("Auth_PG_log_uname_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_log_uname_field),
				  OR_AUTHCFG,
				  "the name of the field containing username in the log table (type char)."),
	AP_INIT_TAKE1("Auth_PG_log_pwd_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_log_pwd_field),
				  OR_AUTHCFG,
				  "the name of the field containing password in the log table (type char)."),
	AP_INIT_TAKE1("Auth_PG_log_date_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_log_date_field),
				  OR_AUTHCFG,
				  "the name of the field containing date in the log table (type char)."),
	AP_INIT_TAKE1("Auth_PG_log_uri_field", ap_set_string_slot,
				  (void *) APR_OFFSETOF(pg_auth_config_rec,
										auth_pg_log_uri_field),
				  OR_AUTHCFG,
				  "the name of the field containing uri (Object fetched) in the log table (type char)."),
	{NULL}
};


static char pg_errstr[MAX_STRING_LEN];
		 /* global errno to be able to handle config/sql 
		  * failures separately
		  */

static char *auth_pg_md5(char *pw)
{
	apr_md5_ctx_t ctx;
	unsigned char digest[APR_MD5_DIGESTSIZE];
	static unsigned char md5hash[APR_MD5_DIGESTSIZE * 2 + 1];
	int i;

	apr_md5(digest, (const unsigned char *) pw, strlen(pw));

	for (i = 0; i < APR_MD5_DIGESTSIZE; i++)
		apr_snprintf((char *) &md5hash[i + i], 3, "%02x", digest[i]);

	md5hash[APR_MD5_DIGESTSIZE * 2] = '\0';
	return (char *) md5hash;
}


static char *auth_pg_base64(char *pw)
{
	if (auth_pgsql_pool_base64 == NULL)
		apr_pool_create_ex(&auth_pgsql_pool_base64, NULL, NULL, NULL);
	if (auth_pgsql_pool == NULL)
		return NULL;

	return ap_pbase64encode(auth_pgsql_pool, pw);
}


/*
 * NetEpi password hashing scheme routines
 * Based on pwcheck.py in NetEpi CaseMgr
 */

static char* netepi_crypt(request_rec *r, char *password, char *encrypted_password_with_salt)
{
	/* We do this ourselves, because platform crypt() implementations vary too
	 * much, and we'd like our data to be portable.
	 *
	 * We need to extract the salt from the encrypted_password_with_salt string
	 * prefixed by $S$xxxxxxxx$.
	 * We know it starts with '$' at this point.
     */
	char *saltcopy;
	char *salt;
	char *saveptr;
	char *salted_password;
	char sha1hash[APR_SHA1PW_IDLEN + APR_SHA1_DIGESTSIZE + 1];
	char *final_hash;

	saltcopy = apr_pstrdup(r->pool, encrypted_password_with_salt);
	if (saltcopy == NULL)
		return NULL;
	salt = apr_strtok(saltcopy, "$", &saveptr);
	if (salt == NULL || strcmp(salt, "S"))
		return NULL;	/* Wrong hash method */
	salt = apr_strtok(NULL, "$", &saveptr);
	if (salt == NULL)
		return NULL;	/* No salt! */
	salted_password = apr_pstrcat(r->pool, salt, password, NULL);
	if (salted_password == NULL)
		return NULL;
	apr_sha1_base64(salted_password, strlen(salted_password), sha1hash);
	/* We want to skip over the "{SHA1}" in the hash and allow room for $S$...$...\0 */
	final_hash = apr_pstrcat(r->pool, "$S$", salt, "$", &sha1hash[APR_SHA1PW_IDLEN], NULL);
	return final_hash;
}

/*
 * Yes, this method is weaker than a normal MD5 hash
 */
static char *auth_pg_netepi(request_rec *r, char *pw, char letter1, char letter2)
{
	static char *extpw;

	extpw = apr_palloc(r->pool, 3 + strlen(pw));
	if (extpw == NULL)
		return NULL;
	extpw[0] = letter1;
	extpw[1] = letter2;
	strcpy(&extpw[2], pw);
	return auth_pg_md5(extpw);
}

char *netepi_flawed_pwd_check(request_rec *r, char *real_pw, char *sent_pw)
{
	char *l1, *l2;
	char *netepi_pw;

	for (l1 = netepi_pw_letters; *l1; l1++)
		for (l2 = netepi_pw_letters; *l2; l2++) {
			netepi_pw = auth_pg_netepi(r, sent_pw, *l1, *l2);
			if (netepi_pw && !strcasecmp(real_pw, netepi_pw))
				return netepi_pw;
		}
	return NULL;
}

char *netepi_pwd_check(pg_auth_config_rec *sec, request_rec *r, char *real_pw, char *sent_pw)
{
	char *netepi_pw;

	if (real_pw == NULL || sent_pw == NULL)
		return NULL;
	/* If there's no $ at the front of the password it's an old password */
	if (real_pw[0] != '$')
		return sec->auth_pg_netepi_old_passwords ? netepi_flawed_pwd_check(r, real_pw, sent_pw) : NULL;
	netepi_pw = netepi_crypt(r, sent_pw, real_pw);
	return strcmp(netepi_pw, real_pw) ? NULL : netepi_pw;
}


/* Got from POstgreSQL 7.2 */
/* ---------------
 * Escaping arbitrary strings to get valid SQL strings/identifiers.
 *
 * Replaces "\\" with "\\\\" and "'" with "''".
 * length is the length of the buffer pointed to by
 * from.  The buffer at to must be at least 2*length + 1 characters
 * long.  A terminating NUL character is written.
 * ---------------
 */

static size_t pg_check_string(char *to, const char *from, size_t length)
{
	const char *source = from;
	char *target = to;
	unsigned int remaining = length;

	while (remaining > 0) {
		switch (*source) {
		case '\\':
			*target = '\\';
			target++;
			*target = '\\';
			/* target and remaining are updated below. */
			break;

		case '\'':
			*target = '\'';
			target++;
			*target = '\'';
			/* target and remaining are updated below. */
			break;

		default:
			*target = *source;
			/* target and remaining are updated below. */
		}
		source++;
		target++;
		remaining--;
	}

	/* Write the terminating NUL character. */
	*target = '\0';

	return target - to;
}


/* Do a query and return the (0,0) value.  The query is assumed to be
 * a select.
 */
char *do_pg_query(request_rec * r, char *query, pg_auth_config_rec * sec)
{
	PGresult *pg_result;
	PGconn *pg_conn;
	char *val;
	char *result = NULL;

	pg_errstr[0] = '\0';

#ifdef DEBUG_AUTH_PGSQL
	ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r,
	  "[mod_auth_pgsql.c] - do_pg_query - going to connect database \"%s\" ",
	  sec->auth_pg_database);
#endif							/* DEBUG_AUTH_PGSQL */

	pg_conn = PQsetdbLogin(sec->auth_pg_host, sec->auth_pg_port,
		sec->auth_pg_options, NULL, sec->auth_pg_database,
		sec->auth_pg_user, sec->auth_pg_pwd);
	if (PQstatus(pg_conn) != CONNECTION_OK) {
		PQreset(pg_conn);
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "mod_auth_pgsql database connection error resetting %s",
					 PQerrorMessage(pg_conn));
		if (PQstatus(pg_conn) != CONNECTION_OK) {
			apr_snprintf(pg_errstr, MAX_STRING_LEN,
						 "mod_auth_pgsql database connection error reset failed %s",
						 PQerrorMessage(pg_conn));
			PQfinish(pg_conn);
			return NULL;
		}
	}
#ifdef DEBUG_AUTH_PGSQL
	ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r,
				  "[mod_auth_pgsql.c] - do_pg_query - going to execute query \"%s\" ",
				  query);
#endif							/* DEBUG_AUTH_PGSQL */

	pg_result = PQexec(pg_conn, query);

	if (pg_result == NULL) {
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "PGSQL 2: %s -- Query: %s ",
					 PQerrorMessage(pg_conn), query);
		PQfinish(pg_conn);
		return NULL;
	}

	if (PQresultStatus(pg_result) == PGRES_EMPTY_QUERY) {
		PQclear(pg_result);
		PQfinish(pg_conn);
		return NULL;
	}

	if (PQresultStatus(pg_result) != PGRES_TUPLES_OK) {
		apr_snprintf(pg_errstr, MAX_STRING_LEN, "PGSQL 3: %s -- Query: %s",
					 PQerrorMessage(pg_conn), query);
		PQclear(pg_result);
		PQfinish(pg_conn);
		return NULL;
	}

	if (PQntuples(pg_result) == 1) {
		val = PQgetvalue(pg_result, 0, 0);
		if (val == NULL) {
			apr_snprintf(pg_errstr, MAX_STRING_LEN, "PGSQL 4: %s",
						 PQerrorMessage(pg_conn));
			PQclear(pg_result);
			PQfinish(pg_conn);
			return NULL;
		}

		if (!(result = (char *) apr_pcalloc(r->pool, strlen(val) + 1))) {
			apr_snprintf(pg_errstr, MAX_STRING_LEN,
						 "Could not get memory for Postgres query.");
			PQclear(pg_result);
			PQfinish(pg_conn);
			return NULL;
		}

		strcpy(result, val);
	}

	/* ignore errors here ! */
	PQclear(pg_result);
	PQfinish(pg_conn);
	return result;
}

char *get_pg_pw(request_rec * r, char *user, pg_auth_config_rec * sec)
{
	char query[MAX_STRING_LEN];
	char *safe_user;
	int n;

	safe_user = apr_palloc(r->pool, 1 + 2 * strlen(user));
	pg_check_string(safe_user, user, strlen(user));

#ifdef DEBUG_AUTH_PGSQL
	ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r,
				  "[mod_auth_pgsql.c] - get_pg_pw - going to retrieve password for user \"%s\" from database",
				  user);
#endif							/* DEBUG_AUTH_PGSQL */

	if ((!sec->auth_pg_pwd_table) ||
		(!sec->auth_pg_pwd_field) || (!sec->auth_pg_uname_field)) {
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "PG: Missing parameters for password lookup: %s%s%s",
					 (sec->auth_pg_pwd_table ? "" : "Password table "),
					 (sec->
					  auth_pg_pwd_field ? "" : "Password field name "),
					 (sec->
					  auth_pg_uname_field ? "" : "UserID field name "));
		return NULL;
	};

	if (sec->auth_pg_lowercaseuid) {
		/* and force it to lowercase */
		n = 0;
		while (safe_user[n] && n < (MAX_STRING_LEN - 1)) {
			if (isupper(safe_user[n])) {
				safe_user[n] = tolower(safe_user[n]);
			}
			n++;
		}
	}

	if (sec->auth_pg_uppercaseuid) {
		/* and force it to uppercase */
		n = 0;
		while (safe_user[n] && n < (MAX_STRING_LEN - 1)) {
			if (islower(safe_user[n])) {
				safe_user[n] = toupper(safe_user[n]);
			}
			n++;
		}
	}

	n = apr_snprintf(query, MAX_STRING_LEN,
					 "select %s from %s where %s='%s' %s",
					 sec->auth_pg_pwd_field, sec->auth_pg_pwd_table,
					 sec->auth_pg_uname_field, safe_user,
					 sec->auth_pg_pwd_whereclause ? sec->
					 auth_pg_pwd_whereclause : "");

	if (n < 0 || n > MAX_STRING_LEN) {
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "PG: Detected SQL-truncation attack. Auth aborted.");
		return NULL;
	}
	return do_pg_query(r, query, sec);
}

static char *get_pg_grp(request_rec * r, char *group, char *user,
				 pg_auth_config_rec * sec)
{
	char query[MAX_STRING_LEN];
	char *safe_user;
	char *safe_group;
	int n;

	safe_user = apr_palloc(r->pool, 1 + 2 * strlen(user));
	safe_group = apr_palloc(r->pool, 1 + 2 * strlen(group));

#ifdef DEBUG_AUTH_PGSQL
	ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r,
				  "[mod_auth_pgsql.c] - get_pg_grp - going to retrieve group for user \"%s\" from database",
				  user);
#endif							/* DEBUG_AUTH_PGSQL */

	query[0] = '\0';
	pg_check_string(safe_user, user, strlen(user));
	pg_check_string(safe_group, group, strlen(group));

	if ((!sec->auth_pg_grp_table) ||
		(!sec->auth_pg_grp_group_field) || (!sec->auth_pg_grp_user_field))
	{
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "PG: Missing parameters for password lookup: %s%s%s",
					 (sec->auth_pg_grp_table ? "" : "Group table name"),
					 (sec->
					  auth_pg_grp_group_field ? "" :
					  "GroupID field name "),
					 (sec->
					  auth_pg_grp_user_field ? "" :
					  "Group table user field name "));
		return NULL;
	};

	if (sec->auth_pg_lowercaseuid) {
		/* and force it to lowercase */
		n = 0;
		while (safe_user[n] && n < (MAX_STRING_LEN - 1)) {
			if (isupper(safe_user[n])) {
				safe_user[n] = tolower(safe_user[n]);
			}
			n++;
		}
	}

	if (sec->auth_pg_uppercaseuid) {
		/* and force it to uppercase */
		n = 0;
		while (safe_user[n] && n < (MAX_STRING_LEN - 1)) {
			if (islower(safe_user[n])) {
				safe_user[n] = toupper(safe_user[n]);
			}
			n++;
		}
	}


	n = apr_snprintf(query, MAX_STRING_LEN,
					 "select %s from %s where %s='%s' and %s='%s' %s",
					 sec->auth_pg_grp_group_field, sec->auth_pg_grp_table,
					 sec->auth_pg_grp_user_field, safe_user,
					 sec->auth_pg_grp_group_field, safe_group,
					 sec->auth_pg_grp_whereclause ? sec->
					 auth_pg_grp_whereclause : "");

	if (n < 0 || n > MAX_STRING_LEN) {
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "PG: Detected SQL-truncation attack. Auth aborted.");
		return NULL;
	}

	return do_pg_query(r, query, sec);
}

/* Process authentication request from Apache*/
static int pg_authenticate_basic_user(request_rec * r)
{
	pg_auth_config_rec *sec =
		(pg_auth_config_rec *) ap_get_module_config(r->per_dir_config,
													&auth_pgsql_module);
	char *val = NULL;
	char *sent_pw, *real_pw;
	int res;
	char *user;

	if ((res = ap_get_basic_auth_pw(r, (const char **) &sent_pw)))
		return res;
	user = r->user;

#ifdef DEBUG_AUTH_PGSQL
	ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r,
				  "[mod_auth_pgsql.c] - pg_authenticate_basic_user - going to auth user \"%s\" pass \"%s\" uri \"%s\"",
				  user, sent_pw, r->unparsed_uri);
#endif							/* DEBUG_AUTH_PGSQL */

	/* if *password* checking is configured in any way, i.e. then
	 * handle it, if not decline and leave it to the next in line..  
	 * We do not check on dbase, group, userid or host name, as it is
	 * perfectly possible to only do group control and leave
	 * user control to the next guy in line.
	 */
	if ((!sec->auth_pg_pwd_table) && (!sec->auth_pg_pwd_field)) {
		ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r,
					  "[mod_auth_pgsql.c] - missing configuration parameters");
		return DECLINED;
	}
	pg_errstr[0] = '\0';

	if (sec->auth_pg_cache_passwords
		&& (!apr_is_empty_table(sec->cache_pass_table))) {
		val = (char *) apr_table_get(sec->cache_pass_table, user);

		if (val)
			real_pw = val;
		else
			real_pw = get_pg_pw(r, user, sec);
	} else
		real_pw = get_pg_pw(r, user, sec);

	if (!real_pw) {
		if (pg_errstr[0]) {
			res = HTTP_INTERNAL_SERVER_ERROR;
		} else {
			if (sec->auth_pg_authoritative) {
				/* force error and access denied */
				apr_snprintf(pg_errstr, MAX_STRING_LEN,
							 "mod_auth_pgsql: Password for user %s not found (PG-Authoritative)",
							 user);
				ap_note_basic_auth_failure(r);
				res = HTTP_UNAUTHORIZED;
			} else {
				/* allow fall through to another module */
				return DECLINED;
			}
		}
		ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
		return res;
	}

	/* allow no password, if the flag is set and the password
	 * is empty. But be sure to log this.
	 */
	if ((sec->auth_pg_nopasswd) && (!strlen(real_pw))) {
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "[mod_auth_pgsql.c] - Empty password accepted for user \"%s\"",
					 user);
		ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
		pg_log_auth_user(r, sec, user, sent_pw);
		return OK;
	};

	/* if the flag is off however, keep that kind of stuff at
	 * an arms length.
	 */
	if ((!strlen(real_pw)) || (!strlen(sent_pw))) {
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "[mod_auth_pgsql.c] - Empty password rejected for user \"%s\"",
					 user);
		ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
		ap_note_basic_auth_failure(r);
		return HTTP_UNAUTHORIZED;
	};

	if (sec->auth_pg_encrypted)
		switch (sec->auth_pg_hash_type) {
		case AUTH_PG_HASH_TYPE_MD5:
			sent_pw = auth_pg_md5(sent_pw);
			break;
		case AUTH_PG_HASH_TYPE_CRYPT:
			sent_pw = (char *) crypt(sent_pw, real_pw);
			break;
		case AUTH_PG_HASH_TYPE_BASE64:
			sent_pw = auth_pg_base64(sent_pw);
			break;
		}


	if (sec->auth_pg_hash_type == AUTH_PG_HASH_TYPE_NETEPI) {
		char *netepi_pw;

		if (netepi_pw = netepi_pwd_check(sec, r, real_pw, sent_pw))
			goto netepi_ok;
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "PG user %s: password mismatch", user);
		ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
		ap_note_basic_auth_failure(r);
		return HTTP_UNAUTHORIZED;
	netepi_ok:
		sent_pw = netepi_pw;

	} else if ((sec->auth_pg_hash_type == AUTH_PG_HASH_TYPE_MD5
		 || sec->auth_pg_hash_type == AUTH_PG_HASH_TYPE_BASE64
		 || sec->auth_pg_pwdignorecase)
		? strcasecmp(real_pw, sent_pw) : strcmp(real_pw, sent_pw)) {
		apr_snprintf(pg_errstr, MAX_STRING_LEN,
					 "PG user %s: password mismatch", user);
		ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
		ap_note_basic_auth_failure(r);
		return HTTP_UNAUTHORIZED;
	}

	/*  store password in the cache */
	if (sec->auth_pg_cache_passwords && !val && sec->cache_pass_table) {
		if ((apr_table_elts(sec->cache_pass_table))->nelts >=
			MAX_TABLE_LEN) {
			apr_table_clear(sec->cache_pass_table);
		}
		apr_table_set(sec->cache_pass_table, user, real_pw);
	}

	pg_log_auth_user(r, sec, user, sent_pw);
	return OK;
}

/* Checking ID */

static int pg_check_auth(request_rec * r)
{
	pg_auth_config_rec *sec =
		(pg_auth_config_rec *) ap_get_module_config(r->per_dir_config,
													&auth_pgsql_module);
	char *user = r->user;
	int m = r->method_number;
	int group_result = DECLINED;



	apr_array_header_t *reqs_arr = (apr_array_header_t *) ap_requires(r);
	require_line *reqs = reqs_arr ? (require_line *) reqs_arr->elts : NULL;

	register int x, res;
	const char *t;
	char *w;

	pg_errstr[0] = '\0';

#ifdef DEBUG_AUTH_PGSQL
	ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r,
				  "[mod_auth_pgsql.c] - pg_check_auth - going to check auth for user \"%s\" ",
				  user);
#endif							/* DEBUG_AUTH_PGSQL */



	/* if we cannot do it; leave it to some other guy 
	 */
	if ((!sec->auth_pg_grp_table) && (!sec->auth_pg_grp_group_field)
		&& (!sec->auth_pg_grp_user_field))
		return DECLINED;

	if (!reqs_arr) {
		if (sec->auth_pg_authoritative) {
			/* force error and access denied */
			apr_snprintf(pg_errstr, MAX_STRING_LEN,
						 "mod_auth_pgsql: user %s denied, no access rules specified (PG-Authoritative)",
						 user);
			ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
			ap_note_basic_auth_failure(r);
			res = HTTP_UNAUTHORIZED;
		} else {
			return DECLINED;
		}
	}

	for (x = 0; x < reqs_arr->nelts; x++) {

		if (!(reqs[x].method_mask & (1 << m)))
			continue;

		t = reqs[x].requirement;
		w = ap_getword(r->pool, &t, ' ');

		if (!strcmp(w, "valid-user"))
			return OK;

		if (!strcmp(w, "user")) {
			while (t[0]) {
				w = ap_getword_conf(r->pool, &t);
				if (!strcmp(user, w))
					return OK;
			}
			if (sec->auth_pg_authoritative) {
				/* force error and access denied */
				apr_snprintf(pg_errstr, MAX_STRING_LEN,
							 "mod_auth_pgsql: user %s denied, no access rules specified (PG-Authoritative)",
							 user);
				ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
				ap_note_basic_auth_failure(r);
				return HTTP_UNAUTHORIZED;
			}

		} else if (!strcmp(w, "group")) {
			/* look up the membership for each of the groups in the table */
			pg_errstr[0] = '\0';

			while (t[0]) {
				if (get_pg_grp(r, ap_getword(r->pool, &t, ' '), user, sec)) {
					group_result = OK;
				};
			};

			if (pg_errstr[0]) {
				ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
				return HTTP_INTERNAL_SERVER_ERROR;
			}

			if (group_result == OK)
				return OK;

			if (sec->auth_pg_authoritative) {
				apr_snprintf(pg_errstr, MAX_STRING_LEN,
							 "[mod_auth_pgsql.c] - user %s not in right groups (PG-Authoritative)",
							 user);
				ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "[mod_auth_pgsql.c] - ERROR - %s", pg_errstr);
				ap_note_basic_auth_failure(r);
				return HTTP_UNAUTHORIZED;
			};
		}
	}

	return DECLINED;
}


/* Send the authentication to the log table */
int
pg_log_auth_user(request_rec * r, pg_auth_config_rec * sec, char *user,
				 char *sent_pw)
{
	char sql[MAX_STRING_LEN];
	char *s;
	int n;
	char fields[MAX_STRING_LEN];
	char values[MAX_STRING_LEN];
	char *safe_user;
	char *safe_pw;
	char *safe_req;
	char ts[MAX_STRING_LEN];	/* time in string format */
	apr_time_exp_t t;			/* time of request start */
	apr_size_t retsize;

	safe_user = apr_palloc(r->pool, 1 + 2 * strlen(user));
	safe_pw = apr_palloc(r->pool, 1 + 2 * strlen(sent_pw));
	safe_req = apr_palloc(r->pool, 1 + 2 * strlen(r->the_request));

	/* we do not want to process internal redirect  */
	if (!ap_is_initial_req(r))
		return DECLINED;
	if ((!sec->auth_pg_log_table) || (!sec->auth_pg_log_uname_field) || (!sec->auth_pg_log_date_field)) {	// At least table name, username and date field are specified
		// send error message and exit 
		return DECLINED;
	}

	/* AUD: MAX_STRING_LEN probably isn't always correct */
	pg_check_string(safe_user, user, strlen(user));
	pg_check_string(safe_pw, sent_pw, strlen(sent_pw));
	pg_check_string(safe_req, r->the_request, strlen(r->the_request));


	if (sec->auth_pg_lowercaseuid) {
		/* and force it to lowercase */
		n = 0;
		while (safe_user[n] && n < (MAX_STRING_LEN - 1)) {
			if (isupper(safe_user[n])) {
				safe_user[n] = tolower(safe_user[n]);
			}
			n++;
		}
	}

	if (sec->auth_pg_uppercaseuid) {
		/* and force it to uppercase */
		n = 0;
		while (safe_user[n] && n < (MAX_STRING_LEN - 1)) {
			if (islower(safe_user[n])) {
				safe_user[n] = toupper(safe_user[n]);
			}
			n++;
		}
	}


	/* time field format  */
	apr_time_exp_lt(&t, r->request_time);
	apr_strftime(ts, &retsize, 100, "%Y-%m-%d %H:%M:%S", &t);



	/* SQL Statement, required fields: Username, Date */
	apr_snprintf(fields, MAX_STRING_LEN, "%s,%s",
				 sec->auth_pg_log_uname_field,
				 sec->auth_pg_log_date_field);
	apr_snprintf(values, MAX_STRING_LEN, "'%s','%s'", safe_user, ts);

	/* Optional parameters */
	if (sec->auth_pg_log_addrs_field) {	/* IP Address field */
		apr_snprintf(sql, MAX_STRING_LEN, ", %s",
					 sec->auth_pg_log_addrs_field);
		strncat(fields, sql, MAX_STRING_LEN - strlen(fields) - 1);
		apr_snprintf(sql, MAX_STRING_LEN, ", '%s'",
					 r->connection->remote_ip);
		strncat(values, sql, MAX_STRING_LEN - strlen(values) - 1);
	}
	if (sec->auth_pg_log_pwd_field) {	/* Password field , clear WARNING */
		apr_snprintf(sql, MAX_STRING_LEN, ", %s",
					 sec->auth_pg_log_pwd_field);
		strncat(fields, sql, MAX_STRING_LEN - strlen(fields) - 1);
		apr_snprintf(sql, MAX_STRING_LEN, ", '%s'", safe_pw);
		strncat(values, sql, MAX_STRING_LEN - strlen(values) - 1);
	}
	if (sec->auth_pg_log_uri_field) {	/* request string */
		apr_snprintf(sql, MAX_STRING_LEN, ", %s",
					 sec->auth_pg_log_uri_field);
		strncat(fields, sql, MAX_STRING_LEN - strlen(fields) - 1);
		apr_snprintf(sql, MAX_STRING_LEN, ", '%s'", safe_req);
		strncat(values, sql, MAX_STRING_LEN - strlen(values) - 1);
	}

	apr_snprintf(sql, MAX_STRING_LEN, "insert into %s (%s) values(%s) ; ",
				 sec->auth_pg_log_table, fields, values);

	s = do_pg_query(r, sql, sec);
	return (0);
}

static int
pg_auth_init_handler(apr_pool_t * p, apr_pool_t * plog, apr_pool_t * ptemp,
					 server_rec * s)
{
#ifdef DEBUG_AUTH_PGSQL
	ap_log_perror(APLOG_MARK, APLOG_WARNING, 0, p,
				  "[mod_auth_pgsql.c] - pg_auth_init_handler -  ");
#endif							/* DEBUG_AUTH_PGSQL */

	ap_add_version_component(p, "mod_auth_pgsql/" AUTH_PGSQL_VERSION);
	return OK;
}

/* Init the module private memory pool, used for the per directory cache tables */
static void *pg_auth_server_config(apr_pool_t * p, server_rec * s)
{
#ifdef DEBUG_AUTH_PGSQL
	ap_log_perror(APLOG_MARK, APLOG_WARNING, 0, p,
				  "[mod_auth_pgsql.c] - pg_auth_server_config -  ");
#endif							/* DEBUG_AUTH_PGSQL */

	if (auth_pgsql_pool == NULL)
		apr_pool_create_ex(&auth_pgsql_pool, NULL, NULL, NULL);

	return OK;
}


static void register_hooks(apr_pool_t * p)
{
	ap_hook_post_config(pg_auth_init_handler, NULL, NULL, APR_HOOK_MIDDLE);
	ap_hook_auth_checker(pg_check_auth, NULL, NULL, APR_HOOK_MIDDLE);
	ap_hook_check_user_id(pg_authenticate_basic_user, NULL, NULL,
						  APR_HOOK_MIDDLE);
};

module AP_MODULE_DECLARE_DATA auth_pgsql_module = {
	STANDARD20_MODULE_STUFF,
	create_pg_auth_dir_config,	/* dir config creater */
	NULL,						/* dir merger --- default is to override */
	pg_auth_server_config,		/* server config */
	NULL,						/* merge server config */
	pg_auth_cmds,				/* command table */
	register_hooks				/* Apache2 register hooks */
};
