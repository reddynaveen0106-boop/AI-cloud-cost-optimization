from backend.app.models import AnalyzeResponse

print("AnalyzeResponse fields:")
print(AnalyzeResponse.model_fields.keys())

sample = AnalyzeResponse(
    caller_identity={
        "account_id": "123456789012",
        "user_id": "123456789012",
        "arn": "arn:aws:iam::123456789012:root"
    },
    region="us-east-1",
    execution_time_seconds=12.5,
    summary={
        "total_resources": 1,
        "ec2": 1,
        "ebs": 0,
        "rds": 0,
        "lambda_functions": 0,
        "s3": 0,
        "elb": 0,
        "nat_gateway": 0,
        "efs": 0,
        "dynamodb": 0,
        "ecs": 0,
        "eks": 0,
        "cloudfront": 0,
        "route53": 0,
        "other": 0
    },
    cost_analysis={
        "total_monthly_cost": 10.5,
        "currency": "USD",
        "period_start": "2026-07-01",
        "period_end": "2026-07-28",
        "cost_by_service": [],
        "note": "Test"
    },
    resources=[],
    ai_analysis={
        "summary": "AI works!",
        "total_estimated_monthly_cost": 10,
        "potential_monthly_savings": 5,
        "savings_percentage": 50,
        "issues": []
    }
)

print("\nModel Dump:")
print(sample.model_dump())