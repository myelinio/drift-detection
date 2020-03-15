
```shell script
SUBSCRIPTION=projects/myelin-development/subscriptions/tt-cluster-sha3-logs-subscription
PROJECT=myelin-development
TOPIC=tt-cluster-sha3-logs-topic
gcloud pubsub topics get-iam-policy \
    projects/${PROJECT}/topics/${TOPIC} \
    --format json

gcloud pubsub subscriptions set-iam-policy \
  projects/${PROJECT}/subscriptions/${SUBSCRIPTION} \
  subscription_policy.json
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