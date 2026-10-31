# Jobee Enhancement: AI Fluency & AI-Assisted Learning

## Context

Jobee is a career guidance platform for students and early-career technology professionals. It helps users understand how AI is changing the technology job market, discover suitable career paths, identify skill gaps and follow learning roadmaps.

We currently provide traditional technical learning roadmaps covering skills such as Python, Java, SQL, machine learning and other conventional technical competencies.

However, we recognise an important gap: traditional technical skills alone do not adequately prepare someone for the changing AI-driven workplace.

We want to introduce **AI Fluency** as a complementary learning capability.

The objective is to teach users how to effectively utilise AI tools in their professional work, including:

- Prompt engineering and effective prompting.
- Context engineering.
- AI-assisted software development.
- AI-assisted research and data analysis.
- AI tools, integrations, connectors and agents.
- Verification, critical thinking, privacy and responsible AI usage.

This should complement traditional technical skills rather than replace them.

## IMPORTANT: Scope and implementation philosophy

This is an incremental enhancement, NOT a redesign of Jobee.

Preserve the existing architecture, UI design language, navigation, features and functionality.

Prioritise a working, polished implementation over unnecessary abstractions.

Specific constraints:

1. Use hardcoded, curated educational content for the initial implementation.
2. Do not introduce a new AI API or LLM dependency for generating lessons.
3. Do not introduce a new backend, database schema or external CMS.
4. Reuse existing components, styling, state management and persistence mechanisms.
5. Do not create an entirely separate learning management system.
6. Do not change the existing career matching algorithm, forecast models or traditional roadmaps.
7. Do not alter existing challenge scoring, passing thresholds, rewards or gameplay.
8. Make the new educational features optional.
9. Ensure everything works on desktop and mobile.

First inspect the repository to understand the current architecture, routing, Learn page, Challenges page, existing UI components and persistence approach. Follow existing conventions rather than introducing a new architecture.

---

# Feature 1: AI Fluency Learning Section

Add an optional AI Fluency section inside the existing Learn page.

Do not create a new sidebar destination unless the existing architecture makes that absolutely necessary.

The existing traditional roadmap must remain unchanged and fully functional.

Users should be able to access AI Fluency lessons independently of their traditional learning roadmap.

### Initial curriculum

Create the following five hardcoded lessons.

### Lesson 1: Prompting Fundamentals

Objective: Teach users to formulate effective AI instructions.

Topics:
- Defining a clear task or objective.
- Providing relevant context.
- Specifying constraints and requirements.
- Defining the expected output format.
- Providing examples when useful.
- Iterating and improving prompts.

Introduce a practical prompt-building framework:

1. Goal: What do you want the AI to accomplish?
2. Context: What background information does it need?
3. Inputs: What information or materials should it work with?
4. Constraints: What limitations or rules must it follow?
5. Output: What format or deliverable do you expect?
6. Verification: How should the result be checked?

Explain that this is a useful checklist, not a universal mandatory prompt formula.

Include:
- Poor prompt example.
- Improved prompt example.
- Explanation of why the improved prompt works.
- A reusable prompt template.
- A short exercise.

### Lesson 2: Context Engineering

Objective: Teach users that providing the right context can be more important than simply writing longer prompts.

Topics:
- Providing relevant files and documents.
- Supplying code snippets and error messages.
- Giving the AI project architecture and technical constraints.
- Maintaining relevant conversation context.
- Breaking complex tasks into smaller steps.
- Iteratively supplying missing information.

Include practical examples for software developers.

For example, demonstrate the difference between:

"Fix my code."

And:

"Here is the relevant Python function, its expected behaviour, the actual error and the dependencies being used. Identify the likely root cause before proposing a minimal fix. Explain any assumptions."

Teach users to provide relevant information instead of indiscriminately dumping entire repositories or large amounts of irrelevant context.

### Lesson 3: AI-Assisted Software Development

Objective: Teach users to work effectively with AI coding assistants.

Topics:
- Understanding unfamiliar codebases.
- Generating code with clear requirements.
- Debugging with contextual error information.
- Refactoring existing implementations.
- Generating unit tests and edge cases.
- Code review and security checks.
- Incremental development instead of accepting large unverified changes.

Introduce a recommended workflow:

1. Understand the task.
2. Ask AI to propose an implementation plan.
3. Review the proposed approach.
4. Implement incrementally.
5. Generate and run tests.
6. Review the generated changes.
7. Verify that the implementation actually meets requirements.

