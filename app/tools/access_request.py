from app.clients import access_api


def submit_access_request(user_token, user_id, role_id):
    status, body = access_api.post_access_request(user_token, user_id, role_id)
    if status >= 400:
        return {"status": status, "error": body["detail"]}
    return {"status": status, "request_id": body["request_id"]}