from pip._vendor.packaging.utils import canonicalize_name


class FormatControl(object):
    """This class has two fields, no_binary and only_binary.
    If a field is falsy, it isn't set. If it is {':all:'}, it should match all
    packages except those listed in the other field. Only one field can be set
    to {':all:'} at a time. The rest of the time exact package name matches
    are listed, with any given package only showing up in one field at a time.
    """
    def __init__(self, no_binary, only_binary):
        self.no_binary = no_binary
        self.only_binary = only_binary

    def _handle_no_binary(self, option, opt_str, value, parser):
        existing = getattr(parser.values, option.dest)
        self.fmt_ctl_handle_mutual_exclude(
            value, existing.no_binary, existing.only_binary,
        )

    def _handle_only_binary(self, option, opt_str, value, parser):
        existing = getattr(parser.values, option.dest)
        self.fmt_ctl_handle_mutual_exclude(
            value, existing.only_binary, existing.no_binary,
        )

    def fmt_ctl_handle_mutual_exclude(self, value, target, other):
        new = value.split(',')
        while ':all:' in new:
            other.clear()
            target.clear()
            target.add(':all:')
            del new[:new.index(':all:') + 1]
            # Without a none, we want to discard everything as :all: covers it
            if ':none:' not in new:
                return
        for name in new:
            if name == ':none:':
                target.clear()
                continue
            name = canonicalize_name(name)
            other.discard(name)
            target.add(name)

    def fmt_ctl_formats(self, canonical_name):
        result = {"binary", "source"}
        if canonical_name in self.only_binary:
            result.discard('source')
        elif canonical_name in self.no_binary:
            result.discard('binary')
        elif ':all:' in self.only_binary:
            result.discard('source')
        elif ':all:' in self.no_binary:
            result.discard('binary')
        return frozenset(result)

    def fmt_ctl_no_binary(self):
        self.fmt_ctl_handle_mutual_exclude(
            ':all:', self.no_binary, self.only_binary,
        )

    def _get_format_control(self, values, option):
        """Get a format_control object."""
        return getattr(values, option.dest)
