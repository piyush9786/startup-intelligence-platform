# Functional Founder Support Dashboard v1

## Correction to the dashboard shell

The initial dashboard shell displayed persisted metrics but several navigation
items only scrolled within the overview page. Phase 4G.3A.1 converts those
controls into real user workflows.

## User journeys

The signed-in founder can now:

- open a dedicated startup profile and readiness page;
- browse active schemes as clickable cards;
- filter verified, funding, and loan schemes;
- open a complete scheme detail page;
- review structured eligibility rules;
- review required documents and explicit certification or registration evidence;
- review application steps and benefits;
- compare published funding amounts, interest ranges, and equity requirements;
- open official scheme sources and application links;
- review a dedicated action roadmap;
- open or generate evidence-grounded founder guidance;
- return from scheme detail to the originating workflow.

## Data boundaries

The implementation uses the existing `SchemeVersion` fields:

- support types and categories;
- minimum and maximum amounts;
- interest-rate ranges;
- equity requirement;
- application status and dates;
- official and application URLs;
- required documents;
- application steps;
- benefits and restrictions;
- structured eligibility rules;
- verification status.

The certification view does not invent a separate certification database. It
surfaces explicit certification, registration, licence, compliance, GST,
Udyam, DPIIT, incorporation, PAN, TAN, FSSAI, ISO, and MSME requirements that
already appear in current scheme documents or eligibility-rule evidence.

Funding and loan classification is derived from structured support types,
amount and interest fields, and explicit funding terminology in the current
scheme version.

## Not implemented in this phase

Meetings, mentor booking, appointments, events, notifications, and application
tracking do not yet have backend models or APIs. They are intentionally not
shown as fake working features.

## Testing

The frontend test suite covers:

- sign-in success and failure;
- real navigation from dashboard actions;
- scheme explorer rendering;
- requirements and certification evidence;
- funding and loan terms;
- scheme-detail navigation;
- official and application links;
- startup readiness;
- action roadmap;
- founder guidance;
- guidance generation;
- empty-profile handling;
- session expiry;
- scheme classification and formatting helpers.
