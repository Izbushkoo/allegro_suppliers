FROM python:3.10-buster
LABEL authors="Izbushko"

RUN pip install poetry==1.6.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

COPY . .

RUN poetry install --without dev

EXPOSE 8787

CMD poetry run gunicorn --config gunicorn_conf.py --timeout 500 --bind :8787 -k uvicorn.workers.UvicornH11Worker --workers 4 \
app.main:app