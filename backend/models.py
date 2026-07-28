from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    region: str = Field(
        ...,
        description="Target AWS Region name (e.g. 'us-east-1', 'ap-south-1')",
        example="us-east-1"
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


class AIAnalysis(BaseModel):
    summary: str = Field(
        ...,
        example="Scanned 13 AWS resources. Found 4 optimization opportunities. Estimated monthly spend: $48.94 with potential savings of $18.50 (37.8%)."
    )
    total_estimated_monthly_cost: float = Field(
        default=0.0,
        example=48.94
    )
    potential_monthly_savings: float = Field(
        default=0.0,
        example=18.50
    )
    savings_percentage: float = Field(
        default=0.0,
        example=37.8
    )
    issues: List[Dict] = Field(
        default_factory=list,
        example=[
            {
                "resource_name": "my-ec2-instance",
                "resource_type": "EC2 Instance",
                "severity": "HIGH",
                "category": "Over-provisioning",
                "description": "Instance appears oversized for its workload.",
                "estimated_monthly_savings": 25.00,
                "fix_commands": [
                    "aws ec2 stop-instances --instance-ids i-1234567890abcdef0"
                ]
            }
        ]
    )


class AnalyzeResponse(BaseModel):
    caller_identity: CallerIdentity = Field(...)
    region: str = Field(...)
    execution_time_seconds: float = Field(...)
    summary: ScanSummary = Field(...)
    cost_analysis: CostAnalysis = Field(...)
    resources: List[ResourceItem] = Field(default_factory=list)
    ai_analysis: AIAnalysis = Field(...)

class RegionItem(BaseModel):
    region_name: str = Field(..., example="us-east-1")
    endpoint: str = Field(..., example="ec2.us-east-1.amazonaws.com")
    opt_in_status: Optional[str] = Field(default=None, example="opt-in-not-required")


class RegionsResponse(BaseModel):
    regions: List[RegionItem]
    count: int
