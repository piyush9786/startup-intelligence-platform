from rest_framework import status
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CurrentUserSerializer,
    FounderRegistrationSerializer,
)


class FounderRegistrationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = FounderRegistrationSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            FounderRegistrationSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            CurrentUserSerializer(request.user).data,
        )
