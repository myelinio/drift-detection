import logging
import shutil
import pickle
import time

from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext

import pubsub

import os

from skmultiflow_detector import build_drift_detector
from utils import get_metric, get_data_dim, parse_request
import numpy as np
import cloudpickle
import requests
from google.cloud import bigquery

"""


export clusterName=tt-cluster-sha456
export PROJECT_ID=myelin-development

# Cleanup
gcloud logging sinks delete ${clusterName}-logs-sink
gcloud pubsub subscriptions delete ${clusterName}-logs-subscription
gcloud pubsub topics delete ${clusterName}-logs-topic


export log_filter="resource.type="k8s_container" AND resource.labels.cluster_name="${clusterName}" AND severity>=WARNING AND ("MyelinLoggingFilterOnRequest" OR "MyelinLoggingFilterOnResponse")"


gcloud pubsub topics create ${clusterName}-logs-topic
gcloud pubsub subscriptions create ${clusterName}-logs-subscription --topic=${clusterName}-logs-topic --expiration-period=24h \
--message-retention-duration=1h --project=${PROJECT_ID}

gcloud logging sinks create ${clusterName}-logs-sink pubsub.googleapis.com/projects/${PROJECT_ID}/topics/${clusterName}-logs-topic --log-filter="${log_filter}" --project=${PROJECT_ID}


logging_sa=$(gcloud logging sinks  describe ${clusterName}-logs-sink  --project=${PROJECT_ID} | awk 'BEGIN {FS="writerIdentity: " } ; { print $2 }')
echo ${logging_sa}

gcloud beta pubsub topics add-iam-policy-binding ${clusterName}-logs-topic \
--member ${logging_sa} \
--role roles/pubsub.publisher




kubectl create secret generic spark-sa --from-file=spark-sa.json


dataset_name=${PROJECT_ID}:$(echo ${clusterName} | sed s/-/_/g)_drift_detection
bq --location=europe-west2 mk \
--dataset \
--default_table_expiration 36000 \
${dataset_name}


bq mk \
-t \
--expiration 360000 \
--label organization:development \
${dataset_name}.state \
model_id:STRING,axon:STRING,drift_probability:FLOAT,timestamp:TIMESTAMP


### review
gcloud iam service-accounts get-iam-policy \
${logging_sa}  --format json

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member ${logging_sa} \
  --role roles/editor


select * from `tt_cluster_sha456_drift_detection.state` order by timestamp desc

-- delete from `tt_cluster_sha456_drift_detection.state` where axon="ml-test-hp"
-- AND `timestamp` < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)

-- select count(*) from `tt_cluster_sha456_drift_detection.state`

logging_sa_s3=$(gcloud logging sinks  describe ${clusterName}-logs-sink-s3  --project=${PROJECT_ID} | awk 'BEGIN {FS="writerIdentity: " } ; { print $2 }')
echo ${logging_sa_s3}

gsutil iam ch ${logging_sa_s3}:objectAdmin gs://${clusterName}-logs-sink


"""

if "LOCAL" in os.environ:
    os.environ[
        'GOOGLE_APPLICATION_CREDENTIALS'] = "/Users/ryadhkhisb/Dev/workspaces/m/myelin-examples/drift-detection/spark-sa.json"
    os.environ['PROJECT_ID'] = "myelin-development"
    os.environ['DRIFT_DETECTOR_TYPE'] = "ADWIN"
    os.environ['PUBSUB_SUBSCRIPTION'] = "projects/myelin-development/subscriptions/tt-cluster-sha456-logs-subscription"
    os.environ['CHECKPOINT_DIRECTORY'] = "/tmp/checkpoint"
    os.environ['MYELIN_NAMESPACE'] = "myelin-app"
    os.environ['PUSHGATEWAY_URL'] = "myelin-uat-prometheus-pushgateway"
    os.environ['PUSHGATEWAY_PORT'] = "9091"
    os.environ['BATCH_DURATION'] = "5"
    os.environ['WINDOW_DURATION'] = "5"
    os.environ['BATCH_SIZE'] = "100"
    os.environ['STATE_TOPIC'] = "projects/myelin-development/topics/tt-cluster-sha456-state-topic"
    os.environ['STATE_TABLE'] = "myelin-development.tt_cluster_sha456_drift_detection.state"
    os.environ['DEBUG_TOPIC'] = "projects/myelin-development/topics/tt-cluster-sha456-logs-topic-debug"
    jar_path = "/Users/ryadhkhisb/Dev/workspaces/m/myelin-examples/drift-detection/lib/spark_pubsub-1.1-SNAPSHOT.jar"
    # jar_path = "/Users/ryadhkhisb/Dev/workspaces/m/myelin-examples/drift-detection/lib/spark_pubsub-1.1-SNAPSHOT.jar," \
    #            "/Users/ryadhkhisb/Dev/workspaces/m/drift-detection/lib/gcs-connector-hadoop2-1.9.9-shaded.jar"

shutil.rmtree(os.environ['CHECKPOINT_DIRECTORY'], True)

project_id = os.environ.get("PROJECT_ID")
batch_duration = int(os.environ.get("BATCH_DURATION"))
window_duration = int(os.environ.get("WINDOW_DURATION"))
batch_size = int(os.environ.get("BATCH_SIZE"))
debug_topic = os.environ.get("DEBUG_TOPIC")
state_topic = os.environ.get("STATE_TOPIC")
state_table = os.environ.get("STATE_TABLE")

