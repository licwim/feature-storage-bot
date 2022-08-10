# Feature Storage Bot

Bot-Storage of all sorts features, tools and utilities

### Admin files
##### config.json
```json
{
    "bot_username": "FeatureStorageBot",
    "bot_token": "*****",
    "api_id": 123,
    "api_hash": "*****",
    "contributors": [
        "nickname"
    ],
    "developer": "nickname",
    "dev_chats": [
        123
    ]
}
```

##### .env
```text
FSB_CONFIG_FILE=path/to/config.json
FSB_DEV_MODE=1

DB_HOST=fsb-db
DB_NAME=feature_storage
DB_USER=root
DB_PASSWORD=111111
```

Add a variable to your local environment:
`PIPENV_DOTENV_LOCATION=path/to/dir/with/.env`


### Local development
1. `shell> docker-compose up -d`
2. `shell> docker-compose logs 2>&1 | grep GENERATED`
3. `shell> docker exec -it feature-storage-bot_fsb-db_1 mysql -A -p`
4. `mysql> ALTER USER 'root'@'localhost' IDENTIFIED BY 'password';`
5. `mysql> CREATE USER 'root'@'%' IDENTIFIED BY '111111';`
6. `mysql> GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';`
7. `mysql> GRANT GRANT OPTION ON *.* TO 'root'@'%';`
8. `mysql> CREATE DATABASE feature_storage;`
9. `mysql> DROP USER 'root'@'localhost';`
10. `shell> docker-compose down`
11. `shell> docker-compose up -d`
