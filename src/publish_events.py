import json

import numpy as np
import requests

DATA_SIZE = 2000000


data_stream = np.ones((DATA_SIZE)) * 19
for i in range(999, 1500):
    data_stream[i] = 99

# Port forward a model proxy:
#  while True; do kubectl port-forward ml-test1-deployer-2990861116-proxy-689cd6dd59-7w9kk  8080:8000; done
#  while True; do kubectl port-forward deploy/ml-test2-deployer-2409019784-proxy  8080:8000; done
url = "http://localhost:8080/predict"
for i in range(DATA_SIZE):
    x = int(data_stream[i])
    data_array = [[x, x, x]]
    jsondata = json.dumps({"data": {"ndarray": data_array}})
    print(jsondata)

    payload = {'json': jsondata}
    session = requests.session()
    print(payload)
    response = session.post(url, data=jsondata, headers={'User-Agent': 'test'})
    # response = session.post(url, json={"data": {"ndarray": data_array}}, headers={'User-Agent': 'test'})

    print(response.status_code)
    print(response.text)

