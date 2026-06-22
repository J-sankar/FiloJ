import pathlib
from shared.config import ALLOWED_FILES


def get_file_type(filename:str) -> str:
    return pathlib.Path(filename).suffix.lower()



def allowed_file_type(filename:str) -> bool :
    file_type = get_file_type(filename)
    return file_type in ALLOWED_FILES