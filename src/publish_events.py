import json

import numpy as np
import requests

DATA_SIZE = 2000


data_stream = np.ones((DATA_SIZE)) * 19
for i in range(999, 1500):
    data_stream[i] = 99

# Port forward a model proxy:
#  while True; do kubectl -n myelin-minimal-ns port-forward ml-test-hp-deployer-2013794992-proxy-7d479669c4-j2xt8  8080:8000; done
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

