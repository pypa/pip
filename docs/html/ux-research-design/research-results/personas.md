# pip Personas

## Problem

We want to develop personas for pip's user to facilitate faster user-centered decision making for the pip development team.

[Skip to recommendations](#recommendations)

## Research

From early interviews with pip users, and from desk research into the different communities that use Python, it was our expectation that there were large communities who were not professional software developers. For example the SciPy library is widely used in the science and engineering communities for mathematical analysis, signal and image processing.

Based on this, we expected a lot of these users would have different expectations, challenges and needs from pip.

Our hypothesis was that:

1. Python users fall into 3 main user types - a software user, a software maker and a software/package maintainer
2. That the majority (over 60%) would define themselves as Python software users
3. That the minority would define themselves as Python software maintainers

### Usertype definitions

During the research we've met different user types in the Python community. The 3 types of Python users, we proposed were:

#### The Python Software User

"I use Python software mainly as a tool to help me do what I want to do. This might be running scientific experiments, making music or analysing data with Python software I install with pip. I don't write Python software for others."

#### The Python Software Maker

"I use the Python software language and Python software packages to make software for others, mostly for other people. An example might be - building web applications for my customers. To make this web application I might use the Django framework, and a number of Python packages and libraries."

#### The Python Package Maintainer

"I spend a lot of my time creating Python software packages and libraries for other people to use in the software they make. I might make Python packages and libraries and then publish them on pypi.org or other software repositories."

## Results

During our research we found that these user types did fit with participants' sense of their usage of Python. Participants did not identify significantly different Python user types when asked.

Each of these user types is a spectrum. Some Python users after time, and with experience/training, a need to use code more than once, started to make their own Python software.

Identifying as one of these user types does not preclude users from also being another user type. Python users were more likely to Python software makers, but rarely Python software maintainers.

Most (86%) participants identified as being a Python software user. This ranged a) from using Python applications - SciPy, Scikit-Learn - as a tool, with no knowledge, or interest to do more, to b) more advanced usage of Python involving modifying others code/scripts, possibly using libraries to create code specifically for their needs.

75% identified as a Python software maker - as with Python software user, this ranged from writing basic scripts, code, to being a professional software developer.

40% identified as a Python software maintainer - the activities of a maintainer were seen as only available to someone who had many years of Python experience, was heavily involved in a particular package or application, or did it as part of their job.

### I am a Python software user

As expected, almost all participants identified as a Python software user (86%). This was the most fundamental user type - both trained software developers and those who came to Python as a result of their job were users.

Non-software developer users identified Python as a language to get stuff done -

> "Almost everyone falls into the user (category) - that’s the target. It's not an obscure language that's meant for specific domains - it's a broad general purpose language designed to get stuff done. It's used by many who don't know other languages, they just need a language to get what they're doing finished." **- Participant 240312164**

However, "using Python software" meant different things depending on who you ask - participants identified as a Python software user on a spectrum.

<table>
  <thead>
    <tr>
     <th>I am a Python software user</th>
     <th>Number of responses</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>I agree</td>
      <td>50</td>
    </tr>
    <tr>
      <td>I disagree</td>
      <td>4</td>
    </tr>
    <tr>
      <td>I have no opinion</td>
      <td>11</td>
    </tr>
    <tr>
      <td>I strongly agree</td>
      <td>70</td>
    </tr>
    <tr>
      <td>I strongly disagree</td>
      <td>4</td>
    </tr>
    <tr>
      <td><strong>Grand Total</strong></td>
      <td><strong>140</strong></td>
    </tr>
  </tbody>
</table>

![Pie chart with responses to question - I am a Python software user](https://i.imgur.com/ir3tP3B.png)

#### Low end of the spectrum

Python software applications were identified by some as a tool they use to do their "actual" work - the scientist, the data analyst, the engineer, the journalist.

Here, they were "using" Python applications like SciPy, PsychPi, NumPy, to run scientific experiments, to gather data, to analyse data, with the objective of creating knowledge to make decisions, to identify what to do next.

These were users who 1) who were new to Python software, 2) came across these Python applications in their profession, and used them as tools.

