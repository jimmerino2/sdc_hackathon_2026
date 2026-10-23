# Project: The Coding Frontier
## A Gamified Coding Academy Powered by an Isometric Survival Game

Act as a senior product architect, game designer, learning-experience designer, UI/UX designer and full-stack engineer.

Your task is to help me design and build a gamified coding education platform inspired by Duolingo, Codédex and CodinGame, with an original isometric voxel/pixel-art survival game as its defining feature.

This is a foundational product concept, not an established specification. Think critically about the product before implementing it. Identify architectural risks, challenge weak assumptions, and prioritise a cohesive, working experience over an excessive number of features.

The long-term vision is ambitious. The initial implementation must be achievable and demonstrate why the product is different from an ordinary LMS.

---

# 1. Product vision

Build a coding education platform where learners acquire practical programming skills by progressing through an adventure.

The target learner is a **complete beginner with no assumed prior programming knowledge**.

The initial teaching language is Python, progressing from programming fundamentals to backend development using FastAPI, HTTP, REST APIs, request validation, state management and data persistence.

The core experience combines three connected environments:

1. **Academy:** learn programming through short, structured lessons and coding challenges.
2. **Frontier:** apply those skills to an interactive survival game whose mechanics depend on the backend code the learner writes.
3. **Workshop:** experiment with code, API requests, responses and game systems in a free-form development playground.

The central learning loop is:

**Learn → Write Code → Run Tests → See the Result in the World → Earn Rewards → Unlock the Next Mission.**

This loop is the foundation of the entire product.

The game must not merely be a visual reward after a coding exercise. The learner's implementation must determine whether the corresponding game action succeeds.

If the learner implements a mining endpoint incorrectly, mining should fail for a reason connected to the code. If the implementation passes the required tests, the simulated world should respond accordingly.

The product should make backend programming tangible, visual, interactive and enjoyable without sacrificing real learning.

## Reference products

Study the following products for their relevant mechanics and user experience:

- https://www.codedex.io/
  - Approachable coding lessons, small exercises, playful presentation, XP, achievements and learning progression.

- https://www.codingame.com/start/
  - Programming through game challenges, experimentation, measurable outcomes and progressively harder problems.
  - Use Mad Pod Racing as inspiration for gameplay-driven programming challenges, rather than copying its racing mechanics.

- Duolingo:
  - Guided progression, short learning sessions, visible milestones, motivation and consistent visual feedback.

These references should inform the design, not be copied. Create an original product identity, game world, characters, challenges, layouts and mechanics.

---

# 2. The three main experiences

Design the entire product around three connected experiences. They should feel like different aspects of one application rather than unrelated modules.

## A. Academy — Learn through coding missions

The Academy introduces concepts gradually and prepares learners to use them in the Frontier.

### Learning philosophy

Assume the learner has never written Python before.

Do not introduce complex FastAPI concepts before the learner understands the underlying programming concepts.

The curriculum should gradually progress through:

**Stage 1: Python foundations**
- Variables and data types.
- Strings, numbers and Boolean values.
- Operators and expressions.
- Conditional statements.
- Loops.
- Functions and parameters.
- Lists and dictionaries.
- Basic error handling.
- Reading error messages and debugging.
- Writing and understanding simple tests.

**Stage 2: Understanding web applications**
- What a client and server are.
- What happens when a user makes a request.
- HTTP methods and status codes.
- JSON and structured data.
- URLs, paths, query parameters and request bodies.
- What an API endpoint is.
- The purpose of a route handler.

**Stage 3: Backend development with FastAPI**
- Creating a FastAPI application.
- Writing GET and POST endpoints.
- Accessing request data.
- Returning JSON responses.
- Validating inputs using Pydantic models.
- Handling invalid requests and exceptions.
- Organising routes and reusable functions.
- Testing endpoints.
- Understanding state and data persistence.

**Stage 4: Practical backend engineering**
- Working with databases.
- CRUD operations.
- Relationships between entities.
- Authentication and authorisation.
- External API integration.
- Security, input validation and common backend mistakes.
- More advanced application architecture.

This is the long-term curriculum roadmap, not a requirement to implement every subject in the MVP.

Organise concepts into small, logical lessons with clear prerequisites.

### Lesson experience

Each lesson should contain:

1. A concise explanation in beginner-friendly language.
2. A concrete example.
3. A demonstration of how the concept works.
4. A coding exercise with starter code.
5. A runnable code editor.
6. Automated tests and readable feedback.
7. Progressive hints.
8. An explanation of why a solution works or fails.
9. A reward and a visible progression update.
10. A connection to an upcoming survival-game objective.

