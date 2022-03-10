{# This is a heavily customised version of towncrier's default template. #}

{#-
  Only render if there's any changes to show.

  This serves as a compatibility "hack" since we render unreleased news entries
  in our changelog with ``sphinxcontrib.towncrier``; which triggers a render even
  when there's no entries to be rendered.
#}
{% if sections[''] %}

{#- Heading for individual version #}
{{ versiondata.version }} ({{ versiondata.date }})
{{ top_underline * ((versiondata.version + versiondata.date)|length + 3) }}
{#

  The following loop will run exactly once, with ``section_name == ""``.

  This is due to the undocumented "sections" feature in towncrier.
  See https://github.com/twisted/towncrier/issues/61.

  We don't use this feature, and this template doesn't render the section
  heading for that reason.
#}
{% for section_name, entries_by_type in sections.items() -%}
{# Only show types with entries and ``showcontent = true``, using the order from pyproject.toml #}
{% for type_ in definitions if (sections[section_name][type_] and definitions[type_]['showcontent']) %}

{# Heading for individual types #}
{{ definitions[type_]['name'] }}
{{ underlines[0] * definitions[type_]['name']|length }}
{# This is the loop that generates individual entries #}
{% for message, issue_reference in sections[section_name][type_]|dictsort(by='value') %}

- {{ message }}
  {%- if type_ not in ["vendor", "process"] %} ({{ issue_reference|sort|join(', ') }}){% endif %}
{% endfor %}

{% else %}
{# We only have entries where the type has ``showcontent = true``. #}
No significant changes.

{% endfor -%}
{% endfor -%}
{% endif -%}
