"""
Tests for the POST /api/restocking-orders endpoint.
"""


SAMPLE_ITEMS = [
    {
        "item_sku": "WDG-001",
        "item_name": "Industrial Widget Type A",
        "quantity": 100,
        "unit_cost": 12.50
    },
    {
        "item_sku": "PCB-001",
        "item_name": "Single Layer PCB Assembly",
        "quantity": 50,
        "unit_cost": 24.99
    }
]


class TestRestockingOrders:
    def test_create_restocking_order_returns_201(self, client):
        response = client.post("/api/restocking-orders", json={"items": SAMPLE_ITEMS})
        assert response.status_code == 201

    def test_created_order_appears_in_get_orders(self, client):
        # Create the restocking order
        post_response = client.post("/api/restocking-orders", json={"items": SAMPLE_ITEMS})
        assert post_response.status_code == 201
        created = post_response.json()

        # Verify it shows up in the orders list
        get_response = client.get("/api/orders")
        assert get_response.status_code == 200
        order_numbers = [o["order_number"] for o in get_response.json()]
        assert created["order_number"] in order_numbers

    def test_lead_time_days_in_valid_range(self, client):
        response = client.post("/api/restocking-orders", json={"items": SAMPLE_ITEMS})
        assert response.status_code == 201
        lead_time = response.json()["lead_time_days"]
        assert 3 <= lead_time <= 14

    def test_order_type_is_restocking(self, client):
        response = client.post("/api/restocking-orders", json={"items": SAMPLE_ITEMS})
        assert response.status_code == 201
        assert response.json()["order_type"] == "restocking"

    def test_missing_items_returns_422(self, client):
        response = client.post("/api/restocking-orders", json={})
        assert response.status_code == 422
