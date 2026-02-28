from locust import HttpUser, task, between
import random

class BookstoreUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Register and login before running tests"""
        email = f"user_{random.randint(1000, 9999)}@example.com"
        password = "testpass123"
        
        # Register
        register_resp = self.client.post(
            "http://api-gateway:8000/auth/register",
            json={
                "email": email,
                "password": password,
                "name": f"Test User {random.randint(1, 100)}"
            },
            name="auth/register"
        )
        
        if register_resp.status_code == 200:
            self.token = register_resp.json().get("access_token")
            self.user_email = email
        else:
            # User exists, try login
            login_resp = self.client.post(
                "http://api-gateway:8000/auth/login",
                data={"username": email, "password": password},
                name="auth/login"
            )
            if login_resp.status_code == 200:
                self.token = login_resp.json().get("access_token")
                self.user_email = email
    
    @task(3)
    def list_books(self):
        """Browse books catalog"""
        self.client.get("http://api-gateway:8000/books", name="books/list")
    
    @task(2)
    def view_inventory(self):
        """Check inventory levels"""
        self.client.get("http://api-gateway:8000/inventory", name="inventory/list")
    
    @task(5)
    def create_order(self):
        """Create a new order"""
        headers = {"Authorization": f"Bearer {self.token}"} if hasattr(self, 'token') else {}
        book_id = random.randint(1, 4)
        quantity = random.randint(1, 5)
        
        self.client.post(
            "http://api-gateway:8000/orders",
            json={"book_id": book_id, "quantity": quantity},
            headers=headers,
            name="orders/create"
        )
    
    @task(2)
    def list_orders(self):
        """View user's orders"""
        headers = {"Authorization": f"Bearer {self.token}"} if hasattr(self, 'token') else {}
        self.client.get(
            "http://api-gateway:8000/orders",
            headers=headers,
            name="orders/list"
        )
