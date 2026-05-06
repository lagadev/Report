from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from api.report import InstagramReporter

app = FastAPI(
    title="Instagram Report API",
    description="API for Instagram account reporting via help center",
    version="1.0.0"
)


class ReportRequest(BaseModel):
    username: str = Field(..., description="Target Instagram username to report")
    account_name: str = Field(..., description="Display name / account name")
    use_proxy: bool = Field(False, description="Whether to use proxy")
    proxy_protocol: Optional[str] = Field(None, description="Proxy protocol: socks4 or socks5")
    proxy_file: Optional[str] = Field(None, description="Path to proxy list file (on server)")


class ReportResponse(BaseModel):
    success: bool
    username: str
    reports_sent: int
    message: str


@app.get("/")
def root():
    return {
        "service": "Instagram Report API",
        "status": "running",
        "endpoints": {
            "/report": "POST - Send a single report",
            "/report/burst": "POST - Send multiple reports (burst mode)",
            "/report/status": "GET - Check report status"
        },
        "docs": "/docs"
    }


@app.post("/report", response_model=ReportResponse)
def send_report(req: ReportRequest):
    """
    Send a single report to Instagram help center for a target username.
    """
    reporter = InstagramReporter(
        username=req.username,
        account_name=req.account_name,
        use_proxy=req.use_proxy,
        proxy_protocol=req.proxy_protocol,
        proxy_file=req.proxy_file
    )
    
    success, message, count = reporter.report_once()
    
    return ReportResponse(
        success=success,
        username=req.username,
        reports_sent=count,
        message=message
    )


@app.post("/report/burst", response_model=ReportResponse)
def send_burst_report(
    username: str = Query(..., description="Target Instagram username"),
    account_name: str = Query(..., description="Account display name"),
    count: int = Query(10, ge=1, le=100, description="Number of reports to send"),
    use_proxy: bool = Query(False),
    proxy_protocol: Optional[str] = Query(None),
    proxy_file: Optional[str] = Query(None)
):
    """
    Send multiple reports in burst mode.
    """
    reporter = InstagramReporter(
        username=username,
        account_name=account_name,
        use_proxy=use_proxy,
        proxy_protocol=proxy_protocol,
        proxy_file=proxy_file
    )
    
    success, message, sent_count = reporter.report_burst(count)
    
    return ReportResponse(
        success=success,
        username=username,
        reports_sent=sent_count,
        message=message
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": __import__("datetime").datetime.now().isoformat()}


# For local development
if __name__ == "__main__":
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
