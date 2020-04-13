from py4j.java_gateway import JavaGateway, JVMView
import os


class MoaDetector:
    def __init__(self, drift_detector_type: str, dim: int, gg: JavaGateway):
        self.gg = gg
        self.detector = moa_detector(drift_detector_type, dim, gg.jvm)

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
        return state

    def __setstate__(self, newstate):
        jar_location = os.path.join(os.environ["SPARK_HOME"],
                                    "jars/meander-detectors-1.0-SNAPSHOT-jar-with-dependencies.jar")
        py4j_jar_path = os.path.join(os.environ["SPARK_HOME"],
                                    "jars/py4j-0.10.7.jar")
        gg = JavaGateway.launch_gateway(jarpath=os.environ.get('PY4J_JAR_PATH', py4j_jar_path),
                                        classpath=os.environ.get('MOA_JAR_PATH', jar_location))
        state = {}
        state['gg'] = gg
        state['detector'] = gg.jvm.uk.ac.bangor.meander.detectors.CollectionUtils.deSerialize(newstate['detector'])
        # re-instate our __dict__ state from the pickled state
        self.__dict__.update(state)


def moa_detector(drift_detector_type: str, dim: int, jvm: JVMView):
    if drift_detector_type == "MOA_KL":
        detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Multivariate.klDetector(10, 5)
    elif drift_detector_type == "MOA_SPLL2":
        detector = jvm.uk.ac.bangor.meander.detectors.Detectors.Multivariate.klDetector(10, 5)
    else:
        raise Exception("Drift detector %s not implemented" % drift_detector_type)
    return jvm.uk.ac.bangor.meander.detectors.MultivariateMoaAdapter(detector)
