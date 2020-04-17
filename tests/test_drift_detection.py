import logging
import numpy as np
import sys

from utils import update_state
import os
import traceback
from scipy.stats import bernoulli

logger = logging.getLogger()

moa_jar_path = "/Users/ryadhkhisb/Dev/workspaces/m/drift-detection/lib/meander-detectors-1.0-SNAPSHOT-jar-with-dependencies.jar"
os.environ['MOA_JAR_PATH'] = moa_jar_path
py4j_jar_path = "/Users/ryadhkhisb/Dev/workspaces/m/drift-detection/pyspark/spark-2.4.1-bin-hadoop2.7/jars/py4j-0.10.7.jar"
os.environ['PY4J_JAR_PATH'] = py4j_jar_path


def value(x):
    return {
        'model_id': 'model_id',
        'model': 'model',
        'axon': 'axon',
        'data': np.array([x]),
    }


def get_batches_normal():
    dim = 100
    data_size = 100
    mean_drift = bernoulli.rvs(0.5, size=dim) * 100
    print('Drifted features: %s' % np.mean(mean_drift))
    data_0 = np.random.normal(np.zeros((dim)), 1, (data_size, dim))
    data_1 = np.random.normal(np.zeros((dim)) + mean_drift, 1, (data_size, dim))
    data = np.concatenate([data_0, data_1], axis=0)
    batch_size = 10
    batches = np.array_split(data, data.shape[0] / batch_size)
    return batches


