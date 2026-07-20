from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schemes.models import Scheme

from .engine import evaluate_rule
from .serializers import EligibilityRequestSerializer


class EligibilityEvaluateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EligibilityRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scheme = Scheme.objects.select_related("current_version").get(
            id=serializer.validated_data["scheme_id"]
        )
        if scheme.current_version is None:
            return Response({"detail": "Scheme has no published current version."}, status=409)

        matched, failed, unknown = [], [], []
        for rule in scheme.current_version.eligibility_rules.all():
            result = evaluate_rule(
                serializer.validated_data["profile"],
                rule.field_path,
                rule.operator,
                rule.expected_value,
            )
            payload = {
                "rule_id": str(rule.id),
                "field_path": result.field_path,
                "operator": result.operator,
                "expected": result.expected,
                "actual": result.actual,
                "mandatory": rule.mandatory,
                "evidence": rule.evidence_text,
            }
            {"matched": matched, "failed": failed, "unknown": unknown}[result.status].append(
                payload
            )

        mandatory_failures = [item for item in failed if item["mandatory"]]
        mandatory_unknowns = [item for item in unknown if item["mandatory"]]
        if mandatory_failures:
            outcome = "ineligible"
        elif mandatory_unknowns:
            outcome = "insufficient_information"
        else:
            outcome = "eligible"

        return Response(
            {
                "scheme_id": str(scheme.id),
                "scheme_name": scheme.canonical_name,
                "result": outcome,
                "matched_rules": matched,
                "failed_rules": failed,
                "unknown_rules": unknown,
            }
        )
