"""Exercise the real acknowledgement route with an isolated in-memory database."""
import hashlib
from datetime import datetime, timedelta, timezone
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.auth import COOKIE_NAME
from backend.app.db import Base, get_db
from backend.app.main import acknowledge_alert
from backend.app.models import Alert, Event, Setting, User, Session as LoginSession


class AcknowledgementTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.addCleanup(engine.dispose)
        self.db = Session(engine)
        self.addCleanup(self.db.close)
        self.alert = Alert(device_id='test', title='Test alarm', detail='Test condition', severity='warning', status='active')
        self.db.add(self.alert)
        self.db.commit()
        app = FastAPI()
        app.add_api_route('/api/alerts/{alert_id}/acknowledge', acknowledge_alert, methods=['POST'])
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def authenticate(self, role):
        self.db.add(Setting(key='auth', value_json='{"enabled":true}'))
        user = User(username=role, password_hash='unused', role=role)
        self.db.add(user)
        self.db.flush()
        self.db.add(LoginSession(user_id=user.id, token_hash=hashlib.sha256(b'test-token').hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        self.db.commit()
        self.client.cookies.set(COOKIE_NAME, 'test-token')
        return user.id

    def acknowledge(self, alert_id=None):
        return self.client.post(f'/api/alerts/{alert_id or self.alert.id}/acknowledge', json={'comment': ' Reviewed '})

    def test_login_disabled_and_repeat(self):
        result = self.acknowledge()
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIsNotNone(result.json()['acknowledged_at'])
        self.assertIsNone(result.json()['acknowledged_by'])
        self.assertEqual(result.json()['acknowledgement_comment'], 'Reviewed')
        self.assertEqual(result.json()['status'], 'active')
        self.assertEqual(self.acknowledge().status_code, 200)
        self.assertEqual(len(self.db.scalars(select(Event)).all()), 1)

    def test_admin_identity(self):
        user_id = self.authenticate('admin')
        result = self.acknowledge()
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['acknowledged_by'], user_id)

    def test_viewer_denied(self):
        self.authenticate('viewer')
        self.assertEqual(self.acknowledge().status_code, 403)
        self.assertIsNone(self.alert.acknowledged_at)

    def test_login_required(self):
        self.db.add(Setting(key='auth', value_json='{"enabled":true}'))
        self.db.commit()
        self.assertEqual(self.acknowledge().status_code, 401)

    def test_missing_and_resolved(self):
        self.assertEqual(self.acknowledge(999).status_code, 404)
        self.alert.status = 'resolved'
        self.db.commit()
        self.assertEqual(self.acknowledge().status_code, 409)


if __name__ == '__main__':
    unittest.main()