Keep explanations focused. Introduce unfamiliar terms before relying on them.

Avoid teaching Python through multiple-choice questions alone. Most core exercises should require learners to write, modify, run and reason about actual code.

Use worked examples and fill-in-the-code exercises during onboarding. Gradually transition to writing complete functions and API routes as the learner becomes more confident.

The interface should make it easy to retry a challenge without losing progress or feeling punished for making mistakes.

---

## B. Frontier — An isometric survival world controlled by code

This is the product's signature feature and should receive the greatest attention during MVP development.

Build an original isometric voxel/pixel-art survival environment with a clear sense of depth, exploration and progression.

It should resemble a small, polished indie survival adventure rather than a conventional coding dashboard with a game embedded inside it.

### Visual and gameplay direction

The world may contain:

- A player character.
- Terrain and explorable areas.
- Trees, rocks, ore deposits and natural resources.
- Mining and resource collection.
- Tools and crafting.
- A hotbar and inventory.
- Resource requirements and locked gates.
- Workstations and interactive objects.
- NPCs and quest-giving characters.
- Additional biomes and areas unlocked through progression.

Use an isometric perspective with layered scenery, tile-based world construction and expressive pixel-art or voxel-inspired assets.

For the initial release, implement a compact, carefully designed environment rather than a massive open world.

The game should be genuinely interactive. Player movement, object interaction, resource collection, inventory updates, animations and mission feedback should work.

However, **the learner should only need to write code for the technical systems currently being taught**. Do not make the beginner implement the rendering engine, movement controls or unrelated game infrastructure.

The host application should supply the game engine. The learner implements the challenge-specific backend behaviour.

### The defining mechanic: code enables game actions

Game actions must connect to actual learner-written Python/FastAPI code.

For example:

The player discovers a copper ore deposit. Interacting with it triggers a mining command.

The game sends a request to the learner's implemented endpoint, such as `POST /mine`.

The learner must implement the route and its business logic. Depending on the mission, the logic may need to validate the resource, check whether the player has the required tool, and determine whether mining is allowed.

The game then responds to the endpoint's actual result.

If the code is correct:
- The mining request succeeds.
- The game receives a successful response.
- The simulated resource is collected.
- Inventory and relevant game state update.
- An animation communicates the successful action.
- The learner receives appropriate progress credit or XP.

If the code is incorrect:
- The action fails for a meaningful reason.
- The resource is not incorrectly awarded.
- The learner can inspect the error, request and response.
- The companion offers a contextual hint.
- The learner can correct the implementation and retry.

Never award a successful game outcome simply because the learner clicked a button or submitted any code.

### Game architecture

Separate the game engine from learner-authored application logic.

The game engine should manage:
- World rendering.
- Player movement.
- Input handling.
- Animations.
- Object interactions.
- Visual inventory updates.
- Game UI and effects.

The challenge execution layer should manage:
- Learner-submitted code.
- API request handling.
- Validation and challenge tests.
- Route execution.
- Challenge-specific game rules.
- Execution results and diagnostic information.

Use a controlled interface between the two.

Learner code should determine whether the assigned action is valid. A trusted host-side game-state adapter should validate the returned result and apply permitted state changes.

Do not give arbitrary learner code direct access to the host game's internal objects, database, filesystem or process.

Design an extensible game-command system so that additional mechanics can be added as new missions are introduced.

Potential commands for future missions include:
- `mine`
- `inspect_inventory`
- `craft_item`
- `open_gate`
- `interact_with_npc`
- `save_progress`

These names are illustrative. Establish a consistent command and endpoint convention during architecture design.

Do not build every command in the initial release.

---

## C. Workshop — A backend experimentation playground

The Workshop lets learners explore what they have learned without needing to follow a mission at every step.

It should feel like a beginner-friendly development laboratory.

### Core capabilities

Include:

- A code editor.
- A route or endpoint list.
- A request method selector.
- An editable request path.
- Query parameters and request headers.
- A JSON request-body editor.
- A Run Request action.
- HTTP status-code display.
- JSON response inspection.
- An error and diagnostic panel.
- Request and response history.
- A reset or restore-example action.
- A way to trigger supported game actions.
- A visible connection between endpoint execution and relevant game-state changes.

The Workshop should explain the relationship between an HTTP request, a route handler, its response and the effect on the simulated world.

For example, a learner can inspect a mining endpoint, send it a request and then compare its response with what happens when they mine the same resource inside the Frontier.

