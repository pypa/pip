def sitecustomize() -> None:
    import sys
    from ._loader import KeyringSubprocessFinder

    sys.meta_path.append(KeyringSubprocessFinder())

    try:
        from importlib import import_module

        # if keyring-subprocess is vendored try to import vendored virtualenv
        vendor_prefix_parts = list(__name__.split(".")[:-2])
        vendored_virtualenv = vendor_prefix_parts + ["virtualenv"]
        vendored_virtualenv = ".".join(vendored_virtualenv)
        import_module(vendored_virtualenv)
        from ._seeder import KeyringSubprocessFromAppData
    except ImportError:
        pass
