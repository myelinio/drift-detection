from typing import List

from skmultiflow.drift_detection import EDDM, PageHinkley, DDM, ADWIN
from skmultiflow.drift_detection.base_drift_detector import BaseDriftDetector
from functools import reduce
import operator
import numpy as np


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

    def drift_probability(self):
        proba = 0
        if self.detected_warning_zone():
            proba = 0.8
        if self.detected_change():
            proba = 0.9
        return proba

def build_drift_detector(drift_detector_type: str, dim) -> MultiflowDetector:
    return MultiflowDetector(drift_detector_type, dim)


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
