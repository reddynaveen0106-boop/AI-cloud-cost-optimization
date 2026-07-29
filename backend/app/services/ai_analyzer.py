
import json
import os
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()


def _to_dict(resource: Any) -> Dict[str, Any]:
    """Convert Pydantic models or dicts to plain dictionaries."""
    if hasattr(resource, "model_dump"):
        return resource.model_dump()
    if isinstance(resource, dict):
        return resource
    return dict(resource)


def _heuristic_fallback_analysis(resources: List[Any], resource_group: str) -> Dict[str, Any]:
    issues = []
    total_cost = 0.0
    potential_savings = 0.0

    normalized = [_to_dict(r) for r in resources]

    if not normalized:
        return {
            "summary": f"No resources were found in region '{resource_group}'.",
            "total_estimated_monthly_cost": 0.0,
            "potential_monthly_savings": 0.0,
            "savings_percentage": 0.0,
            "issues": []
        }

    for res in normalized:
        r_name = res.get("resource_name", "unknown")
        r_type = res.get("resource_type", "unknown")
        sku_name = str(res.get("instance_type_sku", ""))

        if "ec2" in r_type.lower() or "instance" in r_type.lower():
            total_cost += 70
            if any(x in sku_name.lower() for x in ["large", "xlarge", "m5", "t2"]):
                potential_savings += 35
                issues.append({
                    "resource_name": r_name,
                    "resource_type": r_type,
                    "severity": "MEDIUM",
                    "category": "Over-provisioning",
                    "description": "Instance may be oversized.",
                    "estimated_monthly_savings": 35.0,
                    "fix_commands": [
                        f"aws ec2 stop-instances --instance-ids {r_name}"
                    ]
                })

        elif "ebs" in r_type.lower() or "volume" in r_type.lower():
            total_cost += 20
            potential_savings += 20
            issues.append({
                "resource_name": r_name,
                "resource_type": r_type,
                "severity": "HIGH",
                "category": "Unused Resource",
                "description": "Volume may be unused.",
                "estimated_monthly_savings": 20.0,
                "fix_commands": [
                    f"aws ec2 delete-volume --volume-id {r_name}"
                ]
            })
        elif "elastic ip" in r_type.lower() or "eip" in r_type.lower():
            total_cost += 4
            potential_savings += 4
        else:
            total_cost += 15

    pct = round((potential_savings / total_cost) * 100, 1) if total_cost else 0.0

    return {
        "summary": f"Scanned {len(normalized)} resources in {resource_group}. Found {len(issues)} optimization opportunities.",
        "total_estimated_monthly_cost": round(total_cost, 2),
        "potential_monthly_savings": round(potential_savings, 2),
        "savings_percentage": pct,
        "issues": issues,
    }


def analyze_resources(resources: List[Any], resource_group: str) -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")

    normalized = [_to_dict(r) for r in resources]

    if not api_key or api_key == "your_openrouter_api_key":
        return _heuristic_fallback_analysis(normalized, resource_group)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )

        system_prompt = """
You are an expert AWS Cloud Cost Optimization Engineer.

Analyze the provided AWS resources and identify:

- Idle EC2 instances
- Underutilized EC2 instances
- Unattached EBS volumes
- Idle Elastic IPs
- S3 storage optimization opportunities
- RDS rightsizing opportunities
- Lambda optimization
- ECS/EKS optimization
- CloudFront optimization
- NAT Gateway cost optimization

Return ONLY valid JSON in this exact schema:

{
  "summary": "...",
  "total_estimated_monthly_cost": 0,
  "potential_monthly_savings": 0,
  "savings_percentage": 0,
  "issues": [
    {
      "resource_name": "...",
      "resource_type": "...",
      "severity": "...",
      "category": "...",
      "description": "...",
      "estimated_monthly_savings": 0,
      "fix_commands": []
    }
  ]
}
"""

        user_prompt = (
            f"AWS Region: {resource_group}\n\n"
            f"Resources:\n{json.dumps(normalized, indent=2)}"
        )

        response = client.chat.completions.create(
            model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        content = response.choices[0].message.content
        print("\n===== OPENROUTER CONTENT =====")
        print(content)
        print("=============================\n")
        if not content:
            return _heuristic_fallback_analysis(normalized, resource_group)

        return json.loads(content)

    except Exception as exc:
        result = _heuristic_fallback_analysis(normalized, resource_group)
        result["summary"] += f" (Fallback used: {exc})"
        return result
