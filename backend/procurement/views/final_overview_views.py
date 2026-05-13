from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import QuerySet
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# from bidder.models import Bidder
from procurement.models import DocumentCategory, ProcurementDocument, ProcurementPlan

from ..utils import normalize_stage_id
from users.utils import get_queryset_for_user


STAGE_DISPLAY_ORDER: List[Tuple[str, str]] = [
    ("planning", "Planning"),
    ("specification", "Specification"),
    ("spec_review", "Specification Review"),
    ("tender", "Tender"),
    ("evaluation", "Evaluation"),
    ("loi", "LOI"),
    ("loa", "LOA"),
    ("contract_prep", "Contract Preparation"),
    ("other", "Other"),
]

EVALUATION_KINDS = {"technical", "financial", "decision"}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _metadata(document: ProcurementDocument) -> Dict[str, Any]:
    data = getattr(document, "custom_metadata", None)
    return data if isinstance(data, dict) else {}


def _first_non_empty(*values: Any) -> Optional[Any]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return value
    return None


def _safe_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _map_document_stage(document: ProcurementDocument) -> Tuple[str, str]:
    document_type = _normalize_text(document.document_type)
    metadata = _metadata(document)
    evaluation_type = _normalize_text(metadata.get("evaluation_type"))

    if document_type == "specification":
        return "specification", "Specification"

    if document_type in {"review", "review_mom"}:
        return "spec_review", "Specification Review"

    if document_type == "tender":
        return "tender", "Tender"

    if (
        document_type in {"evaluation", "technical", "financial", "decision"}
        or evaluation_type in EVALUATION_KINDS
    ):
        return "evaluation", "Evaluation"

    if document_type == "loi":
        return "loi", "LOI"

    if document_type == "loa":
        return "loa", "LOA"

    if document_type in {
        "contract",
        "contract_mom",
        "contract_mam",
        "performance_guarantee",
        "main_contract",
    }:
        return "contract_prep", "Contract Preparation"

    return "other", "Other"


def _infer_document_purpose(document: ProcurementDocument) -> str:
    metadata = _metadata(document)
    document_type = _normalize_text(document.document_type)

    explicit = _first_non_empty(
        metadata.get("purpose"),
        metadata.get("document_purpose"),
        metadata.get("subject"),
        document.description,
    )
    if explicit:
        return str(explicit)

    if document_type in {"evaluation", "technical", "financial", "decision"}:
        evaluation_type = _normalize_text(metadata.get("evaluation_type")) or document_type
        if evaluation_type == "decision":
            return "Decision and recommendation record"
        return f"{evaluation_type.capitalize()} evaluation report"

    if document_type == "specification":
        return "Technical requirement and scope definition"
    if document_type in {"review", "review_mom"}:
        return "Specification review evidence"
    if document_type == "tender":
        return "Tender publication and bidding documentation"
    if document_type == "loi":
        return "Letter of Intent issued to selected bidder"
    if document_type == "loa":
        return "Letter of Acceptance issued to selected bidder"
    if document_type in {"contract_mom", "contract_mam"}:
        return "Contract minutes of meeting record"
    if document_type == "performance_guarantee":
        return "Performance guarantee submission"
    if document_type == "main_contract":
        return "Signed main contract document"
    if document_type == "contract":
        return "Contract record"

    return "Supporting procurement document"


def _document_type_label(
    document_type: str,
    categories_map: Dict[str, str],
) -> str:
    normalized = _normalize_text(document_type)
    if normalized in categories_map:
        return categories_map[normalized]
    return normalized.replace("_", " ").title() if normalized else "Other"


from users.permissions import HasPermission


