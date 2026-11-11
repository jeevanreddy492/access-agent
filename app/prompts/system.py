EXTRACT_PROMPT = (
    "You read one message asking for access and extract two fields.\n"
    "- user_id: the user who should get the role, exactly as written (e.g. alice).\n"
    "- role_id: the role being requested, exactly as written (e.g. billing-admin).\n"
    "If a field is not clearly in the message, set it to null. Never guess or invent values."
)
