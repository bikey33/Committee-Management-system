

from django.urls import path
from .views import (
    CreateCommitteeView, GetAllCommitteesView, GetCommitteeByIdView,
    UpdateCommitteeView, DeleteCommitteeView, AddMemberView,
    RemoveMemberView, GetCommitteesByMemberView, GetCommitteesByDateRangeView,
    DownloadFormationLetterView, GetCommitteesByProcurementPlanView,
    PreviewFormationLetterView,
    committee_details_with_type, GetCommitteesByTypeView, CommitteeRolesView,
    CommitteeRolesCRUDView, CommitteeRoleDetailView, ReviewCommitteeDefaultMembersView,
    ReviewCommitteeDefaultMembersDeleteView, CommitteePhaseCheckpointView,
    CommitteePhaseCheckpointDetailView, CommitteePhaseTransitionView,
    MyCommitteesReportView, OfficeCommitteesView, CommitteeStatsView,
)

urlpatterns = [
    path('committees/create/', CreateCommitteeView.as_view(), name='create-committee'),
    path('committees/all/', GetAllCommitteesView.as_view(), name='get-all-committees'),
    # Reporting endpoints (must precede the committees/<committee_id>/ catch-all).
    path('committees/reports/my-committees/', MyCommitteesReportView.as_view(), name='my-committees-report'),
    path('committees/reports/office/', OfficeCommitteesView.as_view(), name='office-committees-report'),
    path('committees/reports/stats/', CommitteeStatsView.as_view(), name='committee-stats-report'),
    path('roles/', CommitteeRolesView.as_view(), name='committee-roles'),
    path('roles/manage/', CommitteeRolesCRUDView.as_view(), name='committee-roles-crud'),
    path('roles/manage/<int:role_id>/', CommitteeRoleDetailView.as_view(), name='committee-role-detail'),
    path('committees/<str:committee_id>/', GetCommitteeByIdView.as_view(), name='get-committee-by-id'),
    path('committees/update/<str:committee_id>/', UpdateCommitteeView.as_view(), name='update-committee'),
    path('committees/deletecommittee/<str:committee_id>/', DeleteCommitteeView.as_view(), name='delete-committee'),
    path('committees/addmember/<str:committee_id>/', AddMemberView.as_view(), name='add-member'),
    path('committees/removemember/<str:committee_id>/', RemoveMemberView.as_view(), name='remove-member'),
    path('committees/<str:committee_id>/members/<str:employee_id>/',
         RemoveMemberView.as_view(), name='remove-member-legacy'),
    path('committees/bymember/<str:employee_id>/', GetCommitteesByMemberView.as_view(), name='committees-by-member'),
    path('committees/bydaterange/', GetCommitteesByDateRangeView.as_view(), name='committees-by-date-range'),
    path('committees/<str:committee_id>/download/', DownloadFormationLetterView.as_view(), name='download-formation-letter'),
    path('committees/<str:committee_id>/preview/', PreviewFormationLetterView.as_view(), name='preview-formation-letter'),
    path('committees/bytype/<str:committee_type>/', GetCommitteesByTypeView.as_view(), name='committees-by-type'),
    path('committees/<int:committee_id>/details/', committee_details_with_type, name='committee-details-with-type'),
    path('committees/byprocurementplan/<str:procurement_plan_id>/',
         GetCommitteesByProcurementPlanView.as_view(), name='committees-by-procurement-plan'),
    path('review-defaults/', ReviewCommitteeDefaultMembersView.as_view(), name='review-committee-defaults'),
    path('review-defaults/delete/', ReviewCommitteeDefaultMembersDeleteView.as_view(), name='review-committee-defaults-delete'),
    
    # Phase and checkpoint management
    path('committees/<int:committee_id>/checkpoints/', CommitteePhaseCheckpointView.as_view(), name='committee-checkpoints'),
    path('checkpoints/<int:checkpoint_id>/', CommitteePhaseCheckpointDetailView.as_view(), name='checkpoint-detail'),
    path('committees/<int:committee_id>/phase-transition/', CommitteePhaseTransitionView.as_view(), name='phase-transition'),
]
