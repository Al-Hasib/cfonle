import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key")
)

bucket_name = "carfaxonline-pdfs"

# List objects in the bucket
def all_objects():
    response = s3.list_objects_v2(Bucket=bucket_name)

    if "Contents" in response:
        for obj in response["Contents"]:
            print(obj["Key"])  # Print all files in the bucket
    else:
        print("Bucket is empty!")


def download_pdf_s3(file_name, path):
    download_path = os.path.join(path, file_name)
    s3.download_file(bucket_name, file_name, download_path)
    print("Download PDF successful!")


def upload_pdf_s3(file_path):
    s3_key = os.path.basename()
    s3.upload_file(file_path, bucket_name, s3_key)
    print("Upload PDF successful!")
