from rest_framework import serializers
from .models import Group, GroupExpense, GroupMember, Settlement


from rest_framework import serializers
from .models import Group, GroupExpense, GroupMember, Settlement

class GroupSerializer(serializers.ModelSerializer):
    # Provide basic member info for the frontend dropdown without altering other payloads
    members = serializers.SerializerMethodField()
    expenses = serializers.SerializerMethodField()
    totalExpense = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'created_at', 'members', 'expenses', 'totalExpense']
        read_only_fields = ['id', 'created_at', 'members', 'expenses', 'totalExpense']

    def get_members(self, obj):
        members = obj.groupmember_set.all()
        expenses = obj.expenses.all()
        
        # Calculate balance for each member
        member_balances = {}
        for member in members:
            paid_total = sum(
                float(exp.amount) for exp in expenses if exp.paid_by_id == member.id
            )
            owed_total = sum(
                float(exp.split_breakdown.get(str(member.id), exp.split_breakdown.get(member.id, exp.split_amount)))
                for exp in expenses 
                if member in exp.split_members.all()
            )
            # Balance = what they paid - what they owe
            # Positive = they are owed money, Negative = they owe money
            member_balances[member.id] = paid_total - owed_total
        
        return [
            {
                'id': member.id,
                'name': member.name or (member.user.username if member.user else ''),
                'email': member.user.email if member.user else '',
                'balance': round(member_balances.get(member.id, 0), 2)
            }
            for member in members
        ]
    
    def get_expenses(self, obj):
        expenses = obj.expenses.all()
        return [
            {
                'id': expense.id,
                'description': expense.description,
                'amount': float(expense.amount),
                'category': expense.category,
                'date': expense.date.isoformat(),
                'paidBy': expense.paid_by.name if expense.paid_by and expense.paid_by.name else '',
                'paidById': expense.paid_by_id,
                'splitType': expense.split_type,
                'splitAmount': float(expense.split_amount),
                'splitMembers': list(expense.split_members.values_list('id', flat=True)),
                'splitBreakdown': expense.split_breakdown,
            }
            for expense in expenses
        ]
    
    def get_totalExpense(self, obj):
        total = sum(expense.amount for expense in obj.expenses.all())
        return float(total)

    def create(self, validated_data):
        # Extract members array from request data (frontend sends member names as strings)
        members_data = self.context['request'].data.get('members', [])
        request_user = self.context['request'].user if self.context.get('request') else None
        
        # Create the group first
        validated_data['created_by'] = request_user
        group = Group.objects.create(**validated_data)
        
        # Create GroupMember records for each member name
        for member_name in members_data:
            if member_name:  # Skip empty strings
                GroupMember.objects.create(
                    group=group,
                    name=member_name,
                    user=None  # No user association for now
                )
        
        return group

    def update(self, instance, validated_data):
        # Update basic fields
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()

        # Handle member additions/updates if provided
        members_data = self.context['request'].data.get('members')
        if members_data is not None:
            existing_members = {m.id: m for m in instance.groupmember_set.all()}
            keep_ids = set()

            for item in members_data:
                member_id = None
                member_name = ''
                
                # Handle both dict and string formats
                if isinstance(item, dict):
                    member_id = item.get('id')
                    member_name = item.get('name', '').strip()
                else:
                    member_name = str(item).strip()

                if not member_name:
                    continue

                # If has ID and exists, update it
                if member_id and member_id in existing_members:
                    member = existing_members[member_id]
                    member.name = member_name
                    member.save()
                    keep_ids.add(member.id)
                # Otherwise create new member
                elif not member_id:
                    new_member = GroupMember.objects.create(
                        group=instance,
                        name=member_name,
                        user=None
                    )
                    keep_ids.add(new_member.id)

            # Delete members not in keep_ids (only if IDs were provided in payload)
            if any(isinstance(item, dict) and item.get('id') for item in members_data):
                for member in list(instance.groupmember_set.all()):
                    if member.id not in keep_ids:
                        # Check if member has paid or split expenses
                        if not member.expenses_paid.exists() and not member.expenses_split.exists():
                            member.delete()

        return instance

class GroupExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupExpense
        fields = [
            'id', 'group', 'description', 'amount', 'category', 'date',
            'paid_by', 'split_members', 'split_amount', 'split_type', 'split_breakdown'
        ]
    
    def create(self, validated_data):
        # Extract split_members before creating the expense
        split_members_data = validated_data.pop('split_members', [])
        raw_breakdown = validated_data.pop('split_breakdown', None) or {}
        split_breakdown_data = {str(k): float(v) for k, v in raw_breakdown.items()} if raw_breakdown else {}
        
        # If no split_members provided, default to all members of the group
        if not split_members_data:
            group = validated_data.get('group')
            split_members_data = list(GroupMember.objects.filter(group=group))

        # Build split_breakdown if not provided (equal split)
        if not split_breakdown_data:
            amount = validated_data.get('amount') or 0
            per_member = float(amount) / (len(split_members_data) or 1)
            split_breakdown_data = {str(member.id): round(per_member, 2) for member in split_members_data}
        
        # Create the expense
        expense = GroupExpense.objects.create(**validated_data)
        
        # Add split members (ManyToMany relationship)
        expense.split_members.set(split_members_data)

        # Persist breakdown mapping
        expense.split_breakdown = split_breakdown_data
        expense.save()
        
        return expense

    def update(self, instance, validated_data):
        # Allow updating split members along with other fields
        split_members_data = validated_data.pop('split_members', None)
        raw_breakdown = validated_data.pop('split_breakdown', None)
        split_breakdown_data = {str(k): float(v) for k, v in raw_breakdown.items()} if raw_breakdown is not None else None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if split_members_data is not None:
            instance.split_members.set(split_members_data)

        if split_breakdown_data is not None:
            instance.split_breakdown = split_breakdown_data
            instance.save()

        return instance

class GroupMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupMember
        fields = ['id', 'group', 'user', 'joined_at']

class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ['id', 'group', 'expense', 'member', 'amount', 'settled']
