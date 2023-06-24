#!/usr/bin/env bash

dc='docker-compose -f docker-compose.local.yml'

mysql_query () {
  query=$1
  echo $query

  if [ -z $2 ]
  then
    password=$MYSQL_ROOT_PASSWORD
  else
    password=$2
  fi

  echo $password

  $dc exec fsb-db mysql -A --password="$password" --connect-expired-password -u root -e "$query"
}

$dc build --no-cache
$dc up -d fsb-db

root_password=''
new_root_password=$MYSQL_ROOT_PASSWORD
while [ -z $root_password ]
do
  root_password=$($dc logs 2>&1 | grep GENERATED | awk '{print $(NF)}')
  echo -n .
  sleep 1
done
echo ''
echo "Generated Password: $root_password"
sleep 2

mysql_query "ALTER USER 'root'@'localhost' IDENTIFIED BY '$new_root_password';" $root_password
mysql_query "CREATE USER 'root'@'%' IDENTIFIED BY '$new_root_password';"
mysql_query "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';"
mysql_query "GRANT GRANT OPTION ON *.* TO 'root'@'%';"
mysql_query "CREATE DATABASE feature_storage;"
mysql_query "DROP USER 'root'@'localhost';"

$dc exec fsb-app pipenv run migrator migrate -y

$dc down fsb-db
