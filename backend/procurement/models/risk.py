from django.db import models
from django.utils import timezone
from users.models import CustomUser


class ProcurementRisk(models.Model):
    RISK_TYPES = [
        ('financial', 'Financial Risk'),
        ('technical', 'Technical Risk'),
        ('schedule', 'Schedule Risk'),
        ('vendor', 'Vendor Risk'),
        ('regulatory', 'Regulatory Risk'),
        ('quality', 'Quality Risk'),
        ('security', 'Security Risk'),
        ('operational', 'Operational Risk'),
        ('market', 'Market Risk'),
        ('legal', 'Legal Risk'),
    ]
    
    PROBABILITY_LEVELS = [
        ('very_low', 'Very Low (1-10%)'),
        ('low', 'Low (11-30%)'),
        ('medium', 'Medium (31-60%)'),
        ('high', 'High (61-80%)'),
        ('very_high', 'Very High (81-100%)'),
    ]
    
    IMPACT_LEVELS = [
        ('negligible', 'Negligible'),
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('identified', 'Identified'),
        ('active', 'Active'),
        ('mitigated', 'Mitigated'),
        ('resolved', 'Resolved'),
        ('accepted', 'Accepted'),
    ]

    # Core relationships
    procurement_plan = models.ForeignKey(
        'ProcurementPlan',
        related_name='risks',
        on_delete=models.CASCADE
    )
    
    # Risk details
    risk_title = models.CharField(max_length=200)
    risk_description = models.TextField()
    risk_type = models.CharField(max_length=20, choices=RISK_TYPES)
    
    # Risk assessment
    probability = models.CharField(max_length=15, choices=PROBABILITY_LEVELS)
    impact = models.CharField(max_length=15, choices=IMPACT_LEVELS)
    risk_score = models.DecimalField(max_digits=4, decimal_places=2, help_text="Calculated risk score")
    
    # Mitigation
    mitigation_strategy = models.TextField(help_text="Strategy to mitigate this risk")
    mitigation_actions = models.JSONField(default=list, blank=True, help_text="Specific actions to take")
    
    # Status and ownership
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='identified')
    owner = models.ForeignKey(
        CustomUser,
        related_name='owned_risks',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Timeline
    identified_date = models.DateTimeField(auto_now_add=True)
    target_resolution_date = models.DateField(null=True, blank=True)
    actual_resolution_date = models.DateField(null=True, blank=True)
    
    # Additional tracking
    cost_impact = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    schedule_impact_days = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-risk_score', '-created_at']
        verbose_name = "Procurement Risk"
        verbose_name_plural = "Procurement Risks"

    def __str__(self):
        return f"{self.procurement_plan.policy_number} - {self.risk_title}"

    def calculate_risk_score(self):
        """Calculate numerical risk score based on probability and impact"""
        prob_scores = {
            'very_low': 1, 'low': 2, 'medium': 3, 'high': 4, 'very_high': 5
        }
        impact_scores = {
            'negligible': 1, 'minor': 2, 'moderate': 3, 'major': 4, 'critical': 5
        }
        
        prob_score = prob_scores.get(self.probability, 3)
        impact_score = impact_scores.get(self.impact, 3)
        
        return prob_score * impact_score

    def get_risk_level(self):
        """Get risk level based on calculated score"""
        score = float(self.risk_score)
        if score >= 20:
            return 'critical'
        elif score >= 15:
            return 'high'
        elif score >= 9:
            return 'medium'
        elif score >= 4:
            return 'low'
        else:
            return 'very_low'

    def save(self, *args, **kwargs):
        # Auto-calculate risk score
        self.risk_score = self.calculate_risk_score()
        super().save(*args, **kwargs)