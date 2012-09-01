if __name__ == '__main__':
    import sys
    from . import main

    exit = main()
    if exit:
        sys.exit(exit)
