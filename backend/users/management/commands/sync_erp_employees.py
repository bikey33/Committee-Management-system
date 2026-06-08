"""
Sync the raw ERP staging table `employee_erp_record_master` into the
application's working employee directory (EmployeeDetail).

The ERP table is imported from an external system and treated as read-only
source data (mapped via the unmanaged users.models.ErpEmployeeRecord). This
command performs an idempotent upsert keyed on employee_id (= ERP `empno`), so
it can be re-run on every refresh of the ERP table without creating duplicates.

Usage:
    python manage.py sync_erp_employees
    python manage.py sync_erp_employees --dry-run --limit 50
"""
import datetime
import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from users.models import CustomUser, Directorate, EmployeeDetail, ErpEmployeeRecord, Office


class Command(BaseCommand):
    help = 'Upsert ERP employee records (employee_erp_record_master) into EmployeeDetail.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Compute and report changes without writing to the database.',
        )
        parser.add_argument(
            '--limit', type=int, default=None,
            help='Only process the first N ERP rows (useful for testing).',
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(value):
        """Normalise a raw cell to a stripped non-empty string or None."""
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() == 'nan':
            return None
        return text

    @staticmethod
    def _truncate(value, length):
        if value is None:
            return None
        return value[:length]

    @classmethod
    def _office_name(cls, raw):
        """Normalise a raw work_office cell into an Office name (trim, collapse
        internal whitespace, cap at the model's max_length)."""
        cleaned = cls._clean(raw)
        if not cleaned:
            return None
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cls._truncate(cleaned, 200)

    def _build_name(self, rec):
        parts = [
            self._clean(rec.title),
            self._clean(rec.first_name),
            self._clean(rec.middle_names),
            self._clean(rec.last_name),
        ]
        name = ' '.join(p for p in parts if p)
        name = re.sub(r'\s+', ' ', name).strip()
        return name or None

    def generate_email(self, first_name, last_name, employee_id, existing_emails):
        """Deterministic fallback email when the ERP email is missing/duplicate.

        Mirrors the convention in users/management/commands/import_users.py:
        firstname.lastname@ntc.net.np, falling back to appending the employee_id.
        """
        first = re.sub(r'\s+', ' ', (first_name or '').strip()).lower().replace(' ', '.')
        last = re.sub(r'\s+', ' ', (last_name or '').strip()).lower().replace(' ', '.')
        if not first and not last:
            first = f'employee{employee_id}'

        base = f"{first}.{last}@ntc.net.np".replace('..', '.').lstrip('.')
        if base not in existing_emails:
            return base

        emp = f"{first}.{last}{employee_id}@ntc.net.np".replace('..', '.').lstrip('.')
        if emp not in existing_emails:
            return emp

        # Last resort: guaranteed-unique synthetic address.
        return f"employee{employee_id}@ntc.net.np"

    def _resolve_email(self, rec, employee_id, existing_emails, own_email):
        """Resolve a stable, unique email for this employee.

        `own_email` is the address already stored for this employee_id (or None
        on first import). An email is "taken" only if it belongs to a *different*
        employee, so re-running the sync never regenerates a record's own email.
        """
        erp_email = self._clean(rec.email_address)
        if erp_email:
            erp_email = erp_email.lower()
            if erp_email == own_email or erp_email not in existing_emails:
                return erp_email
        # ERP email missing or collides with another employee: keep the
        # previously assigned email if we have one, otherwise generate a new one.
        if own_email:
            return own_email
        return self.generate_email(
            self._clean(rec.first_name), self._clean(rec.last_name),
            employee_id, existing_emails,
        )

    @staticmethod
    def _to_datetime(date_value):
        if not date_value:
            return None
        if isinstance(date_value, datetime.datetime):
            dt = date_value
        elif isinstance(date_value, datetime.date):
            dt = datetime.datetime.combine(date_value, datetime.time.min)
        else:
            return None
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no database writes will be performed.'))

        queryset = ErpEmployeeRecord.objects.all().order_by('empno')
        if limit:
            queryset = queryset[:limit]

        # Pre-load all emails already in use so generated/ERP emails never collide,
        # and remember each employee's own current email so re-runs stay stable.
        email_by_id = {
            eid: (email.lower() if email else None)
            for eid, email in EmployeeDetail.objects.values_list('employee_id', 'email')
        }
        existing_emails = {e for e in email_by_id.values() if e}

        created = updated = skipped = 0

        # Office population (Strategy A): work_org_id is a stable 1:1 key for
        # work_office in this ERP table, so we upsert one Office per work_org_id
        # (code=work_org_id, name=work_office) and remember which office each
        # employee belongs to so we can link their user account afterwards.
        office_by_orgid = {}       # work_org_id -> Office instance (None in dry-run)
        emp_to_orgid = {}          # employee_id -> work_org_id
        offices_created = offices_updated = 0

        for rec in queryset.iterator():
            try:
                employee_id = self._clean(rec.empno)
                if not employee_id:
                    skipped += 1
                    self.stdout.write(self.style.ERROR(f"Skipped ERP row id={rec.pk}: empty empno"))
                    continue
                if len(employee_id) > 10:
                    skipped += 1
                    self.stdout.write(self.style.ERROR(
                        f"Skipped empno={employee_id}: exceeds employee_id max_length (10)"))
                    continue

                # Upsert this row's office (once per distinct work_org_id) and map
                # the employee to it for later user linking.
                org_id = self._truncate(self._clean(rec.work_org_id), 50)
                office_name = self._office_name(rec.work_office)
                if org_id and office_name:
                    emp_to_orgid[employee_id] = org_id
                    if org_id not in office_by_orgid:
                        if dry_run:
                            office_by_orgid[org_id] = None
                            if Office.objects.filter(code=org_id).exists():
                                offices_updated += 1
                            else:
                                offices_created += 1
                        else:
                            office, office_created = Office.objects.update_or_create(
                                code=org_id, defaults={'name': office_name},
                            )
                            office_by_orgid[org_id] = office
                            if office_created:
                                offices_created += 1
                            else:
                                offices_updated += 1

                email = self._resolve_email(
                    rec, employee_id, existing_emails, email_by_id.get(employee_id),
                )
                existing_emails.add(email)
                email_by_id[employee_id] = email

                defaults = {
                    'name':       self._truncate(self._build_name(rec), 150),
                    'email':      email,
                    'phone':      self._truncate(self._clean(rec.mobile), 15),
                    'mno':        self._truncate(self._clean(rec.mobile), 15),
                    'position':   self._truncate(self._clean(rec.job_name), 100),
                    'level':      self._truncate(self._clean(rec.grade), 10),
                    'department': self._truncate(self._clean(rec.work_office), 50),
                    'seniority':  self._to_datetime(rec.seniority_date),
                }

                if dry_run:
                    exists = EmployeeDetail.objects.filter(employee_id=employee_id).exists()
                    if exists:
                        updated += 1
                    else:
                        created += 1
                    self.stdout.write(f"[dry-run] {employee_id}: {defaults['name']} <{email}>")
                    continue

                with transaction.atomic():
                    _, was_created = EmployeeDetail.objects.update_or_create(
                        employee_id=employee_id, defaults=defaults,
                    )
                if was_created:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"Created {employee_id} ({email})"))
                else:
                    updated += 1
                    self.stdout.write(self.style.WARNING(f"Updated {employee_id} ({email})"))

            except Exception as exc:  # noqa: BLE001 - report and continue per row
                skipped += 1
                self.stdout.write(self.style.ERROR(
                    f"Error on empno={getattr(rec, 'empno', rec.pk)}: {exc}"))

        # Link each existing user account to its office (by the employee's
        # work_org_id). Only users whose office actually changes are written.
        users_linked = 0
        candidates = CustomUser.objects.filter(employee_id__in=emp_to_orgid.keys())
        if dry_run:
            for user in candidates.iterator():
                office = office_by_orgid.get(emp_to_orgid.get(user.employee_id))
                # In dry-run offices aren't created, so compare against existing rows.
                target = office or Office.objects.filter(
                    code=emp_to_orgid.get(user.employee_id)).first()
                if target and user.office_id != target.id:
                    users_linked += 1
        else:
            to_update = []
            for user in candidates.iterator():
                office = office_by_orgid.get(emp_to_orgid.get(user.employee_id))
                if office and user.office_id != office.id:
                    user.office = office
                    to_update.append(user)
            if to_update:
                CustomUser.objects.bulk_update(to_update, ['office'])
                users_linked = len(to_update)

        # Derive directorates from offices that are themselves directorates (name
        # contains "directorate") and link those offices to them. The ERP data has
        # no office->parent hierarchy, so child offices (telecom offices, IMUs,
        # departments) are intentionally left unlinked rather than guessed.
        directorates_created = 0
        offices_linked_to_dir = 0
        directorate_offices = Office.objects.filter(name__icontains='directorate')
        if dry_run:
            for office in directorate_offices.iterator():
                existing = Directorate.objects.filter(name=office.name).first()
                if not existing:
                    directorates_created += 1
                if not existing or office.directorate_id != existing.id:
                    offices_linked_to_dir += 1
        else:
            for office in directorate_offices.iterator():
                directorate, dir_created = Directorate.objects.get_or_create(name=office.name)
                if dir_created:
                    directorates_created += 1
                if office.directorate_id != directorate.id:
                    office.directorate = directorate
                    office.save(update_fields=['directorate'])
                    offices_linked_to_dir += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. employees: created={created} updated={updated} skipped={skipped}; "
            f"offices: created={offices_created} updated={offices_updated}; "
            f"users linked to office={users_linked}; "
            f"directorates created={directorates_created} "
            f"(offices linked to directorate={offices_linked_to_dir})"
            + (' (dry run)' if dry_run else '')))
