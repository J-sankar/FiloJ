import pathlib
from shared.config import ALLOWED_FILES
from fastapi import UploadFile
from shared.logger import get_logger
import magic

logger = get_logger(__name__)


def get_file_type(filename:str) -> str:
    return pathlib.Path(filename).suffix.lower()



def allowed_file_type(filename:str) -> bool :
    file_type = get_file_type(filename)
    return file_type in ALLOWED_FILES



async def validate_mime(file:UploadFile) ->bool:
    claimed_mime = file.content_type
    header = await file.read(2048)
    actual_mime = magic.from_buffer(header)
    logger.debug(f"actual: {actual_mime} | claimed: {claimed_mime}")
    if claimed_mime != actual_mime:
        logger.warning(f"mismatch: CLAIMED MIME: {claimed_mime} | ACTUAL_MIME: {actual_mime}")
        return False
    return True