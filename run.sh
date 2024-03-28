#!/bin/sh
printenv | grep -v "no_proxy" >> /etc/environment

if [ "$FOOL_DAY" = "True" ]; then
  crontab /etc/cron.d/fool.cron
else
  crontab /etc/cron.d/cron
fi

cron -L /var/log/cron.log
pipenv run console migrator migrate -y
pipenv run python -m fsb
