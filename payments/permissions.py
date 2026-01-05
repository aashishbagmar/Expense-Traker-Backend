from rest_framework.views import APIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

class IsPremiumUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_premium

class PremiumReportView(APIView):
    permission_classes = [IsAuthenticated, IsPremiumUser]

    def get(self, request):
        # Example premium-only feature
        return Response({"message": "This is a premium-only report."})
