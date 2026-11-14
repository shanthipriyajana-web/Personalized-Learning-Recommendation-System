"""
Management command to generate synthetic educational datasets.
Usage:
  python manage.py generate_synthetic_data --mode STARTER --seed 20261022
  python manage.py generate_synthetic_data --mode FULL --seed 20261022
"""

from django.core.management.base import BaseCommand
from learning_system.services.data_generator_service import DataGeneratorService


class Command(BaseCommand):
    help = 'Generates synthetic educational dataset with fixed seed and isolated anomalies.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='STARTER',
            choices=['STARTER', 'FULL'],
            help='Generation mode: STARTER (100 learners, 1k attempts) or FULL (10k learners, 500k attempts).'
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=20261022,
            help='Deterministic integer random seed (default: 20261022).'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        seed = options['seed']

        self.stdout.write(self.style.SUCCESS(f"Executing Data Generation: mode={mode}, seed={seed}"))
        run_record = DataGeneratorService.generate_dataset(mode=mode, seed=seed, verbose=True)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully finished data generation run #{run_record.id}!\n"
            f"Learners: {run_record.learner_count}, Skills: {run_record.skill_count}, "
            f"Content: {run_record.content_count}, Attempts: {run_record.attempt_count}"
        ))
