from django.db.models import Q
from django.utils import timezone

from .models import ActivityLog, ProcurementDocument, StageHistory
from .utils import LEGACY_STAGE_SEQUENCE, STRICT_STAGE_SEQUENCE, normalize_stage_id


EVALUATION_KINDS = ("technical", "financial", "decision")


def _count_and_delete(queryset):
    count = queryset.count()
    if count:
        queryset.delete()
    return count


def _cleanup_specification(plan):
    from committee.models import Committee
    from specification.models import Specification
    from tender.models import Tender

    summary = {
        "specification_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(
                procurement_plan=plan, document_type="specification"
            )
        ),
        "specification_committees_deleted": _count_and_delete(
            Committee.objects.filter(
                procurement_plan=plan, committee_type="specification"
            )
        ),
        "specifications_deleted": 0,
        "tenders_detached_from_specification": 0,
    }

    specification_ids = list(
        Specification.objects.filter(procurement_plan=plan).values_list("id", flat=True)
    )
    if specification_ids:
        summary["tenders_detached_from_specification"] = Tender.objects.filter(
            specification_id__in=specification_ids
        ).update(specification=None)
        summary["specifications_deleted"] = _count_and_delete(
            Specification.objects.filter(id__in=specification_ids)
        )

    return summary


def _cleanup_spec_review(plan):
    from committee.models import Committee

    return {
        "review_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(
                procurement_plan=plan, document_type__in=("review", "review_mom")
            )
        ),
        "review_committees_deleted": _count_and_delete(
            Committee.objects.filter(procurement_plan=plan, committee_type="review")
        ),
    }


def _cleanup_committee(plan):
    from committee.models import Committee

    return {
        "committee_stage_committees_deleted": _count_and_delete(
            Committee.objects.filter(procurement_plan=plan, committee_type="evaluation")
        ),
    }


def _cleanup_bidding(plan):
    from bidder.models import BidderDocument
    from tender.models import TenderOpening

    return {
        "tender_openings_deleted": _count_and_delete(
            TenderOpening.objects.filter(tender__procurement_plan=plan)
        ),
        "bidder_documents_deleted": _count_and_delete(
            BidderDocument.objects.filter(procurement_plan=plan)
        ),
    }


def _cleanup_tender(plan):
    from bidder.models import BidderDocument
    from tender.models import Tender

    return {
        "tender_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(procurement_plan=plan, document_type="tender")
        ),
        "bidder_documents_deleted": _count_and_delete(
            BidderDocument.objects.filter(procurement_plan=plan)
        ),
        "tenders_deleted": _count_and_delete(Tender.objects.filter(procurement_plan=plan)),
    }


def _cleanup_evaluation(plan):
    from committee.models import Committee
    from tender.models import TenderOpening

    evaluation_document_filter = Q(
        document_type__in=("evaluation", "technical", "financial", "decision")
    ) | Q(custom_metadata__evaluation_type__in=EVALUATION_KINDS)

    return {
        "evaluation_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(procurement_plan=plan).filter(
                evaluation_document_filter
            )
        ),
        "evaluation_committees_deleted": _count_and_delete(
            Committee.objects.filter(procurement_plan=plan, committee_type="evaluation")
        ),
        "opening_evaluation_tables_cleared": TenderOpening.objects.filter(
            tender__procurement_plan=plan
        ).update(
            technical_evaluations=[],
            financial_evaluations=[],
            decision_details={},
        ),
    }


def _cleanup_loi(plan):
    return {
        "loi_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(procurement_plan=plan, document_type="loi")
        ),
    }


def _cleanup_loa(plan):
    return {
        "loa_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(procurement_plan=plan, document_type="loa")
        ),
    }