They describe NumPy, or SciPy as a Python software application in itself, analogous to being a Windows user, or a Mac user.

These users are not "classically trained programmers" as one participant identified themselves. As a result, they may not have the training, or knowledge about programming concepts like software dependencies. When they are expected to deal with complex or confusing error messages or instructions they have problems, often stopping them.

#### High-end of the spectrum

Python users who "move up the spectrum" to more advanced Python usage had been using Python for longer periods - many years.

Again they may not have been classically trained developers, but through exposure - from work colleagues and their own usage - they started to experiment. This experimentation was in the form of modifying others scripts, taking classes, reading books so they could use code for other purposes.

This was _making_ software - this software could be used by them as part of their day-job, but it could also be used by many others.

We asked participants to explain the progression on this user spectrum - what is the difference between a user and a maker?

Participants spoke about "are you working on something reusable or are you using the tools to achieve a one time task?"

> "I didn't have classic software development training, more statistical analysis experience. I was clueless to the idea that it was a repository that anyone could upload packages to and become a maintainer." **- Participant \_240396891 (Data scientist at an applied research lab using Python do to network traffic analysis/parsing or Machine Learning)**

> "Firstly I use my own software written in Python, I use Python libraries from pip. I use Django, Flask, libraries like requests." **- Participant 240302171**

> "I am not a classically trained programmer, so it's a great way for me to learn and keep current in techniques. Not being a classically trained programmer, in some cases it detracts, I have a reasonable knowledge of the way to use hashes, but if I wanted to change Python's hash I'd have to read books. I can find information out there." **- Participant 240312164 (Nuclear physicist using Python for computer simulations, designing experimental methods)**

### I am a Python software maker

Being a "Python software maker" was a natural progression for some Python users, particularly those who had software development training - either on the job, personal learning or formal education. This training was important to understand fundamental programming concepts.

As discussed earlier, some participants identified as "advanced" Python users, using Python software to modify or create other software. These users were likely to progress onto being software makers.

55% of participants who identified as a software maker had between 5-20+ years of experience with Python. Only 18% of software makers had less than 2 years of experience.

