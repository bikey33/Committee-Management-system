from .views.tender_views import (
    ProcurementPlanTendersView,
)
from .views.import_views import (
    ProcurementImportView,
    ProcurementImportValidateView
)
from .views.activity_log_views import (
    ActivityLogListCreateView,
    ActivityLogDetailView,
    create_activity_log,
    activity_analytics,
    get_recent_activities,
    get_user_activities,
    get_activities_by_action,
    get_critical_activities,
    export_activity_logs
)
from .views.risk_views import (
    RiskListCreateView,
    RiskDetailView,
    bulk_risk_actions,
    risk_analytics,
    risk_dashboard,
    update_risk_status,
    get_risk_matrix
)
from .views.progress_views import (
    ProgressOverviewView,
    update_progress,
    calculate_auto_progress,
    progress_analytics,
    bulk_progress_update
)
from .views.final_overview_views import FinalOverviewView
from .views.notification_views import (
    NotificationListCreateView,
    NotificationDetailView,
    mark_notification_as_read,
    dismiss_notification,
    mark_all_notifications_as_read,
    get_notification_stats
)
from .views.document_views import (
    DocumentListCreateView,
    DocumentDetailView,
    download_document,
    create_document_version
)
from .views.document_category_views import (
    DocumentCategoryListCreateView,
    DocumentCategoryDetailView,
)
from .views.stakeholder_views import (
    StakeholderListCreateView,
    StakeholderDetailView,
    record_stakeholder_activity,
    update_notification_preferences,
    bulk_stakeholder_actions,
    stakeholder_statistics,
    get_stakeholders_by_role,
    get_primary_contacts,
    get_approvers,
)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProcurementPlanViewSet,
    QuarterlyTargetViewSet,
    StageHistoryViewSet,
    TimelineViewSet,
    ProcurementRiskViewSet,
    ApprovalWorkflowViewSet,
    ApprovalWorkflowDependencyViewSet,
    ActivityLogViewSet,
    PerformanceMetricViewSet,
    ExternalIntegrationViewSet,
    DashboardMetricsView,
)

from .views.budget_views import BudgetViewSet

router = DefaultRouter()
router.register(r'plans', ProcurementPlanViewSet, basename='procurementplan')
router.register(r'quarterly-targets', QuarterlyTargetViewSet, basename='quarterlytarget')
router.register(r'stage-history', StageHistoryViewSet, basename='stagehistory')
router.register(r'timelines', TimelineViewSet, basename='timeline')
router.register(r'risks', ProcurementRiskViewSet, basename='procurementrisk')
router.register(r'approval-workflows', ApprovalWorkflowViewSet, basename='approvalworkflow')
router.register(r'approval-workflow-dependencies', ApprovalWorkflowDependencyViewSet,
                basename='approvalworkflowdependency')
router.register(r'activity-logs', ActivityLogViewSet, basename='activitylog')
router.register(r'performance-metrics', PerformanceMetricViewSet, basename='performancemetric')
router.register(r'integrations', ExternalIntegrationViewSet, basename='externalintegration')

# Add stakeholder management URLs

# Add document management URLs

# Import additional view classes

app_name = 'procurement'

