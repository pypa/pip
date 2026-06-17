# pip Upgrade Conflict

## Problem

Currently, pip does _not_ take into account packages that are already installed when a user asks pip to upgrade a package. This can cause dependency conflicts for pip's users.

[Skip to recommendations](#recommendations)

## Research

We published a [survey](https://bit.ly/2ZqJijr) asking users how they would solve the following scenario:

<blockquote>
Imagine you have package tea and coffee with the following dependencies:

tea 1.0.0 - depends on water<1.12<br>
tea 2.0.0 - depends on water>=1.12<br>
coffee 1.0.0 - depends on water<1.12<br>
coffee 2.0.0 - depends on water>=1.12<br>

You have the following packages installed:

tea 1.0.0<br>
coffee 1.0.0<br>
water 1.11.0<br>

You ask pip to upgrade tea. What should pip do?

If pip upgrades tea to 2.0.0, water needs to be upgraded as well, creating a conflict with coffee...

</blockquote>

We gave users four choices:

1. Upgrade tea and water. Show a warning explaining that coffee now has unsatisfied requirements.
2. Upgrade coffee automatically to 2.0.0
3. Install nothing. Tell the user that everything is up-to-date (since the version of tea they have installed is the latest version without conflicts).
4. Install nothing. Show an error explaining that the upgrade would cause incompatibilities.

We allowed users to post their own solution, and asked why they came to their decision.

## Results

In total, we received 693 responses, 407 of which included an explanation of why a particular solution was best.

![](https://i.imgur.com/UdBWkaQ.png)

- 497 responses (71.7%) preferred option 4: that pip should install nothing and raise an error message
- 102 responses (14.7%) preferred option 2: that pip should upgrade package_coffee
- 79 responses (11.4%) preferred option 1: that pip should upgrade tea and water
- 15 responses (2.2%) preferred option 3: that pip should install nothing and tell the user that everything is up to date

From the 407 responses that answered "why" a particular solution was best, the following key themes emerged:

- "explicit is better than implicit" - pip should not create "side effects" that the user does not understand, has not anticipated, and has not consented to
- pip should do everything in its power to avoid introducing conflicts (pip should not "break" the development environment)
- Telling the user that everything is up to date (option 3) is misleading / dishonest
- pip could be more flexible by:
  - allowing the user to choose how they want to resolve the situation
  - allowing the user to override the default behaviour (using flags)

## Recommendations

Based on the results of this research, the pip UX team has made the following recommendations to the development team:

- While the current behaviour exists, [warn the user when conflicts are introduced](https://github.com/pypa/pip/issues/7744#issuecomment-717573440)
- [Change the current behaviour](https://github.com/pypa/pip/issues/9094), so that pip takes into account packages that are already installed when upgrading other packages. Show the user a warning when pip anticipates a dependency conflict (as per option 4)
- Explore [the possibility of adding additional flags to the upgrade command](https://github.com/pypa/pip/issues/9095), to give users more control
