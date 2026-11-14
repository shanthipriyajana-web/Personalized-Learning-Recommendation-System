"""
Automated Test Suite: Data Validation & Anomaly Detection Benchmarks.
"""

from django.test import TestCase
from learning_system.models import Skill, SkillPrerequisite
from learning_system.services.prerequisite_service import PrerequisiteService
from learning_system.services.validation_service import ValidationService


class ValidationSuiteTests(TestCase):
    def test_dag_cycle_detection(self):
        """
        DFS cycle detection identifies loops in skill graph.
        """
        s1 = Skill.objects.create(skill_id='SKL-C1', name='Skill A', code='SKA', category='Test')
        s2 = Skill.objects.create(skill_id='SKL-C2', name='Skill B', code='SKB', category='Test')
        s3 = Skill.objects.create(skill_id='SKL-C3', name='Skill C', code='SKC', category='Test')

        # Create cycle: A -> B -> C -> A
        SkillPrerequisite.objects.create(parent_skill=s2, prerequisite_skill=s1)
        SkillPrerequisite.objects.create(parent_skill=s3, prerequisite_skill=s2)
        SkillPrerequisite.objects.create(parent_skill=s1, prerequisite_skill=s3)

        cycles = PrerequisiteService.detect_skill_cycles()
        self.assertTrue(len(cycles) > 0)

    def test_validation_suite_executes_cleanly(self):
        """
        Full validation suite runs and returns all required metric fields.
        """
        metrics = ValidationService.run_full_validation_suite()
        self.assertIn('evaluation_timestamp', metrics)
        self.assertIn('counts', metrics)
        self.assertIn('metrics', metrics)
        self.assertIn('prerequisite_compliance_rate', metrics['metrics'])
        self.assertIn('pk_uniqueness_rate', metrics['metrics'])
        self.assertIn('fk_integrity_rate', metrics['metrics'])
