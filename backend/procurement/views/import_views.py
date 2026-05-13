from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.core.files.storage import default_storage
import pandas as pd
import json
import os
import logging
from decimal import Decimal

from department.models import Department
from users.models import Office
from ..models import ProcurementPlan, QuarterlyTarget
from ..serializers import ProcurementPlanSerializer
from django.db.models import Q
from users.permissions import HasPermission
from ..mixins import get_procurement_plan_filter

logger = logging.getLogger(__name__)


class ProcurementImportView(APIView):
    """
    Handle import of procurement plans from Excel files
    """
    permission_classes = [HasPermission('planning.excel')]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            logger.info("Starting procurement import process")
            
            # Get the uploaded file
            file = request.FILES.get('file')
            if not file:
                logger.error("No file provided in request")
                return Response(
                    {'error': 'No file provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Received file: {file.name}, size: {file.size}")

            # Get validation result
            validation_result = request.data.get('validation_result')
            if validation_result:
                validation_result = json.loads(validation_result)

            # Save file temporarily
            relative_path = default_storage.save(f'imports/{file.name}', file)
            file_path = default_storage.path(relative_path)
            logger.info(f"File saved to: {file_path}")
            
            try:
                # Read Excel file
                logger.info("Reading Excel file with pandas")
                df = pd.read_excel(file_path)
                # Clean column names
                df.columns = [str(c).strip() for c in df.columns]
                logger.info(f"Excel file read successfully. Shape: {df.shape}, Columns: {list(df.columns)}")
                
                # Get mappings
                mappings = request.data.get('mappings')
                if mappings and isinstance(mappings, str):
                    try:
                        mappings = json.loads(mappings)
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode mappings JSON")
                        mappings = {}
                elif not mappings:
                    mappings = {}

                # Regex to clean currency strings
                import re
                numeric_cleaner = re.compile(r'[^\d\.]+')

                # Process the data
                imported_count = 0
                errors = []
                
                valid_departments = list(
                    Department.objects.values_list('name', flat=True)
                )
                
                with transaction.atomic():
                    for index, row in df.iterrows():
                        try:
                            logger.debug(f"Processing row {index + 1}")
                            
                            # Skip header row if it exists
                            if index == 0 and any(str(cell).lower() in ['department', 'policy no.', 'project name'] for cell in row):
                                logger.info("Skipping header row")
                                continue
                            
                             # Helper function to safely get column value by exact name
                            def get_column_value(column_name, default=''):
                                if column_name in df.columns:
                                    value = row[column_name]
                                    if pd.isna(value): return default
                                    return str(value).strip()
                                return default

                             # Helper function to safely get column value with mappings
                            def get_mapped_value(field_id, default=''):
                                # Try mapping first
                                column_name = mappings.get(field_id)
                                if column_name and column_name in df.columns:
                                    value = row[column_name]
                                    if pd.isna(value): return default
                                    return str(value).strip()
                                
                                # Fallback to standard names
                                fallbacks = {
                                    'policy_number': ['Policy No.', 'Policy Number'],
                                    'project_name': ['Project Name'],
                                    'project_description': ['Project Description', 'Description'],
                                    'estimated_cost': ['Estimated Cost'],
                                    'budget': ['Proposed Amount', 'Budget'],
                                    'fiscal_year': ['Fiscal Year'],
                                    'program_number': ['Program No.', 'Program Number'],
                                    'office': ['Office Code', 'Office', 'Department'],
                                }
                                for fallback in fallbacks.get(field_id, []):
                                    if fallback in df.columns:
                                        value = row[fallback]
                                        if pd.isna(value): continue
                                        return str(value).strip()
                                return default
                            
                            def get_mapped_numeric_value(field_id, default=0):
                                def parse_decimal(val):
                                    if pd.isna(val): return None
                                    if isinstance(val, (int, float, Decimal)):
                                        return Decimal(str(val))
                                    # Handle strings with currency symbols/commas
                                    cleaned = numeric_cleaner.sub('', str(val))
                                    try:
                                        return Decimal(cleaned)
                                    except:
                                        return None

                                # Try mapping first
                                column_name = mappings.get(field_id)
                                if column_name and column_name in df.columns:
                                    parsed = parse_decimal(row[column_name])
                                    if parsed is not None:
                                        return parsed
                                
                                # Fallback to standard names
                                fallbacks = {
                                    'estimated_cost': ['Estimated Cost'],
                                    'budget': ['Proposed Amount', 'Budget'],
                                }
                                for fallback in fallbacks.get(field_id, []):
                                    if fallback in df.columns:
                                        parsed = parse_decimal(row[fallback])
                                        if parsed is not None:
                                            return parsed
                                
                                return Decimal(str(default))
                            
                            # Get office code and find office
                            office_value = get_mapped_value('office')
                            logger.debug(f"Office value from row: {office_value}")
                            
                            # Find office by code first (highest priority)
                            office = Office.objects.filter(code__iexact=office_value).first()
                            
                            if not office:
                                # Try to find by name
                                office = Office.objects.filter(name__iexact=office_value).first()
                            
                            if not office:
                                # Try via linked_department
                                office = Office.objects.filter(linked_department__name__iexact=office_value).first()
                            
                            if not office:
                                # Try case-insensitive department name match
                                matching_dept = Department.objects.filter(name__iexact=office_value).first()
                                if matching_dept:
                                    office = Office.objects.filter(linked_department=matching_dept).first()

                                logger.info(f"Using user's office '{office.name}' for row {index + 1}")
                            
                            # Check if user has permission to create plan for this office
                            manage_filter = get_procurement_plan_filter(request.user, action='manage')
                            if office and manage_filter and not Office.objects.filter(id=office.id).filter(manage_filter).exists():
                                error_msg = f"Row {index + 1}: Permission denied to import for office '{office.name}'"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                                continue
                            
                            if not office and valid_departments and department not in valid_departments:
                                error_msg = f"Row {index + 1}: Invalid department/office '{department}'. Valid departments are: {', '.join(valid_departments)}"
                                logger.warning(error_msg)
                                errors.append(error_msg)
                                continue
                            
                             # Create procurement plan
                            plan_data = {
                                'policy_number': get_mapped_value('policy_number'),
                                'department': office.linked_department.name if office and office.linked_department else office_value,
                                'office': office,
                                'project_name': get_mapped_value('project_name'),
                                'project_description': get_mapped_value('project_description'),
                                'estimated_cost': get_mapped_numeric_value('estimated_cost', 0),
                                'budget': get_mapped_numeric_value('budget', 0),
                                'fiscal_year': get_mapped_value('fiscal_year', '2082/83'),
                                'program_number': get_mapped_value('program_number'),
                                'dept_index': get_mapped_value('program_number', '')[:10],
                                'stage': 'planning',
                                'status': 'draft',
                                'owner': request.user,
                            }
                            
                            logger.debug(f"Creating procurement plan with data: {plan_data}")
                            
                            # Create the procurement plan
                            plan = ProcurementPlan.objects.create(**plan_data)
                            logger.debug(f"Created procurement plan with ID: {plan.id}")
                            
                             # Create quarterly targets
                            for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
                                # Try various possible column names for quarterly targets
                                target_variations = [
                                    f'{quarter} Target', 
                                    f'{quarter.lower()} target', 
                                    f'{quarter}_target', 
                                    f'{quarter.lower()}_target',
                                    f'{quarter}',
                                ]
                                
                                target_value = None
                                for variation in target_variations:
                                    val = get_column_value(variation)
                                    if val and val.strip():
                                        target_value = val.strip()
                                        break
                                
                                if target_value:
                                    QuarterlyTarget.objects.create(
                                        procurement_plan=plan,
                                        quarter=quarter,
                                        target_details=target_value,
                                        status='Planned'
                                    )
                                    logger.debug(f"Created quarterly target for {quarter}")
                            
                            imported_count += 1
                            logger.debug(f"Successfully imported row {index + 1}")
                            
                        except Exception as e:
                            error_msg = f"Row {index + 1}: {str(e)}"
                            logger.error(f"Error processing row {index + 1}: {str(e)}", exc_info=True)
                            errors.append(error_msg)
                            continue
                
                # Clean up temporary file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info("Temporary file cleaned up")
                
                logger.info(f"Import completed. Imported: {imported_count}, Errors: {len(errors)}")
                
                return Response({
                    'success': True,
                    'imported_count': imported_count,
                    'total_rows': len(df),
                    'errors': errors,
                    'message': f'Successfully imported {imported_count} procurement plans'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error during import process: {str(e)}", exc_info=True)
                # Clean up temporary file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info("Temporary file cleaned up after error")
                raise e
                
        except Exception as e:
            logger.error(f"Fatal error in import view: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Import failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcurementImportValidateView(APIView):
    """
    Validate Excel file before import
    """
    permission_classes = [HasPermission('planning.excel')]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            logger.info("Starting procurement import validation")
            
            file = request.FILES.get('file')
            if not file:
                logger.error("No file provided in validation request")
                return Response(
                    {'error': 'No file provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Validating file: {file.name}, size: {file.size}")

            # Save file temporarily
            relative_path = default_storage.save(f'imports/validate_{file.name}', file)
            file_path = default_storage.path(relative_path)
            logger.info(f"Validation file saved to: {file_path}")
            
            try:
                # Read Excel file
                logger.info("Reading Excel file for validation")
                df = pd.read_excel(file_path)
                # Clean column names
                df.columns = [str(c).strip() for c in df.columns]
                logger.info(f"Excel file read for validation. Shape: {df.shape}, Columns: {list(df.columns)}")
                
                # Get mappings (if provided in validation)
                mappings = request.data.get('mappings', '{}')
                if isinstance(mappings, str):
                    try:
                        mappings = json.loads(mappings)
                    except:
                        mappings = {}
                
                # Regex to clean currency strings
                import re
                numeric_cleaner = re.compile(r'[^\d\.]+')

                # Validate data
                errors = []
                valid_rows = 0
                
                valid_departments = list(
                    Department.objects.values_list('name', flat=True)
                )
                
                for index, row in df.iterrows():
                    # Skip header row
                    if index == 0 and any(str(cell).lower() in ['department', 'policy no.', 'project name'] for cell in row):
                        logger.info("Skipping header row in validation")
                        continue
                    
                    row_errors = []
                    
                     # Helper function to safely get column value with mappings
                    def get_mapped_value(field_id, default=''):
                        column_name = mappings.get(field_id)
                        if column_name and column_name in df.columns:
                            value = row[column_name]
                            if pd.isna(value): return default
                            return str(value).strip()
                        
                        # Fallback to standard names
                        fallbacks = {
                            'policy_number': ['Policy No.', 'Policy Number'],
                            'project_name': ['Project Name'],
                            'project_description': ['Project Description', 'Description'],
                            'estimated_cost': ['Estimated Cost'],
                            'budget': ['Proposed Amount', 'Budget'],
                            'office': ['Office Code', 'Office', 'Department'],
                        }
                        for fallback in fallbacks.get(field_id, []):
                            if fallback in df.columns:
                                value = row[fallback]
                                if pd.isna(value): continue
                                return str(value).strip()
                        return default
                    
                    def get_mapped_numeric_value(field_id, default=0):
                        def parse_decimal(val):
                            if pd.isna(val): return None
                            if isinstance(val, (int, float, Decimal)):
                                return Decimal(str(val))
                            # Handle strings with currency symbols/commas
                            cleaned = numeric_cleaner.sub('', str(val))
                            try:
                                return Decimal(cleaned)
                            except:
                                return None

                        column_name = mappings.get(field_id)
                        if column_name and column_name in df.columns:
                            parsed = parse_decimal(row[column_name])
                            if parsed is not None:
                                return parsed
                        
                        fallbacks = {
                            'estimated_cost': ['Estimated Cost'],
                            'budget': ['Proposed Amount', 'Budget'],
                        }
                        for fallback in fallbacks.get(field_id, []):
                            if fallback in df.columns:
                                parsed = parse_decimal(row[fallback])
                                if parsed is not None:
                                    return parsed
                        return Decimal(str(default))
                    
                    # Check required fields
                    if not get_mapped_value('policy_number'):
                        row_errors.append('Policy Number is required')
                    
                    office_val = get_mapped_value('office')
                    if not office_val:
                        row_errors.append('Office/Department is required')
                    else:
                        # Check if it exists as an office code or name
                        office_exists = Office.objects.filter(Q(code__iexact=office_val) | Q(name__iexact=office_val)).exists()
                        if not office_exists:
                            office_exists = Office.objects.filter(linked_department__name__iexact=office_val).exists()
                        
                        if not office_exists and valid_departments and office_val not in valid_departments:
                            row_errors.append(f'Invalid office/department "{office_val}".')
                        
                        # Check permission for the office
                        if office_exists:
                            office_obj = Office.objects.filter(Q(code__iexact=office_val) | Q(name__iexact=office_val)).first()
                            if not office_obj:
                                office_obj = Office.objects.filter(linked_department__name__iexact=office_val).first()
                            
                            if office_obj:
                                manage_filter = get_procurement_plan_filter(request.user, action='manage')
                                if manage_filter and not Office.objects.filter(id=office_obj.id).filter(manage_filter).exists():
                                    row_errors.append(f'Permission denied to manage plans for office "{office_val}"')
                    
                    if not get_mapped_value('project_name'):
                        row_errors.append('Project Name is required')
                    
                    if not get_mapped_value('project_description'):
                        row_errors.append('Project Description is required')
                    
                    # Check numeric fields
                    try:
                        estimated_cost = get_mapped_numeric_value('estimated_cost', -1)
                        if estimated_cost < 0:
                            row_errors.append('Estimated Cost cannot be negative')
                    except:
                        row_errors.append('Estimated Cost must be a valid number')
                    
                    try:
                        budget = get_mapped_numeric_value('budget', -1)
                        if budget < 0:
                            row_errors.append('Proposed Amount cannot be negative')
                    except:
                        row_errors.append('Proposed Amount must be a valid number')
                    
                    if row_errors:
                        errors.append(f"Row {index + 1}: {'; '.join(row_errors)}")
                    else:
                        valid_rows += 1
                
                # Clean up temporary file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info("Validation temporary file cleaned up")
                
                logger.info(f"Validation completed. Valid rows: {valid_rows}, Errors: {len(errors)}")
                
                return Response({
                    'success': len(errors) == 0,
                    'total_rows': len(df),
                    'valid_rows': valid_rows,
                    'errors': errors,
                    'message': f'Validation complete. {valid_rows} valid rows, {len(errors)} errors found.'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error during validation process: {str(e)}", exc_info=True)
                # Clean up temporary file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info("Validation temporary file cleaned up after error")
                raise e
                
        except Exception as e:
            logger.error(f"Fatal error in validation view: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Validation failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
