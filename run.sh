printenv | grep -v "no_proxy" >> /etc/environment
cron -L /var/log/cron.log
pipenv run python -m fsb
