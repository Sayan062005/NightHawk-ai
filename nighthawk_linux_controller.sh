#!/usr/bin/env bash
# ==============================================================================
# NightHawk AI - Standalone Autonomous Linux Controller & C2 Agent
# Powered by NVIDIA NIM: z-ai/glm-5.3 (with z-ai/glm-5.3-flash Fallback)
# Target Environment: Kali Linux, Ubuntu, Debian, Arch, Fedora, WSL
# ==============================================================================

set -o pipefail

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# API Configuration (resolved from environment, .env, or CLI -k flag)
API_KEY="${NVIDIA_API_KEY}"
if [[ -z "$API_KEY" ]]; then
    for f in .env ../.env backend/.env; do
        if [[ -f "$f" ]]; then
            val=$(grep -E '^NVIDIA_API_KEY=' "$f" 2>/dev/null | head -n 1 | cut -d '=' -f2- | tr -d '"'\'' ')
            if [[ -n "$val" && "$val" != your_* ]]; then
                API_KEY="$val"
                break
            fi
        fi
    done
fi
BASE_URL="https://integrate.api.nvidia.com/v1"
PRIMARY_MODEL="z-ai/glm-5.3"
FALLBACK_MODEL="z-ai/glm-5.3-flash"
TIMEOUT=25
MAX_STEPS=20
AUTO_MODE=0
GOAL=""

print_banner() {
    cat << "EOF"
  +===================================================================+
  |    _  ___       __   __  __              __      ___   ____       |
  |   / |/ (_)___ _/ /  / / / /___ __    __ / /__   / _ | /  _/       |
  |  /    / / _ / _ \/ /_/ / _ / |/|/ //  '_/  / __ |_/ /        |
  | /_/|_/_/\_, /_//_/\____/\_,_/|__,__//_/\_\  /_/ |_/___/        |
  |        /___/                                                      |
  |                                                                   |
  |       AUTONOMOUS LINUX RECON & SYSTEM CONTROLLER [AI-C2]          |
  |          Engine: NVIDIA NIM (z-ai/glm-5.3 + Flash Fallback)        |
  +===================================================================+
EOF
}

show_help() {
    print_banner
    echo -e "${BOLD}USAGE:${NC}"
    echo "  ./nighthawk_linux_controller.sh [OPTIONS] [\"GOAL\"]"
    echo ""
    echo -e "${BOLD}OPTIONS:${NC}"
    echo "  -y, --auto            Autonomous mode (executes commands without asking)"
    echo "  -g, --goal <task>     Goal / objective for the AI to accomplish"
    echo "  -k, --api-key <key>   NVIDIA API key (overrides default/env)"
    echo "  -m, --model <name>    Primary model (default: z-ai/glm-5.3)"
    echo "  -f, --fallback <name> Fallback model (default: z-ai/glm-5.3-flash)"
    echo "  -t, --timeout <sec>   Per-call timeout in seconds (default: 25)"
    echo "  -s, --steps <num>     Maximum execution steps (default: 20)"
    echo "  -h, --help            Show this help dialog"
    echo ""
    echo -e "${BOLD}EXAMPLES:${NC}"
    echo "  # Interactive prompt:"
    echo "  ./nighthawk_linux_controller.sh"
    echo ""
    echo "  # Autonomous security audit:"
    echo "  ./nighthawk_linux_controller.sh -y \"Audit all listening ports and find running web servers\""
    echo ""
    echo "  # Penetration test reconnaissance on Kali Linux:"
    echo "  ./nighthawk_linux_controller.sh -y \"Check SUID binaries and look for privilege escalation vectors\""
    echo ""
}

# Parse Arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--auto)
            AUTO_MODE=1
            shift
            ;;
        -g|--goal)
            GOAL="$2"
            shift 2
            ;;
        -k|--api-key)
            API_KEY="$2"
            shift 2
            ;;
        -m|--model)
            PRIMARY_MODEL="$2"
            shift 2
            ;;
        -f|--fallback)
            FALLBACK_MODEL="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -s|--steps)
            MAX_STEPS="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            if [[ -z "$GOAL" ]]; then
                GOAL="$1"
            fi
            shift
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_AGENT="$SCRIPT_DIR/nighthawk_linux_agent.py"

