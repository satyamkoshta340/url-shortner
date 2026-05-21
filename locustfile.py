from locust import HttpUser, task, between

class RedirectUser(HttpUser):
    # Wait 0.1 to 0.5 seconds between tasks to generate load
    wait_time = between(0.1, 0.5)
    short_code = None

    def on_start(self):
        # Create a URL to test with
        response = self.client.post("/shorten", params={"long_url": "https://www.github.com"})
        if response.status_code == 200:
            self.short_code = response.json().get("short_code")
        else:
            print(f"Failed to create short code: {response.text}")

    @task
    def redirect(self):
        if self.short_code:
            # allow_redirects=False so we only measure our own API latency
            self.client.get(f"/{self.short_code}", allow_redirects=False)
