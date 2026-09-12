import tempfile
import unittest

from cleanroom import CleanroomService
from cleanroom.engine import InvalidStage


class CleanroomIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = CleanroomService(self.temp.name + "/cleanroom.db")

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def test_pressure_commissioning_records_evidence_and_idempotent_commands(self):
        first = self.service.commission_pressure("c1", {"or-a": 8, "buffer-a": 6, "corridor": 4})
        second = self.service.commission_pressure("c1", {"or-a": 8, "buffer-a": 6, "corridor": 4})
        self.assertFalse(first["safe"])
        self.assertEqual(len(first["violations"]), 2)
        self.assertTrue(all(command["duplicate"] for command in second["commands"]))

    def test_occupancy_reserves_only_when_checks_pass(self):
        job = self.service.start_occupancy("occ-1", "or-a", {"pressure": True, "particles": True})
        self.assertEqual(job["stage"], "preparation")
        self.assertEqual(self.service.store.room("or-a")["state"], "reserved")
        self.assertTrue(job["payload"]["checks"]["pressure"])

    def test_transfer_blocks_both_open_contacts_and_persists_reason(self):
        job = self.service.start_transfer("tx-1", "buffer-a", "tray-9", (True, True))
        self.assertEqual(job["stage"], "blocked")
        self.assertEqual(job["payload"]["reason"], "both-doors-open")
        self.assertEqual(self.service.store.workflow("tx-1")["payload"]["material_id"], "tray-9")

    def test_maintenance_takeover_freezes_room_and_deduplicates_command(self):
        first = self.service.maintenance_takeover("m1", "supply-1", "tech", "or-a")
        second = self.service.maintenance_takeover("m1", "supply-1", "tech", "or-a")
        self.assertEqual(self.service.store.room("or-a")["state"], "maintenance-hold")
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])

    def test_filter_health_needs_a_trend(self):
        self.service.record_reading("filter-1", "filter_resistance", 4, source="dp-a")
        self.assertEqual(self.service.assess_filter("filter-1")["status"], "unknown")
        self.service.record_reading("filter-1", "filter_resistance", 7, source="dp-a")
        result = self.service.assess_filter("filter-1")
        self.assertEqual(result["status"], "degrading")
        self.assertEqual(result["trend"], 3)

    def test_shared_air_uses_grade_weight_and_does_not_overallocate(self):
        result = self.service.allocate_air("air-1", [
            {"room": "or-a", "grade": "B", "requested": 12},
            {"room": "corridor", "grade": "D", "requested": 12},
        ], 12)
        grants = {row["room"]: row["granted"] for row in result["grants"]}
        self.assertGreater(grants["or-a"], grants["corridor"])
        self.assertLessEqual(sum(grants.values()), 12)
        self.assertEqual(len(result["commands"]), 2)

    def test_disinfection_has_checked_stage_transitions(self):
        job = self.service.start_disinfection("d1", "or-a", 30)
        contact = self.service.coordinator.workflows.advance(job["workflow_id"], "contact", door_closed=True)
        self.assertEqual(contact["revision"], 2)
        with self.assertRaises(InvalidStage):
            self.service.coordinator.workflows.advance(job["workflow_id"], "verified")

    def test_contamination_scope_follows_only_open_boundaries(self):
        result = self.service.report_contamination("i1", "or-a", {("or-a", "buffer-a")}, [1, 2])
        self.assertEqual(result["affected_rooms"], ["buffer-a", "or-a"])
        self.assertEqual(self.service.store.room("buffer-a")["state"], "isolated")
        self.assertEqual(self.service.store.room("corridor")["state"], "available")

    def test_emergency_ventilation_keeps_workflow_and_command_together(self):
        result = self.service.emergency_ventilation("e1", "or-a", True)
        self.assertEqual(result["workflow"]["stage"], "takeover")
        self.assertEqual(result["command"]["kind"], "emergency-exhaust")
        self.assertTrue(result["command"]["parameters"]["smoke"])

    def test_release_is_held_when_any_required_check_fails(self):
        result = self.service.request_release("r1", "or-a", {"pressure": True, "particles": False})
        self.assertEqual(result["stage"], "held")
        self.assertEqual(result["revision"], 2)
        self.assertFalse(result["payload"]["last_evidence"]["checks"]["particles"])

    def test_sensor_assessment_rejects_mixed_calibration_versions(self):
        self.service.record_reading("probe-1", "particles", 1, source="a", calibration_version="v1")
        self.service.record_reading("probe-1", "particles", 1.2, source="b", calibration_version="v2")
        result = self.service.assess_sensor("probe-1", "particles")
        self.assertEqual(result["status"], "conflict")
        self.assertIsNone(result["value"])
        self.assertEqual(result["sample_sequences"], [1, 2])

    def test_heat_recovery_bypasses_contamination_and_is_idempotent(self):
        first = self.service.plan_heat_recovery("h1", "recovery-1", 0.8, True)
        second = self.service.plan_heat_recovery("h1", "recovery-1", 0.8, True)
        self.assertTrue(first["bypass"])
        self.assertEqual(first["command"]["kind"], "bypass-heat-recovery")
        self.assertTrue(second["command"]["duplicate"])

    def test_persistent_workflow_can_be_reopened_by_new_service(self):
        self.service.start_disinfection("persist-1", "or-a", 20)
        database = self.temp.name + "/cleanroom.db"
        self.service.close()
        self.service = CleanroomService(database)
        resumed = self.service.coordinator.workflows.resume("persist-1", "dose")
        self.assertEqual(resumed["room_id"], "or-a")
        self.assertEqual(resumed["payload"]["contact_minutes"], 20)


if __name__ == "__main__":
    unittest.main()
