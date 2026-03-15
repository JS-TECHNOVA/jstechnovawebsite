import json


def _compact_schema(value):
    if isinstance(value, dict):
        cleaned = {key: _compact_schema(item) for key, item in value.items()}
        return {key: item for key, item in cleaned.items() if item not in ("", None, [], {})}
    if isinstance(value, list):
        cleaned = [_compact_schema(item) for item in value]
        return [item for item in cleaned if item not in ("", None, [], {})]
    return value


def _absolute_url(request, value):
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return request.build_absolute_uri(value)


def _compose_title(title, site_name):
    base_title = (title or site_name or "").strip()
    site_title = (site_name or "").strip()
    if not base_title:
        return ""
    if not site_title or base_title.lower() == site_title.lower():
        return base_title
    return f"{base_title} | {site_title}"


def build_seo_context(
    request,
    *,
    site_settings=None,
    source=None,
    fallback_title="",
    fallback_description="",
    fallback_keywords="",
    fallback_image_url="",
    og_type="website",
    schema=None,
):
    site_name = getattr(site_settings, "site_name", "") or "JS Technova"
    meta_title = getattr(source, "seo_meta_title", "") or fallback_title or site_name
    meta_description = getattr(source, "seo_meta_description", "") or fallback_description
    keywords = getattr(source, "seo_keywords", "") or fallback_keywords
    canonical_url = _absolute_url(
        request,
        getattr(source, "seo_canonical_url", "") or request.get_full_path(),
    )
    og_title = getattr(source, "seo_og_title", "") or meta_title
    og_description = getattr(source, "seo_og_description", "") or meta_description
    og_image_url = _absolute_url(
        request,
        getattr(source, "seo_og_image_url", "") or fallback_image_url,
    )
    twitter_title = getattr(source, "seo_twitter_title", "") or og_title
    twitter_description = getattr(source, "seo_twitter_description", "") or og_description
    json_ld = getattr(source, "seo_schema_json_ld", "") or ""
    if not json_ld and schema:
        json_ld = json.dumps(_compact_schema(schema), ensure_ascii=False)

    return {
        "title": _compose_title(meta_title, site_name),
        "site_name": site_name,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "keywords": keywords,
        "canonical_url": canonical_url,
        "robots": getattr(source, "seo_robots", "") or "index,follow",
        "og_title": og_title,
        "og_description": og_description,
        "og_image_url": og_image_url,
        "og_url": canonical_url,
        "og_type": og_type,
        "twitter_card": getattr(source, "seo_twitter_card", "") or "summary_large_image",
        "twitter_title": twitter_title,
        "twitter_description": twitter_description,
        "twitter_image_url": og_image_url,
        "json_ld": json_ld,
    }
