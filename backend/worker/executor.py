import time


def execute(payload: dict, attempt: int) -> dict:
    time.sleep(payload["duration"])
    if attempt <= payload["fail_until_attempt"]:
        raise RuntimeError(f"Simulated failure on attempt {attempt}")
    return {"message": "Job completed", "attempt": attempt, "duration": payload["duration"]}
