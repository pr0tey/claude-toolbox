.PHONY: test test-mdr test-mdr-smoke test-mdr-corner test-mdr-realistic

MDR_TEST = python3 tests/micro-decisions/e2e/test_mdr_protocol.py

# Run all micro-decisions E2E tests (~$1.10)
test-mdr:
	$(MDR_TEST) all

# Run smoke tests only (fast, ~$0.50)
test-mdr-smoke:
	$(MDR_TEST) smoke

# Run corner case tests (~$0.60)
test-mdr-corner:
	$(MDR_TEST) corner

# Run realistic tests with actual code (~$0.60)
test-mdr-realistic:
	$(MDR_TEST) realistic

# Run all plugin tests
test: test-mdr
