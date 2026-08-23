Feature: Earned authority — the constitution the agents cannot edit
  Capital is bought by calibration, never by claims. Deny by default.

  Scenario: An unknown agent is refused
    Given a fund with "iris" registered at standing cap 1000
    When "mallory" asks to spend 10
    Then the decision is refused with reason containing "not on the roster"

  Scenario: An unproven agent trades at a quarter of standing
    Given a fund with "iris" registered at standing cap 1000
    Then the earned cap of "iris" is 250

  Scenario: Sustained good calibration earns the full cap
    Given a fund with "iris" registered at standing cap 1000
    And "iris" has 10 resolved forecasts at p 0.9 that all resolved YES
    Then the earned cap of "iris" is 1000

  Scenario: Confident wrongness decays authority to the floor
    Given a fund with "iris" registered at standing cap 1000
    And "iris" has 10 resolved forecasts at p 0.9 that all resolved NO
    Then the earned cap of "iris" is 250

  Scenario: Hindsight is not a forecast
    Given a fund with "iris" registered at standing cap 1000
    And the question "manifold:q1" has resolved YES
    When "iris" forecasts "manifold:q1" at p 0.99
    Then the decision is refused with reason containing "hindsight"

  Scenario: A resolution never changes
    Given a fund with "iris" registered at standing cap 1000
    And the question "manifold:q1" has resolved YES
    Then resolving "manifold:q1" as NO raises an error

  Scenario: The kill switch outranks everyone
    Given a fund with "iris" registered at standing cap 1000
    And the kill switch is on
    When "iris" asks to spend 1
    Then the decision is refused with reason containing "kill switch"