class FinalOverviewView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, HasPermission('planning.view')]
    queryset = ProcurementPlan.objects.all()

    def get_queryset(self) -> QuerySet[ProcurementPlan]:
        return get_queryset_for_user(self.request.user, ProcurementPlan.objects.all())

    def retrieve(self, request, *args, **kwargs):
        if not getattr(request.user, 'user_role', None):
            return Response(
                {"error": "User must have a role to view final overview."},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan = self.get_object()
        payload = self._build_final_overview_payload(plan, request.user)
        return Response(payload, status=status.HTTP_200_OK)

    def _build_final_overview_payload(
        self, plan: ProcurementPlan, user
    ) -> Dict[str, Any]:
        documents_qs = (
            ProcurementDocument.objects.filter(procurement_plan=plan)
            .select_related("uploaded_by")
            .order_by("-created_at")
        )
        documents = [document for document in documents_qs if document.can_access(user)]

        document_categories = {
            _normalize_text(category.key): category.label
            for category in DocumentCategory.objects.all()
        }

        normalized_documents: List[Dict[str, Any]] = []
        stage_buckets: Dict[str, List[Dict[str, Any]]] = {}
        stage_count_map: Dict[str, int] = {}
        tag_count_map: Dict[str, int] = {}
        purpose_count_map: Dict[str, int] = {}
        type_count_map: Dict[str, int] = {}

        for document in documents:
            stage_id, stage_label = _map_document_stage(document)
            purpose = _infer_document_purpose(document)
            tags = document.tags if isinstance(document.tags, list) else []
            tags = [str(tag).strip() for tag in tags if str(tag).strip()]
            document_type_normalized = _normalize_text(document.document_type)

            serialized_document = {
                "id": document.id,
                "title": document.title,
                "file_name": document.file_name,
                "document_type": document.document_type,
                "document_type_label": _document_type_label(
                    document.document_type, document_categories
                ),
                "stage_id": stage_id,
                "stage_label": stage_label,
                "purpose": purpose,
                "tags": tags,
                "uploaded_by_name": getattr(document.uploaded_by, "name", "")
                or getattr(document.uploaded_by, "email", ""),
                "uploaded_at": document.uploaded_at,
                "created_at": document.created_at,
                "status": document.status,
                "access_level": document.access_level,
                "file": document.file.url if document.file else None,
                "custom_metadata": _metadata(document),
            }
            normalized_documents.append(serialized_document)

            stage_buckets.setdefault(stage_id, []).append(serialized_document)
            stage_count_map[stage_id] = stage_count_map.get(stage_id, 0) + 1
            purpose_count_map[purpose] = purpose_count_map.get(purpose, 0) + 1
            type_count_map[document_type_normalized] = (
                type_count_map.get(document_type_normalized, 0) + 1
            )
            for tag in tags:
                tag_count_map[tag] = tag_count_map.get(tag, 0) + 1

        documents_by_stage: List[Dict[str, Any]] = []
        for stage_id, stage_label in STAGE_DISPLAY_ORDER:
            count = stage_count_map.get(stage_id, 0)
            if count == 0:
                continue
            documents_by_stage.append(
                {
                    "stage_id": stage_id,
                    "stage_label": stage_label,
                    "count": count,
                }
            )

        available_filters = {
            "stages": documents_by_stage,
            "tags": [
                {"value": tag, "count": count}
                for tag, count in sorted(tag_count_map.items(), key=lambda x: (-x[1], x[0]))
            ],
            "purposes": [
                {"value": purpose, "count": count}
                for purpose, count in sorted(
                    purpose_count_map.items(), key=lambda x: (-x[1], x[0])
                )
            ],
            "document_types": [
                {
                    "value": document_type,
                    "label": _document_type_label(document_type, document_categories),
                    "count": count,
                }
                for document_type, count in sorted(
                    type_count_map.items(), key=lambda x: (-x[1], x[0])
                )
            ],
        }

        committees = []
        for committee in plan.committees.all().order_by("-created_at"):
            committees.append(
                {
                    "id": committee.id,
                    "name": committee.name,
                    "committee_type": committee.committee_type,
                    "members_count": committee.memberships.count(),
                    "created_at": committee.created_at,
                    "formation_date": committee.formation_date,
                }
            )

        stage_history = []
        for record in plan.stage_history.select_related("changed_by").all().order_by("changed_at"):
            stage_history.append(
                {
                    "id": record.id,
                    "previous_stage": normalize_stage_id(record.previous_stage),
                    "new_stage": normalize_stage_id(record.new_stage),
                    "changed_at": record.changed_at,
                    "notes": record.notes,
                    "changed_by": {
                        "id": record.changed_by.pk,
                        "name": getattr(record.changed_by, "name", "")
                        or getattr(record.changed_by, "email", ""),
                        "email": getattr(record.changed_by, "email", ""),
                    },
                }
            )

        executive_summary = self._build_executive_summary(plan, documents)
        coverage_matrix = self._build_coverage_matrix(documents)

        return {
            "procurement_plan": {
                "id": plan.id,
                "policy_number": plan.policy_number,
                "project_name": plan.project_name,
                "project_description": plan.project_description,
                "department": plan.department,
                "fiscal_year": plan.fiscal_year,
                "budget": _to_float(_safe_decimal(plan.budget)),
                "estimated_cost": _to_float(_safe_decimal(plan.estimated_cost)),
                "stage": normalize_stage_id(plan.stage),
                "status": plan.status,
                "created_at": plan.created_at,
                "updated_at": plan.updated_at,
                "stage_updated_at": plan.stage_updated_at,
            },
            "executive_award_summary": executive_summary,
            "documents": normalized_documents,
            "documents_by_stage": documents_by_stage,
            "available_filters": available_filters,
            "coverage_matrix": coverage_matrix,
            "committees": committees,
            "stage_history": stage_history,
        }

    def _build_executive_summary(
        self,
        plan: ProcurementPlan,
        documents: List[ProcurementDocument],
    ) -> Dict[str, Any]:
        latest_tender = (
            plan.tenders.all().order_by("-created_at", "-id").first()
            if hasattr(plan, "tenders")
            else None
        )
        opening = getattr(latest_tender, "opening_details", None) if latest_tender else None
        decision_details = opening.decision_details if opening and isinstance(opening.decision_details, dict) else {}

        winner_id = decision_details.get("winning_bidder_id")
        winner_name = decision_details.get("winning_bidder_name")
        decision_remarks = decision_details.get("remarks")

        financial_row = None
        if opening and isinstance(opening.financial_evaluations, list) and winner_id:
            financial_row = next(
                (
                    row
                    for row in opening.financial_evaluations
                    if row.get("bidder_id") == winner_id
                ),
                None,
            )

        bidder_record = None
        if winner_id:
            pass
            # bidder_record = Bidder.objects.filter(id=winner_id).first()

        loa_document = next(
            (document for document in documents if _normalize_text(document.document_type) == "loa"),
            None,
        )
        loi_document = next(
            (document for document in documents if _normalize_text(document.document_type) == "loi"),
            None,
        )
        main_contract_document = next(
            (
                document
                for document in documents
                if _normalize_text(document.document_type) == "main_contract"
            ),
            None,
        )
        performance_guarantee_document = next(
            (
                document
                for document in documents
                if _normalize_text(document.document_type) == "performance_guarantee"
            ),
            None,
        )
        contract_mom_document = next(
            (
                document
                for document in documents
                if _normalize_text(document.document_type) in {"contract_mom", "contract_mam"}
            ),
            None,
        )

        loa_metadata = _metadata(loa_document) if loa_document else {}
        loi_metadata = _metadata(loi_document) if loi_document else {}
        contract_metadata = _metadata(main_contract_document) if main_contract_document else {}

        awarded_amount = _safe_decimal(
            _first_non_empty(
                financial_row.get("bid_amount") if financial_row else None,
                loa_metadata.get("winning_bid_amount"),
                loi_metadata.get("winning_bid_amount"),
            )
        )
        budget = _safe_decimal(plan.budget)
        estimated_cost = _safe_decimal(plan.estimated_cost)

        variance_amount = None
        variance_percent = None
        if budget is not None and awarded_amount is not None:
            variance_amount = budget - awarded_amount
            if budget != 0:
                variance_percent = (variance_amount / budget) * Decimal("100")

        awarding_authority = (
            _first_non_empty(
                loa_metadata.get("awarding_authority"),
                loi_metadata.get("awarding_authority"),
            )
            or "Nepal Telecommunication"
        )
        resolved_winner_name = (
            _first_non_empty(
                winner_name,
                getattr(bidder_record, "name", None),
            )
            or "Selected Bidder"
        )
        statement = (
            f"{awarding_authority} awards the contract for "
            f"{plan.project_name or 'the procurement project'} to {resolved_winner_name}."
        )

        return {
            "awarding_authority": awarding_authority,
            "statement": statement,
            "winner": {
                "id": winner_id,
                "name": resolved_winner_name,
                "contact_person": getattr(bidder_record, "contact_name", None),
                "email": getattr(bidder_record, "email", None),
                "phone": getattr(bidder_record, "contact_number", None),
                "address": getattr(bidder_record, "address", None),
            }
            if winner_id or resolved_winner_name
            else None,
            "award_amount": _to_float(awarded_amount),
            "award_rank": financial_row.get("remark") if financial_row else None,
            "decision": {
                "remarks": decision_remarks,
                "winning_bidder_id": winner_id,
                "winning_bidder_name": winner_name,
            },
            "loi": self._serialize_letter_document(loi_document),
            "loa": self._serialize_letter_document(loa_document),
            "contract": {
                "contract_number": _first_non_empty(
                    contract_metadata.get("contract_number"),
                    contract_metadata.get("reference_number"),
                ),
                "contract_date": _first_non_empty(
                    contract_metadata.get("contract_date"),
                    contract_metadata.get("issue_date"),
                    main_contract_document.created_at if main_contract_document else None,
                ),
                "remarks": contract_metadata.get("remarks"),
                "main_contract_document": self._serialize_document_ref(main_contract_document),
                "performance_guarantee_document": self._serialize_document_ref(
                    performance_guarantee_document
                ),
                "contract_mom_document": self._serialize_document_ref(contract_mom_document),
            },
            "budget_summary": {
                "budget": _to_float(budget),
                "estimated_cost": _to_float(estimated_cost),
                "awarded_amount": _to_float(awarded_amount),
                "variance_amount": _to_float(variance_amount),
                "variance_percent": _to_float(variance_percent),
            },
        }

    def _serialize_letter_document(
        self, document: Optional[ProcurementDocument]
    ) -> Optional[Dict[str, Any]]:
        if not document:
            return None
        metadata = _metadata(document)
        return {
            "document": self._serialize_document_ref(document),
            "reference_number": _first_non_empty(metadata.get("reference_number")),
            "issue_date": _first_non_empty(metadata.get("issue_date"), document.created_at),
            "deadline_last_date": metadata.get("deadline_last_date"),
            "final_deadline_date": metadata.get("final_deadline_date"),
            "remarks": metadata.get("remarks"),
        }

    def _serialize_document_ref(
        self, document: Optional[ProcurementDocument]
    ) -> Optional[Dict[str, Any]]:
        if not document:
            return None
        return {
            "id": document.id,
            "title": document.title,
            "document_type": document.document_type,
            "uploaded_at": document.uploaded_at,
            "file": document.file.url if document.file else None,
        }

    def _build_coverage_matrix(
        self, documents: List[ProcurementDocument]
    ) -> List[Dict[str, Any]]:
        normalized_document_types = [_normalize_text(doc.document_type) for doc in documents]
        evaluation_types = [
            _normalize_text(_metadata(doc).get("evaluation_type")) for doc in documents
        ]

        def has_document_type(*types: str) -> bool:
            normalized_types = {_normalize_text(t) for t in types}
            return any(document_type in normalized_types for document_type in normalized_document_types)

        def has_evaluation(kind: str) -> bool:
            normalized_kind = _normalize_text(kind)
            if has_document_type(normalized_kind):
                return True
            return any(value == normalized_kind for value in evaluation_types)

        matrix = [
            (
                "specification",
                "Specification",
                [("specification", "Specification document", has_document_type("specification"))],
            ),
            (
                "spec_review",
                "Specification Review",
                [
                    ("review", "Review document", has_document_type("review")),
                    ("review_mom", "Review MoM document", has_document_type("review_mom")),
                ],
            ),
            (
                "tender",
                "Tender",
                [("tender", "Tender publication document", has_document_type("tender"))],
            ),
            (
                "evaluation",
                "Evaluation",
                [
                    ("technical", "Technical evaluation", has_evaluation("technical")),
                    ("financial", "Financial evaluation", has_evaluation("financial")),
                    ("decision", "Decision report", has_evaluation("decision")),
                ],
            ),
            ("loi", "LOI", [("loi", "LOI document", has_document_type("loi"))]),
            ("loa", "LOA", [("loa", "LOA document", has_document_type("loa"))]),
            (
                "contract_prep",
                "Contract Preparation",
                [
                    (
                        "contract_mom",
                        "Contract MoM",
                        has_document_type("contract_mom", "contract_mam"),
                    ),
                    (
                        "performance_guarantee",
                        "Performance Guarantee",
                        has_document_type("performance_guarantee"),
                    ),
                    (
                        "main_contract",
                        "Main Contract",
                        has_document_type("main_contract"),
                    ),
                ],
            ),
        ]

        response = []
        for stage_id, stage_label, checks in matrix:
            completed = sum(1 for _, _, is_done in checks if is_done)
            response.append(
                {
                    "stage_id": stage_id,
                    "stage_label": stage_label,
                    "completed_requirements": completed,
                    "total_requirements": len(checks),
                    "requirements": [
                        {
                            "key": key,
                            "label": label,
                            "completed": is_done,
                        }
                        for key, label, is_done in checks
                    ],
                }
            )
        return response
