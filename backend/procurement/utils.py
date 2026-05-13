from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.response import Response


STRICT_STAGE_SEQUENCE = (
    "planning",
    "specification",
    "spec_review",
    "tender",
    "evaluation",
    "loi",
    "loa",
    "contract_prep",
    "final_contract",
)

LEGACY_STAGE_SEQUENCE = (
    "planning",
    "specification",
    "tender",
    "committee",
    "bidding",
    "evaluation",
    "contract",
    "complaint",
    "management",
)

EVALUATION_KINDS = {"technical", "financial", "decision"}


def normalize_stage_id(stage_id):
    value = str(stage_id or "").strip().lower()
    if value == "final_overview":
        return "final_contract"
    if value == "loa_loi":
        return "loi"
    return value


def _normalize_text(value):
    return str(value or "").strip().lower()


def _document_metadata(document):
    metadata = getattr(document, "custom_metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _is_evaluation_document(document):
    document_type = _normalize_text(getattr(document, "document_type", ""))
    metadata_type = _normalize_text(_document_metadata(document).get("evaluation_type"))
    return (
        document_type in {"evaluation", "technical", "financial", "decision"}
        or metadata_type in EVALUATION_KINDS
    )


def _matches_evaluation_kind(document, kind):
    normalized_kind = _normalize_text(kind)
    metadata_type = _normalize_text(_document_metadata(document).get("evaluation_type"))
    if metadata_type:
        return metadata_type == normalized_kind

    document_type = _normalize_text(getattr(document, "document_type", ""))
    if document_type == normalized_kind:
        return True

    title = _normalize_text(getattr(document, "title", ""))
    if normalized_kind == "decision":
        return "decision" in title or "ber" in title
    return normalized_kind in title


def _get_transition_sequence(current_stage, target_stage):
    if current_stage in STRICT_STAGE_SEQUENCE and target_stage in STRICT_STAGE_SEQUENCE:
        return STRICT_STAGE_SEQUENCE
    if current_stage in LEGACY_STAGE_SEQUENCE and target_stage in LEGACY_STAGE_SEQUENCE:
        return LEGACY_STAGE_SEQUENCE
    return None


def get_stage_completion_status(plan):
    committees = list(plan.committees.all())
    documents = list(plan.documents.all())
    tenders = list(plan.tenders.all())

    has_winner_from_opening = False
    has_bid_opening_completed = False
    for tender in tenders:
        try:
            opening = tender.opening_details
        except Exception:
            opening = None
        if not opening:
            continue

        if opening.is_completed or bool(opening.muchulka_document):
            has_bid_opening_completed = True

        decision_details = opening.decision_details or {}
        if isinstance(decision_details, dict) and decision_details.get("winning_bidder_id"):
            has_winner_from_opening = True

    has_legacy_winner_metadata = any(
        _normalize_text(document.document_type) in {"loa", "loi"}
        and _document_metadata(document).get("winning_bidder_id")
        for document in documents
    )
    has_winner_selected = has_winner_from_opening or has_legacy_winner_metadata

    evaluation_documents = [document for document in documents if _is_evaluation_document(document)]

    return {
        "planning": {
            "has_name": bool(str(getattr(plan, "project_name", "")).strip()),
            "has_budget": (getattr(plan, "budget", 0) or 0) > 0
            and (getattr(plan, "estimated_cost", 0) or 0) > 0,
            "has_quarterly_target": plan.quarterly_targets.exists(),
        },
        "specification": {
            "has_committee": any(
                committee.committee_type == "specification"
                for committee in committees
            ),
            "has_documents": any(
                _normalize_text(document.document_type) == "specification"
                for document in documents
            ),
        },
        "spec_review": {
            "has_review_committee": any(
                committee.committee_type == "review"
                for committee in committees
            ),
            "has_review_document": any(
                _normalize_text(document.document_type) == "review"
                for document in documents
            ),
            "has_review_mom": any(
                _normalize_text(document.document_type) == "review_mom"
                for document in documents
            ),
        },
        "tender": {
            "has_tender": len(tenders) > 0,
            "has_bid_opening_completed": has_bid_opening_completed,
        },
        "evaluation": {
            "has_eval_committee": any(
                committee.committee_type == "evaluation"
                for committee in committees
            ),
            "has_technical_doc": any(
                _matches_evaluation_kind(document, "technical")
                for document in evaluation_documents
            ),
            "has_financial_doc": any(
                _matches_evaluation_kind(document, "financial")
                for document in evaluation_documents
            ),
            "has_decision_doc": any(
                _matches_evaluation_kind(document, "decision")
                for document in evaluation_documents
            ),
        },
        "loi": {
            "has_bidder_selected": has_winner_selected,
            "has_loi_document": any(
                _normalize_text(document.document_type) == "loi"
                for document in documents
            ),
        },
        "loa": {
            "has_bidder_selected": has_winner_selected,
            "has_loa_document": any(
                _normalize_text(document.document_type) == "loa"
                for document in documents
            ),
        },
        "contract_prep": {
            "has_contract_committee": any(
                committee.committee_type == "contract"
                for committee in committees
            ),
            "has_contract_mom": any(
                _normalize_text(document.document_type) in {"contract_mom", "contract_mam"}
                for document in documents
            ),
            "has_performance_guarantee": any(
                _normalize_text(document.document_type) == "performance_guarantee"
                for document in documents
            ),
            "has_main_contract": any(
                _normalize_text(document.document_type) == "main_contract"
                for document in documents
            ),
        },
        "final_contract": {
            "is_complete": True,
        },
    }


def get_stage_completion_failures(plan, stage_id):
    stage = normalize_stage_id(stage_id)
    status = get_stage_completion_status(plan)

    # Detect if any active tender in this plan is single-stage type
    is_single_stage = any(
        getattr(t, 'tender_stage_type', None) == 'single_stage'
        for t in plan.tenders.all()
    )

    evaluation_checks = [
        ("has_eval_committee", "Create an evaluation committee."),
        ("has_technical_doc", "Upload evaluation report."),
    ]
    if not is_single_stage:
        evaluation_checks.append(
            ("has_financial_doc", "Upload financial evaluation report.")
        )
    evaluation_checks.append(
        ("has_decision_doc", "Upload decision document.")
    )

    checks = {
        "planning": [
            ("has_name", "Add project name and description."),
            ("has_budget", "Enter budget and estimated cost."),
            ("has_quarterly_target", "Add at least one quarterly target."),
        ],
        "specification": [
            ("has_committee", "Create a specification committee."),
            ("has_documents", "Upload at least one specification document."),
        ],
        "spec_review": [
            ("has_review_committee", "Create a review committee."),
            ("has_review_document", "Upload a review document."),
            ("has_review_mom", "Upload a review MOM document."),
        ],
        "tender": [
            ("has_tender", "Create a tender."),
            (
                "has_bid_opening_completed",
                "Complete bid opening and upload Muchulka document.",
            ),
        ],
        "evaluation": evaluation_checks,
        "loi": [
            (
                "has_bidder_selected",
                "Select and save winning bidder in Evaluation decision.",
            ),
            ("has_loi_document", "Upload LOI document."),
        ],
        "loa": [
            (
                "has_bidder_selected",
                "Select and save winning bidder in Evaluation decision.",
            ),
            ("has_loa_document", "Upload LOA document."),
        ],
        "contract_prep": [
            ("has_contract_committee", "Create a contract committee."),
            ("has_contract_mom", "Upload Contract MoM document."),
            ("has_performance_guarantee", "Upload Performance Guarantee document."),
            ("has_main_contract", "Upload Main Contract document."),
        ],
    }

    stage_checks = checks.get(stage, [])
    stage_status = status.get(stage, {})
    missing = [
        message
        for field_name, message in stage_checks
        if not stage_status.get(field_name, False)
    ]
    return missing


def validate_stage_transition(plan, target_stage):
    current_stage = normalize_stage_id(getattr(plan, "stage", ""))
    normalized_target = normalize_stage_id(target_stage)

    if not normalized_target:
        return False, ["Target stage is required."]

    if current_stage == normalized_target:
        return True, []

    sequence = _get_transition_sequence(current_stage, normalized_target)
    if not sequence:
        return (
            False,
            [f"Transition from '{current_stage}' to '{normalized_target}' is not allowed."],
        )

    current_index = sequence.index(current_stage)
    target_index = sequence.index(normalized_target)

    if target_index < current_index:
        return (
            False,
            [f"Moving backwards is not allowed: '{current_stage}' -> '{normalized_target}'."],
        )

    if target_index > current_index + 1:
        expected_next = sequence[current_index + 1]
        return (
            False,
            [
                "Cannot skip stages. "
                f"Complete '{expected_next}' before moving to '{normalized_target}'."
            ],
        )

    missing = get_stage_completion_failures(plan, current_stage)
    if missing:
        return (
            False,
            [
                f"Cannot proceed to '{normalized_target}' until '{current_stage}' is complete."
            ]
            + missing,
        )

    return True, []


def apply_procurement_filters(queryset, request):
    """Apply search and filters to procurement plan queryset"""
    params = request.query_params
    search = params.get('search', '')
    status_filter = params.get('status', '')
    owner_filter = params.get('owner', '')
    stage_filter = params.get('stage', '')
    office_filter = params.get('office', '')
    fiscal_year_filter = params.get('fiscal_year', '')

    if search:
        queryset = queryset.filter(
            Q(project_name__icontains=search) |
            Q(policy_number__icontains=search) |
            Q(project_description__icontains=search)
        )

    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    if stage_filter and stage_filter != 'all':
        normalized_stage = normalize_stage_id(stage_filter)
        queryset = queryset.filter(stage=normalized_stage)

    if office_filter and office_filter != 'all':
        if str(office_filter).isdigit():
            queryset = queryset.filter(office_id=office_filter)
        else:
            queryset = queryset.filter(
                Q(office__name__icontains=office_filter) | 
                Q(department__icontains=office_filter)
            )

    if fiscal_year_filter and fiscal_year_filter != 'all':
        queryset = queryset.filter(fiscal_year=fiscal_year_filter)

    if owner_filter:
        queryset = queryset.filter(owner__id=owner_filter)

    # Date range filtering
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)

    return queryset


