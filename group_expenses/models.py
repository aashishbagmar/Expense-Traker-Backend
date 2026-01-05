from django.db import models
from django.conf import settings
from django.db.models import JSONField


class Group(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="groups_created")

    def __str__(self):
        return self.name

class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True)  # Store member name directly
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.name:
            return f"{self.name} in {self.group.name}"
        return f"{self.user.username} in {self.group.name}"

class GroupExpense(models.Model):
    # Which group this expense belongs to
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses", default=1)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50)
    date = models.DateField()

    # Who paid for the expense
    paid_by = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name="expenses_paid")

    # Split details
    split_members = models.ManyToManyField(GroupMember, related_name="expenses_split")
    split_amount = models.DecimalField(max_digits=10, decimal_places=2)
    split_type = models.CharField(max_length=20, default="equal")  # e.g., equal/custom
    split_breakdown = JSONField(default=dict, blank=True)  # member_id -> amount
    
    def __str__(self):
        return self.description

class Settlement(models.Model):
    # Group and expense that generated the settlement
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="settlements", default=1)
    expense = models.ForeignKey('GroupExpense', on_delete=models.CASCADE, related_name="settlements", null=True, blank=True)

    # Who needs to pay (member) and how much
    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE, related_name="settlements")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    settled = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.member.user.username} - {self.amount}"

