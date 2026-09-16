FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
    python3.8 \
    python3-pip \
    mysql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    sqlalchemy \
    pymysql \
    pandas \
    requests \
    beautifulsoup4 \
    cryptography

WORKDIR /app

CMD ["bash"]