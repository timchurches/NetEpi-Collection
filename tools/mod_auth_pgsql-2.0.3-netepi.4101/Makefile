APACHE2_HOME=/usr
PGSQL_LIB=/usr/lib64/pgsql
PGSQL_INCLUDE=/usr/include/pgsql

shared:
	${APACHE2_HOME}/sbin/apxs  -i -a -c -I ${PGSQL_INCLUDE} -L ${PGSQL_LIB} -lpq mod_auth_pgsql.c

indent:
	indent -kr -ts4 mod_auth_pgsql.c

clean:
	rm -rf .libs/ *.la *.o *.lo *.slo *~	