urlpatterns = [
    path('', include(router.urls)),

    # Budget management URLs
    path('plans/<int:pk>/budget/', BudgetViewSet.as_view({'get': 'budget'}), name='budget-overview'),
    path('plans/<int:pk>/budget/breakdown/', BudgetViewSet.as_view({'get': 'breakdown'}), name='budget-breakdown'),
    path('plans/<int:pk>/budget/revisions/',
         BudgetViewSet.as_view({'get': 'revisions', 'post': 'revisions'}), name='budget-revisions'),
    path('plans/<int:pk>/budget/revisions/<str:revision_id>/approve/',
         BudgetViewSet.as_view({'post': 'approve_revision'}), name='budget-approve-revision'),
    path('plans/<int:pk>/budget/revisions/<str:revision_id>/reject/',
         BudgetViewSet.as_view({'post': 'reject_revision'}), name='budget-reject-revision'),
    path('plans/<int:pk>/budget/variance-analysis/',
         BudgetViewSet.as_view({'get': 'variance_analysis'}), name='budget-variance'),
    path('plans/<int:pk>/budget/spending/', BudgetViewSet.as_view({'get': 'spending'}), name='budget-spending'),
    path('plans/<int:pk>/budget/alerts/', BudgetViewSet.as_view({'get': 'alerts'}), name='budget-alerts'),
    path('plans/<int:pk>/budget/metrics/', BudgetViewSet.as_view({'get': 'metrics'}), name='budget-metrics'),
    path('plans/<int:pk>/budget/export/', BudgetViewSet.as_view({'get': 'export'}), name='budget-export'),

    # Tender-related URLs
    path('plans/<int:id>/tenders/', ProcurementPlanTendersView.as_view(), name='procurement-plan-tenders'),

    # Stakeholder management URLs
    path('stakeholders/', StakeholderListCreateView.as_view(), name='stakeholder-list-create'),
    path('stakeholders/<int:pk>/', StakeholderDetailView.as_view(), name='stakeholder-detail'),
    path('stakeholders/<int:pk>/activity/', record_stakeholder_activity, name='stakeholder-activity'),
    path('stakeholders/<int:pk>/notifications/', update_notification_preferences, name='stakeholder-notifications'),
    path('stakeholders/bulk-actions/', bulk_stakeholder_actions, name='stakeholder-bulk-actions'),
    path('stakeholders/statistics/', stakeholder_statistics, name='stakeholder-statistics'),
    path('stakeholders/by-role/', get_stakeholders_by_role, name='stakeholders-by-role'),
    path('stakeholders/primary-contacts/', get_primary_contacts, name='stakeholders-primary-contacts'),
    path('stakeholders/approvers/', get_approvers, name='stakeholders-approvers'),

    # Document management URLs
    path('documents/', DocumentListCreateView.as_view(), name='document-list-create'),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<int:pk>/download/', download_document, name='document-download'),
    path('documents/<int:pk>/create-version/', create_document_version, name='document-create-version'),

    # Document category/type management URLs
    path('document-types/', DocumentCategoryListCreateView.as_view(), name='document-type-list-create'),
    path('document-types/<int:pk>/', DocumentCategoryDetailView.as_view(), name='document-type-detail'),

    # Notification management URLs
    path('notifications/', NotificationListCreateView.as_view(), name='notification-list-create'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/<int:pk>/read/', mark_notification_as_read, name='notification-read'),
    path('notifications/<int:pk>/dismiss/', dismiss_notification, name='notification-dismiss'),
    path('notifications/mark-all-read/', mark_all_notifications_as_read, name='notifications-mark-all-read'),
    path('notifications/stats/', get_notification_stats, name='notification-stats'),

    # Progress management URLs
    path('plans/<int:pk>/progress/', ProgressOverviewView.as_view(), name='progress-overview'),
    path('plans/<int:pk>/final-overview/', FinalOverviewView.as_view(), name='final-overview'),
    path('plans/<int:pk>/progress/update/', update_progress, name='progress-update'),
    path('plans/<int:pk>/progress/calculate/', calculate_auto_progress, name='progress-calculate'),
    path('progress/analytics/', progress_analytics, name='progress-analytics'),
    path('progress/bulk-update/', bulk_progress_update, name='progress-bulk-update'),
    path('dashboard/metrics/', DashboardMetricsView.as_view(), name='dashboard-metrics'),

    # Risk management URLs
    path('risks/', RiskListCreateView.as_view(), name='risk-list-create'),
    path('risks/<int:pk>/', RiskDetailView.as_view(), name='risk-detail'),
    path('risks/bulk-actions/', bulk_risk_actions, name='risk-bulk-actions'),
    path('risks/analytics/', risk_analytics, name='risk-analytics'),
    path('risks/dashboard/', risk_dashboard, name='risk-dashboard'),
    path('risks/<int:pk>/status/', update_risk_status, name='risk-status-update'),
    path('risks/matrix/', get_risk_matrix, name='risk-matrix'),

    # Activity log management URLs
    path('activity-logs/', ActivityLogListCreateView.as_view(), name='activity-log-list-create'),
    path('activity-logs/<int:pk>/', ActivityLogDetailView.as_view(), name='activity-log-detail'),
    path('activity-logs/create/', create_activity_log, name='activity-log-create'),
    path('activity-logs/analytics/', activity_analytics, name='activity-log-analytics'),
    path('activity-logs/recent/', get_recent_activities, name='activity-log-recent'),
    path('activity-logs/user/', get_user_activities, name='activity-log-user'),
    path('activity-logs/action/<str:action>/', get_activities_by_action, name='activity-log-by-action'),
    path('activity-logs/critical/', get_critical_activities, name='activity-log-critical'),
    path('activity-logs/export/', export_activity_logs, name='activity-log-export'),



    # Import URLs
    path('import/', ProcurementImportView.as_view(), name='procurement-import'),
    path('import/validate/', ProcurementImportValidateView.as_view(), name='procurement-import-validate'),
]
