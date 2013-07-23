import sys

def main(): # needed for console script
    if __package__ == '':
        # To be able to run 'python pip.whl/pip':
        import os.path
        path = os.path.dirname(os.path.dirname(__file__))
        sys.path[0:0] = [path]
    from pip.runner import run
    exit = run()
    if exit:
        sys.exit(exit)

if __name__ == '__main__':
    main()