# Check if Python 3 is available
if command -v python3 &>/dev/null; then
    # Prepare arguments for python agent
    PY_ARGS=()
    PY_ARGS+=("-k" "$API_KEY")
    PY_ARGS+=("-m" "$PRIMARY_MODEL")
    PY_ARGS+=("-f" "$FALLBACK_MODEL")
    PY_ARGS+=("--timeout" "$TIMEOUT")
    PY_ARGS+=("--max-steps" "$MAX_STEPS")

    if [[ $AUTO_MODE -eq 1 ]]; then
        PY_ARGS+=("-y")
    fi

    if [[ -n "$GOAL" ]]; then
        PY_ARGS+=("$GOAL")
    fi

    # If nighthawk_linux_agent.py exists in same directory, execute directly
    if [[ -f "$PYTHON_AGENT" ]]; then
        exec python3 "$PYTHON_AGENT" "${PY_ARGS[@]}"
    else
        # Extract embedded Python agent into temporary file and execute
        TMP_AGENT=$(mktemp /tmp/sentinel_agent_XXXXXX.py)
        trap 'rm -f "$TMP_AGENT"' EXIT
        
        # Extract Python code embedded at bottom of this script
        sed -n '/^

exit 0

#__EMBEDDED_PYTHON_START__
#!/usr/bin/env python3
"""
NightHawk AI - Autonomous Linux Command & Control Agent
Powered by NVIDIA NIM (z-ai/glm-5.3 with automatic z-ai/glm-5.3-flash fallback)

Zero external dependencies required (uses Python standard library).
Compatible with Kali Linux, Ubuntu, Debian, Arch, Fedora, Alpine, WSL.
"""

import sys
import os
import json
import time
import subprocess
import platform
import argparse
import urllib.request
import urllib.error
import re
import shlex

# ---------------------------------------------------------------------------
# Default Configuration
# ---------------------------------------------------------------------------
def load_env_api_key() -> str:
    """Reads NVIDIA_API_KEY from environment or local .env file."""
    if os.environ.get("NVIDIA_API_KEY"):
        return os.environ.get("NVIDIA_API_KEY", "")
    for p in [".env", "../.env", "backend/.env"]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.strip().startswith("NVIDIA_API_KEY="):
                            val = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                            if val and not val.startswith("your_"):
                                return val
            except Exception:
                pass
    return ""

DEFAULT_API_KEY = load_env_api_key()

# Dangerous commands to block or require double-confirmation
CATASTROPHIC_PATTERNS = [
    r"rm\s+-(?:r|f|rf|fr)\s+/(?:\s|$|\*)",       # rm -rf /
    r"mkfs\.[a-z0-9]+\s+/dev/",                  # mkfs on device
    r">\s*/dev/sd[a-z]",                          # raw write to disk
    r"dd\s+if=.*?of=/dev/sd[a-z]",                # dd to disk
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", # forkbomb
    r"shutdown\s+-h\s+now",                       # instant shutdown
    r"init\s+0",                                  # poweroff
    r"chmod\s+-R\s+777\s+/",                      # recursive root chmod 777
]

# Ensure UTF-8 output even in non-UTF-8 terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ANSI Terminal Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def print_banner():
    banner = rf"""{Colors.CYAN}{Colors.BOLD}
  +===================================================================+
  |    _  ___       __   __  __              __      ___   ____       |
  |   / |/ (_)___ _/ /  / / / /___ __    __ / /__   / _ | /  _/       |
  |  /    / / _ `/ _ \/ /_/ / _ `/ |/|/ //  '_/  / __ |_/ /        |
  | /_/|_/_/\_, /_//_/\____/\_,_/|__,__//_/\_\  /_/ |_/___/        |
  |        /___/                                                      |
  |                                                                   |
  |       AUTONOMOUS LINUX RECON & SYSTEM CONTROLLER [AI-C2]          |
  |          Engine: NVIDIA NIM (z-ai/glm-5.3 + Flash Fallback)        |
  +===================================================================+{Colors.RESET}
"""
    try:
        print(banner)
    except Exception:
        print("=== NIGHTHAWK AI LINUX CONTROLLER ===")



