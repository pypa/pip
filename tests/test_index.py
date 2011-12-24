from pip.index import package_to_requirement, HTMLPage


def test_package_name_should_be_converted_to_requirement():
    """
    Test that it translates a name like Foo-1.2 to Foo==1.3
    """
    assert package_to_requirement('Foo-1.2') == 'Foo==1.2'
    assert package_to_requirement('Foo-dev') == 'Foo==dev'
    assert package_to_requirement('Foo') == 'Foo'


def test_html_page_should_be_able_to_scrap_rel_links():
    """
    Test scraping page looking for url in href
    """
    page = HTMLPage("""
        <!-- The <th> elements below are a terrible terrible hack for setuptools -->
        <li>
        <strong>Home Page:</strong>
        <!-- <th>Home Page -->
        <a href="http://supervisord.org/">http://supervisord.org/</a>
        </li>""", "supervisor")

    links = list(page.scraped_rel_links())
    assert len(links) == 1
    assert links[0].url == 'http://supervisord.org/'

