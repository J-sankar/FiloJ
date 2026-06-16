from shared.logger import get_logger
import aioboto3 
import os
from aiobotocore.config import AioConfig
from botocore.exceptions import ClientError
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


logger = get_logger(__name__)


class S3StorageAdapter:
    """Storage class adapter for file object storage using s3"""
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = os.getenv("S3_ENDPOINT", "http://localhost:9000")
        self.region = "us-east-1"
        self.upload_bucket = "uploads"

        self.quarantine_bucket = "quarantine"

    async def setup_buckets(self):
        """Create or check if the buckets exists"""
        buckets = [self.upload_bucket, self.quarantine_bucket]
        async with self.session.client("s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,) as s3:
            
            for bucket in buckets:
                try:
                    await s3.head_bucket(Bucket=bucket)
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code")
                    if error_code == "404":
                        await s3.create_bucket(Bucket=bucket)
                    else :
                        logger.error(f"ERROR: {str(e).lower()}")
                        raise e
                logger.info(f"Bucket configured: {bucket}")


    async def upload_file(self, file_key:str, file_stream) -> None:
        """Upload a file stream to s3"""
        async with self.session.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,

        ) as s3:
           
           try:
               
               await s3.upload_fileobj(file_stream, self.upload_bucket,Key=file_key)
               logger.info(f"File uploaded: {file_key[:8]}") 
           except Exception as e :
               logger.error(f"ERROR: {str(e).lower()}")
               raise e


    async def get_file_url(self,file_key:str, expires_in: int = 3600):
        """get predefine_url for file objects in s3"""
        async with self.session.client("s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=AioConfig(

            signature_version='s3v4',
            s3={'addressing_style': 'path'})
            ) as s3:

            try:
                
                response = await s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.upload_bucket, 'Key': file_key},
                ExpiresIn=expires_in,
                )
            except ClientError as e:
                logger.error(f"ERROR: {str(e).lower()}")
                return None

    # The response contains the presigned URL
            return response
        
    async def move_to_quarantine(self, file_key: str) -> None:
        """Move infected files to quarantine bucket"""
        async with self.session.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        ) as s3:
            try:
                # Copy to quarantine
                await s3.copy_object(
                    Bucket=self.quarantine_bucket,
                    CopySource={"Bucket": self.upload_bucket, "Key": file_key},
                    Key=file_key,
                )
                await s3.head_object(Bucket=self.quarantine_bucket, Key=file_key)
                # Delete from uploads
                await s3.delete_object(Bucket=self.upload_bucket, Key=file_key)
                logger.info(f"File quarantined: {file_key[:8]}")
            except Exception as e:
                logger.error(f"ERROR: {str(e).lower()}")
                raise e

                


    async def delete_fileobj(self, file_key:str) -> None:
        """Delete file from uploads bucket"""
        async with self.session.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        ) as s3:
            try:        
                await s3.delete_object(Bucket=self.upload_bucket,Key=file_key)
                logger.info(f"File object deleted: {file_key[:8]}")
            except Exception as e:
                logger.error(f"ERROR: {str(e).lower()}")
                raise e 