# ---------------------------------------------------------------------------
# NVIDIA NIM Client with Automatic Fallback & Response Wait
# ---------------------------------------------------------------------------
class NvidiaNIMClient:
    def __init__(self, api_key: str = None, base_url: str = DEFAULT_BASE_URL,
                 primary_model: str = DEFAULT_PRIMARY_MODEL,
                 fallback_model: str = DEFAULT_FALLBACK_MODEL,
                 timeout: float = 30.0):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY") or DEFAULT_API_KEY
        self.base_url = base_url.rstrip("/")
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.timeout = timeout

    def chat_completion(self, messages: list, temperature: float = 0.3, max_tokens: int = 2048) -> dict:
        """
        Sends chat completion request.
        First tries primary model (z-ai/glm-5.3). If it times out, returns HTTP 504/429/500,
        or errors out, automatically falls back to fallback model (z-ai/glm-5.3-flash).
        """
        candidates = [self.primary_model]
        if self.fallback_model and self.fallback_model != self.primary_model:
            candidates.append(self.fallback_model)

        last_error = None

        for model_candidate in candidates:
            is_fallback = (model_candidate != self.primary_model)
            if is_fallback:
                print(f"{Colors.YELLOW}[!] Primary model '{self.primary_model}' timed out or was slow. Falling back to '{model_candidate}'...{Colors.RESET}")
            else:
                print(f"{Colors.GRAY}[*] Querying NVIDIA NIM ({model_candidate}) [timeout={int(self.timeout)}s]...{Colors.RESET}", end="", flush=True)

            payload = {
                "model": model_candidate,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }

            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "NightHawk-LinuxAgent/1.0"
                },
                method="POST"
            )

            start_t = time.time()
            try:
                # Use slightly longer timeout for flash if primary timed out
                call_timeout = self.timeout if not is_fallback else max(self.timeout, 45.0)
                with urllib.request.urlopen(req, timeout=call_timeout) as resp:
                    resp_bytes = resp.read()
                    data = json.loads(resp_bytes.decode("utf-8"))
                    elapsed = time.time() - start_t
                    print(f" {Colors.GREEN}done ({elapsed:.1f}s){Colors.RESET}")

                    choice = data.get("choices", [{}])[0]
                    msg = choice.get("message", {})
                    
                    # Note: GLM-5.3 / GLM-5.3-flash may return reasoning_content
                    content = msg.get("content")
                    reasoning = msg.get("reasoning_content")

                    # If content is empty/None but reasoning exists, use reasoning
                    extracted_text = content if (content and content.strip()) else (reasoning or "")

                    return {
                        "model": model_candidate,
                        "content": extracted_text,
                        "reasoning": reasoning,
                        "raw_message": msg,
                        "is_fallback": is_fallback,
                        "elapsed": elapsed
                    }

            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")[:300]
                except Exception:
                    pass
                print(f" {Colors.RED}HTTP {e.code}{Colors.RESET}")
                last_error = f"HTTP {e.code}: {err_body}"
                # If HTTP error is client error 401 or 400, fallback might not help unless model is unknown
                if e.code == 401:
                    raise RuntimeError(f"NVIDIA API Key Authentication Failed (HTTP 401): {err_body}")

            except (urllib.error.URLError, TimeoutError, OSError) as e:
                print(f" {Colors.RED}Timeout/Connection Error ({e}){Colors.RESET}")
                last_error = str(e)

        raise RuntimeError(f"All NVIDIA NIM model candidates failed. Last error: {last_error}")


