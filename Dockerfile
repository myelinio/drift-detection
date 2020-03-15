FROM myelinio/pyspark:spark-2.4.1

WORKDIR /work

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip install -r  requirements.txt

ADD ./src/pyspark_pubsub_consumer.py /work
ADD ./src/pubsub.py /work
ADD ./log4j.properties /work
ADD ./job.properties /work

ENV PYTHONPATH=${PYTHONPATH}:/work

ADD lib/spark_pubsub-1.1-SNAPSHOT.jar ${SPARK_HOME}/jars

ENV DRIFT_DETECTOR_TYPE ADWIN
ENV GOOGLE_APPLICATION_CREDENTIALS /tmp/spark-sa.json
ENV CHECKPOINT_DIRECTORY /tmp/checkpoint
ENV PROJECT_ID myelin-development
ENV PUBSUB_SUBSCRIPTION projects/myelin-development/subscriptions/test

ADD ./spark-sa.json /tmp/spark-sa.json

WORKDIR /opt/spark/work-dir
