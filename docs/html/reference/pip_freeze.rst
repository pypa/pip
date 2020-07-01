
.. _`pip freeze`:

==========
pip freeze
==========

.. contents::


Usage
=====

.. pip-command-usage:: freeze


Description
===========

.. pip-command-description:: freeze


Options
=======

.. pip-command-options:: freeze


Examples
========

#. Generate output suitable for a requirements file.

    ::

     $ pip freeze
     docutils==0.11
     Jinja2==2.7.2
     MarkupSafe==0.19
     Pygments==1.6
     Sphinx==1.2.2

#. Generate output suitable for a requirements file, with pinned hashes.

    ::

     $ pip freeze --hashes
     certifi==2020.6.20 --hash=sha256:8fc0819f1f30ba15bdb34cceffb9ef04d99f420f68eb75d901e9560b8749fc41
     chardet==3.0.4 --hash=sha256:fc323ffcaeaed0e0a02bf4d117757b98aed530d9ed4531e3e15460124c106691
     idna==2.10 --hash=sha256:b97d804b1e9b523befed77c48dacec60e6dcb0b5391d57af6a65a312a90648c0
     requests==2.24.0 --hash=sha256:fe75cc94a9443b9246fc7049224f75604b113c36acb93f87b80ed42c44cbb898
     six==1.15.0 --hash=sha256:8b74bedcbbbaca38ff6d7491d76f2b06b3592611af620f8426e82dddb04a5ced
     urllib3==1.25.9 --hash=sha256:88206b0eb87e6d677d424843ac5209e3fb9d0190d0ee169599165ec25e9d9115

#. Generate output suitable for a requirements file, with pinned hashes and specific algorithm.

    ::

     $ pip freeze --hashes -a sha512
     certifi==2020.6.20 --hash=sha512:960f1cbe72443230ecba527b5bc4bb8a45a33feb646b0ad01dcb606b9ec3729d27dff5cfa04655d92efd4dec691d61c62d80f8fd39a82fc21528727eeb5c9991
     chardet==3.0.4 --hash=sha512:bfae58c8ea19c87cc9c9bf3d0b6146bfdb3630346bd954fe8e9f7da1f09da1fc0d6943ff04802798a665ea3b610ee2d65658ce84fe5a89f9e93625ea396a17f4
     idna==2.10 --hash=sha512:7b7be129e1a99288aa74a15971377cb17bee1618843c03c8f782e287d0f3ecf3b8f26e3ea736444eb358f1d6079131a7eb291446f3279874eb8e00b624d9471c
     requests==2.24.0 --hash=sha512:64c49592455abbcd1168f5e1908a8db77bbeb373264b1cf6db8a1fefe65f9a0879e30066d34b041e7f013c7fc1ccdd87b91bc637f2a53972be45bb984364fa0d
     six==1.15.0 --hash=sha512:0416d59434623604de755601c919722c2b800042612a2a7b221ecd3ccf556aca3a78f0f926fd640032a3d74d153457628a89c25065dfcdbb96892d5bf7279904
     urllib3==1.25.9 --hash=sha512:b20687b4ce06164c5b932b43c5b758efd864668ee2b60f6cd6ce6c27f0ea16b9d1222ec0c061618fc3f0de362c0f18be95864bd91ecaa73fdfa92bd666fb4378


#. Generate a requirements file and then install from it in another environment.

    ::

     $ env1/bin/pip freeze > requirements.txt
     $ env2/bin/pip install -r requirements.txt
