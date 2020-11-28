"""A sphinx extension for collecting per doc feedback."""

from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict, List, Union

    from sphinx.application import Sphinx


DEFAULT_DOC_LINES_THRESHOLD = 250
RST_INDENT = 4
EMAIL_INDENT = 6


def _modify_rst_document_source_on_read(
        app: Sphinx,
        docname: str,
        source: List[str],
) -> None:
    """Add info block to top and bottom of each document source.

    This function modifies RST source in-place by adding an admonition
    block at the top and the bottom of each document right after it's
    been read from disk preserving :orphan: at top, if present.
    """
    admonition_type = app.config.docs_feedback_admonition_type
    big_doc_lines = app.config.docs_feedback_big_doc_lines
    escaped_email = app.config.docs_feedback_email.replace(' ', r'\ ')
    excluded_documents = set(app.config.docs_feedback_excluded_documents)
    questions_list = app.config.docs_feedback_questions_list

    valid_admonitions = {
        'attention', 'caution', 'danger', 'error', 'hint',
        'important', 'note', 'tip', 'warning', 'admonition',
    }

    if admonition_type not in valid_admonitions:
        raise ValueError(
            'Expected `docs_feedback_admonition_type` to be one of '
            f'{valid_admonitions} but got {admonition_type}.'
        )

    if not questions_list:
        raise ValueError(
            'Expected `docs_feedback_questions_list` to list questions '
            'but got none.'
        )

    if docname in excluded_documents:
        # NOTE: Completely ignore any document
        # NOTE: listed in 'docs_feedback_excluded_documents'.
        return

    is_doc_big = source[0].count('\n') >= big_doc_lines

    questions_list_rst = '\n'.join(
        f'{" " * RST_INDENT}{number!s}. {question}'
        for number, question in enumerate(questions_list, 1)
    )
    questions_list_urlencoded = (
        '\n'.join(
            f'\n{" " * RST_INDENT}{number!s}. {question} '
            for number, question in enumerate(
                chain(
                    (f'Document: {docname}. Page URL: https://', ),
                    questions_list,
                ),
            )
        ).
        rstrip('\r\n\t ').
        replace('\r', '%0D').
        replace('\n', '%0A').
        replace(' ', '%20')
    )

    admonition_msg = rf"""
    **Did this article help?**

    We are currently doing research to improve pip's documentation
    and would love your feedback.
    Please `email us`_ and let us know{{let_us_know_ending}}

{{questions_list_rst}}

    .. _email us:
       mailto:{escaped_email}\
       ?subject=[Doc:\ {docname}]\ Pip\ docs\ feedback\ \
       (URL\:\ https\://)\
       &body={questions_list_urlencoded}
    """
    let_us_know_ending = ':'

    info_block_bottom = (
        f'.. {admonition_type}::\n\t\t{admonition_msg.format_map(locals())}\n'
    )

    questions_list_rst = ''
    let_us_know_ending = (
        ' why you came to this page and what on it helped '
        'you and what did not.    '
        '(:issue:`Read more about this research <8517>`)'
    )
    info_block_top = '' if is_doc_big else (
        f'.. {admonition_type}::\n\t\t{admonition_msg.format_map(locals())}\n'
    )

    orphan_mark = ':orphan:'
    is_orphan = orphan_mark in source[0]
    if is_orphan:
        source[0] = source[0].replace(orphan_mark, '')
    else:
        orphan_mark = ''

    source[0] = '\n\n'.join((
        orphan_mark, info_block_top, source[0], info_block_bottom,
    ))


def setup(app: Sphinx) -> Dict[str, Union[bool, str]]:
    """Initialize the Sphinx extension.

    This function adds a callback for modifying the document sources
    in-place on read.

    It also declares the extension settings changable via :file:`conf.py`.
    """
    rebuild_trigger = 'html'  # rebuild full html on settings change
    app.add_config_value(
        'docs_feedback_admonition_type',
        default='important',
        rebuild=rebuild_trigger,
    )
    app.add_config_value(
        'docs_feedback_big_doc_lines',
        default=DEFAULT_DOC_LINES_THRESHOLD,
        rebuild=rebuild_trigger,
    )
    app.add_config_value(
        'docs_feedback_email',
        default='Docs UX Team <docs-feedback+ux/pip.pypa.io@pypa.io>',
        rebuild=rebuild_trigger,
    )
    app.add_config_value(
        'docs_feedback_excluded_documents',
        default=set(),
        rebuild=rebuild_trigger,
    )
    app.add_config_value(
        'docs_feedback_questions_list',
        default=(),
        rebuild=rebuild_trigger,
    )

    app.connect('source-read', _modify_rst_document_source_on_read)

    return {
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        'version': 'builtin',
    }
