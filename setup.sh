#!/usr/bin/env bash

mysql_query () {
  query=$1
  echo $query

  if [ -z $2 ]
  then
    password='111111'
  else
    password=$2
  fi

  echo $password

  docker exec -it feature-storage-bot_fsb-db_1 mysql -A --password="$password" --connect-expired-password -u root -e "$query"
}

docker-compose build --no-cache
docker-compose up -d

root_password=''
new_root_password='111111'
while [ -z $root_password ]
do
  root_password=$(docker-compose logs 2>&1 | grep GENERATED | awk '{print $(NF)}')
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

docker exec -it feature-storage-bot_fsb-app_1 pipenv run migrator migrate -y

docker-compose down
