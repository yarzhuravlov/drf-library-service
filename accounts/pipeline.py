from social_core.pipeline.social_auth import associate_user as base_associate

def safe_associate_user(backend, uid, user=None, social=None, *args, **kwargs):
    if social:
        return {"social": social}
    return base_associate(backend, uid, user=user, *args, **kwargs)