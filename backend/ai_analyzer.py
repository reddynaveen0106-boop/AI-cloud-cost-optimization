import datetime
import json
import os
import time
from typing import Any, Dict, List
from dotenv import load_dotenv

from logger import logger
from models import AIAnalysisResult, AIIssueItem, AIMetadata

# Load environment variables from .env file if available
load_dotenv()


def _strip_resource(res: Dict[str, Any]) -> Dict[str, Any]:
    """Strips large AWS response objects down to lean, token-efficient resource dicts."""
    if hasattr(res, "model_dump"):
        res = res.model_dump()

    return {
        "resource_name": res.get("resource_name", "unknown"),
        "aws_service": res.get("aws_service", "Unknown"),
        "resource_type": res.get("resource_type", "Unknown Resource"),
        "region": res.get("region", "global"),
        "status": res.get("status", "unknown"),
        "instance_type_sku": res.get("instance_type_sku", "N/A"),
        "tags": res.get("tags", {}),
        "recommendation": res.get("recommendation", "")
    }


def _batch_or_truncate_resources(resources: List[Dict[str, Any]], max_items: int = 50) -> List[Dict[str, Any]]:
    """Limits resource array to max_items to prevent token limits on large accounts."""
    stripped = [_strip_resource(r) for r in resources]
    if len(stripped) > max_items:
        logger.info(f"Truncating {len(stripped)} resources to top {max_items} for AI analysis payload efficiency.")
        return stripped[:max_items]
    return stripped


