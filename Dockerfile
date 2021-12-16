FROM python:3.10.1
LABEL maintainer="licwimm@gmail.com"

WORKDIR /var/app

COPY . .

RUN pip install pipenv \
    && pipenv install

CMD ["pipenv", "run", "python", "-m", "fsb"]
