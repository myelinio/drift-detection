
FROM openjdk:8-alpine

ARG spark_jars=jars
ARG img_path=kubernetes/dockerfiles

# Before building the docker image, first build and make a Spark distribution following
# the instructions in http://spark.apache.org/docs/latest/building-spark.html.
# If this docker file is being used in the context of building your images from a Spark
# distribution, the docker build command should be invoked from the top level directory
# of the Spark distribution. E.g.:
# docker build -t spark:latest -f kubernetes/dockerfiles/spark/Dockerfile .


#RUN apk add --update-cache --no-cache libgcc libquadmath musl \
#&& apk add --update-cache --no-cache libgfortran gfortran \
#&& apk add --update-cache --no-cache libpng-dev openblas-dev
#libgcc libquadmath musl libgfortran gfortran libpng-dev openblas-dev

RUN set -ex && \
    apk upgrade --no-cache && \
    apk add --no-cache bash tini libc6-compat linux-pam nss musl-dev linux-headers g++  && \
    mkdir -p /opt/spark && \
    mkdir -p /opt/spark/work-dir && \
    touch /opt/spark/RELEASE && \
    rm /bin/sh && \
    ln -sv /bin/bash /bin/sh && \
    echo "auth required pam_wheel.so use_uid" >> /etc/pam.d/su && \
    chgrp root /etc/passwd && chmod ug+rw /etc/passwd

COPY ${spark_jars} /opt/spark/jars
COPY ./bin /opt/spark/bin
COPY ./sbin /opt/spark/sbin
COPY ./entrypoint.sh /opt/
#COPY examples /opt/spark/examples
#COPY data /opt/spark/data

ENV SPARK_HOME /opt/spark

WORKDIR /
RUN mkdir ${SPARK_HOME}/python
# TODO: Investigate running both pip and pip3 via virtualenvs
RUN apk add --no-cache python3 python3-dev py3-numpy && \
    python3 -m ensurepip && \
    pip3 install --upgrade pip setuptools && \
    # We remove ensurepip since it adds no functionality since pip is
    # installed on the image and it just takes up 1.6MB on the image
    rm -r /usr/lib/python*/ensurepip && \
    pip install --upgrade pip setuptools  && \
    # You may install with python3 packages by using pip3.6
    # Removed the .cache to save space
    rm -r /root/.cache

#RUN apk add --no-cache python && \
#    apk add --no-cache python3 && \
#    python -m ensurepip && \
#    python3 -m ensurepip && \
#    # We remove ensurepip since it adds no functionality since pip is
#    # installed on the image and it just takes up 1.6MB on the image
#    rm -r /usr/lib/python*/ensurepip && \
#    pip install --upgrade pip setuptools && \
#    # You may install with python3 packages by using pip3.6
#    # Removed the .cache to save space
#    rm -r /root/.cache

COPY ./python/lib ${SPARK_HOME}/python/lib
ENV PYTHONPATH ${SPARK_HOME}/python/lib/pyspark.zip:${SPARK_HOME}/python/lib/py4j-*.zip

WORKDIR /opt/spark/work-dir
ENTRYPOINT [ "/opt/entrypoint.sh" ]
