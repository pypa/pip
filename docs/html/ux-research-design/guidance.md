# UX Guidance

This section of the documentation is intended for contributors who wish to work on improving pip's user experience, including pip's documentation.

## What is User Centered Design?

User-centered design (UCD) or human-centered design (HCD) is an iterative process in which design decisions are informed by an understanding of users and their needs. There are many terms used to describe this type of work; in this document we will use "user experience (UX) research and design".

For the pip project, UX research and design can be used to:

- Develop a deeper understanding of pip's users, the context in which they use pip and the challenges that they face
- Inform the design of new or existing pip features, so that pip us more usable and accessible. This may include improving pip's output (including error messages), controls (e.g. commands and flags) and documentation
- Help pip's development team prioritize feature requests based on user needs

At a high level, the UX research and design process is comprised of:

1. **[Research](#conducting-research-for-pip)**, where a variety of techniques are used (e.g.[surveys](#surveys) and [interviews](#interviews)) to learn about users and what they want from the tools they use
2. **[Design](#user-interface-design)**, where solutions are proposed to response to the research conducted. UX research and design is conducted iteratively, with design proposals or prototypes tested with users to validate that they are effective in meeting users' needs. Often, it is necessary to complete several cycles of research, design and validation to find a solution that works:

![Graphic showing an iterative process of Research, Make (Design), Validate, around user goals and needs.](https://user-images.githubusercontent.com/3323703/124515613-c5bae880-ddd7-11eb-99d6-35c0a7522c7a.png)

For more information on how this process has been applied to the pip project, see [research results](research-results/index).

See also:

- [Introduction to user centered design from the interaction design foundation](https://www.interaction-design.org/literature/topics/user-centered-design)
- [User-Centered Design Basics from usability.gov](https://www.usability.gov/what-and-why/user-centered-design.html)
- [User-centered design articles and videos from Nielson Norman Group](https://www.nngroup.com/topic/user-centered-design/)

## Conducting Research for pip

User research can be used to answer a few different types of questions:

- _Understanding the context generally_ — e.g. how is pip used by people? What different environments and contexts is pip used in?
- _Understanding the users more broadly_ — e.g. who uses pip? How much experience do they have typically? How do they learn how to use pip? Are there any common characteristics between pip users? How diverse are the needs of pip's users?
- _Evaluating a specific need or challenge_ — e.g. how are pip users encountering a given issue? When does it come up? Do pip users regularly encounter this issue? How would a new feature address this issue?

During the research process, it is important to engage users for input, and incorporate their feedback into decision making.

Input and feedback from users is as valuable to an open source project as code contributions; end users may not be ready yet to submit a pull request or make fixes into the code directly, but their feedback can help to shape pip's priorities and direction.

There are many ways to engage users in open source projects, and sometimes input from community members can feel overwhelming! Providing a structure, such as surveys and interviews, can make it easier to collect and understand feedback. Some examples of how to engage users are:

- _Surveys_ — good for targeted feedback about specific issues and broad community context and understanding
- _Interviews_ — good for in-depth conversations to understand or explore a topic
- _Testing_ — good to evaluate an issue or validate a design idea
- _Open issue queues_ (e.g. GitHub issues) & support ticket systems — great data source to understand common challenges
- _Forums or discussion tools_ — great data source to understand common challenges or engage broader community in open discussion
- _Conferences and events_ — great opportunity to go lightweight interviews or testing of specific features

When running [UX research on pip in 2020](research-results/index), we found that surveys and interviews were particularly useful tools to engage with pip's users. Some general guidelines, as well as pip-specific recommendations are below.

### Surveys

Surveys are great for collecting broad, large scale input, e.g. learning more about pip's user community as a whole, or for getting targeted feedback about a specific issue.

Surveys can also be leveraged to get in-situ feedback with early releases of new tools, e.g. prompting users on the command line if they are using a beta version of a feature or asking people for feedback on a documentation page.

As an example, in 2020, the pip UX team published several surveys to learn about pip and pip's users. This included:

- Understanding 'who uses pip'
- Collecting feedback about pip's documentation
- Collecting feedback about pip's beta release of the 2020 dependency resolver
- Asking users how specific parts of pip's 2020 dependency resolver should behave

A full list of the surveys published in 2020 and their results [can be found here](research-results/index).

#### Designing Surveys

When designing surveys, it is important to first establish what you want to learn. It can be useful to write this down as research-results/index questions. Example pip research-results/index questions [can be found here](https://github.com/pypa/pip/issues/8518).

If you find that your topic is large, or you have many research-results/index questions, consider publishing several separate surveys, as long surveys risk a low response / high dropoff rate.

Below is a brief guide to building a survey for pip:

<ol>
  <li>
    <strong>Introduce your survey</strong><br>
    Explain the motivation for the survey, or (for surveys about pip's behaviour) set the scene with a scenario.
  </li>
  <li>
    <strong>Design your questions</strong><br>
    <ul>
      <li>
        Limit the number of questions you ask to avoid a low response rate. A good rule of thumb is: 3-4 questions about the specific topic, 2-3 questions about users level of experience / what they use Python or pip for.<br>
        When asking about years of experience use the following groupings as options:
        <ul>
          <li>< 1 Year</li>
          <li>1-3 Years</li>
          <li>4-6 Years</li>
          <li>7-10 Years</li>
          <li>11-15 Years</li>
          <li>16+ Years</li>
        </ul>
      </li>
      <li>
        Use <a href="https://en.wikipedia.org/wiki/Closed-ended_question">closed questions</a> with a fixed number of possible responses (e.g. yes/no, multiple choice, checkboxes, or <a href="https://www.nngroup.com/articles/rating-scales">likert scale</a>) for measuring behaviour, opinion or preferences
      </li>
      <li>
        Use <a href="https://en.wikipedia.org/wiki/Open-ended_question">open questions</a> to learn about reasoning. If you are using a lot of closed questions in your survey, it is useful to include some open questions to "fish" for less expected answers - e.g. asking a user "why?" they chose a particular option
      </li>
    </ul>
  </li>
  <li>
    <strong>Pilot your survey and modify it based on feedback</strong><br>
    This could be as simple as sharing it with 1-2 people to see if it makes sense.
  </li>
  <li>
    <strong>Determine where to do outreach</strong><br>
    Establish who you want to hear from and where you should post the survey. Are there community members or groups that can help you reach more people?<br>
    <ul>
      <li>Does the survey need to be translated into other languages to reach a broader set of the community?</li>
      <li>Are you able to compensate people for their time?</li>
      <li>Do participants want to be acknowledged as contributors?</li>
    </ul>
  </li>
  <li>
    <strong>Launch and promote your survey</strong><br>
    See <a href="#survey-and-interview-outreach">survey and interview outreach</a> for recommendations on how to do outreach for pip based on the UX research-results/index conducted in 2020.
  </li>
</ol>

#### Survey Case Study

The process described above was followed in 2020, when we wanted to establish whether pip [should install packages with conflicting dependencies](https://github.com/pypa/pip/issues/8452).

First, we introduced the purpose of the survey, with a scenario:

![survey introduction with scenario with packages that conflict](https://user-images.githubusercontent.com/3323703/124516502-b046be00-ddd9-11eb-830c-62b8a6fb6182.png)

Next, we asked a closed question to establish what the user prefers:

![survey question asking whether pip should allow users to install packages when there are conflicting dependencies](https://user-images.githubusercontent.com/3323703/124516576-e5eba700-ddd9-11eb-8baf-e07773e75742.png)

Following this, we qualified the response with an open question:

![survey question asking respondents why pip should allow users to install packages with conflicting dependencies](https://user-images.githubusercontent.com/3323703/124516646-129fbe80-ddda-11eb-9c8a-da127f19fccd.png)

This was followed by further questions about workarounds, syntax and behaviour preferences.

Finally, we asked survey participants about themselves, including how much Python experience they have, and what they use Python for. This was to find out if different types of Python users answered the questions differently.

This survey was shared with the pip team and improved several times, before it was published and promoted using a variety of [outreach channels](#survey-and-interview-outreach).

In total, we received 415 responses, with [clear results](research-results/override-conflicting-dependencies) that helped us to make strong recommendations on how to move forward with this feature.

#### Analysing Survey Results

Surveys are particularly useful for being able to quickly understand trends from a larger population of responses. If your questions are designed well, then you should be able to easily aggregate the data and make statements such as: `X% of respondents said that Option B was the best option.`

#### Contextualizing the Responses

It's important to remember that the responses to your survey will be biased by the way that you did outreach for your survey, so unless you can be sure that the people who responded to your survey are representative of all of your users, then you need to be sure to contextualize the results to the participants. Within your survey responses it can be helpful to see if there is variation in the responses by different aspects of your users or your user community, e.g.

- By experience level — Are responses consistent across experience level or do they vary? E.g. Do newer or more junior experience users have different responses, needs or challenges?
- By background/context — Are responses consistent across background or context? E.g. Do users in a corporate context have similar responses to hobbyist/independent users? Do data analysts have similar responses to software engineers?

#### How many responses is enough?

It depends! This is a hard question to answer in research like this — Traditional statistics would suggest that "enough" depends on the total population you need the survey to represent. In UX research, the answer tends to be more around when you see variation in responses level out, and so it's more about signals and trends in the data.

If you are finding that there aren't patterns in the data, it might mean that your questions weren't clear or provided too many options, or it might mean that you need to reach out to more people.

See also:

- [28 Tips for Creating Great Qualitative Surveys from Nielson Norman Group](https://www.nngroup.com/articles/qualitative-surveys/)
- [Open vs. Closed Questions in User Research from Nielsen Norman Group](https://www.nngroup.com/videos/open-vs-closed-questions/)
- [Survey questions 101: over 70 survey question examples + types of surveys and FAQs - from HotJar](https://www.hotjar.com/blog/survey-questions/)

### Interviews

Interviews are a great way to have more in-depth conversations with users to better understand or explore a topic. Unlike surveys, they are not a great way to understand overall patterns, as it is hard to engage with a large number of people due to the time involved. It can be particularly useful to plan around conferences and events as a way to connect with many users in a more informal setting.

#### Designing Interviews

As with surveys, it's important to establish what you want to learn before you begin.

Often, interviews are conducted with a script; this helps the interview run smoothly by providing some structure. However, it is also ok to go "off script" if the conversation is moving in an interesting or insightful direction.

Below is a brief guide to running an interview for pip:

<ol>
  <li>
    <strong>Write your script</strong><br>
    This should include an introduction that sets the scene for the participant, explaining what the interview is about, how you (or observers) will take notes, how long it will take, how their feedback will be used (and shared) and any other pointers you want to share.<br>
    Next, design your questions. Limit the number of questions, so that you have enough time to cover key points and the interview does not run for too long. Like in surveys, a good rule of thumb is 2-3 questions about users' level of experience, and what they use Python/pip for, plus 3-4 questions about the specific topic.<br>
    There are <a href="https://simplysecure.org/resources/qualitative_interviewing.pdf">four different types of interview questions</a>:
    <ol>
      <li>
        <em>Descriptive</em> — This type of question gives you concrete, specific stories and details. It also helps your interviewee "arrive" at the interview, resurfacing their relevant experiences and memories. E.g.<br>
        <ul>
          <li>Tell me about a time…</li>
          <li>Tell me about the first time…</li>
          <li>Tell me about the last time…</li>
          <li>Tell me about the worst/best time…</li>
          <li>Walk me through how you…</li>
        </ul>
      </li>
      <li>
        <em>Reflective</em> — These questions allow the interviewee to revisit and think more deeply about their experiences. Helping the interviewee reflect is at the heart of your interview. Don't rush – give them lots of space to put their thoughts together.<br>
        <ul>
          <li>What do you think about…</li>
          <li>How do you feel about…</li>
          <li>Why do you do…</li>
          <li>Why do you think…</li>
          <li>What effects did it have when…</li>
          <li>How has ... changed over time?</li>
        </ul>
      </li>
      <li>
        <em>Clarifying</em> — This type of question gives interviewees the opportunity to expand on key points. Skillful clarifying questions also let you subtly direct the interviewee's storytelling towards the areas you find most intriguing and relevant.<br>
        <ul>
          <li>What do you mean when you say…</li>
          <li>So, in other words…</li>
          <li>It sounds like you're saying [...]. Is that right?</li>
          <li>Can you tell me more about that?</li>
        </ul>
      </li>
      <li>
        <em>Exploratory</em> — These questions are an invitation to the interview-ee to think creatively about their situation, and are best left for the end of the interview. Careful, though – suggestions from a single person are rarely the answer to your design problem, and you need to be clear to them that you're just collecting ideas at this point.<br/>
        <ul>
          <li>How would you change…</li>
          <li>What would happen if…</li>
          <li>If you had a magic wand...</li>
        </ul>
      </li>
    </ol>
  </li>
  <li>
    <strong>Pilot interview with 1-2 people & modify based on their feedback</strong>
  </li>
  <li>
    <strong>Determine how to do outreach for interviews</strong><br/>
    <ul>
      <li>Who do you want to be sure to hear from? Where do you need to post to contact people for interviews? Are there community members or groups that can help you reach specific people?</li>
      <li>Do the interviews need to be translated into other languages to reach a broader set of the community or a specific community?</li>
      <li>How will people sign up for your interview?</li>
      <li>Are you able to compensate people for their time?</li>
      <li>Do participants want to be acknowledged as contributors?</li>
    </ul>
  </li>
  <li>
    <strong>Start outreach!</strong><br/>
    See <a href="#survey-and-interview-outreach">survey and interview outreach</a> for recommendations on how to do outreach for pip based on the UX research conducted in 2020.
  </li>
</ol>

Here is an example user interview script used for speaking to users about pip's documentation:

> **Introduction**
>
> - Firstly thank you for giving me your time and for your continued involvement.
> - The purpose of this interview is to better understand how pip's documentation is perceived and used by Python community members
> - The interview will take approximately 30 minutes. If you don't understand any of the questions please ask me to repeat or rephrase. If you don't have a good answer, feel free to tell me to skip.
> - I will be taking notes. These will be shared on GitHub or the pip docs, but we will remove any identifying data to > protect your anonymity
> - Please be honest - your feedback can help us make pip better. I won't be offended by anything you have to say :)
> - (optional) Do you mind if I record this session?
>
> **Opening questions**
>
> - Can you tell me a bit about how you use Python?
> - How long have you been using pip?
>
> **Solving problems**
>
> - Can you tell me about a time you had a problem when using pip?
>   - What happened?
>   - What did you do?
>   - Where did you go?
>   - How did you resolve your problem?
> - Please go to[ https://pip.pypa.io/en/stable/](https://pip.pypa.io/en/stable/)
>   - Have you ever used this documentation?
>   - On a scale of 1-10 how useful was it?
>   - Why?
> - Are there any projects that you use that you'd like us to look at when thinking about improving pip's docs?
>   - What makes that documentation good/useful?
>
> **Conclusion**
>
> - What one thing could the pip team do to help users troubleshoot pip problems?
> - Do you have any questions?

#### How many interviews is enough?

This depends on the complexity of the issue you are discussing, and whether or not you feel that you have gained enough insight from the interviews you have conducted. It also depends on whether you feel you have heard from a wide enough range of people. For example, you may wish to stop interviewing only after you have heard from both expert _and_ novice pip users.

Often, conducting just a few interviews will uncover so many problems that there is enough material to make recommendations to the team.

#### Analyzing Interview Data

Formal interview analysis typically uses a process called "coding" where multiple researchers review interview transcripts and label different statements or comments based on a code system or typology that has been developed to align with the research. This is a great practice and a great way to make sure that the researchers' bias is addressed as part of the process, but most teams do not have the staffing or resources to do this practice.

Instead many smaller teams use lightweight processes of capturing interview statements into **themes**, e.g. specific topics or issue areas around needs or challenges. Interviews are also a great source for **quotes**, which can be helpful for providing an example of why something is important or when/how something comes up for users.

Interview analysis is frequently done using sticky notes, where you can write a quote, issue or finding on a sticky note and then move the sticky notes around into clusters that can be labeled or categorized into the themes. Remotely this can be facilitated by any number of tools, e.g. digital sticky board tools like [Miro](https://miro.com/) or [Mural](https://www.mural.co/), or even kanban board tools like [Trello](https://trello.com/), [Wekan](https://wekan.github.io/) or [Cryptpad](https://cryptpad.fr/), or this can be done just with text documents or spreadsheets, using lists and categories. It can be helpful to use a [worksheet for debriefing](https://simplysecure.org/resources/interview_synthesis.pdf) at the end of each interview to capture insights and themes quickly before you forget topics from the specific interview.

See also:

- [User Interviews: How, When, and Why to Conduct Them from Nielson Norman Group](https://www.nngroup.com/articles/user-interviews/)
- [Interviewing Users from Nielson Norman Group](https://www.nngroup.com/articles/interviewing-users/)

### Survey and Interview Outreach

The following is a list of outreach platforms that the pip team used when conducting research in 2020. Some were more successful than others:

#### Recommended: UX Research Panel

As part of the [2020 UX Work](research-results/index), we published a form that asked people to join a research panel and be regularly contacted about surveys and interview opportunities. This is now a [mailing list that users can sign up for](https://mail.python.org/mailman3/lists/pip-ux-studies.python.org/), and will be used in an ongoing way in addition to broad public outreach.

#### Recommended: Twitter

We found Twitter to be a very effective platform for engaging with the Python community and drive participation in UX research. We recommend:

1. Asking [ThePSF](https://twitter.com/ThePSF), [PyPA](https://twitter.com/ThePyPA) and [PyPI](https://twitter.com/pypi) to retweet calls for survey and interview participation
2. Asking specific individuals (who have reach within specific communities, or general followings within the Python community) to retweet.
3. Explicitly asking for retweets within tweets
4. Responding to users within Twitter

#### Recommended: Specific Interest Groups

We engaged with the [PyLadies](https://pyladies.com/) community via their [Slack channel](https://slackin.pyladies.com/) to drive more participation from women using pip, as we found this demographic more difficult to reach via other channels

#### Recommended: Conference Communities

Due to the 2020 Global Pandemic we were unable to engage with users via PyCon (or other regional conferences) as we would have liked. However, we would still recommend this channel as a fast and insightful way to engage with large groups of interested people.

#### Worth Exploring: Adding a prompt/path into pip's 'help' command

We didn't have a chance to explore this opportunity, but the idea came up during workshops in December 2020 with Pypa Maintainers, and could be a great way to engage users and help point them towards opportunities to contribute.

#### Not recommended: Forums (Discourse, etc)

We used [discuss.python.org](https://discuss.python.org/) several times, posting to the [packaging forum](https://discuss.python.org/c/packaging/14) to ask packaging maintainers about their views on pip's functionality. Unfortunately, this was not as fruitful as we hoped, with very few responses. We found that engaging with packaging maintainers via Twitter was more effective.

Posting surveys on Reddit was also not as useful as we had expected. If the user posting the survey or call for research participation does not have significant credit on Reddit, then the posting process itself can be challenging. Overall we did not see as much engagement in surveys or interviews come from Reddit relative to other outreach means.

## User Interface Design

Many people associate the term "user interface" with websites or applications, however it is important to remember that a CLI is a user interface too, and deserves the same design consideration as graphical user interfaces.

Designing for pip includes:

- Designing pip's _input_ - establishing the best way to group functionality under commands, and how to name those commands so that they make sense to the user
- Writing pip's _output_ - establishing how pip responds to commands and what information it provides the user. This includes writing success and error messages.
- Providing supplemental materials - e.g. documentation that helps users understand pip's operation

### Error Message Format

A good error message should mention:

* what the user has tried to do
* possible next steps to try and solve the error
  * possible steps need to go from "easiest" to "most complicated"
* why the error has happened - include a way to see more information
  about the situation

A [sample `ResolutionImpossible` error that follows this guidance
is available](resolution-impossible-example).

**Further reading**

- <https://uxplanet.org/how-to-write-good-error-messages-858e4551cd4>
- <https://www.nngroup.com/articles/error-message-guidelines/>

### Design Principles / Usability Heuristics

There are many interaction design principles that help designers design great experiences. Nielsen Norman's [10 Usability Heuristics for User Interface Design](https://www.nngroup.com/articles/ten-usability-heuristics) is a great place to start. Here are some of the ways these principles apply to pip:

- Visibility of system status: ensure all commands result in clear feedback that is relevant to the user - but do not overload the user with too much information (see "Aesthetic and minimalist design")
- Consistency and standards: when writing interfaces, strive for consistency with the rest of the Python packaging ecosystem, and (where possible) adopt familiar patterns from other CLI tools
- Aesthetic and minimalist design: remove noise from CLI output to ensure the user can find the most important information
- Help users recognize, diagnose, and recover from errors: clearly label and explain errors: what happened, why, and what the user can do to try and fix the error. Link to documentation where you need to provide a detailed explanation.
- Help and documentation: provide help in context and ensure that documentation is task-focussed

#### Additional Resources

- [Command Line Interface Guidelines](https://clig.dev)
- [10 design principles for delightful CLIs](https://blog.developer.atlassian.com/10-design-principles-for-delightful-clis/)

### Design Tools

Tools that are frequently used in the design process are personas and guidelines, but also wireframing, prototyping, and testing, as well as creating flow diagrams or models.

#### Personas

_For a more in-depth overview of personas and using them in open source projects, this [resource from Simply Secure](https://simplysecure.org/blog/personas) may be helpful._

Personas are abstractions or archetypes of people who might use your tool. It often takes the form of a quick portrait including things like — name, age range, job title, enough to give you a sense of who this person is. You can capture this information into a [persona template](https://simplysecure.org/resources/persona-template-tech.pdf) and share them with your open source community as a resource see [examples from the Gitlab UX Team](https://about.gitlab.com/handbook/marketing/strategic-marketing/roles-personas/).

Personas are particularly useful to help ground a feature design in priorities for specific needs of specific users. This helps provide useful constraints into the design process, so that you can focus your work, and not try to make every feature a swiss army knife of solutions for every user.

In 2020, the pip UX team developed the following personas for the pip project:

- Python Software User
- Python Software Maker
- Python Package Maintainer

An in-depth write up on how the pip personas were created, and how they can be applied to future pip UX work can be [found here](research-results/personas).

#### Prototyping

In any UX project, it is important to prototype and test interfaces with real users. This provides the team with a feedback loop, and ensures that the solution shipped to the end user meets their needs.

Prototyping CLIs can be a challenge. See [Creating rapid CLI prototypes with cli-output](https://www.ei8fdb.org/prototyping-command-line-interfaces-with-cli-output/) for recommendations.

#### Copywriting Style Guides

Given pip's interface is text, it is particularly important that clear and consistent language is used.

The following copywriting Style Guides may be useful to the pip team:

- [Warehouse (PyPI) copywriting styleguide and glossary of terms](https://warehouse.readthedocs.io/ui-principles.html#write-clearly-with-consistent-style-and-terminology)
- Firefox:
  - [Voice and Tone](https://meet.google.com/linkredirect?authuser=0&dest=https%3A%2F%2Fdesign.firefox.com%2Fphoton%2Fcopy%2Fvoice-and-tone.html)
  - [Writing for users](https://meet.google.com/linkredirect?authuser=0&dest=https%3A%2F%2Fdesign.firefox.com%2Fphoton%2Fcopy%2Fwriting-for-users.html)
- [Heroku CLI](https://devcenter.heroku.com/articles/cli-style-guide) (very specific to Heroku's CLI tools)
- [Redhat Pattern Fly style guide](https://www.patternfly.org/v4/ux-writing/about)
- [Writing for UIs from Simply Secure](https://simplysecure.org/blog/writing-for-uis)

### General Resources

- Heroku talk on design of their CLI tools ([video](https://www.youtube.com/watch?v=PHiDG-_XoRk) transcript)
- [Simply Secure: UX Starter Pack](https://simplysecure.org/ux-starter-pack/)
- [Simply Secure: Feedback Gathering Guide](https://simplysecure.org/blog/feedback-gathering-guide)
- [Simply Secure: Getting Quick Tool Feedback](https://simplysecure.org/blog/design-spot-tool-feedback)
- [Internews: UX Feedback Collection Guidebook](https://globaltech.internews.org/our-resources/ux-feedback-collection-guidebook)
- [Simply Secure: Knowledge Base](http://simplysecure.org/knowledge-base/)
- [Open Source Design](https://opensourcedesign.net/resources/)
- [Nielsen Norman Group](https://www.nngroup.com/articles/)
- [Interaction Design Foundation](https://www.interaction-design.org/literature)
