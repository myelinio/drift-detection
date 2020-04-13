import logging

import numpy as np

from skmultiflow_detector import build_drift_detector

logger = logging.getLogger()

"/Users/ryadhkhisb/.m2/repository/nz/ac/waikato/cms/moa/moa/2017.06/moa-2017.06.jar"

from py4j.java_gateway import JavaGateway

# gateway = JavaGateway()
gg = JavaGateway.launch_gateway(jarpath="/Users/ryadhkhisb/anaconda2/envs/nn/share/py4j/py4j0.10.7.jar",
                                classpath="/Users/ryadhkhisb/.m2/repository/uk/ac/bangor/meander-core/1.0-SNAPSHOT/meander-core-1.0-SNAPSHOT.jar:"
                                          "/Users/ryadhkhisb/.m2/repository/uk/ac/bangor/meander-detectors/1.0-SNAPSHOT/meander-detectors-1.0-SNAPSHOT.jar")

gg = JavaGateway.launch_gateway(classpath="/Users/ryadhkhisb/.m2/repository/uk/ac/bangor/meander-detectors/1.0-SNAPSHOT/meander-detectors-1.0-SNAPSHOT.jar")
gg = JavaGateway.launch_gateway(jarpath="/Users/ryadhkhisb/anaconda2/envs/nn/share/py4j/py4j0.10.7.jar", classpath="/Users/ryadhkhisb/.m2/repository/uk/ac/bangor/meander-core/1.0-SNAPSHOT/meander-core-1.0-SNAPSHOT.jar;")
gg = JavaGateway.launch_gateway(classpath="/Users/ryadhkhisb/Dev/workspaces/m/detectblinks/target/detect-blinks-1.0-SNAPSHOT-jar-with-dependencies.jar")

mr_detector = gg.jvm.uk.ac.bangor.meander.detectors.controlchart.MR.detector(True)
context = gg.jvm.uk.ac.bangor.meander.streams.StreamContext()
result = mr_detector.execute(1.0, context)


def test_normal_mu_shift():
    dim = 1
    data_0 = np.random.normal(0, 1, (100, dim))
    data_1 = np.random.normal(10, 1, (100, dim))
    data = np.concatenate([data_0, data_1], axis=0)
    detector = build_drift_detector("ADWIN", dim)
    batch_size = 1
    batches = np.array_split(data, data.shape[0] / batch_size)
    detection_steps = []
    warning_steps = []
    for i, b in enumerate(batches):
        detector.fit(b)
        if detector.detected_warning_zone():
            logger.warning('Warning zone has been detected in data: ' + str(b))
            warning_detected = True
            warning_steps.append(i)
        if detector.detected_change():
            logger.warning('Change has been detected in data: ' + str(b))
            change_detected = True
            detection_steps.append(i)
    print('warning_steps: %s' % warning_steps)
    print('detection_steps: %s' % detection_steps)
