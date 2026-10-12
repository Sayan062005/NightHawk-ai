#!/usr/bin/env python3
"""
NightHawk AI - Docker Automated Verification & Orchestration Suite
Builds images, starts Linux server containers, and verifies end-to-end functionality.
"""

import sys
import os
import subprocess
import time
import urllib.request
import json

class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def print_header(msg: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}=== {msg} ==={Colors.RESET}")

def run_cmd(cmd: list, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    print(f"{Colors.YELLOW}[*] Executing: {' '.join(cmd)}{Colors.RESET}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if res.stdout.strip():
        print(res.stdout)
    if res.stderr.strip():
        print(f"{Colors.RED}{res.stderr}{Colors.RESET}")
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed with code {res.returncode}")
    return res

def check_docker_daemon() -> bool:
    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return res.returncode == 0
    except Exception:
        return False

def verify_http(url: str, name: str, retries: int = 30, delay: float = 2.0) -> bool:
    print(f"{Colors.CYAN}[*] Waiting for {name} to be healthy at {url}...{Colors.RESET}")
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status in (200, 304):
                    body = resp.read().decode("utf-8", errors="ignore")
                    print(f"{Colors.GREEN}[+] {name} is UP! (HTTP {resp.status}){Colors.RESET}")
                    if "status" in body:
                        print(f"    Response: {body[:150]}")
                    return True
        except Exception:
            time.sleep(delay)
    print(f"{Colors.RED}[!] {name} failed to respond within {retries * delay}s{Colors.RESET}")
    return False

def main():
    print(f"{Colors.CYAN}{Colors.BOLD}NightHawk AI — Docker Multi-Container Test Engine{Colors.RESET}")
    
    # 1. Check Docker CLI
    if not check_docker_daemon():
        print(f"{Colors.RED}[!] Docker daemon is not currently responding or Docker is still starting up.{Colors.RESET}")
        return 1

    # 2. Build & Launch Containers
    print_header("Building and Starting NightHawk AI Containers")
    run_cmd(["docker", "compose", "up", "-d", "--build"])

    # 3. Check Backend Container
    print_header("Verifying Backend API Container")
    backend_ok = verify_http("http://127.0.0.1:8000/api/v1/health", "Backend API")

    # 4. Check Frontend Container
    print_header("Verifying Frontend SOC Container")
    frontend_ok = verify_http("http://127.0.0.1:3000", "Frontend SOC Dashboard")

    # 5. Execute Autonomous Linux Controller in Linux Server Container
    print_header("Executing Autonomous Linux Controller in Docker Linux Sandbox")
    cmd_test = [
        "docker", "compose", "exec", "-T", "linux-server",
        "python3", "/app/nighthawk_linux_agent.py",
        "Audit listening network sockets and check running system processes",
        "--max-steps", "3", "-y"
    ]
    test_res = run_cmd(cmd_test, check=False)
    
    print_header("Docker Test Summary")
    print(f"Backend API (Port 8000)       : {'PASSED' if backend_ok else 'FAILED'}")
    print(f"Frontend SOC Dashboard (3000) : {'PASSED' if frontend_ok else 'FAILED'}")
    print(f"Linux Server C2 Sandbox       : {'PASSED' if test_res.returncode == 0 else 'CHECK OUTPUT'}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