# ---------------------------------------------------------------------------
# Linux Host Telemetry & Environment Inspector
# ---------------------------------------------------------------------------
class LinuxHostInspector:
    @staticmethod
    def gather_environment_info() -> dict:
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
            "cwd": os.getcwd(),
            "shell": os.environ.get("SHELL", "/bin/bash"),
        }

        # Check OS release
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            info["distro"] = line.split("=", 1)[1].strip().strip('"')
            except Exception:
                pass
        
        # Check privileges
        if hasattr(os, "geteuid"):
            info["euid"] = os.geteuid()
            info["is_root"] = (os.geteuid() == 0)
        else:
            info["is_root"] = False

        # Detect available CLI security/system tools
        tools_to_check = [
            "bash", "sh", "curl", "wget", "jq", "nmap", "sqlmap", "nikto",
            "gobuster", "hydra", "metasploit", "wireshark", "tcpdump",
            "netstat", "ss", "lsof", "ps", "top", "htop", "systemctl",
            "docker", "ip", "ifconfig", "ping", "traceroute", "grep", "awk", "sed"
        ]
        available_tools = []
        for tool in tools_to_check:
            try:
                res = subprocess.run(["which", tool], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    available_tools.append(tool)
            except Exception:
                pass
        info["available_tools"] = available_tools

        return info


# ---------------------------------------------------------------------------
# Autonomous Command & Control Agent Loop
# ---------------------------------------------------------------------------
class AutonomousLinuxAgent:
    def __init__(self, client: NvidiaNIMClient, auto_mode: bool = False, max_steps: int = 20):
        self.client = client
        self.auto_mode = auto_mode
        self.max_steps = max_steps
        self.env = LinuxHostInspector.gather_environment_info()

    def build_system_prompt(self) -> str:
        distro = self.env.get("distro", self.env.get("platform", "Linux"))
        user = self.env.get("user", "user")
        is_root = self.env.get("is_root", False)
        tools = ", ".join(self.env.get("available_tools", []))
        cwd = self.env.get("cwd", "/root")

        return f"""You are NightHawk AI Linux Controller — an elite autonomous AI system administrator, penetration tester, and DevOps automation agent.
You have direct terminal execution access to this Linux host.

Host Telemetry:
- OS / Distro: {distro}
- Architecture: {self.env.get('machine')}
- Current User: {user} (Root: {is_root})
- Current Working Directory: {cwd}
- Shell: {self.env.get('shell')}
- Available Tools on PATH: {tools}

Operational Instructions:
1. You receive a user goal or system task.
2. Formulate your reasoning and choose ONE shell command to execute next.
3. You will receive the actual command execution output (stdout, stderr, exit code) in the next turn.
4. Inspect the output. If there are errors, adapt and fix them. If more steps are needed, continue.
5. When the user's objective is fully accomplished, set "done": true and provide a comprehensive final summary.

IMPORTANT: You MUST respond ONLY with valid JSON in this exact structure:
{{
  "thought": "Your internal step-by-step reasoning explaining why this command is chosen and what you expect.",
  "command": "The exact shell command to run (or null if done)",
  "explanation": "A concise human-readable description of what this command does.",
  "is_dangerous": false,
  "done": false,
  "final_summary": ""
}}

Rules:
- Output raw JSON only. Do not wrap in markdown quotes if possible, or use standard ```json ... ``` blocks.
- Keep commands non-interactive where possible (e.g. use -y for apt, -q, --batch, or timeout flags).
- Do not run commands that hang indefinitely without a timeout.
- Never destroy the operating system.
"""

    def is_catastrophic(self, command: str) -> bool:
        """Check if command matches known catastrophic destructive patterns."""
        if not command:
            return False
        for pat in CATASTROPHIC_PATTERNS:
            if re.search(pat, command, re.IGNORECASE):
                return True
        return False

    def execute_shell_command(self, cmd: str) -> dict:
        """Executes the command on the host shell and returns stdout, stderr, returncode, elapsed."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}⚡ EXECUTING:{Colors.RESET} {Colors.BOLD}{cmd}{Colors.RESET}")
        
        start_time = time.time()
        # Choose shell (bash preferred on Linux)
        shell_bin = "/bin/bash" if os.path.exists("/bin/bash") else None

        try:
            kwargs = {
                "shell": True,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
            }
            if shell_bin and os.name != "nt":
                kwargs["executable"] = shell_bin

            proc = subprocess.run(cmd, **kwargs)
            elapsed_ms = int((time.time() - start_time) * 1000)

            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            code = proc.returncode

            # Print output to terminal with clean color formatting
            if stdout.strip():
                print(f"{Colors.GREEN}--- [STDOUT] ---{Colors.RESET}")
                # Print preview if output is huge
                lines = stdout.splitlines()
                if len(lines) > 50:
                    for line in lines[:30]:
                        print(f"  {line}")
                    print(f"{Colors.YELLOW}  ... [{len(lines) - 40} lines truncated for display] ...{Colors.RESET}")
                    for line in lines[-10:]:
                        print(f"  {line}")
                else:
                    for line in lines:
                        print(f"  {line}")

            if stderr.strip():
                print(f"{Colors.RED}--- [STDERR] (code {code}) ---{Colors.RESET}")
                for line in stderr.splitlines():
                    print(f"  {line}")

            print(f"{Colors.GRAY}↳ Return code: {code} | Duration: {elapsed_ms}ms{Colors.RESET}\n")

            # Cap output fed back to LLM to prevent context overflow (max 4000 chars)
            max_chars = 4000
            stdout_for_llm = stdout if len(stdout) <= max_chars else stdout[:max_chars] + f"\n... [Output truncated: {len(stdout)} chars total] ..."
            stderr_for_llm = stderr if len(stderr) <= max_chars else stderr[:max_chars] + f"\n... [Stderr truncated: {len(stderr)} chars total] ..."

            return {
                "returncode": code,
                "stdout": stdout_for_llm,
                "stderr": stderr_for_llm,
                "elapsed_ms": elapsed_ms
            }

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            print(f"{Colors.RED}[!] Execution Error: {e}{Colors.RESET}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Subprocess execution failed: {str(e)}",
                "elapsed_ms": elapsed_ms
            }

    def parse_ai_json(self, raw_text: str) -> dict:
        """Parses LLM response, extracting JSON object even if enclosed in markdown or reasoning."""
        clean_text = raw_text.strip()
        
        # 1. Try direct JSON parse
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            pass

        # 2. Extract ```json ... ``` codeblock
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Find outermost { ... }
        start_idx = clean_text.find("{")
        end_idx = clean_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(clean_text[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass

        # 4. Fallback: treat response as command if simple, or thought
        return {
            "thought": raw_text[:300],
            "command": None,
            "explanation": "Could not parse structured JSON from AI output.",
            "is_dangerous": False,
            "done": True,
            "final_summary": raw_text
        }

    def run_goal(self, goal: str):
        """Runs the autonomous command loop until goal is achieved or steps exhausted."""
        print(f"\n{Colors.MAGENTA}{Colors.BOLD}🎯 GOAL:{Colors.RESET} {Colors.BOLD}{goal}{Colors.RESET}")
        print(f"{Colors.GRAY}Mode: {'Autonomous (--auto)' if self.auto_mode else 'Interactive'}{Colors.RESET}")

        messages = [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": f"Execute the following task on this Linux system: {goal}"}
        ]

        step = 0
        while step < self.max_steps:
            step += 1
            print(f"\n{Colors.BLUE}{Colors.BOLD}══════════════════════ [STEP {step} of {self.max_steps}] ══════════════════════{Colors.RESET}")

            # Query AI with fallback
            try:
                res = self.client.chat_completion(messages, temperature=0.2, max_tokens=2048)
            except Exception as e:
                print(f"{Colors.RED}[!] Failed to get AI response: {e}{Colors.RESET}")
                break

            ai_text = res["content"]
            parsed = self.parse_ai_json(ai_text)

            thought = parsed.get("thought", "")
            cmd = parsed.get("command")
            explanation = parsed.get("explanation", "")
            is_dangerous = parsed.get("is_dangerous", False)
            done = parsed.get("done", False)
            final_summary = parsed.get("final_summary", "")

            # Display AI's analysis
            if thought:
                print(f"{Colors.CYAN}🧠 AI Thought:{Colors.RESET} {thought}")
            if explanation:
                print(f"{Colors.GREEN}📋 Plan:{Colors.RESET} {explanation}")

            # Check if task is complete
            if done or not cmd or cmd.strip() == "":
                print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 GOAL ACHIEVED!{Colors.RESET}")
                if final_summary:
                    print(f"{Colors.BOLD}Summary of Results:{Colors.RESET}\n{final_summary}\n")
                elif thought:
                    print(f"{Colors.BOLD}Final Status:{Colors.RESET}\n{thought}\n")
                return

            cmd = cmd.strip()

            # Safety check: Catastrophic destruction
            if self.is_catastrophic(cmd):
                print(f"{Colors.RED}{Colors.BOLD}[CRITICAL WARNING] Catastrophic destructive command detected!{Colors.RESET}")
                print(f"{Colors.RED}Command: {cmd}{Colors.RESET}")
                confirm = input(f"{Colors.YELLOW}Type 'CONFIRM_DESTROY' to run or anything else to abort: {Colors.RESET}")
                if confirm.strip() != "CONFIRM_DESTROY":
                    print(f"{Colors.YELLOW}[*] Command execution aborted by safety guardrail.{Colors.RESET}")
                    messages.append({"role": "assistant", "content": json.dumps(parsed)})
                    messages.append({"role": "user", "content": "Execution blocked by user safety guardrail. Please choose a safe alternative command."})
                    continue

            # In interactive mode, confirm with user
            if not self.auto_mode:
                print(f"{Colors.YELLOW}Command to execute:{Colors.RESET} {Colors.BOLD}{cmd}{Colors.RESET}")
                choice = input(f"Run this command? [{Colors.GREEN}Y{Colors.RESET}/n/e(edit)/q(quit)]: ").strip().lower()
                if choice == "q":
                    print(f"{Colors.YELLOW}[*] Session terminated by user.{Colors.RESET}")
                    return
                elif choice == "e":
                    new_cmd = input("Edit command: ").strip()
                    if new_cmd:
                        cmd = new_cmd
                elif choice == "n":
                    print(f"{Colors.YELLOW}[*] Skipped command.{Colors.RESET}")
                    messages.append({"role": "assistant", "content": json.dumps(parsed)})
                    messages.append({"role": "user", "content": "Command execution skipped by user. Propose an alternative or summarize."})
                    continue

            # Execute command
            exec_res = self.execute_shell_command(cmd)

            # Record turn in conversation
            messages.append({"role": "assistant", "content": json.dumps(parsed)})
            exec_feedback = (
                f"Command: {cmd}\n"
                f"Exit Code: {exec_res['returncode']}\n"
                f"Stdout:\n{exec_res['stdout']}\n"
                f"Stderr:\n{exec_res['stderr']}\n"
                f"Elapsed: {exec_res['elapsed_ms']}ms"
            )
            messages.append({"role": "user", "content": f"Command Result:\n{exec_feedback}\n\nAnalyze this output and decide the next step."})

        if step >= self.max_steps:
            print(f"{Colors.YELLOW}[!] Reached maximum limit of {self.max_steps} steps.{Colors.RESET}")


# ---------------------------------------------------------------------------
# Interactive REPL Prompt
# ---------------------------------------------------------------------------
def interactive_repl(agent: AutonomousLinuxAgent):
    print_banner()
    print(f"{Colors.GREEN}[+] Host Environment Initialized:{Colors.RESET}")
    print(f"    - System: {agent.env.get('distro', agent.env.get('platform'))}")
    print(f"    - User: {agent.env.get('user')} (Root: {agent.env.get('is_root')})")
    print(f"    - CWD: {agent.env.get('cwd')}")
    print(f"    - Mode: {'Autonomous (Runs commands without asking)' if agent.auto_mode else 'Interactive (Asks before running)'}")
    print(f"\n{Colors.GRAY}Type your objective (e.g. 'audit open ports', 'find top cpu consumers', 'check kernel version'). Type 'exit' to quit.{Colors.RESET}\n")

    while True:
        try:
            prompt_str = f"{Colors.CYAN}nighthawk-ai{Colors.RESET}@{Colors.MAGENTA}linux{Colors.RESET}:{Colors.BLUE}{os.getcwd()}{Colors.RESET}$ "
            goal = input(prompt_str).strip()
            if not goal:
                continue
            if goal.lower() in ("exit", "quit", "q"):
                print(f"{Colors.GREEN}Exiting NightHawk Linux Controller. Goodbye!{Colors.RESET}")
                break
            if goal.lower() == "clear":
                os.system("clear" if os.name != "nt" else "cls")
                continue

            agent.run_goal(goal)

        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.YELLOW}[*] Interrupted. Exiting...{Colors.RESET}")
            break


# ---------------------------------------------------------------------------
# CLI Argument Parser & Entrypoint
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="NightHawk AI - Autonomous Linux Controller powered by NVIDIA NIM (z-ai/glm-5.3 with Flash Fallback)"
    )
    parser.add_argument("goal", nargs="?", default=None, help="The goal or task for the AI to execute on Linux")
    parser.add_argument("-y", "--auto", action="store_true", help="Autonomous mode: execute commands without manual confirmation")
    parser.add_argument("-k", "--api-key", default=None, help="NVIDIA API Key (overrides NVIDIA_API_KEY env var)")
    parser.add_argument("-m", "--model", default=DEFAULT_PRIMARY_MODEL, help=f"Primary model (default: {DEFAULT_PRIMARY_MODEL})")
    parser.add_argument("-f", "--fallback-model", default=DEFAULT_FALLBACK_MODEL, help=f"Fallback model (default: {DEFAULT_FALLBACK_MODEL})")
    parser.add_argument("--timeout", type=float, default=25.0, help="Per-request timeout in seconds before fallback (default: 25s)")
    parser.add_argument("--max-steps", type=int, default=20, help="Maximum number of command execution steps (default: 20)")

    args = parser.parse_args()

    client = NvidiaNIMClient(
        api_key=args.api_key,
        primary_model=args.model,
        fallback_model=args.fallback_model,
        timeout=args.timeout
    )

    agent = AutonomousLinuxAgent(
        client=client,
        auto_mode=args.auto,
        max_steps=args.max_steps
    )

    if args.goal:
        print_banner()
        agent.run_goal(args.goal)
    else:
        interactive_repl(agent)


if __name__ == "__main__":
    main()

#__EMBEDDED_PYTHON_END__
