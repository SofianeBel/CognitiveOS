---
name: test-fix
description: Run tests and automatically fix any failures encountered
argument-hint: "[optional: specific test file or pattern]"
---

# Test and Fix

Run the test suite and automatically fix any failures encountered. This command iterates until all tests pass or a maximum number of fix attempts is reached.

## Workflow

### Step 1: Initial Test Run

Run the tests to identify any failures:

```bash
pytest tests/ -v --tb=short $ARGUMENTS
```

If a specific test file or pattern is provided in `$ARGUMENTS`, run only those tests.

### Step 2: Analyze Failures

If tests fail:
1. Read the full error output carefully
2. Identify the root cause of each failure:
   - Import errors
   - Missing dependencies
   - Logic errors in test or source code
   - Mock/fixture issues
   - Environment configuration problems

### Step 3: Fix Failures Iteratively

For each failure:

1. **Import/Module errors**:
   - Check if the import path is correct
   - Verify the module exists
   - Add missing `__init__.py` files if needed

2. **Missing dependencies**:
   - Check `requirements.txt`
   - Install missing packages
   - Update imports

3. **Logic errors**:
   - Read the source code being tested
   - Read the test code
   - Identify the discrepancy
   - Fix the appropriate file (prefer fixing tests only if the source is correct)

4. **Mock/Fixture issues**:
   - Ensure mocks match actual function signatures
   - Verify fixtures are properly scoped
   - Check for missing mock patches

5. **Environment issues**:
   - Verify environment variables are set
   - Check for required test fixtures/data

### Step 4: Re-run Tests

After making fixes, re-run the tests:

```bash
pytest tests/ -v --tb=short $ARGUMENTS
```

Repeat Steps 2-4 until:
- All tests pass, OR
- Maximum of 5 fix iterations is reached

### Step 5: Report Results

Provide a summary:
- Total tests run
- Tests that passed
- Tests that were fixed (with description of fixes)
- Any remaining failures that couldn't be auto-fixed

## Constraints

- Do NOT modify test assertions unless the test itself is clearly wrong
- Prefer fixing source code over tests when the test expectation is correct
- Always explain what was changed and why
- If a fix is uncertain, ask for confirmation before applying
- Maximum 5 fix iterations to prevent infinite loops

## Success Criteria

- [ ] All tests pass (or clear explanation of unfixable failures)
- [ ] No regressions introduced
- [ ] All fixes are explained
- [ ] Code still follows project conventions (check CLAUDE.md)
