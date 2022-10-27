Git 2.38.1 patched CVE-2022-39253 by disaling automated fetch against a
``file:`` repository. This breaks git submodule, which is used by a pip test.
Information on how projects relying on automated fetch should  configure git
correctly after this change is lacking, so the test is disabled for now until
someone can come up with a better solution.