def _cleanup_contract_prep(plan):
    from committee.models import Committee

    clarification_filter = Q(
        document_type="correspondence",
        custom_metadata__context="contract_clarification",
    )
    contract_document_filter = Q(document_type__in=(
        "contract",
        "contract_mom",
        "contract_mam",
        "performance_guarantee",
        "main_contract",
    ))

    return {
        "contract_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(procurement_plan=plan).filter(
                contract_document_filter
            )
        ),
        "contract_clarification_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(procurement_plan=plan).filter(
                clarification_filter
            )
        ),
        "contract_committees_deleted": _count_and_delete(
            Committee.objects.filter(procurement_plan=plan, committee_type="contract")
        ),
    }


def _cleanup_contract_legacy(plan):
    return {
        "legacy_contract_documents_deleted": _count_and_delete(
            ProcurementDocument.objects.filter(
                procurement_plan=plan,
                document_type__in=("loa", "loi", "contract"),
            )
        ),
    }


def _cleanup_complaint(plan):
    return {"complaint_cleanup": "no_stage_specific_data"}


def _cleanup_management(plan):
    return {"management_cleanup": "no_stage_specific_data"}


def _cleanup_final_contract(plan):
    return {"final_contract_cleanup": "no_stage_specific_data"}


STAGE_RESET_HANDLERS = {
    "specification": _cleanup_specification,
    "spec_review": _cleanup_spec_review,
    "committee": _cleanup_committee,
    "bidding": _cleanup_bidding,
    "tender": _cleanup_tender,
    "evaluation": _cleanup_evaluation,
    "loi": _cleanup_loi,
    "loa": _cleanup_loa,
    "contract": _cleanup_contract_legacy,
    "complaint": _cleanup_complaint,
    "management": _cleanup_management,
    "contract_prep": _cleanup_contract_prep,
    "final_contract": _cleanup_final_contract,
}


def get_previous_stage(current_stage):
    normalized_current = normalize_stage_id(current_stage)
    if normalized_current in STRICT_STAGE_SEQUENCE:
        sequence = STRICT_STAGE_SEQUENCE
    elif normalized_current in LEGACY_STAGE_SEQUENCE:
        sequence = LEGACY_STAGE_SEQUENCE
    else:
        return None

    current_index = sequence.index(normalized_current)
    if current_index == 0:
        return None
    return sequence[current_index - 1]


def perform_stage_reset(plan, user, target_stage=None, reason=""):
    current_stage = normalize_stage_id(plan.stage)
    previous_stage = get_previous_stage(current_stage)
    if not previous_stage:
        raise ValueError("Current stage cannot be reset further.")

    normalized_target = normalize_stage_id(target_stage) if target_stage else previous_stage
    if normalized_target != previous_stage:
        raise ValueError(
            f"Only reset to immediate previous stage is allowed: '{current_stage}' -> '{previous_stage}'."
        )

    cleanup_handler = STAGE_RESET_HANDLERS.get(current_stage)
    if cleanup_handler is None:
        raise ValueError(f"Stage reset is not supported for stage '{current_stage}'.")

    cleanup_summary = cleanup_handler(plan)

    old_stage = plan.stage
    plan.stage = normalized_target
    plan.stage_updated_at = timezone.now()
    plan.progress_percentage = plan.calculate_progress_percentage()

    update_fields = ["stage", "stage_updated_at", "progress_percentage"]
    if plan.status == "completed":
        plan.status = "active"
        update_fields.append("status")
    plan.save(update_fields=update_fields)

    StageHistory.objects.create(
        procurement_plan=plan,
        previous_stage=old_stage,
        new_stage=normalized_target,
        changed_by=user,
        notes=reason or "",
    )

    ActivityLog.log_activity(
        procurement_plan=plan,
        action="stage_reverted",
        user=user,
        description=f"Stage reverted from {old_stage} to {normalized_target}",
        details={
            "old_stage": old_stage,
            "new_stage": normalized_target,
            "cleanup_summary": cleanup_summary,
            "reason": reason or "",
        },
        old_values={"stage": old_stage},
        new_values={"stage": normalized_target},
        user_agent="",
    )

    return {
        "old_stage": old_stage,
        "new_stage": normalized_target,
        "cleanup_summary": cleanup_summary,
    }