def test_normal_mu_shift():
    batches = get_batches_normal()

    # drift_detector_type = "MOA_KL"
    drift_detector_type = "MOA_SUBSAMPLE_SIMPLE_MAJORITY"
    univariate_detector_types = \
        ["CUSUM", "ADWIN", "GEOMETRIC_MOVING_AVERAGE",
         "DDM", "EDDM", "EWMA", "PAGE_HINKLEY", "HDDM_A",
         "HDDM_W", "SEED", "SEQ1"]

    # univariate_detector_types = ["HDDM_A"]

    # TODO EnsembleDriftDetectionMethods
    univariate_detector_options = {
        "CUSUM": {
            "minNumInstancesOption": {"type": "IntOption", "value": 300, "min": 0, "max": sys.maxsize},
            "deltaOption": {"type": "FloatOption", "value": 0.005, "min": 0.0, "max": 1.0},
            "lambdaOption": {"type": "FloatOption", "value": 50.0, "min": 0.0, "max": sys.float_info.max},
        },
        "ADWIN": {
            "deltaAdwinOption": {"type": "FloatOption", "value": 0.002, "min": 0.0, "max": 1.0},
        },
        "DDM": {
            "minNumInstancesOption": {"type": "IntOption", "value": 30, "min": 0, "max": sys.maxsize},
            "warningLevelOption": {"type": "FloatOption", "value": 2.0, "min": 1.0, "max": 4.0},
            "outcontrolLevelOption": {"type": "FloatOption", "value": 3.0, "min": 1.0, "max": 5.0},
        },
        "EWMA": {
            "minNumInstancesOption": {"type": "IntOption", "value": 30, "min": 0, "max": sys.maxsize},
            "lambdaOption": {"type": "FloatOption", "value": 0.2, "min": 0.0, "max": sys.float_info.max},
        },
        "GEOMETRIC_MOVING_AVERAGE": {
            "minNumInstancesOption": {"type": "IntOption", "value": 30, "min": 0, "max": sys.maxsize},
            "lambdaOption": {"type": "FloatOption", "value": 1.0, "min": 0.0, "max": sys.float_info.max},
            "alphaOption": {"type": "FloatOption", "value": 0.99, "min": 0.0, "max": 1.0},
        },
        "EDDM": {},
        "PAGE_HINKLEY": {
            "minNumInstancesOption": {"type": "IntOption", "value": 30, "min": 0, "max": sys.maxsize},
            "deltaOption": {"type": "FloatOption", "value": 0.005, "min": 0.0, "max": 1.0},
            "lambdaOption": {"type": "FloatOption", "value": 50.0, "min": 0.0, "max": sys.float_info.max},
            "alphaOption": {"type": "FloatOption", "value": 1 - 0.0001, "min": 0.0, "max": 1.0},
        },
        "HDDM_A": {
            "driftConfidenceOption": {"type": "FloatOption", "value": 0.001, "min": 0.0, "max": 1.0},
            "warningConfidenceOption": {"type": "FloatOption", "value": 0.005, "min": 0.0, "max": 1.0},
            "oneSidedTestOption": {"type": "MultiChoiceOption", "value": 1, "options": [0, 1]},
        },
        "HDDM_W": {
            "driftConfidenceOption": {"type": "FloatOption", "value": 0.001, "min": 0.0, "max": 1.0},
            "warningConfidenceOption": {"type": "FloatOption", "value": 0.005, "min": 0.0, "max": 1.0},
            "lambdaOption": {"type": "FloatOption", "value": 0.05, "min": 0.0, "max": 1.0},
            "oneSidedTestOption": {"type": "MultiChoiceOption", "value": 0, "options": [0, 1]},
        },
        "SEED": {
            "deltaSEEDOption": {"type": "FloatOption", "value": 0.05, "min": 0.0, "max": 1.0},
            "blockSizeSEEDOption": {"type": "IntOption", "value": 32, "min": 32, "max": 256},
            "epsilonPrimeSEEDOption": {"type": "FloatOption", "value": 0.01, "min": 0.0025, "max": 0.01},
            "alphaSEEDOption": {"type": "FloatOption", "value": 0.8, "min": 0.2, "max": 0.8},
            "compressTermSEEDOption": {"type": "IntOption", "value": 75, "min": 50, "max": 100},
        },
        "SEQ1": {
            "deltaOption": {"type": "FloatOption", "value": 0.01, "min": 0.0, "max": 1.0},
            "deltaWarningOption": {"type": "FloatOption", "value": 0.1, "min": 0.0, "max": 1.0},
            "blockSeqDriftOption": {"type": "IntOption", "value": 200, "min": 100, "max": 10000},
        },

    }
    """
    IntOption 
    FloatOption
    ListOption
    MultiChoiceOption
    
    CusumDM: minNumInstancesOption = new IntOption("minNumInstances", 'n',  "The minimum number of instances before permitting detecting change.", 30, 0, Integer.MAX_VALUE);
             deltaOption = new FloatOption("delta", 'd', "Delta parameter of the Cusum Test", 0.005, 0.0, 1.0);
             lambdaOption = new FloatOption("lambda", 'l', "Threshold parameter of the Cusum Test", 50, 0.0, Float.MAX_VALUE);
             
    ADWINChangeDetector: deltaAdwinOption = new FloatOption("deltaAdwin", 'a',  "Delta of Adwin change detection", 0.002, 0.0, 1.0);
    
    DDM: minNumInstancesOption = new IntOption("minNumInstances", 'n', "The minimum number of instances before permitting detecting change.", 30, 0, Integer.MAX_VALUE);
         warningLevelOption = new FloatOption( "warningLevel", 'w', "Warning Level.", 2.0, 1.0, 4.0);
         outcontrolLevelOption = new FloatOption("outcontrolLevel", 'o', "Outcontrol Level.", 3.0, 1.0, 5.0);
         
    EnsembleDriftDetectionMethods: changeDetectorsOption = new ListOption("changeDetectors", 'c', "Change Detectors to use.", new ClassOption("driftDetectionMethod", 'd',  "Drift detection method to use.", ChangeDetector.class, "DDM"),new Option[0], ',');
                                   predictionOption = new MultiChoiceOption("prediction", 'l', "Prediction to use.", new String[]{"max", "min", "majority"}, new String[]{"Maximum", "Minimum", "Majority"}, 0);

    EWMAChartDM: minNumInstancesOption = new IntOption("minNumInstances", 'n',  "The minimum number of instances before permitting detecting change.", 30, 0, Integer.MAX_VALUE);
                 lambdaOption = new FloatOption("lambda", 'l', "Lambda parameter of the EWMA Chart Method", 0.2, 0.0, Float.MAX_VALUE);


    GeometricMovingAverageDM: minNumInstancesOption = new IntOption("minNumInstances", 'n',  "The minimum number of instances before permitting detecting change.", 30, 0, Integer.MAX_VALUE);
                              lambdaOption = new FloatOption("lambda", 'l', "Threshold parameter of the Geometric Moving Average Test", 1, 0.0, Float.MAX_VALUE);
                              alphaOption = new FloatOption("alpha", 'a', "Alpha parameter of the Geometric Moving Average Test", .99, 0.0, 1.0);
                              
    HDDM_A_Test: driftConfidenceOption = new FloatOption("driftConfidence", 'd', "Confidence to the drift", 0.001, 0, 1);
                 warningConfidenceOption = new FloatOption("warningConfidence", 'w', "Confidence to the warning", 0.005, 0, 1);
                 oneSidedTestOption = new MultiChoiceOption("typeOfTest", 't',  "Monitors error increments and decrements (two-sided) or only increments (one-sided)", new String[]{ "One-sided", "Two-sided"}, new String[]{"One-sided", "Two-sided"}, 1);

    HDDM_W_Test: driftConfidenceOption = new FloatOption("driftConfidence", 'd', "Confidence to the drift", 0.001, 0, 1);
                 warningConfidenceOption = new FloatOption("warningConfidence", 'w', "Confidence to the warning", 0.005, 0, 1);
                 lambdaOption = new FloatOption("lambda", 'm', "Controls how much weight is given to more recent data compared to older data. Smaller values mean less weight given to recent data.", 0.050, 0, 1);
                 oneSidedTestOption = new MultiChoiceOption("typeOfTest", 't', "Monitors error increments and decrements (two-sided) or only increments (one-sided)", new String[]{"One-sided", "Two-sided"}, new String[]{"One-sided", "Two-sided"},0);

    PageHinkleyDM: minNumInstancesOption = new IntOption("minNumInstances", 'n', "The minimum number of instances before permitting detecting change.", 30, 0, Integer.MAX_VALUE);
                   deltaOption = new FloatOption("delta", 'd', "Delta parameter of the Page Hinkley Test", 0.005, 0.0, 1.0);
                   lambdaOption = new FloatOption("lambda", 'l', "Lambda parameter of the Page Hinkley Test", 50, 0.0, Float.MAX_VALUE);
                   alphaOption = new FloatOption("alpha", 'a', "Alpha parameter of the Page Hinkley Test", 1 - 0.0001, 0.0, 1.0);
                   
    RDDM: minNumInstancesOption = new IntOption("minNumInstances", 'n', "Minimum number of instances before monitoring changes.", 129, 0, Integer.MAX_VALUE);
          warningLevelOption = new FloatOption("warningLevel", 'w', "Warning Level.", 1.773, 1.0, 4.0);
          driftLevelOption = new FloatOption("driftLevel", 'o', "Drift Level.", 2.258, 1.0, 5.0);
          maxSizeConceptOption = new IntOption("maxSizeConcept", 'x', "Maximum Size of Concept.", 40000, 1, Integer.MAX_VALUE);
          minSizeStableConceptOption = new IntOption("minSizeStableConcept", 'y', "Minimum Size of Stable Concept.", 7000, 1, 20000);
          warnLimitOption = new IntOption("warnLimit", 'z', "Warning Limit of instances", 1400, 1, 20000);
          
    SEEDChangeDetector: deltaSEEDOption = new FloatOption("deltaSEED", 'd', "Delta value of SEED Detector", 0.05, 0.0, 1.0);
                        blockSizeSEEDOption = new IntOption("blockSizeSEED", 'b', "BlockSize value of SEED Detector", 32, 32, 256);
                        epsilonPrimeSEEDOption = new FloatOption("epsilonPrimeSEED", 'e', "EpsilonPrime value of SEED Detector", 0.01, 0.0025, 0.01);
                        alphaSEEDOption = new FloatOption("alphaSEED", 'a', "Alpha value of SEED Detector", 0.8, 0.2, 0.8);
                        compressTermSEEDOption = new IntOption("compressTermSEED", 'c', "CompressTerm value of SEED Detector", 75, 50, 100);
          
    SeqDrift1ChangeDetector: deltaOption = new FloatOption("deltaSeqDrift1", 'd', "Delta of SeqDrift1 change detection",0.01, 0.0, 1.0);
                             deltaWarningOption = new FloatOption("deltaWarningOption", 'w', "Delta of SeqDrift1 change detector to declare warning state",0.1, 0.0, 1.0);
                             blockSeqDriftOption = new IntOption("blockSeqDrift1Option",'b',"Block size of SeqDrift1 change detector", 200, 100, 10000);

    
    SeqDrift2ChangeDetector: deltaSeqDrift2Option = new FloatOption("deltaSeq2Drift", 'd', "Delta of SeqDrift2 change detection",0.01, 0.0, 1.0);
                             blockSeqDrift2Option = new IntOption("blockSeqDrift2Option",'b',"Block size of SeqDrift2 change detector", 200, 100, 10000);

 
    EDDM: N/A
    """

    # drift_detector_type = "SKMULTIFLOW_ADWIN"
    job_conf = {
        'moa_jar_path': moa_jar_path,
        'drift_detector_type': drift_detector_type,
        'univariate_detector_type': drift_detector_type,
        'threshold': 0.01,
        'py4j_jar_path': py4j_jar_path,
    }
    logger.warning('Starting test')
    dump = False
    for univariate_cd in univariate_detector_types:
        job_conf['univariate_detector_type'] = univariate_cd
        job_conf['univariate_detector_options'] = univariate_detector_options[univariate_cd]
        print(">>> univariate_cd: %s" % univariate_cd)
        try:
            detection_steps = []
            warning_steps = []
            state = None
            for i, b in enumerate(batches):
                new_values = [value(x) for x in b]
                state = update_state(new_values, state, job_conf, dump)

                if state[1]["warning_detected"]:
                    # logger.warning('Warning zone has been detected at index: %s, data: %s' % (i, str(b)))
                    warning_steps.append(i)
                if state[1]["change_detected"]:
                    # logger.warning('Change has been detected at index: %s, data: %s' % (i, str(b)))
                    detection_steps.append(i)
            print('warning_steps (%s): %s' % (len(warning_steps), warning_steps))
            print('detection_steps (%s): %s' % (len(detection_steps), detection_steps))
            if not dump:
                state[0].gg.shutdown()
        except Exception as e:
            traceback.print_exc()
            print(">>> univariate_cd fails: %s, error: %s" % (univariate_cd, e))


if __name__ == '__main__':
    test_normal_mu_shift()
