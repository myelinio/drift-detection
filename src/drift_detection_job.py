import logging
import os
import shutil

from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext

import pubsub
from utils import parse_request, create_context, update_state, publish_state_metric, \
    write_state_to_bq


if __name__ == "__main__":
    moa_jar_path = os.path.join(os.environ.get("SPARK_HOME", ""), "jars/meander-detectors-1.0-SNAPSHOT-jar-with-dependencies.jar")
    py4j_jar_path = os.path.join(os.environ.get("SPARK_HOME", ""), "jars/py4j-0.10.7.jar")

    if "LOCAL" in os.environ:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = \
            "/Users/ryadhkhisb/Dev/workspaces/m/myelin-examples/drift-detection/spark-sa.json"
        os.environ['PROJECT_ID'] = "myelin-development"
        os.environ['DRIFT_DETECTOR_TYPE'] = "MOA_KL"
        os.environ['PUBSUB_SUBSCRIPTION'] =\
            "projects/myelin-development/subscriptions/test1-sha456-logs-subscription"
        os.environ['CHECKPOINT_DIRECTORY'] = "/tmp/checkpoint"
        os.environ['MYELIN_NAMESPACE'] = "myelin-app"
        os.environ['PUSHGATEWAY_URL'] = "myelin-uat-prometheus-pushgateway"
        os.environ['PUSHGATEWAY_PORT'] = "9091"
        os.environ['BATCH_DURATION'] = "5"
        os.environ['WINDOW_DURATION'] = "5"
        os.environ['BATCH_SIZE'] = "100"
        os.environ['STATE_TOPIC'] = "projects/myelin-development/topics/test1-sha456-state-topic"
        os.environ['STATE_TABLE'] = "myelin-development.test1_sha456_drift_detection.state"
        os.environ['DEBUG_TOPIC'] = "projects/myelin-development/topics/test1-sha456-logs-topic-debug"
        os.environ['INPUT_DRIFT_PROBABILITY_METRIC'] = "input_drift_probability"
        jar_path = "/Users/ryadhkhisb/Dev/workspaces/m/myelin-examples/drift-detection/lib/spark_pubsub-1.1-SNAPSHOT.jar," \
                   "/Users/ryadhkhisb/Dev/workspaces/m/drift-detection/lib/meander-detectors-1.0-SNAPSHOT-jar-with-dependencies.jar"
        moa_jar_path = "/Users/ryadhkhisb/Dev/workspaces/m/drift-detection/lib/meander-detectors-1.0-SNAPSHOT-jar-with-dependencies.jar"
        os.environ['MOA_JAR_PATH'] = "/Users/ryadhkhisb/Dev/workspaces/m/drift-detection/lib/meander-detectors-1.0-SNAPSHOT-jar-with-dependencies.jar"
        os.environ['PY4J_JAR_PATH'] = "/Users/ryadhkhisb/Dev/workspaces/m/drift-detection/pyspark/spark-2.4.1-bin-hadoop2.7/jars/py4j-0.10.7.jar"


    shutil.rmtree(os.environ['CHECKPOINT_DIRECTORY'], True)

    project_id = os.environ.get("PROJECT_ID")
    batch_duration = int(os.environ.get("BATCH_DURATION"))
    window_duration = int(os.environ.get("WINDOW_DURATION"))
    batch_size = int(os.environ.get("BATCH_SIZE"))
    state_table = os.environ.get("STATE_TABLE")

    subscription_name = os.environ.get("PUBSUB_SUBSCRIPTION")
    checkpoint_directory = os.environ.get("CHECKPOINT_DIRECTORY")
    drift_detector_type = os.environ.get("DRIFT_DETECTOR_TYPE")
    cred_location = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    pushgateway_url = os.environ.get("PUSHGATEWAY_URL")
    port = os.environ.get("PUSHGATEWAY_PORT")
    myelin_ns = os.environ.get("MYELIN_NAMESPACE")
    input_drift_probability_metric = os.environ.get("INPUT_DRIFT_PROBABILITY_METRIC")

    main_logger = logging.getLogger()
    main_logger.warning("subscription name: {}".format(subscription_name))
    main_logger.warning("state table: {}".format(state_table))
    main_logger.warning("input_drift_probability_metric: {}".format(input_drift_probability_metric))
    main_logger.warning("batch size: {}".format(batch_size))
    main_logger.warning("window duration: {}".format(window_duration))
    main_logger.warning("batch duration: {}".format(batch_duration))

    spark_config = SparkSession.builder.appName("DriftDetector")

    if "LOCAL" in os.environ:
        spark_config = spark_config.config("spark.jars", jar_path) \
            .config("spark.driver.extraClassPath", jar_path) \
            .config("spark.executor.extraClassPath", jar_path)
    spark = spark_config.getOrCreate()
    job_conf = {
        'moa_jar_path': moa_jar_path,
        'drift_detector_type': drift_detector_type,
        'py4j_jar_path': py4j_jar_path,
    }
    # In Memory
    # context = StreamingContext(spark.sparkContext, batch_duration)
    # lines = [[1, 2, 3], [4, 5, 6]]
    # stream = context.queueStream(lines)

    # Google storage
    # context = StreamingContext.getOrCreate(checkpointDirectory, create_context)
    # stream = context.textFileStream("gs://test1-sha456-logs-sink/data/")
    # spark._jsc.hadoopConfiguration().set('fs.gs.impl', 'com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem')
    # spark._jsc.hadoopConfiguration().set('fs.AbstractFileSystem.gs.impl',
    #                                      'com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS')
    # spark._jsc.hadoopConfiguration().set('fs.gs.project.id', project_id)
    # spark._jsc.hadoopConfiguration().set('google.cloud.auth.service.account.enable', 'true')
    # spark._jsc.hadoopConfiguration().set('google.cloud.auth.service.account.json.keyfile', cred_location)

    # Pubsub
    context = StreamingContext.getOrCreate(checkpoint_directory, lambda: create_context(spark, checkpoint_directory, batch_duration))
    stream = pubsub.PubsubUtils.createStream(context, subscription_name, batch_size, True)

    stream.flatMap(parse_request) \
        .updateStateByKey(lambda new_values, state: update_state(new_values, state, job_conf)) \
        .map(lambda state: publish_state_metric(state, pushgateway_url, myelin_ns, port, input_drift_probability_metric)) \
        .foreachRDD(lambda rdd: write_state_to_bq(rdd, state_table))

    context.start()
    context.awaitTermination()
