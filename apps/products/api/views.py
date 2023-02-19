import asyncio
import concurrent.futures

import requests
from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .serializers import UserSerializer

User = get_user_model()


async def fetch_ip():
    await asyncio.sleep(3)
    return "123.42.941"


def fetch_headers():
    response = requests.get("http://httpbin.org/headers")
    print(response.status_code)
    return response.json()


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    @action(detail=False, methods=["get"])
    def ip(self, request):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ip = loop.run_until_complete(fetch_ip())
        return Response({"result": ip})

    @action(detail=False, methods=["get"])
    def headers(self, request):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_headers) for _ in range(2)]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        return Response({"result": "ok"})
