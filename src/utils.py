import json
import operator
from functools import reduce


# from google.cloud import pubsub_v1


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


if __name__ == "__main__":
    for l in open("/Users/ryadhkhisb/Downloads/data/1583793882.510804"):
        print(parse_request_file(l))
