Make the ``setup.py install`` deprecation warning less noisy. We warn only
when ``setup.py install`` succeeded and ``setup.py bdist_wheel`` failed, as
situations where both fails are most probably irrelevant to this deprecation.
