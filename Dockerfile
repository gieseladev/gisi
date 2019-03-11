FROM python:slim

# Install Supervisord
RUN apt-get update && apt-get install -y --no-install-recommends supervisor && rm -rf /var/lib/apt/lists/*
COPY .docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Install Python requirements
RUN pip install pipenv
COPY ./Pipfile ./
COPY ./Pipfile.lock ./
RUN pipenv sync

VOLUME /gisi/logs
VOLUME /gisi/data

COPY gisi /gisi/gisi
COPY run.py /gisi/
COPY data /gisi/_data

COPY .docker/start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]