The Workshop should reuse the same challenge definitions and execution pathway wherever practical. Avoid maintaining separate implementations of the same game rules for the Academy, Frontier and Workshop.

Do not turn this into a full professional IDE. The goal is to make experimentation approachable.

---

# 3. Roadmap, quests and progression

The learner should experience the curriculum as a journey through an explorable world.

Avoid presenting the entire curriculum as a plain list of course modules.

### World structure

Use a hierarchy such as:

World → Chapter → Mission → Lesson and Coding Challenge.

Each world introduces a group of related technical skills. Each chapter builds toward a practical outcome, and each mission unlocks new learning opportunities.

For example:

**World 1: The First Expedition**
- Discover the world.
- Learn basic Python values and conditions.
- Understand functions and simple data structures.
- Meet the companion.
- Complete a first guided coding task.
- Unlock the first interactive resource.

**World 2: The Lost Signal**
- Understand client/server communication.
- Learn HTTP, JSON and request/response behaviour.
- Build a small FastAPI endpoint.
- Test it using the Workshop.
- Unlock more interactions.

**World 3: The Resource Frontier**
- Validate mining requests.
- Check requirements and game conditions.
- Return appropriate responses.
- Connect route results to inventory.
- Unlock additional crafting mechanics.

These are illustrative progression themes. Refine them to ensure the prerequisites are pedagogically sound.

### Mission specification

Every mission should have a structured definition containing:

- Unique identifier and title.
- Narrative introduction.
- Learning objective.
- Prerequisite concepts.
- Explanation and examples.
- Starter code.
- Coding task and expected behaviour.
- Automated tests.
- Progressive hints.
- Feedback for common errors.
- XP and achievement conditions.
- Unlock rules.
- Relevant game interaction.
- Completion state.

Prefer data-driven lesson definitions over hardcoding every mission into a separate page.

The system should be capable of adding future missions through lesson content, starter code, tests, reward definitions and supported game-command configuration.

### Progression mechanics

Include coherent systems for:

- Player XP and levels.
- Lesson completion.
- Chapter and world completion.
- Locked, available, active and completed missions.
- Prerequisite-based unlocking.
- Skill mastery and revision.
- Achievements and badges.
- Optional challenges.
- Daily learning objectives.
- Progress summaries.
- Streaks as a later or optional feature.

The roadmap should clearly communicate what the learner has completed, what they can do now and what they will unlock next.

Reward correct understanding and meaningful effort. Do not encourage mindless repetition or excessive grinding.

Do not implement complicated competitive ranking, multiplayer or elaborate economy systems in the MVP.

---

# 4. Companion avatar and scripted coaching

Give the learner a companion character who accompanies them through the Academy and Frontier.

The companion should have a recognisable personality and react to the learner's actions. It should not behave like a static tutorial bubble.

### Personality

Make the companion:

- Playful and witty.
- Slightly sarcastic.
- Encouraging when the learner struggles.
- Proud of meaningful improvements.
- Curious about the world.
- Capable of lighthearted teasing.
- Helpful rather than condescending.

Allow roasting to be lighthearted, with intensity kept appropriate for an educational product. Never attack the learner's intelligence, personal traits or worth.

### Contextual reactions

The companion should react to events such as:

- Entering a new world.
- Starting a mission.
- Making a mistake.
- Failing a test.
- Repeatedly encountering the same error.
- Discovering a useful debugging insight.
- Completing a challenge.
- Unlocking a world or achievement.
- Exploring a new object.
- Asking for a hint.

Example dialogue:

**Successful implementation**

"Look at you, validating inputs before changing the game state. Character development!"

**Repeated failure**

"That endpoint has failed three times. Maybe we should investigate the evidence before creating a fourth crime scene."

**Contextual hint**

"The request reached your route. Now check what your function actually does with the request body."

**Achievement unlocked**

"A working endpoint and a new badge. You're starting to look employable."

These examples demonstrate the intended personality. Create original dialogue suited to the actual context.

### MVP implementation

Use a scripted, event-driven dialogue system. Do not require an external LLM or paid API.

Create dialogue categories and selection rules based on:
- Mission events.
- Test results.
- Error categories.
- Progress milestones.
- Repeated attempts.
- Newly unlocked skills.

Where relevant, map feedback to specific test failures or error types instead of displaying generic dialogue.

Prevent repetitive dialogue from becoming annoying. Use multiple suitable lines, cooldowns or simple selection rules.

The companion should support optional hints and explanations without immediately revealing the complete answer.