def _heuristic_fallback_analysis(
    stripped_resources: List[Dict[str, Any]],
    region: str,
    start_time: float,
    reason: str = "Fallback rule engine activated."
) -> Dict[str, Any]:
    """
    Fallback rule-based cost engine when OpenRouter API is missing, rate-limited, or unavailable.
    Provides deterministic findings, confidence scores, and CLI fix commands.
    """
    issues = []
    total_savings = 0.0

    if not stripped_resources:
        duration_ms = int((time.time() - start_time) * 1000)
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return {
            "metadata": {
                "model": "heuristic-rule-engine-v1",
                "analysis_timestamp": now_utc,
                "analysis_duration_ms": duration_ms
            },
            "executive_summary": f"Scanned region '{region}'. No cloud resources detected. No cost actions required.",
            "total_estimated_monthly_savings": 0.0,
            "issues": [],
            "best_practices": [
                "Establish AWS Budget alerts to monitor monthly spend thresholds.",
                "Enable AWS Cost Anomaly Detection to identify sudden cost spikes."
            ]
        }

    for res in stripped_resources:
        r_name = res.get("resource_name", "unknown")
        r_type = res.get("resource_type", "unknown").lower()
        r_status = res.get("status", "unknown").lower()
        r_sku = str(res.get("instance_type_sku", "")).lower()

        # Rule 1: Stopped EC2 Instances
        if "ec2" in r_type or "instance" in r_type:
            if r_status in ["stopped", "stopping"]:
                savings = 35.0
                total_savings += savings
                issues.append({
                    "resource_name": r_name,
                    "resource_type": "EC2 Instance",
                    "severity": "HIGH",
                    "category": "Unused Resource",
                    "description": f"Compute instance '{r_name}' is currently stopped. Terminate or snapshot attached EBS volumes to save costs.",
                    "estimated_monthly_savings": savings,
                    "confidence_score": 95,
                    "fix_commands": [
                        f"# Terminate stopped EC2 instance\naws ec2 terminate-instances --region {region} --instance-ids {r_name}"
                    ]
                })
            elif any(gen in r_sku for gen in ["t2.", "m4.", "c4.", "r4."]):
                savings = 15.0
                total_savings += savings
                issues.append({
                    "resource_name": r_name,
                    "resource_type": "EC2 Instance",
                    "severity": "MEDIUM",
                    "category": "Pricing Tier",
                    "description": f"Instance '{r_name}' uses legacy instance tier ({r_sku}). Upgrade to modern generation (e.g. t3/m6g) for up to 20% savings.",
                    "estimated_monthly_savings": savings,
                    "confidence_score": 85,
                    "fix_commands": [
                        f"# Modify instance type to modern tier (t3.micro)\naws ec2 modify-instance-attribute --region {region} --instance-id {r_name} --instance-type '{{\"Value\": \"t3.micro\"}}'"
                    ]
                })

        # Rule 2: Unattached EBS Volumes
        elif "ebs" in r_type or "volume" in r_type:
            if r_status == "available":
                savings = 20.0
                total_savings += savings
                issues.append({
                    "resource_name": r_name,
                    "resource_type": "EBS Volume",
                    "severity": "HIGH",
                    "category": "Unused Resource",
                    "description": f"Storage volume '{r_name}' is unattached ('available'). Delete volume or snapshot to stop idle storage charges.",
                    "estimated_monthly_savings": savings,
                    "confidence_score": 98,
                    "fix_commands": [
                        f"# Delete unattached EBS volume\naws ec2 delete-volume --region {region} --volume-id {r_name}"
                    ]
                })
            elif "gp2" in r_sku:
                savings = 8.0
                total_savings += savings
                issues.append({
                    "resource_name": r_name,
                    "resource_type": "EBS Volume",
                    "severity": "MEDIUM",
                    "category": "Pricing Tier",
                    "description": f"Volume '{r_name}' uses legacy gp2 volume type. Migrate to gp3 for 20% lower cost per GB.",
                    "estimated_monthly_savings": savings,
                    "confidence_score": 90,
                    "fix_commands": [
                        f"# Modify EBS volume type to gp3\naws ec2 modify-volume --region {region} --volume-id {r_name} --volume-type gp3"
                    ]
                })

        # Rule 3: Unassociated Elastic IPs
        elif "elastic ip" in r_type or "address" in r_type:
            if r_status == "unassociated":
                savings = 3.60
                total_savings += savings
                issues.append({
                    "resource_name": r_name,
                    "resource_type": "Elastic IP",
                    "severity": "HIGH",
                    "category": "Unused Resource",
                    "description": f"Unassociated Elastic IP '{r_name}' is incurring idle hourly fees.",
                    "estimated_monthly_savings": savings,
                    "confidence_score": 99,
                    "fix_commands": [
                        f"# Release unassociated Elastic IP\naws ec2 release-address --region {region} --allocation-id {r_name}"
                    ]
                })

    duration_ms = int((time.time() - start_time) * 1000)
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary_text = (
        f"Scanned {len(stripped_resources)} resources in '{region}'. "
        f"Identified {len(issues)} cost optimization opportunities with potential monthly savings of ${total_savings:.2f}. ({reason})"
    )

    return {
        "metadata": {
            "model": "heuristic-rule-engine-v1",
            "analysis_timestamp": now_utc,
            "analysis_duration_ms": duration_ms
        },
        "executive_summary": summary_text,
        "total_estimated_monthly_savings": round(total_savings, 2),
        "issues": issues,
        "best_practices": [
            "Implement automated tagging compliance for Environment, Owner, and CostCenter.",
            "Schedule non-production EC2 instances to stop automatically outside business hours.",
            "Transition cold S3 data to Glacier Infrequent Access after 30 days."
        ]
    }


