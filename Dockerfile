FROM python:3.10.1
LABEL maintainer="licwimm@gmail.com"

ENV PIPENV_IGNORE_VIRTUALENV=1
ENV PIPENV_VENV_IN_PROJECT=1

WORKDIR /var/app

COPY . .

RUN pip install pipenv \
    && pipenv install

CMD ["pipenv", "run", "python", "-m", "fsb"]
