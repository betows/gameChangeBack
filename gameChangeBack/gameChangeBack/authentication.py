from arccanet.jwt import JWTAuthentication


class CustomAuthentication(JWTAuthentication):

    def authenticate(self, request):
        try:
            return super(CustomAuthentication, self).authenticate(request)
        except Exception:
            return None
