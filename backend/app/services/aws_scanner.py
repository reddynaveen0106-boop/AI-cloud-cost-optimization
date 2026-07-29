import datetime
import time
from typing import Any, Dict, List, Tuple

from ..logger import logger
from ..models import (
    CallerIdentity,
    CostAnalysis,
    CostByServiceItem,
    RegionItem,
    RegionsResponse,
    ResourceItem,
    ScanSummary,
)

from ..utils import run_aws_cli


def get_caller_identity() -> CallerIdentity:
    """
    Executes 'aws sts get-caller-identity --output json' to verify AWS credentials,
    confirm CLI setup, and return the Account ID, User ID, and ARN.
    """
    data = run_aws_cli(["sts", "get-caller-identity", "--output", "json"], timeout=30)
    account_id = data.get("Account", "Unknown")
    user_id = data.get("UserId", "Unknown")
    arn = data.get("Arn", "Unknown")

    logger.info(f"Verified IAM caller identity: Account ID={account_id}, User/Role={arn}")
    return CallerIdentity(account_id=account_id, user_id=user_id, arn=arn)


def list_aws_regions() -> RegionsResponse:
    """
    Executes 'aws ec2 describe-regions --output json' to return all available AWS regions.
    """
    data = run_aws_cli(["ec2", "describe-regions", "--output", "json"], timeout=30)
    raw_regions = data.get("Regions", [])

    region_items = []
    for r in raw_regions:
        region_items.append(
            RegionItem(
                region_name=r.get("RegionName", ""),
                endpoint=r.get("Endpoint", ""),
                opt_in_status=r.get("OptInStatus")
            )
        )

    logger.info(f"Fetched {len(region_items)} available AWS regions.")
    return RegionsResponse(regions=region_items, count=len(region_items))


