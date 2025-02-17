#!/usr/bin/env bash

dc='docker-compose -f docker-compose.local.yml'

mysql_query () {
  query=$1
  password=$MYSQL_ROOT_PASSWORD
  echo $query

  $dc exec fsb-db mysql -A --password="$password" --connect-expired-password -u root -e "$query"
}

$dc build --no-cache
$dc up -d fsb-db

root_password=$MYSQL_ROOT_PASSWORD
grep_count=0

while [ $grep_count -eq 0 ]
do
  grep_count=$($dc logs 2>&1 | grep -c 'ready for connections')
  echo -n .
  sleep 1
done

echo ''
echo "Root Password: $root_password"
sleep 2

mysql_query "ALTER USER 'root'@'%' IDENTIFIED BY '$root_password';"
mysql_query "CREATE DATABASE feature_storage;"
mysql_query "DROP USER 'root'@'localhost';"

pipenv run cli migrator migrate -y

$dc down
