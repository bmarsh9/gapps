#!/usr/bin/env bash

# Set up MariaDB/MySQL database, user and password
## setup_db.sh db1
#
# Delete
## setup_db.sh -d db1

while getopts ":d:l:" OPT; do
    case $OPT in
        d)
            mysql -u root -e "DROP DATABASE IF EXISTS $OPTARG;"
            mysql -u root -e "DROP USER IF EXISTS '$OPTARG'@'%';"
            echo "MariaDB user and database dropped."
            exit
            ;;
        l)
            mysql -u root -e "SHOW DATABASES;"
            exit
            ;;
    esac
done

if [ -z "$1" ]; then
  echo "no database specified. aborting."
  exit
fi

mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS \`$1\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$1'@'%' IDENTIFIED BY '$1';
GRANT ALL PRIVILEGES ON \`$1\`.* TO '$1'@'%';
FLUSH PRIVILEGES;
EOF
echo "MariaDB user and database '$1' created."
