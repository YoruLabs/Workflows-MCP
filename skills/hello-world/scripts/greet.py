"""
Hello World Greeting Script

A simple script that generates personalized greetings.
Part of the hello-world example skill.
"""

import sys
import json
from datetime import datetime


def run(params: dict = None) -> dict:
    """
    Generate a personalized greeting.
    
    Args:
        params: Optional dictionary with:
            - name (str): Name to greet (default: "World")
            - uppercase (bool): Whether to uppercase the greeting (default: False)
    
    Returns:
        dict: The greeting result with status, greeting, and timestamp
    """
    params = params or {}
    
    name = params.get("name", "World")
    uppercase = params.get("uppercase", False)
    
    greeting = f"Hello, {name}!"
    
    if uppercase:
        greeting = greeting.upper()
    
    return {
        "status": "success",
        "greeting": greeting,
        "timestamp": datetime.now().isoformat(),
        "params_received": params
    }


if __name__ == "__main__":
    # Allow passing params as JSON via command line
    params = {}
    if len(sys.argv) > 1:
        try:
            params = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print(json.dumps({"status": "error", "message": "Could not parse params as JSON"}))
            sys.exit(1)
    
    result = run(params)
    print(json.dumps(result, indent=2, default=str))
