from py4j.java_gateway import JavaGateway, JVMView, get_field
import os


class MoaDetector:
    def __init__(self, drift_detector_type: str, job_conf: dict, gg: JavaGateway):
        self.gg = gg
        self.detector = moa_detector(drift_detector_type, job_conf, gg.jvm)

    def fit(self, batch):
        for x in batch:
            self.detector.input(self._to_java_array(x))

    def detected_change(self):
        return self.detector.getChange()

    def detected_warning_zone(self):
        return self.detector.getChange()

    def drift_probability(self):
        proba = 0
        if self.detected_warning_zone():
            proba = 0.8
        if self.detected_change():
            proba = 0.9
        return proba

    def _to_java_array(self, data):
        array = self.gg.new_array(self.gg.jvm.double, len(data))
        for i, d in enumerate(data):
            array[i] = float(d)
        return array

    def __getstate__(self):
        state = {}
        state['detector'] = self.gg.jvm.uk.ac.bangor.meander.detectors.CollectionUtils.serialize(self.detector)
        self.gg.shutdown()
        return state

    def __setstate__(self, newstate):
        jar_location = os.path.join(os.environ.get("SPARK_HOME", ""),
                                    "jars/meander-detectors-1.0-SNAPSHOT-jar-with-dependencies.jar")
        py4j_jar_path = os.path.join(os.environ.get("SPARK_HOME", ""), "jars/py4j-0.10.7.jar")
        gg = JavaGateway.launch_gateway(jarpath=os.environ.get('PY4J_JAR_PATH', py4j_jar_path),
                                        classpath=os.environ.get('MOA_JAR_PATH', jar_location))
        state = {}
        state['gg'] = gg
        state['detector'] = gg.jvm.uk.ac.bangor.meander.detectors.CollectionUtils.deSerialize(newstate['detector'])
        # re-instate our __dict__ state from the pickled state
        self.__dict__.update(state)


def moa_detector(drift_detector_type: str, job_conf: dict, jvm: JVMView):
    if drift_detector_type == "MOA_KL":
        detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Multivariate.klDetector(10, 5)
    elif drift_detector_type == "MOA_SPLL2":
        detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Multivariate.klDetector(100, 1)
    elif drift_detector_type == "MOA_SUBSAMPLE_LOGISTIC_DECAY":
        univariate_detector = build_univariate_detector(job_conf, jvm)
        threshold = job_conf['threshold']
        detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Ensemble.subSampleLogisticDecay(univariate_detector,
                                                                                                threshold)
    elif drift_detector_type == "MOA_SUBSAMPLE_SIMPLE_MAJORITY":
        univariate_detector = build_univariate_detector(job_conf, jvm)
        threshold = job_conf['threshold']
        detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Ensemble.subSampleSimpleMajority(univariate_detector,
                                                                                                 threshold)
    else:
        raise Exception("Drift detector %s not implemented" % drift_detector_type)
    return jvm.uk.ac.bangor.meander.detectors.MultivariateMoaAdapter(detector)


def build_univariate_detector(job_conf, jvm):
    univariate_detector_type = job_conf['univariate_detector_type']
    if univariate_detector_type == "CUSUM":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.cusum()
    elif univariate_detector_type == "ADWIN":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.adwin()
    elif univariate_detector_type == "GEOMETRIC_MOVING_AVERAGE":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.geometricMovingAverage()
    elif univariate_detector_type == "DDM":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.ddm()
    elif univariate_detector_type == "EDDM":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.eddm()
    elif univariate_detector_type == "EWMA":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.ewma()
    elif univariate_detector_type == "PAGE_HINKLEY":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.pageHinkley()
    elif univariate_detector_type == "HDDM_A":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.hddmA()
    elif univariate_detector_type == "HDDM_W":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.hddmW()
    elif univariate_detector_type == "SEED":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.seed()
    elif univariate_detector_type == "SEQ1":
        univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.seq1()
    # elif univariate_detector_type == "SEQ2":
    #     univariate_detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Univariate.seq2()
    else:
        raise Exception("Univariate drift detector %s not implemented" % univariate_detector_type)

    options = job_conf['univariate_detector_options']
    for k, v in options.items():
        moaDetector = get_field(univariate_detector, 'moaDetector')
        if v['type'] == 'MultiChoiceOption':
            get_field(moaDetector, k).setChosenIndex(v['value'])
        else:
            get_field(moaDetector, k).setValue(v['value'])
    return univariate_detector