def create_procurement_paginated_response(queryset, request, serializer_class):
    """Create paginated response for procurement plan list"""
    page_size = int(request.query_params.get('page_size', 20))
    page = int(request.query_params.get('page', 1))

    max_page_size = 100
    if page_size > max_page_size:
        page_size = max_page_size

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    serializer = serializer_class(page_obj.object_list, many=True)

    return Response({
        'success': True,
        'data': {
            'plans': serializer.data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page': page + 1 if page_obj.has_next() else None,
                'previous_page': page - 1 if page_obj.has_previous() else None,
            }
        }
    })


def create_standard_paginated_response(queryset, request, serializer_class, data_key='results'):
    """Create standard DRF-style paginated response (similar to our custom ProcurementPlanPagination)"""
    page_size = int(request.query_params.get('page_size', 20))
    page = int(request.query_params.get('page', 1))

    # Limit max page size
    max_page_size = 100
    if page_size > max_page_size:
        page_size = max_page_size

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    serializer = serializer_class(page_obj.object_list, many=True, context={'request': request})

    if hasattr(request, 'build_absolute_uri'):
        base_url = request.build_absolute_uri(request.path)
        query_params = request.query_params.copy()

        if page_obj.has_next():
            query_params['page'] = page + 1

        if page_obj.has_previous():
            query_params['page'] = page - 1

    return Response({
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page,
        'page_size': page_size,
        data_key: serializer.data
    })
