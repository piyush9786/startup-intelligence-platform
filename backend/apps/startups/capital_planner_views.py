"""
API views for the AI Capital Planner.

Endpoints:
  GET  /api/v1/startup-capital-plans/current/
       Retrieve the latest capital plan for the founder's current startup profile.

  POST /api/v1/startup-capital-plans/generate/
       Generate a new capital plan snapshot given input financial figures.
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.startups.models import StartupCapitalPlan, StartupProfile

from .capital_planner_serializers import (
    StartupCapitalPlanGenerateSerializer,
    StartupCapitalPlanSerializer,
)
from .services.capital_planner_service import generate_startup_capital_plan

logger = logging.getLogger(__name__)


def _get_current_profile(user) -> StartupProfile | None:
    return (
        StartupProfile.objects.filter(owner=user)
        .order_by("-created_at")
        .first()
    )


class StartupCapitalPlanCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = _get_current_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No startup profile found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        plan = (
            StartupCapitalPlan.objects.filter(
                owner=request.user,
                startup_profile=profile,
            )
            .order_by("-created_at")
            .first()
        )

        if plan is None:
            return Response(
                {"detail": "No capital plan generated yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StartupCapitalPlanSerializer(plan)
        return Response(serializer.data)


class StartupCapitalPlanGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = _get_current_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No startup profile found. Complete your startup profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = StartupCapitalPlanGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        plan = generate_startup_capital_plan(
            owner=request.user,
            profile=profile,
            available_capital=data["available_capital"],
            monthly_revenue=data["monthly_revenue"],
            fixed_costs=data["fixed_costs"],
            variable_costs=data["variable_costs"],
        )

        out = StartupCapitalPlanSerializer(plan)
        return Response(out.data, status=status.HTTP_201_CREATED)
