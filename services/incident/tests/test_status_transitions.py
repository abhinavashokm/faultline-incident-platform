from itertools import product
from unittest import TestCase

from fastapi import HTTPException

from app.incidents.schemas import IncidentStatus
from app.incidents.service import validate_status_transition


class IncidentStatusTransitionTests(TestCase):
    def test_only_forward_transitions_and_reopening_are_allowed(self) -> None:
        statuses: tuple[IncidentStatus, ...] = ("open", "investigating", "mitigated", "resolved")
        allowed = set(zip(statuses, statuses[1:] + statuses[:1], strict=True))

        for current, target in product(statuses, repeat=2):
            with self.subTest(current=current, target=target):
                if (current, target) in allowed:
                    validate_status_transition(current, target)
                else:
                    with self.assertRaises(HTTPException) as raised:
                        validate_status_transition(current, target)
                    self.assertEqual(raised.exception.status_code, 409)
                    if current == target:
                        self.assertIn("already", raised.exception.detail)
                    else:
                        self.assertIn(f"from {current} to {target}", raised.exception.detail)
