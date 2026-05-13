# Import ViewSets from base_views.py
from .base_views import (
    ProcurementPlanViewSet,
    QuarterlyTargetViewSet,
    StageHistoryViewSet,
    TimelineViewSet,
    ProcurementRiskViewSet,
    ApprovalWorkflowViewSet,
    ApprovalWorkflowDependencyViewSet,
    ActivityLogViewSet,
    PerformanceMetricViewSet,
)
from .procurement_plan_views import (
    ProcurementPlanListCreateView,
    ProcurementPlanDetailView
)
from .timeline_views import (
    TimelineListCreateView,
    TimelineDetailView
)
from .document_views import (
    DocumentListCreateView,
    DocumentDetailView,
    download_document,
    create_document_version
)
from .notification_views import (
    NotificationListCreateView,
    NotificationDetailView,
    mark_notification_as_read,
    dismiss_notification,
    mark_all_notifications_as_read,
    get_notification_stats
)
from .progress_views import (
    ProgressOverviewView,
    update_progress,
    calculate_auto_progress,
    progress_analytics,
    bulk_progress_update
)
from .final_overview_views import FinalOverviewView
from .stakeholder_views import (
    StakeholderListCreateView,
    StakeholderDetailView,
    record_stakeholder_activity,
    update_notification_preferences,
    bulk_stakeholder_actions,
    stakeholder_statistics,
    get_stakeholders_by_role,
    get_primary_contacts,
    get_approvers
)
from .risk_views import (
    RiskListCreateView,
    RiskDetailView,
    bulk_risk_actions,
    risk_analytics,
    risk_dashboard,
    update_risk_status,
    get_risk_matrix
)
from .activity_log_views import (
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
from .integration_views import ExternalIntegrationViewSet
from .tender_views import (
    ProcurementPlanTendersView,
)
from .dashboard_views import DashboardMetricsView

__all__ = [
    # ViewSets
    'ProcurementPlanViewSet',
    'QuarterlyTargetViewSet',
    'StageHistoryViewSet',
    'TimelineViewSet',
    'ProcurementRiskViewSet',
    'ApprovalWorkflowViewSet',
    'ApprovalWorkflowDependencyViewSet',
    'ActivityLogViewSet',
    'PerformanceMetricViewSet',
    # Class-based views
    'ProcurementPlanListCreateView',
    'ProcurementPlanDetailView',
    'TimelineListCreateView',
    'TimelineDetailView',
    'DocumentListCreateView',
    'DocumentDetailView',
    'download_document',
    'create_document_version',
    'NotificationListCreateView',
    'NotificationDetailView',
    'mark_notification_as_read',
    'dismiss_notification',
    'mark_all_notifications_as_read',
    'get_notification_stats',
    'ProgressOverviewView',
    'update_progress',
    'calculate_auto_progress',
    'progress_analytics',
    'bulk_progress_update',
    'FinalOverviewView',
    'StakeholderListCreateView',
    'StakeholderDetailView',
    'record_stakeholder_activity',
    'update_notification_preferences',
    'bulk_stakeholder_actions',
    'stakeholder_statistics',
    'get_stakeholders_by_role',
    'get_primary_contacts',
    'get_approvers',
    'RiskListCreateView',
    'RiskDetailView',
    'bulk_risk_actions',
    'risk_analytics',
    'risk_dashboard',
    'update_risk_status',
    'get_risk_matrix',
    'ActivityLogListCreateView',
    'ActivityLogDetailView',
    'create_activity_log',
    'activity_analytics',
    'get_recent_activities',
    'get_user_activities',
    'get_activities_by_action',
    'get_critical_activities',
    'export_activity_logs',
    'ExternalIntegrationViewSet',
    'ProcurementPlanTendersView',
    'DashboardMetricsView',
]
