import httpx
from dispatcher.core.exceptions import RetryableDispatchError,PermanentDispatchError

async def attempt_delivery(http_client:httpx.AsyncClient, url:str,body:str, headers:dict)->None :
    try:
        response = await http_client.post(url,content=body,headers=headers)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        raise RetryableDispatchError(str(e)) from e
    if 300 <= response.status_code < 429:
        raise PermanentDispatchError(f"redirect not followed: {response.status_code}")
    if response.status_code == 429 or response.status_code >= 500:
        raise RetryableDispatchError(f"status {response.status_code}")
    response.raise_for_status()   # raises for remaining 4xx -> uncaught here, translated below
    return response
 