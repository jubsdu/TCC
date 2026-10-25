"""Smoke test HTTP do fluxo cadastro → onboarding → home → login.
Requer as dependências de requirements.txt, incluindo Flask.
"""
import os
os.environ["DATABASE_URL"] = "sqlite://"

import unittest
from app import app, db_session
from models import User, Measurement_ia


class AppFlowTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = app.test_client()

    def tearDown(self):
        db_session.remove()

    def test_registration_onboarding_and_existing_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/register", data={
            "name": "Conta de teste",
            "phone": "11999999999",
            "email": "flow-test@example.test",
            "password": "senha12345",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/onboarding-reason"))

        response = self.client.post(
            "/onboarding-reason",
            data={"reason": "ansiedade"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["next"], "/onboarding-treatment")

        response = self.client.post("/onboarding-treatment", data={"treatment": ["psychotherapy"]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/home"))

        response = self.client.get("/home")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dados simulados para demonstra", response.data)

        response = self.client.get("/api/heart-rate/live")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["simulated"])
        self.assertGreaterEqual(payload["bpm"], 55)
        self.assertLessEqual(payload["bpm"], 120)

        self.client.get("/logout")
        response = self.client.post("/login", data={
            "email": "flow-test@example.test",
            "password": "senha12345",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/home"))

        db_session.remove()
        user = db_session.query(User).filter_by(email="flow-test@example.test").first()
        self.assertIsNotNone(user)
        self.assertTrue(user.onboarding_completed)
        self.assertGreater(db_session.query(Measurement_ia).filter_by(user_id=user.id).count(), 48)


if __name__ == "__main__":
    unittest.main()