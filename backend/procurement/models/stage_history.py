from django.db import models
from users.models import CustomUser


class StageHistory(models.Model):
    procurement_plan = models.ForeignKey('ProcurementPlan', related_name='stage_history', on_delete=models.CASCADE)
    previous_stage = models.CharField(max_length=20, blank=True)
    new_stage = models.CharField(max_length=20)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name = "Stage History"
        verbose_name_plural = "Stage Histories"
        
    def __str__(self):
        direction = f"{self.previous_stage} → {self.new_stage}" if self.previous_stage else f"Started at {self.new_stage}"
        return f"{self.procurement_plan.policy_number}: {direction}"