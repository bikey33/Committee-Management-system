from django.contrib import admin
from .models import (
    ProcurementPlan, QuarterlyTarget, StageHistory, Timeline, 
    ProcurementStakeholder, ExternalIntegration
)

class StageHistoryInline(admin.TabularInline):
    model = StageHistory
    extra = 0
    fields = ['previous_stage', 'new_stage', 'changed_by', 'changed_at', 'notes']
    readonly_fields = ['changed_at']
    ordering = ['-changed_at']

class QuarterlyTargetInline(admin.TabularInline):
    model = QuarterlyTarget
    extra = 1
    fields = ['quarter', 'target_details', 'status', 'created_at']
    readonly_fields = ['created_at']

class TimelineInline(admin.TabularInline):
    model = Timeline
    extra = 0
    fields = [
        'stage', 'planned_start_date', 'planned_end_date', 
        'actual_start_date', 'actual_end_date', 'status',
        'is_milestone', 'is_critical_path', 'buffer_days'
    ]
    readonly_fields = ['status']
    ordering = ['planned_start_date']

class ProcurementStakeholderInline(admin.TabularInline):
    model = ProcurementStakeholder
    extra = 0
    fields = [
        'user', 'role', 'involvement_level', 'authority_level', 
        'primary_contact', 'status', 'contact_priority'
    ]
    readonly_fields = ['assigned_at', 'last_activity_date']
    ordering = ['contact_priority', 'role']

@admin.register(StageHistory)
class StageHistoryAdmin(admin.ModelAdmin):
    list_display = ['procurement_plan', 'previous_stage', 'new_stage', 'changed_by', 'changed_at']
    list_filter = ['new_stage', 'previous_stage', 'changed_at']
    search_fields = ['procurement_plan__policy_number', 'procurement_plan__project_name', 'notes']
    readonly_fields = ['changed_at']
    ordering = ['-changed_at']

@admin.register(ProcurementPlan)
class ProcurementPlanAdmin(admin.ModelAdmin):
    list_display = [
        'policy_number', 'project_name', 'department', 'stage', 'status', 
        'priority', 'progress_percentage', 'estimated_cost', 'budget', 'created_at'
    ]
    list_filter = [
        'department', 'stage', 'status', 'priority', 'created_at', 
        'planned_start_date', 'planned_end_date'
    ]
    search_fields = ['policy_number', 'project_name', 'project_description']
    inlines = [QuarterlyTargetInline, TimelineInline, ProcurementStakeholderInline, StageHistoryInline]
    readonly_fields = [
        'created_at', 'updated_at', 'stage_updated_at', 'proposed_budget_percentage',
        'progress_percentage'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('policy_number', 'department', 'dept_index', 'project_name', 'project_description')
        }),
        ('Financial Details', {
            'fields': ('estimated_cost', 'budget', 'proposed_budget_percentage')
        }),
        ('Status & Progress', {
            'fields': ('stage', 'status', 'priority', 'progress_percentage')
        }),
        ('Timeline', {
            'fields': (
                'planned_start_date', 'planned_end_date', 
                'actual_start_date', 'actual_end_date',
                'next_milestone_date', 'next_milestone_description'
            )
        }),
        ('Relationships', {
            'fields': ('owner', 'committee')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'stage_updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'committee')

@admin.register(QuarterlyTarget)
class QuarterlyTargetAdmin(admin.ModelAdmin):
    list_display = ['procurement_plan', 'quarter', 'status', 'created_at']
    list_filter = ['quarter', 'status', 'created_at']
    search_fields = ['procurement_plan__policy_number', 'target_details']

@admin.register(Timeline)
class TimelineAdmin(admin.ModelAdmin):
    list_display = [
        'procurement_plan', 'stage', 'planned_start_date', 'planned_end_date',
        'status', 'is_milestone', 'is_critical_path', 'is_overdue'
    ]
    list_filter = [
        'stage', 'status', 'is_milestone', 'is_critical_path', 
        'planned_start_date', 'auto_calculated'
    ]
    search_fields = ['procurement_plan__policy_number', 'procurement_plan__project_name', 'milestone_description']
    readonly_fields = ['created_at', 'updated_at', 'is_overdue']
    fieldsets = (
        ('Basic Information', {
            'fields': ('procurement_plan', 'stage', 'milestone_description')
        }),
        ('Timeline', {
            'fields': (
                'planned_start_date', 'planned_end_date',
                'actual_start_date', 'actual_end_date',
                'status'
            )
        }),
        ('Properties', {
            'fields': ('is_milestone', 'is_critical_path', 'buffer_days', 'auto_calculated')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_overdue(self, obj):
        return obj.is_overdue()
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('procurement_plan')

@admin.register(ProcurementStakeholder)
class ProcurementStakeholderAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'procurement_plan', 'role', 'involvement_level', 
        'authority_level', 'primary_contact', 'status', 'assigned_at'
    ]
    list_filter = [
        'role', 'involvement_level', 'authority_level', 'status', 
        'primary_contact', 'assigned_at'
    ]
    search_fields = [
        'user__username', 'user__name', 'user__email',
        'procurement_plan__policy_number', 'procurement_plan__project_name'
    ]
    readonly_fields = ['assigned_at', 'created_at', 'updated_at', 'last_activity_date']
    autocomplete_fields = ['user', 'assigned_by', 'escalation_contact']
    
    fieldsets = (
        ('Basic Assignment', {
            'fields': (
                'procurement_plan', 'user', 'role', 'involvement_level',
                'status', 'assigned_by', 'assigned_at'
            )
        }),
        ('Authority & Responsibilities', {
            'fields': (
                'authority_level', 'responsibilities', 'primary_contact',
                'contact_priority'
            )
        }),
        ('Assignment Period', {
            'fields': (
                'assignment_start_date', 'assignment_end_date'
            )
        }),
        ('Communication', {
            'fields': (
                'notification_preferences', 'escalation_contact'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'documents_reviewed', 'meetings_attended', 'approvals_given',
                'last_activity_date'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'procurement_plan', 'assigned_by'
        )

@admin.register(ExternalIntegration)
class ExternalIntegrationAdmin(admin.ModelAdmin):
    list_display = [
        'system_name', 'sync_status', 'last_sync', 'is_active', 'created_at'
    ]
    list_filter = ['sync_status', 'created_at', 'last_sync']
    search_fields = ['system_name', 'api_endpoint']
    readonly_fields = ['created_at', 'updated_at', 'sync_age_days']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('system_name', 'sync_status', 'last_sync')
        }),
        ('Configuration', {
            'fields': ('api_endpoint', 'configuration')
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'sync_age_days'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'
    
    def sync_age_days(self, obj):
        return obj.sync_age_days
    sync_age_days.short_description = 'Days Since Last Sync'