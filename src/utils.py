import json
import operator
from functools import reduce


import logging
import shutil
import pickle
import time

from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext

import pubsub

import os

from skmultiflow_detector import build_drift_detector
import numpy as np
import cloudpickle
import requests
from google.cloud import bigquery


def parse_request_file(line):
    lines = []
    request_splits = line.split("MyelinLoggingFilterOnRequest:", 1)
    if len(request_splits) == 2:
        body = request_splits[1].replace('\\"', '"')
        parsed_body = json.loads(body)
        if parsed_body[":path"] == "/predict":
            model = parsed_body[":authority"].split(":")[0]
            # lines.append((model, (p['timestamp'], parsed_body["requestBody"]["data"]["ndarray"], parsed_body)))
            lines.append((model, (0, parsed_body["requestBody"]["data"]["ndarray"], parsed_body)))
    return lines


def parse_request(l_tuple):
    lines = []
    if l_tuple is None:
        return []
    for line in l_tuple:
        p = json.loads(line)
        request_splits = p["textPayload"].split("MyelinLoggingFilterOnRequest:", 1)
        if len(request_splits) == 2:

            body = request_splits[1].replace('\\"', '\"')
            parsed_body = json.loads(body)
            if parsed_body[":path"] == "/predict" and parsed_body["ISTIO_METAJSON_LABELS"]["app"].endswith("-proxy"):
                model_id = parsed_body["ISTIO_METAJSON_LABELS"]["deployers.myelinproj.io/deployer"]
                model = parsed_body["ISTIO_METAJSON_LABELS"]["stable-app"]
                axon = parsed_body["ISTIO_METAJSON_LABELS"]["axon"]
                lines.append((model_id,
                              {"model": model,
                               "model_id": model_id,
                               "axon": axon,
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


def filter_predict_requests(l_tuple):
    line = l_tuple[0]
    p = json.loads(line)
    request_splits = p["textPayload"].split("MyelinLoggingFilterOnRequest:", 1)
    if len(request_splits) == 2:
        if '"/predict"' in request_splits[1]:
            return True
    return False



def get_data_dim(batch):
    if len(batch[0].shape) == 1:
        data_dim = batch[0].shape[0]
    else:
        data_dim = reduce(operator.mul, batch[0].shape)
    return data_dim


def get_metric(axon_name, metric_name):
    metric = "{}_{}".format(metric_name, axon_name)
    return metric.replace("-", "__")


def publish_state_metric(state, pushgateway_url, myelin_ns, port, drift_probability_metric):
    publish_to_pushgateway(state[1][1]["axon"], state[0], state[1][1]["drift_probability"],
                           pushgateway_url, myelin_ns, port, drift_probability_metric)
    return state


def update_state(new_values, state, drift_detector_type):
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
    logger.warning(">>> all data: %s" % new_values)
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


def publish_to_pushgateway(axon_name, task_id, value, pushgateway_url, myelin_ns, port, drift_probability_metric):
    logger = logging.getLogger()
    publish_url = "http://{}.{}.svc.cluster.local:{}/metrics/job/{}/pod/".format(pushgateway_url, myelin_ns, port,
                                                                                 task_id)
    internal_metric = get_metric(axon_name, drift_probability_metric)
    payload = "{} {}\n".format(internal_metric, value)
    res = requests.post(url=publish_url, data=payload,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    logger.warning("********** submitted to pushgateway url %s, got response status: %s" % (publish_url, res.status_code))


def create_context(spark, checkpoint_directory, batch_duration):
    ssc = StreamingContext(spark.sparkContext, batch_duration)
    ssc.checkpoint(checkpoint_directory)
    return ssc


def write_state_to_bq(rdd, state_table):
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
    for l in open("/Users/ryadhkhisb/Downloads/data/1583793882.510804"):
        print(parse_request_file(l))
