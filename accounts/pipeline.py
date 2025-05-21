from social_core.pipeline.social_auth import associate_user as base_associate


def stop_if_social_exists(strategy, backend, uid, *args, **kwargs):
    """
    Stops the pipeline if a social account with the given UID and backend
    already exists. If such a social account is found and is linked to a user,
    returns them. If the social account exists but the user does not, deletes
    the broken social link.
    """
    from social_django.models import UserSocialAuth
    try:
        social = UserSocialAuth.objects.get(uid=uid, provider=backend.name)
        try:
            user = social.user  # Will raise DoesNotExist if user is broken
        except Exception:
            social.delete()
            return
        return {"social": social, "user": user}
    except UserSocialAuth.DoesNotExist:
        return


def safe_associate_user(backend, uid, user=None, social=None, *args, **kwargs):
    """
    Associates the authenticated social account with a user if not already
    associated. If the social account is already linked, simply returns the
    existing social instance. Otherwise, delegates the association to the
    default pipeline method.
    """
    if social:
        return {"social": social}
    return base_associate(backend, uid, user=user, *args, **kwargs)


def rebind_social_user(strategy, backend, uid, user=None, *args, **kwargs):
    """
    Rebinds a social account to a new user if needed. If the social account
    exists and is linked to a different user, updates the link to the given
    user. Does nothing if the social account does not exist.
    """
    from social_django.models import UserSocialAuth
    try:
        social = UserSocialAuth.objects.get(uid=uid, provider=backend.name)
        if user and social.user != user:
            social.user = user
            social.save()
    except UserSocialAuth.DoesNotExist:
        pass


def associate_by_email(strategy, details, user=None, *args, **kwargs):
    """
    Attempts to find and associate a user by their email address during social
    authentication. If a user with the provided email exists, returns the user
    for pipeline continuation. Skips this step if a user is already present.
    """
    if user:
        return
    email = details.get("email")
    if email:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            return {"user": user}
        except User.DoesNotExist:
            return
