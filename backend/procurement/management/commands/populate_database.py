import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker
from users.models import CustomUser
from procurement.models import ProcurementPlan
from specification.models import Specification
from tender.models import Tender
from committee.models import Committee
from bidding.models import Bid
from evaluation.models import Evaluation
from contract.models import Contract


class Command(BaseCommand):
    help = 'Populates all tables with interconnected, realistic fake data for each procurement stage.'

    def handle(self, *args, **options):
        self.stdout.write("Starting database population with structured data...")

        fake = Faker()

        try:
            with transaction.atomic():
                self.stdout.write("Populating users...")
                users = self._create_users(fake, 10)
                if not users:
                    self.stdout.write(self.style.ERROR("Failed to create users. Aborting."))
                    return

                stages = [stage[0] for stage in ProcurementPlan.STAGE_CHOICES if stage[0] != 'complaint']

                for stage in stages:
                    self.stdout.write(self.style.SUCCESS(f"Creating data for stage: {stage}"))

                    plan = self._create_procurement_plan(fake, users, stage)
                    if not plan:
                        continue

                    if stages.index(stage) >= stages.index('specification'):
                        spec = self._create_specification(fake, plan)
                        if not spec:
                            continue

                    if stages.index(stage) >= stages.index('tender'):
                        tender = self._create_tender(fake, plan, spec)
                        if not tender:
                            continue

                    if stages.index(stage) >= stages.index('committee'):
                        committee = self._create_committee(fake, users)
                        if not committee:
                            continue
                        tender.committee = committee
                        tender.save()

                    if stages.index(stage) >= stages.index('bidding'):
                        bids = self._create_bids(fake, users, tender)

                    if stages.index(stage) >= stages.index('evaluation'):
                        if bids and committee:
                            self._create_evaluations(fake, bids, [committee])

                    if stages.index(stage) >= stages.index('contract'):
                        if bids:
                            self._create_contract(fake, tender)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))

        self.stdout.write(self.style.SUCCESS("Database population complete."))

    def _create_users(self, fake, count):
        users = []
        for _ in range(count):
            try:
                user = CustomUser.objects.create_user(
                    employee_id=fake.unique.bothify(text='EMP####'),
                    email=fake.unique.email(),
                    password='password123'
                )
                users.append(user)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating user: {e}"))
        return users

    def _create_procurement_plan(self, fake, users, stage):
        try:
            return ProcurementPlan.objects.create(
                policy_number=fake.unique.bothify(text='POL-#####-???'),
                department=random.choice(['Wireline', 'Wireless']),
                project_name=f"{stage.replace('_', ' ').title()} Project",
                project_description=fake.text(),
                estimated_cost=fake.pydecimal(left_digits=6, right_digits=2, positive=True),
                budget=fake.pydecimal(left_digits=6, right_digits=2, positive=True),
                stage=stage,
                status=random.choice([c[0] for c in ProcurementPlan.STATUS_CHOICES]),
                priority=random.choice([c[0] for c in ProcurementPlan.PRIORITY_CHOICES]),
                owner=random.choice(users),
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating procurement plan: {e}"))
            return None

    def _create_specification(self, fake, plan):
        try:
            return Specification.objects.create(
                procurement_plan=plan,
                title=f"Spec for {plan.project_name}",
                description=fake.text(),
                created_by=plan.owner
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating specification: {e}"))
            return None

    def _create_tender(self, fake, plan, spec):
        try:
            return Tender.objects.create(
                procurement_plan=plan,
                specification=spec,
                title=f"Tender for {plan.project_name}",
                description=fake.text(),
                publication_date=timezone.make_aware(fake.past_datetime()),
                closing_date=timezone.make_aware(fake.future_datetime()),
                ifb_number=fake.unique.bothify(text='IFB-#####-???')
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating tender: {e}"))
            return None

    def _create_committee(self, fake, users):
        try:
            committee = Committee.objects.create(
                name=fake.bs(),
                purpose=fake.text(),
                committee_type=random.choice(['specification', 'evaluation', 'other']),
            )
            return committee
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating committee: {e}"))
            return None

    def _create_bids(self, fake, users, tender):
        bids = []
        bidders = random.sample(list(users), k=random.randint(1, min(len(users), 5)))
        for bidder in bidders:
            try:
                bid = Bid.objects.create(
                    tender=tender,
                    bidder=bidder,
                    amount=fake.pydecimal(left_digits=5, right_digits=2, positive=True),
                    submission_date=timezone.make_aware(fake.past_datetime()),
                    created_by=bidder,
                    title=f"Bid for {tender.title}",
                    description=fake.text(),
                )
                bids.append(bid)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating bid: {e}"))
        return bids

    def _create_evaluations(self, fake, bids, committees):
        evals = []
        for bid in bids:
            try:
                evaluation = Evaluation.objects.create(
                    bid=bid,
                    committee=random.choice(committees),
                    score=random.uniform(1.0, 10.0),
                    comments=fake.text(),
                )
                evals.append(evaluation)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating evaluation: {e}"))
        return evals

    def _create_contract(self, fake, tender):
        if hasattr(tender, 'bids') and tender.bids.exists():
            winning_bid = tender.bids.order_by('amount').first()
            try:
                return Contract.objects.create(
                    bid=winning_bid,
                    contract_amount=winning_bid.amount,
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating contract: {e}"))
        return None
