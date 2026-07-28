import json
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from exceptions import (
    AWSCLIExecutionError,
    AWSCLINotInstalledError,
    AWSCLITimeoutError,
    AWSInvalidCredentialsError,
    AWSInvalidRegionError,
    AWSNotConfiguredError,
    AWSScannerError,
)
from logger import logger


def find_aws_executable() -> Optional[str]:
    """Locate the 'aws' CLI executable on system PATH."""
    for name in ["aws", "aws.exe", "aws.cmd", "aws.bat"]:
        exe = shutil.which(name)
        if exe:
            return exe
    return None


def run_aws_cli(args: List[str], timeout: int = 30) -> Any:
    """
    Executes an AWS CLI command with subprocess and returns parsed JSON output.
    Enforces a strict timeout (default 30 seconds).
    Raises custom exceptions for CLI errors.
    """
    aws_exe = find_aws_executable()
    cmd_executable = aws_exe if aws_exe else "aws"

    is_windows = sys.platform == "win32"
    if is_windows:
        escaped_args = [f'"{a}"' if " " in a and not a.startswith('"') else a for a in args]
        full_cmd = f'"{cmd_executable}" ' + " ".join(escaped_args)
    else:
        full_cmd = [cmd_executable] + args

    cmd_str_log = f"aws {' '.join(args)}"
    logger.debug(f"Running command: {cmd_str_log}")

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            shell=is_windows,
            timeout=timeout,
            check=False
        )
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd_str_log}")
        raise AWSCLITimeoutError(f"AWS CLI command timed out after {timeout} seconds: '{cmd_str_log}'")
    except FileNotFoundError:
        logger.error("AWS CLI executable not found in system PATH.")
        raise AWSCLINotInstalledError()
    except Exception as e:
        logger.error(f"Subprocess execution failed: {str(e)}")
        raise AWSScannerError(f"Failed to execute command '{cmd_str_log}': {str(e)}")

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    combined_output = f"{stdout}\n{stderr}"

    # Error Check 1: Missing CLI indicator
    missing_indicators = [
        "'aws' is not recognized",
        "aws: command not found",
        "command not found",
        "No such file or directory"
    ]
    if result.returncode != 0 and any(ind.lower() in combined_output.lower() for ind in missing_indicators):
        raise AWSCLINotInstalledError()

    # Error Check 2: Unconfigured / Invalid credentials
    credential_indicators = [
        "Unable to locate credentials",
        "security token included in the request is invalid",
        "ExpiredToken",
        "AccessDenied",
        "AuthFailure",
        "Unauthenticated",
        "InvalidClientTokenId",
        "The config profile could not be found"
    ]
    if any(ind.lower() in combined_output.lower() for ind in credential_indicators):
        if "Unable to locate credentials" in combined_output or "config profile" in combined_output:
            raise AWSNotConfiguredError("AWS credentials not found. Please run 'aws configure'.")
        raise AWSInvalidCredentialsError(f"AWS credential error: {stderr or stdout}")

    # Error Check 3: Invalid Region
    region_indicators = [
        "InvalidRegion",
        "is not a valid region",
        "Could not connect to the endpoint URL",
        "Unknown region"
    ]
    if any(ind.lower() in combined_output.lower() for ind in region_indicators):
        raise AWSInvalidRegionError(f"Invalid AWS region specified or endpoint unreachable: {stderr or stdout}")

    if result.returncode != 0:
        logger.warning(f"Command '{cmd_str_log}' failed with returncode {result.returncode}: {stderr}")
        raise AWSCLIExecutionError(f"AWS CLI execution failed (exit code {result.returncode}): {stderr or stdout}")

    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed for stdout of '{cmd_str_log}': {str(e)}")
        raise AWSScannerError(f"Failed to parse AWS CLI JSON output: {str(e)}")
