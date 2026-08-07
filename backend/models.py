from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    region: str = Field(
        ...,
        description="Target AWS Region name (e.g. 'us-east-1', 'ap-south-1')",
        example="us-east-1"
    )
    analysis_id: Optional[str] = Field(
        default=None,
        description="Optional unique identifier for tracking progress via WebSockets",
        example="scan-123456789"
    )


class ResourceItem(BaseModel):
    resource_name: str = Field(..., example="ProdServer")
    resource_type: str = Field(..., example="EC2 Instance")
    aws_service: str = Field(..., example="EC2")
    region: str = Field(..., example="us-east-1")
    availability_zone: str = Field(default="N/A", example="us-east-1a")
    status: str = Field(default="unknown", example="stopped")
    instance_type_sku: Optional[str] = Field(default="N/A", example="t3.micro")
    tags: Dict[str, str] = Field(default_factory=dict, example={"Environment": "Production"})
    recommendation: str = Field(
        default="No immediate action required.",
        example="Terminate if unused for more than 30 days."
    )


class ScanSummary(BaseModel):
    total_resources: int = Field(default=0, example=42)
    ec2: int = Field(default=0, example=10)
    ebs: int = Field(default=0, example=8)
    rds: int = Field(default=0, example=2)
    lambda_functions: int = Field(default=0, example=15)
    s3: int = Field(default=0, example=7)
    elb: int = Field(default=0, example=1)
    nat_gateway: int = Field(default=0, example=1)
    efs: int = Field(default=0, example=0)
    dynamodb: int = Field(default=0, example=0)
    ecs: int = Field(default=0, example=0)
    eks: int = Field(default=0, example=0)
    cloudfront: int = Field(default=0, example=0)
    route53: int = Field(default=0, example=0)
    other: int = Field(default=0, example=0)


class CostByServiceItem(BaseModel):
    service_name: str = Field(..., example="Amazon Elastic Compute Cloud - Compute")
    amount: float = Field(..., example=120.45)
    unit: str = Field(default="USD", example="USD")


class CostAnalysis(BaseModel):
    total_monthly_cost: float = Field(default=0.0, example=350.75)
    currency: str = Field(default="USD", example="USD")
    period_start: Optional[str] = Field(default=None, example="2026-07-01")
    period_end: Optional[str] = Field(default=None, example="2026-07-28")
    cost_by_service: List[CostByServiceItem] = Field(default_factory=list)
    note: Optional[str] = Field(default=None, example="Cost Explorer metrics retrieved successfully.")


class CallerIdentity(BaseModel):
    account_id: str = Field(..., example="123456789012")
    user_id: str = Field(..., example="AKIAIOSFODNN7EXAMPLE")
    arn: str = Field(..., example="arn:aws:iam::123456789012:user/admin")


# AI Analysis Output Models
class AIMetadata(BaseModel):
    model: str = Field(..., example="openai/gpt-4o-mini")
    analysis_timestamp: str = Field(..., example="2026-07-28T12:00:00Z")
    analysis_duration_ms: int = Field(..., example=1234)


class AIIssueItem(BaseModel):
    resource_name: str = Field(..., example="ProdServer")
    resource_type: str = Field(..., example="EC2 Instance")
    severity: str = Field(..., example="HIGH", description="HIGH | MEDIUM | LOW")
    category: str = Field(..., example="Unused Resource", description="Unused Resource | Over-provisioning | Misconfiguration | Pricing Tier")
    description: str = Field(..., example="Compute instance 'ProdServer' is stopped but incurring EBS storage charges.")
    estimated_monthly_savings: float = Field(..., example=25.0)
    confidence_score: int = Field(..., example=95, description="Confidence score from 0 to 100")
    fix_commands: List[str] = Field(
        default_factory=list,
        example=["aws ec2 terminate-instances --instance-ids i-1234567890abcdef0"]
    )


class AIAnalysisResult(BaseModel):
    metadata: AIMetadata
    executive_summary: str = Field(..., example="Scanned 42 resources. Identified $85.00/mo in potential savings across idle EC2 and unattached EBS volumes.")
    total_estimated_monthly_savings: float = Field(..., example=85.0)
    issues: List[AIIssueItem] = Field(default_factory=list)
    best_practices: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    analysis_id: str = Field(..., example="scan-123456789")
    caller_identity: CallerIdentity
    region: str
    execution_time_seconds: float
    summary: ScanSummary
    cost_analysis: CostAnalysis
    ai_analysis: AIAnalysisResult
    resources: List[ResourceItem]


class RegionItem(BaseModel):
    region_name: str = Field(..., example="us-east-1")
    endpoint: str = Field(..., example="ec2.us-east-1.amazonaws.com")
    opt_in_status: Optional[str] = Field(default=None, example="opt-in-not-required")


class RegionsResponse(BaseModel):
    regions: List[RegionItem]
    count: int


# Database & WebSocket Models
class AnalysisHistoryItem(BaseModel):
    id: str = Field(..., example="scan-123456789")
    user_id: Optional[int] = Field(default=None, example=1)
    region: str = Field(..., example="us-east-1")
    resources_scanned: int = Field(..., example=42)
    issues_found: int = Field(..., example=5)
    estimated_monthly_savings: str = Field(..., example="$85.00")
    analysis_result: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(..., example="completed")
    created_at: str = Field(..., example="2026-07-28T12:00:00Z")


class AnalysisHistoryResponse(BaseModel):
    history: List[AnalysisHistoryItem]
    count: int


class WebSocketProgressMessage(BaseModel):
    analysis_id: str = Field(..., example="scan-123456789")
    stage: str = Field(..., example="Scanning AWS resources in us-east-1...")
    progress_percent: int = Field(..., example=50)
    timestamp: str = Field(..., example="2026-07-28T12:00:00Z")


# Auth Models
class UserAuthRequest(BaseModel):
    email: str = Field(..., example="user@example.com")
    password: str = Field(..., example="secretpassword123")


class AuthTokenResponse(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", example="bearer")
    user: Dict[str, Any] = Field(..., example={"id": 1, "email": "user@example.com"})

