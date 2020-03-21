FROM myelinio/pyspark:spark-2.4.1

WORKDIR /work

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip install -r  requirements.txt


ENV PYTHONPATH=${PYTHONPATH}:/work

ADD lib/spark_pubsub-1.1-SNAPSHOT.jar ${SPARK_HOME}/jars
RUN rm ${SPARK_HOME}/jars/kubernetes-client-4.1.2.jar
ADD lib/kubernetes-client-4.4.2.jar ${SPARK_HOME}/jars


ENV GOOGLE_APPLICATION_CREDENTIALS /src/drift-detection/secrets/spark-sa.json
ENV PROJECT_ID myelin-development

ADD ./src/pyspark_pubsub_consumer.py /work
ADD ./src/pubsub.py /work
#ADD ./log4j.properties /work
#ADD ./job.properties /work

ADD ./log4j.properties ${SPARK_HOME}/conf/log4j.properties

WORKDIR /opt/spark/work-dir
