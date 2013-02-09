

def test_simple_output():
    """
    Basic behaviour of output formating.

    """
    out = OutputFormat('- {project_name}')
    result = out.format_context({
        'project_name': 'pip'
    })
    assert result == '- pip'


def test_conditional_output():
    """
    Used to format properly when missing values.

    """
    out = OutputFormat('- {project_name}')
    result = out.format_context({
        'project_name': 'pip'
    })
    assert result == '- pip'