Include at least one realistic development scenario and an example prompt.

### Lesson 4: AI Tools, Integrations and Workflows

Objective: Help users understand how to select and combine AI capabilities.

Topics:
- General-purpose AI assistants.
- Web search and research capabilities.
- File and document analysis.
- Code execution and data analysis.
- Image, audio and multimodal capabilities.
- AI coding assistants.
- Connectors and external integrations.
- MCP (Model Context Protocol) at an introductory level.
- AI agents and workflow automation.

Explain when each capability is useful.

Include practical scenarios illustrating how multiple AI capabilities can work together.

Do not make the curriculum dependent on one provider or specific paid subscription.

Avoid outdated terminology or claiming that one product's feature is universally available across other AI platforms.

### Lesson 5: Verification and Responsible AI

Objective: Teach users to remain accountable for AI-assisted work.

Topics:
- Hallucinations and fabricated information.
- Fact-checking with reliable sources.
- Reviewing AI-generated code.
- Testing generated solutions.
- Identifying bias and unsupported assumptions.
- Protecting confidential information and credentials.
- Understanding copyright and responsible usage.
- Knowing when human judgement is necessary.

Include practical examples of how AI-generated work can appear convincing while being incorrect.

---

# Feature 2: Reusable AI Learning Content Structure

Create a central, hardcoded content collection rather than scattering lesson text across page components.

Use the existing project's preferred file and data conventions.

Each lesson should support:

- Unique ID.
- Title.
- Short description.
- Category.
- Difficulty level.
- Estimated completion time.
- Learning objectives.
- Main educational content.
- Examples.
- Prompt templates.
- Practical exercise.
- Verification checklist.
- Further reading links.
- Applicable technology roles or skill tags.

Structure the content so that more lessons can be added later without changing the overall component architecture.

Keep the content human-readable and easy to maintain.

Where external material inspires or informs a lesson, include the original source link and, where relevant, licence attribution.

Do not scrape and republish entire third-party courses.

---

# Feature 3: Contextual AI Tips in Challenges

This is one of the most important integrations.

Existing Jobee Challenges contain two-stage projects in GitHub repositories, which are scored by an LLM against an existing rubric.

Introduce an optional, expandable section titled:

"AI Assist" or "AI Workshop"

This section should appear within an existing challenge interface without disrupting the current challenge workflow.

Its purpose is to teach users how they can leverage AI while completing the challenge.

### Required capabilities

1. Display contextual tips relevant to the challenge.
2. Provide useful prompt templates.
3. Allow users to copy prompts to their clipboard.
4. Explain why the prompt is effective.
5. Include a checklist for verifying AI-generated results.
6. Link to relevant AI Fluency lessons.

Where possible, associate tips with the challenge's programming language, topic, difficulty and applicable role.

Examples:

**Debugging tip**

Explain how to give AI the error message, relevant source code, expected behaviour and environment details.

**Code generation tip**

Explain how to describe requirements, constraints, existing architecture and expected tests before requesting an implementation.

**Testing tip**

Explain how to ask AI to identify edge cases, generate unit tests and assess missing coverage.

**Code review tip**

Explain how to ask AI to identify security, performance and maintainability concerns without blindly accepting every suggestion.

### Challenge reflection

After completing a challenge, optionally provide a short AI collaboration reflection:

- What did you use AI for?
- What did you independently verify?
- What suggestions did you change or reject?

This reflection is educational only.

IMPORTANT:
- Do not change the existing challenge scoring rubric.
- Do not change the existing passing threshold of 85.
- Do not alter existing stinger rewards or Hive mechanics.
- Do not make AI usage compulsory.
- Do not penalise users for choosing to complete a challenge without AI assistance.

---

# Feature 4: Role-Specific AI Guidance

Use Jobee's existing eight technology roles to associate relevant AI skills and recommendations.

Examples:

**Software Engineer**
- AI-assisted development.
- Debugging and code review.
- Test generation.
- Repository context management.
- Agentic coding workflows.

**Data Scientist**
- AI-assisted exploratory data analysis.
- Hypothesis generation.
- Data cleaning.
- Statistical verification.
- Model evaluation.

**AI Engineer**
- Prompt engineering.
- Context engineering.
- RAG.
- AI evaluation.
- Tool calling and agent workflows.

