# backend/utils/message_templates.py

def get_committee_sms_template(name, role, committee_type, policy_number, project_name):
    """
    Template for SMS notification when a user is added to a committee.
    """
    return (
        f"Dear {name}, you have been appointed as a {role} of the {committee_type} "
        f" ({project_name}). "
        f"Please check your email for the official formation letter."
    )

def get_committee_email_template(name, role, committee_name, policy_number, project_name):
    """
    Template for Email notification when a user is added to a committee.
    """
    return (
        f"Dear {name},\n\n"
        f"We are pleased to inform you that you have been appointed as a {role} of the '{committee_name}' "
        f"({project_name}).\n\n"
        f"Your involvement is crucial for the successful execution of this procurement process. "
        f"Please find the attached official committee formation letter for your reference and further action.\n\n"
        f"Best regards,\n"
        f"Procurement Management System"
    )

def get_otp_sms_template(otp_code):
    """
    Standard template for OTP SMS messages.
    """
    return f"Your OTP for Procurement Management System is {otp_code}. Do not share it with anyone."
