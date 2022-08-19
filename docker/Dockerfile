FROM debian:11.3
RUN apt-get update \
    && apt-get install -yy python3 python3-pip python3-dev libxml2-dev libxslt1-dev antiword unrtf poppler-utils tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev swig libpulse-dev \
    && apt-get install -yy hledger hledger-web
RUN pip3 install requests textract