subscription_name = os.environ.get("PUBSUB_SUBSCRIPTION")
checkpointDirectory = os.environ.get("CHECKPOINT_DIRECTORY")
drift_detector_type = os.environ.get("DRIFT_DETECTOR_TYPE")
cred_location = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
pushgateway_url = os.environ.get("PUSHGATEWAY_URL")
port = os.environ.get("PUSHGATEWAY_PORT")
myelin_ns = os.environ.get("MYELIN_NAMESPACE")


def publish_state(state):
    return publish_to_pushgateway(state[1][1]["axon"], state[0], state[1][1]["drift_probability"])


def update_state(new_values, state):
    logger = logging.getLogger()
    if len(new_values) == 0:
        return state
    drift_detector = None
    if state:
        drift_detector = pickle.loads(state[0])
        warning_detected, change_detected = state[1]["warning_detected"], state[1]["change_detected"]
    else:
        warning_detected, change_detected = False, False

    ####### DEBUG
    logger.warning("&&&&&&&& all data: %s" % new_values)

    all_data = []
    for value in new_values:
        all_data.append(value)
    logger.warning("&&&&&&&& all data: %s" % all_data)
    ######

    model_id = new_values[0]["model_id"]
    model = new_values[0]["model"]
    axon = new_values[0]["axon"]

    for value in new_values:
        data = value["data"]
        batch = np.array(data).astype(np.float64)
        if len(data) == 0:
            continue
        data_dim = get_data_dim(batch)

        if not drift_detector:
            drift_detector = build_drift_detector(drift_detector_type, data_dim)
        drift_detector.fit(data)
        if drift_detector.detected_warning_zone():
            logger.warning('Warning zone has been detected in data: ' + str(value))
            warning_detected = True
        if drift_detector.detected_change():
            logger.warning('Change has been detected in data: ' + str(value))
            change_detected = True
        logger.warning("********** drift_detector data %s:" % data)
        logger.warning("********** drift_detector %s:" % [
            [d.get_params(deep=True) for d in drift_detector.detectors]
        ])
    drift_probability = 0
    if warning_detected:
        drift_probability = 0.8
    if change_detected:
        drift_probability = 0.9
    return (cloudpickle.dumps(drift_detector),
            {"model": model,
             "model_id": model_id,
             "axon": axon,
             "warning_detected": warning_detected,
             "change_detected": change_detected,
             "drift_probability": drift_probability}
            )


def publish_to_pushgateway(axon_name, task_id, value):
    publish_url = "http://{}.{}.svc.cluster.local:{}/metrics/job/{}/pod/".format(pushgateway_url, myelin_ns, port,
                                                                                 task_id)
    internal_metric = get_metric(axon_name, "drift-probability")
    payload = "{} {}\n".format(internal_metric, value)
    res = requests.post(url=publish_url, data=payload,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    return axon_name, task_id, value, res.text, res.status_code


def create_context():
    ssc = StreamingContext(spark.sparkContext, batch_duration)
    ssc.checkpoint(checkpointDirectory)
    return ssc


def write_state_to_bq(rdd):
    logger = logging.getLogger()
    logger.info("write_state_to_bq")
    if rdd is not None:
        data = rdd.collect()
        if len(data) > 0:
            client = bigquery.Client()
            table = client.get_table(state_table)
            rows_to_insert = []
            for tup in data:
                x = tup[1][1]
                rows_to_insert.append((x['model_id'], x['axon'], x['drift_probability'], time.time()))

            errors = client.insert_rows(table, rows_to_insert)  # Make an API request.
            if errors == []:
                logger.error("New rows have been added.")


if __name__ == "__main__":
    main_logger = logging.getLogger()
    main_logger.warning("subscription name: {}".format(subscription_name))
    main_logger.warning("batch size: {}".format(batch_size))
    main_logger.warning("window duration: {}".format(window_duration))
    main_logger.warning("batch duration: {}".format(batch_duration))

    spark_config = SparkSession.builder.appName("DriftDetector")

    if "LOCAL" in os.environ:
        spark_config = spark_config.config("spark.jars", jar_path) \
            .config("spark.driver.extraClassPath", jar_path) \
            .config("spark.executor.extraClassPath", jar_path)
    spark = spark_config.getOrCreate()

    # In Memory
    # context = StreamingContext(spark.sparkContext, batch_duration)
    # lines = [[1, 2, 3], [4, 5, 6]]
    # stream = context.queueStream(lines)

    # Google storage
    # context = StreamingContext.getOrCreate(checkpointDirectory, create_context)
    # stream = context.textFileStream("gs://tt-cluster-sha456-logs-sink/data/")
    spark._jsc.hadoopConfiguration().set('fs.gs.impl', 'com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem')
    spark._jsc.hadoopConfiguration().set('fs.AbstractFileSystem.gs.impl',
                                         'com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS')
    spark._jsc.hadoopConfiguration().set('fs.gs.project.id', project_id)
    spark._jsc.hadoopConfiguration().set('google.cloud.auth.service.account.enable', 'true')
    spark._jsc.hadoopConfiguration().set('google.cloud.auth.service.account.json.keyfile', cred_location)

    # Pubsub
    context = StreamingContext.getOrCreate(checkpointDirectory, create_context)
    stream = pubsub.PubsubUtils.createStream(context, subscription_name, batch_size, True)

    stream.flatMap(parse_request()).updateStateByKey(update_state).map(publish_to_pushgateway).foreachRDD(
        write_state_to_bq)

    context.start()
    context.awaitTermination()
