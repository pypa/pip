# -*- coding: utf-8 -*-
"""Return compact set of columns as a string with newlines for an
array of strings.

Adapted from the routine of the same name inside cmd.py"""

import os


def computed_displaywidth():
    '''Figure out a reasonable default with. Use os.environ['COLUMNS'] if possible,
    and failing that use 80.
    '''
    width=80
    if 'COLUMNS' in os.environ:
        try:
            width = int(os.environ['COLUMNS'])
        except:
            pass
        pass
    return width

default_opts = {
    'arrange_array'    : False,  # Check if file has changed since last time
    'arrange_vertical' : True,
    'array_prefix'     : '',
    'array_suffix'     : '',
    'colfmt'           : None,
    'colsep'           : '  ',
    'displaywidth'     : computed_displaywidth(),
    'lineprefix'       : '',
    'linesuffix'       : "\n",
    'ljust'            : None,
    'term_adjust'      : False
    }

def get_option(key, options):
    global default_opts
    if key not in options:
        return default_opts.get(key)
    else:
        return options[key]
    return None # Not reached


def columnize(array, displaywidth=80, colsep = '  ',
              arrange_vertical=True, ljust=True, lineprefix='',
              opts={}):
    """Return a list of strings as a compact set of columns arranged
    horizontally or vertically.

    For example, for a line width of 4 characters (arranged vertically):
        ['1', '2,', '3', '4'] => '1  3\n2  4\n'

    or arranged horizontally:
        ['1', '2,', '3', '4'] => '1  2\n3  4\n'

    Each column is only as wide as necessary.  By default, columns are
    separated by two spaces - one was not legible enough. Set "colsep"
    to adjust the string separate columns. Set `displaywidth' to set
    the line width.

    Normally, consecutive items go down from the top to bottom from
    the left-most column to the right-most. If "arrange_vertical" is
    set false, consecutive items will go across, left to right, top to
    bottom."""
    if not isinstance(array, list) and not isinstance(array, tuple):
        raise TypeError((
            'array needs to be an instance of a list or a tuple'))

    o = {}
    if len(opts.keys()) > 0:
        for key in default_opts.keys():
            o[key] = get_option(key, opts)
            pass
        if o['arrange_array']:
            o['array_prefix'] = '['
            o['lineprefix']   = ' '
            o['linesuffix']   = ",\n"
            o['array_suffix'] = "]\n"
            o['colsep']       = ', '
            o['arrange_vertical'] = False
            pass

    else:
        o = default_opts.copy()
        o['displaywidth']     = displaywidth
        o['colsep']           = colsep
        o['arrange_vertical'] = arrange_vertical
        o['ljust']            = ljust
        o['lineprefix']       = lineprefix
        pass

    # if o['ljust'] is None:
    #     o['ljust'] = !(list.all?{|datum| datum.kind_of?(Numeric)})
    #     pass

    if o['colfmt']:
        array = [(o['colfmt'] % i) for i in array]
    else:
        array = [str(i) for i in array]
        pass

    # Some degenerate cases
    size = len(array)
    if 0 == size:
        return "<empty>\n"
    elif size == 1:
        return '%s%s%s\n' % (o['array_prefix'], str(array[0]),
                             o['array_suffix'])

    if o['displaywidth'] - len(o['lineprefix']) < 4:
        o['displaywidth'] = len(o['lineprefix']) + 4
    else:
        o['displaywidth'] -= len(o['lineprefix'])
        pass

    o['displaywidth'] = max(4, o['displaywidth'] - len(o['lineprefix']))
    if o['arrange_vertical']:
        array_index = lambda nrows, row, col: nrows*col + row
        # Try every row count from 1 upwards
        for nrows in range(1, size):
            ncols = (size+nrows-1) // nrows
            colwidths = []
            totwidth = -len(o['colsep'])
            for col in range(ncols):
                # get max column width for this column
                colwidth = 0
                for row in range(nrows):
                    i = array_index(nrows, row, col)
                    if i >= size: break
                    x = array[i]
                    colwidth = max(colwidth, len(x))
                    pass
                colwidths.append(colwidth)
                totwidth += colwidth + len(o['colsep'])
                if totwidth > o['displaywidth']:
                    break
                pass
            if totwidth <= o['displaywidth']:
                break
            pass
        # The smallest number of rows computed and the
        # max widths for each column has been obtained.
        # Now we just have to format each of the
        # rows.
        s = ''
        for row in range(nrows):
            texts = []
            for col in range(ncols):
                i = row + nrows*col
                if i >= size:
                    x = ""
                else:
                    x = array[i]
                texts.append(x)
            while texts and not texts[-1]:
                del texts[-1]
            for col in range(len(texts)):
                if o['ljust']:
                    texts[col] = texts[col].ljust(colwidths[col])
                else:
                    texts[col] = texts[col].rjust(colwidths[col])
                    pass
                pass
            s += "%s%s%s" % (o['lineprefix'], str(o['colsep'].join(texts)),
                             o['linesuffix'])
            pass
        return s
    else:
        array_index = lambda ncols, row, col: ncols*(row-1) + col
        # Try every column count from size downwards
        colwidths = []
        for ncols in range(size, 0, -1):
            # Try every row count from 1 upwards
            min_rows = (size+ncols-1) // ncols
            nrows = min_rows -1
            while nrows < size:
                nrows += 1
                rounded_size = nrows * ncols
                colwidths = []
                totwidth  = -len(o['colsep'])
                for col in range(ncols):
                    # get max column width for this column
                    colwidth  = 0
                    for row in range(1, nrows+1):
                        i = array_index(ncols, row, col)
                        if i >= rounded_size: break
                        elif i < size:
                            x = array[i]
                            colwidth = max(colwidth, len(x))
                            pass
                        pass
                    colwidths.append(colwidth)
                    totwidth += colwidth + len(o['colsep'])
                    if totwidth >= o['displaywidth']:
                        break
                    pass
                if totwidth <= o['displaywidth'] and i >= rounded_size-1:
                    # Found the right nrows and ncols
                    # print "right nrows and ncols"
                    nrows  = row
                    break
                elif totwidth >= o['displaywidth']:
                    # print "reduce ncols", ncols
                    # Need to reduce ncols
                    break
                pass
            if totwidth <= o['displaywidth'] and i >= rounded_size-1:
                break
            pass
        # The smallest number of rows computed and the
        # max widths for each column has been obtained.
        # Now we just have to format each of the
        # rows.
        s = ''
        if len(o['array_prefix']) != 0:
            prefix = o['array_prefix']
        else:
            prefix = o['lineprefix']
            pass
        for row in range(1, nrows+1):
            texts = []
            for col in range(ncols):
                i = array_index(ncols, row, col)
                if i >= size:
                    break
                else: x = array[i]
                texts.append(x)
                pass
            for col in range(len(texts)):
                if o['ljust']:
                    texts[col] = texts[col].ljust(colwidths[col])
                else:
                    texts[col] = texts[col].rjust(colwidths[col])
                    pass
                pass
            s += "%s%s%s" % (prefix, str(o['colsep'].join(texts)),
                             o['linesuffix'])
            prefix = o['lineprefix']
            pass
        if o['arrange_array']:
            colsep = o['colsep'].rstrip()
            colsep_pos = -(len(colsep)+1)
            if s[colsep_pos:] == colsep + "\n":
                s = s[:colsep_pos] + o['array_suffix'] + "\n"
                pass
            pass
        else:
            s += o['array_suffix']
            pass
        return s
    pass

