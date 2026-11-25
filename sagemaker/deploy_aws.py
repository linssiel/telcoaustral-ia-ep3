import json
import os
import subprocess
import sys
import tarfile
import time
import boto3

REGION = "us-east-1"
ENDPOINT_NAME = "telcoaustral-intent-endpoint"
MODEL_NAME = f"telcoaustral-sklearn-model-{int(time.time())}"
CONFIG_NAME = f"telcoaustral-config-{int(time.time())}"
IMAGE_URI = "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"

def build_full_tarball():
    artifacts_dir = "model_artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)
    joblib_path = os.path.join(artifacts_dir, "model.joblib")

    if not os.path.exists(joblib_path):
        print("0. Entrenando modelo local primero (sagemaker/train.py)...")
        subprocess.run([sys.executable, "sagemaker/train.py"], check=True)

    tar_path = os.path.join(artifacts_dir, "model_deploy.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(joblib_path, arcname="model.joblib")
        tar.add("sagemaker/inference.py", arcname="code/inference.py")
    return tar_path

def deploy():
    session = boto3.Session(region_name=REGION)
    sts = session.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account_id}:role/LabRole"
    bucket = f"sagemaker-{REGION}-{account_id}"

    s3 = session.client("s3")
    try:
        s3.create_bucket(Bucket=bucket)
    except Exception:
        pass

    tar_path = build_full_tarball()
    s3_key = "telcoaustral-ep3/model/model_deploy.tar.gz"
    print(f"1. Subiendo modelo + inference.py a s3://{bucket}/{s3_key} ...")
    s3.upload_file(tar_path, bucket, s3_key)
    model_data_s3 = f"s3://{bucket}/{s3_key}"

    sm = session.client("sagemaker")
    print(f"2. Registrando Modelo en AWS SageMaker ({MODEL_NAME})...")
    sm.create_model(
        ModelName=MODEL_NAME,
        PrimaryContainer={
            "Image": IMAGE_URI,
            "ModelDataUrl": model_data_s3,
            "Environment": {
                "SAGEMAKER_PROGRAM": "inference.py",
                "SAGEMAKER_SUBMIT_DIRECTORY": model_data_s3
            }
        },
        ExecutionRoleArn=role_arn
    )

    print(f"3. Creando Endpoint Configuration ({CONFIG_NAME})...")
    sm.create_endpoint_config(
        EndpointConfigName=CONFIG_NAME,
        ProductionVariants=[{
            "VariantName": "AllTraffic",
            "ModelName": MODEL_NAME,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.t2.medium"
        }]
    )

    existing = [e["EndpointName"] for e in sm.list_endpoints(NameContains=ENDPOINT_NAME)["Endpoints"]]
    if ENDPOINT_NAME in existing:
        print(f"4. Actualizando Endpoint '{ENDPOINT_NAME}'...")
        sm.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=CONFIG_NAME)
    else:
        print(f"4. Desplegando Endpoint Real-Time '{ENDPOINT_NAME}'...")
        sm.create_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=CONFIG_NAME)

    print("   Esperando a que AWS SageMaker deje el Endpoint en estado 'InService' (~3-5 min)...")
    waiter = sm.get_waiter("endpoint_in_service")
    waiter.wait(EndpointName=ENDPOINT_NAME)
    print(f"\n✅ ¡ENDPOINT DESPLEGADO Y ACTIVO (InService)!: {ENDPOINT_NAME}")

    runtime = session.client("sagemaker-runtime")
    resp = runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Body=json.dumps({"text": "se me cayo el internet de la casa y no tengo señal"})
    )
    print("Prueba de inferencia real en AWS:", resp["Body"].read().decode("utf-8"))

if __name__ == "__main__":
    deploy()