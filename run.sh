printenv | grep -v "no_proxy" >> /etc/environment
cron -L /var/log/cron.log
pipenv run console migrator migrate -y
pipenv run python -m fsb