def get_cost_and_usage(region: str) -> CostAnalysis:
    """
    Executes 'aws ce get-cost-and-usage' to fetch monthly cost breakdown by service.
    Falls back gracefully if Cost Explorer is not enabled or permission is denied.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    end_date = now.strftime("%Y-%m-%d")
    start_date = now.replace(day=1).strftime("%Y-%m-%d")

    # If start and end date are equal (first day of month), look back 30 days
    if start_date == end_date:
        start_date = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    ce_args = [
        "ce", "get-cost-and-usage",
        "--time-period", f"Start={start_date},End={end_date}",
        "--granularity", "MONTHLY",
        "--metrics", "UnblendedCost",
        "--group-by", "Type=DIMENSION,Key=SERVICE",
        "--output", "json"
    ]

    try:
        data = run_aws_cli(ce_args, timeout=30)
        results = data.get("ResultsByTime", [])

        total_cost = 0.0
        service_costs = []

        if results:
            groups = results[0].get("Groups", [])
            for group in groups:
                keys = group.get("Keys", [])
                service_name = keys[0] if keys else "Other AWS Services"
                metrics = group.get("Metrics", {}).get("UnblendedCost", {})
                amount = float(metrics.get("Amount", 0.0))
                unit = metrics.get("Unit", "USD")

                if amount > 0.01:
                    total_cost += amount
                    service_costs.append(CostByServiceItem(service_name=service_name, amount=round(amount, 2), unit=unit))

        service_costs.sort(key=lambda x: x.amount, reverse=True)

        return CostAnalysis(
            total_monthly_cost=round(total_cost, 2),
            currency="USD",
            period_start=start_date,
            period_end=end_date,
            cost_by_service=service_costs,
            note="Successfully fetched cost data from AWS Cost Explorer."
        )

    except Exception as e:
        logger.warning(f"AWS Cost Explorer query skipped or unavailable: {str(e)}")
        return CostAnalysis(
            total_monthly_cost=0.0,
            currency="USD",
            period_start=start_date,
            period_end=end_date,
            cost_by_service=[],
            note="Cost Explorer API unavailable or requires 'ce:GetCostAndUsage' permissions."
        )


def _generate_recommendation(res_type: str, status: str, name: str, sku: str, tags: Dict[str, str]) -> str:
    """Generates actionable cost optimization recommendation strings."""
    res_type_lower = res_type.lower()
    status_lower = status.lower()

    if "ec2" in res_type_lower or "instance" in res_type_lower:
        if status_lower in ["stopped", "stopping"]:
            return "Instance is stopped. Terminate if unused for >30 days or convert attached EBS to snapshot to save compute reservation costs."
        elif status_lower == "running":
            if any(legacy in sku.lower() for legacy in ["t2.", "m4.", "c4.", "r4."]):
                return f"Instance is using previous-generation tier '{sku}'. Upgrade to current gen (e.g. t3/m6g) for up to 20% cost-performance savings."
            return "Monitor CPU/Memory utilization to evaluate right-sizing or purchasing Savings Plans."

    elif "ebs" in res_type_lower or "volume" in res_type_lower:
        if status_lower == "available":
            return "Unattached EBS volume detected! Delete volume or create a snapshot and remove volume to eliminate unattached storage costs."
        elif "gp2" in sku.lower():
            return "Volume is using gp2 storage tier. Migrate to gp3 for 20% lower cost per GB and baseline 3000 IOPS."

    elif "elastic ip" in res_type_lower or "address" in res_type_lower:
        if status_lower == "unassociated":
            return "Unassociated Elastic IP incurring hourly idle fees. Release Elastic IP immediately to eliminate waste."

    elif "rds" in res_type_lower or "database" in res_type_lower:
        if status_lower in ["stopped", "stopping"]:
            return "RDS instance is currently stopped. Note that storage costs still apply while stopped."
        return "Review RDS Multi-AZ requirements and consider Reserved DB Instances for long-running production workloads."

    elif "nat gateway" in res_type_lower:
        return "NAT Gateways incur ~$0.045/hr plus data processing charges. Evaluate replacing with NAT Instance or VPC Endpoints for S3/DynamoDB."

    elif "lambda" in res_type_lower:
        return "Verify function execution timeouts and memory allocation. Optimize memory provisioning using AWS Lambda Power Tuning."

    elif "s3" in res_type_lower:
        return "Configure S3 Lifecycle policies to automatically transition infrequently accessed objects to S3 Glacier / Infrequent Access."

    elif "elb" in res_type_lower or "load balancer" in res_type_lower:
        return "Review target group health. Remove unused load balancers that have 0 active targets."

    elif "efs" in res_type_lower:
        return "Enable EFS Lifecycle Management to automatically move cold files to EFS Infrequent Access (IA)."

    return "Review resource usage tag compliance and lifecycle policy configuration."


def scan_aws_resources(region: str) -> Tuple[CallerIdentity, List[ResourceItem], ScanSummary, CostAnalysis]:
    """
    Scans resources across AWS services in the specified region.
    Returns caller identity, parsed resources, resource summary counts, and cost analysis.
    """
    logger.info(f"Starting AWS resource scan for region: '{region}'...")
    start_time = time.time()

    # 1. IAM Identity Check
    caller_identity = get_caller_identity()

    resources: List[ResourceItem] = []
    summary = ScanSummary()

    # 2. Scan EC2 Instances
    try:
        ec2_data = run_aws_cli(["ec2", "describe-instances", "--region", region, "--output", "json"], timeout=30)
        for resv in ec2_data.get("Reservations", []):
            for inst in resv.get("Instances", []):
                inst_id = inst.get("InstanceId", "unknown-instance")
                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", []) if "Key" in t and "Value" in t}
                name = tags.get("Name", inst_id)
                status = inst.get("State", {}).get("Name", "unknown")
                az = inst.get("Placement", {}).get("AvailabilityZone", "N/A")
                sku = inst.get("InstanceType", "N/A")

                rec = _generate_recommendation("EC2 Instance", status, name, sku, tags)
                resources.append(
                    ResourceItem(
                        resource_name=name,
                        resource_type="EC2 Instance",
                        aws_service="EC2",
                        region=region,
                        availability_zone=az,
                        status=status,
                        instance_type_sku=sku,
                        tags=tags,
                        recommendation=rec
                    )
                )
                summary.ec2 += 1
    except Exception as e:
        logger.warning(f"EC2 instance scan encountered an issue in {region}: {str(e)}")

    # 3. Scan EBS Volumes
    try:
        vol_data = run_aws_cli(["ec2", "describe-volumes", "--region", region, "--output", "json"], timeout=30)
        for vol in vol_data.get("Volumes", []):
            vol_id = vol.get("VolumeId", "unknown-volume")
            tags = {t["Key"]: t["Value"] for t in vol.get("Tags", []) if "Key" in t and "Value" in t}
            name = tags.get("Name", vol_id)
            status = vol.get("State", "unknown")
            az = vol.get("AvailabilityZone", "N/A")
            vol_type = vol.get("VolumeType", "gp2")
            size = vol.get("Size", 0)
            sku = f"{vol_type} ({size} GB)"

            rec = _generate_recommendation("EBS Volume", status, name, sku, tags)
            resources.append(
                ResourceItem(
                    resource_name=name,
                    resource_type="EBS Volume",
                    aws_service="EC2",
                    region=region,
                    availability_zone=az,
                    status=status,
                    instance_type_sku=sku,
                    tags=tags,
                    recommendation=rec
                )
            )
            summary.ebs += 1
    except Exception as e:
        logger.warning(f"EBS volume scan encountered an issue in {region}: {str(e)}")

    # 4. Scan Elastic IPs
    try:
        addr_data = run_aws_cli(["ec2", "describe-addresses", "--region", region, "--output", "json"], timeout=30)
        for addr in addr_data.get("Addresses", []):
            alloc_id = addr.get("AllocationId", addr.get("PublicIp", "unknown-eip"))
            tags = {t["Key"]: t["Value"] for t in addr.get("Tags", []) if "Key" in t and "Value" in t}
            name = tags.get("Name", alloc_id)
            is_associated = bool(addr.get("AssociationId") or addr.get("InstanceId") or addr.get("NetworkInterfaceId"))
            status = "associated" if is_associated else "unassociated"

            rec = _generate_recommendation("Elastic IP", status, name, "IPv4", tags)
            resources.append(
                ResourceItem(
                    resource_name=name,
                    resource_type="Elastic IP",
                    aws_service="EC2",
                    region=region,
                    availability_zone="N/A",
                    status=status,
                    instance_type_sku="IPv4 EIP",
                    tags=tags,
                    recommendation=rec
                )
            )
            summary.ec2 += 1
    except Exception as e:
        logger.warning(f"Elastic IP scan encountered an issue in {region}: {str(e)}")

    # 5. Scan RDS DB Instances
    try:
        rds_data = run_aws_cli(["rds", "describe-db-instances", "--region", region, "--output", "json"], timeout=30)
        for db in rds_data.get("DBInstances", []):
            db_id = db.get("DBInstanceIdentifier", "unknown-rds")
            tags = {t["Key"]: t["Value"] for t in db.get("TagList", []) if "Key" in t and "Value" in t}
            status = db.get("DBInstanceStatus", "unknown")
            az = db.get("AvailabilityZone", "N/A")
            sku = db.get("DBInstanceClass", "N/A")

            rec = _generate_recommendation("RDS DB Instance", status, db_id, sku, tags)
            resources.append(
                ResourceItem(
                    resource_name=db_id,
                    resource_type="RDS DB Instance",
                    aws_service="RDS",
                    region=region,
                    availability_zone=az,
                    status=status,
                    instance_type_sku=sku,
                    tags=tags,
                    recommendation=rec
                )
            )
            summary.rds += 1
    except Exception as e:
        logger.warning(f"RDS scan encountered an issue in {region}: {str(e)}")

    # 6. Scan Lambda Functions
    try:
        lambda_data = run_aws_cli(["lambda", "list-functions", "--region", region, "--output", "json"], timeout=30)
        for fn in lambda_data.get("Functions", []):
            fn_name = fn.get("FunctionName", "unknown-function")
            runtime = fn.get("Runtime", "N/A")
            memory = fn.get("MemorySize", 128)
            sku = f"{runtime} ({memory} MB)"
            tags = fn.get("Tags") or {}

            rec = _generate_recommendation("Lambda Function", "Active", fn_name, sku, tags)
            resources.append(
                ResourceItem(
                    resource_name=fn_name,
                    resource_type="Lambda Function",
                    aws_service="Lambda",
                    region=region,
                    availability_zone="N/A",
                    status="Active",
                    instance_type_sku=sku,
                    tags=tags,
                    recommendation=rec
                )
            )
            summary.lambda_functions += 1
    except Exception as e:
        logger.warning(f"Lambda scan encountered an issue in {region}: {str(e)}")

    # 7. Scan S3 Buckets
    try:
        s3_data = run_aws_cli(["s3api", "list-buckets", "--output", "json"], timeout=30)
        for bucket in s3_data.get("Buckets", []):
            b_name = bucket.get("Name", "unknown-bucket")
            rec = _generate_recommendation("S3 Bucket", "Active", b_name, "Standard Storage", {})
            resources.append(
                ResourceItem(
                    resource_name=b_name,
                    resource_type="S3 Bucket",
                    aws_service="S3",
                    region=region,
                    availability_zone="Global",
                    status="Active",
                    instance_type_sku="S3 Standard",
                    tags={},
                    recommendation=rec
                )
            )
            summary.s3 += 1
    except Exception as e:
        logger.warning(f"S3 bucket scan encountered an issue: {str(e)}")

    # 8. Scan ELB / ALB
    try:
        elb_data = run_aws_cli(["elbv2", "describe-load-balancers", "--region", region, "--output", "json"], timeout=30)
        for lb in elb_data.get("LoadBalancers", []):
            lb_name = lb.get("LoadBalancerName", "unknown-lb")
            lb_type = lb.get("Type", "application")
            scheme = lb.get("Scheme", "internet-facing")
            sku = f"{lb_type.capitalize()} LB ({scheme})"
            rec = _generate_recommendation("ELB", "active", lb_name, sku, {})
            resources.append(
                ResourceItem(
                    resource_name=lb_name,
                    resource_type="Elastic Load Balancer",
                    aws_service="ELB",
                    region=region,
                    availability_zone="Multi-AZ",
                    status="active",
                    instance_type_sku=sku,
                    tags={},
                    recommendation=rec
                )
            )
            summary.elb += 1
    except Exception as e:
        logger.debug(f"ELB scan skipped in {region}: {str(e)}")

    # 9. Scan NAT Gateways
    try:
        nat_data = run_aws_cli(["ec2", "describe-nat-gateways", "--region", region, "--output", "json"], timeout=30)
        for nat in nat_data.get("NatGateways", []):
            nat_id = nat.get("NatGatewayId", "unknown-nat")
            status = nat.get("State", "unknown")
            tags = {t["Key"]: t["Value"] for t in nat.get("Tags", []) if "Key" in t and "Value" in t}
            name = tags.get("Name", nat_id)
            rec = _generate_recommendation("NAT Gateway", status, name, "Managed NAT", tags)
            resources.append(
                ResourceItem(
                    resource_name=name,
                    resource_type="NAT Gateway",
                    aws_service="EC2",
                    region=region,
                    availability_zone="Multi-AZ",
                    status=status,
                    instance_type_sku="Managed NAT Gateway",
                    tags=tags,
                    recommendation=rec
                )
            )
            summary.nat_gateway += 1
    except Exception as e:
        logger.debug(f"NAT Gateway scan skipped in {region}: {str(e)}")

    # 10. Scan EFS File Systems
    try:
        efs_data = run_aws_cli(["efs", "describe-file-systems", "--region", region, "--output", "json"], timeout=30)
        for fs in efs_data.get("FileSystems", []):
            fs_id = fs.get("FileSystemId", "unknown-efs")
            tags = {t["Key"]: t["Value"] for t in fs.get("Tags", []) if "Key" in t and "Value" in t}
            name = tags.get("Name", fs_id)
            status = fs.get("LifeCycleState", "available")
            rec = _generate_recommendation("EFS File System", status, name, "General Purpose", tags)
            resources.append(
                ResourceItem(
                    resource_name=name,
                    resource_type="EFS File System",
                    aws_service="EFS",
                    region=region,
                    availability_zone="Multi-AZ",
                    status=status,
                    instance_type_sku="EFS Standard",
                    tags=tags,
                    recommendation=rec
                )
            )
            summary.efs += 1
    except Exception as e:
        logger.debug(f"EFS scan skipped in {region}: {str(e)}")

    # 11. Scan DynamoDB Tables
    try:
        ddb_data = run_aws_cli(["dynamodb", "list-tables", "--region", region, "--output", "json"], timeout=30)
        for t_name in ddb_data.get("TableNames", []):
            rec = _generate_recommendation("DynamoDB Table", "active", t_name, "On-Demand/Provisioned", {})
            resources.append(
                ResourceItem(
                    resource_name=t_name,
                    resource_type="DynamoDB Table",
                    aws_service="DynamoDB",
                    region=region,
                    availability_zone="Regional",
                    status="active",
                    instance_type_sku="DynamoDB Table",
                    tags={},
                    recommendation=rec
                )
            )
            summary.dynamodb += 1
    except Exception as e:
        logger.debug(f"DynamoDB scan skipped in {region}: {str(e)}")

    # 12. Scan ECS Clusters
    try:
        ecs_data = run_aws_cli(["ecs", "list-clusters", "--region", region, "--output", "json"], timeout=30)
        for cl_arn in ecs_data.get("clusterArns", []):
            cl_name = cl_arn.split("/")[-1]
            rec = _generate_recommendation("ECS Cluster", "active", cl_name, "Fargate/EC2", {})
            resources.append(
                ResourceItem(
                    resource_name=cl_name,
                    resource_type="ECS Cluster",
                    aws_service="ECS",
                    region=region,
                    availability_zone="Regional",
                    status="active",
                    instance_type_sku="ECS Cluster",
                    tags={},
                    recommendation=rec
                )
            )
            summary.ecs += 1
    except Exception as e:
        logger.debug(f"ECS scan skipped in {region}: {str(e)}")

    # 13. Scan EKS Clusters
    try:
        eks_data = run_aws_cli(["eks", "list-clusters", "--region", region, "--output", "json"], timeout=30)
        for k_name in eks_data.get("clusters", []):
            rec = _generate_recommendation("EKS Cluster", "active", k_name, "Control Plane ($0.10/hr)", {})
            resources.append(
                ResourceItem(
                    resource_name=k_name,
                    resource_type="EKS Cluster",
                    aws_service="EKS",
                    region=region,
                    availability_zone="Regional",
                    status="active",
                    instance_type_sku="Managed EKS",
                    tags={},
                    recommendation=rec
                )
            )
            summary.eks += 1
    except Exception as e:
        logger.debug(f"EKS scan skipped in {region}: {str(e)}")

    # 14. Scan CloudFront Distributions
    try:
        cf_data = run_aws_cli(["cloudfront", "list-distributions", "--output", "json"], timeout=30)
        dist_list = cf_data.get("DistributionList", {}).get("Items", [])
        for dist in dist_list:
            dist_id = dist.get("Id", "unknown-cf")
            domain = dist.get("DomainName", "")
            status = "Enabled" if dist.get("Enabled") else "Disabled"
            rec = _generate_recommendation("CloudFront Distribution", status, dist_id, "Edge CDN", {})
            resources.append(
                ResourceItem(
                    resource_name=f"{dist_id} ({domain})",
                    resource_type="CloudFront Distribution",
                    aws_service="CloudFront",
                    region=region,
                    availability_zone="Global CDN",
                    status=status,
                    instance_type_sku="CloudFront CDN",
                    tags={},
                    recommendation=rec
                )
            )
            summary.cloudfront += 1
    except Exception as e:
        logger.debug(f"CloudFront scan skipped: {str(e)}")

    # 15. Scan Route53 Hosted Zones
    try:
        r53_data = run_aws_cli(["route53", "list-hosted-zones", "--output", "json"], timeout=30)
        for zone in r53_data.get("HostedZones", []):
            z_name = zone.get("Name", "unknown-zone")
            z_id = zone.get("Id", "").replace("/hostedzone/", "")
            rec = _generate_recommendation("Route53 Hosted Zone", "active", z_name, "$0.50/month per zone", {})
            resources.append(
                ResourceItem(
                    resource_name=f"{z_name} ({z_id})",
                    resource_type="Route53 Hosted Zone",
                    aws_service="Route53",
                    region=region,
                    availability_zone="Global DNS",
                    status="active",
                    instance_type_sku="Hosted Zone",
                    tags={},
                    recommendation=rec
                )
            )
            summary.route53 += 1
    except Exception as e:
        logger.debug(f"Route53 scan skipped: {str(e)}")

    # Total summary count calculation
    summary.total_resources = len(resources)

    # 16. Cost Explorer Analysis
    cost_analysis = get_cost_and_usage(region)

    elapsed_time = round(time.time() - start_time, 2)
    logger.info(
        f"Completed AWS scan in region '{region}' for Account '{caller_identity.account_id}'. "
        f"Found {summary.total_resources} resources in {elapsed_time}s."
    )

    return caller_identity, resources, summary, cost_analysis
