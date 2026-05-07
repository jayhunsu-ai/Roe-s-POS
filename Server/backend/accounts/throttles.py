from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = 'login'

    def get_cache_key(self, request, view):
        if request.method != 'POST':
            return None

        identifier = request.data.get('email')
        if identifier:
            identifier = identifier.strip().lower()
        else:
            identifier = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': identifier,
        }