![Pie chart with responses to question - I am a Python software maker](https://i.imgur.com/aqg1kaL.png)

We did not ask these participants about the "quality" of the software they created, but apart from the professional software developers, the opinion of these users was they were not software developers.

<table>
  <thead>
    <tr>
     <th>I am a Python software user</th>
     <th>Number of responses</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>I agree</td>
      <td>50</td>
    </tr>
    <tr>
      <td>I disagree</td>
      <td>9</td>
    </tr>
    <tr>
      <td>I have no opinion</td>
      <td>14</td>
    </tr>
    <tr>
      <td>I strongly agree</td>
      <td>56</td>
    </tr>
    <tr>
      <td>I strongly disagree</td>
      <td>10</td>
    </tr>
    <tr>
     <td><strong>Grand Total</strong></td>
     <td><strong>140</strong></td>
    </tr>
  </tbody>
</table>

Making software was as defined earlier as "are you working on something reusable or are you using the tools to achieve a one time task?"

> "I'm using Python software and libraries to make this product I'm working on, it's foundation is based on Python, with React, D3 and all built on Python. The cloud assets are Python and testing is Python." **- Participant 240315927 (a professional IT developer building a Python based data analysis application)**

> "I make software in Python. My day job is making software in python. Mainly Django web design. I work for a retail company, where I write calculating orders, creating data in other inventory management systems. Data analysis." **- Participant 240393825**

> "I have written software, sometimes for business and personal reasons. At one point I worked on a django website project, that was being used by 1000s of people. I don't think any of my live projects are based.

> "Most of it is for sysadmin, automation. I [like] to use python instead of shell scripting. I manage a server with wordpress sites. I wrote a script to update these sites, mailman list and sql DB management, and for different utilities." **- Participant 240313542**

> "I use Python for creating things - like outputs for data scientist, software engineer. I make software to look at patterns, and analyse stuff. I think I'm a maker because someone else is using - they are colleagues. Usually its non-technical colleagues. I produce outputs - make data understandable. They use the results, or a package it behind a flask app. Or analyse graphs." **- Participant 240426799**

### I am a Python software maintainer

The Python software/package maintainer user type was seen as requiring a significant amount of time and experience - domain experience as the software could be very specific (e.g. SciKit Learn, SciPy, etc), technical/coding experience, and experience in the community. You need to have spent time in doing the other jobs, before you could become a maintainer.

For large projects it was seen as necessary to have core code contributors, and maintainers. Maintainers did not always write code - they could be more involved with technical architecture, technical design, than writing code.

An aspect of the software maintainer role that wasn’t mentioned a lot was the community management aspect.

![Pie chart with responses to question - I am a Python software maintainer](https://i.imgur.com/gXPc946.png)

<table>
  <thead>
    <tr>
      <th>I am a Python package maintainer</th>
      <th>Number of responses</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>I agree</td>
      <td>39</td>
    </tr>
    <tr>
      <td>I disagree</td>
      <td>24</td>
    </tr>
    <tr>
      <td>I have no opinion</td>
      <td>20</td>
    </tr>
    <tr>
      <td>I strongly agree</td>
      <td>18</td>
    </tr>
    <tr>
      <td>I strongly disagree</td>
      <td>38</td>
    </tr>
    <tr>
     <td><strong>Grand Total</strong></td>
     <td><strong>140</strong></td>
    </tr>
  </tbody>
</table>

> "You can become a maintainer once you get past a certain level of experience." **- Participant 240278297**

> "To be a package maintainer, you'd have to spend a lot of time fixing issues, e.g. your package is on Github and you'd be looking at issues, reviewing PRs, writing documentation. A package maintainer is someone heavily involved in the project. They deal with more support calls, they do more thinking about issues to get your package into multiple environments. That's the good thing about the Python community - I was trying to use a Python package but there was an issue with the documentation. I said, there's a better way of doing this example. They answered and said "great, do you want to do it? Doing package maintaining, it doesn't interest me, I don't have time for it really - if I have a specific issue I will focus on it. It'd be nice (to do more)." **- Participant 240278297 (professional Python software developer)**

> "I am a core developer of scikit-learn, I spend time writing code. These days strictly speaking - writing code is the least thing I do - mostly I do reviews of other people's code. There is a lot of API design work, it can translate into writing code. I may be the one writing the code or not. I am involved with the CI every now and then. [...] I have been the release manager for the last 2 releases. There are different types of maintainer - writing code maintainers, but you do need core devs writing code. But being a maintainer and building a community -that is about communication and PRs, and mentoring people." **- Participant 240306385 (core maintainer of SciKit-Learn)**

## Recommendations

### Provide documentation recommending "best/recommended ways"

The majority of participants were using Python as a tool, as a participant said: "it's a broad general purpose language designed to get stuff done."

The majority of participants - scientists, product/electronic engineers, data analysts, nuclear physicists - used Python for their work - they may write Python software, for themselves, possibly for colleagues. A smaller number are maintainers of widely used Python packages.

As a result they are not classically trained software developers and so may not have "the right" understanding of important software programming concepts.

Users of all types, and experience struggled with knowing the "right" way to do something. They often spoke about the "recommended way" to do something - to start a new project, to make a package:

> "As a new comer, it's not easy to figure out what should be in the right way to structure a _setup.py_ or _pyproject.toml_. There is a good guide, but it's not easy to figure out what to use. I wish there was a guide like 'Make an application (or library) in 30 minutes'."
