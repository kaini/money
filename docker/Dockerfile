FROM debian:11.3
RUN apt-get update \
    && apt-get install -yy python3 python3-pip python3-dev libxml2-dev libxslt1-dev antiword unrtf poppler-utils tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev swig libpulse-dev

RUN cd /usr/local/bin \
    && apt-get update && apt-get install -yy curl unzip \
    && curl -LOC- https://github.com/simonmichael/hledger/releases/download/1.26.1/hledger-linux-x64.zip \
    && echo 'd6c445f6e24dfb476292b812338ff6db362ddae6ecd82c2724be1e833f2becba hledger-linux-x64.zip' | sha256sum -c \
    && unzip hledger-linux-x64.zip \
    && mv hledger-linux-x64 hledger && mv hledger-ui-linux-x64 hledger-ui && mv hledger-web-linux-x64 hledger-web \
    && chmod +x hledger hledger-ui hledger-web

RUN pip3 install requests textract urwid thefuzz