Apply similar mappings to other existing roles.

These should be static educational recommendations, not another AI-powered matching algorithm.

Do not change role match scores or their weights.

---

# Feature 5: UI and User Experience

Maintain Jobee's existing visual identity, mascot, colour palette, layout and interaction patterns.

The new features should feel like a natural extension of Jobee rather than a separate application.

For the AI Fluency section:

- Show available lessons as compact cards.
- Display estimated duration and difficulty.
- Provide clear lesson progression.
- Use a readable lesson detail view.
- Include practical before-and-after prompt examples.
- Make prompt templates easily copyable.
- Show lesson completion status.
- Ensure responsive layouts.

For Challenge AI Tips:

- Prefer expandable cards, contextual panels or dialogs.
- Do not automatically bombard users with popups.
- Make it easy to dismiss and reopen tips.
- Keep the challenge itself as the primary focus.

Reuse existing UI components wherever possible.

Do not add a new UI library unless there is a genuine technical reason.

---

# Feature 6: Progress Tracking

Support optional lesson completion tracking.

Use the existing persistence mechanism if suitable.

Do not create a new database or backend integration solely for this feature.

If the current architecture does not provide a suitable persistence mechanism, implement a lightweight local solution consistent with existing project conventions.

AI Fluency completion must remain independent of traditional roadmap progress.

Do not modify existing career progress, challenge rewards or leaderboard calculations.

---

# Educational Content Quality Requirements

This is particularly important.

Do not fill lessons with generic statements such as "AI can improve productivity" or "Write better prompts."

Every lesson should teach a specific, actionable competency.

Use this educational pattern:

1. Concept: What is being taught?
2. Why it matters: When and why should someone use it?
3. Demonstration: Show a practical example.
4. Application: Give the learner a small exercise.
5. Verification: Explain how to determine whether the result is correct.
6. Further reading: Provide relevant reputable resources.

Prefer technology workplace scenarios over generic consumer examples.

Prioritise transferable AI skills over individual product-specific features.

Use reputable references such as:

- UNESCO AI Competency Framework for Students:
  https://www.unesco.org/en/articles/ai-competency-framework-students

- Microsoft Generative AI for Beginners:
  https://github.com/microsoft/generative-ai-for-beginners

- DAIR.AI Prompt Engineering Guide:
  https://www.promptingguide.ai/

- OpenAI Prompt Engineering:
  https://developers.openai.com/api/docs/guides/prompt-engineering

- Anthropic Prompt Engineering:
  https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview

- Google Gemini Prompting Strategies:
  https://ai.google.dev/gemini-api/docs/prompting-strategies

- VS Code AI Agent Best Practices:
  https://code.visualstudio.com/docs/agents/best-practices

External documentation may change, so use it as a reference rather than assuming that every technique is permanently valid.

---

# Explicitly Out of Scope

Do not implement the following in this iteration:

- AI chatbot or AI tutor.
- Automatically generated educational content.
- AI-powered prompt evaluation.
- External LMS integration.
- Third-party course hosting.
- New backend or database.
- New subscription or monetisation features.
- New career matching models.
- Changes to forecasting models.
- Changes to existing traditional learning roadmaps.
- Changes to the Challenges grading and rewards system.

These can be considered in a later iteration.

---

# Acceptance Criteria

The implementation is complete when:

1. The existing Learn page still works and displays the original roadmap.
2. Users can access an optional AI Fluency learning section.
3. All five initial lessons have meaningful and actionable educational content.
4. Lessons include examples, exercises and verification guidance.
5. Users can access relevant AI Tips while completing Challenges.
6. Prompt templates can be copied successfully.
7. Relevant tips are associated with appropriate existing roles and challenges.
8. Lesson completion is tracked without disrupting existing progress.
9. The UI is responsive and consistent with Jobee.
10. No existing career matching, forecasts, roadmaps, challenge grading, rewards or social functionality is broken.

## Implementation approach

Before coding, inspect the current repository and identify the smallest set of files and components required.

Implement the working end-to-end feature using existing conventions.

After implementation:

- Run the relevant type checks, linting and tests.
- Fix any regressions introduced by the changes.
- Check that existing pages still behave correctly.
- Summarise the files changed and the features implemented.
- Identify any elements you could not complete.

**Final priority: Build a useful, working AI Fluency learning experience without turning this incremental enhancement into a major architectural rewrite of Jobee.**