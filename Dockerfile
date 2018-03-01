FROM frolvlad/alpine-python3

RUN apk update && apk add \
    build-base \
    freetype-dev \
    fribidi-dev \
    harfbuzz-dev \
    jpeg-dev \
    lcms2-dev \
    libpng \
    openjpeg-dev \
    python3-dev \
    tcl-dev \
    tiff-dev \
    tk-dev \
    zlib-dev

WORKDIR /gisi
ADD . /gisi

RUN pip install -r requirements.txt

CMD ["python3", "run.py"]