import random
from django.core.management.base import BaseCommand
from faker import Faker
from procurement.models import ProcurementPlan
from users.models import CustomUser

class Command(BaseCommand):
    help = 'Populates the ProcurementPlan model with realistic fake data.'

    def handle(self, *args, **options):
        self.stdout.write("Starting to populate procurement plans...")
        
        fake = Faker()
        
        users = list(CustomUser.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR("No users found. Please create some users first."))
            return

        for _ in range(20):  # Create 20 fake procurement plans
            try:
                ProcurementPlan.objects.create(
                    policy_number=fake.unique.bothify(text='POL-#####-???'),
                    department=random.choice(['Wireline', 'Wireless']),
                    project_name=fake.catch_phrase(),
                    project_description=fake.text(),
                    estimated_cost=fake.pydecimal(left_digits=6, right_digits=2, positive=True),
                    budget=fake.pydecimal(left_digits=6, right_digits=2, positive=True),
                    stage=random.choice([choice[0] for choice in ProcurementPlan.STAGE_CHOICES]),
                    status=random.choice([choice[0] for choice in ProcurementPlan.STATUS_CHOICES]),
                    priority=random.choice([choice[0] for choice in ProcurementPlan.PRIORITY_CHOICES]),
                    owner=random.choice(users),
                    planned_start_date=fake.date_between(start_date='-1y', end_date='today'),
                    planned_end_date=fake.date_between(start_date='today', end_date='+1y'),
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating a procurement plan: {e}"))

        self.stdout.write(self.style.SUCCESS("Successfully populated procurement plans."))
