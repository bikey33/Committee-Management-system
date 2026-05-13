from django.contrib import admin
from django.db.models import Q
from .models import Committee, CommitteeMembership, CommitteeRole
from users.models import CustomUser

@admin.register(CommitteeMembership)
class CommitteeMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'committee', 'get_committee_role')
    list_filter = ('committee_role',)
    search_fields = ('user__employee_id', 'user__username', 'committee__name')
    autocomplete_fields = ('user', 'committee')
    ordering = ('committee__name',)

    def get_committee_role(self, obj):
        role = CommitteeRole.objects.filter(value=obj.committee_role).first()
        return role.label if role else obj.committee_role
    get_committee_role.short_description = 'Role'

class CommitteeMembershipInline(admin.TabularInline):
    model = CommitteeMembership
    extra = 1
    fields = ('user', 'committee_role')
    autocomplete_fields = ('user',)

@admin.register(CommitteeRole)
class CommitteeRoleAdmin(admin.ModelAdmin):
    list_display = ('label', 'value', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('label', 'value')
    ordering = ('sort_order', 'label')

@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    list_display = ('name', 'formation_date', 'created_by', 'should_notify')
    list_filter = ('should_notify', 'formation_date')
    search_fields = ('name', 'purpose', 'created_by__employee_id', 'created_by__username')
    inlines = [CommitteeMembershipInline]
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-formation_date',)
    list_select_related = ('created_by',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        if user.is_superuser or (user.role and user.role.role_name == 'SUPERADMIN'):
            return qs

        return qs.filter(
            Q(memberships__user=user) |
            Q(created_by=user) |
            Q(created_by__role__in=user.get_allowed_roles())
        ).distinct()

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            queryset |= self.model.objects.filter(
                memberships__user__employee_id__icontains=search_term
            ).distinct()
        return queryset, use_distinct
