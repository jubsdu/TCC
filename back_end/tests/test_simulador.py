"""Testes sem dependência do servidor web: geração, persistência e isolamento."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import User, Measurement_ia, Activity, Measurement_pressure
from simulador_ia import seed_user_data, create_live_reading


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)
        self.db = self.factory()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_each_user_gets_persistent_independent_samples(self):
        users = []
        for number in (1, 2):
            user = User(
                name=f"Pessoa {number}",
                email=f"pessoa{number}@example.test",
                password="hash-de-teste",
                onboarding_completed=False,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            users.append(user)
            seed_user_data(self.db, user.id)

        for user in users:
            initial = self.db.query(Measurement_ia).filter_by(user_id=user.id).count()
            self.assertEqual(initial, 48)
            self.assertGreater(self.db.query(Activity).filter_by(user_id=user.id).count(), 0)
            self.assertGreater(self.db.query(Measurement_pressure).filter_by(user_id=user.id).count(), 0)
            sample = create_live_reading(self.db, user.id)
            current = self.db.query(Measurement_ia).filter_by(user_id=user.id).count()
            self.assertEqual(current, initial + 1)
            self.assertGreaterEqual(sample.bpm, 55)
            self.assertLessEqual(sample.bpm, 120)

        self.assertEqual(self.db.query(Measurement_ia).filter_by(user_id=users[0].id).count(), 49)
        self.assertEqual(self.db.query(Measurement_ia).filter_by(user_id=users[1].id).count(), 49)


if __name__ == "__main__":
    unittest.main()
