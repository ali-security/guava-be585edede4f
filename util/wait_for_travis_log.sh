#!/bin/sh
# Keep the job open until Travis has archived this job's log through the test
# report printed by util/print_skipped_tests.py, so a log fetched the moment the
# build finishes is complete. after_script cannot change the build result.
url="https://api.travis-ci.com/v3/job/${TRAVIS_JOB_ID}/log.txt"
marker="SEAL_TEST_REPORT_""COMPLETE"
waited=0
while [ "$waited" -lt 1320 ]; do
  if curl -fsSL "$url" 2>/dev/null | grep -q "$marker"; then
    echo "Travis log archived through the test report (${waited}s)"
    exit 0
  fi
  echo "waiting for Travis log archive... (${waited}s)"
  sleep 20
  waited=$((waited + 20))
done
echo "stopped waiting for the Travis log archive after ${waited}s"
exit 0
