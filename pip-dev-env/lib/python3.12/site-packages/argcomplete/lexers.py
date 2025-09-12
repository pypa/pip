import os

from .exceptions import ArgcompleteException
from .io import debug
from .packages import _shlex


def split_line(line, point=None):
    if point is None:
        point = len(line)
    line = line[:point]
    lexer = _shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.wordbreaks = os.environ.get("_ARGCOMPLETE_COMP_WORDBREAKS", "")
    words = []

    def split_word(word):
        # TODO: make this less ugly
        point_in_word = len(word) + point - lexer.instream.tell()
        if isinstance(lexer.state, (str, bytes)) and lexer.state in lexer.whitespace:
            point_in_word += 1
        if point_in_word > len(word):
            debug("In trailing whitespace")
            words.append(word)
            word = ""
        prefix, suffix = word[:point_in_word], word[point_in_word:]
        prequote = ""
        # posix
        if lexer.state is not None and lexer.state in lexer.quotes:
            prequote = lexer.state
        # non-posix
        # if len(prefix) > 0 and prefix[0] in lexer.quotes:
        #    prequote, prefix = prefix[0], prefix[1:]

        return prequote, prefix, suffix, words, lexer.last_wordbreak_pos

    while True:
        try:
            word = lexer.get_token()
            if word == lexer.eof:
                # TODO: check if this is ever unsafe
                # raise ArgcompleteException("Unexpected end of input")
                return "", "", "", words, None
            if lexer.instream.tell() >= point:
                debug("word", word, "split, lexer state: '{s}'".format(s=lexer.state))
                return split_word(word)
            words.append(word)
        except ValueError:
            debug("word", lexer.token, "split (lexer stopped, state: '{s}')".format(s=lexer.state))
            if lexer.instream.tell() >= point:
                return split_word(lexer.token)
            else:
                msg = (
                    "Unexpected internal state. "
                    "Please report this bug at https://github.com/kislyuk/argcomplete/issues."
                )
                raise ArgcompleteException(msg)
