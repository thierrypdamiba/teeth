Feature: The desk's self-patching surface — bounded freedom
  Agents may retune typed knobs for everyone and petition anything else.
  No agent-authored free text may enter another agent's prompt via config.

  Scenario: A config patch within bounds applies immediately
    When agent "vol-crusher" patches "config:tape_len" to 18
    Then the patch status contains "CONFIG CHANGED"
    And the desk config "tape_len" is 18

  Scenario: A config patch outside bounds is refused
    When agent "vol-crusher" patches "config:tape_len" to 999
    Then the patch status contains "outside bounds"

  Scenario: Only whitelisted knobs are mutable
    When agent "vol-crusher" patches "config:scoring_rule" to 1
    Then the patch status contains "not on the mutable surface"

  Scenario: Anything bigger becomes a public petition, not a change
    When agent "tape-reader" files a petition about "strike gap" proposing "disclose gap"
    Then the patch status contains "PETITION"
    And a petition file exists mentioning "strike gap"
