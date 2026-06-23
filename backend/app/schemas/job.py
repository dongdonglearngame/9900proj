from typing import Literal

JobStatus = Literal["pending", "running", "completed", "failed"]
JobPhase = Literal["queued", "search", "postprocess", "metrics", "done", "failed"]
