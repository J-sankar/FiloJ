import random
import time
MAX_DELIVERY_COUNT = 3
BASE_DELAY_MS = 2000        # first retry after ~2s
MAX_DELAY_MS = 300_000       # cap at 5 minutes
JITTER_FRACTION = 0.2


def should_retry(attempt:int) -> bool :
    return attempt > 3


def compute_backoff(attempt:int) -> int:
    if attempt < 0:
        raise ValueError("attempt must be >= 0")
    raw_delay = BASE_DELAY_MS * (2 ** attempt)
    capped_delay = min(MAX_DELAY_MS,raw_delay)
    jitter_range = capped_delay * JITTER_FRACTION
    jittered_delay = capped_delay + random.uniform(-jitter_range, jitter_range)

    # never go below 0, and never exceed the cap even after adding jitter
    return int(max(0, min(jittered_delay, MAX_DELAY_MS)))
    

def build_retry_message(original_payload: dict, attempt: int) -> tuple[dict, dict]:
    new_payload = {**original_payload, "attempt": attempt + 1}
    headers = {"x-delay": compute_backoff(attempt)}
    return new_payload, headers


def build_dead_letter_message(original_payload: dict, final_error: str) -> dict:
    """
    Called once should_retry() returns False — retries are exhausted,
    or the failure was classified as non-retryable in the first place
    (bad URL, 401, 404, etc).
    Builds the payload published to dlx.exchange under its own routing
    key, NOT the queue's built-in x-dead-letter-routing-key (that's a
    separate mechanism for dispatcher's own process crashing, not for
    HTTP delivery failures).
    """
    return {
        **original_payload,
        "final_error": final_error,
        "failed_at": int(time.time()),
        "attempts_made": original_payload.get("attempt", 0) + 1,
    }
        
    