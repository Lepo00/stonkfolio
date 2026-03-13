from rest_framework import generics, permissions
from rest_framework.throttling import AnonRateThrottle

from .models import User
from .serializers import RegisterSerializer, UserSerializer


class RegisterThrottle(AnonRateThrottle):
    rate = "5/hour"


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterThrottle]


class UserMeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
