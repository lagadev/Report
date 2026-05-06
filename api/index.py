from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from api.fb_report import FacebookReporter

app = FastAPI(
    title="Facebook Report API",
    description="Facebook Help Center reporting automation API",
    version="1.0.0"
)


class FacebookReportRequest(BaseModel):
    target_profile_url: str = Field(..., description="Full URL of the profile to report")
    imposter_full_name: str = Field(..., description="Full name on the impostor profile")
    your_full_name: str = Field(..., description="Your full name (reporter)")
    your_email: str = Field(..., description="Your contact email")
    imposter_email_or_phone: Optional[str] = Field(None, description="Email or phone on impostor profile")
    additional_info: Optional[str] = Field(None, description="Additional context")
    use_proxy: bool = Field(False, description="Use proxy")
    proxy_protocol: Optional[str] = Field(None, description="socks4 or socks5")
    proxy_list: Optional[list[str]] = Field(None, description="List of proxy addresses")


class ReportResponse(BaseModel):
    success: bool
    target_url: str
    reports_sent: int
    message: str


@app.get("/")
def root():
    return {
        "service": "Facebook Report API",
        "status": "running",
        "endpoints": {
            "/report/impersonation": "POST - Report an impersonating profile",
            "/report/burst": "POST - Send multiple reports (burst mode)",
            "/health": "GET - Health check"
        },
        "docs": "/docs"
    }


@app.post("/report/impersonation", response_model=ReportResponse)
def report_impersonation(req: FacebookReportRequest):
    """
    Report a single impersonating profile to Facebook Help Center.
    Uses the impersonation report form (ID: 295309487309948).
    """
    reporter = FacebookReporter(
        target_profile_url=req.target_profile_url,
        imposter_full_name=req.imposter_full_name,
        your_full_name=req.your_full_name,
        your_email=req.your_email,
        imposter_email_or_phone=req.imposter_email_or_phone,
        additional_info=req.additional_info,
        use_proxy=req.use_proxy,
        proxy_protocol=req.proxy_protocol,
        proxy_list=req.proxy_list
    )
    
    success, message, count = reporter.report_once()
    
    return ReportResponse(
        success=success,
        target_url=req.target_profile_url,
        reports_sent=count,
        message=message
    )


@app.post("/report/burst", response_model=ReportResponse)
def report_burst(
    target_profile_url: str = Query(..., description="Full URL of the profile to report"),
    imposter_full_name: str = Query(..., description="Full name on the impostor profile"),
    your_full_name: str = Query(..., description="Your full name"),
    your_email: str = Query(..., description="Your contact email"),
    imposter_email_or_phone: Optional[str] = Query(None),
    additional_info: Optional[str] = Query(None),
    count: int = Query(5, ge=1, le=30, description="Number of reports to send"),
    use_proxy: bool = Query(False),
    proxy_protocol: Optional[str] = Query(None),
    proxy_list: Optional[str] = Query(None, description="Comma-separated proxy list")
):
    """
    Send multiple impersonation reports in burst mode.
    Max 30 reports per burst to avoid rate limiting.
    """
    proxy_arr = proxy_list.split(",") if proxy_list else None
    
    reporter = FacebookReporter(
        target_profile_url=target_profile_url,
        imposter_full_name=imposter_full_name,
        your_full_name=your_full_name,
        your_email=your_email,
        imposter_email_or_phone=imposter_email_or_phone,
        additional_info=additional_info,
        use_proxy=use_proxy,
        proxy_protocol=proxy_protocol,
        proxy_list=proxy_arr
    )
    
    success, message, sent_count = reporter.report_burst(count)
    
    return ReportResponse(
        success=success,
        target_url=target_profile_url,
        reports_sent=sent_count,
        message=message
    )


@app.get("/health")
def health_check():
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
