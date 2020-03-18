import pickle
from typing import List

import cloudpickle
from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from skmultiflow.drift_detection.base_drift_detector import BaseDriftDetector
import numpy as np

import pubsub
import requests
from skmultiflow.drift_detection import EDDM, PageHinkley, DDM, ADWIN

import os
import json
from functools import reduce
import operator

"""

export clusterName=tt-cluster-sha3
export PROJECT_ID=myelin-development
export log_filter="resource.type="k8s_container" AND resource.labels.cluster_name="${clusterName}" AND severity>=WARNING AND ("MyelinLoggingFilterOnRequest" OR "MyelinLoggingFilterOnResponse")"
gcloud pubsub topics create ${clusterName}-logs-topic
gcloud logging sinks create ${clusterName}-logs-sink pubsub.googleapis.com/projects/${PROJECT_ID}/topics/${clusterName}-logs-topic --log-filter="${log_filter}" --project=${PROJECT_ID}

gcloud pubsub subscriptions create ${clusterName}-logs-subscription --topic=${clusterName}-logs-topic --expiration-period=24h \
--message-retention-duration=1h --project=${PROJECT_ID}

logging_sa=serviceAccount:p971122396974-626809@gcp-sa-logging.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member ${logging_sa} \
  --role roles/editor


gcloud beta pubsub topics add-iam-policy-binding ${clusterName}-logs-topic \
--member ${logging_sa} \
--role roles/pubsub.publisher

gcloud iam service-accounts get-iam-policy \
${logging_sa}  --format json



"""

if "LOCAL" in os.environ:
    os.environ[
        'GOOGLE_APPLICATION_CREDENTIALS'] = "/Users/ryadhkhisb/Dev/workspaces/m/myelin-examples/drift-detection/spark-sa.json"
    os.environ['PROJECT_ID'] = "myelin-development"
    os.environ['DRIFT_DETECTOR_TYPE'] = "ADWIN"
    os.environ['PUBSUB_SUBSCRIPTION'] = "projects/myelin-development/subscriptions/tt-cluster-sha3-logs-subscription"
    os.environ['CHECKPOINT_DIRECTORY'] = "/tmp/checkpoint"
    os.environ['MYELIN_NAMESPACE'] = "myelin-app"
    os.environ['PUSHGATEWAY_URL'] = "myelin-uat-prometheus-pushgateway"
    os.environ['PUSHGATEWAY_PORT'] = "9091"
    jar_path = "/Users/ryadhkhisb/Dev/workspaces/m/myelin-examples/drift-detection/lib/spark_pubsub-1.1-SNAPSHOT.jar"

project_id = os.environ.get("PROJECT_ID")
batchDuration = 5
window_duration = 5
batch_size = 2
subscription_name = os.environ.get("PUBSUB_SUBSCRIPTION")
checkpointDirectory = os.environ.get("CHECKPOINT_DIRECTORY")
drift_detector_type = os.environ.get("DRIFT_DETECTOR_TYPE")
cred_location = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
pushgateway_url = os.environ.get("PUSHGATEWAY_URL")
port = os.environ.get("PUSHGATEWAY_PORT")
myelin_ns = os.environ.get("MYELIN_NAMESPACE")


def filter_predict_requests(l_tuple):
    line = l_tuple[0]
    p = json.loads(line)
    request_splits = p["textPayload"].split("MyelinLoggingFilterOnRequest:", 1)
    if len(request_splits) == 2:
        if '"/predict"' in request_splits[1]:
            return True
    return False

#
# def parse_request_file(line):
#     lines = []
#     request_splits = line.split("MyelinLoggingFilterOnRequest:", 1)
#     if len(request_splits) == 2:
#         body = request_splits[1].replace('\\"', '"')
#         parsed_body = json.loads(body)
#         if parsed_body[":path"] == "/predict":
#             model = parsed_body[":authority"].split(":")[0]
#             lines.append((model, (p['timestamp'], parsed_body["requestBody"]["data"]["ndarray"], parsed_body)))
#             lines.append((model, (0, parsed_body["requestBody"]["data"]["ndarray"], parsed_body)))
#     return lines


def parse_request(l_tuple):
    lines = []
    if l_tuple is None:
        return []
    for line in l_tuple:
        p = json.loads(line)
        request_splits = p["textPayload"].split("MyelinLoggingFilterOnRequest:", 1)
        # lines.append(("model", (0, "ndarray", line)))

        # request_splits = line.split("MyelinLoggingFilterOnRequest:", 1)
        if len(request_splits) == 2:

            body = request_splits[1].replace('\\"', '\"')
            parsed_body = json.loads(body)
            if parsed_body[":path"] == "/predict" and parsed_body["ISTIO_METAJSON_LABELS"]["app"].endswith("-proxy"):
                model_id = parsed_body["ISTIO_METAJSON_LABELS"]["deployers.myelinproj.io/deployer"]
                model = parsed_body["ISTIO_METAJSON_LABELS"]["stable-app"]
                lines.append((model_id,
                              {"model": model,
                               "model_id": model_id,
                               "timestamp": p['timestamp'],
                               "data": parsed_body["requestBody"]["data"]["ndarray"],
                               "parsed_body": parsed_body
                               }))
    return lines


