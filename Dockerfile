FROM python:3.10.1
LABEL maintainer="licwimm@gmail.com"

ENV PIPENV_IGNORE_VIRTUALENV=1
ENV PIPENV_VENV_IN_PROJECT=1

WORKDIR /var/app

RUN apt update && apt install -y \
    vim \
    cron

COPY . .

RUN pip install pipenv \
    && pipenv install

# Setting up cron
ADD cron /etc/cron.d/cron
RUN touch /var/log/cron.log \
    && mkdir /var/log/cron \
    && chmod 644 /var/log/cron \
    && chmod 644 /etc/cron.d/cron
RUN crontab /etc/cron.d/cron

CMD cron -L /var/log/cron.log && pipenv run python -m fsb