def analyze_resources(
    resources: List[Dict[str, Any]],
    region: str,
    account_id: str = "Unknown",
    summary_counts: Dict[str, Any] = None
) -> AIAnalysisResult:
    """
    Analyzes AWS resources using OpenRouter Chat Completions API (openai/gpt-4o-mini).
    Strips raw fields, batches resources, uses response_format json_object, temperature=0.2,
    and returns AIAnalysisResult with confidence scores and execution metadata.
    Falls back gracefully if key is unconfigured or API call fails.
    """
    start_time = time.time()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()

    # Pre-process & strip resources
    stripped_resources = _batch_or_truncate_resources(resources, max_items=50)

    # If API key missing or default placeholder, use heuristic rule fallback engine
    if not api_key or api_key == "your_api_key_here":
        logger.info("OPENROUTER_API_KEY missing or set to default placeholder. Using heuristic fallback engine.")
        raw_fallback = _heuristic_fallback_analysis(
            stripped_resources, region, start_time, reason="OpenRouter API key not configured in backend/.env"
        )
        return AIAnalysisResult(**raw_fallback)

    try:
        import openai

        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "AI Cloud Cost Detective"
            }
        )

        system_prompt = (
            "You are an expert Cloud Cost Detective AI specializing in AWS Infrastructure Cost Optimization. "
            "Your task is to analyze AWS resources, identify waste, over-provisioning, idle assets, misconfigurations, "
            "and wrong instance types or storage tiers, and output actionable remediation recommendations.\n\n"
            "CRITICAL INSTRUCTION: You MUST return strictly valid JSON ONLY, conforming exactly to the following JSON schema:\n"
            "{\n"
            '  "executive_summary": "High level executive summary of cost optimization findings",\n'
            '  "total_estimated_monthly_savings": 125.50,\n'
            '  "issues": [\n'
            "    {\n"
            '      "resource_name": "<name_or_id>",\n'
            '      "resource_type": "<type_e.g._EC2_Instance_or_EBS_Volume>",\n'
            '      "severity": "HIGH" | "MEDIUM" | "LOW",\n'
            '      "category": "Unused Resource" | "Over-provisioning" | "Pricing Tier" | "Misconfiguration",\n'
            '      "description": "Explanation of cost waste and impact",\n'
            '      "estimated_monthly_savings": 35.00,\n'
            '      "confidence_score": 95,\n'
            '      "fix_commands": [\n'
            '        "aws ec2 terminate-instances --region <region> --instance-ids <id>"\n'
            "      ]\n"
            "    }\n"
            "  ],\n"
            '  "best_practices": [\n'
            '    "Actionable best practice recommendation 1",\n'
            '    "Actionable best practice recommendation 2"\n'
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"AWS Account ID: {account_id}\n"
            f"Region: {region}\n"
            f"Summary Resource Counts: {json.dumps(summary_counts or {})}\n"
            f"Resources Scanned ({len(stripped_resources)} items):\n"
            f"{json.dumps(stripped_resources, indent=2)}\n\n"
            "Analyze these resources for cost savings opportunities. Return ONLY valid JSON."
        )

        logger.info(f"Sending cost analysis request to OpenRouter API (model: {model_name})...")

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        duration_ms = int((time.time() - start_time) * 1000)
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if content:
            parsed_data = json.loads(content)
            parsed_data["metadata"] = {
                "model": model_name,
                "analysis_timestamp": now_utc,
                "analysis_duration_ms": duration_ms
            }

            # Ensure default fields are present
            if "total_estimated_monthly_savings" not in parsed_data:
                parsed_data["total_estimated_monthly_savings"] = sum(
                    item.get("estimated_monthly_savings", 0.0) for item in parsed_data.get("issues", [])
                )
            if "best_practices" not in parsed_data:
                parsed_data["best_practices"] = [
                    "Set up AWS Cost Anomaly Detection to receive alerts for unbudgeted spikes.",
                    "Review AWS Trusted Advisor recommendations weekly."
                ]

            logger.info(f"OpenRouter analysis completed in {duration_ms}ms using model {model_name}.")
            return AIAnalysisResult(**parsed_data)
        else:
            raise ValueError("OpenRouter API returned empty response content.")

    except Exception as e:
        logger.warning(f"OpenRouter API call failed or threw exception: {str(e)}. Falling back to rule engine.")
        raw_fallback = _heuristic_fallback_analysis(
            stripped_resources, region, start_time, reason=f"OpenRouter API fallback: {str(e)}"
        )
        return AIAnalysisResult(**raw_fallback)