Design the dialogue system so an AI-powered coach can be added later without rewriting the application's event and coaching architecture.

---

# 5. Visual design system

Use the following required colour palette.

| Role | Colour |
|---|---|
| Primary | `#FFC107` |
| Secondary | `#FF9800` |
| Dark background | `#1E1E1E` |
| Warm light background | `#FFFDF5` |
| White | `#FFFFFF` |

### Art direction

The product should combine:

- A charming, handcrafted adventure-game world.
- Isometric pixel-art or voxel-inspired environments.
- Warm lighting and environmental depth.
- Expressive character animations.
- Golden-yellow and orange accents for interaction, progression and rewards.
- Dark developer panels for code and debugging.
- Warm cream surfaces for lessons and readable educational content.
- Clear, consistent icons and meaningful visual feedback.

Use colour purposefully. The primary and secondary colours should highlight important actions and state changes rather than overwhelm every screen.

### UI principles

- Make the product feel like a coherent game and learning platform.
- Do not use a generic SaaS dashboard as the main visual identity.
- Avoid excessive cards, borders and disconnected panels.
- Maintain readable typography and strong contrast.
- Make the code editor comfortable for extended use.
- Clearly distinguish successful, failed, locked, active and completed states.
- Use transitions and animations where they improve feedback.
- Avoid decorative animations that interfere with typing, scrolling or navigation.
- Respect reduced-motion preferences.
- Ensure the interface remains usable on smaller screens.

Desktop should be the primary experience because the learner needs a code editor and a playable environment. Provide sensible responsive layouts, but do not compromise the core desktop workflow for incomplete mobile gameplay.

Create original visual assets or use properly licensed assets. Do not copy proprietary characters, logos or assets from Minecraft or the reference platforms.

---

# 6. Technical stack and architecture

First inspect the existing repository. Read its documentation and project instructions, identify its framework and dependencies, and determine what is already functional.

Preserve useful existing work. Do not replace an established project structure without a concrete reason.

If the repository is empty, evaluate the following starting architecture.

### Web application

- Next.js and React for the main application.
- TypeScript for the frontend.
- Tailwind CSS or an appropriate existing styling system.
- Reusable components and a consistent design system.
- A browser-based coding editor with Python syntax highlighting and suitable beginner-friendly behaviour.

### Game

Evaluate Phaser 3 or another suitable lightweight rendering framework for an isometric, tile-based environment.

Prioritise:
- Smooth interaction.
- Reliable input handling.
- Clear rendering.
- Responsive sizing.
- Simple scene and entity management.
- Integration with the surrounding React application.

Use the framework that best supports the intended MVP without introducing unnecessary complexity.

### Backend and learning runtime

Use Python and FastAPI for the platform's backend API where appropriate.

Keep the following concerns separate:
- The trusted platform backend.
- The learner's submitted Python/FastAPI application.
- The isolated challenge runner.
- The game client and trusted simulation state.
- Lesson definitions and evaluation tests.

The learner's FastAPI application must be independently executable and testable. Do not merely imitate an endpoint by returning canned JSON from the frontend.

### Data and persistence

Choose a simple persistence solution suitable for a local prototype.

Store the meaningful state needed to resume a session, including:
- Completed lessons.
- XP and player level.
- Achievement status.
- Unlocked missions.
- Relevant game progress.
- Inventory and resource state where appropriate.

Keep storage behind a clear interface so local storage or a lightweight local database can be replaced with more durable server-side persistence later.

Do not make authentication, account management or cloud deployment prerequisites for proving the MVP.

---

# 7. Critical requirement: safe learner-code execution

The learner must be able to submit real executable Python code. That code must run separately from the trusted platform.

Never execute arbitrary learner source code through an unsafe `eval` implementation or directly inside the main web server process.

For the local prototype, prefer a Docker-based isolated code runner or another clearly justified approach that provides meaningful process and resource isolation.

Investigate the environment's available tooling before choosing the implementation.

### Execution requirements

The runner should, where supported:

- Execute learner code as a non-root user.
- Apply a strict execution timeout.
- Apply memory, CPU and process limits.
- Disable unnecessary network access.
- Prevent access to application secrets and sensitive host files.
- Avoid privileged containers.
- Use appropriate filesystem restrictions.
- Avoid giving learner code access to the Docker socket.
- Clean up temporary execution environments.
- Limit submitted code and output sizes.
- Return a structured execution result rather than allowing arbitrary process output to control the application.

