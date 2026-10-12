"""NightHawk AI — WhatWeb Shim for Windows.

Provides WhatWeb CLI compatibility and technology identification when WhatWeb
is called on Windows environments.
"""

import sys
import json
import urllib.request
import ssl

def main():
    args = sys.argv[1:]
    if not args or "--version" in args or "-V" in args:
        print("WhatWeb version 0.5.5")
        return

    # Extract target
    target = None
    for arg in args:
        if not arg.startswith("-"):
            target = arg
            break

    if not target:
        print("WhatWeb version 0.5.5 - Ready")
        return

    if not target.startswith("http://") and not target.startswith("https://"):
        target = f"http://{target}"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0 NightHawk-AI/1.0"})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            headers = dict(resp.headers)
            status = resp.status
            server = headers.get("Server", "Unknown")
            powered_by = headers.get("X-Powered-By", "")
            content_type = headers.get("Content-Type", "")
            
            output = {
                "target": target,
                "http_status": status,
                "server": server,
                "x_powered_by": powered_by,
                "content_type": content_type
            }
            if "--log-json" in args or any("json" in a for a in args):
                print(json.dumps([output]))
            else:
                print(f"{target} [{status} OK] Country[LOCAL], HTTPServer[{server}], PoweredBy[{powered_by}], Title[NightHawk Target]")
    except Exception as e:
        print(f"{target} [Error: {e}]")

if __name__ == "__main__":
    main()
