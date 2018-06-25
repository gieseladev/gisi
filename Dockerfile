FROM python:stretch

LABEL maintainer=Simon

# Install required packages
RUN apt-get -yqq update && \
    apt-get -yqq --no-install-recommends install curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Install Chrome WebDriver
RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    mkdir -p /opt/chromedriver-"$CHROMEDRIVER_VERSION" && \
    curl -sS -o /tmp/chromedriver_linux64.zip http://chromedriver.storage.googleapis.com/"$CHROMEDRIVER_VERSION"/chromedriver_linux64.zip && \
    unzip -qq /tmp/chromedriver_linux64.zip -d /opt/chromedriver-"$CHROMEDRIVER_VERSION" && \
    rm /tmp/chromedriver_linux64.zip && \
    chmod +x /opt/chromedriver-"$CHROMEDRIVER_VERSION"/chromedriver && \
    ln -fs /opt/chromedriver-"$CHROMEDRIVER_VERSION"/chromedriver /usr/local/bin/chromedriver

# Install Google Chrome
RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get -yqq update && \
    apt-get -yqq --no-install-recommends install google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Install Supervisord
RUN apt-get update && apt-get install -y --no-install-recommends supervisor && rm -rf /var/lib/apt/lists/*
COPY .docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Install Python requirements
COPY ./requirements.txt ./
RUN pip install -r requirements.txt

VOLUME /gisi/logs
VOLUME /gisi/data

COPY gisi /gisi/gisi
COPY run.py /gisi/
COPY data /gisi/data
RUN mkdir /gisi/logs

COPY .docker/start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]