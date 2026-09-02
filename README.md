# talmudic-harness (user plugin)

Hire this plugin for contested, irreversible, or overclaim-risky work:
architecture, security, privacy, deployment, data-loss, or a two-door plan
whose first path may be wrong. Skip status, facts, and one-line edits.

It is four deterministic primitives, not a reasoning engine, and it does not
spawn reviewers. Rabbinic terms are engineering metaphors, not authority
claims. Lives outside the Hermes core checkout so `hermes update` no longer
depends on carried local commits.

## Install

```sh
hermes plugins install Dannyzen/hermes-talmudic-harness --enable
```

## Install location

`~/.hermes/plugins/talmudic-harness/`

## Enable

In `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - talmudic-harness
  entries:
    talmudic-harness:
      allow_tool_override: false

talmudic_harness:
  enabled: true
  prompt_guidance: false  # opt in explicitly if you want guidance on every turn
  # ... existing amoraic / chavrusa / teaching_friend / eduyot ...

platform_toolsets:
  cli:
    - talmudic_harness
  whatsapp:
    - talmudic_harness
```

Restart the gateway after enabling: `systemctl --user restart hermes-gateway.service`

## Actions

Call the action that produces the artifact you need:

- `refine_question` — ranked Q_opt matrix when the next question is unclear
- `chavrusa_brief` — isolated proposer/challenger briefs when you will dispatch both leaves
- `teaching_friend_request` — plain-English skipped-step check
- `eduyot_entry` — append-only JSONL under `~/.hermes/talmudic_harness/` for rejected branches that may return

The plugin does not spawn agents. Current Hermes delegation inherits the
parent's tools and does not provide this plugin a safe internal way to enforce a
read-only child. Briefs are `executor: caller_managed`. If dispatch is skipped,
no review ran.

## Prompt guidance

Uses plugin `pre_llm_call` (ephemeral user context), not a core system-prompt patch.

Prompt guidance is disabled by default. Enabling the plugin keeps the
`talmudic_harness` tool available without injecting Talmudic instructions into
every turn. Set `talmudic_harness.prompt_guidance: true` only when you want
always-on guidance; otherwise invoke the tool explicitly for contested,
irreversible, or overclaim-risky work.