Do not expose a local prototype's arbitrary-code execution service to the public internet.

### End-to-end challenge execution

Implement a real pathway:

1. The learner edits Python code.
2. The submission is sent to the trusted platform backend.
3. The runner starts an isolated execution environment.
4. The submitted FastAPI application and evaluation harness run in that environment.
5. Automated tests exercise the actual submitted implementation.
6. Execution results, test failures and relevant HTTP information return to the platform.
7. A game action invokes the same challenge-specific execution pathway.
8. The trusted simulator validates the returned result and applies only permitted game-state changes.
9. The interface displays the outcome and relevant feedback.

For the MVP, a controlled harness using FastAPI's test client can execute genuine HTTP requests against the learner's application inside the isolated environment without exposing the learner's application as a public network service.

Provide a predictable contract between the runner and the game. A returned success flag alone must not allow arbitrary inventory values, resource duplication or unrestricted changes to the host application.

The mining route should determine the mission-specific result. The trusted simulation should validate the output and apply the corresponding game effect.

The Workshop and Frontier must use the same learner implementation and challenge execution path wherever appropriate.

### Local development fallback

If Docker or the preferred isolation mechanism is unavailable:

- Explain the exact missing dependency.
- Do not claim the fallback safely executes arbitrary code.
- Keep the execution interface clean and implementable.
- Provide a clearly labelled demonstration mode only if necessary to preview the UI.
- Never present hardcoded output as proof that the learner's actual implementation passed.

Document how to run the real runner locally.

The core educational mechanic should be designed around actual code execution, not postponed behind a mock API.

---

# 8. MVP: The First Expedition

The first release should demonstrate the product through one complete, playable learning experience.

Do not implement the entire long-term platform at once.

Build a compact vertical slice called **The First Expedition**.

### Required functionality

**1. Entry and onboarding**
- A welcoming entry screen.
- A short introduction to the world and companion.
- A simple local learner profile.
- A brief indication of how learning, coding and gameplay connect.

**2. Academy**
- A roadmap with a handful of mission nodes.
- A small set of introductory lessons.
- Beginner-friendly explanations of essential Python and HTTP concepts.
- An interactive Python editor with starter code.
- Run and submit controls.
- Actual automated tests.
- Clear error output, hints and completion feedback.

**3. Frontier**
- One small but genuinely playable isometric pixel-art/voxel-inspired world.
- Basic character movement and interaction.
- At least one copper ore deposit.
- An inventory and visible collected-resource counter.
- A mining interaction that sends a request to the learner's actual FastAPI implementation.
- Visual feedback for success and failure.

**4. Learner implementation**
- A guided task to implement the mining endpoint.
- Tests that exercise the submitted code.
- Validation of the required mining behaviour.
- Meaningful failures for invalid or incomplete implementations.
- A retry workflow.
- No hardcoded success that ignores the learner's code.

**5. Workshop**
- A basic request inspector.
- A method and route selector.
- JSON request-body editing.
- Execution of the relevant learner implementation.
- HTTP response and error inspection.
- A small request history or execution log.

**6. Gamification**
- XP and a visible progress indicator.
- One meaningful achievement.
- A mission-completion animation or equivalent feedback.
- A visible unlock for the next mission.
- Persistent progress across a page reload.

**7. Companion**
- Scripted dialogue.
- Context-aware hints for the mining mission.
- Reactions to success and failure.
- Dialogue that uses real execution and test information.

**8. Integration**
- All three experiences must work together.
- The code tested in the Academy should be the code exercised by the Frontier and Workshop.
- Successful actions should create consistent, traceable state changes.
- Progress and rewards should not be awarded twice through repeated requests unless the reward rules explicitly permit it.

The resulting MVP should feel like a small but complete product rather than a disconnected set of screens.

If a requested feature proves too large for the MVP, prioritise the defining learning loop and explain the deferral. Do not silently replace an important working feature with a placeholder.

---

# 9. Product acceptance criteria

The MVP is not complete simply because the UI looks convincing.

Verify the actual learner journey.

### Learning
- A complete beginner can understand what the first lesson asks them to do.
- The lesson explains the concepts necessary for the task.
- The learner can edit and execute Python code.
- Incorrect implementations fail meaningful tests.
- Correct implementations pass the same tests reliably.
- Errors are understandable and actionable.

### Game integration
- The player can move around the small world.
- The mining object can be interacted with.
- The resulting action exercises the learner's real route.
- Incorrect implementation produces a failed or rejected game action.
- Correct implementation produces the expected response and game effect.
- The inventory and world state remain consistent.
- Repeated or malformed requests cannot duplicate rewards or bypass the mission rules.

