import boto3

# Initialize the S3 client
# s3 = boto3.client('s3')
s3 = boto3.client(
    's3',
    aws_access_key_id='your-access-key',
    aws_secret_access_key='your-secret-key',
    region_name='us-east-1'
)

# Define bucket name and file details
bucket_name = 'carfaxonline-pdfs'
s3_file_key = 'New Text Document.txt'  # S3 object key (path in bucket)
local_file_path = 'downloaded-file.txt'  # Local file name

# Download the file
s3.download_file(bucket_name, s3_file_key, local_file_path)

print(f"File {s3_file_key} downloaded successfully as {local_file_path}")
