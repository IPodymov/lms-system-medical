---
name: refactoring
description: Principles and checklist for refactoring existing code (this repo is a Django monolith) safely — behavior-preserving structural cleanup, not feature work. Use before and during any refactor pass, whether scoped to one app or the whole project.
---

# Code Refactoring

Refactoring changes structure without changing behavior. The two must never be mixed in one step: if a change alters what the code does (fixes a bug, changes a response, adds validation), that's a fix or a feature, and it should be a separate, clearly-labeled change from the structural cleanup — even inside the same PR.

## Before starting

- **Establish a baseline.** Run the test suite, linter, and type checker before touching anything and note the result. If the suite is red or a linter already has findings, those are pre-existing and out of scope unless the user asked for them — don't let them silently blend into "refactor" changes.
- **Refactor toward an existing pattern, not a new one.** In a codebase with an established convention (e.g. this project's intent per `docs/ARCHITECTURE.md`: views stay thin, state changes go through services), converge inconsistent code onto that convention rather than inventing a third way. Check what the best-structured sibling module already does before designing the "ideal" shape from scratch.
- **Scope by seams, not by ambition.** Prefer a sequence of small, independently-verifiable changes (one app, one module, one duplicated pattern at a time) over one sweeping change that touches everything simultaneously — each seam should be testable on its own before moving to the next.

## What counts as a good refactor target

- **Duplicated logic** (the same query, the same validation, the same permission check) copy-pasted across two or more places. Extract to one function/service and call it from both. Rule of thumb: the third repetition is the one that justifies the abstraction — don't pre-abstract on the first or second occurrence of something that might not recur.
- **Fat entry points.** In Django specifically: a view function/method that builds querysets, branches on business rules, and mutates multiple models inline. Push the business logic into a service function or model method; the view's job is to parse the request, call one thing, and shape the response.
- **Long functions doing several unrelated things.** Split along responsibility boundaries the function already implicitly has (e.g. "validate input" / "compute" / "persist" / "notify"), not by mechanically chopping at a line count.
- **Leaky abstractions and inconsistent conventions** — some views class-based, others function-based, with no rule; some places using `get_object_or_404`, others a manual `try/except DoesNotExist`. Pick the convention the codebase already favors in most places and converge the minority.
- **N+1 queries and other performance smells surfaced by structural cleanup** — if extracting a query into a shared function is also the natural place to add `select_related`/`prefetch_related`, do it, but call it out explicitly since it's a behavior-adjacent (performance) change, not purely structural.
- **Dead code**: unused functions, commented-out blocks, flags that are always the same value. Delete rather than comment out — version control is the history, not the file.

## What is not a refactor (don't do these under this banner)

- Changing an API response shape, a URL, a template's visible output, or validation rules.
- Introducing a new abstraction layer "for future flexibility" that nothing in the current codebase needs yet (a factory, a plugin system, a generic base class with one subclass). Match the abstraction to what actually varies today.
- Renaming things purely for personal taste when the existing name is accurate and consistent with the rest of the codebase.
- Reformatting whitespace/import order across files a change didn't otherwise touch — that's the linter/formatter's job (`ruff format`/`ruff check --fix` here), and mixing it into a refactor diff obscures the real change.

## Django/Python specifics for this codebase

- Business logic belongs in a `services.py` (or model methods/managers), not in `views.py`. If an app's `views.py` is doing multi-step model mutation, that's the primary refactor signal — extract a function named for the business action (`publish_course(course, user)`), not for the HTTP verb.
- Prefer `get_object_or_404` / Django's built-in shortcuts over hand-written existence checks, for consistency with the rest of the app.
- Watch for queryset evaluation inside loops (`for x in qs: x.related.something`) — this is both a performance smell and usually a sign the view is doing work a queryset annotation or `select_related` should do instead.
- Keep migrations untouched by refactors — a structural code cleanup should not require a new migration; if it does, the change stopped being a pure refactor.
- Run `ruff check` and the relevant app's tests after every discrete refactor step, not just at the end — a regression is far cheaper to find one step back than after ten combined changes.

## Verification, every time

1. Run the full test suite (or at minimum the affected app's tests) after each discrete refactor step — not only at the very end.
2. Run the linter/formatter (`ruff check`, `ruff format`) — a refactor should never introduce new lint findings.
3. Diff the change and read it as a reviewer would: does anything here change behavior? If yes, either justify it explicitly to the user or revert that part.
4. Summarize what moved and why in terms of the resulting structure (e.g. "extracted duplicated enrollment-check logic from three views into `learning/services.py:can_enroll`"), not a line-by-line change log.
