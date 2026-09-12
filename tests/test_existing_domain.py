import unittest
from cleanroom.service import CleanroomService

class ExistingCleanroomTests(unittest.TestCase):
    def setUp(self):
        self.s=CleanroomService()
        for asset,kind in [("r1","room"),("r2","room"),("p1","particle_probe"),("f1","filter"),("h1","heat_recovery_unit")]: self.s.baseline.register_asset(asset,kind)
    def tearDown(self): self.s.close()
    def test_pressure_action_is_single_room(self): self.assertEqual(self.s.domain.pressure_action("r1",8,12)["basis"],"single-room")
    def test_occupancy_starts_in_preparation(self): self.assertEqual(self.s.domain.occupancy_job("o1","r1",{"pressure":True})["payload"]["phase"],"preparation")
    def test_pass_box_only_checks_two_contacts(self): self.assertFalse(self.s.domain.pass_box_policy(True,True))
    def test_maintenance_hold_is_an_audited_action(self): self.assertEqual(self.s.domain.maintenance_hold("r1","tech")["actor"],"tech")
    def test_filter_condition_is_one_threshold(self): self.assertEqual(self.s.domain.filter_condition(8,7),"alarm")
    def test_air_allocation_keeps_request_order(self): self.assertEqual(self.s.domain.allocate_air([{"room":"r1","requested":8},{"room":"r2","requested":8}],10)[1]["granted"],2)
    def test_disinfection_is_a_persistent_fixed_cycle(self): self.assertEqual(self.s.domain.disinfection_job("d1","r1",30)["payload"]["restart_policy"],"full-cycle")
    def test_incident_scope_starts_with_one_room(self): self.assertEqual(self.s.domain.contamination_incident("c1","r1",99)["payload"]["scope"],["r1"])
    def test_emergency_ventilation_records_action_and_job(self): self.assertEqual(self.s.domain.emergency_ventilation("e1","r1",True)["payload"]["phase"],"takeover")
    def test_release_uses_one_snapshot(self): self.assertEqual(self.s.domain.release_job("x1","r1",{"pressure":True})["payload"]["basis"],"single-snapshot")
    def test_sensor_assessment_uses_latest_usable(self): self.assertEqual(self.s.domain.sensor_assessment("s1","p1",[{"value":1},{"value":2}])["payload"]["value"],2)
    def test_heat_recovery_records_signal_and_job(self): self.assertEqual(self.s.domain.heat_recovery_job("hjob","h1",.7)["payload"]["basis"],"current-efficiency")
