#!/usr/bin/env python3
"""Test MLX server directly."""

import httpx

url = "http://127.0.0.1:8080/v1/chat/completions"
data = {
    "model": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 20,
}

print(f"Testing {url}...")
print(f"Model: {data['model']}")

response = httpx.post(url, json=data, timeout=30.0)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")

if response.status_code == 200:
    print("\n✅ Server works!")
else:
    print(f"\n❌ Server returned {response.status_code}")
