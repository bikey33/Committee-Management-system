from rest_framework import serializers
from django.conf import settings
from .models import Committee, CommitteeMembership, CommitteeRole
from django.db.utils import OperationalError, ProgrammingError
from users.models import CustomUser, Office
from procurement.models import ProcurementPlan
import logging
from django.db import models

logger = logging.getLogger(__name__)


class CommitteeMemberSerializer(serializers.ModelSerializer):
    employeeId = serializers.CharField(source='employee_id')
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    email = serializers.EmailField()
    office = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    phone = serializers.CharField(allow_null=True, required=False)
    _id = serializers.CharField(source='employee_id')

    class Meta:
        model = CustomUser
        fields = ['_id', 'employeeId', 'name', 'role', 'email', 'phone', 'office', 'position']

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or getattr(obj, 'name', '') or getattr(obj, 'username', '')

    def get_role(self, obj):
        role_map = self.context.get('role_map')
        if role_map is not None:
            return role_map.get(obj.employee_id, 'member')

        membership = CommitteeMembership.objects.filter(
            user=obj, committee=self.context.get('committee')
        ).first()
        if membership:
            return membership.committee_role
        return 'member'

    def get_office(self, obj):
        if hasattr(obj, 'office') and obj.office:
            return obj.office.name
        return getattr(obj, 'department', None)

    def get_position(self, obj):
        if hasattr(obj, 'position') and obj.position:
            return obj.position.name
        return getattr(obj, 'designation', None)


class CommitteeSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id', read_only=True)
    createdBy = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    membersList = serializers.SerializerMethodField()
    office = serializers.PrimaryKeyRelatedField(
        queryset=Office.objects.all(),
        required=False,
        allow_null=True
    )
    formation_date = serializers.DateField(required=False, allow_null=True, input_formats=['%Y-%m-%d'])
    assigned_date = serializers.DateField(required=False, allow_null=True, input_formats=['%Y-%m-%d'])
    specification_submission_date = serializers.DateField(required=False, allow_null=True, input_formats=['%Y-%m-%d'])
    review_date = serializers.DateField(required=False, allow_null=True, input_formats=['%Y-%m-%d'])
    completion_date = serializers.DateField(required=False, allow_null=True, input_formats=['%Y-%m-%d'])
    decision_date = serializers.DateField(required=False, allow_null=True, input_formats=['%Y-%m-%d'])
    members = serializers.JSONField(required=False, default=[])
    formation_letter = serializers.FileField(required=False, allow_null=True, write_only=True)
    committee_type = serializers.ChoiceField(choices=Committee.COMMITTEE_TYPES, required=True)
    deadline = serializers.DateField(required=False, allow_null=True, input_formats=['%Y-%m-%d'])
    approval_status = serializers.CharField(required=False)
    committee_status = serializers.CharField(required=False)
    
    office_name = serializers.SerializerMethodField()
    formationLetterURL = serializers.SerializerMethodField()

    class Meta:
        model = Committee
        fields = [
            '_id', 'name', 'purpose', 'committee_type', 'office', 'office_name',
            'deadline', 'formation_date', 'assigned_date', 'specification_submission_date',
            'review_date', 'completion_date', 'decision_date',
            'formation_letter', 'formationLetterURL', 'approval_status', 'committee_status',
            'members', 'membersList', 'createdBy', 'createdAt', 'updatedAt'
        ]
        read_only_fields = [
            'id', 'createdBy', 'createdAt', 'updatedAt', 'membersList', 'office_name', 'formationLetterURL'
        ]

    def get_createdBy(self, obj):
        user = obj.created_by
        if not user:
            return None
        return {
            '_id': user.employee_id,
            'name': user.username,
            'email': user.email,
            'role': user.user_role.name if hasattr(user, 'user_role') and user.user_role else 'member',
            'employeeId': user.employee_id
        }

    def get_formationLetterURL(self, obj):
        if obj.formation_letter:
            # Returns S3 URL when using S3 storage, or local media URL otherwise
            return obj.formation_letter.url
        return None

    def get_office_name(self, obj):
        if obj.office:
            return obj.office.name
        if obj.procurement_plan and obj.procurement_plan.office:
            return obj.procurement_plan.office.name
        return None

    def get_membersList(self, obj):
        memberships = list(obj.memberships.select_related('user').all())
        role_map = {m.user.employee_id: m.committee_role for m in memberships}
        users = [m.user for m in memberships]
        return CommitteeMemberSerializer(
            users,
            many=True,
            context={'committee': obj, 'role_map': role_map}
        ).data

    def validate(self, data):
        committee_type = data.get('committee_type')
        procurement_plan = data.get('procurement_plan')

        return data

    def validate_members(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Members must be a list.")

        try:
            valid_roles = list(CommitteeRole.objects.filter(is_active=True).values_list('value', flat=True))
        except (ProgrammingError, OperationalError):
            valid_roles = []
        if not valid_roles:
            valid_roles = [
                'chairperson',
                'coordinator',
                'sub_coordinator',
                'secretary',
                'member',
                'invitee',
                'subject_expert',
                'others',
            ]
        employee_ids = []
        normalized_members = []

        for member in value:
            if isinstance(member, str):
                employee_id = member
                role = 'member'
            elif isinstance(member, dict):
                employee_id = member.get('employeeId')
                role = member.get('role', 'member')
            else:
                raise serializers.ValidationError("Each member must be a string or an object with employeeId.")

            if not employee_id:
                raise serializers.ValidationError("Each member must have an employeeId.")
            
            # Case-insensitive role check
            role_match = next((vr for vr in valid_roles if vr.lower() == role.lower()), None)
            if not role_match:
                # Fallback check against standard lowercase roles if DB list is empty or doesn't match
                standard_roles = ['chairperson', 'coordinator', 'sub_coordinator', 'secretary', 'member', 'invitee', 'subject_expert', 'others']
                if role.lower() in standard_roles:
                    role_match = role.lower()
                else:
                    raise serializers.ValidationError(f"Invalid role: {role}. Must be one of {valid_roles}.")
            
            # Use the matched role (preserving case from DB if it was found)
            normalized_members.append({'employeeId': employee_id, 'role': role_match})

            # Check if user exists with either employee_id or username
            user = CustomUser.objects.filter(
                models.Q(employee_id=employee_id) | models.Q(username=employee_id)
            ).first()

            if not user:
                raise serializers.ValidationError(f"User with employee_id/username {employee_id} not found.")

            employee_ids.append(employee_id)

        if len(employee_ids) != len(set(employee_ids)):
            raise serializers.ValidationError("Duplicate employee IDs are not allowed.")
        return normalized_members

    def validate_procurement_plan(self, value):
        if value and not ProcurementPlan.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Invalid procurement plan ID.")
        return value

    def create(self, validated_data):
        members = validated_data.pop('members', [])
        formation_letter = validated_data.pop('formation_letter', None)
        specification_title = validated_data.pop('specification_title', None)
        specification_description = validated_data.pop('specification_description', None)
        committee_type = validated_data.get('committee_type')
        procurement_plan = validated_data.get('procurement_plan')

        committee = Committee.objects.create(
            **validated_data,
            formation_letter=formation_letter,
            created_by=self.context['request'].user
        )

        logger.debug(f"Created committee {committee.id}")

        # Create memberships
        for member in members:
            # Find user by either employee_id or username
            user = CustomUser.objects.filter(
                models.Q(employee_id=member['employeeId']) | models.Q(username=member['employeeId'])
            ).first()

            if user:
                CommitteeMembership.objects.create(
                    committee=committee,
                    user=user,
                    committee_role=member.get('role', 'member')
                )
            else:
                logger.warning(f"User not found for employee_id: {member['employeeId']}")

        return committee

    def update(self, instance, validated_data):
        logger.debug(f"Updating committee {instance.id} with validated data: {validated_data}")
        members = validated_data.pop('members', None)
        formation_letter = validated_data.pop('formation_letter', None)
        specification_title = validated_data.pop('specification_title', None)
        specification_description = validated_data.pop('specification_description', None)
        committee_type = validated_data.get('committee_type', instance.committee_type)
        procurement_plan = validated_data.get('procurement_plan', instance.procurement_plan)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if formation_letter is not None:
            instance.formation_letter = formation_letter

        if specification_title is not None:
            instance.specification_title = specification_title
        if specification_description is not None:
            instance.specification_description = specification_description

        instance.save()

        logger.debug(f"Updated committee {instance.id}")

        # Update members if provided
        if members is not None:
            CommitteeMembership.objects.filter(committee=instance).delete()
            for member in members:
                # Find user by either employee_id or username
                user = CustomUser.objects.filter(
                    models.Q(employee_id=member['employeeId']) | models.Q(username=member['employeeId'])
                ).first()

                if user:
                    CommitteeMembership.objects.create(
                        committee=instance,
                        user=user,
                        committee_role=member.get('role', 'member')
                    )
                else:
                    logger.warning(f"User not found for employee_id: {member['employeeId']}")

            logger.debug(f"Members updated: {[m['employeeId'] for m in members]}")

        return instance
