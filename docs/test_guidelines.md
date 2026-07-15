# Testing Guidelines for Service Teams

This document defines what each service team should provide so that its component can be integrated and tested reliably in the overall BiodivPipeline.

## 1. Service-Internal Tests

Each service team **SHOULD** implement tests for its own service logic.

This includes, where applicable:

- unit tests for core functions or business logic,
- tests for relevant edge cases and error handling,
- API or endpoint tests for REST-based services.

The concrete choice of test framework and the implementation details are left to the respective service team and should match the technology used by that service.

## 2. Test Materials Required for Pipeline Integration

To support integration into the overall pipeline testing setup, each service team **MUST** provide:

1. **A small valid test input file**
   - Representative of the service input
   - Small enough for automated test runs

2. **An expected output file or a clear expected output specification**
   - Provide an expected output file if the result is stable.
   - If the exact output may vary, describe what should be checked instead.

3. **A short input/output contract**
   - Input format
   - Output format
   - Required fields
   - Optional fields, if relevant
   - Error output, if applicable

4. **Information about unstable output fields**
   - For example: timestamps, generated IDs, runtime values, randomised content, or API metadata

5. **At least one successful test case**
   - Input that should be processed correctly
   - Expected result or expected output structure

6. **Preferably one edge case or failure case**
   - For example: invalid input, missing field, unresolved concept, or empty result

7. **A short example of how to run the service**
   - Command or minimal usage description needed to reproduce the test case

## 3. Test Data Requirements

Test data **MUST**:

- be small,
- be easy to understand,
- be representative of the real service input,
- avoid unnecessary large real-world datasets,
- be deterministic wherever possible.

## 4. Recommended Folder Structure

```text
tests/data/<service_name>/input/
tests/data/<service_name>/expected/
```

Example:

```text
tests/data/outlier_detection/input/sample_records.csv
tests/data/outlier_detection/expected/quality_report.json
```

## 5. Outputs That May Vary

If a service output depends on external APIs, changing databases, randomised behaviour, or other non-deterministic factors, the team **MUST** document:

- which parts of the output may change,
- which parts should still remain testable,
- how the service can be tested reproducibly as far as possible.
