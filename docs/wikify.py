#!/usr/bin/env python
"""
wikify your texts! micro-framework for text wikification

goals - avoid conflicts between text modifications rules
        and be easy to extend and debug

operation (flat algorithm)
 for each region
   - find region in processed text
   - process region matched
   - exclude processed text from further processing
 (flat algorithm) doesn't process nested markup,
  for example *`bold preformatted text`*


example - replace all wiki:something with HTML links
 [x] wrap text into list with single item
 [x] split text into three parts using regexp `wiki:\w+`
 [x] copy 1st part (not-matched) into the resulting list
 [x] replace matched part with link, insert (processed)
     into the resulting list
 [ ] process (the-rest) until text list doesn't change

 [ ] repeat the above for the rest of rules, skipping
     (processed) parts

 [x] reassemble text from the list


0.1  - proof of concept, production ready, no API sugar
       and optimizations
0.2  - helper to build regexp based rules
0.3  - allow callables in replacements for regexp rules
0.4  - accept single rule in wikify in addition to list
0.5  - helper to build rules to link tracker references
0.6  - flatten nested rule lists
0.7  - fixed major flaw in text replacements mapping
0.8  - python 3 compatibility
0.9  - case insensitive match in tracker link rule

1.0  - use wikify as Sphinx extension
"""

__author__ = "anatoly techtonik <techtonik@gmail.com>"
__license__ = "Public Domain"
__version__ = "1.0"
__site__ = "https://bitbucket.org/techtonik/wikify/"


DEBUG = False

# --- this block allows to use wikify as Sphinx extension ---

"""
Example:

extensions = ['wikify']

# setup wikify extension to convert issue references to links
from wikify import create_regexp_rule, create_tracker_link_rule
wikify_html_rules = [
    # PR #123 or pull request #123
    create_regexp_rule('(PR|pull request)\s+#(\d+)',
        '<a href="https://github.com/pypa/pip/pull/\\2">\\0</a>'),
    # issue #123 or just #123
    create_tracker_link_rule('https://github.com/pypa/pip/issues/')
]
wikify_html_pages = ['news']
"""

def setup(app):
  """ this wikify extension works as filter for HTML content so far """

  # [ ] mask for pages a rule applies to
  # [ ] or named sets of rules and separate list of pages
  # [ ] or set the rules directly inside page context

  # define extension variables
  app.add_config_value('wikify_html_rules', [], 'html')
  # list of page names to process
  app.add_config_value('wikify_html_pages', [], 'html')

  # http://sphinx-doc.org/extdev/appapi.html#event-html-page-context
  app.connect('html-page-context', sphinx_html_page_context)

  # there is also a source-read event, but it doesn't work for includes
  # https://bitbucket.org/birkenfeld/sphinx/issue/1415/source-read-callback-doesnt-resolve
  app.connect('source-read', sphinx_source_read)


def sphinx_html_page_context(app, pagename, templatename, context, doctree):
  """ replacemens in rendered HTML, which is available as context['body'] """
  if not app.config.wikify_html_rules:
    return

  if (pagename in app.config.wikify_html_pages) or not app.config.wikify_html_pages:
    #import pprint
    #print(ascii(context['body']))
    print('..wikifying %s' % pagename)
    context['body'] = wikify(context['body'], app.config.wikify_html_rules)

def sphinx_source_read(app, docname, source):
  pass # print(docname)

# /-- end Sphinx extension ---


# --- define rules ---

# rule is a function that takes text and returns either
# None (not mathed) or a list of three text items:
# [ not-matched, processed, the-rest ]

import re

# examples of simple rules
def rule_link_wikify(text):
  """ replace `wikify` text with a link to repository """
  if not 'wikify' in text:
    return None
  res = text.split('wikify', 1)
  url = '<a href="%s">wikify</a>' % __site__
  return (res[0], url, res[1])

def rule_stub_links(text):
  """ replace urls with [link] stubs """
  linkre = re.compile('https?://\S+')
  # [ ] test with commas and other URL escaped symbols
  match = linkre.search(text)
  if match == None:
    return None
  return (text[:match.start()], "[link]", text[match.end():])


def subst_backrefs(pattern, groups):
  """ utility function to replace backreferences such as \0, \1
      in the given `pattern` string with elements from
      the `groups` tuple
  """
  backrefs = re.findall(r'\\\d{1,2}', pattern)
  for b in backrefs:
    pattern = pattern.replace(b, groups[int(b[1:])])
  return pattern


