{%- macro sectitle(version, project_date, underline) -%}
.. _v{{ version.replace('.', '-') }}:

{% set title = version + ' (' + project_date + ')' %}
{{ title }}
{{ underline * title|length }}
{%- endmacro -%}

{%- macro deftitle(version, title, underline) -%}
.. _v{{ version.replace('.', '-') }}-{{ title.lower().replace(' ', '-') }}:

{{ title }}
{{ underline * title|length }}
{%- endmacro -%}

{%- set underline = "=" -%}
{{ sectitle(versiondata.version, versiondata.date, underline) }}
{% for section in sections %}
{%- set underline = "-" -%}
{% if section %}
{{ section }}
{{ underline * section|length }}
{%- set underline = "~" -%}

{% endif %}
{% if sections[section] %}
{% for category, val in definitions.items() if category in sections[section] and category != 'trivial' %}

{{ deftitle(versiondata.version, definitions[category]['name'], underline) }}

{% if definitions[category]['showcontent'] %}
{% for text, values in sections[section][category]|dictsort(by='value') %}
- {{ text }}{% if category != 'vendor' and category != 'process' %} ({{ values|sort|join(', ') }}){% endif %}

{% endfor %}
{% else %}
- {{ sections[section][category]['']|sort|join(', ') }}


{% endif %}
{% if sections[section][category]|length == 0 %}

No significant changes.


{% else %}
{% endif %}
{% endfor %}
{% else %}

No significant changes.


{% endif %}
{% endfor %}
