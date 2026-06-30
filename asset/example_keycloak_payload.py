payload = {
    "exp": 1765598462,
    "iat": 1765598162,
    "auth_time": 1765597006,
    "jti": "onrtrt:10928cb0-4f4e-66ff-0aef-5b67c2a9b5a0",
    "iss": "http://localhost:8080/realms/gantry",
    "aud": "account",
    "sub": "809da58b-19ff-48c9-8037-5553b8b86a90",
    "typ": "Bearer",
    "azp": "gantry-frontend",
    "sid": "64da6118-8f03-85a5-8793-01145bac60a2",
    "acr": "0",
    "allowed-origins": ["http://localhost:3000"],
    "realm_access": {
        "roles": [
            "offline_access",
            "default-roles-gantry",
            "uma_authorization",
        ]
    },
    "resource_access": {
        "account": {
            "roles": ["manage-account", "manage-account-links", "view-profile"]
        }
    },
    "scope": "openid email profile",
    "email_verified": False,
    "name": "thong nguyen",
    "preferred_username": "test",
    "given_name": "thong",
    "family_name": "nguyen",
    "email": "test@test.com",
}
