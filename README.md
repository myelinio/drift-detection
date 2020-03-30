
```shell script


export clusterName=tt-cluster-sha456
export PROJECT_ID=myelin-development

# Cleanup
gcloud logging sinks delete ${clusterName}-logs-sink
gcloud pubsub subscriptions delete ${clusterName}-logs-subscription
gcloud pubsub topics delete ${clusterName}-logs-topic


export log_filter="resource.type="k8s_container" AND resource.labels.cluster_name="${clusterName}" AND severity>=WARNING AND ("MyelinLoggingFilterOnRequest" OR "MyelinLoggingFilterOnResponse")"


gcloud pubsub topics create ${clusterName}-logs-topic
gcloud pubsub subscriptions create ${clusterName}-logs-subscription --topic=${clusterName}-logs-topic --expiration-period=24h \
--message-retention-duration=1h --project=${PROJECT_ID}

gcloud logging sinks create ${clusterName}-logs-sink pubsub.googleapis.com/projects/${PROJECT_ID}/topics/${clusterName}-logs-topic --log-filter="${log_filter}" --project=${PROJECT_ID}


logging_sa=$(gcloud logging sinks  describe ${clusterName}-logs-sink  --project=${PROJECT_ID} | awk 'BEGIN {FS="writerIdentity: " } ; { print $2 }')
echo ${logging_sa}

gcloud beta pubsub topics add-iam-policy-binding ${clusterName}-logs-topic \
--member ${logging_sa} \
--role roles/pubsub.publisher




kubectl create secret generic spark-sa --from-file=spark-sa.json


dataset_name=${PROJECT_ID}:$(echo ${clusterName} | sed s/-/_/g)_drift_detection
bq --location=europe-west2 mk \
--dataset \
--default_table_expiration 36000 \
${dataset_name}


bq mk \
-t \
--expiration 360000 \
--label organization:development \
${dataset_name}.state \
model_id:STRING,axon:STRING,drift_probability:FLOAT,timestamp:TIMESTAMP


### review
gcloud iam service-accounts get-iam-policy \
${logging_sa}  --format json

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member ${logging_sa} \
  --role roles/editor


select * from `tt_cluster_sha456_drift_detection.state` order by timestamp desc

-- delete from `tt_cluster_sha456_drift_detection.state` where axon="ml-test-hp"
-- AND `timestamp` < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)

-- select count(*) from `tt_cluster_sha456_drift_detection.state`

logging_sa_s3=$(gcloud logging sinks  describe ${clusterName}-logs-sink-s3  --project=${PROJECT_ID} | awk 'BEGIN {FS="writerIdentity: " } ; { print $2 }')
echo ${logging_sa_s3}

gsutil iam ch ${logging_sa_s3}:objectAdmin gs://${clusterName}-logs-sink

```


```json
{
  "bindings": [
    {
      "members": [
        "serviceAccount:p971122396974-835960@gcp-sa-logging.iam.gserviceaccount.com"
      ],
      "role": "roles/pubsub.publisher"
    }
  ],
  "etag": "BwWf01biaWs=",
  "version": 1
}
```
```json
   {
     "etag": "BwUjMhCsNvY=",
     "bindings": [
       {
         "role": "roles/pubsub.admin",
         "members": [
           "user:user-1@gmail.com"
         ]
       },
       {
         "role": "roles/pubsub.editor",
         "members": [
           "serviceAccount:service-account-2@appspot.gserviceaccount.com"
          ]
       }
     ]
   }
```


## Build Zip
```shell script
conda create --name drift-detection python=3.6
conda activate drift-detection

pip install  -t dependencies numpy
pip install numpy
pip install -t dependencies -r requirements.txt
cp ./src/pubsub.py dependencies
cp ./src/pyspark_pubsub_consumer.py dependencies
cp ./log4j.properties dependencies
cd dependencies
zip -r ../spark-drift-detection.zip .
cd ..
wget https://archive.apache.org/dist/spark/spark-2.4.1/spark-2.4.1-bin-hadoop2.7.tgz  && \
tar xvf spark-2.4.1-bin-hadoop2.7.tgz  && \
rm spark-2.4.1-bin-hadoop2.7.tgz

spark-2.4.1-bin-hadoop2.7/bin/spark-submit \
--master k8s://https://$(minikube ip):8443 \
--deploy-mode cluster \
--name spark-example \
--conf spark.executor.instances=1 \
--conf spark.kubernetes.container.image=pyspark-k8s-example:2.4.1 \
--conf spark.kubernetes.authenticate.driver.serviceAccountName=spark \
--conf spark.kubernetes.pyspark.pythonVersion=3 \
--py-files spark-drift-detection.zip pyspark_pubsub_consumer.py


```


```shell script

minikube start --cpus 4 --memory 4096
eval $(minikube docker-env)
kubectl create serviceaccount spark
kubectl create clusterrolebinding spark-role --clusterrole=edit --serviceaccount=default:spark --namespace=default

docker build . -t pyspark-k8s-example:2.4.1
  
wget https://archive.apache.org/dist/spark/spark-2.4.1/spark-2.4.1-bin-hadoop2.7.tgz  && \
tar xvf spark-2.4.1-bin-hadoop2.7.tgz  && \
rm spark-2.4.1-bin-hadoop2.7.tgz


docker build -t myelinio/drift-detection:0.0.2 . 

spark-2.4.1-bin-hadoop2.7/bin/spark-submit \
    --master k8s://https://$(minikube ip):8443 \
    --deploy-mode cluster \
    --name spark-example \
    --conf spark.executor.instances=1 \
    --conf spark.kubernetes.container.image=myelinio/drift-detection:0.0.2 \
    --conf spark.kubernetes.container.image.pullPolicy=IfNotPresent \
    --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark \
    --conf spark.kubernetes.pyspark.pythonVersion=3 \
    /work/pyspark_pubsub_consumer.py


```