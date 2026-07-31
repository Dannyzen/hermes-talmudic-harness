# talmudic-harness (user plugin)

Moves the Talmudic AI harness out of the Hermes core checkout so
`hermes update` no longer depends on carried local commits.

The rabbinic terms are disciplined engineering metaphors for source grounding,
adversarial review, rejected-branch retention, and verification. They are not
claims of religious or halachic authority.

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

- `refine_question` — Amoraic Q_opt matrix
- `chavrusa_brief` — deterministic proposer/challenger briefs for caller-managed review
- `teaching_friend_request` — deterministic plain-English verifier request
- `eduyot_entry` — append-only JSONL under `~/.hermes/talmudic_harness/`

The plugin does not spawn agents itself. Current Hermes delegation inherits the
parent's tools and does not provide this plugin a safe internal way to enforce a
read-only child. The calling agent may use the returned briefs with an explicit,
restricted delegation tool when the task justifies the cost.

## Prompt guidance

Uses plugin `pre_llm_call` (ephemeral user context), not a core system-prompt patch.

Prompt guidance is disabled by default. Enabling the plugin keeps the
`talmudic_harness` tool available without injecting Talmudic instructions into
every turn. Set `talmudic_harness.prompt_guidance: true` only when you want
always-on guidance; otherwise invoke the tool explicitly for unusually hard,
high-stakes, or contested reasoning.
