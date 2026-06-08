
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Role, Permission, RolePermission, EmployeeDetail, Directorate, Office


# ---------------------------------------------------------------------------
# New RBAC models
# ---------------------------------------------------------------------------
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('codename', 'name', 'group', 'is_active')
    list_filter = ('group', 'is_active')
    search_fields = ('codename', 'name')
    ordering = ('group', 'codename')


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    autocomplete_fields = ['permission']
    fields = ('permission', 'is_active', 'granted_by', 'granted_at')
    readonly_fields = ('granted_at',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'permission_count', 'user_count', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = [RolePermissionInline]

    def permission_count(self, obj):
        return obj.role_permissions.filter(is_active=True).count()
    permission_count.short_description = 'Permissions'

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = 'Users'


class EmployeeDetailInline(admin.StackedInline):
    model = EmployeeDetail
    fk_name = 'user'
    can_delete = False
    extra = 0


# ---------------------------------------------------------------------------
# CustomUser
# ---------------------------------------------------------------------------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'employee_id', 'username', 'email',
        'user_role', 'employee_department', 'is_active', 'is_superuser', 'last_login',
    )
    search_fields = ('employee_id', 'username', 'email', 'employee_profile__name')
    list_filter = ('user_role', 'is_active', 'is_superuser')
    inlines = [EmployeeDetailInline]

    fieldsets = (
        (None, {'fields': ('employee_id', 'password')}),
        ('Account Info', {'fields': ('username', 'email', 'office')}),
        ('Role', {'fields': ('user_role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'employee_id', 'username', 'password1', 'password2',
                'email', 'office', 'user_role',
            ),
        }),
    )

    def employee_department(self, obj):
        if getattr(obj, 'employee_profile', None):
            return obj.employee_profile.department
        return None
    employee_department.short_description = 'Department'


@admin.register(EmployeeDetail)
class EmployeeDetailAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'name', 'user_email', 'position', 'level')
    search_fields = ('employee_id', 'name', 'user__email')

    def user_email(self, obj):
        # `user` is a nullable OneToOne: ERP-imported employees have no login
        # account yet. Fall back to the employee's own email when unlinked.
        if obj.user_id:
            return obj.user.email
        return obj.email
    user_email.short_description = 'Email'


@admin.register(Directorate)
class DirectorateAdmin(admin.ModelAdmin):
    list_display = ('name', 'office_count')
    search_fields = ('name',)

    def office_count(self, obj):
        return obj.offices.count()
    office_count.short_description = 'Offices'


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'directorate', 'created_at')
    search_fields = ('name', 'code', 'directorate__name')
    list_filter = ('directorate',)