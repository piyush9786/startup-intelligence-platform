# Founder Dashboard Motion and Hierarchy v1

This frontend polish milestone reorganizes the authenticated founder dashboard
around the order in which a founder should make decisions. It also introduces
restrained, accessible interface motion without changing any authoritative
backend decision.

## Information hierarchy

The dashboard now presents information in this order:

1. the persisted next best action;
2. readiness status and outstanding actions;
3. ranked scheme opportunities;
4. evidence-grounded guidance;
5. supporting requirements, funding, and planning tools.

The hero is a founder command center rather than a second discovery menu. It
uses the current persisted readiness action plan to name the next action and
routes the founder to the consolidated starting plan. When no action plan is
available, it routes to the startup assessment.

The navigation follows the same workflow:

```text
Dashboard
→ My startup
→ Startup assessment
→ Starting plan
→ Action roadmap
→ Schemes and supporting requirements
→ Founder advisor
```

## Motion implementation

The frontend uses the `motion` package and React entry points documented by
Motion:

```text
motion/react
motion/react-m
```

`LazyMotion` and the `domAnimation` feature bundle keep the main production
bundle below Vite's chunk-size warning threshold. Motion is used for:

- page and dashboard-section entry transitions;
- navigation selection feedback;
- next-action progress;
- metric, recommendation, and tool-card interaction;
- transient success, error, and generation notices.

The integration does not animate business values or imply state changes that
did not occur.

## Accessibility

`MotionConfig` uses `reducedMotion="user"`, so operating-system reduced-motion
preferences are respected. Existing semantic headings, buttons, navigation
landmarks, focus behavior, and accessible labels remain intact.

## Responsive behavior

The desktop layout uses:

- a persistent ordered navigation rail;
- a two-column command hero;
- a four-card progress overview;
- a decisions column and supporting-tools column.

Tablet and mobile layouts collapse the hero, metrics, decisions, and tools
into a single reading order. Navigation remains horizontally scrollable on
compact screens.

## Validation

The phase is covered by:

- a dashboard integration assertion for the persisted next action;
- the complete frontend test suite;
- the production Vite build;
- a live Vite transform/runtime smoke check.
