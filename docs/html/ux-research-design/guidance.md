# Pip UX research and design guidelines

This section of the documentation is intended for contributors who wish to work on improving pip's user experience, including pip's documentation.

## What is user centered design?

User-centered design (UCD) or human-centered design (HCD) is an iterative process in which  design decisions are informed by an understanding of users and their needs. There are many terms used to describe this type of work; in this document we will use "user experience (UX) research and design".

For the pip project, UX research and design can be used to:

- Develop a deeper understanding of pip's users, the context in which they use pip and the challenges that they face
- Inform the design of new or existing pip features, so that pip us more usable and accessible. This may include improving pip's output (including error messages), controls (e.g. commands and flags) and documentation
- Help pip's development team prioritize feature requests based on user needs

At a high level, the UX research and design process is comprised of:

1. **[Research](#research)**, where a variety of techniques are used (e.g.[surveys](#surveys) and [interviews](#interviews)) to learn about users and what they want from the tools they use
2. **[Design](#design)**, where solutions are proposed to response to the research conducted. UX research and design is conducted iteratively, with design proposals (i.e. [prototypes](#prototypes)) tested with users to validate that they are effective in meeting users' needs. Often, it is necessary to complete several cycles of research, design and validation to find a solution that works:

![Graphic showing an iterative process of Research, Make (Design), Validate, around user goals and needs.](images/image1.png "image_tooltip")

For more information on how this process has been applied to the pip project, see [research results](#ux-research-design/research-results).

See also:

- [https://www.interaction-design.org/literature/topics/user-centered-design](https://www.interaction-design.org/literature/topics/user-centered-design)
- [https://www.usability.gov/what-and-why/user-centered-design.html](https://www.usability.gov/what-and-why/user-centered-design.html)
- [https://www.nngroup.com/topic/user-centered-design/](https://www.nngroup.com/topic/user-centered-design/)


## <a name="research"></a>Conducting research for pip

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
- _Open issue queues_ (e.g. Github issues) & Support ticket systems — great data source to understand common challenges
- _Forums or discussion tools_ — great data source to understand common challenges or engage broader community in open discussion
- _Conferences and events_ — great opportunity to go lightweight interviews or testing of specific features

When running [UX research on pip in 2020](ux-research-design/research-results), we found that surveys and interviews were particularly useful tools to engage with pip's users. Some general guidelines, as well as pip-specific recommendations are below.

### <a name="surveys"></a>Surveys

Surveys are great for collecting broad, large scale input, e.g. learning more about pip's user community as a whole, or for getting targeted feedback about a specific issue.

Surveys can also be leveraged to get in-situ feedback with early releases of new tools, e.g. prompting users on the command line if they are using a beta version of a feature or asking people for feedback on a documentation page.

As an example, in 2020, the pip UX team published several surveys to learn about pip and pip's users. This included:

- Understanding ‘who uses pip'
- Collecting feedback about pip's documentation
- Collecting feedback about pip's beta release of the 2020 dependency resolver
- Asking users how specific parts of pip's 2020 dependency resolver should behave

A full list of the surveys published in 2020 and their results [can be found here](#TODO).

#### Designing surveys

When designing surveys, it is important to first establish what you want to learn. It can be useful to write this down as research questions. Example pip research questions [can be found here](https://github.com/pypa/pip/issues/8518).

If you find that your topic is large, or you have many research questions, consider publishing several separate surveys, as long surveys risk a low response / high dropoff rate.

Below is a brief guide to building a survey for pip:

1. **Introduce your survey** \
Explain the motivation for the survey, or (for surveys about pip's behaviour) set the scene with a scenario.
2. **Design your questions**
  1. Limit the number of questions you ask to avoid a low response rate. A good rule of thumb is: 3-4 questions about the specific topic, 2-3 questions about users level of experience / what they use Python or pip for. \
When asking about years of experience use the following groupings as options:
    - < 1 Year
    - 1-3 Years
    - 4-6 Years
    - 7-10 Years
    - 11-15 Years
    - 16+ Years
  2. Use **[closed questions](https://en.wikipedia.org/wiki/Closed-ended_question)** with a fixed number of possible responses (e.g. yes/no, multiple choice, checkboxes, or [likert scale](https://www.nngroup.com/articles/rating-scales)) for measuring behaviour, opinion or preferences
  3. Use **[open questions](https://en.wikipedia.org/wiki/Open-ended_question)** to learn about reasoning. If you are using a lot of closed questions in your survey, it is useful to include some open questions to “fish” for less expected answers - e.g. asking a user “why?” they chose a particular option
3. **Pilot your survey and modify it based on feedback** \
This could be as simple as sharing it with 1-2 people to see if it makes sense.
4. **Determine where to do outreach**  \
Establish who you want to hear from and where you should post the survey. Are there community members or groups that can help you reach more people?
  - Does the survey need to be translated into other languages to reach a broader set of the community?
  - Are you able to compensate people for their time?
  - Do participants want to be acknowledged as contributors?
5. **Launch and promote your survey**

See [survey and interview outreach](#outreach) for recommendations on how to do outreach for pip based on the UX research conducted in 2020.

#### Survey case study

The process described above was followed in 2020, when we wanted to establish whether pip [should install packages with conflicting dependencies](https://github.com/pypa/pip/issues/8452).

First, we introduced the purpose of the survey, with a scenario:

![alt_textTODO](images/image2.png "image_tooltip")

Next, we asked a closed question to establish what the user prefers:

![alt_textTODO](images/image3.png "image_tooltip")

Following this, we qualified the response with an open question:

![alt_textTODO](images/image4.png "image_tooltip")

This was followed by further questions about workarounds, syntax and behaviour preferences.

Finally, we asked survey participants about themselves, including how much Python experience they have, and what they use Python for. This was to find out if different types of Python users answered the questions differently.

This survey was shared with the pip team and improved several times, before it was published and promoted using a variety of [outreach channels](TODO).

In total, we received 415 responses, with [clear results](https://hackmd.io/MIRY9jpRSNyuzMXoWmSqIg) that helped us to make strong recommendations on how to move forward with this feature.

#### Analysing Survey Results

Surveys are particularly useful for being able to quickly understand trends from a larger population of responses. If your questions are designed well, then you should be able to easily aggregate the data and make statements such as: _`X% of respondents said that Option B was the best option._`

#### Contextualizing the responses

It's important to remember that the responses to your survey will be biased by the way that you did outreach for your survey, so unless you can be sure that the people who responded to your survey are representative of all of your users, then you need to be sure to contextualize the results to the participants. Within your survey responses it can be helpful to see if there is variation in the responses by different aspects of your users or your user community, e.g.

- By experience level — Are responses consistent across experience level or do they vary? E.g. Do newer or more junior experience users have different responses, needs or challenges?
- By background/context — Are responses consistent across background or context? E.g. Do users in a corporate context have similar responses to hobbyist/independent users? Do data analysts have similar responses to software engineers?

#### How many responses is enough?

It depends! This is a hard question to answer in research like this — Traditional statistics would suggest that “enough” depends on the total population you need the survey to represent. In UX research, the answer tends to be more around when you see variation in responses level out, and so it's more about signals and trends in the data.

If you are finding that there aren't patterns in the data, it might mean that your questions weren't clear or provided too many options, or it might mean that you need to reach out to more people.

See also:

- [https://www.nngroup.com/articles/qualitative-surveys/](https://www.nngroup.com/articles/qualitative-surveys/)
- [https://www.nngroup.com/videos/open-vs-closed-questions/](https://www.nngroup.com/videos/open-vs-closed-questions/)
- [https://www.hotjar.com/blog/survey-questions/](https://www.hotjar.com/blog/survey-questions/)


### <a name="interviews"></a>Interviews

Interviews are a great way to have more in-depth conversations with users to better understand or explore a topic. Unlike surveys, they are not a great way to understand overall patterns, as it is hard to engage with a large number of people due to the time involved. It can be particularly useful to plan around conferences and events as a way to connect with many users in a more informal setting.

#### Designing Interviews for pip

As with surveys, it's important to establish what you want to learn before you begin.

Often, interviews are conducted with a script; this helps the interview run smoothly by providing some structure. However, it is also ok to go “off script” if the conversation is moving in an interesting or insightful direction.

Below is a brief guide to running an interview for pip:

1. **Write your script** \
This should include an introduction that sets the scene for the participant, explaining what the interview is about, how you (or observers) will take notes, how long it will take, how their feedback will be used (and shared) and any other pointers you want to share. \
Next, design your questions. Limit the number of questions, so that you have enough time to cover key points and the interview does not run for too long. Like in surveys, a good rule of thumb is 2-3 questions about users' level of experience, and what they use Python/pip for, plus 3-4 questions about the specific topic. \
There are [four different types of interview questions](https://simplysecure.org/resources/qualitative_interviewing.pdf):
  1. _Descriptive_ — This type of question gives you concrete, specific stories and details. It also helps your interviewee “arrive” at the interview, resurfacing their relevant experiences and memories. E.g.
    - Tell me about a time…
    - Tell me about the first time…
    - Tell me about the last time…
    - Tell me about the worst/best time…
    - Walk me through how you…
  2. _Reflective_ — These questions allow the interviewee to revisit and think more deeply about their experiences. Helping the interviewee reflect is at the heart of your interview. Don't rush – give them lots of space to put their thoughts together.
    - What do you think about…
    - How do you feel about…
    - Why do you do…
    - Why do you think…
    - What effects did it have when…
    - How has ... changed over time?
  3. _Clarifying_ — This type of question gives interviewees the opportunity to expand on key points. Skillful clarifying questions also let you subtly direct the interviewee's storytelling towards the areas you find most intriguing and relevant.
    - What do you mean when you say…
    - So, in other words…
    - It sounds like you're saying [...]. Is that right?
    - Can you tell me more about that?
  4. _Exploratory_ — These questions are an invitation to the interview-ee to think creatively about their situation, and are best left for the end of the interview. Careful, though – suggestions from a single person are rarely the answer to your design problem, and you need to be clear to them that you're just collecting ideas at this point.
    - How would you change…
    - What would happen if…
    - If you had a magic wand...
2. **Pilot interview with 1-2 people & modify based on their feedback**
3. **Determine how to do outreach for interviews**
  - Who do you want to be sure to hear from? Where do you need to post to contact people for interviews? Are there community members or groups that can help you reach specific people?
  - Do the interviews need to be translated into other languages to reach a broader set of the community or a specific community?
  - How will people sign up for your interview?
  - Are you able to compensate people for their time?
  - Do participants want to be acknowledged as contributors?
4. **Start outreach!**

See [survey and interview outreach](#outreach) for recommendations on how to do outreach for pip based on the UX research conducted in 2020.

Here is an example user interview script used for speaking to users about pip's documentation:

> **Introduction**
>
> - Firstly thank you for giving me your time and for your continued involvement.
> - The purpose of this interview is to better understand how pip's documentation is perceived and used by Python community members
> - The interview will take approximately 30 minutes. If you don't understand any of the questions please ask me to  repeat or rephrase. If you don't have a good answer, feel free to tell me to skip.
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

#### Analyzing interview data

Formal interview analysis typically uses a process called “coding” where multiple researchers review interview transcripts and label different statements or comments based on a code system or typology that has been developed to align with the research. This is a great practice and a great way to make sure that the researchers' bias is addressed as part of the process, but most teams do not have the staffing or resources to do this practice.

Instead many smaller teams use lightweight processes of capturing interview statements into **themes**, e.g. specific topics or issue areas around needs or challenges. Interviews are also a great source for **quotes**, which can be helpful for providing an example of why something is important or when/how something comes up for users.

Interview analysis is frequently done using sticky notes, where you can write a quote, issue or finding on a sticky note and then move the sticky notes around into clusters that can be labeled or categorized into the themes. Remotely this can be facilitated by any number of tools, e.g. digital sticky board tools like [Miro](https://miro.com/) or [Mural](https://www.mural.co/), or even kanban board tools like [Trello](https://trello.com/), [Wekan](https://wekan.github.io/) or [Cryptpad](https://cryptpad.fr/), or this can be done just with text documents or spreadsheets, using lists and categories. It can be helpful to use a [worksheet for debriefing](https://simplysecure.org/resources/interview_synthesis.pdf) at the end of each interview to capture insights and themes quickly before you forget topics from the specific interview.

See also:

- [https://www.nngroup.com/articles/user-interviews/](https://www.nngroup.com/articles/user-interviews/)
- [https://www.nngroup.com/articles/interviewing-users/](https://www.nngroup.com/articles/interviewing-users/)


### <a name="outreach"></a>Survey and interview outreach

TODO !!!!

The following is a list of outreach platforms that the pip team used when conducting research in 2020. Some were more successful than others:

1. **Recommended: **UX Research Panel** \
As part of the

<p id="gdcalert21" ><span style="color: red; font-weight: bold">>>>>>  gd2md-html alert: undefined internal link (link text: "2020 UX Work"). Did you generate a TOC? </span><br>(<a href="#">Back to top</a>)(<a href="#gdcalert22">Next alert</a>)<br><span style="color: red; font-weight: bold">>>>>> </span></p>

[2020 UX Work](#heading=h.9afrh0qpjvbk), we published a form that asked people to join a research panel and be regularly contacted about surveys and interview opportunities. This is now a [mailing list that users can sign up for](https://mail.python.org/mailman3/lists/pip-ux-studies.python.org/), and will be used in an ongoing way in addition to broad public outreach.
2. **Recommended: **Twitter** \
We found Twitter to be a very effective platform for engaging with the Python community and drive participation in UX research. We recommend:
    1. Asking [ThePSF](https://twitter.com/ThePSF), [PyPA](https://twitter.com/ThePyPA) and [PyPI](https://twitter.com/pypi) to retweet calls for survey and interview participation
    2. Asking specific individuals (who have reach within specific communities, or general followings within the Python community) to retweet.
    3. Explicitly asking for retweets within tweets: \


<p id="gdcalert22" ><span style="color: red; font-weight: bold">>>>>>  gd2md-html alert: inline image link here (to images/image5.png). Store image on your image server and adjust path/filename/extension if necessary. </span><br>(<a href="#">Back to top</a>)(<a href="#gdcalert23">Next alert</a>)<br><span style="color: red; font-weight: bold">>>>>> </span></p>


![alt_text](images/image5.png "image_tooltip")

    4. Responding to users within Twitter
3. **Not recommended: **Forums (Discourse, etc)
    5. We used [discuss.python.org](https://discuss.python.org/) several times, posting to the [packaging forum](https://discuss.python.org/c/packaging/14) to ask packaging maintainers about their views on pip's functionality. Unfortunately, this was not as fruitful as we hoped, with very few responses. We found that engaging with packaging maintainers via Twitter was more effective.
    6. Posting surveys on Reddit was also not as useful as we had expected. If the user posting the survey or call for research participation does not have significant credit on reddit, then the posting process itself can be challenging. Overall we did not see as much engagement in surveys or interviews come from Reddit relative to other outreach means.
4. **Recommended: **Specific Interest Groups \
We engaged with the [PyLadies](https://pyladies.com/) community via their [Slack channel](https://slackin.pyladies.com/) to drive more participation from women using pip, as we found this demographic more difficult to reach via other channels
5. **Recommended:** Conference communities \
Due to the 2020 Global Pandemic we were unable to engage with users via PyCon (or other regional conferences) as we would have liked. However, we would still recommend this channel as a fast and insightful way to engage with large groups of interested people.
6. **Worth Exploring:** Adding a prompt/path into the ‘help' command in the command line tool.  \
We didn't have a chance to explore this opportunity, but the idea came up during workshops in December 2020 with Pypa Maintainers, and could be a great way to engage users and help point them towards opportunities to contribute.


### <a name="design"></a>**Design / User interface design**

Many people associate the term “user interface” with websites or applications, however it is important to remember that a CLI is a user interface too, and deserves the same design consideration as graphical user interfaces.

Designing for pip includes:

- Designing pip's _input_ - establishing the best way to group functionality under commands, and how to name those commands so that they make sense to the user
- Writing pip's _output_ - establishing how pip responds to commands and what information it provides the user. This includes writing success and error messages.
- Providing supplemental materials  - e.g. documentation that helps users understand pip's operation

#### Design principles / usability heuristics

There are many interaction design principles that help designers design great experiences. Nielsen Norman's [10 Usability Heuristics for User Interface Design](https://www.nngroup.com/articles/ten-usability-heuristics/) is a great place to start.  Here are some of the ways these principles apply to pip:

- Visibility of system status: ensure all commands result in clear feedback that is relevant to the user (but do not overload the user with too much information (see “Aesthetic and minimalist design”)
- Consistency and standards: when writing interfaces, strive for consistency with the rest of the Python packaging ecosystem, and (where possible) adopt familiar patterns from other CLI tools
- Aesthetic and minimalist design: remove noise from CLI output to ensure the user can find the most important information
- Help users recognize, diagnose, and recover from errors: cleary label and explain errors: what happened, why, and what the user can do to try and fix the error. Link to documentation where you need to provide a detailed explanation.
- Help and documentation: provide help in context and ensure that documentation is task-focussed


##### Additional Resources

- [Command Line Interface Guidelines](https://clig.dev)
- [10 design principles for delightful CLIs](https://blog.developer.atlassian.com/10-design-principles-for-delightful-clis/)


#### Design Tools

Tools that are frequently used in the design process are personas and guidelines, but also wireframing, prototyping, and testing, as well as creating flow diagrams or models.


##### Personas

_For a more in-depth overview of personas and using them in open source projects, this [resource from Simply Secure](https://simplysecure.org/blog/personas) may be helpful._

Personas are abstractions or archetypes of people who might use your tool. It often takes the form of a quick portrait including things like — name, age range, job title, enough to give you a sense of who this person is. You can capture this information into a [persona template](https://simplysecure.org/resources/persona-template-tech.pdf) and share them with your open source community as a resource see [examples from the Gitlab UX Team](https://about.gitlab.com/handbook/marketing/strategic-marketing/roles-personas/).

Personas are particularly useful to help ground a feature design in priorities for specific needs of specific users. This helps provide useful constraints into the design process, so that you can focus your work, and not try to make every feature a swiss army knife of solutions for every user.

In 2020, the pip UX team developed the following personas for the pip project:

- Python Software User
- Python Software Maker
- Python Package Maintainer

An in-depth write up on how the pip personas were created, and how they can be applied to future pip UX work can be [found here](https://docs.google.com/document/d/1730saWFkRUhKC_c0m92gfm3NLySDDtydBY9sDs9BMhk/edit?usp=sharing).


##### <a name="prototypes"></a>Prototyping

In any UX project, it is important to prototype and test interfaces with real users. This provides the team with a feedback loop, and ensures that the solution shipped to the end user meets their needs.

Prototyping CLIs can be a challenge. See [Creating rapid CLI prototypes with cli-output](https://www.ei8fdb.org/thoughts/2020/10/prototyping-command-line-interfaces-with-cli-output/ ) for recommendations.


##### Copywriting Style Guides

Given pip's interface is text, it is particularly important that clear and consistent language is used.

The following copywriting Style Guides may be useful to the pip team:

- [Warehouse (PyPI) copywriting styleguide and glossary of terms](https://warehouse.readthedocs.io/ui-principles.html#write-clearly-with-consistent-style-and-terminology)
- Firefox:
  - [Voice and Tone](https://meet.google.com/linkredirect?authuser=0&dest=https%3A%2F%2Fdesign.firefox.com%2Fphoton%2Fcopy%2Fvoice-and-tone.html)
  - [Writing for users](https://meet.google.com/linkredirect?authuser=0&dest=https%3A%2F%2Fdesign.firefox.com%2Fphoton%2Fcopy%2Fwriting-for-users.html)
- [Heroku CLI](https://devcenter.heroku.com/articles/cli-style-guide ) (very specific to Heroku's CLI tools)
- [Redhat Pattern Fly style guide](https://www.patternfly.org/v4/ux-writing/about)
- [Writing for UIs from Simply Secure](https://simplysecure.org/blog/writing-for-uis)


### General resources

- Heroku talk on design of their CLI tools ([video](https://www.youtube.com/watch?v=PHiDG-_XoRk) transcript)
- [Simply Secure: UX Starter Pack](https://simplysecure.org/ux-starter-pack/)
- [Simply Secure: Feedback Gathering Guide](https://simplysecure.org/blog/feedback-gathering-guide)
- [Simply Secure: Getting Quick Tool Feedback](https://simplysecure.org/blog/design-spot-tool-feedback)
- [Internews: UX Feedback Collection Guidebook](https://globaltech.internews.org/our-resources/ux-feedback-collection-guidebook)
- [Simply Secure: Knowledge Base](http://simplysecure.org/knowledge-base/)
- [Open Source Design](https://opensourcedesign.net/resources/)
- [Nielsen Norman Group](https://www.nngroup.com/articles/)
- [Interaction Design Foundation](https://www.interaction-design.org/literature)
