from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .audit import get_current_audit_user
from .models import AuditLog

AUDIT_EXCLUDED_FIELDS = {"created_at", "updated_at", "created_by", "updated_by"}


def _is_website_model(instance):
    return instance._meta.app_label == "website"


def _is_auditable_instance(instance):
    return (
        _is_website_model(instance)
        and not isinstance(instance, AuditLog)
        and hasattr(instance, "created_by_id")
        and hasattr(instance, "updated_by_id")
    )


def _current_actor():
    user = get_current_audit_user()
    if getattr(user, "is_authenticated", False):
        return user
    return None


def _should_invalidate_public_cache(instance):
    return _is_website_model(instance) and not isinstance(instance, (AuditLog,)) and instance.__class__.__name__ != "ContactSubmission"


def _track_changed_fields(instance):
    if instance._state.adding or not instance.pk:
        instance._audit_changed_fields = []
        return

    try:
        previous = instance.__class__._default_manager.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        instance._audit_changed_fields = []
        return

    changed_fields = []
    for field in instance._meta.concrete_fields:
        if field.primary_key or field.name in AUDIT_EXCLUDED_FIELDS:
            continue
        if getattr(previous, field.attname) != getattr(instance, field.attname):
            changed_fields.append(field.name)
    instance._audit_changed_fields = changed_fields


@receiver(pre_save)
def attach_audit_user(sender, instance, **kwargs):
    if not _is_auditable_instance(instance):
        return

    actor = _current_actor()
    if actor:
        if instance._state.adding and not instance.created_by_id:
            instance.created_by = actor
        instance.updated_by = actor

    _track_changed_fields(instance)


@receiver(post_save)
def create_audit_log_on_save(sender, instance, created, **kwargs):
    if not _is_auditable_instance(instance):
        return

    if _should_invalidate_public_cache(instance):
        cache.clear()

    actor = _current_actor()
    if not actor:
        return

    details = {}
    changed_fields = getattr(instance, "_audit_changed_fields", [])
    if changed_fields:
        details["changed_fields"] = changed_fields

    AuditLog.objects.create(
        action=AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE,
        model_label=instance._meta.label,
        object_pk=str(instance.pk),
        object_repr=str(instance)[:255],
        actor=actor,
        actor_username=actor.get_username(),
        details=details,
    )


@receiver(post_delete)
def create_audit_log_on_delete(sender, instance, **kwargs):
    if not _is_auditable_instance(instance):
        return

    if _should_invalidate_public_cache(instance):
        cache.clear()

    actor = _current_actor()
    if not actor:
        return

    AuditLog.objects.create(
        action=AuditLog.ACTION_DELETE,
        model_label=instance._meta.label,
        object_pk=str(instance.pk),
        object_repr=str(instance)[:255],
        actor=actor,
        actor_username=actor.get_username(),
        details={},
    )