def parse_response(l_tuple):
    line = l_tuple[0]
    p = json.loads(line)
    response_splits = p["textPayload"].split("MyelinLoggingFilterOnResponse:", 1)
    if len(response_splits) == 2:
        return response_splits[1]
    return "{}"


class MultiflowDetector:
    def __init__(self, detector_type: str, dim: int):
        self.detectors: List[BaseDriftDetector] = [skmultiflow_detector(detector_type) for _ in range(dim)]

    def fit(self, batch):
        for x in batch:
            for i, e in enumerate(np.array(x).flatten().astype(np.float64)):
                self.detectors[i].add_element(e)

    def detected_change(self):
        return reduce(operator.ior, [detector.detected_change() for detector in self.detectors])

    def detected_warning_zone(self):
        return reduce(operator.ior, [detector.detected_warning_zone() for detector in self.detectors])


def skmultiflow_detector(drift_detector_type: str) -> BaseDriftDetector:
    if drift_detector_type == "EDDM":
        multiflow_detector = EDDM()
    elif drift_detector_type == "PageHinkley":
        multiflow_detector = PageHinkley()
    elif drift_detector_type == "DDM":
        multiflow_detector = DDM()
    elif drift_detector_type == "ADWIN":
        multiflow_detector = ADWIN()
    else:
        raise Exception("Drift detector %s not implemented" % drift_detector_type)
    return multiflow_detector


def build_drift_detector(drift_detector_type: str, dim) -> MultiflowDetector:
    return MultiflowDetector(drift_detector_type, dim)


def update_state(new_values, state):
    drift_detector = None
    if state:
        drift_detector = pickle.loads(state[0])
        warning_detected, change_detected = state[1]["warning_detected"], state[1]["change_detected"]
    else:
        warning_detected, change_detected = False, False

    ####### DEBUG
    print("&&&&&&&& all data: %s" % new_values)

    all_data = []
    for value in new_values:
        all_data.append(value)
    print("&&&&&&&& all data: %s" % all_data)
    ######

    model_id = ""
    model = ""
    if len(new_values) > 0:
        model_id = new_values[0]["model_id"]
        model = new_values[0]["model"]

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
            print('Warning zone has been detected in data: ' + str(value))
            warning_detected = True
        if drift_detector.detected_change():
            print('Change has been detected in data: ' + str(value))
            change_detected = True
        print("********** drift_detector data %s:" % data)
        print("********** drift_detector %s:" % [
            [d.get_params(deep=True) for d in drift_detector.detectors]
        ])
    drift_proba = 0
    if warning_detected:
        drift_proba = 0.8
    if change_detected:
        drift_proba = 0.9

    return (cloudpickle.dumps(drift_detector),
            {"model": model,
             "model_id": model_id,
             "warning_detected": warning_detected,
             "change_detected": change_detected,
             "drift_proba": drift_proba}
            )


def get_data_dim(batch):
    if len(batch[0].shape) == 1:
        data_dim = batch[0].shape[0]
    else:
        data_dim = reduce(operator.mul, batch[0].shape)
    return data_dim


def get_metric(axon_name, metric_name):
    metric = "{}_{}".format(metric_name, axon_name)
    return metric.replace("-", "__")


def publish_state(state):
    print(state)
    return publish_to_pushgateway(state[1][1]["model"], state[0], state[1][1]["drift_proba"])


def publish_to_pushgateway(axon_name, task_id, value):
    publish_url = "http://{}.{}.svc.cluster.local:{}/metrics/job/{}/pod/".format(pushgateway_url, myelin_ns, port,
                                                                                 task_id)
    internal_metric = get_metric(axon_name, "drift-probability")
    payload = "{} {}\n".format(internal_metric, value)
    res = requests.post(url=publish_url, data=payload,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    return axon_name, task_id, value, res.text, res.status_code


if __name__ == "__main__":
    spark_config = SparkSession.builder.appName("DriftDetector")

    if "LOCAL" in os.environ:
        spark_config = spark_config.config("spark.jars", jar_path) \
            .config("spark.driver.extraClassPath", jar_path) \
            .config("spark.executor.extraClassPath", jar_path)
    spark = spark_config.getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")
    logger = spark.sparkContext._jvm.org.apache.log4j
    logger.LogManager.getLogger("org").setLevel(logger.Level.ERROR)
    logger.LogManager.getLogger("akka").setLevel(logger.Level.ERROR)

    ssc = StreamingContext(spark.sparkContext, batchDuration)
    ssc.checkpoint(checkpointDirectory)

    stream = pubsub.PubsubUtils.createStream(ssc, subscription_name, batch_size, True)
    # stream = ssc.textFileStream(log_file)
    # parsed_logs = stream.filter(filter_predict_requests).flatMap(parse_request).groupBy(sf.window("date", "10 seconds", "10 seconds", str(startSecond) + " seconds")).agg(sf.sum("val").alias("sum"))

    parsed_logs = stream.flatMap(parse_request).window(window_duration).updateStateByKey(update_state)
    # parsed_logs = stream.flatMap(parse_request)
    # parsed_logs = stream
    parsed_logs.map(lambda x: publish_state(x)).pprint()

    ssc.start()
    ssc.awaitTermination()
