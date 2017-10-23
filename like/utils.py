from django.core.urlresolvers import reverse
from django.db import models

from django.contrib.contenttypes.models import ContentType

from .models import Like


def name(obj):
    return "{0}.{1}".format(obj._meta.app_label, obj._meta.object_name)


def _allowed(model):
    if isinstance(model, models.Model):
        app_model = name(model)
    elif hasattr(model, "_meta"):
        app_model = name(model)
    elif isinstance(model, str):
        app_model = model
    else:
        return False
    return app_model


def widget_context(user, obj, request):
    ct = ContentType.objects.get_for_model(obj)
    like_count = Like.objects.filter(
        receiver_content_type=ct,
        receiver_object_id=obj.pk
    ).count()
    if like_count == 1:
        counts_text = 'Like'
    else:
        counts_text = 'Likes'

    can_like = user.is_authenticated

    ctx = {
        "can_like": can_like,
        "like_count": like_count,
        "counts_text": counts_text,
        "object": obj,
        "request": request
    }
    if can_like:

        liked = Like.objects.filter(
            sender=user,
            receiver_content_type=ct,
            receiver_object_id=obj.pk
        ).exists()

        if liked:
            like_text = 'Unlike'
            like_class = 'unlike'
        else:
            like_text = 'Like'
            like_class = 'like'

        ctx.update({
            "like_url": reverse("likes:like_toggle", kwargs={
                "content_type_id": ct.id,
                "object_id": obj.pk
            }),
            "liked": liked,
            "like_text": like_text,
            "like_class": like_class
        })
    else:
        ctx.update({
            "like_text": 'Like',
            "like_class": 'no_like',
        })
    return ctx
