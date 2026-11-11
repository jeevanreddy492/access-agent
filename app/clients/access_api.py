# Fake access-request API. Later, a real HTTP call goes here.

TOKENS = {
    "tok-alice": {"access:request"},   # alice can request access
    "tok-bob": set(),                  # bob cannot
}

# roles each user already has
ENTITLEMENTS = {
    "alice": ["report-viewer"],
    "bob": [],
}


def post_access_request(token, user_id, role_id):
    if token not in TOKENS:
        return 401, {"detail": "invalid token"}
    if "access:request" not in TOKENS[token]:
        return 403, {"detail": "not allowed"}
    if role_id in ENTITLEMENTS.get(user_id, []):
        return 409, {"detail": "user already has this role"}
    return 201, {"request_id": "REQ-1"}