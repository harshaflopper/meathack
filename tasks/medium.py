"""
Medium Task: Config Debugging
Capacity: 300 tokens | Cycles: 20
Scenario: Staging deployment failure — .env files, docker-compose configs,
          application error logs, and troubleshooting runbook
Goal: Find REDIS_HOST=localhost misconfiguration, fix it, restart services
"""
from tasks.base import Task


def get_medium_task() -> Task:
    return Task(
        name="config_debugging_medium",
        difficulty="medium",
        attention_capacity=300,
        max_cycles=20,
        inputs=[
            (
                '[File: .env.staging]\n'
                'DATABASE_URL=postgresql://app_user:s3cret@10.0.2.14:5432/appdb\n'
                'REDIS_HOST=localhost\n'
                'REDIS_PORT=6379\n'
                'LOG_LEVEL=debug\n'
                'API_RATE_LIMIT=100\n'
                'SESSION_TTL=3600'
            ),
            (
                '[File: docker-compose.staging.yml]\n'
                'services:\n'
                '  api:\n'
                '    image: app-api:2.14.3\n'
                '    ports: ["8080:8080"]\n'
                '    env_file: .env.staging\n'
                '    depends_on: [redis, postgres]\n'
                '  redis:\n'
                '    image: redis:7-alpine\n'
                '    ports: ["6379:6379"]\n'
                '    networks: [backend]\n'
                '  postgres:\n'
                '    image: postgres:15\n'
                '    networks: [backend]'
            ),
            (
                '[Log: api-server 2024-03-15T14:02:11Z] INFO  Starting API server v2.14.3\n'
                '[Log: api-server 2024-03-15T14:02:11Z] INFO  Connecting to Redis at localhost:6379\n'
                '[Log: api-server 2024-03-15T14:02:12Z] ERROR ConnectionRefusedError: '
                'Connection refused at localhost:6379 — retrying (1/3)\n'
                '[Log: api-server 2024-03-15T14:02:15Z] ERROR ConnectionRefusedError: '
                'Connection refused at localhost:6379 — retrying (2/3)\n'
                '[Log: api-server 2024-03-15T14:02:18Z] FATAL Max retries exceeded. Redis unavailable.'
            ),
            (
                '[File: config/redis.py]\n'
                'import os\n'
                'import redis\n'
                '\n'
                'REDIS_HOST = os.getenv("REDIS_HOST", "localhost")\n'
                'REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))\n'
                '\n'
                'cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)\n'
                '\n'
                'def ping():\n'
                '    try:\n'
                '        return cache.ping()\n'
                '    except redis.ConnectionError as e:\n'
                '        raise SystemExit(f"Redis connection failed: {e}")'
            ),
            (
                '[File: config/nginx.conf]\n'
                'upstream api_backend {\n'
                '    server api:8080;\n'
                '}\n'
                'server {\n'
                '    listen 80;\n'
                '    location / {\n'
                '        proxy_pass http://api_backend;\n'
                '        proxy_set_header Host $host;\n'
                '    }\n'
                '    location /health {\n'
                '        return 200 "OK";\n'
                '    }\n'
                '}'
            ),
            (
                '[Log: docker-network 2024-03-15T14:01:55Z] INFO  Network "backend" created\n'
                '[Log: docker-network 2024-03-15T14:01:56Z] INFO  Container "redis" attached to '
                '"backend" network with IP 172.18.0.3\n'
                '[Log: docker-network 2024-03-15T14:01:56Z] INFO  Container "postgres" attached to '
                '"backend" network with IP 172.18.0.4\n'
                '[Log: docker-network 2024-03-15T14:01:57Z] WARN  Container "api" is NOT attached '
                'to "backend" network — using default bridge'
            ),
            (
                '[Runbook: Redis Connectivity Troubleshooting]\n'
                '1. Verify REDIS_HOST in .env matches the Docker service name (should be "redis", '
                'not "localhost" in containerized deployments)\n'
                '2. Ensure both api and redis containers share the same Docker network\n'
                '3. Check firewall rules: port 6379 must be open within the network\n'
                '4. Test with: docker exec api redis-cli -h redis ping'
            ),
        ],
        final_question=(
            "Fix the issue causing the API server to fail connecting to Redis on staging. "
            "What specific configuration changes are needed?"
        ),
        expected_answers=[
            "REDIS_HOST",
            "localhost",
            "redis",
            "network",
        ],
        config_bugs={
            "REDIS_HOST": "localhost",
            "correct_value": "redis",
            "api_network": "missing backend network",
        },
        services={
            "api": "crashed",
            "redis": "running",
            "postgres": "running",
            "nginx": "running",
        },
        partial_milestones={
            "found_config_bug": ["redis_host", "localhost", ".env"],
            "found_network_issue": ["network", "backend", "not attached"],
            "found_logs": ["connectionrefused", "connection refused", "retrying"],
        },
    )
