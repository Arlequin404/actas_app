#!/bin/bash
echo "🔐 Reemplazando método de autenticación 'trust' por 'md5' en pg_hba.conf..."
sed -i 's/host all all all trust/host all all all md5/' "$PGDATA/pg_hba.conf"
