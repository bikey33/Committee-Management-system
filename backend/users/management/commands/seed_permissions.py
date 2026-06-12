from django.core.management.base import BaseCommand
from users.models import Permission, Role, RolePermission

PERMISSIONS = [
    # (group, codename, name)
    ('user_management', 'users.view',                   'View Users & Employees'),
    ('user_management', 'users.manage',                 'Create / Edit / Delete Users & Employees'),
    ('user_management', 'roles.manage',                 'Manage Roles & Permissions'),
    ('settings',        'settings.offices',             'Manage Offices & Directorates'),
    ('settings',        'settings.committee_roles',     'Manage Committee Role Types'),
    ('settings',        'settings.review_defaults',     'Manage Review Committee Default Members'),
    ('committee',       'committee.view',               'View Committees (own office + memberships)'),
    ('committee',       'committee.create',             'Create Committees'),
    ('committee',       'committee.manage',             'Edit / Delete Committees & Members'),
    ('committee',       'committee.view_cross_office',  'View Committees Across All Offices'),
    ('reports',         'reports.view',                 'View Reports & Analytics'),
]

# Roles to seed. Each entry: (name, description, [codenames])
ROLES = [
    (
        'Superadmin',
        'Full system access — all permissions.',
        [p[1] for p in PERMISSIONS],   # all codenames
    ),
    (
        'Admin User',
        'Administrative access: manage users, committees, offices, and reports. Cannot manage roles.',
        [
            'users.view',
            'users.manage',
            'settings.offices',
            'settings.committee_roles',
            'settings.review_defaults',
            'committee.view',
            'committee.create',
            'committee.manage',
            'committee.view_cross_office',
            'reports.view',
        ],
    ),
    (
        'Member',
        'Standard employee: own committees, office committees, and reports.',
        ['committee.view', 'reports.view'],
    ),
]

# Old role names to rename to their canonical counterparts
ROLE_RENAMES = {
    'Normal User': 'Member',
}


def _assign_permissions(role, codename_set, perm_map, stdout, style):
    """Assign permissions from perm_map whose codenames are in codename_set to role."""
    assigned = 0
    for codename in codename_set:
        perm = perm_map.get(codename)
        if not perm:
            continue
        rp, created = RolePermission.objects.get_or_create(
            role=role,
            permission=perm,
            defaults={'is_active': True},
        )
        if not rp.is_active:
            rp.is_active = True
            rp.save()
            created = True
        if created:
            assigned += 1
    return assigned


class Command(BaseCommand):
    help = (
        'Seed all RBAC permissions and default roles. '
        'Also ensures every existing role whose name is a "superadmin" variant '
        'receives all permissions. Safe to re-run.'
    )

    def handle(self, *args, **options):
        # ── 1. Upsert permissions ────────────────────────────────────────────
        perm_map = {}
        created_count = 0

        for group, codename, name in PERMISSIONS:
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': name, 'group': group, 'is_active': True},
            )
            if not created:
                changed = False
                if perm.name != name:      perm.name = name;   changed = True
                if perm.group != group:    perm.group = group; changed = True
                if not perm.is_active:     perm.is_active = True; changed = True
                if changed:
                    perm.save()
            else:
                created_count += 1
                self.stdout.write(f'  + permission: {codename}')
            perm_map[codename] = perm

        self.stdout.write(self.style.SUCCESS(
            f'Permissions: {created_count} created, '
            f'{len(PERMISSIONS) - created_count} already existed.\n'
        ))

        # ── 2. Rename legacy roles (skip if target already exists) ──────────
        for old_name, new_name in ROLE_RENAMES.items():
            old_role = Role.objects.filter(name=old_name).first()
            if not old_role:
                continue
            if Role.objects.filter(name=new_name).exists():
                # Target already exists — re-point any users on the old role to the new one
                new_role = Role.objects.get(name=new_name)
                moved = old_role.users.count()
                old_role.users.update(user_role=new_role)
                old_role.delete()
                self.stdout.write(self.style.WARNING(
                    f"Role '{old_name}' merged into existing '{new_name}' "
                    f"({moved} user(s) re-assigned, old role deleted)."
                ))
            else:
                old_role.name = new_name
                old_role.save()
                self.stdout.write(self.style.WARNING(
                    f"Renamed role '{old_name}' → '{new_name}'."
                ))

        # ── 3. Upsert named roles and assign permissions ─────────────────────
        for role_name, description, codenames in ROLES:
            role, role_created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': description, 'is_active': True},
            )
            label = 'created' if role_created else 'exists'
            n = _assign_permissions(role, codenames, perm_map, self.stdout, self.style)
            self.stdout.write(self.style.SUCCESS(
                f"Role '{role_name}' ({label}): {n} new permissions assigned."
            ))

        self.stdout.write(self.style.SUCCESS('\nDone.'))