# helper to build regexp based rules
def create_regexp_rule(search, replace=r'\0'):
  """ helper that returns rule for wikify. `search` is regexp, and
      `replace` can be string with backreferences (like \0, \1 etc.)
      or a callable that receives `re.MatchObject`.
  """
  search = re.compile(search)

  def regexp_rule(text):
      # saving for debug
      _research = search
      _replace = replace

      match = _research.search(text)
      if match == None:
        return None

      if callable(_replace):
        replaced = _replace(match)
      else:
        # match.groups() doesn't return whole match as a 1st element
        groups = (match.group(0),) + match.groups()
        replaced = subst_backrefs(_replace, groups)

      return (text[:match.start()], replaced, text[match.end():])

  return regexp_rule

def create_tracker_link_rule(url):
  """ helper that returns rule that replaces references like #123,
      issue #123 with link to `url`. issue number is appended.
  """
  if not url.endswith('/'):
    url += '/'
  base = '<a href="%s' % url
  return [
    # issue #123
    create_regexp_rule('(?i)(issue|bug) *#(\d+)', base + '\\2">\\0</a>'),
    # just #123, but not &#8211; or something#123
    create_regexp_rule('(?<![&\w])(#(\d+))', base + '\\2">\\1</a>')
  ]

# [ ] sets of common rules
# [ ] configurable replacements


# --- execute rules ---

# [ ] indented prints after every step

def wikify(text, rules):
  """
  Replaces text according to the given rules. Guarantees
  that replacements won't affect each other.
  Args:
    text: string
    rules: rule or a list of rules. each rule may return None
           (not-matched) or text split into three parts
           [pre, processed, post]. wikify excludes processed
           part and applies the rest of rules to two others
  Returns:
    string
  Raises:
    TypeError: rule returns invalid result
  """

  if type(rules) != list:
    rules = [rules]

  # [x] flatten nested
  def flatten(lol):
    res = []
    for l in lol:
      if type(l) != list:
        res.append(l)
      else:
        res.extend(flatten(l))
    return res
  rules = flatten(rules)
  

  texts = []  # store processed pieces
  subst = []  # store replacements

  texts = [text]
  step  = 0
  match = 0
  if DEBUG:
    print('debug: start with %s rules' % len(rules))
  for rule in rules:
    subidx = 0  # index in replacements array
    for idx,part in enumerate(texts):
      if part == None:
        subidx += 1
        continue
      step += 1
      res = rule(part)
      if res == None:
        continue
      elif len(res) != 3:
        raise TypeError(
          "Rule '%s' returned %d element(s) instead of 3"
            % (rule.__name__, len(res)))

      match += 1
      # store changed part (middle) in replacements array
      subst.insert(subidx, res[1])
      if DEBUG:
        print('debug: step_%s match_%s substs_%s' % (step, match, len(subst)))
        print(texts)
        print(subst)

      # replace current texts element with triple
      # ( not-matched, None, the-rest )
      res = list(res)
      res[1] = None
      # exclude empty strings from resulting texts array
      res = [s for s in res if s != '']
      texts[idx:idx+1] = res

  # -- reasseble
  # [ ] optimize for memory usage
  # [ ] sanity check count(None) == len(subst)
  restext = ''
  subidx = 0
  for part in texts:
    if part == None:
      # substitute
      restext += subst[subidx]
      subidx += 1
    else:
      restext += part
  return restext


if __name__ == '__main__':
  # tests for linkstub
  text = 'a web site http://example.com according to cap'
  print(text)
  print(wikify(text, rule_stub_links))
  print(rule_stub_links(text))

  text = ''
  print(wikify(text, rule_stub_links))

  print(wikify('wikify you texts!', rule_link_wikify))

  text = 'somematch metext'
  print(text)
  m = create_regexp_rule('match me', ' replacement (\\0) ')
  print(wikify(text, m))

  # linkify issue numbers like #123, but not HTML entity like &#8211;
  w = create_tracker_link_rule('https://bitbucket.org/techtonik/wikify/issue/')
  print(wikify('issue #123, &#8121;', w))
  print(wikify('bug#123, &#8121;', [w]))
  print(wikify('#123, match me, &#8121;', [w, m]))
  print(wikify('x#123, match me, &#8121;', [w, m]))
  
  f = create_regexp_rule('f', '_first rule_')
  l = create_regexp_rule('l', '_last rule_')
  print(wikify('f l f', [f, l]))
  
