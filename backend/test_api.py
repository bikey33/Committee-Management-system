import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pms.settings') # Change if needed
django.setup()
from committee.serializers import CommitteeSerializer
data = {
    "name": "Test",
    "purpose": "Test",
    "committee_type": "review",
    "formation_date": "",
    "office": "",
    "members": [{"employeeId": "123", "role": "member"}]
}
s = CommitteeSerializer(data=data)
print("Is Valid:", s.is_valid())
if not s.is_valid():
    print("Errors:", s.errors)
