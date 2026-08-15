from shared.broker import BrokerClient
from shared.models import Job
from shared.database import AsyncSesssionLocal
from shared.logger import get_logger
from shared.storage import S3StorageAdapter
from aio_pika.abc import AbstractIncomingMessage,AbstractQueue
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from PIL import Image
import json
from io import BytesIO
import asyncio
from asyncio.exceptions import CancelledError
import piexif
import uuid

MAX_CHUNK_SIZE=50*1024*1024
MAX_DELIVERY_COUNT=3
logger = get_logger(__name__)

async def _publish_audit(
    broker: BrokerClient, job_id: str, routing_key: str, action: str
) -> None:
    """Thin wrapper so audit-log dicts aren't duplicated everywhere."""
    await broker.publish(
        "system.events",
        routing_key,
        payload={
            "job_id": job_id,
            "service": "image_processor",
            "routing_key": routing_key,
            "action": action,
        },
    )

def _rotate_image(img:Image) ->Image:
    if "exif" in img.info:
        exif_dict = piexif.load(img.info["exif"])

        if piexif.ImageIFD.Orientation in exif_dict["0th"]:
            orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)
        

            if orientation == 2:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:
                img = img.rotate(180)
            elif orientation == 4:
                img = img.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 5:
                img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 6:
                img = img.rotate(-90, expand=True)
            elif orientation == 7:
                img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    return img


async def process_image(broker:BrokerClient,message:AbstractIncomingMessage)->None :
    async with message.process(requeue=True):
        try:
            logger.debug("Reached here")
            s3 = S3StorageAdapter()
            logger.debug(f"Payload: {message.body}")
            data_decoded = message.body.decode("utf-8")
            data = json.loads(data_decoded)
            logger.debug(data)
            job_id: str = data["job_id"]
            logger.debug(job_id)
            file_key: str = data["file_hash"]
            logger.debug(f"{job_id} {file_key if job_id or file_key else 'Not found'}")
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Malformed message, discarding: {e}")
            await message.nack(requeue=False)
            return
        try:
            async with AsyncSesssionLocal() as db:
                logger.debug("Searching job")
                result = await db.execute(
                        select(Job).options(selectinload(Job.file)).where(Job.id == uuid.UUID(job_id))
)
                job = result.scalar_one_or_none()
                if not job:
                    logger.error(f"Job not found: {job_id[:8]}")
                    return
                file_metadata = job.file
                if not file_metadata:
                    logger.error(f"Job: {job_id[:8]} | file data not found")
                    return 
                logger.debug("Reached here")
                if file_metadata.upload_id != file_key.split(".")[0]:
                    logger.error(f"Job:{job_id[:8]} | filehash does not match")
                    return
                logger.debug("Job and metadata found")
                job.status = "processing"
                await db.commit()
                file_hash = file_metadata.upload_id
                logger.info(f"Job:{job_id[:8]} | started image processing")
                await _publish_audit(broker,job_id,"event.image_processor.process_start", "started image processing")
                img_stream = BytesIO()
                async for chunk in s3.get_file_stream(file_key,chunk_size=MAX_CHUNK_SIZE):
                    img_stream.write(chunk)
                
                img_stream.seek(0)
                with Image.open(img_stream) as img:
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    

                    img =_rotate_image(img)
                    logger.debug("Rotated image")
                    clean = Image.new(img.mode,img.size)
                    clean.putdata(list(img.getdata()))

                    save_payload : dict[BytesIO, list[str]] = {}

                    for size in [(128, 128), (512, 512), (1024, 1024)]:
                        thumb = clean.copy()
                        thumb.thumbnail(size, resample=Image.Resampling.LANCZOS)


                        for format in ["WEBP", "JPEG"]:
                            out_stream = BytesIO()
                            thumb.save(out_stream,format=format)
                            save_payload[out_stream] = [f"{file_hash}/{size[0]}.{format.lower()}",f"image/{format.lower()}",f"{size[0]}"]
                            logger.debug(f"Job: {job_id[:8]} |Created copy: {format} {size[0]}")

                    for outstream,data in save_payload.items():
                        outstream.seek(0)
                        bucket = s3.processed_bucket
                        new_key = data[0]
                        content_type =  data[1]
                        size = data[2]
                        await s3.upload_file(new_key,outstream,bucket,content_type=content_type)
                        logger.debug(f"Job: {job_id[:8]} | Saved copy: {content_type}b{size}")
                        outstream.close()
                file_metadata.bucket = s3.processed_bucket
                job.status = "completed"
                await db.commit()
                logger.info(f"Job: {job_id[:8]} | Processing Complete")
                await _publish_audit(broker, job_id,"event.image_process.complete","processing complete")
        except MemoryError :
            logger.error(f"Job: {job_id[:8]} | Out of memory !")
            await _publish_audit(broker, job_id,"event.image_process.fail","Memory Error , processing failed")
            return
        except CancelledError:
            pass
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(f"Job: {job_id[:8]} | Error: {str(e).lower()}")
            delivery_count = message.headers.get("x-delivery-count",0)
            if delivery_count >= MAX_DELIVERY_COUNT:
                action = f"{str(e).lower()[:20]} | move to dlx"
            else:
                action = f"{str(e).lower()[:20]} | retry count {delivery_count+1}/{MAX_DELIVERY_COUNT}"
            await _publish_audit(broker, job_id,"event.image_process.fail",action=action)
            raise






async def processor():
    broker: BrokerClient |None = None
    try:
        broker = BrokerClient()
        await broker.connect()
        queue: AbstractQueue = await broker.get_configured_queue("work.tasks", "task.image.process", "image_processor")
        async with queue.iterator() as iterator:
            message:AbstractIncomingMessage
            async for message in iterator:
                await process_image(broker,message)
    except (KeyboardInterrupt, CancelledError):  
        logger.warning("Shutting down...")
    except Exception as e:
        logger.error(f"ERROR | {str(e).lower()}")
    finally:
        if broker.connection:
            await broker.close()




if __name__ == "__main__":
    asyncio.run(processor())