# Demo it
if __name__=='__main__':
    # from trepan.api import debug
    # debug()
    print(columnize(range(12),
                      opts={'displaywidth':6, 'arrange_array':True}))
    print(columnize(range(12),
                      opts={'displaywidth':10, 'arrange_array':True}))
    for t in ((4, 4,), (4, 7), (100, 80)):
        width = t[1]
        data = [str(i) for i in range(t[0])]
        options = {}
        for t2 in ((False, 'horizontal',), (True, 'vertical',)):
            print("Width: %d, direction: %s" % (width, t2[1]))
            options['displaywidth'] = width
            options['arrange_vertical'] = t2[0]
            print(columnize(data, opts=options))
            pass
        pass
    print(columnize([]))
    print(columnize(["a", '2', "c"], 10, ', '))
    print(columnize(["oneitem"]))
    print(columnize(("one", "two", "three",)))
    data = (
        "one",       "two",         "three",
        "for",       "five",        "six",
        "seven",     "eight",       "nine",
        "ten",       "eleven",      "twelve",
        "thirteen",  "fourteen",    "fifteen",
        "sixteen",   "seventeen",   "eightteen",
        "nineteen",  "twenty",      "twentyone",
        "twentytwo", "twentythree", "twentyfour",
        "twentyfive","twentysix",   "twentyseven",)
    print(columnize(data))
    print(columnize(data, arrange_vertical=False))
    data = [str(i) for i in range(55)]
    print(columnize(data, opts={'displaywidth':39, 'arrange_array':True}))
    print(columnize(data, displaywidth=39, ljust=False,
                    colsep=', ', lineprefix='    '))
    print(columnize(data, displaywidth=39, ljust=False,
                    arrange_vertical=False,
                    colsep = ', '))

    print(columnize(data, displaywidth=39, ljust=False,
                    arrange_vertical=False,
                    colsep = ', ', lineprefix='    '))

    import sys
    try:
        print(columnize(5))
    except TypeError:
        _, err, _ = sys.exc_info()
        print(err)
        pass

    print(columnize(list(range(4))))
