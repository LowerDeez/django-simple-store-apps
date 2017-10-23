from django import template
from django.template import loader

from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType

from ..models import Like
from ..utils import widget_context, _allowed


register = template.Library()


@register.simple_tag(takes_context=True)
def likes_widget(context, user, obj, template_name="like.html"):
    """
    Usage:
        {% load like_tags %}
        ...
        {% likes_widget request.user post %}
    or
        {% likes_widget request.user post "pinax/likes/_widget_brief.html" %}
    """
    request = context["request"]
    return loader.get_template(template_name).render(
        widget_context(user, obj, request))


@register.simple_tag
def who_likes(obj):
    """
    Usage:
        {% who_likes obj as var %}
    """
    return Like.objects.filter(
        receiver_content_type=ContentType.objects.get_for_model(obj),
        receiver_object_id=obj.pk
    )


@register.simple_tag
def likes(user, *models):
    """
    Usage:
        {% likes user as var %}
    Or
        {% likes user [model1, model2] as var %}
    """
    content_types = []
    model_list = models
    for model in model_list:
        if not _allowed(model):
            continue
        app, model = model.split(".")
        content_types.append(
            ContentType.objects.get(app_label=app, model__iexact=model)
        )
    return Like.objects.filter(sender=user, receiver_content_type__in=content_types)


@register.simple_tag
@register.filter
def likes_count(obj):
    """
    Usage:
        {% likes_count obj %}
    or
        {% likes_count obj as var %}
    or
        {{ obj|likes_count }}
    """
    return Like.objects.filter(
        receiver_content_type=ContentType.objects.get_for_model(obj),
        receiver_object_id=obj.pk
    ).count()

