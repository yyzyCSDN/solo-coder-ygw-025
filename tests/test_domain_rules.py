import unittest
from cleanroom.rules import DomainRules
class DomainRuleTests(unittest.TestCase):
    def test_room_grade(self): self.assertEqual(DomainRules.room_grade("a"),"A")
    def test_particle_count(self):
        with self.assertRaises(ValueError): DomainRules.particle_count(-1)
