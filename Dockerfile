FROM python:3.10.11
LABEL maintainer="licwimm@gmail.com"

ENV PIPENV_IGNORE_VIRTUALENV=1
ENV PIPENV_VENV_IN_PROJECT=1

WORKDIR /var/app

RUN apt update && apt install -y \
    vim \
    cron

COPY . .
RUN chmod -R 660 .

RUN pip install pipenv \
    && pipenv install

# Setting up cron
ADD cron /etc/cron.d/cron
ADD fool.cron /etc/cron.d/fool.cron
RUN touch /var/log/cron.log \
    && mkdir /var/log/cron \
    && chmod 644 /var/log/cron \
    && chmod 644 /etc/cron.d/cron
RUN mkdir /var/log/app \
    && chmod 644 -R /var/log/app

RUN chmod 777 /var/app/run.sh
CMD /var/app/run.sh
