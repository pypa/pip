# How pip users think about security

## Problem

We wanted to understand how pip users think about security when installing packages with pip.

[Skip to recommendations](#recommendations)

## Research

We asked participants about their behaviours and practices in terms of the security and integrity of the Python packages they install with pip, and of the software they create.

We asked participants to tell us how often they:

1. Carry out a code audit of the Python software they install with pip
2. Think about the security and integrity of the (Python) software they install (with pip)
3. Think about the security and integrity of the (Python) code they create

## Results

While the security and integrity of the software users install (51%) and make (71%) is important to research participants, less than 7% do code audits of the packages or code they install with pip.

This is due to lack of time to audit large packages, lack of expertise, reliance on widely adopted Python packages, the expectation that pip automatically checks hashes, and reliance of the wider Python community to act as canary in the coalmine.

This behaviour was common across all user types, and baselines of software development experience.

These results - particularly the lack of expertise in auditing packages fits in with the overall findings that the majority of pip users are not "classically trained" (i.e. having formally learned software development) software developers and so lack the expertise and/or formal training in software development practices.

There is a gulf between what the maintainers expect users to think, and worry about, and what the users actually worry and think about. Right now, pip leaves users to "fend for themselves" in terms of providing them with assurance of the software they install. This isn't meant as a criticism, but an observation.

### Responses to question: before I install any Python software with pip, I carry out a code audit

The vast majority of participants, 82%, do not (rarely or never) do a code audit of the software packages they install using pip, the reasons are explained below.

| Before I install any Python software with pip, I carry out a code audit: | Number of responses |
| ------------------------------------------------------------------------ | ------------------- |
| Always                                                                   | 3                   |
| Frequently                                                               | 9                   |
| Rarely                                                                   | 66                  |
| Never                                                                    | 68                  |
| I'm not sure what this means                                             | 5                   |
| No opinion                                                               | 13                  |
| **Total number of participants**                                         | **164**             |

### Responses to question: I think about the security and integrity of the software I install

![screenshot of responses to question about security](https://i.imgur.com/wy4lGwJ.png)

The vast majority of participants did think about the security and integrity of the software they installed - and unlike responses about code audits, in some cases participants made attempts to verify the security and integrity of the software they installed.

Most attempts were made by those who had experience in software development, however in some cases, people gave up.

Those who were not classically trained software developers did not know where to start.

Both of these groups identified their "sphere of influence" and did their best to cover this.

### User thoughts about security

Selected quotes from research participants

#### Responsibility as author

Participants who spent a lot of their time writing Python code - either for community or as part of their job - expressed a responsibility to their users for the code they wrote - people who wrote code which was made public expressed a stronger responsibility.

They thought about where the software would be used, who would use it, and possible attack surfaces.

> "On the basic point, I have to think about attack surfaces. If I am writing the thing (software), I have to give a crap. I have to answer the emails! In the code I push to[ pypi.org](http://pypi.org/) I think about it doubley. What could people do with this code? Whether I do a good job, that's different! I am aware of it when publishing it or making it [publicly] available. Whether I do a good job, that's different! I am aware of it when publishing it or making it [publicly] available. I rely on community resources - Python security related, I follow security people blogs, Twitter. I use Hypothesis for fuzz-testing. I also rely on having security policies in place and a reporting mechanism. I steer clear of crypto, I rely on other peoples. There's a certain amount of knowledge in the Python community, I am actively involved in it. If something happens, I will hear about it. I use Twitter, if something happens, in the morning it can take me awhile to figure out what's happened. I have a lot of trust in the ecosystem to be self healing. As long as you don't stray too far-off the reservation (into using odd or uncommon or new packages), it's a better sense of security." **- Participant (data scientist turned Python developer)**

> Yes, because I'm liable for that. If the problem is my code, and I deliver something and they get attacked. I'm screwed. **- Participant (professional Python developer and trainer)**

#### Reliance on software packages

Participants also explained they rely on code security scanning and checking software packages.

> "I use linters (Bandit), I scan the code I have created and when there is an issue I raise a red flag."

> "I use Hypothesis for fuzz-testing."

#### Reliance on good software development practices

A small number of participants explained they have good software practices in place, which help with writing secure software.

> "We have a book about ethics of code - we have mandatory certification."

> "I also rely on having security policies in place and a reporting mechanism. I steer clear of crypto, I rely on other peoples."

Of the users who have used pip's hash checking functionality:

- One finds the error messages "too annoying and loud", and has difficulty matching the file name to the hash
- Another finds the process of explicitly pinning hashes to be too tiresome (especially for dependencies)

One user mentioned that he likes [NPM audit](https://docs.npmjs.com/cli/v6/commands/npm-audit) and would like to see something similar in the Python ecosystem.

#### Lack of time

The lack of time to carry out the audit of the package code, and that of the dependencies, was cited as a very common reason. In most cases participants used Python code as a means to achieving their goal.

#### Lack of expertise to carry out the audit

The lack of expertise or knowledge of auditing software was mainly due to participants expertise not being software development. However, in the case participants were "classically" software developers, lack of expertise was also a commonly given reason for not carrying out audits.

#### Use of only widely used, well-established packages

Use of well-established, high-quality packages was a common reason amongst all types of participants - professional Python software developers and those who used Python as a tool.

"Well-established, high-quality packages" were defined by users as packages that:

- have been in existence for many years
- are popular, or commonly used by those in their community or industry
- have responsive maintainers
- maintained by people the participant has heard of
- have many hundreds or thousands of users
- are in active development (many open issues, many forks, Github stars)
- are developed in the open, and transparently
- their history is known, or can be found out publicly

#### Reliance on the Python community to find issues

There was a reliance on the community to find issues and make them know publicly - "Many eyes shallow bugs".

> "I rarely do code audits. Most of the time I rely on the opinions of the community. I look at how many maintainers there are. Maybe it's not good practice but I don't have time to go through the code." **- Participant 240315091**

#### Use of only internal packages

> "I only install internal packages, so I don't need to worry about this."

This theme was not that common, mainly in large software development environments or where security was of high importance.

#### Expectation that pip audits packages

Some users expect/assume that pip (and PyPI) should "protect" them from malicious actors - e.g. by automatically checking hashes, or detecting malicious packages.

> "If I was downloading a package on my own I check the hash, if it's installed by pip, then no. I expect pip to do it. If it doesn't do it, it does surprise me. Every package manager checks the hash against what it downloads. The hashes are already known on pypi." **- Participant 240312164 (Nuclear physicist)**

#### Other notable comments

> "Never. I should but I never do [audit code]. I don't stray, I am risk adverse. I install packages that are good already. I consider my risk surface small. I don't have time or resources to audit them. I have sufficient faith in the ecosystem to be self-auditing. If something turned up in a well known package, the community is well known for making a stink. And anyway a code audit wouldn't pick it up." **- Participant 240326752 (professional Python developer)**

> "On the private level (work) the code is developed internally. I don't audit the code on pypi - due to lack of time auditing the dependencies, and I trust it. I know they had a security breach a few years ago, but it doesn't happen that often. I know they don't audit anything but I still don't audit the code."

> "I wouldn't know how to [audit code], also I'm writing this stuff for myself. It'll work or not. Sometimes I end up installing 2 or 3 packages and find out that I need to install something else. I move on if it doesn't work. The last resort is I will write the code myself."

> "I'm quite trusting - Python is open source, I'm assuming that if a package is on[ pypi.org](http://pypi.org/) - it must be alright. I install the package first, then I look at it. I find a package by figuring out - we need to do a certain task, we search for it on the Internet, look at the documentation, we install it and then see if it is what we want" **- Participant 240278297**

> "If I want to install a package, it's for a reason. I want to calculate the azimuth and elevation of the moon with PyEphem. Do a code audit? Pffff. Most of the stuff I do is banal. It needs to meet a dependency, so I install it. I'm not going to do a code audit. I don't care. Never, but this is one of the things - is the package on pypi the exact source I see on Github? You could end up with files that are distributed differently. Probably (I don't do it) because I am too scared to look. There is this thing that pip verifies (the packages) hash - so that is a feature to guard against this. What is the hash of? No idea. It's located in the local python install." **- Participant 240426799 (systems administrator)**

> "No [I don't audit code]. [laughs] Coz, I'm not going to read thousands of lines of code before I install a package. Oh my God. [..] I wouldn't be able to find it. I'm trading off - honestly how popular the package is, number of stars on GH. pypi doesn't have any UI way to tell me how many downloads it has. If it did I would use that." **- Participant 240386315 (IT administrator)**

> "Well, I don't have the background to do a code audit of something like Numerical Python. Most packages I use are huge. Most people aren't doing code of those packages, except the maintainer. I am relying on whatever is built into pip to do package security. I also assume if there is an exploit someone will find it and let the world now. I'm really lazy." **- Participant 240312164 (Nuclear physicist)**

> "I would like some security advisor, [like in npm](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities) - it works very well, when you install a package "there are security vulns. with this package - 1 low, 5 medium, 8 high. I haven't come across security issues with Python packages." **- CZI convening research participant**

## Recommendations

### Provide package security guidance or auditing mechanism

A small number of participants (3-4) over the research period mentioned the[ NPM audit command](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities) as an example of a good way to assess package security. It may provide a model for how to approach this user need.

### Automatically check package hashes

pip should **by default** check packages hashes during install, providing a way for users to turn this behaviour off.

In the case of no hash being available, pip should warn users and provide recommendations for users - from simplest to most advanced.

### Mechanism to report suspicious packages

Users should have a mechanism to report suspicious, or malicious, packages/behaviour. Where this mechanism should exist is open to discussion. The minimum should be a mechanism for users to flag packages on pypi.org.

### Improve the output of pips activities easier to understand

Right now pip's output is overwhelming and while it contains a lot of information, little of it is perceivable to the user - meaning is lost in "the wall of text".

Pip's output must be redesigned to provide users with the right information - including security warnings - at the right time.