### Workshop
- The learner can inspect and execute a supported request.
- Actual response status and content are displayed.
- The request history reflects real executions.
- Game actions and Workshop requests use a consistent implementation.

### Progression
- Successful completion awards the appropriate XP.
- The achievement unlocks at the correct time.
- The next mission becomes available.
- Reloading preserves meaningful progress.
- Rewards cannot be duplicated through simple replay or repeated submissions.

### Engineering
- The isolated runner is demonstrably separate from the trusted platform.
- Execution timeouts and failure cases are handled.
- Tests do not depend on a specific successful hardcoded solution.
- Major controls are functional.
- The app can be started through documented commands.
- Important changes are verified with appropriate tests and development checks.

---

# 10. Implementation workflow

Follow these phases in order.

## Phase 0 — Inspect and establish the product

Before substantial code changes:

1. Inspect the repository and project instructions.
2. Identify existing code, framework, dependencies and conventions.
3. Summarise the proposed user experience and core gameplay loop.
4. Propose the frontend, game and Python execution architecture.
5. Explain how learner-written FastAPI code will be executed and tested.
6. Identify the security assumptions and local dependencies.
7. Define the first mission, its starter code, tests, request/response contract and game-state changes.
8. Establish a realistic implementation plan and acceptance criteria.

The primary product decisions are already established:

- Target learner: complete beginner.
- Teaching language: Python with FastAPI.
- Game style: isometric voxel/pixel-art survival.
- Code execution: local prototype with an isolated runner.
- Companion: scripted contextual coach.
- Main experiences: Academy, Frontier and Workshop.
- Colour palette: `#FFC107`, `#FF9800`, `#1E1E1E`, `#FFFDF5` and `#FFFFFF`.

Do not ask me to decide these again.

Ask up to three additional questions only if a material implementation decision cannot be responsibly resolved through repository inspection and a sensible recommendation. For each question, provide a recommended default.

Record the agreed design in suitable project documentation, such as:
- `docs/product-brief.md`
- `docs/architecture.md`
- `docs/learning-curriculum.md`
- `docs/mvp-plan.md`

Adapt filenames and structure to the existing repository.

After presenting Phase 0 findings and any essential questions, pause before major implementation so the product direction can be reviewed. If I explicitly instruct you to proceed using your recommendations, continue without repeating questions already answered.

## Phase 1 — Build the vertical slice

Implement the foundational UI, lesson content, code runner, isometric environment, mining interaction, test feedback, progression and Workshop.

Integrate them incrementally. Validate the connection between learner code and game behaviour early rather than leaving integration until the end.

Do not build a complete game world before proving the central code-execution mechanic.

## Phase 2 — Test the end-to-end experience

Run the relevant tests and verify the full journey from the first lesson to successful mining, rewards and mission unlock.

Fix important integration defects and document any remaining limitations.

## Phase 3 — Refine the product

Improve:
- Visual polish.
- Game responsiveness and feedback.
- Lesson clarity.
- Avatar dialogue.
- Error explanations.
- Accessibility.
- Persistence.
- Developer experience.

Only after the vertical slice works should you expand the curriculum or add more gameplay systems.

---

# 11. Final development principles

Throughout the project:

- Prioritise a working end-to-end experience over feature quantity.
- Treat teaching quality as a first-class product requirement.
- Design for complete beginners without making the product feel childish.
- Let learner-written code control meaningful game outcomes.
- Keep the Academy, Frontier and Workshop connected to the same relevant state and execution pathway.
- Prefer reusable mission definitions, tests and game-command interfaces.
- Keep the architecture extensible but proportionate to the MVP.
- Avoid premature multiplayer, billing, complex social features, production account management and large-world systems.
- Do not add dependencies without a clear purpose.
- Do not leave major buttons, routes or gameplay controls nonfunctional.
- Never describe simulated execution as real code execution.
- Never claim that code is securely sandboxed without an implemented isolation boundary.
- Test important functionality after implementation and refactoring.
- Communicate actual limitations clearly rather than hiding them behind polished UI.

The long-term ambition is a coding adventure that can grow from basic Python to substantial backend engineering.

However, the immediate objective is deliberately narrow:

**Make a beginner understand a programming concept, implement a real FastAPI endpoint, use it to mine copper in a playable world, inspect the request and response, and earn a reward that unlocks the next mission.**

That single experience must prove the product's fundamental idea.

Begin with Phase 0.