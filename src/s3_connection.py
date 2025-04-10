import boto3
import os
from dotenv import load_dotenv
import botocore

load_dotenv()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
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
    os.makedirs(path, exist_ok=True)
    download_path = os.path.join(path, file_name)
    s3.download_file(bucket_name, file_name, download_path)
    print("Download PDF successful!")


def upload_pdf_s3(file_path):
    s3_key = os.path.basename(file_path)
    s3.upload_file(file_path, bucket_name, s3_key)
    print("Upload PDF successful!")



def pdf_exists(object_name=None):
    """Check if a PDF file exists in S3"""
    try:
        s3.head_object(Bucket="carfaxonline-pdfs", Key=object_name)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise  # Other errors should not be silenced

# Example
if pdf_exists('file.pdf'):
    print("PDF exists. Ready to download.")
    
    
else:
    print("PDF does not exist.")

if __name__=="__main__":
    all_objects()
    # Example
    # if pdf_exists('Student ID Card.pdf'):
    #     print("✅ PDF exists. Ready to download.")
        
    #     download_pdf_s3(file_name='Student ID Card.pdf', path ="PDF_S3")

    # else:
    #     print("❌ PDF does not exist.")
    upload_pdf_s3("PDF_S3/Student ID.pdf")
