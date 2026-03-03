# Generative AI / LLM Policy

We appreciate that we can't realistically police how you author your pull requests, which includes whether you employ large-language model (LLM)-based development tools.
So, we don't.

However, due to both legal and human reasons, we have to establish boundaries.

## Overview

- We take the responsibility for this project very seriously and we expect you to take your responsibility for your contributions seriously, too.
  This used to be a given, but it changed now that a pull request is just one prompt away.

- Every contribution has to be backed by a human who unequivocally owns the copyright for all changes.
  No LLM bots in `Co-authored-by:`s.

- Repeated slop contributions are unacceptable, and will be closed without review.
  We reserve the right to exclude contributors who continue to submit such material.

- Absolutely no unsupervised agentic tools like OpenClaw.

---

By submitting a pull request, you certify that:

- You are the author of the contribution or have the legal right to submit it.
- You either hold the copyright to the changes or have explicit legal authorization to contribute them under this project's license.
- You understand the code.
- You accept full responsibility for it.


## Legal

There is ongoing legal uncertainty regarding the copyright status of LLM-generated works and their provenance.
Because of this, allowing contributions by LLMs has unpredictable consequences for the copyright status of this project – even when leaving aside possible copyright violations due to plagiarism.


## Human

As the makers of software that is used by millions of people worldwide and with a reputation for high-quality maintenance, we take our responsibility to our users very seriously.
No matter what LLM vendors or boosters on LinkedIn tell you, we have to manually review every change before merging, because it's our responsibility to keep the project stable.

Please understand that by opening low-quality pull requests you're not helping anyone.
Worse, you're [poisoning the open source ecosystem](https://lwn.net/Articles/1058266/) that was precarious even before the arrival of LLM tools.
Having to wade through plausible-looking-but-low-quality pull requests and trying to determine which ones are legit is extremely demoralizing and has already burned out many good maintainers.

Put bluntly, we have no time or interest to become part of your vibe coding loop where you drop LLM slop at our door, we spend time and energy to review it, and you just feed it back into the LLM for another iteration.

This dynamic is especially pernicious because it poisons the well for mentoring new contributors which we are committed to.


## Summary

In practice, this means:

- Pull requests that have an LLM product listed as co-author can't be merged and will be closed without further discussion.
  We cannot risk the copyright status of this project.

  If you used LLM tools during development, you may still submit – but you must remove any LLM co-author tags and take full ownership of every line.

- By submitting a pull request, you take full technical and legal responsibility for the contents of the pull request and promise that you hold the copyright for the changes submitted.

  "An LLM wrote it" is *not* an acceptable response to questions or critique.
  If you cannot explain and defend the changes you submit, do not submit them and open a high-quality bug report or feature request instead.

- Accounts that exercise bot-like behavior – like automated mass pull requests – will be permanently banned, whether they belong to a human or not.

- LLM-generated comments must be concise and accurate, and you must be prepared to stand by them.
  Do not post summaries unless you are certain that they add value to the discussion.
  Remember that all LLM output *looks* plausible.
  When using these tools, it's your responsibility to ensure that the output is correct, and useful.

- Remember that LLM generated content is generally easier for you to produce, but *harder* for others to read, review or interpret.
  Prioritising your time over that of others is contrary to the project's code of conduct.
  Verbose, repetitive, or off topic comments may be marked as spam.

## Thanks

This policy was based on the policy of the `attrs` project. Many thanks to them for developing it.
