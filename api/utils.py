import pathlib

ALLOWED_FILES = {
    ".pdf":"pdf",
    ".png":"image",
    ".jpeg":"image",
    ".ppt":"ppt",
    ".mkv": "video"
}

def get_file_type(filename:str) -> str:
    return pathlib.Path(filename).suffix.lower()



def allowed_file_type(filename:str) -> bool :
    file_type = get_file_type(filename)
    return file_type in ALLOWED_FILES