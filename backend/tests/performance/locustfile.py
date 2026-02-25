"""
Locust load testing configuration for Network Guardian AI.

Usage:
    locust -f backend/tests/performance/locustfile.py --host http://localhost:8000

For distributed testing:
    locust -f backend/tests/performance/locustfile.py --host http://localhost:8000 --master
    locust -f backend/tests/performance/locustfile.py --host http://localhost:8000 --worker

For headless testing:
    locust -f backend/tests/performance/locustfile.py --host http://localhost:8000 --headless -u 100 -r 10 -t 60s
"""
import random
import string

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser


TEST_DOMAINS = [
    "google.com",
    "facebook.com",
    "amazon.com",
    "microsoft.com",
    "apple.com",
    "netflix.com",
    "twitter.com",
    "linkedin.com",
    "github.com",
    "stackoverflow.com",
]

SUSPICIOUS_DOMAINS = [
    "malware-test-site.com",
    "phishing-example.net",
    "suspicious-domain.xyz",
    "tracking-pixel.com",
    "ad-server.net",
]


def generate_dga_domain():
    """Generate a DGA-like domain for testing."""
    length = random.randint(10, 20)
    chars = string.ascii_lowercase + string.digits
    domain = ''.join(random.choice(chars) for _ in range(length))
    tld = random.choice(['.com', '.net', '.xyz', '.top'])
    return f"{domain}{tld}"


class NetworkGuardianUser(FastHttpUser):
    """
    Simulated user for load testing Network Guardian AI.
    Uses FastHttpUser for better performance.
    """
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a user starts."""
        self.auth_token = None
        self.domains_analyzed = 0
        
    @task(10)
    def health_check(self):
        """Check system health - high frequency."""
        self.client.get("/health", name="/health")
    
    @task(5)
    def get_system_status(self):
        """Get system intelligence - medium frequency."""
        self.client.get("/system", name="/system")
    
    @task(3)
    def analyze_normal_domain(self):
        """Analyze a normal domain - medium frequency."""
        domain = random.choice(TEST_DOMAINS)
        self.client.post(
            "/analyze",
            json={"domain": domain},
            name="/analyze [normal]"
        )
        self.domains_analyzed += 1
    
    @task(1)
    def analyze_suspicious_domain(self):
        """Analyze a suspicious domain - low frequency."""
        domain = random.choice(SUSPICIOUS_DOMAINS)
        self.client.post(
            "/analyze",
            json={"domain": domain},
            name="/analyze [suspicious]"
        )
        self.domains_analyzed += 1
    
    @task(1)
    def analyze_dga_domain(self):
        """Analyze a DGA-like domain - low frequency."""
        domain = generate_dga_domain()
        self.client.post(
            "/analyze",
            json={"domain": domain},
            name="/analyze [DGA]"
        )
        self.domains_analyzed += 1
    
    @task(3)
    def get_history(self):
        """Get analysis history - medium frequency."""
        self.client.get("/history", name="/history")
    
    @task(2)
    def chat_request(self):
        """Make a chat request - medium frequency."""
        messages = [
            "What can you do?",
            "Is google.com safe?",
            "Explain how you detect threats",
            "What is DGA?",
            "How does entropy analysis work?"
        ]
        self.client.post(
            "/chat",
            json={"message": random.choice(messages)},
            name="/chat"
        )


class AuthenticatedUser(HttpUser):
    """
    Simulated authenticated user for testing protected endpoints.
    """
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Authenticate on start."""
        response = self.client.post(
            "/auth/token",
            json={"username": "admin", "password": "admin123"}
        )
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
        else:
            self.auth_token = None
    
    @task(5)
    def get_auth_status(self):
        """Check authentication status."""
        if self.auth_token:
            self.client.get(
                "/auth/status",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                name="/auth/status"
            )
    
    @task(2)
    def get_user_profile(self):
        """Get user profile."""
        if self.auth_token:
            self.client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                name="/auth/me"
            )


class HighLoadUser(FastHttpUser):
    """
    Simulated user for stress testing with minimal wait time.
    """
    
    wait_time = between(0.1, 0.5)
    
    @task(20)
    def rapid_health_checks(self):
        """Rapid health checks for stress testing."""
        self.client.get("/health", name="/health [stress]")
    
    @task(10)
    def rapid_analyze(self):
        """Rapid analysis requests for stress testing."""
        domain = generate_dga_domain()
        self.client.post(
            "/analyze",
            json={"domain": domain},
            name="/analyze [stress]"
        )


class MetricsUser(HttpUser):
    """
    User that primarily accesses metrics endpoints.
    """
    
    wait_time = between(5, 10)
    
    @task(3)
    def get_stats(self):
        """Get system statistics."""
        self.client.get("/api/stats", name="/api/stats")
    
    @task(2)
    def get_alerts(self):
        """Get alerts."""
        self.client.get("/alerts", name="/alerts")
    
    @task(1)
    def get_database_stats(self):
        """Get database statistics."""
        self.client.get("/database/stats", name="/database/stats")


# Event listeners for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log request details for analysis."""
    if exception:
        print(f"Request failed: {name} - {exception}")
    elif response_time > 1000:
        print(f"Slow request: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("Load test starting...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("Load test completed.")
