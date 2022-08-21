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
`PIPENV_DOTENV_LOCATION=path/to/.env`


### Local development
`pipenv run setup`
