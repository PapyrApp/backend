FROM python:3.11

WORKDIR /app

ADD . /app

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/src

CMD ["gunicorn", "-k", "gevent", "-w", "1", "-b", "0.0.0.0:8000", "src.wsgi:app"]
