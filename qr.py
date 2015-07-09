#!/usr/bin/env python

import sys


def fileread_expect(f, t):
    """Reads data from the file, expecting a specific string. Throws ValueError
    if it's not found."""

    if isinstance(t, list):
        b = f.read(len(t[0]))
    elif isinstance(t, str):
        b = f.read(len(t))
    else:
        raise ValueError("The second argument should either"
                         "be a string or a list of strings.")

    def get_pos(f):
        try:
            pos = " (position: %d)" % f.tell()
        except IOError:
            pos = ""

    if isinstance(t, list):
        for x in t:
            if b == x:
                return b
        raise ValueError("Unexpected %s, expected %s%s" % (repr(b), repr(t),
                         get_pos(f)))
    if b != t:
        raise ValueError("Unexpected %s, expected %s%s" % (repr(b), repr(t),
                         get_pos(f)))
    return b


def handle_escape_sequence(f, color):
    b = fileread_expect(f, ['[0', '[4'])
    if b == '[0':
        fileread_expect(f, 'm')
        return get_atom(f, False)
    elif b == '[4':
        b = fileread_expect(f, ['7', '0'])
        color = b == '7'
        fileread_expect(f, 'm')
        return get_atom(f, color)


def get_atom(f, color):
    """Read the input file looking for "qrcode-terminal" output.

    Arguments:
        f: the file to read from
        color: the color that was used so far. In the first call, use True.

    Returns tuple: (character, color), where character can be an int (1 or 0),
    '\\n' or None."""

    b = f.read(1)

    # is it EOF?
    if b == '':
        return None, None

    if b == '\n':
        return '\n', color
        # return get_atom(f, color)

    if b == ' ':
        return 0 if color else 1, color

    # if it is an escape sequence, check it and call get_atom again.
    if b == '\x1b':
        return handle_escape_sequence(f, color)
    else:
        raise ValueError('Unexpected byte: %s' % b)


def load_matrix(f):
    is_black = True
    l = []
    tmp = []
    while True:
        a, is_black = get_atom(f, is_black)
        if a is None:
            break
        if a == '\n':
            l += [tmp]
            tmp = []
        else:
            tmp += [a]
    return l


def compress(m):
    def pairs_checked(seq):
        while True:
            y = (next(seq), next(seq))
            if y[0] != y[1]:
                raise ValueError("Pairs are not equal")
            yield y[0]
    ret = []
    for l in m:
        add = []
        for x in pairs_checked(iter(l)):
            add += [x]
        ret += [add]
    return ret


def flatten_arr(arr):
    return (''.join(str(c) for c in arr))

def arr_to_b2(arr):
    return int(flatten_arr(arr), 2)


def main():
    f = open(sys.argv[1])
    m = load_matrix(f)
    m = compress(m)
    if len(m) != len(m[0]):
        raise ValueError("QR code is not square")
    if len(m) != 23:
        raise NotImplementedError("This program can currently"
                                  " parse only 23x23 QR codes.")

    ECC_EXPLAIN = {0b00: 'H (30%)', 0b01: 'Q (25%)',
                   0b10: 'M (15%)', 0b11: 'L (7%)'}
    ecc_arr = m[9][1:3]
    ecc_lvl = arr_to_b2(ecc_arr)
    print("Error correction: %s" % ECC_EXPLAIN.get(ecc_lvl, ecc_lvl))
    # TODO: check if this is consistent with its horizontal equivalent

    mask_arr = m[9][3:6]
    mask = arr_to_b2(mask_arr)
    print("Mask: %s" % flatten_arr(mask_arr))

    ENCODING_EXPLAIN = {
        0b0000: 'End of message',
        0b0001: 'Numeric encoding (10 bits per 3 digits)',
        0b0010: 'Alphanumeric encoding (11 bits per 2 characters)',
        0b0011: 'Structured append (used to split a message across multiple QR symbols)',
        0b0100: 'Byte encoding (8 bits per character)',
        0b0101: 'FNC1 in first position (see Code 128 for more information)',
        0b0111: 'Extended Channel Interpretation (select alternate character set or encoding)',
        0b1000: 'Kanji encoding (13 bits per character)',
        0b1001: 'FNC1 in second position',
    }

    encoding_arr = [m[21][21], m[21][20], m[20][21], m[20][20]]
    print("Encoding: %s" % flatten_arr(encoding_arr))

    if 'ipython' in sys.argv:
        import IPython
        IPython.embed()

if __name__ == '__main__':
    main()
